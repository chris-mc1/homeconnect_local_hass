"""
Keeps the alarm clock event of the appliance up to date.

Some ovens (Gaggenau BO470112, BS474112) leave BSH.Common.Event.AlarmClockElapsed on "Present"
after the alarm is confirmed on the oven. The oven does not report the event again when the next
timer elapses, because the value does not change. Acknowledging the event resets it.

This is done automatically, there is no entity for it. The event is acknowledged
(BSH.Common.Command.AcknowledgeEvent) when all of these are true:

- the event is "Present"
- the alarm clock is 0: the alarm was confirmed on the oven or no timer is set. The alarm clock is
  not 0 while a timer is running or an alarm has elapsed without being confirmed, so the display
  of the oven and a running timer are never touched. Acknowledging does end a running timer.

The oven refuses every write with code 516 (WriteRequest Busy) while it is operated locally
(BSH.Common.Status.LocalControlActive is True, until about 10 seconds after the last touch).
Tried right after confirming and every second after that: it was busy for the whole period, so
the acknowledge waits until the oven is not operated locally.
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

from .helpers import acknowledge_with_retry

if TYPE_CHECKING:
    import asyncio

    from homeassistant.core import HomeAssistant
    from homeconnect_websocket import HomeAppliance
    from homeconnect_websocket.entities import Entity as HcEntity

_LOGGER = logging.getLogger(__name__)

# Entities of the appliance
EVENT = "BSH.Common.Event.AlarmClockElapsed"
ALARM_CLOCK = "BSH.Common.Setting.AlarmClock"
LOCAL_CONTROL = "BSH.Common.Status.LocalControlActive"
ACKNOWLEDGE_COMMAND = "BSH.Common.Command.AcknowledgeEvent"

# Number of attempts and the pause between two attempts in seconds
ATTEMPTS = 3
RETRY_DELAY = 5
# After a successful acknowledge no other acknowledge is sent for this many seconds. The appliance
# needs a moment to report that the event was reset, in the meantime the event still looks Present.
COOLDOWN = 5


class AlarmClockCleaner:
    """Resets the alarm clock event of the appliance when it is left on."""

    def __init__(self, hass: HomeAssistant, appliance: HomeAppliance) -> None:
        """Set up the cleaner, use `is_supported` first."""
        self._hass = hass
        self._event = appliance.entities[EVENT]
        self._alarm_clock = appliance.entities[ALARM_CLOCK]
        self._local_control = appliance.entities[LOCAL_CONTROL]
        self._entities = (self._event, self._alarm_clock, self._local_control)
        self._task: asyncio.Task | None = None
        # time.monotonic() of the last successful acknowledge
        self._last_acknowledge: float | None = None

    @staticmethod
    def is_supported(appliance: HomeAppliance) -> bool:
        """Check if the appliance has everything that is needed."""
        return (
            EVENT in appliance.entities
            and ALARM_CLOCK in appliance.entities
            and LOCAL_CONTROL in appliance.entities
            and ACKNOWLEDGE_COMMAND in appliance.commands
        )

    def start(self) -> None:
        """Start following the appliance."""
        for entity in self._entities:
            entity.register_callback(self._callback)
        self._check()

    def stop(self) -> None:
        """Stop following the appliance."""
        for entity in self._entities:
            entity.unregister_callback(self._callback)
        if self._task is not None and not self._task.done():
            self._task.cancel()
        self._task = None

    async def _callback(self, _: HcEntity) -> None:
        self._check()

    def _conditions_met(self) -> bool:
        """Check if the event can be acknowledged now."""
        return (
            self._event.value == "Present"
            and self._alarm_clock.value == 0
            and self._local_control.value is False
        )

    def _check(self) -> None:
        """Start acknowledging when possible and not already busy with it."""
        if self._task is not None and not self._task.done():
            return
        if (
            self._last_acknowledge is not None
            and time.monotonic() - self._last_acknowledge < COOLDOWN
        ):
            return
        if self._conditions_met():
            _LOGGER.debug("Alarm clock: conditions met, acknowledging")
            self._task = self._hass.async_create_background_task(
                self._async_acknowledge(), name="homeconnect_ws alarm clock acknowledge"
            )
        else:
            _LOGGER.debug(
                "Alarm clock: nothing to do (event=%s, alarm clock=%s, local control=%s)",
                self._event.value,
                self._alarm_clock.value,
                self._local_control.value,
            )

    async def _async_acknowledge(self) -> None:
        """Acknowledge the event, retry when the appliance is busy."""
        if await acknowledge_with_retry(
            self._event,
            still_needed=self._conditions_met,
            attempts=ATTEMPTS,
            delay=RETRY_DELAY,
        ):
            self._last_acknowledge = time.monotonic()
            _LOGGER.debug("Alarm clock: acknowledged")
