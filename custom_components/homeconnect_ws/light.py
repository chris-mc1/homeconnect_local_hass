"""Light entities."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP_KELVIN,
    ColorMode,
    LightEntity,
)
from homeassistant.components.light.const import DEFAULT_MAX_KELVIN, DEFAULT_MIN_KELVIN
from homeassistant.util.color import brightness_to_value, value_to_brightness
from homeassistant.util.scaling import scale_ranged_value_to_int_range
from homeconnect_websocket.message import Action
from homeconnect_websocket.message import Message as HC_Message

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
    _color_temperature_entity: HcEntity | None = None

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

        if entity_description.color_temperature_entity is not None:
            self._color_temperature_entity = self._appliance.entities[
                entity_description.color_temperature_entity
            ]
            self._entities.append(self._color_temperature_entity)

        if self._color_temperature_entity and self._brightness_entity:
            self._attr_supported_color_modes = {ColorMode.COLOR_TEMP}
            self._attr_color_mode = ColorMode.COLOR_TEMP
            self._attr_max_color_temp_kelvin = DEFAULT_MAX_KELVIN
            self._attr_min_color_temp_kelvin = DEFAULT_MIN_KELVIN
        elif self._brightness_entity:
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
        if self._color_temperature_entity:
            available &= entity_is_available(
                self._color_temperature_entity, self.entity_description.available_access
            )
        return available

    @property
    def is_on(self) -> bool | None:
        return bool(self._entity.value)

    @property
    def brightness(self) -> int | None:
        return value_to_brightness((1, 100), self._brightness_entity.value)

    @property
    def color_temp_kelvin(self) -> int | None:
        return scale_ranged_value_to_int_range(
            (1, 100),
            (DEFAULT_MIN_KELVIN + 1, DEFAULT_MAX_KELVIN),
            self._color_temperature_entity.value,
        )

    async def async_turn_on(self, **kwargs: Any) -> None:
        message = HC_Message(
            resource="/ro/values",
            action=Action.POST,
            data=[],
        )
        if ATTR_BRIGHTNESS in kwargs:
            value_in_range = int(
                max(
                    brightness_to_value((1, 100), kwargs[ATTR_BRIGHTNESS]),
                    self._brightness_entity.min,
                )
            )
            message.data.append({"uid": self._brightness_entity.uid, "value": value_in_range})
        if ATTR_COLOR_TEMP_KELVIN in kwargs:
            value_in_range = int(
                scale_ranged_value_to_int_range(
                    (DEFAULT_MIN_KELVIN + 1, DEFAULT_MAX_KELVIN),
                    (1, 100),
                    kwargs[ATTR_COLOR_TEMP_KELVIN],
                )
            )
            message.data.append(
                {"uid": self._color_temperature_entity.uid, "value": value_in_range}
            )
        if self._entity.value is not True:
            message.data.append({"uid": self._entity.uid, "value": True})
        await self._appliance.session.send_sync(message)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._entity.set_value(False)
