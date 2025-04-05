"""Number entities."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.number import NumberEntity

from .entity import HCEntity
from .helpers import create_entities

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.device_registry import DeviceInfo
    from homeassistant.helpers.entity_platform import AddEntitiesCallback
    from homeconnect_websocket import HomeAppliance

    from . import HCConfigEntry
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
        appliance: HomeAppliance,
        device_info: DeviceInfo,
    ) -> None:
        super().__init__(entity_description, appliance, device_info)
        if hasattr(self._entity, "min") and self._entity.min is not None:
            self._attr_native_min_value = self._entity.min
        if hasattr(self._entity, "max") and self._entity.max is not None:
            self._attr_native_max_value = self._entity.max
        if hasattr(self._entity, "step") and self._entity.step is not None:
            self._attr_native_step = self._entity.step

    @property
    def native_value(self) -> int | float:
        return self._entity.value

    async def async_set_native_value(self, value: float) -> None:
        await self._entity.set_value(int(value))
