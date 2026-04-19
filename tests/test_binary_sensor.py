"""Tests for binary sensor entity."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.const import ATTR_FRIENDLY_NAME, STATE_OFF, STATE_ON, STATE_UNKNOWN

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

    state = hass.states.get("binary_sensor.fake_brand_homeappliance_binarysensor")
    assert state
    assert state.state == STATE_OFF
    assert state.name == "Fake_brand HomeAppliance BinarySensor"
    assert state.attributes[ATTR_FRIENDLY_NAME] == "Fake_brand HomeAppliance BinarySensor"

    state = hass.states.get("binary_sensor.fake_brand_homeappliance_binarysensor_enum")
    assert state
    assert state.state == STATE_UNKNOWN
    assert state.name == "Fake_brand HomeAppliance BinarySensor.Enum"
    assert state.attributes[ATTR_FRIENDLY_NAME] == "Fake_brand HomeAppliance BinarySensor.Enum"


async def test_update(
    hass: HomeAssistant,
    mock_appliance: MockAppliance,
    patch_entity_description: None,  # noqa: ARG001
) -> None:
    """Test updating entity."""
    entity_id = "binary_sensor.fake_brand_homeappliance_binarysensor"
    assert await setup_config_entry(hass, MOCK_CONFIG_DATA)

    await mock_appliance.entities["Test.BinarySensor"].update({"value": True})
    await hass.async_block_till_done()

    state = hass.states.get(entity_id)
    assert state.state == STATE_ON

    await mock_appliance.entities["Test.BinarySensor"].update({"value": False})
    await hass.async_block_till_done()

    state = hass.states.get(entity_id)
    assert state.state == STATE_OFF


async def test_update_enum(
    hass: HomeAssistant,
    mock_appliance: MockAppliance,
    patch_entity_description: None,  # noqa: ARG001
) -> None:
    """Test updating entity with enum."""
    entity_id = "binary_sensor.fake_brand_homeappliance_binarysensor_enum"
    assert await setup_config_entry(hass, MOCK_CONFIG_DATA)

    await mock_appliance.entities["Test.BinarySensor.Enum"].update({"value": 0})
    await hass.async_block_till_done()

    state = hass.states.get(entity_id)
    assert state.state == STATE_OFF

    await mock_appliance.entities["Test.BinarySensor.Enum"].update({"value": 1})
    await hass.async_block_till_done()

    state = hass.states.get(entity_id)
    assert state.state == STATE_ON
