"""Select entities."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.select import SelectEntity

from .entity import HCEntity
from .helpers import create_entities

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.device_registry import DeviceInfo
    from homeassistant.helpers.entity_platform import AddEntitiesCallback
    from homeconnect_websocket import HomeAppliance
    from homeconnect_websocket.entities import Option as Program_Option
    from homeconnect_websocket.entities import SelectedProgram

    from . import HCConfigEntry
    from .entity_descriptions.descriptions_definitions import HCSelectEntityDescription

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001
    config_entry: HCConfigEntry,
    async_add_entites: AddEntitiesCallback,
) -> None:
    """Set up select platform."""
    entities = create_entities(
        {"select": HCSelect, "program": HCProgram, "start_in": HCStartIn},
        config_entry.runtime_data,
    )
    async_add_entites(entities)


class HCSelect(HCEntity, SelectEntity):
    """Select Entity."""

    entity_description: HCSelectEntityDescription
    _rev_options: dict[str, str]

    def __init__(
        self,
        entity_description: HCSelectEntityDescription,
        appliance: HomeAppliance,
        device_info: DeviceInfo,
    ) -> None:
        super().__init__(entity_description, appliance, device_info)
        if self._entity.enum:
            self._attr_options = []
            if self.entity_description.has_state_translation:
                self._rev_options = {}
                for value in self._entity.enum.values():
                    self._attr_options.append(str(value).lower())
                    self._rev_options[str(value).lower()] = value
            else:
                for value in self._entity.enum.values():
                    self._attr_options.append(str(value))

    @property
    def current_option(self) -> str:
        if self.entity_description.has_state_translation:
            return str(self._entity.value).lower()
        return str(self._entity.value)

    async def async_select_option(self, option: str) -> None:
        if self.entity_description.has_state_translation:
            option = self._rev_options[option]
        await self._entity.set_value(option)


class HCProgram(HCSelect):
    """Program select Entity."""

    _entity: SelectedProgram

    def __init__(
        self,
        entity_description: HCSelectEntityDescription,
        appliance: HomeAppliance,
        device_info: DeviceInfo,
    ) -> None:
        super().__init__(entity_description, appliance, device_info)
        self._programs = {}
        for name in self._appliance.programs:
            self._programs[name.split(".")[-1].lower()] = name

    @property
    def options(self) -> list[str] | None:
        return list(self._programs.keys())

    @property
    def current_option(self) -> list[str] | None:
        return (
            self._appliance.selected_program.name.split(".")[-1].lower()
            if self._appliance.selected_program
            else None
        )

    async def async_select_option(self, option: str) -> None:
        await self._appliance.programs[self._programs[option]].select()


class HCStartIn(HCSelect):
    """Start_in select Entity."""

    _entity: Program_Option

    def __init__(
        self,
        entity_description: HCSelectEntityDescription,
        appliance: HomeAppliance,
        device_info: DeviceInfo,
    ) -> None:
        super().__init__(entity_description, appliance, device_info)
        self._options = []
        for t in range(int(self._entity.min), int(self._entity.max), 900):
            self._options.append(f"{int(t / 3600)}:{int((t % 3600) / 60):02}")

    @property
    def options(self) -> list[str] | None:
        return self._options

    @property
    def current_option(self) -> str:
        t = self._entity.value
        return f"{int(t / 3600)}:{int((t % 3600) / 60):02}"

    async def async_select_option(self, option: str) -> None:
        parts = option.split(":")
        delay = int(parts[0]) * 3600 + int(parts[1]) * 60
        await self._entity.set_value(delay)
