"""Sensor entities."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.device_registry import DeviceInfo
from homeconnect_websocket import HomeAppliance

from .entity import HCEntity
from .helpers import create_entities

import logging
from aiohttp.client_exceptions import ClientConnectionResetError

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

    #async def async_update(self) -> None:
    #    network_info = await self._appliance.get_network_config()
    #    self._attr_native_value = network_info[0]["rssi"]

    async def async_update(self) -> None:
        """Called by Home Assistant every SCAN_INTERVAL to refresh WiFi RSSI."""
        import asyncio

        max_retries = 3
        delay = 1

        for attempt in range(1, max_retries + 1):
            try:
                network_info = await self._appliance.get_network_config()
                if network_info and isinstance(network_info, list) and "rssi" in network_info[0]:
                    self._attr_native_value = network_info[0]["rssi"]
                    return
                else:
                    _LOGGER.warning(
                        "WiFi entity: unexpected response format while updating signal for %s: %s",
                        self.entity_id,
                        #self._appliance.info.get("name"),
                        network_info,
                    )
                    return
            except ClientConnectionResetError:
                _LOGGER.debug(
                    "Polling: connection reset while fetching WiFi info for %s (attempt %s/%s)",
                    self.entity_id,
                    #self._appliance.info.get("name"),
                    attempt,
                    max_retries,
                )
            except Exception as err:
                _LOGGER.error(
                    "Polling: failed to update WiFi signal for %s on attempt %s/%s: %s",
                    self.entity_id,
                    #self._appliance.info.get("name"),
                    attempt,
                    max_retries,
                    err,
                )

            if attempt < max_retries:
                await asyncio.sleep(delay)
                delay *= 2  # exponential backoff