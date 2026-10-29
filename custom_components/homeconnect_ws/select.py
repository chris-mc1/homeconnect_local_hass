"""Select entities."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.select import SelectEntity
from homeconnect_websocket.entities import Execution

from .const import CONF_FILTER_UNSAVED_FAVORITES
from .entity import HCEntity
from .helpers import create_entities, error_decorator
from .program_names import favorite_settings, program_labels, selectable_program_labels

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback
    from homeconnect_websocket.entities import SelectedProgram

    from . import HCConfigEntry, HCData
    from .entity_descriptions.descriptions_definitions import HCSelectEntityDescription
PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001
    config_entry: HCConfigEntry,
    async_add_entites: AddEntitiesCallback,
) -> None:
    """Set up select platform."""
    entities = create_entities(
        {"select": HCSelect, "program": HCProgram},
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
        runtime_data: HCData,
    ) -> None:
        super().__init__(entity_description, runtime_data)

        self._rev_options = {}
        if entity_description.options:
            self._attr_options = entity_description.options
        elif self._entity.enum:
            self._attr_options = []
            if self.entity_description.has_state_translation:
                for value in self._entity.enum.values():
                    self._attr_options.append(str(value).lower())
            else:
                for value in self._entity.enum.values():
                    self._attr_options.append(str(value))

        if self.entity_description.has_state_translation and self._entity.enum:
            for value in self._entity.enum.values():
                self._rev_options[str(value).lower()] = value

    @property
    def current_option(self) -> str:
        if self.entity_description.has_state_translation:
            value = str(self._entity.value).lower()
            if value in self._attr_options:
                return value
        value = str(self._entity.value)
        if value in self._attr_options:
            return value
        return None

    @error_decorator
    async def async_select_option(self, option: str) -> None:
        if self._rev_options:
            option = self._rev_options[option]
        await self._entity.set_value(option)


class HCProgram(HCSelect):
    """Program select Entity."""

    _entity: SelectedProgram

    def __init__(
        self,
        entity_description: HCSelectEntityDescription,
        runtime_data: HCData,
    ) -> None:
        super().__init__(entity_description, runtime_data)
        self._programs = entity_description.mapping
        self._entities.extend(favorite_settings(runtime_data.appliance, self._programs))

    def _program_labels(self) -> dict[str, str]:
        if self.coordinator.config_entry.options.get(CONF_FILTER_UNSAVED_FAVORITES, False):
            return selectable_program_labels(self._runtime_data.appliance, self._programs)
        return program_labels(self._runtime_data.appliance, self._programs)

    @property
    def options(self) -> list[str] | None:
        return list(self._program_labels().values())

    @property
    def current_option(self) -> str | None:
        selected = self._runtime_data.appliance.selected_program
        if selected:
            return self._program_labels().get(selected.name)
        return None

    @error_decorator
    async def async_select_option(self, option: str) -> None:
        labels = self._program_labels()
        reverse = {value: key for key, value in labels.items()}
        selected_program = self._runtime_data.appliance.programs[reverse[option]]
        if selected_program.execution in (Execution.SELECT_ONLY, Execution.SELECT_AND_START):
            await selected_program.select()
        elif selected_program.execution == Execution.START_ONLY:
            await selected_program.start()
