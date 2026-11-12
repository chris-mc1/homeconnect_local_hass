"""Home Connect Coordinator."""

from __future__ import annotations

import asyncio
import logging
import random
import time
from collections import deque
from typing import TYPE_CHECKING

import aiohttp
from homeassistant.const import CONF_DEVICE_ID, CONF_HOST
from homeassistant.exceptions import ConfigEntryError
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeconnect_websocket import (
    AuthenticationError,
    ConnectionState,
    DeviceDescription,
    HomeAppliance,
    HomeConnectError,
)

from . import const
from .const import (
    CONF_AES_IV,
    CONF_PSK,
    DOMAIN,
    ISSUE_RECONNECT_STORM,
    ISSUE_WRONG_DEVICE,
    MAX_RECONECT_TIME,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from . import HCConfigEntry

_LOGGER = logging.getLogger(__name__)

_DISCONNECTED_STATES = (
    ConnectionState.ABNORMAL_CLOSURE,
    ConnectionState.CLOSED,
    ConnectionState.RECONNECTING,
)


def _normalize_mac(mac: object) -> str | None:
    """Reduce a MAC address to its lowercase hex digits."""
    if not isinstance(mac, str):
        return None
    normalized = "".join(char for char in mac.lower() if char in "0123456789abcdef")
    return normalized if len(normalized) == 12 else None


class _ConnectFailure:
    """Reason a connection attempt failed."""

    def __init__(self, reason: str, *, identity: bool = False) -> None:
        self.reason = reason
        self.identity = identity
        """The appliance did not authenticate or is not the expected appliance."""


class HomeConnectCoordinator(DataUpdateCoordinator):
    """
    Owns the connection to one appliance.

    Exactly one connection loop runs per coordinator. Every connection attempt
    and every close is bounded by a timeout and attempts are spaced by an
    exponential backoff, so a misbehaving appliance can at worst make this
    config entry unavailable.
    """

    config_entry: HCConfigEntry
    appliance: HomeAppliance
    connected: bool = False
    _closing: bool = False
    _connection_task: asyncio.Task | None = None
    _unavailable_handle: asyncio.TimerHandle | None = None

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
        # The appliance updates its info dict in place after connecting, keep the
        # expected identity from the profile.
        self._expected_mac = _normalize_mac(description["info"].get("mac"))
        self._host = config_entry.data[CONF_HOST]

        self.appliance = HomeAppliance(
            description=description,
            host=self._host,
            app_name="Homeassistant",
            app_id=config_entry.data[CONF_DEVICE_ID],
            psk64=config_entry.data[CONF_PSK],
            iv64=config_entry.data.get(CONF_AES_IV, None),
            # One reused session per config entry, closed by HA on unload.
            session=async_create_clientsession(hass),
            # Reconnecting is done here, with backoff and timeouts.
            reconect=False,
            connection_callback=self._connection_state_callback,
        )
        self.disconnect_time = time.time()
        self._disconnected = asyncio.Event()
        self._connect_times: deque[float] = deque()
        if not self.appliance.info:
            msg = "Appliance has no device info"
            raise ConfigEntryError(msg)

    async def close(self) -> None:
        """Stop the connection loop and close the connection."""
        self._closing = True
        self._cancel_unavailable_timer()
        task = self._connection_task
        if task is not None and not task.done():
            task.cancel()
            # Never returns later than the timeout, never raises
            await asyncio.wait([task], timeout=const.CLOSE_TIMEOUT)
        self._connection_task = None
        await self._safe_close()
        self.connected = False
        self._delete_issues()

    async def _async_setup(self) -> None:
        self._start_connection_loop()

    def _start_connection_loop(self) -> None:
        """Start the connection loop, unless it is already running."""
        if self._connection_task is not None and not self._connection_task.done():
            return
        self._closing = False
        self._connection_task = self.config_entry.async_create_background_task(
            self.hass, self._connection_loop(), f"homeconnect_ws_{self.name}"
        )

    async def _connection_loop(self) -> None:
        """Connect, wait for the connection to drop, back off, repeat."""
        self.logger.debug("Connecting to %s", self.appliance.info.get("vib"))
        failures = 0
        identity_failures = 0
        while not self._closing:
            await self._reconnect_watchdog()
            self._disconnected.clear()
            failure = await self._connect_once()

            if failure is None:
                connected_at = self.hass.loop.time()
                self._on_connected(recovered=failures > 0)
                identity_failures = 0
                await self._wait_for_disconnect()
                if self._closing:
                    return
                if self.hass.loop.time() - connected_at >= const.STABLE_CONNECTION_TIME:
                    failures = 0
                else:
                    # Connected but dropped right away: keep backing off
                    failures += 1
                failure = _ConnectFailure("connection lost")
                self._schedule_unavailable()
            else:
                failures += 1
                if failure.identity:
                    identity_failures += 1

            await self._safe_close()

            delay = self._backoff_delay(failures)
            if identity_failures >= const.IDENTITY_FAILURE_THRESHOLD:
                self._on_wrong_device(
                    failure, first=identity_failures == const.IDENTITY_FAILURE_THRESHOLD
                )
                delay = max(delay, const.IDENTITY_RETRY_DELAY)
            self._log_failure(failure, failures, delay)
            await asyncio.sleep(delay)

    async def _connect_once(self) -> _ConnectFailure | None:  # noqa: PLR0911
        """Run one connection attempt. Returns None once connected and verified."""
        try:
            async with asyncio.timeout(const.CONNECT_TIMEOUT):
                await self.appliance.connect()
        except AuthenticationError as exc:
            return _ConnectFailure(f"authentication failed ({exc})", identity=True)
        except TimeoutError:
            return _ConnectFailure(f"no answer within {const.CONNECT_TIMEOUT} s")
        except (HomeConnectError, aiohttp.ClientError, OSError) as exc:
            return _ConnectFailure(f"{type(exc).__name__}: {exc}".rstrip(": "))
        except Exception as exc:
            self.logger.debug("Unexpected error connecting to %s", self._host, exc_info=True)
            return _ConnectFailure(f"unexpected {type(exc).__name__}: {exc}")

        if not self.appliance.session.connected:
            return _ConnectFailure("connection closed during setup")

        await asyncio.sleep(0)  # let the appliance process the device info response
        reported_mac = _normalize_mac(self.appliance.info.get("mac"))
        if self._expected_mac and reported_mac and reported_mac != self._expected_mac:
            return _ConnectFailure(
                f"appliance reports MAC {reported_mac}, expected {self._expected_mac}",
                identity=True,
            )
        return None

    async def _wait_for_disconnect(self) -> None:
        """Block until the session is no longer connected."""
        while not self._closing:
            try:
                async with asyncio.timeout(const.LIVENESS_POLL_INTERVAL):
                    await self._disconnected.wait()
            except TimeoutError:
                pass
            if not self.appliance.session.connected:
                return
            self._disconnected.clear()

    async def _safe_close(self) -> None:
        """Close the appliance connection. Never raises, never takes forever."""
        try:
            async with asyncio.timeout(const.CLOSE_TIMEOUT):
                await self.appliance.close()
        except TimeoutError:
            self.logger.warning("Timeout closing connection to %s", self._host)
        except Exception:
            self.logger.exception("Error closing connection to %s", self._host)

    async def _reconnect_watchdog(self) -> None:
        """Pause the entry if connections are attempted too frequently."""
        now = self.hass.loop.time()
        while self._connect_times and now - self._connect_times[0] > 60:
            self._connect_times.popleft()
        if len(self._connect_times) >= const.MAX_CONNECTS_PER_MINUTE:
            self.logger.error(
                "More than %s connection attempts to %s within a minute, pausing for %s s",
                const.MAX_CONNECTS_PER_MINUTE,
                self._host,
                const.RECONNECT_STORM_PAUSE,
            )
            self._create_issue(ISSUE_RECONNECT_STORM)
            self._mark_unavailable()
            self._connect_times.clear()
            await asyncio.sleep(const.RECONNECT_STORM_PAUSE)
        self._connect_times.append(self.hass.loop.time())

    @staticmethod
    def _backoff_delay(failures: int) -> float:
        """Exponential backoff with jitter."""
        exponent = min(max(failures, 1) - 1, 32)
        delay = min(const.RECONNECT_DELAY_INITIAL * 2**exponent, const.RECONNECT_DELAY_MAX)
        return delay * random.uniform(1 - const.RECONNECT_JITTER, 1 + const.RECONNECT_JITTER)  # noqa: S311

    def _log_failure(self, failure: _ConnectFailure, failures: int, delay: float) -> None:
        """Log a failure. Only the first of a streak and reaching the cap are visible."""
        # Uncapped delays of this and the previous attempt
        uncapped = const.RECONNECT_DELAY_INITIAL * 2 ** (failures - 1)
        reached_cap = uncapped >= const.RECONNECT_DELAY_MAX > uncapped / 2
        level = logging.WARNING if failures <= 1 or reached_cap else logging.DEBUG
        self.logger.log(
            level,
            "Can't connect to %s (%s), attempt %s, retrying in %.0f s",
            self._host,
            failure.reason,
            failures,
            delay,
        )

    def _on_connected(self, *, recovered: bool) -> None:
        self._cancel_unavailable_timer()
        self._delete_issues()
        self.connected = True
        if recovered:
            self.logger.info("Reconnected to %s", self._host)
        self.async_set_updated_data(None)

    def _on_wrong_device(self, failure: _ConnectFailure, *, first: bool) -> None:
        if first:
            self.logger.error(
                "%s does not answer as %s (%s), retrying only every %s s",
                self._host,
                self.config_entry.title,
                failure.reason,
                const.IDENTITY_RETRY_DELAY,
            )
        self._create_issue(ISSUE_WRONG_DEVICE)
        self._mark_unavailable()

    def _create_issue(self, issue: str) -> None:
        ir.async_create_issue(
            self.hass,
            DOMAIN,
            f"{issue}_{self.config_entry.entry_id}",
            is_fixable=False,
            severity=ir.IssueSeverity.ERROR,
            translation_key=issue,
            translation_placeholders={"host": self._host, "name": self.config_entry.title},
        )

    def _delete_issues(self) -> None:
        for issue in (ISSUE_WRONG_DEVICE, ISSUE_RECONNECT_STORM):
            ir.async_delete_issue(self.hass, DOMAIN, f"{issue}_{self.config_entry.entry_id}")

    def _schedule_unavailable(self) -> None:
        """Mark entities unavailable if the connection is not back in time."""
        if self._unavailable_handle is None and self.connected:
            self._unavailable_handle = self.hass.loop.call_later(
                MAX_RECONECT_TIME, self._mark_unavailable
            )
        self.async_set_updated_data(None)

    def _cancel_unavailable_timer(self) -> None:
        if self._unavailable_handle is not None:
            self._unavailable_handle.cancel()
            self._unavailable_handle = None

    def _mark_unavailable(self) -> None:
        self._cancel_unavailable_timer()
        if self.connected:
            self.connected = False
            self.async_set_updated_data(None)

    async def _async_update_data(self) -> None:
        return None

    async def _connection_state_callback(self, event: ConnectionState) -> None:
        if event in _DISCONNECTED_STATES:
            self._disconnected.set()
        self.async_set_updated_data(None)
