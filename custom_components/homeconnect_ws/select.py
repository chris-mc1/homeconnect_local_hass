"""Select entities."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.select import SelectEntity
from homeconnect_websocket.entities import Access, Execution

from .entity import HCEntity
from .helpers import create_entities, entity_is_available, error_decorator

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback
    from homeconnect_websocket.entities import ActiveProgram, Program, SelectedProgram

    from . import HCConfigEntry, HCData
    from .entity_descriptions.descriptions_definitions import HCSelectEntityDescription
PARALLEL_UPDATES = 0

_ACTIVE_PROGRAM_ACCESS = (Access.READ_WRITE, Access.WRITE_ONLY)
_SELECTED_PROGRAM_SUFFIX = ".SelectedProgram"


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
    _active_program_entity: ActiveProgram | None = None

    def __init__(
        self,
        entity_description: HCSelectEntityDescription,
        runtime_data: HCData,
    ) -> None:
        super().__init__(entity_description, runtime_data)
        self._programs = entity_description.mapping
        self._rev_programs = {value: key for key, value in self._programs.items()}
        if (
            entity_description.entity
            and entity_description.entity.endswith(_SELECTED_PROGRAM_SUFFIX)
        ):
            active_program_entity = (
                f"{entity_description.entity.removesuffix(_SELECTED_PROGRAM_SUFFIX)}"
                ".ActiveProgram"
            )
            self._active_program_entity = runtime_data.appliance.entities.get(
                active_program_entity
            )
            if self._active_program_entity:
                self._entities.append(self._active_program_entity)

    @property
    def options(self) -> list[str] | None:
        return list(self._programs.values())

    @property
    def available(self) -> bool:
        if super().available:
            return True
        conn = (
            self._runtime_data.coordinator.connected
            or self._runtime_data.appliance.session.connected
        )
        if not conn or self._active_program_entity is None:
            return False
        return entity_is_available(
            self._active_program_entity, _ACTIVE_PROGRAM_ACCESS
        ) and self._programs_are_start_only()

    def _programs_are_start_only(self) -> bool:
        programs: list[Program | None] = [
            self._runtime_data.appliance.programs.get(program)
            for program in self._programs
        ]
        return bool(programs) and all(
            program is not None
            and program.available is not False
            and program.execution == Execution.START_ONLY
            for program in programs
        )

    @property
    def current_option(self) -> str | None:
        current_program = self._runtime_data.appliance.selected_program
        if current_program is None and self._active_program_entity is not None:
            current_program = self._runtime_data.appliance.active_program

        if current_program:
            if current_program.name in self._programs:
                return self._programs[current_program.name]
            return current_program.name
        return None

    @error_decorator
    async def async_select_option(self, option: str) -> None:
        selected_program = self._runtime_data.appliance.programs[self._rev_programs[option]]
        if selected_program.execution in (Execution.SELECT_ONLY, Execution.SELECT_AND_START):
            await selected_program.select()
        elif selected_program.execution == Execution.START_ONLY:
            await selected_program.start()
