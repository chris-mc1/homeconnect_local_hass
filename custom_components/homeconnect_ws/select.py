"""Select entities."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.select import SelectEntity
from homeassistant.exceptions import HomeAssistantError
from homeconnect_websocket.entities import Execution

from .const import DOMAIN
from .entity import HCEntity
from .helpers import create_entities, error_decorator, valid_program_options

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback
    from homeconnect_websocket.entities import SelectedProgram

    from . import HCConfigEntry, HCData
    from .entity_descriptions.descriptions_definitions import HCSelectEntityDescription
PARALLEL_UPDATES = 0

OPERATION_STATE = "BSH.Common.Status.OperationState"
# Operation states in which a program is running (or waiting to run).
RUNNING_STATES = {"Run", "Pause", "DelayedStart", "ActionRequired"}


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
        self._rev_programs = {value: key for key, value in self._programs.items()}

    @property
    def options(self) -> list[str] | None:
        return list(self._programs.values())

    @property
    def current_option(self) -> list[str] | None:
        appliance = self._runtime_data.appliance
        program = appliance.selected_program
        brands = self.entity_description.prefer_active_program_for_brands
        if (
            brands
            and appliance.info.get("brand", "").upper() in brands
            and appliance.active_program
        ):
            program = appliance.active_program
        if program:
            if program.name in self._programs:
                return self._programs[program.name]
            return program.name
        return None

    def _check_no_program_running(self) -> None:
        """Raise an error when the appliance would ignore the selection of a program."""
        state = self._runtime_data.appliance.entities.get(OPERATION_STATE)
        brands = self.entity_description.block_change_while_running_for_brands
        brand = self._runtime_data.appliance.info.get("brand", "").upper()
        if brands and brand in brands and state is not None and state.value in RUNNING_STATES:
            raise HomeAssistantError(translation_domain=DOMAIN, translation_key="program_running")

    @error_decorator
    async def async_select_option(self, option: str) -> None:
        selected_program = self._runtime_data.appliance.programs[self._rev_programs[option]]
        # The appliance ignores the selected program until the running program has ended.
        self._check_no_program_running()
        # Only send the options the appliance accepts, the shadow values of options that are not
        # available (or have no value) are rejected with "400 BadRequest".
        options = valid_program_options(
            selected_program, self._runtime_data.appliance.info.get("brand", "")
        )
        if selected_program.execution in (Execution.SELECT_ONLY, Execution.SELECT_AND_START):
            await selected_program.select(options=options, override_options=True)
        elif selected_program.execution == Execution.START_ONLY:
            await selected_program.start(options=options, override_options=True)
