"""Switch entities."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.switch import SwitchEntity

from .entity import HCEntity
from .helpers import create_entities

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity import DeviceInfo
    from homeassistant.helpers.entity_platform import AddEntitiesCallback
    from homeconnect_websocket import HomeAppliance

    from . import HCConfigEntry
    from .entity_descriptions.descriptions_definitions import HCSwitchEntityDescription

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001
    config_entry: HCConfigEntry,
    async_add_entites: AddEntitiesCallback,
) -> None:
    """Set up switch platform."""
    entities = create_entities(
        {"switch": HCSwitch, "power_switch": HCPowerSwitch}, config_entry.runtime_data
    )
    async_add_entites(entities)


class HCSwitch(HCEntity, SwitchEntity):
    """Switch Entity."""

    entity_description: HCSwitchEntityDescription

    def __init__(
        self,
        entity_description: HCSwitchEntityDescription,
        appliance: HomeAppliance,
        device_info: DeviceInfo,
    ) -> None:
        super().__init__(entity_description, appliance, device_info)
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

    async def async_turn_on(self, **kwargs: Any) -> None:
        if self._value_mapping:
            await self._entity.set_value(self._value_mapping[0])
        else:
            await self._entity.set_value(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        if self._value_mapping:
            await self._entity.set_value(self._value_mapping[1])
        else:
            await self._entity.set_value(False)


STANDBY_ENUM_VALUE = 3


class HCPowerSwitch(HCSwitch):
    """Power switch Entity."""

    entity_description: HCSwitchEntityDescription

    def __init__(
        self,
        entity_description: HCSwitchEntityDescription,
        appliance: HomeAppliance,
        device_info: DeviceInfo,
    ) -> None:
        super().__init__(entity_description, appliance, device_info)
        if STANDBY_ENUM_VALUE in self._entity.enum:
            self._value_mapping = ("On", "Standby")
        else:
            self._value_mapping = ("On", "Off")
