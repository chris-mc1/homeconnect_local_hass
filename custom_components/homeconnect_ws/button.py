"""Button entities."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.button import ButtonEntity

from .entity import HCEntity
from .helpers import create_entities, error_decorator

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback
    from homeconnect_websocket.entities import ActiveProgram, Command

    from . import HCConfigEntry, HCData
    from .entity_descriptions.descriptions_definitions import HCButtonEntityDescription

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001
    config_entry: HCConfigEntry,
    async_add_entites: AddEntitiesCallback,
) -> None:
    """Set up button platform."""
    entities = create_entities(
        {"button": HCButton, "start_button": HCStartButton}, config_entry.runtime_data
    )
    async_add_entites(entities)


class HCButton(HCEntity, ButtonEntity):
    """Abort Button Entity."""

    _entity: Command
    entity_description: HCButtonEntityDescription

    async def async_press(self) -> None:
        await self._entity.set_value(True)


class HCStartButton(HCEntity, ButtonEntity):
    """Start Button Entity."""

    _entity: ActiveProgram
    entity_description: HCButtonEntityDescription

    def __init__(
        self,
        entity_description: HCButtonEntityDescription,
        runtime_data: HCData,
    ) -> None:
        super().__init__(entity_description, runtime_data)
        # Availability depends on the selected program, so update the state
        # when the selected program changes, not only the active program.
        selected_program = runtime_data.appliance._selected_program  # noqa: SLF001
        if selected_program is not None and selected_program not in self._entities:
            self._entities.append(selected_program)

    @property
    def available(self) -> bool:
        available = super().available
        available &= self._runtime_data.appliance.selected_program is not None
        return available

    @error_decorator
    async def async_press(self) -> None:
        await self._runtime_data.appliance.selected_program.start()
