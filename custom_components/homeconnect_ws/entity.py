"""Base Entity."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.helpers.entity import Entity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeconnect_websocket.entities import Option

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
        if entity_description.extra_attributes:
            for extra_attribute in entity_description.extra_attributes:
                if extra_attribute["entity"] in self._runtime_data.appliance.entities:
                    self._extra_attributes.append(extra_attribute)
        if isinstance(self._entity, Option):
            # Availability of an option depends on the selected and the active program
            appliance = self._runtime_data.appliance
            for program_root in (appliance._selected_program, appliance._active_program):  # noqa: SLF001
                if program_root is not None and program_root not in self._entities:
                    self._entities.append(program_root)

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
            and self._used_by_program()
        )

    def _used_by_program(self) -> bool:
        """
        Return False if the active or selected program does not use this option.

        The device description lists the options of each program, e.g. an oven's hot air
        program has a setpoint temperature but no grill level, and a microwave program has
        neither. Without a program, or for a program without an option list, nothing changes.
        """
        if not isinstance(self._entity, Option):
            return True
        appliance = self._runtime_data.appliance
        try:
            program = appliance.active_program or appliance.selected_program
        except KeyError:
            # program uid not in the description
            return True
        if program is None or not program._options:  # noqa: SLF001
            return True
        return self._entity in program._options  # noqa: SLF001

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
