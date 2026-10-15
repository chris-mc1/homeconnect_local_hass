"""Tests for cavity-scoped oven completion and preheating events."""

from __future__ import annotations

from copy import deepcopy
from typing import TYPE_CHECKING
from unittest.mock import Mock

import pytest
from custom_components.homeconnect_ws import coordinator
from custom_components.homeconnect_ws.const import DOMAIN
from custom_components.homeconnect_ws.entity_descriptions import (
    HCBinarySensorEntityDescription,
    get_available_entities,
)
from custom_components.homeconnect_ws.entity_descriptions.cooking import generate_oven_event
from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.const import STATE_OFF, STATE_ON, STATE_UNKNOWN, EntityCategory
from homeassistant.helpers import entity_registry as er
from homeconnect_websocket.entities import DeviceDescription, EntityDescription

from . import setup_config_entry
from .const import CONFIG_ENTRIES, DEVICE_DESCRIPTION

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeconnect_websocket.testutils import MockAppliance, MockApplianceType

EVENTS = {
    "AlarmClockElapsed": "alarm_clock_elapsed",
    "ProgramFinished": "program_finished",
    "ProgramAborted": "program_aborted",
    "RegularPreheatFinished": "regular_preheat_finished",
    "FastPreheatFinished": "fast_preheat_finished",
    "MeatprobeTemperatureReached": "meatprobe_temperature_reached",
}
EVENT_ENUM = {"0": "Off", "1": "Present", "2": "Confirmed"}


def event_description(name: str, uid: int) -> EntityDescription:
    """Build an event with the appliance's standard presence/confirmation enum."""
    return EntityDescription(uid=uid, name=name, enumeration=EVENT_ENUM)


@pytest.mark.parametrize("cavities", [(), ("001",), ("140", "141")])
async def test_event_discovery(
    mock_homeconnect_appliance: MockApplianceType, cavities: tuple[str, ...]
) -> None:
    """Discover selected advertised events and keep cavity names and IDs distinct."""
    description = DeviceDescription(
        event=[
            event_description(
                f"Cooking.Oven.Event.Cavity.{cavity}.{event}", 6000 + index * 100 + uid
            )
            for index, cavity in enumerate(cavities)
            for uid, event in enumerate([*EVENTS, "ErrorDoorLatch"])
        ]
    )
    appliance = await mock_homeconnect_appliance(description=description)
    descriptions = generate_oven_event(appliance)["binary_sensor"]
    by_key = {entity.key: entity for entity in descriptions}
    assert len(descriptions) == len(EVENTS) * len(cavities)
    assert len(by_key) == len(descriptions)
    for cavity in cavities:
        for event, key in EVENTS.items():
            entity = by_key[f"binary_sensor_oven_{key}_{cavity}"]
            assert entity.entity == f"Cooking.Oven.Event.Cavity.{cavity}.{event}"
            assert entity.translation_placeholders == {
                "group_name": f" {int(cavity)}" if len(cavities) > 1 else ""
            }
            assert entity.entity_registry_enabled_default
            if event == "ProgramAborted":
                assert entity.device_class == BinarySensorDeviceClass.PROBLEM
                assert entity.entity_category == EntityCategory.DIAGNOSTIC
            elif event == "ProgramFinished":
                assert entity.entity_category == EntityCategory.DIAGNOSTIC


async def test_partial_event_profile(mock_homeconnect_appliance: MockApplianceType) -> None:
    """Keep the existing alarm clock mapping and omit unsupported event entities."""
    appliance = await mock_homeconnect_appliance(
        description=DeviceDescription(
            event=[event_description("Cooking.Oven.Event.Cavity.001.AlarmClockElapsed", 6000)]
        )
    )
    assert generate_oven_event(appliance)["binary_sensor"] == [
        HCBinarySensorEntityDescription(
            key="binary_sensor_oven_alarm_clock_elapsed_001",
            translation_key="binary_sensor_oven_alarm_clock_elapsed",
            translation_placeholders={"group_name": ""},
            entity="Cooking.Oven.Event.Cavity.001.AlarmClockElapsed",
            value_on={"Present", "Confirmed"},
            value_off={"Off"},
        )
    ]


async def test_generic_events_unchanged(mock_homeconnect_appliance: MockApplianceType) -> None:
    """Keep generic completion events on appliances using the BSH.Common namespace."""
    appliance = await mock_homeconnect_appliance(
        description=DeviceDescription(
            event=[
                event_description(f"BSH.Common.Event.{event}", 6000 + index)
                for index, event in enumerate(["ProgramFinished", "ProgramAborted"])
            ]
        )
    )
    descriptions = get_available_entities(appliance)["binary_sensor"]
    assert {entity.key for entity in descriptions} == {
        "binary_sensor_program_finished",
        "binary_sensor_program_aborted",
    }
    assert not generate_oven_event(appliance)["binary_sensor"]


@pytest.fixture
async def oven_events_appliance(
    mock_homeconnect_appliance: MockApplianceType, monkeypatch: pytest.MonkeyPatch
) -> MockAppliance:
    """Set up an oven advertising all supported cavity events."""
    description = deepcopy(DEVICE_DESCRIPTION)
    description["event"].extend(
        event_description(f"Cooking.Oven.Event.Cavity.001.{event}", 6000 + index)
        for index, event in enumerate(EVENTS)
    )
    appliance = await mock_homeconnect_appliance(description=description)
    appliance.session.connected = True
    monkeypatch.setattr(coordinator, "HomeAppliance", Mock(return_value=appliance))
    monkeypatch.setattr(coordinator.HomeConnectCoordinator, "connected", True)
    return appliance


@pytest.mark.parametrize("event", EVENTS)
async def test_event_states(
    hass: HomeAssistant, oven_events_appliance: MockAppliance, event: str
) -> None:
    """Keep Present and Confirmed active, and clear only when the appliance reports Off."""
    assert await setup_config_entry(hass, CONFIG_ENTRIES[0])
    key = f"binary_sensor_oven_{EVENTS[event]}_001"
    entity_id = er.async_get(hass).async_get_entity_id(
        "binary_sensor", DOMAIN, f"{oven_events_appliance.info['deviceID']}-{key}"
    )
    assert entity_id is not None
    assert hass.states.get(entity_id).state == STATE_UNKNOWN
    entity = oven_events_appliance.entities[f"Cooking.Oven.Event.Cavity.001.{event}"]
    for value, expected in [(0, STATE_OFF), (1, STATE_ON), (2, STATE_ON), (0, STATE_OFF)]:
        await entity.update({"value": value})
        await hass.async_block_till_done()
        assert hass.states.get(entity_id).state == expected
