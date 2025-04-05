"""Description for all supported Entities."""

from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.homeconnect_ws.helpers import merge_dicts

from .common import COMMON_ENTITY_DESCRIPTIONS
from .cooking import COOKING_ENTITY_DESCRIPTIONS
from .descriptions_definitions import (
    HCBinarySensorEntityDescription,
    HCButtonEntityDescription,
    HCEntityDescription,
    HCNumberEntityDescription,
    HCSelectEntityDescription,
    HCSensorEntityDescription,
    HCSwitchEntityDescription,
    _EntityDescriptionsType,
)
from .dishcare import DISHCARE_ENTITY_DESCRIPTIONS
from .refrigeration import REFRIGERATION_ENTITY_DESCRIPTIONS

if TYPE_CHECKING:
    from homeconnect_websocket import HomeAppliance

    from .descriptions_definitions import EntityDescriptions

ALL_ENTITY_DESCRIPTIONS: _EntityDescriptionsType | None = None


def get_all_entity_description() -> _EntityDescriptionsType:
    global ALL_ENTITY_DESCRIPTIONS  # noqa: PLW0603
    if ALL_ENTITY_DESCRIPTIONS is None:
        ALL_ENTITY_DESCRIPTIONS = merge_dicts(
            COMMON_ENTITY_DESCRIPTIONS,
            COOKING_ENTITY_DESCRIPTIONS,
            DISHCARE_ENTITY_DESCRIPTIONS,
            REFRIGERATION_ENTITY_DESCRIPTIONS,
        )
    return ALL_ENTITY_DESCRIPTIONS


def get_available_entities(appliance: HomeAppliance) -> EntityDescriptions:
    """Get all available Entity descriptions."""
    available_entities: dict[str, list[HCEntityDescription]] = {
        "abort_button": [],
        "active_program": [],
        "binary_sensor": [],
        "event_sensor": [],
        "number": [],
        "power_switch": [],
        "program": [],
        "select": [],
        "sensor": [],
        "start_button": [],
        "start_in": [],
        "switch": [],
    }
    for description_type, descriptions in get_all_entity_description().items():
        for description in descriptions:
            if callable(description) and (dynamic_description := description(appliance)):
                available_entities[description_type].append(dynamic_description)
            all_subscribed_entities = []
            if description.entity:
                all_subscribed_entities.append(description.entity)
            if description.entities:
                all_subscribed_entities.extend(description.entities)
            if set(all_subscribed_entities).intersection(appliance.entities):
                available_entities[description_type].append(description)
    return available_entities


__all__ = [
    "HCBinarySensorEntityDescription",
    "HCButtonEntityDescription",
    "HCEntityDescription",
    "HCNumberEntityDescription",
    "HCSelectEntityDescription",
    "HCSensorEntityDescription",
    "HCSwitchEntityDescription",
    "get_available_entities",
]
