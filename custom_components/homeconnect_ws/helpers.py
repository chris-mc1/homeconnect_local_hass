"""Helper functions."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers.service import async_extract_config_entry_ids
from homeconnect_websocket.errors import AccessError, CodeResponsError, NotConnectedError

from .const import DOMAIN

if TYPE_CHECKING:
    import re
    from collections.abc import Callable, Coroutine

    from homeassistant.core import HomeAssistant, ServiceCall
    from homeconnect_websocket import HomeAppliance
    from homeconnect_websocket.entities import Access, Event
    from homeconnect_websocket.entities import Entity as HcEntity

    from . import HCConfigEntry, HCData
    from .entity import HCEntity

_LOGGER = logging.getLogger(__name__)

# Code the appliance responds with when it refuses a write: "WriteRequest Busy". It does this while
# it is operated locally, until about 10 seconds after the last touch.
WRITE_REQUEST_BUSY = 516
# Values of an Event that mean that it is on
EVENT_ON_VALUES = {"Present", "Confirmed"}


def create_entities(
    entities_classes: dict[str, type[HCEntity]], runtime_data: HCData
) -> set[HCEntity]:
    """Create entities from entity_descriptions."""
    entities = set()
    for entity_key, entity_class in entities_classes.items():
        if entity_key in runtime_data.available_entity_descriptions:
            for entity_description in runtime_data.available_entity_descriptions[entity_key]:
                _LOGGER.debug("Creating Entity %s", entity_description.key)
                try:
                    entity = entity_class(
                        entity_description=entity_description, runtime_data=runtime_data
                    )
                except Exception:
                    _LOGGER.exception("Failed to create Entity %s", entity_description.key)
                else:
                    entities.add(entity)
    return entities


def merge_dicts(*args: dict[str, list]) -> dict[str, list]:
    """Merge multiple dictionaries of type dict[str, list]."""
    out_dict: dict[str, list] = {}
    for in_dict in args:
        for key, value in in_dict.items():
            if key not in out_dict:
                out_dict[key] = value
            else:
                out_dict[key].extend(value)
    return out_dict


@dataclass
class EntityMatch:
    """Returned by get_entities_from_regex."""

    entity: str
    groups: tuple[str]


def get_entities_from_regex(appliance: HomeAppliance, pattern: re.Pattern) -> list[EntityMatch]:
    """Get all entities matching the pattern."""
    return [
        EntityMatch(entity=entity, groups=match.groups())
        for entity in appliance.entities
        if (match := pattern.match(entity))
    ]


def get_groups_from_regex(appliance: HomeAppliance, pattern: re.Pattern) -> set[tuple[str]]:
    """Get all regex groups matching the pattern."""
    groups = set()
    for entity in appliance.entities:
        if (match := pattern.match(entity)) and match.groups() not in groups:
            groups.add(match.groups())
    return groups


async def get_config_entry_from_call(
    hass: HomeAssistant, service_call: ServiceCall
) -> HCConfigEntry | None:
    """Get the config entry from a service call."""
    config_entry_ids = await async_extract_config_entry_ids(service_call)
    for config_entry_id in config_entry_ids:
        config_entry = hass.config_entries.async_get_entry(config_entry_id)
        if config_entry.domain == DOMAIN:
            return config_entry
    raise ServiceValidationError(translation_domain=DOMAIN, translation_key="not_appliance")


def entity_is_available(entity: HcEntity, available_access: tuple[Access]) -> bool:
    """Check is HC entity is available."""
    available = True
    if hasattr(entity, "available"):
        available &= entity.available

    if hasattr(entity, "access"):
        available &= entity.access in available_access
    return available


def error_decorator[T](func: Callable[..., Coroutine[T]]) -> Callable[..., Coroutine[T]]:
    """Catches HomeConnect Errors and raise HomeAssistantError."""

    async def wrap(*args: Any, **kwargs: Any) -> Any:
        try:
            return await func(*args, **kwargs)
        except AccessError:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="access_error",
            ) from None
        except CodeResponsError as exc:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="code_respons",
                translation_placeholders={"message": exc.message},
            ) from None
        except NotConnectedError:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="not_connected",
            ) from None

    return wrap


class EventStaleTracker:
    """
    Tracks if an Event that is on belongs to an earlier alarm.

    Some ovens (Gaggenau BO470112, BS474112) leave AlarmClockElapsed on "Present" after the alarm
    is confirmed on the oven. When a new timer is started the event is still "Present" and the
    oven does not report it again when the new timer elapses.

    The event is "stale" when a timer was started (the timer entity went from 0 to a value)
    after the event was last reported as on.
    """

    def __init__(self, event: HcEntity, timer: HcEntity, on_values: set[str]) -> None:
        """
        Track an event and the timer that belongs to it.

        Args:
        ----
            event (HcEntity): The event, e.g. BSH.Common.Event.AlarmClockElapsed
            timer (HcEntity): The timer, e.g. BSH.Common.Setting.AlarmClock, 0 when not set
            on_values (set[str]): Values of the event that mean that it is on

        """
        self._event = event
        self._timer = timer
        self._on_values = on_values
        self._timer_running = bool(timer.value)
        self.stale = False

    def update(self, entity: HcEntity) -> None:
        """Process an update of the event or the timer."""
        if entity is self._timer:
            running = bool(entity.value)
            if running and not self._timer_running:
                self.stale = True
            self._timer_running = running
        elif entity is self._event and entity.value in self._on_values:
            self.stale = False


async def acknowledge_with_retry(
    event: Event,
    *,
    still_needed: Callable[[], bool],
    attempts: int,
    delay: float,
) -> bool:
    """
    Acknowledge an Event, try again when the appliance is busy.

    Args:
    ----
        event (Event): The event to acknowledge
        still_needed (Callable[[], bool]): Checked before every attempt, stops when it is False
        attempts (int): Maximum number of attempts
        delay (float): Pause between two attempts in seconds

    Returns:
    -------
        bool: True when the appliance accepted the acknowledge

    """
    for attempt in range(1, attempts + 1):
        if not still_needed():
            return False
        try:
            await event.acknowledge()
        except CodeResponsError as exc:
            if exc.code != WRITE_REQUEST_BUSY:
                _LOGGER.warning("Failed to acknowledge %s: %s", event.name, exc)
                return False
            _LOGGER.debug(
                "Appliance busy, acknowledge %s attempt %s/%s", event.name, attempt, attempts
            )
        except (AccessError, NotConnectedError) as exc:
            _LOGGER.debug("Failed to acknowledge %s: %s", event.name, exc)
            return False
        else:
            return True
        if attempt < attempts:
            await asyncio.sleep(delay)
    return False
