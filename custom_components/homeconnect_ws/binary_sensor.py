"""Binary Sensor entities."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.const import EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .entity import HCEntity
from .entity_descriptions.descriptions_definitions import HCBinarySensorEntityDescription
from .helpers import EventStaleTracker, create_entities, leaves_alarm_event_on

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.device_registry import DeviceInfo
    from homeassistant.helpers.entity_platform import AddEntitiesCallback
    from homeconnect_websocket import HomeAppliance
    from homeconnect_websocket.entities import Entity as HcEntity

    from . import HCConfigEntry, HCData

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
    entities.add(HCConnectionSensor(CONNECTION_SENSOR_DESCRIPTIONS, config_entry.runtime_data))
    async_add_entites(entities)


class HCBinarySensor(HCEntity, BinarySensorEntity):
    """Binary Sensor Entity."""

    entity_description: HCBinarySensorEntityDescription

    def __init__(
        self,
        entity_description: HCBinarySensorEntityDescription,
        runtime_data: HCData,
    ) -> None:
        super().__init__(entity_description, runtime_data)
        self._alarm_clock: HcEntity | None = None
        self._tracker: EventStaleTracker | None = None
        name = entity_description.alarm_clock_entity
        # A hob sets the alarm clock to 0 in the same message as the event and only keeps the event
        # on until the alarm is confirmed: the sensor would never be on if the alarm clock decided,
        # so for a hob the event alone decides.
        if (
            name
            and name in runtime_data.appliance.entities
            and leaves_alarm_event_on(runtime_data.appliance)
        ):
            self._alarm_clock = runtime_data.appliance.entities[name]
            self._tracker = EventStaleTracker(
                self._entity, self._alarm_clock, entity_description.value_on or set()
            )
            # Also update the state when this entity changes
            self._entities.append(self._alarm_clock)

    async def callback(self, entity: HcEntity) -> None:
        if self._tracker is not None:
            self._tracker.update(entity)
        await super().callback(entity)

    @property
    def is_on(self) -> bool:
        if self._alarm_clock is not None and (self._alarm_clock.value == 0 or self._tracker.stale):
            return False
        if self.entity_description.value_on:
            if self._entity.value in self.entity_description.value_on:
                return True
            if self._entity.value in self.entity_description.value_off:
                return False
            return None
        return bool(self._entity.value)


class HCConnectionSensor(CoordinatorEntity, BinarySensorEntity):
    """Connection sensor Entity."""

    _attr_has_entity_name = True
    _attr_should_poll = True
    _attr_available = True
    entity_description: HCBinarySensorEntityDescription

    def __init__(
        self, entity_description: HCBinarySensorEntityDescription, runtime_data: HCData
    ) -> None:
        super().__init__(runtime_data.coordinator)
        self._appliance: HomeAppliance = runtime_data.appliance
        self.entity_description = entity_description
        self._attr_unique_id = f"{runtime_data.appliance.info['deviceID']}-{entity_description.key}"
        self._attr_device_info: DeviceInfo = runtime_data.device_info
        self._attr_translation_key = entity_description.key

    @property
    def is_on(self) -> bool:
        return self._appliance.session.connected
