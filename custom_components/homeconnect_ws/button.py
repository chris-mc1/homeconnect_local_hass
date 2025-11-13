"""Button entities."""

from __future__ import annotations

from typing import TYPE_CHECKING, Set

from homeassistant.components.button import ButtonEntity
from homeconnect_websocket.entities import Execution

from .entity import HCEntity
from .helpers import create_entities
from .entity_descriptions.descriptions_definitions import HCButtonEntityDescription

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback
    from homeconnect_websocket.entities import ActiveProgram, Command

    from . import HCConfigEntry
    from .entity_descriptions.descriptions_definitions import HCButtonEntityDescription

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: HCConfigEntry,
    async_add_entites: AddEntitiesCallback,
) -> None:
    entities: Set[HCEntity] = create_entities(
        {"button": HCButton, "start_button": HCStartButton},
        config_entry.runtime_data,
    )

    has_start_button_already = any(isinstance(e, HCStartButton) for e in entities)
    aed = config_entry.runtime_data.available_entity_descriptions
    has_program_entities = ("program" in aed and aed["program"]) or ("select" in aed and aed["select"])

    if not has_start_button_already and has_program_entities:
        start_desc = HCButtonEntityDescription(
            key="start",
            name="Start",
            icon="mdi:play",
        )
        entities.add(
            HCStartButton(
                entity_description=start_desc,
                appliance=config_entry.runtime_data.appliance,
                device_info=config_entry.runtime_data.device_info,
            )
        )

    async_add_entites(list(entities))


class HCButton(HCEntity, ButtonEntity):
    _entity: Command
    entity_description: HCButtonEntityDescription

    async def async_press(self) -> None:
        await self._entity.set_value(True)


class HCStartButton(HCEntity, ButtonEntity):
    _entity: ActiveProgram
    entity_description: HCButtonEntityDescription

    @property
    def available(self) -> bool:
        if not super().available:
            return False
        return self._appliance.selected_program is not None

    async def async_press(self) -> None:
        await self._appliance.selected_program.start()
