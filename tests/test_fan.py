"""Tests for fan entity."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.fan import (
    ATTR_PERCENTAGE,
    ATTR_PERCENTAGE_STEP,
    SERVICE_SET_PERCENTAGE,
    FanEntityFeature,
)
from homeassistant.components.fan import DOMAIN as FAN_DOMAIN
from homeassistant.const import (
    ATTR_ENTITY_ID,
    ATTR_FRIENDLY_NAME,
    ATTR_SUPPORTED_FEATURES,
    SERVICE_TURN_OFF,
    STATE_OFF,
    STATE_ON,
)
from homeconnect_websocket.message import Action, Message

from . import setup_config_entry
from .const import CONFIG_ENTRIES

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeconnect_websocket.testutils import MockAppliance


async def test_setup(
    hass: HomeAssistant,
    mock_appliance: MockAppliance,
    patch_entity_description: None,
) -> None:
    """Test setting up entity."""
    assert await setup_config_entry(hass, CONFIG_ENTRIES[0])

    state = hass.states.get("fan.fake_brand_homeappliance_fan")
    assert state
    assert state.name == "Fake_brand HomeAppliance Fan"
    assert state.attributes[ATTR_FRIENDLY_NAME] == "Fake_brand HomeAppliance Fan"
    assert (
        state.attributes[ATTR_SUPPORTED_FEATURES]
        == FanEntityFeature.SET_SPEED | FanEntityFeature.TURN_OFF
    )
    assert state.attributes[ATTR_PERCENTAGE_STEP] == 25


async def test_update(
    hass: HomeAssistant,
    mock_appliance: MockAppliance,
    patch_entity_description: None,
) -> None:
    """Test updating entity."""
    assert await setup_config_entry(hass, CONFIG_ENTRIES[0])

    state = hass.states.get("fan.fake_brand_homeappliance_fan")
    assert state.state == STATE_OFF

    await mock_appliance.entities["Test.FanSpeed1"].update({"value": 1})
    await hass.async_block_till_done()

    state = hass.states.get("fan.fake_brand_homeappliance_fan")
    assert state.state == STATE_ON
    assert state.attributes[ATTR_PERCENTAGE] == 25

    await mock_appliance.entities["Test.FanSpeed1"].update({"value": 2})
    await hass.async_block_till_done()

    state = hass.states.get("fan.fake_brand_homeappliance_fan")
    assert state.state == STATE_ON
    assert state.attributes[ATTR_PERCENTAGE] == 50

    await mock_appliance.entities["Test.FanSpeed1"].update({"value": 0})
    await mock_appliance.entities["Test.FanSpeed2"].update({"value": 1})
    await hass.async_block_till_done()

    state = hass.states.get("fan.fake_brand_homeappliance_fan")
    assert state.state == STATE_ON
    assert state.attributes[ATTR_PERCENTAGE] == 75

    await mock_appliance.entities["Test.FanSpeed1"].update({"value": 0})
    await mock_appliance.entities["Test.FanSpeed2"].update({"value": 2})
    await hass.async_block_till_done()

    state = hass.states.get("fan.fake_brand_homeappliance_fan")
    assert state.state == STATE_ON
    assert state.attributes[ATTR_PERCENTAGE] == 100


async def test_set_speed(
    hass: HomeAssistant,
    mock_appliance: MockAppliance,
    patch_entity_description: None,
) -> None:
    """Test setting a speed."""
    assert await setup_config_entry(hass, CONFIG_ENTRIES[0])

    await hass.services.async_call(
        FAN_DOMAIN,
        SERVICE_SET_PERCENTAGE,
        {
            ATTR_ENTITY_ID: "fan.fake_brand_homeappliance_fan",
            ATTR_PERCENTAGE: 25,
        },
        blocking=True,
    )

    mock_appliance.session.send_sync.assert_awaited_once_with(
        Message(
            resource="/ro/values",
            action=Action.POST,
            data=[{"uid": 403, "value": 1}, {"uid": 404, "value": 0}],
        )
    )
    mock_appliance.session.send_sync.reset_mock()

    await hass.services.async_call(
        FAN_DOMAIN,
        SERVICE_SET_PERCENTAGE,
        {
            ATTR_ENTITY_ID: "fan.fake_brand_homeappliance_fan",
            ATTR_PERCENTAGE: 75,
        },
        blocking=True,
    )

    mock_appliance.session.send_sync.assert_awaited_once_with(
        Message(
            resource="/ro/values",
            action=Action.POST,
            data=[{"uid": 403, "value": 0}, {"uid": 404, "value": 1}],
        )
    )


async def test_turn_off(
    hass: HomeAssistant,
    mock_appliance: MockAppliance,
    patch_entity_description: None,
) -> None:
    """Test turning off a fan without Program."""
    assert await setup_config_entry(hass, CONFIG_ENTRIES[0])

    await hass.services.async_call(
        FAN_DOMAIN,
        SERVICE_TURN_OFF,
        {ATTR_ENTITY_ID: "fan.fake_brand_homeappliance_fan"},
        blocking=True,
    )

    mock_appliance.session.send_sync.assert_awaited_once_with(
        Message(
            resource="/ro/values",
            action=Action.POST,
            data=[{"uid": 403, "value": 0}, {"uid": 404, "value": 0}],
        )
    )


async def test_set_speed_program(
    hass: HomeAssistant,
    mock_appliance: MockAppliance,
    patch_entity_description: None,
) -> None:
    """Test setting a speed when the speed entities are Program options."""
    assert await setup_config_entry(hass, CONFIG_ENTRIES[0])

    # No active Program: start the fan Program with the new speed
    await hass.services.async_call(
        FAN_DOMAIN,
        SERVICE_SET_PERCENTAGE,
        {ATTR_ENTITY_ID: "fan.fake_brand_homeappliance_fan_program", ATTR_PERCENTAGE: 25},
        blocking=True,
    )
    mock_appliance.session.send_sync.assert_awaited_once_with(
        Message(
            resource="/ro/activeProgram",
            action=Action.POST,
            data={
                "program": 504,
                "options": [{"uid": 403, "value": 1}, {"uid": 404, "value": 0}],
            },
        )
    )
    mock_appliance.session.send_sync.reset_mock()

    # Fan Program active: change options of the active Program
    await mock_appliance.entities["Test.ActiveProgram"].update({"value": 504})
    await mock_appliance.entities["Test.FanSpeed1"].update({"value": 1})
    await hass.async_block_till_done()
    assert (
        hass.states.get("fan.fake_brand_homeappliance_fan_program").attributes[ATTR_PERCENTAGE]
        == 25
    )

    await hass.services.async_call(
        FAN_DOMAIN,
        SERVICE_SET_PERCENTAGE,
        {ATTR_ENTITY_ID: "fan.fake_brand_homeappliance_fan_program", ATTR_PERCENTAGE: 75},
        blocking=True,
    )
    mock_appliance.session.send_sync.assert_awaited_once_with(
        Message(
            resource="/ro/activeProgram",
            action=Action.POST,
            data={
                "program": 504,
                "options": [{"uid": 403, "value": 0}, {"uid": 404, "value": 1}],
            },
        )
    )
    mock_appliance.session.send_sync.reset_mock()

    # Program ended: fan is off although the options keep their value
    await mock_appliance.entities["Test.ActiveProgram"].update({"value": 0})
    await hass.async_block_till_done()
    state = hass.states.get("fan.fake_brand_homeappliance_fan_program")
    assert state.state == STATE_OFF
    assert state.attributes[ATTR_PERCENTAGE] == 0
    mock_appliance.session.send_sync.reset_mock()

    # Other Program without the speed options active: start the fan Program
    await mock_appliance.entities["Test.ActiveProgram"].update({"value": 500})
    await hass.async_block_till_done()

    await hass.services.async_call(
        FAN_DOMAIN,
        SERVICE_SET_PERCENTAGE,
        {ATTR_ENTITY_ID: "fan.fake_brand_homeappliance_fan_program", ATTR_PERCENTAGE: 50},
        blocking=True,
    )
    mock_appliance.session.send_sync.assert_awaited_once_with(
        Message(
            resource="/ro/activeProgram",
            action=Action.POST,
            data={
                "program": 504,
                "options": [{"uid": 403, "value": 2}, {"uid": 404, "value": 0}],
            },
        )
    )


async def test_turn_off_program(
    hass: HomeAssistant,
    mock_appliance: MockAppliance,
    patch_entity_description: None,
) -> None:
    """Test turning off a fan when the speed entities are Program options."""
    assert await setup_config_entry(hass, CONFIG_ENTRIES[0])
    await mock_appliance.entities["Test.ActiveProgram"].update({"value": 504})
    await hass.async_block_till_done()

    # No AbortProgram command: power off
    await hass.services.async_call(
        FAN_DOMAIN,
        SERVICE_TURN_OFF,
        {ATTR_ENTITY_ID: "fan.fake_brand_homeappliance_fan_program"},
        blocking=True,
    )
    mock_appliance.session.send_sync.assert_awaited_once_with(
        Message(resource="/ro/values", action=Action.POST, data={"uid": 539, "value": 1})
    )
    mock_appliance.session.send_sync.reset_mock()

    # Percentage 0 turns off too
    await hass.services.async_call(
        FAN_DOMAIN,
        SERVICE_SET_PERCENTAGE,
        {ATTR_ENTITY_ID: "fan.fake_brand_homeappliance_fan_program", ATTR_PERCENTAGE: 0},
        blocking=True,
    )
    mock_appliance.session.send_sync.assert_awaited_once_with(
        Message(resource="/ro/values", action=Action.POST, data={"uid": 539, "value": 1})
    )
    mock_appliance.session.send_sync.reset_mock()

    # AbortProgram command available: abort the active Program
    mock_appliance.commands["BSH.Common.Command.AbortProgram"] = mock_appliance.commands[
        "Test.AbortProgram"
    ]
    await hass.services.async_call(
        FAN_DOMAIN,
        SERVICE_TURN_OFF,
        {ATTR_ENTITY_ID: "fan.fake_brand_homeappliance_fan_program"},
        blocking=True,
    )
    mock_appliance.session.send_sync.assert_awaited_once_with(
        Message(resource="/ro/values", action=Action.POST, data={"uid": 300, "value": True})
    )
