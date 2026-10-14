"""Base Entity."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.helpers.entity import Entity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .helpers import entity_is_available

if TYPE_CHECKING:
    from homeassistant.helpers.device_registry import DeviceInfo
    from homeconnect_websocket.entities import Entity as HcEntity

    from . import HCData
    from .entity_descriptions.descriptions_definitions import (
        ExtraAttributeDict,
        HCEntityDescription,
    )

_LOGGER = logging.getLogger(__name__)


class HCEntity(CoordinatorEntity, Entity):
    """Base Entity."""

    entity_description: HCEntityDescription
    _attr_has_entity_name = True
    _entity: HcEntity | None = None
    _entities: list[HcEntity]
    _extra_attributes: list[ExtraAttributeDict]
    _has_callback: bool = False

    def __init__(
        self,
        entity_description: HCEntityDescription,
        runtime_data: HCData,
    ) -> None:
        super().__init__(runtime_data.coordinator)
        self._runtime_data = runtime_data
        self.entity_description = entity_description
        self._attr_unique_id = f"{runtime_data.appliance.info['deviceID']}-{entity_description.key}"
        self._attr_device_info: DeviceInfo = runtime_data.device_info
        if entity_description.translation_key is None:
            self._attr_translation_key = entity_description.key

        self._entities = []
        self._extra_attributes = []
        if entity_description.entity:
            self._entity = self._runtime_data.appliance.entities[entity_description.entity]
            self._entities.append(self._runtime_data.appliance.entities[entity_description.entity])
        if entity_description.entities:
            for entity_name in entity_description.entities:
                self._entities.append(self._runtime_data.appliance.entities[entity_name])
        for name, _ in entity_description.available_when or []:
            # Also update this entity when an entity that decides the availability changes.
            if name in self._runtime_data.appliance.entities and self._conditions_apply():
                self._entities.append(self._runtime_data.appliance.entities[name])
        if entity_description.extra_attributes:
            for extra_attribute in entity_description.extra_attributes:
                if extra_attribute["entity"] in self._runtime_data.appliance.entities:
                    self._extra_attributes.append(extra_attribute)

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        for entity in self._entities:
            entity.register_callback(self.callback)

    async def async_will_remove_from_hass(self) -> None:
        for entity in self._entities:
            entity.unregister_callback(self.callback)

    @property
    def available(self) -> bool:
        # FIX: session.connected fallback prevents unavailable during reconnects
        # and initial load before coordinator callback. 300s timeout still applies.
        conn = (
            self._runtime_data.coordinator.connected
            or self._runtime_data.appliance.session.connected
        )
        return (
            conn
            and entity_is_available(self._entity, self.entity_description.available_access)
            and self._conditions_met()
        )

    def _conditions_apply(self) -> bool:
        """Check if the available_when conditions apply to the brand of this appliance."""
        brands = getattr(self.entity_description, "available_when_brands", None)
        if brands is None:
            return True
        return self._runtime_data.appliance.info.get("brand", "").upper() in brands

    def _conditions_met(self) -> bool:
        """Check the available_when conditions, an unknown value (None) is not a failure."""
        if not self.entity_description.available_when or not self._conditions_apply():
            return True
        for name, allowed_values in self.entity_description.available_when:
            entity = self._runtime_data.appliance.entities.get(name)
            if (
                entity is not None
                and entity.value is not None
                and entity.value not in allowed_values
            ):
                return False
        return True

    @property
    def extra_state_attributes(self) -> dict:
        extra_state_attributes = {}
        for description in self._extra_attributes:
            entity = self._runtime_data.appliance.entities[description["entity"]]
            if "value_fn" in description:
                try:
                    extra_state_attributes[description["name"]] = description["value_fn"](entity)
                except Exception as exc:
                    _LOGGER.debug(
                        "Failed to set extra attribute %s for %s: %s",
                        description["name"],
                        self.entity_description.key,
                        str(exc),
                        exc_info=True,
                    )
                    extra_state_attributes[description["name"]] = None
            else:
                extra_state_attributes[description["name"]] = entity.value
        return extra_state_attributes

    async def callback(self, _: HcEntity) -> None:
        if not self._has_callback:
            self._has_callback = True
            self.async_write_ha_state()
            self._has_callback = False
