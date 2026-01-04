"""Sensor entities."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from aiohttp.client_exceptions import ClientConnectionResetError
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.device_registry import DeviceInfo
from homeconnect_websocket import HomeAppliance, NotConnectedError

from .entity import HCEntity
from .helpers import create_entities

_LOGGER = logging.getLogger(__name__)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity import DeviceInfo
    from homeassistant.helpers.entity_platform import AddEntitiesCallback
    from homeconnect_websocket import HomeAppliance

    from . import HCConfigEntry
    from .entity_descriptions.descriptions_definitions import HCSensorEntityDescription

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001
    config_entry: HCConfigEntry,
    async_add_entites: AddEntitiesCallback,
) -> None:
    """Set up sensor platform."""
    entities = create_entities(
        {
            "sensor": HCSensor,
            "event_sensor": HCEventSensor,
            "active_program": HCActiveProgram,
            "wifi": HCWiFI,
        },
        config_entry.runtime_data,
    )
    async_add_entites(entities)


class HCSensor(HCEntity, SensorEntity):
    """Sensor Entity."""

    entity_description: HCSensorEntityDescription

    def __init__(
        self,
        entity_description: HCSensorEntityDescription,
        appliance: HomeAppliance,
        device_info: DeviceInfo,
    ) -> None:
        super().__init__(entity_description, appliance, device_info)

        if self._entity.enum:
            if self.entity_description.has_state_translation:
                self._attr_options = [str(value).lower() for value in self._entity.enum.values()]
            else:
                self._attr_options = [str(value) for value in self._entity.enum.values()]

    @property
    def native_value(self) -> int | float | str:
        if self._entity.value is None:
            return None
        if self._entity.enum and self.entity_description.has_state_translation:
            return str(self._entity.value).lower()
        if self.entity_description.key == "sensor_remaining_program_time" and self._entity.value is not None:
            from datetime import timedelta
            from homeassistant.util import dt as dt_util
            return dt_util.now() + timedelta(seconds=self._entity.value)
        return self._entity.value


class HCEventSensor(HCEntity, SensorEntity):
    """Event Sensor Entity."""

    entity_description: HCSensorEntityDescription

    @property
    def native_value(self) -> str:
        if self.entity_description.options:
            for entity, value in zip(self._entities, self.entity_description.options, strict=False):
                if (entity.enum is not None and entity.value in {"Present", "Confirmed"}) or (
                    entity.enum is None and bool(entity.value)
                ):
                    return value
        return self.entity_description.options[-1]

    @property
    def available(self) -> bool:
        return self._appliance.session.connected


class HCActiveProgram(HCSensor):
    """Active Program Sensor Entity."""

    entity_description: HCSensorEntityDescription

    def __init__(
        self,
        entity_description: HCSensorEntityDescription,
        appliance: HomeAppliance,
        device_info: DeviceInfo,
    ) -> None:
        super().__init__(entity_description, appliance, device_info)
        self._attr_options = list(entity_description.mapping.values())

    @property
    def native_value(self) -> str | None:
        if self._appliance.active_program:
            if self._appliance.active_program.name in self.entity_description.mapping:
                return self.entity_description.mapping[self._appliance.active_program.name]
            return self._appliance.active_program.name
        return None


class HCWiFI(HCEntity, SensorEntity):
    """WiFi signal Sensor Entity with push-like updates."""

    _attr_should_poll = True

    def __init__(
        self,
        entity_description: HCSensorEntityDescription,
        appliance: HomeAppliance,
        device_info: DeviceInfo,
    ) -> None:
        super().__init__(entity_description, appliance, device_info)

    async def async_update(self) -> None:
        try:
            network_info = await self._appliance.get_network_config()
            if network_info and isinstance(network_info, list) and "rssi" in network_info[0]:
                self._attr_native_value = network_info[0]["rssi"]
            else:
                _LOGGER.debug("WiFi update failed: unexpected response format: %s", network_info)
        except ClientConnectionResetError:
            _LOGGER.debug("WiFi update failed: Connection reset")
        except NotConnectedError:
            _LOGGER.debug("WiFi update failed: Not connected")
