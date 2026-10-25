"""Button entities."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from homeassistant.components.button import ButtonEntity
from homeconnect_websocket.errors import CodeResponsError

from .entity import HCEntity
from .helpers import (
    EVENT_ON_VALUES,
    WRITE_REQUEST_BUSY,
    EventStaleTracker,
    acknowledge_with_retry,
    create_entities,
    error_decorator,
    leaves_alarm_event_on,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback
    from homeconnect_websocket.entities import ActiveProgram, Command, Event
    from homeconnect_websocket.entities import Entity as HcEntity

    from . import HCConfigEntry, HCData
    from .entity_descriptions.descriptions_definitions import HCButtonEntityDescription

PARALLEL_UPDATES = 0

# The appliance refuses writes while it is operated locally, until about 10 seconds after the last
# touch. The acknowledge buttons try again every second for 15 seconds.
ACKNOWLEDGE_RETRY_DELAY = 1
ACKNOWLEDGE_RETRIES = 15


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001
    config_entry: HCConfigEntry,
    async_add_entites: AddEntitiesCallback,
) -> None:
    """Set up button platform."""
    entities = create_entities(
        {"button": HCButton, "start_button": HCStartButton}, config_entry.runtime_data
    )
    async_add_entites(entities)


class HCButton(HCEntity, ButtonEntity):
    """Abort Button Entity."""

    _entity: Command | Event
    entity_description: HCButtonEntityDescription

    def __init__(
        self,
        entity_description: HCButtonEntityDescription,
        runtime_data: HCData,
    ) -> None:
        super().__init__(entity_description, runtime_data)
        self._retry_task: asyncio.Task | None = None
        self._alarm_clock: HcEntity | None = None
        self._tracker: EventStaleTracker | None = None
        # A hob sets the alarm clock to 0 in the same message as the event, so the alarm clock
        # cannot tell whether an alarm has elapsed: there the event itself decides.
        self._event_decides = (
            entity_description.alarm_state == "elapsed"
            and not leaves_alarm_event_on(runtime_data.appliance)
        )
        name = entity_description.alarm_clock_entity
        if name and name in runtime_data.appliance.entities:
            self._alarm_clock = runtime_data.appliance.entities[name]
            self._tracker = EventStaleTracker(self._entity, self._alarm_clock, EVENT_ON_VALUES)
            # Also update the state when this entity changes
            self._entities.append(self._alarm_clock)

    async def callback(self, entity: HcEntity) -> None:
        if self._tracker is not None:
            self._tracker.update(entity)
        await super().callback(entity)

    @property
    def available(self) -> bool:
        available = super().available
        if self._event_decides:
            # The alarm has elapsed as long as the event is Present, whatever the alarm clock is
            return available and self._entity.value == "Present"
        if self._alarm_clock is not None:
            # Only when the alarm clock is set: a timer is running or an alarm has elapsed
            available &= bool(self._alarm_clock.value)
            if self._alarm_clock.value and self.entity_description.alarm_state:
                # An event that is on is an elapsed alarm, unless a timer was started after it
                # was reported: the appliance leaves the event on after a confirmed alarm.
                elapsed = self._entity.value in EVENT_ON_VALUES and not self._tracker.stale
                available &= elapsed == (self.entity_description.alarm_state == "elapsed")
        return available

    async def async_press(self) -> None:
        if self.entity_description.acknowledge_event:
            await self._acknowledge_event()
            return
        await self._entity.set_value(True)

    async def async_will_remove_from_hass(self) -> None:
        if self._retry_task is not None and not self._retry_task.done():
            self._retry_task.cancel()
        await super().async_will_remove_from_hass()

    @error_decorator
    async def _acknowledge_event(self) -> None:
        """
        Acknowledge the Event of this button.

        Sends BSH.Common.Command.AcknowledgeEvent with the uid of the event as value
        (POST /ro/values {"uid": <AcknowledgeEvent uid>, "value": <event uid>}).

        When the appliance answers Busy (it is operated locally) the press is not an error: the
        acknowledge is tried again in the background until it is accepted.
        """
        try:
            await self._entity.acknowledge()
        except CodeResponsError as exc:
            if exc.code != WRITE_REQUEST_BUSY:
                raise
            if self._retry_task is None or self._retry_task.done():
                self._retry_task = self.hass.async_create_background_task(
                    self._async_retry_acknowledge(),
                    name=f"{self.entity_description.key} acknowledge retry",
                )

    async def _async_retry_acknowledge(self) -> None:
        """Try again to acknowledge, the appliance was busy."""
        await asyncio.sleep(ACKNOWLEDGE_RETRY_DELAY)
        # Stops when the alarm clock is 0 in the meantime, there is nothing to acknowledge then
        await acknowledge_with_retry(
            self._entity,
            still_needed=lambda: self.available,
            attempts=ACKNOWLEDGE_RETRIES,
            delay=ACKNOWLEDGE_RETRY_DELAY,
        )


class HCStartButton(HCEntity, ButtonEntity):
    """Start Button Entity."""

    _entity: ActiveProgram
    entity_description: HCButtonEntityDescription

    @property
    def available(self) -> bool:
        available = super().available
        available &= self._runtime_data.appliance.selected_program is not None
        return available

    @error_decorator
    async def async_press(self) -> None:
        await self._runtime_data.appliance.selected_program.start()
