"""Number entities."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.number import DEFAULT_MAX_VALUE, DEFAULT_MIN_VALUE, NumberEntity

from .entity import HCEntity
from .helpers import create_entities, error_decorator

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from . import HCConfigEntry, HCData
    from .entity_descriptions.descriptions_definitions import HCNumberEntityDescription

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001
    config_entry: HCConfigEntry,
    async_add_entites: AddEntitiesCallback,
) -> None:
    """Set up number platform."""
    entities = create_entities({"number": HCNumber}, config_entry.runtime_data)
    async_add_entites(entities)


class HCNumber(HCEntity, NumberEntity):
    """Number Entity."""

    entity_description: HCNumberEntityDescription

    def __init__(
        self,
        entity_description: HCNumberEntityDescription,
        runtime_data: HCData,
    ) -> None:
        super().__init__(entity_description, runtime_data)
        self._entity._type = int  # noqa: SLF001 Force integer type

    @property
    def native_value(self) -> int | float:
        return self._entity.value

    @property
    def native_min_value(self) -> float:
        if hasattr(self._entity, "min") and self._entity.min is not None:
            return self._entity.min
        if self.entity_description.native_min_value is not None:
            return self.entity_description.native_min_value
        return DEFAULT_MIN_VALUE

    @property
    def native_max_value(self) -> float:
        if hasattr(self._entity, "max") and self._entity.max is not None:
            return self._entity.max
        if self.entity_description.native_max_value is not None:
            return self.entity_description.native_max_value
        return DEFAULT_MAX_VALUE

    @property
    def native_step(self) -> float | None:
        if hasattr(self._entity, "step") and self._entity.step is not None:
            return self._entity.step
        return None

    @error_decorator
    async def async_set_native_value(self, value: float) -> None:
        await self._entity.set_value(int(value))
