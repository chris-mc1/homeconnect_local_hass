"""Tests for light entity."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_BRIGHTNESS_PCT,
    ATTR_COLOR_MODE,
    ATTR_COLOR_TEMP_KELVIN,
    ATTR_RGB_COLOR,
    ATTR_SUPPORTED_COLOR_MODES,
    SERVICE_TURN_ON,
    ColorMode,
)
from homeassistant.components.light import (
    DOMAIN as LIGHT_DOMAIN,
)
from homeassistant.components.light.const import DEFAULT_MAX_KELVIN, DEFAULT_MIN_KELVIN
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
    await mock_appliance.entities["Test.Lighting"].update({"value": True})
    await hass.async_block_till_done()

    state = hass.states.get("light.fake_brand_homeappliance_light_1")
    assert state
    assert state.name == "Fake_brand HomeAppliance Light.1"
    assert state.attributes[ATTR_FRIENDLY_NAME] == "Fake_brand HomeAppliance Light.1"
    assert state.attributes[ATTR_COLOR_MODE] == ColorMode.ONOFF
    assert state.attributes[ATTR_SUPPORTED_COLOR_MODES] == [ColorMode.ONOFF]

    state = hass.states.get("light.fake_brand_homeappliance_light_2")
    assert state
    assert state.name == "Fake_brand HomeAppliance Light.2"
    assert state.attributes[ATTR_FRIENDLY_NAME] == "Fake_brand HomeAppliance Light.2"
    assert state.attributes[ATTR_COLOR_MODE] == ColorMode.BRIGHTNESS
    assert state.attributes[ATTR_SUPPORTED_COLOR_MODES] == [ColorMode.BRIGHTNESS]

    state = hass.states.get("light.fake_brand_homeappliance_light_3")
    assert state
    assert state.name == "Fake_brand HomeAppliance Light.3"
    assert state.attributes[ATTR_FRIENDLY_NAME] == "Fake_brand HomeAppliance Light.3"
    assert state.attributes[ATTR_COLOR_MODE] == ColorMode.COLOR_TEMP
    assert state.attributes[ATTR_SUPPORTED_COLOR_MODES] == [ColorMode.COLOR_TEMP]

    state = hass.states.get("light.fake_brand_homeappliance_light_4")
    assert state
    assert state.name == "Fake_brand HomeAppliance Light.4"
    assert state.attributes[ATTR_FRIENDLY_NAME] == "Fake_brand HomeAppliance Light.4"
    assert state.attributes[ATTR_COLOR_MODE] == ColorMode.RGB
    assert state.attributes[ATTR_SUPPORTED_COLOR_MODES] == [ColorMode.RGB]


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
    await hass.async_block_till_done()

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
            data=[{"uid": 108, "value": True}],
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
    mock_appliance.session.send_sync.assert_awaited_once_with(
        Message(
            resource="/ro/values",
            action=Action.POST,
            data=[{"uid": 109, "value": 100}],
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

    mock_appliance.session.send_sync.assert_awaited_once_with(
        Message(
            resource="/ro/values",
            action=Action.POST,
            data=[{"uid": 109, "value": 50}],
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

    mock_appliance.session.send_sync.assert_awaited_once_with(
        Message(
            resource="/ro/values",
            action=Action.POST,
            data=[{"uid": 109, "value": 2}],
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

    mock_appliance.session.send_sync.assert_awaited_once_with(
        Message(
            resource="/ro/values",
            action=Action.POST,
            data=[{"uid": 109, "value": 2}],
        )
    )
    mock_appliance.session.send_sync.reset_mock()


async def test_update_color_temp(
    hass: HomeAssistant,
    mock_appliance: MockAppliance,
    patch_entity_description: None,  # noqa: ARG001
) -> None:
    """Test Color temp."""
    mock_appliance.entities.pop("Cooking.Hood.Setting.ColorTemperature")
    assert await setup_config_entry(hass, MOCK_CONFIG_DATA, mock_appliance)
    await mock_appliance.entities["Test.Lighting"].update({"value": True})
    await mock_appliance.entities["Test.LightingBrightness"].update({"value": 100})
    await mock_appliance.entities["Test.LightingColorTempPercent"].update({"value": 100})
    await hass.async_block_till_done()

    state = hass.states.get("light.fake_brand_homeappliance_light_3")
    assert state.state == STATE_ON
    assert state.attributes[ATTR_BRIGHTNESS] == 255  # 100%
    assert state.attributes[ATTR_COLOR_TEMP_KELVIN] == DEFAULT_MAX_KELVIN  # 100%

    await mock_appliance.entities["Test.LightingColorTempPercent"].update({"value": 0})
    await hass.async_block_till_done()

    state = hass.states.get("light.fake_brand_homeappliance_light_3")
    assert state.attributes[ATTR_COLOR_TEMP_KELVIN] == DEFAULT_MIN_KELVIN  # 0%

    await mock_appliance.entities["Test.LightingColorTempPercent"].update({"value": 50})
    await hass.async_block_till_done()

    state = hass.states.get("light.fake_brand_homeappliance_light_3")
    assert state.attributes[ATTR_COLOR_TEMP_KELVIN] == 4267  # 50%


async def test_set_color_temp(
    hass: HomeAssistant,
    mock_appliance: MockAppliance,
    patch_entity_description: None,  # noqa: ARG001
) -> None:
    """Test Color temp."""
    mock_appliance.entities.pop("Cooking.Hood.Setting.ColorTemperature")
    assert await setup_config_entry(hass, MOCK_CONFIG_DATA, mock_appliance)
    await mock_appliance.entities["Test.Lighting"].update({"value": True})
    await mock_appliance.entities["Test.LightingBrightness"].update({"value": 100})
    await mock_appliance.entities["Test.LightingColorTempPercent"].update({"value": 0})
    await hass.async_block_till_done()

    await hass.services.async_call(
        LIGHT_DOMAIN,
        SERVICE_TURN_ON,
        {
            ATTR_ENTITY_ID: "light.fake_brand_homeappliance_light_3",
            ATTR_COLOR_TEMP_KELVIN: DEFAULT_MAX_KELVIN,
        },
        blocking=True,
    )
    mock_appliance.session.send_sync.assert_awaited_once_with(
        Message(
            resource="/ro/values",
            action=Action.POST,
            data=[{"uid": 110, "value": 100}],
        )
    )
    mock_appliance.session.send_sync.reset_mock()

    await hass.services.async_call(
        LIGHT_DOMAIN,
        SERVICE_TURN_ON,
        {
            ATTR_ENTITY_ID: "light.fake_brand_homeappliance_light_3",
            ATTR_COLOR_TEMP_KELVIN: DEFAULT_MIN_KELVIN,
        },
        blocking=True,
    )

    mock_appliance.session.send_sync.assert_awaited_once_with(
        Message(
            resource="/ro/values",
            action=Action.POST,
            data=[{"uid": 110, "value": 0}],
        )
    )
    mock_appliance.session.send_sync.reset_mock()

    await hass.services.async_call(
        LIGHT_DOMAIN,
        SERVICE_TURN_ON,
        {
            ATTR_ENTITY_ID: "light.fake_brand_homeappliance_light_3",
            ATTR_COLOR_TEMP_KELVIN: 4268,
        },
        blocking=True,
    )

    mock_appliance.session.send_sync.assert_awaited_once_with(
        Message(
            resource="/ro/values",
            action=Action.POST,
            data=[{"uid": 110, "value": 50}],
        )
    )
    mock_appliance.session.send_sync.reset_mock()


async def test_set_brightness_color_temp(
    hass: HomeAssistant,
    mock_appliance: MockAppliance,
    patch_entity_description: None,  # noqa: ARG001
) -> None:
    """Test Brightness and Color temp."""
    mock_appliance.entities.pop("Cooking.Hood.Setting.ColorTemperature")
    assert await setup_config_entry(hass, MOCK_CONFIG_DATA, mock_appliance)
    await mock_appliance.entities["Test.Lighting"].update({"value": False})
    await mock_appliance.entities["Test.LightingBrightness"].update({"value": 0})
    await mock_appliance.entities["Test.LightingColorTempPercent"].update({"value": 0})
    await hass.async_block_till_done()

    await hass.services.async_call(
        LIGHT_DOMAIN,
        SERVICE_TURN_ON,
        {
            ATTR_ENTITY_ID: "light.fake_brand_homeappliance_light_3",
            ATTR_BRIGHTNESS_PCT: 100,
            ATTR_COLOR_TEMP_KELVIN: DEFAULT_MAX_KELVIN,
        },
        blocking=True,
    )

    mock_appliance.session.send_sync.assert_awaited_once_with(
        Message(
            resource="/ro/values",
            action=Action.POST,
            data=[
                {"uid": 109, "value": 100},
                {"uid": 110, "value": 100},
                {"uid": 108, "value": True},
            ],
        )
    )
    mock_appliance.session.send_sync.reset_mock()

    await mock_appliance.entities["Test.Lighting"].update({"value": True})
    await mock_appliance.entities["Test.LightingBrightness"].update({"value": 100})
    await mock_appliance.entities["Test.LightingColorTempPercent"].update({"value": 100})
    await hass.async_block_till_done()

    await hass.services.async_call(
        LIGHT_DOMAIN,
        SERVICE_TURN_ON,
        {
            ATTR_ENTITY_ID: "light.fake_brand_homeappliance_light_3",
            ATTR_BRIGHTNESS_PCT: 2,
            ATTR_COLOR_TEMP_KELVIN: DEFAULT_MIN_KELVIN,
        },
        blocking=True,
    )

    mock_appliance.session.send_sync.assert_awaited_once_with(
        Message(
            resource="/ro/values",
            action=Action.POST,
            data=[
                {"uid": 109, "value": 2},
                {"uid": 110, "value": 0},
            ],
        )
    )


async def test_update_color_temp_inverted(
    hass: HomeAssistant,
    mock_appliance: MockAppliance,
    patch_entity_description: None,  # noqa: ARG001
) -> None:
    """Test Color temp."""
    assert await setup_config_entry(hass, MOCK_CONFIG_DATA, mock_appliance)
    await mock_appliance.entities["Test.Lighting"].update({"value": True})
    await mock_appliance.entities["Test.LightingBrightness"].update({"value": 100})
    await mock_appliance.entities["Test.LightingColorTempPercent"].update({"value": 0})
    await hass.async_block_till_done()

    state = hass.states.get("light.fake_brand_homeappliance_light_3")
    assert state.state == STATE_ON
    assert state.attributes[ATTR_BRIGHTNESS] == 255  # 100%
    assert state.attributes[ATTR_COLOR_TEMP_KELVIN] == DEFAULT_MAX_KELVIN  # 0%

    await mock_appliance.entities["Test.LightingColorTempPercent"].update({"value": 100})
    await hass.async_block_till_done()

    state = hass.states.get("light.fake_brand_homeappliance_light_3")
    assert state.attributes[ATTR_COLOR_TEMP_KELVIN] == DEFAULT_MIN_KELVIN  # 100%

    await mock_appliance.entities["Test.LightingColorTempPercent"].update({"value": 50})
    await hass.async_block_till_done()

    state = hass.states.get("light.fake_brand_homeappliance_light_3")
    assert state.attributes[ATTR_COLOR_TEMP_KELVIN] == 4267  # 50%


async def test_set_color_temp_inverted(
    hass: HomeAssistant,
    mock_appliance: MockAppliance,
    patch_entity_description: None,  # noqa: ARG001
) -> None:
    """Test Color temp."""
    assert await setup_config_entry(hass, MOCK_CONFIG_DATA, mock_appliance)
    await mock_appliance.entities["Test.Lighting"].update({"value": True})
    await mock_appliance.entities["Test.LightingBrightness"].update({"value": 100})
    await mock_appliance.entities["Test.LightingColorTempPercent"].update({"value": 100})
    await hass.async_block_till_done()

    await hass.services.async_call(
        LIGHT_DOMAIN,
        SERVICE_TURN_ON,
        {
            ATTR_ENTITY_ID: "light.fake_brand_homeappliance_light_3",
            ATTR_COLOR_TEMP_KELVIN: DEFAULT_MAX_KELVIN,
        },
        blocking=True,
    )
    mock_appliance.session.send_sync.assert_awaited_once_with(
        Message(
            resource="/ro/values",
            action=Action.POST,
            data=[{"uid": 110, "value": 0}],
        )
    )
    mock_appliance.session.send_sync.reset_mock()

    await hass.services.async_call(
        LIGHT_DOMAIN,
        SERVICE_TURN_ON,
        {
            ATTR_ENTITY_ID: "light.fake_brand_homeappliance_light_3",
            ATTR_COLOR_TEMP_KELVIN: DEFAULT_MIN_KELVIN,
        },
        blocking=True,
    )

    mock_appliance.session.send_sync.assert_awaited_once_with(
        Message(
            resource="/ro/values",
            action=Action.POST,
            data=[{"uid": 110, "value": 100}],
        )
    )
    mock_appliance.session.send_sync.reset_mock()

    await hass.services.async_call(
        LIGHT_DOMAIN,
        SERVICE_TURN_ON,
        {
            ATTR_ENTITY_ID: "light.fake_brand_homeappliance_light_3",
            ATTR_COLOR_TEMP_KELVIN: 4267,
        },
        blocking=True,
    )

    mock_appliance.session.send_sync.assert_awaited_once_with(
        Message(
            resource="/ro/values",
            action=Action.POST,
            data=[{"uid": 110, "value": 50}],
        )
    )
    mock_appliance.session.send_sync.reset_mock()


async def test_set_brightness_color_temp_inverted(
    hass: HomeAssistant,
    mock_appliance: MockAppliance,
    patch_entity_description: None,  # noqa: ARG001
) -> None:
    """Test Brightness and Color temp."""
    assert await setup_config_entry(hass, MOCK_CONFIG_DATA, mock_appliance)
    await mock_appliance.entities["Test.Lighting"].update({"value": False})
    await mock_appliance.entities["Test.LightingBrightness"].update({"value": 0})
    await mock_appliance.entities["Test.LightingColorTempPercent"].update({"value": 0})
    await hass.async_block_till_done()

    await hass.services.async_call(
        LIGHT_DOMAIN,
        SERVICE_TURN_ON,
        {
            ATTR_ENTITY_ID: "light.fake_brand_homeappliance_light_3",
            ATTR_BRIGHTNESS_PCT: 100,
            ATTR_COLOR_TEMP_KELVIN: DEFAULT_MAX_KELVIN,
        },
        blocking=True,
    )

    mock_appliance.session.send_sync.assert_awaited_once_with(
        Message(
            resource="/ro/values",
            action=Action.POST,
            data=[
                {"uid": 109, "value": 100},
                {"uid": 110, "value": 0},
                {"uid": 108, "value": True},
            ],
        )
    )
    mock_appliance.session.send_sync.reset_mock()

    await mock_appliance.entities["Test.Lighting"].update({"value": True})
    await mock_appliance.entities["Test.LightingBrightness"].update({"value": 100})
    await mock_appliance.entities["Test.LightingColorTempPercent"].update({"value": 0})
    await hass.async_block_till_done()

    await hass.services.async_call(
        LIGHT_DOMAIN,
        SERVICE_TURN_ON,
        {
            ATTR_ENTITY_ID: "light.fake_brand_homeappliance_light_3",
            ATTR_BRIGHTNESS_PCT: 2,
            ATTR_COLOR_TEMP_KELVIN: DEFAULT_MIN_KELVIN,
        },
        blocking=True,
    )

    mock_appliance.session.send_sync.assert_awaited_once_with(
        Message(
            resource="/ro/values",
            action=Action.POST,
            data=[
                {"uid": 109, "value": 2},
                {"uid": 110, "value": 100},
            ],
        )
    )


async def test_update_color(
    hass: HomeAssistant,
    mock_appliance: MockAppliance,
    patch_entity_description: None,  # noqa: ARG001
) -> None:
    """Test update RGB."""
    assert await setup_config_entry(hass, MOCK_CONFIG_DATA, mock_appliance)
    await mock_appliance.entities["Test.Lighting"].update({"value": True})
    await mock_appliance.entities["Test.LightingCustomColor"].update({"value": "#ff0000"})
    await mock_appliance.entities["Test.LightingColor"].update({"value": 1})
    await hass.async_block_till_done()

    state = hass.states.get("light.fake_brand_homeappliance_light_4")
    assert state.state == STATE_ON
    assert state.attributes[ATTR_BRIGHTNESS] == 255  # 100%
    assert state.attributes[ATTR_RGB_COLOR] == (255, 0, 0)

    await mock_appliance.entities["Test.LightingCustomColor"].update({"value": "#7f0000"})
    await hass.async_block_till_done()

    state = hass.states.get("light.fake_brand_homeappliance_light_4")
    assert state.state == STATE_ON
    assert state.attributes[ATTR_BRIGHTNESS] == 127  # 100%
    assert state.attributes[ATTR_RGB_COLOR] == (255, 0, 0)


async def test_set_color(
    hass: HomeAssistant,
    mock_appliance: MockAppliance,
    patch_entity_description: None,  # noqa: ARG001
) -> None:
    """Test set RGB."""
    assert await setup_config_entry(hass, MOCK_CONFIG_DATA, mock_appliance)
    await mock_appliance.entities["Test.Lighting"].update({"value": True})
    await mock_appliance.entities["Test.LightingCustomColor"].update({"value": "#ff0000"})
    await mock_appliance.entities["Test.LightingColor"].update({"value": 1})
    await hass.async_block_till_done()

    await hass.services.async_call(
        LIGHT_DOMAIN,
        SERVICE_TURN_ON,
        {
            ATTR_ENTITY_ID: "light.fake_brand_homeappliance_light_4",
            ATTR_BRIGHTNESS: 127,
        },
        blocking=True,
    )
    mock_appliance.session.send_sync.assert_awaited_once_with(
        Message(
            resource="/ro/values",
            action=Action.POST,
            data=[{"uid": 111, "value": "#7f0000"}],
        )
    )
    mock_appliance.session.send_sync.reset_mock()

    await hass.services.async_call(
        LIGHT_DOMAIN,
        SERVICE_TURN_ON,
        {
            ATTR_ENTITY_ID: "light.fake_brand_homeappliance_light_4",
            ATTR_RGB_COLOR: (0, 255, 0),
        },
        blocking=True,
    )

    mock_appliance.session.send_sync.assert_awaited_once_with(
        Message(
            resource="/ro/values",
            action=Action.POST,
            data=[{"uid": 111, "value": "#00ff00"}],
        )
    )
    mock_appliance.session.send_sync.reset_mock()

    await hass.services.async_call(
        LIGHT_DOMAIN,
        SERVICE_TURN_ON,
        {
            ATTR_ENTITY_ID: "light.fake_brand_homeappliance_light_4",
            ATTR_RGB_COLOR: (0, 255, 0),
            ATTR_BRIGHTNESS_PCT: 50,
        },
        blocking=True,
    )

    mock_appliance.session.send_sync.assert_awaited_once_with(
        Message(
            resource="/ro/values",
            action=Action.POST,
            data=[{"uid": 111, "value": "#008000"}],
        )
    )
    mock_appliance.session.send_sync.reset_mock()

    await mock_appliance.entities["Test.LightingCustomColor"].update({"value": "#800000"})
    await hass.async_block_till_done()

    await hass.services.async_call(
        LIGHT_DOMAIN,
        SERVICE_TURN_ON,
        {
            ATTR_ENTITY_ID: "light.fake_brand_homeappliance_light_4",
            ATTR_RGB_COLOR: (0, 0, 255),
        },
        blocking=True,
    )

    mock_appliance.session.send_sync.assert_awaited_once_with(
        Message(
            resource="/ro/values",
            action=Action.POST,
            data=[{"uid": 111, "value": "#000080"}],
        )
    )
    mock_appliance.session.send_sync.reset_mock()

    await mock_appliance.entities["Test.LightingColor"].update({"value": 33})
    await hass.async_block_till_done()

    await hass.services.async_call(
        LIGHT_DOMAIN,
        SERVICE_TURN_ON,
        {
            ATTR_ENTITY_ID: "light.fake_brand_homeappliance_light_4",
            ATTR_BRIGHTNESS_PCT: 50,
        },
        blocking=True,
    )
    mock_appliance.session.send_sync.assert_awaited_once_with(
        Message(
            resource="/ro/values",
            action=Action.POST,
            data=[{"uid": 111, "value": "#800000"}, {"uid": 112, "value": 1}],
        )
    )
    mock_appliance.session.send_sync.reset_mock()
