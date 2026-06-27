"""Home Connect Coordinator."""

from __future__ import annotations

import asyncio
import logging
import time
from copy import deepcopy
from typing import TYPE_CHECKING

import aiohttp
from homeassistant.const import CONF_DESCRIPTION, CONF_DEVICE_ID, CONF_HOST
from homeassistant.core import callback
from homeassistant.exceptions import ConfigEntryError
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.event import async_call_later
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
    DOMAIN,
)

if TYPE_CHECKING:
    from datetime import datetime

    from homeassistant.core import CALLBACK_TYPE, HomeAssistant

    from . import HCConfigEntry

_LOGGER = logging.getLogger(__name__)

CONNECTION_LOST_ISSUE_DELAY = 25  # seconds
CONNECT_RETRY_INITIAL_DELAY = 5  # seconds
CONNECT_RETRY_MAX_DELAY = 60  # seconds

# Appliance types that routinely cut their own WiFi when powered off between
# cycles. Being unreachable is a normal, expected state for these, not a
# fault, so we don't escalate connect failures to ERROR or raise a repair
# issue for them (see upstream chris-mc1/homeconnect_local_hass issues #274
# and #293).
EXPECTED_OFFLINE_APPLIANCE_TYPES = frozenset({"Washer", "Dryer", "WasherDryer"})


class HomeConnectCoordinator(DataUpdateCoordinator):
    """My custom coordinator."""

    config_entry: HCConfigEntry
    appliance: HomeAppliance
    _connecting: bool = True
    connected: bool = False
    _connection_lost_issue_unsub: CALLBACK_TYPE | None = None
    _track_connectivity_issues: bool

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
        self.disconnect_time = time.time()
        if not self.appliance.info:
            raise ConfigEntryError(
                translation_domain=DOMAIN,
                translation_key="no_device_info",
            )
        self._track_connectivity_issues = (
            self.appliance.info.get("type") not in EXPECTED_OFFLINE_APPLIANCE_TYPES
        )

    async def close(self) -> None:
        self._connecting = False
        self._cancel_connection_lost_issue_timer()
        ir.async_delete_issue(self.hass, DOMAIN, self._connection_lost_issue_id)
        await self.appliance.close()

    @property
    def _connection_lost_issue_id(self) -> str:
        return f"connection_lost_{self.config_entry.entry_id}"

    async def _async_setup(self) -> None:
        self.config_entry.async_create_task(self.hass, self._connect())

    async def _connect(self) -> None:
        self.logger.debug(
            "Connecting to %s", self.config_entry.data[CONF_DESCRIPTION]["info"].get("vib")
        )
        first_failure = True
        retry_delay = CONNECT_RETRY_INITIAL_DELAY
        while self._connecting:
            try:
                await self.appliance.connect()
                if self.appliance.session.connected:
                    self.connected = True  # FIX
                    self.async_set_updated_data(None)  # FIX
                    return
            except (ConnectionFailedError, HCHandshakeError, aiohttp.ClientResponseError):
                # aiohttp.ClientResponseError (e.g. a 404 on the websocket upgrade)
                # isn't wrapped by the library into ConnectionFailedError/
                # HCHandshakeError, and doesn't trigger a connection state change
                # either, so it needs to be handled here directly.
                await self.appliance.close()
                self._mark_disconnected()
                msg = f"Can't connect to {self.config_entry.data[CONF_HOST]}, retrying"
                if first_failure and self._track_connectivity_issues:
                    self.logger.error(msg)  # noqa: TRY400
                    first_failure = False  # first_failure_fix
                else:
                    self.logger.debug(msg)
            except AllreadyConnectedError:
                await self.appliance.close()
                msg = f"Allready connected to {self.config_entry.data[CONF_HOST]}"
                self.logger.error(msg)  # noqa: TRY400
                return
            except Exception:
                await self.appliance.close()
                msg = f"Can't connect to {self.config_entry.data[CONF_HOST]}"
                self.logger.exception(msg)

            if not self._connecting:
                return
            await asyncio.sleep(retry_delay)
            retry_delay = min(retry_delay * 2, CONNECT_RETRY_MAX_DELAY)

    async def _async_update_data(self) -> None:
        return None

    async def _connection_state_callback(self, event: ConnectionState) -> None:
        if event == ConnectionState.CONNECTED:
            if not self.connected:
                self.logger.info(
                    "Connection to %s restored",
                    self.config_entry.data[CONF_DESCRIPTION]["info"].get("vib"),
                )
            self.connected = True
            self._cancel_connection_lost_issue_timer()
            ir.async_delete_issue(self.hass, DOMAIN, self._connection_lost_issue_id)

        elif event in (ConnectionState.RECONNECTING, ConnectionState.ABNORMAL_CLOSURE):
            # ABNORMAL_CLOSURE covers a connection that has never succeeded yet
            # (e.g. the appliance is already unreachable when HA starts), since
            # the library only enters RECONNECTING after a prior successful
            # connection drops.
            if self.connected and self._track_connectivity_issues:
                self.logger.warning(
                    "Connection to %s lost",
                    self.config_entry.data[CONF_DESCRIPTION]["info"].get("vib"),
                )
            self._mark_disconnected()

        elif event == ConnectionState.CLOSED:
            self.connected = False
            self._cancel_connection_lost_issue_timer()
            ir.async_delete_issue(self.hass, DOMAIN, self._connection_lost_issue_id)

        self.async_set_updated_data(None)

    @callback
    def _mark_disconnected(self) -> None:
        """Mark the appliance as disconnected and schedule the repair issue timer."""
        self.connected = False
        if self._track_connectivity_issues and self._connection_lost_issue_unsub is None:
            self._connection_lost_issue_unsub = async_call_later(
                self.hass,
                CONNECTION_LOST_ISSUE_DELAY,
                self._async_create_connection_lost_issue,
            )

    @callback
    def _cancel_connection_lost_issue_timer(self) -> None:
        if self._connection_lost_issue_unsub is not None:
            self._connection_lost_issue_unsub()
            self._connection_lost_issue_unsub = None

    @callback
    def _async_create_connection_lost_issue(self, _now: datetime) -> None:
        self._connection_lost_issue_unsub = None
        if not self.connected:
            ir.async_create_issue(
                self.hass,
                DOMAIN,
                self._connection_lost_issue_id,
                is_fixable=False,
                severity=ir.IssueSeverity.WARNING,
                translation_key="connection_lost",
                translation_placeholders={
                    "name": self.config_entry.data[CONF_DESCRIPTION]["info"].get("vib"),
                },
            )
