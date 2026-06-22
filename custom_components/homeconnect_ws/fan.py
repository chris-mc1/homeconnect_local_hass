"""Fan entities."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Any, NamedTuple

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.exceptions import ServiceValidationError
from homeassistant.util.percentage import percentage_to_ranged_value, ranged_value_to_percentage
from homeconnect_websocket.entities import Access

from .const import DOMAIN
from .entity import HCEntity
from .helpers import create_entities, entity_is_available, error_decorator

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback
    from homeconnect_websocket.entities import Entity as HcEntity, Program

    from . import HCConfigEntry, HCData
    from .entity_descriptions.descriptions_definitions import HCFanEntityDescription

PARALLEL_UPDATES = 0


class SpeedMapping(NamedTuple):
    """Mapping of entity name / value and speed."""

    entity_name: str
    entity_value: int
    speed: int


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001
    config_entry: HCConfigEntry,
    async_add_entites: AddEntitiesCallback,
) -> None:
    """Set up fan platform."""
    entities = create_entities({"fan": HCFan}, config_entry.runtime_data)
    async_add_entites(entities)


class HCFan(HCEntity, FanEntity):
    """Fan Entity."""

    entity_description: HCFanEntityDescription
    _speed_entities: dict[str, HcEntity] | None = None
    _speed_range: range = None
    _speed_mapping: list[SpeedMapping]

    def __init__(
        self,
        entity_description: HCFanEntityDescription,
        runtime_data: HCData,
    ) -> None:
        super().__init__(entity_description, runtime_data)
        self._attr_supported_features = (
            FanEntityFeature.SET_SPEED | FanEntityFeature.TURN_OFF | FanEntityFeature.TURN_ON
        )
        self._speed_mapping = []
        self._speed_entities = {}
        self._attr_speed_count = 0
        for entity_name in entity_description.entities:
            entity = self._runtime_data.appliance.entities[entity_name]
            self._speed_entities[entity_name] = entity
            for option in entity.enum:
                if option != 0:
                    self._attr_speed_count += 1
                    self._speed_mapping.append(
                        SpeedMapping(
                            entity_name=entity_name,
                            entity_value=option,
                            speed=self._attr_speed_count,
                        )
                    )

        self._speed_range = (1, self._attr_speed_count)

    @property
    def available(self) -> bool:
        available = super().available
        for entity in self._speed_entities.values():
            available &= entity_is_available(entity, self.entity_description.available_access)
        return available

    @property
    def is_on(self) -> bool:
        return self._runtime_data.appliance.active_program is not None

    @property
    def percentage(self) -> int | None:
        if not self.is_on:
            return 0
        for speed in self._speed_mapping:
            if self._speed_entities[speed.entity_name].value_raw == speed.entity_value:
                return ranged_value_to_percentage(self._speed_range, speed.speed)
        return 0

    def _venting_program(self) -> Program:
        default_program = self.entity_description.default_program
        if default_program is None:
            msg = "Hood fan is missing default_program"
            raise ServiceValidationError(msg)
        if self._runtime_data.appliance.active_program is not None:
            return self._runtime_data.appliance.active_program
        return self._runtime_data.appliance.programs[default_program]

    def _speed_options(
        self,
        program: Program,
        *,
        entity_name: str | None = None,
        value: int = 0,
    ) -> dict[int, int]:
        """Build writable fan option uids for the given program."""
        options: dict[int, int] = {}
        for option in program._options:
            if option.name not in self._speed_entities:
                continue
            if option.access != Access.READ_WRITE:
                continue
            if entity_name is None or option.name == entity_name:
                options[option.uid] = value
            else:
                options[option.uid] = 0
        return options

    @error_decorator
    async def async_set_percentage(self, percentage: int) -> None:
        new_speed = math.ceil(percentage_to_ranged_value(self._speed_range, percentage))
        if new_speed == 0:
            await self.async_turn_off()
            return

        new_speed_entity: str | None = None
        new_speed_value: int | None = None
        for speed in self._speed_mapping:
            if speed.speed == new_speed:
                new_speed_entity = speed.entity_name
                new_speed_value = speed.entity_value

        if new_speed_entity is None:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="speed_invalid",
                translation_placeholders={"percentage": str(percentage)},
            )

        program = self._venting_program()
        options = self._speed_options(
            program,
            entity_name=new_speed_entity,
            value=new_speed_value,
        )
        if not options:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="speed_invalid",
                translation_placeholders={"percentage": str(percentage)},
            )

        await program.start(options)

    @error_decorator
    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **kwargs: Any,
    ) -> None:
        if percentage is None:
            await self._venting_program().start(options={}, override_options=True)
        else:
            await self.async_set_percentage(int(percentage))

    @error_decorator
    async def async_turn_off(self, **kwargs: Any) -> None:
        appliance = self._runtime_data.appliance
        if appliance.active_program is None:
            return

        options = self._speed_options(appliance.active_program, value=0)
        if not options:
            return

        await appliance.active_program.start(options)
