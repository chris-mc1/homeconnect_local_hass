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
    SERVICE_TURN_ON,
    STATE_OFF,
    STATE_ON,
)
from homeconnect_websocket.message import Action, Message

from . import setup_config_entry
from .const import MOCK_CONFIG_DATA

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeconnect_websocket.testutils import MockAppliance


async def test_setup(
    hass: HomeAssistant,
    mock_appliance: MockAppliance,  # noqa: ARG001
    patch_entity_description: None,  # noqa: ARG001
) -> None:
    """Test setting up entity."""
    assert await setup_config_entry(hass, MOCK_CONFIG_DATA)

    state = hass.states.get("fan.fake_brand_homeappliance_fan")
    assert state
    assert state.name == "Fake_brand HomeAppliance Fan"
    assert state.attributes[ATTR_FRIENDLY_NAME] == "Fake_brand HomeAppliance Fan"
    assert (
        state.attributes[ATTR_SUPPORTED_FEATURES]
        == FanEntityFeature.SET_SPEED | FanEntityFeature.TURN_OFF | FanEntityFeature.TURN_ON
    )
    assert state.attributes[ATTR_PERCENTAGE_STEP] == 25


async def test_update(
    hass: HomeAssistant,
    mock_appliance: MockAppliance,
    patch_entity_description: None,  # noqa: ARG001
) -> None:
    """Test updating entity."""
    assert await setup_config_entry(hass, MOCK_CONFIG_DATA)
    await mock_appliance.entities["Test.ActiveProgram"].update({"value": 0})
    await hass.async_block_till_done()

    state = hass.states.get("fan.fake_brand_homeappliance_fan")
    assert state.state == STATE_OFF

    await mock_appliance.entities["Test.ActiveProgram"].update({"value": 504})
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


async def test_turn_on(
    hass: HomeAssistant,
    mock_appliance: MockAppliance,
    patch_entity_description: None,  # noqa: ARG001
) -> None:
    """Test turning on."""
    assert await setup_config_entry(hass, MOCK_CONFIG_DATA, mock_appliance)
    await mock_appliance.entities["Test.ActiveProgram"].update({"value": 0})
    await hass.async_block_till_done()

    await hass.services.async_call(
        FAN_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: "fan.fake_brand_homeappliance_fan"},
        blocking=True,
    )

    mock_appliance.session.send_sync.assert_awaited_once_with(
        Message(
            resource="/ro/activeProgram",
            action=Action.POST,
            data={
                "program": 504,
                "options": [],
            },
        )
    )


async def test_turn_off(
    hass: HomeAssistant,
    mock_appliance: MockAppliance,
    patch_entity_description: None,  # noqa: ARG001
) -> None:
    """Test turning off."""
    assert await setup_config_entry(hass, MOCK_CONFIG_DATA, mock_appliance)
    await mock_appliance.entities["Test.ActiveProgram"].update({"value": 504})
    await hass.async_block_till_done()

    await hass.services.async_call(
        FAN_DOMAIN,
        SERVICE_TURN_OFF,
        {ATTR_ENTITY_ID: "fan.fake_brand_homeappliance_fan"},
        blocking=True,
    )

    mock_appliance.session.send_sync.assert_awaited_once_with(
        Message(
            resource="/ro/activeProgram",
            action=Action.POST,
            data=[
                {
                    "program": 0,
                    "options": [],
                }
            ],
        )
    )


async def test_set_speed(
    hass: HomeAssistant,
    mock_appliance: MockAppliance,
    patch_entity_description: None,  # noqa: ARG001
) -> None:
    """Test setting a speed."""
    assert await setup_config_entry(hass, MOCK_CONFIG_DATA)
    await mock_appliance.entities["Test.ActiveProgram"].update({"value": 0})
    await mock_appliance.entities["Test.Option1"].update({"value": True})
    await hass.async_block_till_done()

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
            resource="/ro/activeProgram",
            action=Action.POST,
            data={
                "program": 504,
                "options": [
                    {"uid": 403, "value": 1},
                    {"uid": 404, "value": 0},
                    {"uid": 401, "value": True},
                ],
            },
        )
    )
    mock_appliance.session.send_sync.reset_mock()

    await mock_appliance.entities["Test.ActiveProgram"].update({"value": 505})
    await hass.async_block_till_done()

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
            resource="/ro/activeProgram",
            action=Action.POST,
            data={
                "program": 505,
                "options": [
                    {"uid": 403, "value": 0},
                    {"uid": 404, "value": 1},
                    {"uid": 401, "value": True},
                ],
            },
        )
    )
