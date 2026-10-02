"""Home Connect Coordinator."""

from __future__ import annotations

import asyncio
import logging
import random
import time
from typing import TYPE_CHECKING

import aiohttp
from homeassistant.const import CONF_DEVICE_ID, CONF_HOST
from homeassistant.core import callback
from homeassistant.exceptions import ConfigEntryError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeconnect_websocket import (
    AllreadyConnectedError,
    ConnectionState,
    DeviceDescription,
    HomeAppliance,
)
from homeconnect_websocket.errors import HCConnectionError

from .const import (
    CLOSE_TIMEOUT,
    CONF_AES_IV,
    CONF_PSK,
    CONNECT_TIMEOUT,
    INITIAL_RECONNECT_DELAY,
    MAX_RECONECT_TIME,
    MAX_RECONNECT_DELAY,
    MIN_STABLE_CONNECTION_TIME,
    RECONNECT_JITTER,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from . import HCConfigEntry

_LOGGER = logging.getLogger(__name__)

# Expected failures while the appliance is off or unreachable:
# - HCConnectionError: ConnectionFailedError, HCHandshakeError, AuthenticationError
# - aiohttp.ClientError: e.g. WSServerHandshakeError "503 Invalid response status"
# - OSError, TimeoutError (asyncio.TimeoutError is an alias)
CONNECTION_ERRORS = (HCConnectionError, aiohttp.ClientError, OSError, TimeoutError)


def reconnect_delay(failures: int) -> float:
    """
    Return the delay in seconds before the next connect attempt.

    Exponential backoff (5 s, 10 s, 20 s, ...) capped at MAX_RECONNECT_DELAY, reduced
    by a random jitter of up to RECONNECT_JITTER so appliances don't retry in lockstep.
    """
    delay = min(INITIAL_RECONNECT_DELAY * 2 ** max(failures - 1, 0), MAX_RECONNECT_DELAY)
    return delay * (1 - random.uniform(0, RECONNECT_JITTER))  # noqa: S311


def _describe_error(exc: BaseException) -> str:
    """Return a short, single line reason for a connection error."""
    if isinstance(exc, aiohttp.WSServerHandshakeError):
        return f"HTTP {exc.status} {exc.message}"
    if isinstance(exc, TimeoutError) and not str(exc):
        return "Timeout"
    reason = f"{type(exc).__name__}: {exc}" if str(exc) else type(exc).__name__
    if exc.__cause__ is not None and exc.__cause__ is not exc:
        reason = f"{reason} ({_describe_error(exc.__cause__)})"
    return reason


class HomeConnectCoordinator(DataUpdateCoordinator):
    """
    Home Connect Coordinator.

    Owns the connection to the appliance: the initial connect and every reconnect
    after the connection was lost run in one background task with exponential backoff.
    The library's own reconnect loop is disabled, it retries without delay.
    """

    config_entry: HCConfigEntry
    appliance: HomeAppliance
    connected: bool = False

    def __init__(
        self, hass: HomeAssistant, config_entry: HCConfigEntry, description: DeviceDescription
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            # Name of the data. For logging purposes.
            name=description["info"]["model"],
            config_entry=config_entry,
            always_update=True,
        )
        self._host: str = config_entry.data[CONF_HOST]
        self._closing = False
        self._closed = False
        self._connect_task: asyncio.Task | None = None
        self._unavailable_timer: asyncio.TimerHandle | None = None
        self._connected_since = 0.0
        # Connections lost shortly after connecting, in a row
        self._unstable_connections = 0
        # Own session, closed in close(). The library would create its own session and
        # never close it after an abnormal closure ("Unclosed client session").
        self._client_session = aiohttp.ClientSession()

        self.appliance = HomeAppliance(
            description=description,
            host=self._host,
            app_name="Homeassistant",
            app_id=config_entry.data[CONF_DEVICE_ID],
            psk64=config_entry.data[CONF_PSK],
            iv64=config_entry.data.get(CONF_AES_IV, None),
            session=self._client_session,
            reconect=False,
            connection_callback=self._connection_state_callback,
        )
        self._wrap_library_recv_loop()
        self.disconnect_time = time.time()
        if not self.appliance.info:
            self._client_session.detach()
            msg = "Appliance has no device info"
            raise ConfigEntryError(msg)

    def _wrap_library_recv_loop(self) -> None:
        """
        Handle connection errors raised by the library receive loop.

        Without reconnect, HCSession re-raises connection errors (e.g. "No PONG received")
        from its receive loop, which runs in a background task nobody awaits. asyncio then
        logs "Task exception was never retrieved". The lost connection is handled via the
        connection state callback, so the error is only logged at debug level.
        """
        session = self.appliance.session
        recv_loop = session._wrap_recv_loop  # noqa: SLF001

        async def wrap_recv_loop() -> None:
            try:
                await recv_loop()
            except HCConnectionError as exc:
                self.logger.debug("Receive loop for %s ended: %s", self._host, _describe_error(exc))

        session._wrap_recv_loop = wrap_recv_loop  # noqa: SLF001

    async def close(self) -> None:
        """Stop connecting and close the connection, safe to call multiple times."""
        if self._closed:
            return
        self._closed = True
        self._closing = True
        self._cancel_unavailable_timer()
        if self._connect_task is not None and not self._connect_task.done():
            self._connect_task.cancel()
            # asyncio.wait doesn't raise, the task's CancelledError stays in the task
            await asyncio.wait([self._connect_task])
        await self._close_appliance()
        if not self._client_session.closed:
            await self._client_session.close()

    async def async_shutdown(self) -> None:
        """Cancel listeners and close the connection, called on unload and HA stop."""
        await super().async_shutdown()
        await self.close()

    async def _async_setup(self) -> None:
        self._start_connect()

    async def _async_update_data(self) -> None:
        return None

    @property
    def _connecting(self) -> bool:
        return self._connect_task is not None and not self._connect_task.done()

    def _start_connect(self, delay: float = 0) -> None:
        if self._closing or self._connecting:
            return
        self._connect_task = self.config_entry.async_create_background_task(
            self.hass, self._connect(delay), f"homeconnect_ws_{self.name}"
        )

    async def _connect(self, delay: float = 0) -> None:
        if delay:
            self.logger.debug("Reconnecting to %s in %.0f s", self._host, delay)
            await asyncio.sleep(delay)
        self.logger.debug("Connecting to %s (%s)", self.appliance.info.get("vib"), self._host)
        failures = 0
        traceback_logged = False
        while not self._closing:
            try:
                async with asyncio.timeout(CONNECT_TIMEOUT):
                    await self.appliance.connect()
                if not self.appliance.session.connected:
                    msg = "Not connected after handshake"
                    raise ConnectionError(msg)  # noqa: TRY301
            except AllreadyConnectedError:
                self.logger.error("Allready connected to %s", self._host)  # noqa: TRY400
                return
            except CONNECTION_ERRORS as exc:
                reason = _describe_error(exc)
                exc_info = None
            except Exception as exc:  # noqa: BLE001
                # Unexpected, log the traceback once per outage
                reason = _describe_error(exc)
                exc_info = None if traceback_logged else exc
                traceback_logged = True
            else:
                self._connected(failures)
                return

            await self._close_appliance()
            failures += 1
            delay = reconnect_delay(failures)
            if failures == 1 or exc_info is not None:
                self.logger.warning(
                    "Can't connect to %s: %s, retrying in %.0f s",
                    self._host,
                    reason,
                    delay,
                    exc_info=exc_info,
                )
            else:
                self.logger.debug(
                    "Can't connect to %s (attempt %d): %s, retrying in %.0f s",
                    self._host,
                    failures,
                    reason,
                    delay,
                )
            await asyncio.sleep(delay)

    def _connected(self, failures: int) -> None:
        if failures:
            self.logger.info("Connected to %s after %d failed attempt(s)", self._host, failures)
        else:
            self.logger.debug("Connected to %s", self._host)
        self._cancel_unavailable_timer()
        self._connected_since = self.hass.loop.time()
        self.connected = True
        self.async_set_updated_data(None)

    async def _close_appliance(self) -> None:
        """Close the appliance connection without blocking the event loop."""
        try:
            async with asyncio.timeout(CLOSE_TIMEOUT):
                await self.appliance.close()
        except TimeoutError:
            self.logger.debug("Timeout closing connection to %s", self._host)
            await self._cancel_library_tasks()
        except Exception:
            self.logger.debug("Error closing connection to %s", self._host, exc_info=True)

    async def _cancel_library_tasks(self) -> None:
        # Workaround: TaskManager.shutdown() spins forever if a task outlives its timeout
        task_manager = self.appliance._task_manager  # noqa: SLF001
        tasks = [
            task
            for task in (task_manager._tasks | task_manager._background_tasks)  # noqa: SLF001
            if task is not asyncio.current_task()
        ]
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.wait(tasks, timeout=CLOSE_TIMEOUT)

    async def _connection_state_callback(self, event: ConnectionState) -> None:
        if event == ConnectionState.CONNECTED:
            self.connected = True
            self._cancel_unavailable_timer()

        elif event in (ConnectionState.ABNORMAL_CLOSURE, ConnectionState.CLOSED):
            # While the connect task runs, it owns the connection state
            if not self._closing and not self._connecting:
                if event == ConnectionState.ABNORMAL_CLOSURE and self.connected:
                    self._connection_lost()
                else:
                    self.connected = False
                    self._start_connect()

        self.async_set_updated_data(None)

    def _connection_lost(self) -> None:
        if self.hass.loop.time() - self._connected_since < MIN_STABLE_CONNECTION_TIME:
            # Appliance drops the connection right after connecting, keep backing off
            self._unstable_connections += 1
        else:
            self._unstable_connections = 0
        delay = reconnect_delay(self._unstable_connections) if self._unstable_connections else 0
        if self._unstable_connections <= 1:
            self.logger.warning("Connection to %s lost, reconnecting", self._host)
        else:
            self.logger.debug(
                "Connection to %s lost again shortly after connecting, reconnecting in %.0f s",
                self._host,
                delay,
            )
        # Keep entities available for a short outage
        self._start_unavailable_timer()
        self._start_connect(delay)

    def _start_unavailable_timer(self) -> None:
        self._cancel_unavailable_timer()
        self._unavailable_timer = self.hass.loop.call_later(
            MAX_RECONECT_TIME, self._connection_reconnect_callback
        )

    def _cancel_unavailable_timer(self) -> None:
        if self._unavailable_timer is not None:
            self._unavailable_timer.cancel()
            self._unavailable_timer = None

    @callback
    def _connection_reconnect_callback(self) -> None:
        self._unavailable_timer = None
        if not self.appliance.session.connected:
            self.connected = False
            self.async_set_updated_data(None)
