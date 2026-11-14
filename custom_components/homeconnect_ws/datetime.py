"""Date/time entities."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from homeassistant.components.datetime import DateTimeEntity
from homeassistant.util import dt as dt_util

from .entity import HCEntity
from .helpers import create_entities, error_decorator

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from . import HCConfigEntry, HCData
    from .entity_descriptions.descriptions_definitions import HCDateTimeEntityDescription

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001
    config_entry: HCConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up date/time platform."""
    entities = create_entities({"datetime": HCDateTime}, config_entry.runtime_data)
    async_add_entities(entities)


class HCDateTime(HCEntity, DateTimeEntity):
    """Home Connect date/time entity."""

    entity_description: HCDateTimeEntityDescription

    def __init__(
        self,
        entity_description: HCDateTimeEntityDescription,
        runtime_data: HCData,
    ) -> None:
        """Initialize date/time entity."""
        super().__init__(entity_description, runtime_data)
        self._entity._type = str  # noqa: SLF001

    @property
    def native_value(self) -> datetime | None:
        """Return appliance-local date/time."""
        value = self._entity.value
        if not value:
            return None

        parsed = dt_util.parse_datetime(str(value))
        if parsed is None:
            return None

        if parsed.tzinfo is None:
            timezone = dt_util.get_time_zone(self.hass.config.time_zone)
            if timezone is None:
                return None
            parsed = parsed.replace(tzinfo=timezone)

        return parsed

    @error_decorator
    async def async_set_value(self, value: datetime) -> None:
        """Set appliance-local date/time."""
        timezone = dt_util.get_time_zone(self.hass.config.time_zone)
        if timezone is not None:
            value = value.astimezone(timezone)

        await self._entity.set_value(value.strftime("%Y-%m-%dT%H:%M:%S"))
