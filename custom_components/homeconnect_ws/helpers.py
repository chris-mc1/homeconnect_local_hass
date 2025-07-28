"""Helper functions."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.service import async_extract_config_entry_ids

from custom_components.homeconnect_ws.const import DOMAIN

if TYPE_CHECKING:
    import re

    from homeassistant.core import HomeAssistant, ServiceCall
    from homeconnect_websocket import HomeAppliance
    from homeconnect_websocket.entities import Access
    from homeconnect_websocket.entities import Entity as HcEntity

    from . import HCConfigEntry, HCData
    from .entity import HCEntity

_LOGGER = logging.getLogger(__name__)


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
                        entity_description=entity_description,
                        appliance=runtime_data.appliance,
                        device_info=runtime_data.device_info,
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
    config_entry_ids = await async_extract_config_entry_ids(hass, service_call)
    for config_entry_id in config_entry_ids:
        config_entry = hass.config_entries.async_get_entry(config_entry_id)
        if config_entry.domain == DOMAIN:
            return config_entry
    msg = "Not a Homeconnect Appliance"
    raise ServiceValidationError(msg)


def entity_is_available(entity: HcEntity, available_access: tuple[Access]) -> bool:
    """Check is HC entity is available."""
    available = True
    if hasattr(entity, "available"):
        available &= entity.available

    if hasattr(entity, "access"):
        available &= entity.access in available_access
    return True
