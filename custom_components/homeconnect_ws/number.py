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
        for name, _ in entity_description.available_when or []:
            # Also update this entity when an entity that decides the availability changes.
            condition_entity = runtime_data.appliance.entities.get(name)
            if condition_entity is not None:
                self._entities.append(condition_entity)

    def _available_when_applies(self) -> bool:
        """Check if the available_when condition applies to the brand of this appliance."""
        brands = self.entity_description.available_when_brands
        if brands is None:
            return True
        return self._runtime_data.appliance.info.get("brand", "").upper() in brands

    @property
    def available(self) -> bool:
        if not super().available:
            return False
        if self.entity_description.available_when and self._available_when_applies():
            for name, allowed_values in self.entity_description.available_when:
                condition_entity = self._runtime_data.appliance.entities.get(name)
                # An unknown value (None) does not make the entity unavailable.
                if (
                    condition_entity is not None
                    and condition_entity.value is not None
                    and condition_entity.value not in allowed_values
                ):
                    return False
        return True

    @property
    def native_value(self) -> int | float | None:
        if self.entity_description.use_raw_value:
            # The enumeration label (for example "60dC") is not a number, use the raw value.
            # Raw values outside of the range of this entity (for example the Fahrenheit
            # entries of the enumeration) are unknown here.
            value = self._entity.value_raw
            if value is None or value > self.native_max_value:
                return None
            return value
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
        if self.entity_description.use_raw_value:
            raw_value = int(value)
            limit = self.entity_description.raw_value_off_below
            if limit is not None and raw_value < limit:
                # Not in the enumeration, 0 is the "Off" entry.
                raw_value = 0
            await self._entity.set_value_raw(raw_value)
            return
        await self._entity.set_value(int(value))
