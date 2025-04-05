"""Binary Sensor entities."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.const import EntityCategory

from .entity import HCEntity
from .entity_descriptions.descriptions_definitions import HCBinarySensorEntityDescription
from .helpers import create_entities

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.device_registry import DeviceInfo
    from homeassistant.helpers.entity_platform import AddEntitiesCallback
    from homeconnect_websocket import HomeAppliance

    from . import HCConfigEntry

PARALLEL_UPDATES = 0

CONNECTION_SENSOR_DESCRIPTIONS = HCBinarySensorEntityDescription(
    key="connection",
    device_class=BinarySensorDeviceClass.CONNECTIVITY,
    entity_category=EntityCategory.DIAGNOSTIC,
)


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001
    config_entry: HCConfigEntry,
    async_add_entites: AddEntitiesCallback,
) -> None:
    """Set up binary_sensor platform."""
    entities = create_entities({"binary_sensor": HCBinarySensor}, config_entry.runtime_data)
    entities.add(
        HCConnectionSensor(
            CONNECTION_SENSOR_DESCRIPTIONS,
            config_entry.runtime_data.appliance,
            config_entry.runtime_data.device_info,
        )
    )
    async_add_entites(entities)


class HCBinarySensor(HCEntity, BinarySensorEntity):
    """Binary Sensor Entity."""

    entity_description: HCBinarySensorEntityDescription

    @property
    def is_on(self) -> bool:
        if self.entity_description.value_on:
            if self._entity.value in self.entity_description.value_on:
                return True
            if self._entity.value in self.entity_description.value_off:
                return False
            return None
        return bool(self._entity.value)


class HCConnectionSensor(BinarySensorEntity):
    """Connection sensor Entity."""

    _attr_has_entity_name = True
    _attr_should_poll = True
    _attr_available = True
    entity_description: HCBinarySensorEntityDescription

    def __init__(
        self,
        entity_description: HCBinarySensorEntityDescription,
        appliance: HomeAppliance,
        device_info: DeviceInfo,
    ) -> None:
        super().__init__()
        self._appliance: HomeAppliance = appliance
        self.entity_description = entity_description
        self._attr_unique_id = f"{appliance.info['deviceID']}-{entity_description.key}"
        self._attr_device_info: DeviceInfo = device_info
        self._attr_translation_key = entity_description.key

    @property
    def is_on(self) -> bool:
        return self._appliance.session.connected
