"""Tests for light entity."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_BRIGHTNESS_PCT,
    ATTR_SUPPORTED_COLOR_MODES,
    SERVICE_TURN_ON,
    ColorMode,
)
from homeassistant.components.light import (
    DOMAIN as LIGHT_DOMAIN,
)
from homeassistant.const import (
    ATTR_ENTITY_ID,
    ATTR_FRIENDLY_NAME,
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

    state = hass.states.get("light.fake_brand_homeappliance_light_1")
    assert state
    assert state.name == "Fake_brand HomeAppliance Light.1"
    assert state.attributes[ATTR_FRIENDLY_NAME] == "Fake_brand HomeAppliance Light.1"
    assert state.attributes[ATTR_SUPPORTED_COLOR_MODES] == [ColorMode.ONOFF]

    state = hass.states.get("light.fake_brand_homeappliance_light_2")
    assert state
    assert state.name == "Fake_brand HomeAppliance Light.2"
    assert state.attributes[ATTR_FRIENDLY_NAME] == "Fake_brand HomeAppliance Light.2"
    assert state.attributes[ATTR_SUPPORTED_COLOR_MODES] == [ColorMode.BRIGHTNESS]


async def test_update_on_off(
    hass: HomeAssistant,
    mock_appliance: MockAppliance,
    patch_entity_description: None,  # noqa: ARG001
) -> None:
    """Test On/Off."""
    assert await setup_config_entry(hass, MOCK_CONFIG_DATA, mock_appliance)

    await mock_appliance.entities["Test.Lighting"].update({"value": True})
    await hass.async_block_till_done()

    state = hass.states.get("light.fake_brand_homeappliance_light_1")
    assert state.state == STATE_ON

    await mock_appliance.entities["Test.Lighting"].update({"value": False})
    await hass.async_block_till_done()

    state = hass.states.get("light.fake_brand_homeappliance_light_1")
    assert state.state == STATE_OFF


async def test_on(
    hass: HomeAssistant,
    mock_appliance: MockAppliance,
    patch_entity_description: None,  # noqa: ARG001
) -> None:
    """Test Set On/Off."""
    assert await setup_config_entry(hass, MOCK_CONFIG_DATA, mock_appliance)

    await mock_appliance.entities["Test.Lighting"].update({"value": False})

    await hass.services.async_call(
        LIGHT_DOMAIN,
        SERVICE_TURN_ON,
        {
            ATTR_ENTITY_ID: "light.fake_brand_homeappliance_light_1",
        },
        blocking=True,
    )

    mock_appliance.session.send_sync.assert_awaited_once_with(
        Message(
            resource="/ro/values",
            action=Action.POST,
            data={"uid": 108, "value": True},
        )
    )
    mock_appliance.session.send_sync.reset_mock()


async def test_update_brightness(
    hass: HomeAssistant,
    mock_appliance: MockAppliance,
    patch_entity_description: None,  # noqa: ARG001
) -> None:
    """Test Brightness."""
    assert await setup_config_entry(hass, MOCK_CONFIG_DATA, mock_appliance)
    await mock_appliance.entities["Test.Lighting"].update({"value": True})
    await mock_appliance.entities["Test.LightingBrightness"].update({"value": 100})
    await hass.async_block_till_done()

    state = hass.states.get("light.fake_brand_homeappliance_light_2")
    assert state.state == STATE_ON
    assert state.attributes[ATTR_BRIGHTNESS] == 255  # 100%

    await mock_appliance.entities["Test.LightingBrightness"].update({"value": 2})
    await hass.async_block_till_done()

    state = hass.states.get("light.fake_brand_homeappliance_light_2")
    assert state.attributes[ATTR_BRIGHTNESS] == 5  # 2%

    await mock_appliance.entities["Test.LightingBrightness"].update({"value": 50})
    await hass.async_block_till_done()

    state = hass.states.get("light.fake_brand_homeappliance_light_2")
    assert state.attributes[ATTR_BRIGHTNESS] == 128  # 50%

    await mock_appliance.entities["Test.LightingBrightness"].update({"value": 3})
    await hass.async_block_till_done()

    state = hass.states.get("light.fake_brand_homeappliance_light_2")
    assert state.attributes[ATTR_BRIGHTNESS] == 8  # 3%


async def test_set_brightness(
    hass: HomeAssistant,
    mock_appliance: MockAppliance,
    patch_entity_description: None,  # noqa: ARG001
) -> None:
    """Test Brightness."""
    assert await setup_config_entry(hass, MOCK_CONFIG_DATA, mock_appliance)
    await mock_appliance.entities["Test.Lighting"].update({"value": True})
    await mock_appliance.entities["Test.LightingBrightness"].update({"value": 2})
    await hass.async_block_till_done()

    await hass.services.async_call(
        LIGHT_DOMAIN,
        SERVICE_TURN_ON,
        {
            ATTR_ENTITY_ID: "light.fake_brand_homeappliance_light_2",
            ATTR_BRIGHTNESS_PCT: 100,
        },
        blocking=True,
    )
    mock_appliance.session.send_sync.assert_any_await(
        Message(
            resource="/ro/values",
            action=Action.POST,
            data={"uid": 109, "value": 100},
        )
    )
    mock_appliance.session.send_sync.reset_mock()

    await hass.services.async_call(
        LIGHT_DOMAIN,
        SERVICE_TURN_ON,
        {
            ATTR_ENTITY_ID: "light.fake_brand_homeappliance_light_2",
            ATTR_BRIGHTNESS_PCT: 50,
        },
        blocking=True,
    )

    mock_appliance.session.send_sync.assert_any_await(
        Message(
            resource="/ro/values",
            action=Action.POST,
            data={"uid": 109, "value": 50},
        )
    )
    mock_appliance.session.send_sync.reset_mock()

    await hass.services.async_call(
        LIGHT_DOMAIN,
        SERVICE_TURN_ON,
        {
            ATTR_ENTITY_ID: "light.fake_brand_homeappliance_light_2",
            ATTR_BRIGHTNESS_PCT: 2,
        },
        blocking=True,
    )

    mock_appliance.session.send_sync.assert_any_await(
        Message(
            resource="/ro/values",
            action=Action.POST,
            data={"uid": 109, "value": 2},
        )
    )
    mock_appliance.session.send_sync.reset_mock()

    await hass.services.async_call(
        LIGHT_DOMAIN,
        SERVICE_TURN_ON,
        {
            ATTR_ENTITY_ID: "light.fake_brand_homeappliance_light_2",
            ATTR_BRIGHTNESS_PCT: 1,
        },
        blocking=True,
    )

    mock_appliance.session.send_sync.assert_any_await(
        Message(
            resource="/ro/values",
            action=Action.POST,
            data={"uid": 109, "value": 2},
        )
    )
    mock_appliance.session.send_sync.reset_mock()
