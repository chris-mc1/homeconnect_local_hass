"""Tests for number entity."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.number import (
    ATTR_MAX,
    ATTR_MIN,
    ATTR_STEP,
    ATTR_VALUE,
    SERVICE_SET_VALUE,
)
from homeassistant.components.number import DOMAIN as NUMBER_DOMAIN
from homeassistant.const import ATTR_ENTITY_ID, ATTR_FRIENDLY_NAME
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

    state = hass.states.get("number.fake_brand_homeappliance_number")
    assert state
    assert state.name == "Fake_brand HomeAppliance Number"
    assert state.attributes[ATTR_FRIENDLY_NAME] == "Fake_brand HomeAppliance Number"
    assert state.attributes[ATTR_MIN] == 0
    assert state.attributes[ATTR_MAX] == 20
    assert state.attributes[ATTR_STEP] == 2


async def test_update(
    hass: HomeAssistant,
    mock_appliance: MockAppliance,
    patch_entity_description: None,
) -> None:
    """Test updating entity."""
    entity_id = "number.fake_brand_homeappliance_number"
    assert await setup_config_entry(hass, CONFIG_ENTRIES[0])

    await mock_appliance.entities["Test.Number"].update({"value": 0})
    await hass.async_block_till_done()

    state = hass.states.get(entity_id)
    assert state
    assert state.state == "0"

    await mock_appliance.entities["Test.Number"].update({"value": 10})
    await hass.async_block_till_done()

    state = hass.states.get(entity_id)
    assert state.state == "10"

    await mock_appliance.entities["Test.Number"].update({"min": 10, "max": 50, "stepSize": 5})
    await hass.async_block_till_done()

    state = hass.states.get(entity_id)
    assert state.attributes[ATTR_MIN] == 10
    assert state.attributes[ATTR_MAX] == 50
    assert state.attributes[ATTR_STEP] == 5


async def test_set_value(
    hass: HomeAssistant,
    mock_appliance: MockAppliance,
    patch_entity_description: None,
) -> None:
    """Test setting a value."""
    entity_id = "number.fake_brand_homeappliance_number"
    assert await setup_config_entry(hass, CONFIG_ENTRIES[0])

    await hass.services.async_call(
        NUMBER_DOMAIN,
        SERVICE_SET_VALUE,
        {ATTR_ENTITY_ID: entity_id, ATTR_VALUE: "2"},
        blocking=True,
    )
    mock_appliance.session.send_sync.assert_awaited_once_with(
        Message(
            resource="/ro/values",
            action=Action.POST,
            data={"uid": 204, "value": 2},
        )
    )
