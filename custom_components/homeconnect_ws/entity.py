"""BAse Entity."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.helpers.entity import Entity

if TYPE_CHECKING:
    from homeassistant.helpers.device_registry import DeviceInfo
    from homeconnect_websocket import HomeAppliance
    from homeconnect_websocket.entities import Entity as HcEntity

    from .entity_descriptions.descriptions_definitions import (
        ExtraAttributeDict,
        HCEntityDescription,
    )

_LOGGER = logging.getLogger(__name__)


class HCEntity(Entity):
    """Base Entity."""

    entity_description: HCEntityDescription
    _attr_has_entity_name = True
    _entity: HcEntity | None = None
    _entities: list[HcEntity]
    _extra_attributes: list[ExtraAttributeDict]

    def __init__(
        self,
        entity_description: HCEntityDescription,
        appliance: HomeAppliance,
        device_info: DeviceInfo,
    ) -> None:
        super().__init__()
        self._appliance: HomeAppliance = appliance
        self.entity_description = entity_description
        self._attr_unique_id = f"{appliance.info['deviceID']}-{entity_description.key}"
        self._attr_device_info: DeviceInfo = device_info
        self._attr_translation_key = entity_description.key

        self._entities = []
        self._extra_attributes = []
        if entity_description.entity:
            self._entity = self._appliance.entities[entity_description.entity]
            self._entities.append(self._appliance.entities[entity_description.entity])
        if entity_description.entities:
            for entity_name in entity_description.entities:
                self._entities.append(self._appliance.entities[entity_name])
        if entity_description.extra_attributes:
            for extra_attribute in entity_description.extra_attributes:
                if extra_attribute["entity"] in self._appliance.entities:
                    self._extra_attributes.append(extra_attribute)

    async def async_added_to_hass(self) -> None:
        for entity in self._entities:
            entity.register_callback(self.callback)

    async def async_will_remove_from_hass(self) -> None:
        for entity in self._entities:
            entity.unregister_callback(self.callback)

    @property
    def available(self) -> bool:
        available = self._appliance.session.connected

        if hasattr(self._entity, "available"):
            available &= self._entity.available

        if hasattr(self._entity, "access"):
            available &= self._entity.access in self.entity_description.available_access

        return available

    @property
    def extra_state_attributes(self) -> dict:
        extra_state_attributes = {}
        for description in self._extra_attributes:
            entity = self._appliance.entities[description["entity"]]
            if "value_fn" in description:
                extra_state_attributes[description["name"]] = description["value_fn"](entity)
            else:
                extra_state_attributes[description["name"]] = entity.value
        return extra_state_attributes

    async def callback(self, _: HcEntity) -> None:
        self.async_write_ha_state()
