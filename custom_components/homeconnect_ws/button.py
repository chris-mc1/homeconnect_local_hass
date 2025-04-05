"""Button entities."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.button import ButtonEntity

from .entity import HCEntity
from .helpers import create_entities

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback
    from homeconnect_websocket.entities import ActiveProgram, Command

    from . import HCConfigEntry
    from .entity_descriptions.descriptions_definitions import HCButtonEntityDescription

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001
    config_entry: HCConfigEntry,
    async_add_entites: AddEntitiesCallback,
) -> None:
    """Set up button platform."""
    entities = create_entities(
        {"abort_button": HCAbortButton, "start_button": HCStartButton}, config_entry.runtime_data
    )
    async_add_entites(entities)


class HCAbortButton(HCEntity, ButtonEntity):
    """Abort Button Entity."""

    _entity: Command
    entity_description: HCButtonEntityDescription

    async def async_press(self) -> None:
        await self._entity.set_value(True)


class HCStartButton(HCEntity, ButtonEntity):
    """Start Button Entity."""

    _entity: ActiveProgram
    entity_description: HCButtonEntityDescription

    async def async_press(self) -> None:
        await self._appliance.selected_program.start()
