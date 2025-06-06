"""Description for all supported Entities."""

from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.homeconnect_ws.helpers import merge_dicts

from .common import COMMON_ENTITY_DESCRIPTIONS
from .consumer_products import CONSUMER_PRODUCTS_ENTITY_DESCRIPTIONS
from .cooking import COOKING_ENTITY_DESCRIPTIONS
from .descriptions_definitions import (
    EntityDescriptions,
    HCBinarySensorEntityDescription,
    HCButtonEntityDescription,
    HCEntityDescription,
    HCFanEntityDescription,
    HCLightEntityDescription,
    HCNumberEntityDescription,
    HCSelectEntityDescription,
    HCSensorEntityDescription,
    HCSwitchEntityDescription,
    _EntityDescriptionsDefinitionsType,
    _EntityDescriptionsType,
)
from .dishcare import DISHCARE_ENTITY_DESCRIPTIONS
from .laundry_care import LAUNDRY_ENTITY_DESCRIPTIONS
from .refrigeration import REFRIGERATION_ENTITY_DESCRIPTIONS

if TYPE_CHECKING:
    from homeconnect_websocket import HomeAppliance


ALL_ENTITY_DESCRIPTIONS: _EntityDescriptionsDefinitionsType | None = None


def get_all_entity_description() -> _EntityDescriptionsDefinitionsType:
    global ALL_ENTITY_DESCRIPTIONS  # noqa: PLW0603
    if ALL_ENTITY_DESCRIPTIONS is None:
        ALL_ENTITY_DESCRIPTIONS = merge_dicts(
            COMMON_ENTITY_DESCRIPTIONS,
            CONSUMER_PRODUCTS_ENTITY_DESCRIPTIONS,
            COOKING_ENTITY_DESCRIPTIONS,
            DISHCARE_ENTITY_DESCRIPTIONS,
            LAUNDRY_ENTITY_DESCRIPTIONS,
            REFRIGERATION_ENTITY_DESCRIPTIONS,
        )
    return ALL_ENTITY_DESCRIPTIONS


def get_available_entities(appliance: HomeAppliance) -> EntityDescriptions:
    """Get all available Entity descriptions."""
    available_entities: _EntityDescriptionsType = {
        "button": [],
        "active_program": [],
        "binary_sensor": [],
        "event_sensor": [],
        "number": [],
        "program": [],
        "select": [],
        "sensor": [],
        "start_button": [],
        "switch": [],
        "wifi": [],
        "light": [],
        "fan": [],
    }
    appliance_entities = set(appliance.entities)
    for description_type, descriptions in get_all_entity_description().items():
        # dynamic descriptions
        if description_type == "dynamic":
            for descriptions_fn in descriptions:
                dynamic_descriptions: _EntityDescriptionsType = descriptions_fn(appliance)
                for key, value in dynamic_descriptions.items():
                    available_entities[key].extend(value)
            continue
        for description in descriptions:
            if callable(description):
                if dynamic_description := description(appliance):
                    available_entities[description_type].append(dynamic_description)
            else:
                all_subscribed_entities = set()
                if description.entity:
                    all_subscribed_entities.add(description.entity)
                if description.entities:
                    all_subscribed_entities.update(description.entities)
                if appliance_entities.issuperset(all_subscribed_entities):
                    available_entities[description_type].append(description)
    return available_entities


__all__ = [
    "EntityDescriptions",
    "HCBinarySensorEntityDescription",
    "HCButtonEntityDescription",
    "HCEntityDescription",
    "HCFanEntityDescription",
    "HCLightEntityDescription",
    "HCNumberEntityDescription",
    "HCSelectEntityDescription",
    "HCSensorEntityDescription",
    "HCSwitchEntityDescription",
    "_EntityDescriptionsType",
    "get_available_entities",
]
