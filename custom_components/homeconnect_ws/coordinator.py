"""Home Connect Coordinator."""

from __future__ import annotations

import asyncio
import logging
from copy import deepcopy
from typing import TYPE_CHECKING

from homeassistant.const import CONF_DESCRIPTION, CONF_DEVICE_ID, CONF_HOST
from homeassistant.exceptions import ConfigEntryError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeconnect_websocket import (
    AllreadyConnectedError,
    ConnectionFailedError,
    ConnectionState,
    HCHandshakeError,
    HomeAppliance,
)

from .const import (
    CONF_AES_IV,
    CONF_PSK,
    RECONNECT_GRACE_TIME,
    WATCHDOG_INTERVAL,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from . import HCConfigEntry

_LOGGER = logging.getLogger(__name__)

# Backoff bounds (seconds) for the initial connection retry loop.
_INITIAL_RETRY_BACKOFF = 5
_MAX_RETRY_BACKOFF = 60

# Hard cap (seconds) on a single forced close/connect cycle, so a hung socket call
# can't stall the coordinator's update timer and kill the watchdog permanently.
_RECONNECT_TIMEOUT = 30


class HomeConnectCoordinator(DataUpdateCoordinator):
    """
    Coordinator that owns the websocket connection to a Home Connect appliance.

    The upstream ``homeconnect_websocket`` library has its own reconnect loop, but it
    can stop permanently after a handshake error or an unexpected exception, and a ping
    timeout on AES appliances is surfaced as a generic error. To make the integration
    self-healing regardless of library behaviour, this coordinator runs a periodic
    watchdog (``update_interval``) that forces a clean reconnect when the connection has
    been down past a short grace period.

    Availability note: ``connected`` is intentionally not cleared on a brief
    ``RECONNECTING`` event. Entities stay available during the grace period (up to
    ``RECONNECT_GRACE_TIME``) to avoid flapping during short library-driven reconnects;
    only the watchdog marks the connection unavailable once it is confirmed stuck.
    """

    config_entry: HCConfigEntry
    appliance: HomeAppliance
    _connecting: bool = True
    _reconnecting: bool = False
    _initial_connect_done: bool = False
    _down_since: float | None = None
    connected: bool = False

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: HCConfigEntry,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            # Name of the data. For logging purposes.
            name=config_entry.data["description"]["info"]["vib"],
            config_entry=config_entry,
            always_update=True,
            update_interval=WATCHDOG_INTERVAL,
        )
        self.appliance = HomeAppliance(
            description=deepcopy(config_entry.data[CONF_DESCRIPTION]),
            host=config_entry.data[CONF_HOST],
            app_name="Homeassistant",
            app_id=config_entry.data[CONF_DEVICE_ID],
            psk64=config_entry.data[CONF_PSK],
            iv64=config_entry.data.get(CONF_AES_IV, None),
            connection_callback=self._connection_state_callback,
        )
        self._connect_lock = asyncio.Lock()
        if not self.appliance.info:
            msg = "Appliance has no device info"
            raise ConfigEntryError(msg)

    @property
    def _host(self) -> str:
        return self.config_entry.data[CONF_HOST]

    async def close(self) -> None:
        """Stop reconnecting and close the connection (called on unload)."""
        self._connecting = False
        # Serialise against an in-flight forced reconnect so we don't close while a
        # connect is mid-flight (or immediately reconnect after closing).
        async with self._connect_lock:
            await self.appliance.close()

    async def _async_setup(self) -> None:
        self.config_entry.async_create_task(self.hass, self._connect())

    async def _connect(self) -> None:
        """Establish the initial connection, retrying with backoff until it succeeds."""
        self.logger.debug("Connecting to %s", self._host)
        first_failure = True
        backoff = _INITIAL_RETRY_BACKOFF
        try:
            while self._connecting and not self.appliance.session.connected:
                try:
                    async with self._connect_lock:
                        await self.appliance.connect()
                    if self.appliance.session.connected:
                        self.connected = True
                        self._down_since = None
                        self.async_set_updated_data(None)
                        return
                except (ConnectionFailedError, HCHandshakeError):
                    await self.appliance.close()
                    msg = f"Can't connect to {self._host}, retrying"
                    if first_failure:
                        self.logger.error(msg)  # noqa: TRY400
                        first_failure = False
                    else:
                        self.logger.debug(msg)
                except AllreadyConnectedError:
                    # The session is already (re)connecting; let it proceed.
                    return
                except Exception:
                    await self.appliance.close()
                    self.logger.exception("Can't connect to %s", self._host)
                # Back off before retrying so a persistent failure can't spin the loop.
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, _MAX_RETRY_BACKOFF)
        finally:
            self._initial_connect_done = True

    async def _async_update_data(self) -> None:
        """
        Watchdog: verify the connection is alive and recover if it is stuck.

        Returns ``None``; entity state is delivered via appliance callbacks rather than
        coordinator data. This never raises, so a failed reconnect attempt does not mark
        the coordinator update as failed.
        """
        if not self._connecting:
            return
        if self.appliance.session.connected:
            self.connected = True
            self._down_since = None
            return

        # Connection is down. Give the library's own reconnect loop a brief grace
        # period, then force a clean reconnect as a backstop.
        if not self._initial_connect_done:
            return
        now = self.hass.loop.time()
        if self._down_since is None:
            self._down_since = now
        if now - self._down_since >= RECONNECT_GRACE_TIME:
            await self._force_reconnect()
        return

    async def _force_reconnect(self) -> None:
        """Force a clean close/connect cycle as a backstop for a stuck connection."""
        if self._connect_lock.locked():
            # An initial connect or another forced reconnect is already running.
            return
        async with self._connect_lock:
            if self.appliance.session.connected:
                # Recovered between the grace check and acquiring the lock.
                self.connected = True
                self._down_since = None
                return
            # Confirmed still down past the grace period: report unavailable now.
            self.connected = False
            self.async_set_updated_data(None)
            self.logger.debug(
                "Watchdog: connection to %s down for >%ss, forcing reconnect",
                self._host,
                RECONNECT_GRACE_TIME,
            )
            try:
                async with asyncio.timeout(_RECONNECT_TIMEOUT):
                    try:
                        await self.appliance.close()
                    except Exception:  # noqa: BLE001
                        self.logger.debug(
                            "Watchdog close of %s failed, continuing to reconnect",
                            self._host,
                            exc_info=True,
                        )
                    await self.appliance.connect()
            except AllreadyConnectedError:
                self.logger.debug(
                    "Watchdog reconnect to %s skipped: session already connecting",
                    self._host,
                )
                return
            except TimeoutError:
                self.logger.debug("Watchdog reconnect to %s timed out, will retry", self._host)
                return
            except (ConnectionFailedError, HCHandshakeError):
                self.logger.debug("Watchdog reconnect to %s failed, will retry", self._host)
            except Exception:  # noqa: BLE001 - watchdog must never die on an unexpected error
                self.logger.debug("Watchdog reconnect to %s errored", self._host, exc_info=True)
            else:
                if self.appliance.session.connected:
                    self.connected = True
                    self._down_since = None
                    self.async_set_updated_data(None)
                    self.logger.debug("Watchdog reconnected to %s", self._host)

    async def _connection_state_callback(self, event: ConnectionState) -> None:
        """Track connection-state changes reported by the library."""
        if event == ConnectionState.CONNECTED:
            if self._reconnecting:
                self.logger.debug("Reconnected to %s", self._host)
            self.connected = True
            self._reconnecting = False
            self._down_since = None
        elif event in (
            ConnectionState.RECONNECTING,
            ConnectionState.CLOSING,
            ConnectionState.CLOSED,
            ConnectionState.ABNORMAL_CLOSURE,
        ):
            # Only an active reconnect attempt should log "Reconnected" on success.
            self._reconnecting = event == ConnectionState.RECONNECTING
            # Record when the connection went down. We deliberately do not clear
            # `connected` here: the watchdog clears it (and forces a reconnect) once
            # we have been down past the grace period, which avoids flapping entity
            # availability during brief library-driven reconnects.
            if self._down_since is None:
                self._down_since = self.hass.loop.time()

        self.async_set_updated_data(None)
