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
    mock_appliance: MockAppliance,
    patch_entity_description: None,  # noqa: ARG001
) -> None:
    """Test setting up entity."""
    assert await setup_config_entry(hass, MOCK_CONFIG_DATA, mock_appliance)

    state = hass.states.get("fan.fake_brand_homeappliance_fan")
    assert state
    assert state.name == "Fake_brand HomeAppliance Fan"
    assert state.attributes[ATTR_FRIENDLY_NAME] == "Fake_brand HomeAppliance Fan"
    assert state.attributes[ATTR_SUPPORTED_FEATURES] == FanEntityFeature.SET_SPEED
    assert state.attributes[ATTR_PERCENTAGE_STEP] == 25


async def test_update(
    hass: HomeAssistant,
    mock_appliance: MockAppliance,
    patch_entity_description: None,  # noqa: ARG001
) -> None:
    """Test updating entity."""
    assert await setup_config_entry(hass, MOCK_CONFIG_DATA, mock_appliance)

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
    patch_entity_description: None,  # noqa: ARG001
) -> None:
    """Test setting a speed."""
    assert await setup_config_entry(hass, MOCK_CONFIG_DATA, mock_appliance)

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
