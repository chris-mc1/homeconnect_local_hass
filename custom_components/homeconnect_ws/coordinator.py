"""Home Connect Coordinator."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import TYPE_CHECKING

from homeassistant.const import CONF_DEVICE_ID, CONF_HOST
from homeassistant.core import callback
from homeassistant.exceptions import ConfigEntryError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeconnect_websocket import (
    AllreadyConnectedError,
    ConnectionFailedError,
    ConnectionState,
    DeviceDescription,
    HCHandshakeError,
    HomeAppliance,
)

from .const import CONF_AES_IV, CONF_PSK, MAX_RECONECT_TIME

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from . import HCConfigEntry

_LOGGER = logging.getLogger(__name__)


class HomeConnectCoordinator(DataUpdateCoordinator):
    """My custom coordinator."""

    config_entry: HCConfigEntry
    appliance: HomeAppliance
    _connecting: bool = True
    _reconnecting: bool = False
    connected: bool = False
    _reconnect_timer: asyncio.TimerHandle | None = None

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

        self.appliance = HomeAppliance(
            description=description,
            host=config_entry.data[CONF_HOST],
            app_name="Homeassistant",
            app_id=config_entry.data[CONF_DEVICE_ID],
            psk64=config_entry.data[CONF_PSK],
            iv64=config_entry.data.get(CONF_AES_IV, None),
            connection_callback=self._connection_state_callback,
        )
        self.disconnect_time = time.time()
        if not self.appliance.info:
            msg = "Appliance has no device info"
            raise ConfigEntryError(msg)

    async def close(self) -> None:
        self._connecting = False
        self._cancel_reconnect_timer()
        await self.appliance.close()

    async def _async_setup(self) -> None:
        self.config_entry.async_create_background_task(
            self.hass, self._connect(), f"homeconnect_ws_{self.name}"
        )

    async def _connect(self) -> None:
        self.logger.debug("Connecting to %s", self.appliance.info.get("vib"))
        first_failure = True
        while self._connecting:
            try:
                await self.appliance.connect()
                if self.appliance.session.connected:
                    self.connected = True  # FIX
                    self.async_set_updated_data(None)  # FIX
                    return
            except (ConnectionFailedError, HCHandshakeError):
                await self.appliance.close()
                msg = f"Can't connect to {self.config_entry.data[CONF_HOST]}, retrying"
                if first_failure:
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

            if self._connecting:
                await asyncio.sleep(5)

    async def _async_update_data(self) -> None:
        return None

    async def _connection_state_callback(self, event: ConnectionState) -> None:
        if not self._connecting:
            return

        if event == ConnectionState.CONNECTED:
            self.connected = True
            self._cancel_reconnect_timer()
            if self._reconnecting:
                self.logger.debug("Reconnected to %s", self.appliance.info.get("vib"))
            self._reconnecting = False

        elif event in (
            ConnectionState.RECONNECTING,
            ConnectionState.CLOSING,
            ConnectionState.CLOSED,
            ConnectionState.ABNORMAL_CLOSURE,
        ):
            # A handshake failure can terminate the library's reconnect loop.
            # Keep one deadline even if the library changes state again.
            if self._reconnect_timer is None:
                self._reconnecting = True
                self._reconnect_timer = self.hass.loop.call_later(
                    MAX_RECONECT_TIME, self._connection_reconnect_callback
                )
            if event in (ConnectionState.CLOSED, ConnectionState.ABNORMAL_CLOSURE):
                self.connected = False

        self.async_set_updated_data(None)

    @callback
    def _cancel_reconnect_timer(self) -> None:
        if self._reconnect_timer is not None:
            self._reconnect_timer.cancel()
            self._reconnect_timer = None

    @callback
    def _connection_reconnect_callback(self) -> None:
        self._reconnect_timer = None
        if not self._connecting or self.appliance.session.connected:
            return

        self.connected = False
        self.async_set_updated_data(None)
        self.logger.warning("Connection recovery timed out; reloading this appliance")
        self.config_entry.async_create_background_task(
            self.hass,
            self.hass.config_entries.async_reload(self.config_entry.entry_id),
            f"homeconnect_ws_recover_{self.name}",
        )
