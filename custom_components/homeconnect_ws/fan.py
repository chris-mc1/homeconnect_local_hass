"""Fan entities."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Any, NamedTuple

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.exceptions import ServiceValidationError
from homeassistant.util.percentage import percentage_to_ranged_value, ranged_value_to_percentage
from homeconnect_websocket.entities import Execution
from homeconnect_websocket.message import Action, Message

from .entity import HCEntity
from .helpers import create_entities

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.device_registry import DeviceInfo
    from homeassistant.helpers.entity_platform import AddEntitiesCallback
    from homeconnect_websocket import HomeAppliance
    from homeconnect_websocket.entities import Entity as HcEntity

    from . import HCConfigEntry
    from .entity_descriptions.descriptions_definitions import HCFanEntityDescription

PARALLEL_UPDATES = 0

_OPERATION_STATE_ENTITY = "BSH.Common.Status.OperationState"
_INACTIVE_STATES = {"inactive", "ready"}
_VENTING_PROGRAM = "Cooking.Common.Program.Hood.Venting"


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
    _operation_state_entity: HcEntity | None = None

    def __init__(
        self,
        entity_description: HCFanEntityDescription,
        appliance: HomeAppliance,
        device_info: DeviceInfo,
    ) -> None:
        super().__init__(entity_description, appliance, device_info)
        self._attr_supported_features = FanEntityFeature.SET_SPEED | FanEntityFeature.TURN_OFF
        self._speed_mapping = []
        self._speed_entities = {}
        self._attr_speed_count = 0
        for entity_name in entity_description.entities:
            entity = self._appliance.entities[entity_name]
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

        if _OPERATION_STATE_ENTITY in self._appliance.entities:
            self._operation_state_entity = self._appliance.entities[_OPERATION_STATE_ENTITY]
            self._entities.append(self._operation_state_entity)

    @property
    def is_on(self) -> bool | None:
        if self._operation_state_entity is not None:
            return str(self._operation_state_entity.value or "").lower() not in _INACTIVE_STATES
        return self.percentage is not None and self.percentage > 0

    @property
    def percentage(self) -> int | None:
        if not self.is_on:
            return 0
        for speed in self._speed_mapping:
            if self._speed_entities[speed.entity_name].value_raw == speed.entity_value:
                return ranged_value_to_percentage(self._speed_range, speed.speed)
        return 0

    async def async_set_percentage(self, percentage: int) -> None:
        new_speed = math.ceil(percentage_to_ranged_value(self._speed_range, percentage))
        if new_speed == 0:
            await self.async_turn_off()
            return

        new_speed_entity: str = None
        new_speed_value: int = None
        for speed in self._speed_mapping:
            if speed.speed == new_speed:
                new_speed_entity = speed.entity_name
                new_speed_value = speed.entity_value

        if new_speed_entity is None:
            msg = f"Speed {percentage} is invalid"
            raise ServiceValidationError(msg)

        is_active = (
            self._operation_state_entity is not None
            and str(self._operation_state_entity.value or "").lower() not in _INACTIVE_STATES
        )

        if not is_active and _VENTING_PROGRAM in self._appliance.programs:
            prog = self._appliance.programs[_VENTING_PROGRAM]
            if prog.execution == Execution.START_ONLY:
                await prog.start()
            else:
                await prog.select()

        data = []
        for entity in self._speed_entities.values():
            if entity.name == new_speed_entity:
                data.append({"uid": entity.uid, "value": new_speed_value})
            else:
                data.append({"uid": entity.uid, "value": 0})
        message = Message(
            resource="/ro/values",
            action=Action.POST,
            data=data,
        )
        await self._appliance.session.send_sync(message)

    async def async_turn_off(self, **kwargs: Any) -> None:
        message = Message(
            resource="/ro/activeProgram",
            action="DELETE",
            data=[],
        )
        await self._appliance.session.send_sync(message)
