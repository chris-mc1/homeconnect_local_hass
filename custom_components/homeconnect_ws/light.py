"""Light entities."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ColorMode,
    LightEntity,
)
from homeassistant.util.color import brightness_to_value, value_to_brightness

from .entity import HCEntity
from .helpers import create_entities, entity_is_available

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.device_registry import DeviceInfo
    from homeassistant.helpers.entity_platform import AddEntitiesCallback
    from homeconnect_websocket import HomeAppliance
    from homeconnect_websocket.entities import Entity as HcEntity

    from . import HCConfigEntry
    from .entity_descriptions.descriptions_definitions import HCLightEntityDescription

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001
    config_entry: HCConfigEntry,
    async_add_entites: AddEntitiesCallback,
) -> None:
    """Set up light platform."""
    entities = create_entities({"light": HCLight}, config_entry.runtime_data)
    async_add_entites(entities)


class HCLight(HCEntity, LightEntity):
    """Light Entity."""

    entity_description: HCLightEntityDescription
    _brightness_entity: HcEntity | None = None
    _brightness_scale: tuple[float, float] | None = None

    def __init__(
        self,
        entity_description: HCLightEntityDescription,
        appliance: HomeAppliance,
        device_info: DeviceInfo,
    ) -> None:
        super().__init__(entity_description, appliance, device_info)
        if entity_description.brightness_entity is not None:
            self._brightness_entity = self._appliance.entities[entity_description.brightness_entity]
            self._entities.append(self._brightness_entity)

            self._attr_supported_color_modes = {ColorMode.BRIGHTNESS}
            self._attr_color_mode = ColorMode.BRIGHTNESS
        else:
            self._attr_supported_color_modes = {ColorMode.ONOFF}
            self._attr_color_mode = ColorMode.ONOFF

    @property
    def available(self) -> set[ColorMode] | None:
        available = super().available
        if self._brightness_entity:
            available &= entity_is_available(
                self._brightness_entity, self.entity_description.available_access
            )
        return available

    @property
    def is_on(self) -> bool | None:
        return bool(self._entity.value)

    @property
    def brightness(self) -> int | None:
        return value_to_brightness((1, 100), self._brightness_entity.value)

    async def async_turn_on(self, **kwargs: Any) -> None:
        if ATTR_BRIGHTNESS in kwargs:
            value_in_range = int(
                max(
                    brightness_to_value((1, 100), kwargs[ATTR_BRIGHTNESS]),
                    self._brightness_entity.min,
                )
            )
            await self._brightness_entity.set_value(value_in_range)
        await self._entity.set_value(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._entity.set_value(False)
