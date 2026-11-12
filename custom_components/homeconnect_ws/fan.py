"""Fan entities."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Any, NamedTuple

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.exceptions import ServiceValidationError
from homeassistant.util.percentage import percentage_to_ranged_value, ranged_value_to_percentage
from homeconnect_websocket.entities import Access, ActiveProgram
from homeconnect_websocket.message import Action, Message

from .const import DOMAIN
from .entity import HCEntity
from .helpers import create_entities, error_decorator

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback
    from homeconnect_websocket.entities import Entity as HcEntity
    from homeconnect_websocket.entities import Program as HcProgram

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
        self._attr_supported_features = FanEntityFeature.SET_SPEED | FanEntityFeature.TURN_OFF
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

        if entity_description.program:
            # Program options keep their last value when the Program ends,
            # track the active Program to report the fan as off
            for entity in self._runtime_data.appliance.entities.values():
                if isinstance(entity, ActiveProgram):
                    self._entities.append(entity)
                    break

    @property
    def percentage(self) -> int | None:
        if self.entity_description.program and self._runtime_data.appliance.active_program is None:
            return 0
        for speed in self._speed_mapping:
            if self._speed_entities[speed.entity_name].value_raw == speed.entity_value:
                return ranged_value_to_percentage(self._speed_range, speed.speed)
        return 0

    def _speed_options(self, speed_entity: str | None, speed_value: int) -> dict[int, int]:
        """Return the values of all speed entities for the given speed, keyed by uid."""
        return {
            entity.uid: speed_value if entity.name == speed_entity else 0
            for entity in self._speed_entities.values()
        }

    def _get_speed_program(self) -> HcProgram | None:
        """
        Return the Program to send speed options to.

        The active Program is used if it has the speed entities as options,
        otherwise the Program from the entity description.
        """
        appliance = self._runtime_data.appliance
        speed_uids = {entity.uid for entity in self._speed_entities.values()}
        active_program = appliance.active_program
        if active_program is not None:
            program_option_uids = {option.uid for option in getattr(active_program, "_options", [])}
            if speed_uids <= program_option_uids:
                return active_program
        return appliance.programs.get(self.entity_description.program)

    @error_decorator
    async def async_set_percentage(self, percentage: int) -> None:
        if percentage == 0:
            await self.async_turn_off()
            return
        new_speed = math.ceil(percentage_to_ranged_value(self._speed_range, percentage))
        new_speed_entity: str = None
        new_speed_value: int = None
        for speed in self._speed_mapping:
            if speed.speed == new_speed:
                new_speed_entity = speed.entity_name
                new_speed_value = speed.entity_value
        if not new_speed_entity:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="speed_invalid",
                translation_placeholders={"percentage": str(percentage)},
            )
        options = self._speed_options(new_speed_entity, new_speed_value)

        if self.entity_description.program and (program := self._get_speed_program()):
            # Speed entities are Program options (e.g. Hood Venting/Intensive level),
            # they have to be set by (re)starting the Program with the new options
            await program.start(options=options, override_options=True)
        else:
            message = Message(
                resource="/ro/values",
                action=Action.POST,
                data=[{"uid": uid, "value": value} for uid, value in options.items()],
            )
            await self._runtime_data.appliance.session.send_sync(message)

    @error_decorator
    async def async_turn_off(self, **kwargs: Any) -> None:
        appliance = self._runtime_data.appliance
        if self.entity_description.program:
            # Program options can't be set to 0, stop the Program instead
            abort = appliance.commands.get("BSH.Common.Command.AbortProgram")
            if abort is not None and abort.available and appliance.active_program is not None:
                await abort.execute(True)  # noqa: FBT003
                return
            power_state = appliance.settings.get("BSH.Common.Setting.PowerState")
            if (
                power_state is not None
                and power_state.access in (Access.READ_WRITE, Access.WRITE_ONLY)
                and power_state.enum
            ):
                for off_value in ("Off", "Standby"):
                    if off_value in power_state.enum.values():
                        await power_state.set_value(off_value)
                        return

        message = Message(
            resource="/ro/values",
            action=Action.POST,
            data=[{"uid": uid, "value": 0} for uid in self._speed_options(None, 0)],
        )
        await appliance.session.send_sync(message)
