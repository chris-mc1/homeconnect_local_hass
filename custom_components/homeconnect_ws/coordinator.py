"""Home Connect Coordinator."""

from __future__ import annotations

import logging
import time
from datetime import timedelta
from typing import TYPE_CHECKING

from homeassistant.const import CONF_DEVICE_ID, CONF_HOST
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
from homeconnect_websocket.message import Message

from .const import CONF_AES_IV, CONF_PSK, MAX_RECONECT_TIME

# The appliance only pushes changes; re-read all values periodically.
REFRESH_INTERVAL = timedelta(seconds=60)

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
            update_interval=REFRESH_INTERVAL,
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

    async def _async_update_data(self) -> None:
        if not self.appliance.session.connected:
            return None
        try:
            response = await self.appliance.session.send_sync(
                Message(resource="/ro/allMandatoryValues")
            )
            if response is not None and response.data:
                async with self.appliance.callback_manager:
                    await self.appliance._update_entities(response.data)  # noqa: SLF001
        except Exception:  # noqa: BLE001
            self.logger.debug("Periodic refresh failed", exc_info=True)
        return None

    async def _connection_state_callback(self, event: ConnectionState) -> None:
        if event == ConnectionState.RECONNECTING:
            if not self._reconnecting:
                self._reconnecting = True
                reconnect_timeout = int(self.hass.loop.time()) + MAX_RECONECT_TIME
                self.hass.loop.call_at(reconnect_timeout, self._connection_reconnect_callback)

        elif event == ConnectionState.CONNECTED:
            self.connected = True
            if self._reconnecting:
                self.logger.debug("Reconnected to %s", self.appliance.info.get("vib"))
                self._reconnecting = False

        elif event == ConnectionState.CLOSED:
            self.connected = False

        self.async_set_updated_data(None)

    def _connection_reconnect_callback(self) -> None:
        if not self.appliance.session.connected:
            self.connected = False
            self.async_set_updated_data(None)
