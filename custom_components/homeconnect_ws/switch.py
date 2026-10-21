"""Switch entities."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import STATE_OFF, STATE_ON, EntityCategory
from homeassistant.helpers.restore_state import RestoreEntity

from .entity import HCEntity
from .entity_descriptions.descriptions_definitions import HCSwitchEntityDescription
from .helpers import create_entities, error_decorator, has_dish_programs

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from . import HCConfigEntry, HCData

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001
    config_entry: HCConfigEntry,
    async_add_entites: AddEntitiesCallback,
) -> None:
    """Set up switch platform."""
    entities = create_entities({"switch": HCSwitch}, config_entry.runtime_data)
    # Only an appliance with automatic dishes (an oven) has something to show or hide.
    if has_dish_programs(config_entry.runtime_data.appliance):
        entities.add(HCShowDishProgramsSwitch(config_entry.runtime_data))
    async_add_entites(entities)


class HCSwitch(HCEntity, SwitchEntity):
    """Switch Entity."""

    entity_description: HCSwitchEntityDescription

    def __init__(
        self,
        entity_description: HCSwitchEntityDescription,
        runtime_data: HCData,
    ) -> None:
        super().__init__(entity_description, runtime_data)
        self._value_mapping: tuple[str, str] = entity_description.value_mapping

    @property
    def is_on(self) -> bool:
        if self._value_mapping:
            if self._value_mapping[0] == self._entity.value:
                return True
            if self._value_mapping[1] == self._entity.value:
                return False
            return None
        return bool(self._entity.value)

    @error_decorator
    async def async_turn_on(self, **kwargs: Any) -> None:
        if self._value_mapping:
            await self._entity.set_value(self._value_mapping[0])
        else:
            await self._entity.set_value(True)

    @error_decorator
    async def async_turn_off(self, **kwargs: Any) -> None:
        if self._value_mapping:
            await self._entity.set_value(self._value_mapping[1])
        else:
            await self._entity.set_value(False)


class HCShowDishProgramsSwitch(HCEntity, SwitchEntity, RestoreEntity):
    """
    Switch to show or hide the programs for automatic dishes in the program select.

    An oven has many automatic dishes (58 on the Gaggenau BO470112, 96 on the BS474112). They are
    listed in the program select, so it is long. This is a setting of the integration for one
    appliance, it is not an entity of the appliance: the value is kept in the runtime data (read
    by the program select) and restored by Home Assistant after a restart.
    """

    def __init__(self, runtime_data: HCData) -> None:
        super().__init__(
            HCSwitchEntityDescription(
                key="switch_show_dish_programs",
                entity_category=EntityCategory.CONFIG,
            ),
            runtime_data,
        )

    @property
    def is_on(self) -> bool:
        return self._runtime_data.show_dish_programs

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        # Restore the last value, the default (on) shows all programs as before.
        if (last_state := await self.async_get_last_state()) is not None and (
            last_state.state in (STATE_ON, STATE_OFF)
        ):
            self._runtime_data.show_dish_programs = last_state.state == STATE_ON
            self._update_program_select()

    def _set(self, *, show: bool) -> None:
        """Save the value and let the program select update its list."""
        self._runtime_data.show_dish_programs = show
        self.async_write_ha_state()
        self._update_program_select()

    def _update_program_select(self) -> None:
        """Update all entities of this appliance, among them the program select."""
        self._runtime_data.coordinator.async_update_listeners()

    async def async_turn_on(self, **kwargs: Any) -> None:
        self._set(show=True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        self._set(show=False)
