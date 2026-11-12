"""Home Connect Coordinator."""

from __future__ import annotations

import logging
import time
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

from .const import CONF_AES_IV, CONF_PSK, MAX_RECONECT_TIME

if TYPE_CHECKING:
    from asyncio import TimerHandle

    from homeassistant.core import HomeAssistant

    from . import HCConfigEntry

_LOGGER = logging.getLogger(__name__)


class HomeConnectCoordinator(DataUpdateCoordinator):
    """My custom coordinator."""

    config_entry: HCConfigEntry
    appliance: HomeAppliance
    _connecting: bool = True
    _reconnecting: bool = False
    _reconnect_timeout: TimerHandle | None = None
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
        self._cancel_reconnect_timeout()
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
        return None

    async def _connection_state_callback(self, event: ConnectionState) -> None:
        if event == ConnectionState.RECONNECTING:
            if not self._reconnecting:
                self._reconnecting = True
                reconnect_timeout = int(self.hass.loop.time()) + MAX_RECONECT_TIME
                self._reconnect_timeout = self.hass.loop.call_at(
                    reconnect_timeout, self._connection_reconnect_callback
                )

        elif event == ConnectionState.CONNECTED:
            self.connected = True
            if self._reconnecting:
                self.logger.debug("Reconnected to %s", self.appliance.info.get("vib"))
                self._reconnecting = False
            # a timeout left from a recovered outage would hit a later, shorter one
            self._cancel_reconnect_timeout()

        elif event == ConnectionState.CLOSED:
            self.connected = False
            self._cancel_reconnect_timeout()

        self.async_set_updated_data(None)

    def _cancel_reconnect_timeout(self) -> None:
        if self._reconnect_timeout is not None:
            self._reconnect_timeout.cancel()
            self._reconnect_timeout = None

    def _connection_reconnect_callback(self) -> None:
        self._reconnect_timeout = None
        if not self.appliance.session.connected:
            self.connected = False
            self.async_set_updated_data(None)
