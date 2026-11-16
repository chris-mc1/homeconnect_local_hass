"""Tests for button entity."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from homeassistant.components.button import DOMAIN as BUTTON_DOMAIN
from homeassistant.components.button import SERVICE_PRESS
from homeassistant.const import ATTR_ENTITY_ID, ATTR_FRIENDLY_NAME, STATE_UNAVAILABLE
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

    state = hass.states.get("button.fake_brand_homeappliance_activeprogram")
    assert state
    assert state.name == "Fake_brand HomeAppliance ActiveProgram"
    assert state.attributes[ATTR_FRIENDLY_NAME] == "Fake_brand HomeAppliance ActiveProgram"

    state = hass.states.get("button.fake_brand_homeappliance_abortprogram")
    assert state
    assert state.name == "Fake_brand HomeAppliance AbortProgram"
    assert state.attributes[ATTR_FRIENDLY_NAME] == "Fake_brand HomeAppliance AbortProgram"


async def test_start(
    hass: HomeAssistant,
    mock_appliance: MockAppliance,
    patch_entity_description: None,
) -> None:
    """Test pressing start button."""
    entity_id = "button.fake_brand_homeappliance_activeprogram"
    assert await setup_config_entry(hass, CONFIG_ENTRIES[0])
    await mock_appliance.entities["Test.SelectedProgram"].update({"value": 500})
    await hass.async_block_till_done()

    await hass.services.async_call(
        domain=BUTTON_DOMAIN,
        service=SERVICE_PRESS,
        service_data={ATTR_ENTITY_ID: entity_id},
        blocking=True,
    )

    mock_appliance.session.send_sync.assert_awaited_once_with(
        Message(
            resource="/ro/activeProgram",
            action=Action.POST,
            data={
                "program": 500,
                "options": [{"uid": 401, "value": None}, {"uid": 402, "value": None}],
            },
        )
    )


@pytest.mark.parametrize(
    ("execution", "available"),
    [
        ("selectandstart", True),
        # the program can't be started remotely, see issue #400
        ("none", False),
    ],
)
async def test_start_available(
    hass: HomeAssistant,
    mock_appliance: MockAppliance,
    patch_entity_description: None,
    execution: str,
    *,
    available: bool,
) -> None:
    """Test start button availability depends on the runtime execution type."""
    entity_id = "button.fake_brand_homeappliance_activeprogram"
    assert await setup_config_entry(hass, CONFIG_ENTRIES[0])
    await mock_appliance.entities["Test.SelectedProgram"].update({"value": 500})
    await mock_appliance.entities["Test.Program.Program1"].update({"execution": execution})
    # the button only listens to the ActiveProgram entity, trigger a state update
    await mock_appliance.entities["Test.ActiveProgram"].update({})
    await hass.async_block_till_done()

    state = hass.states.get(entity_id)
    assert state
    assert (state.state != STATE_UNAVAILABLE) is available


async def test_abort(
    hass: HomeAssistant,
    mock_appliance: MockAppliance,
    patch_entity_description: None,
) -> None:
    """Test pressing abort button."""
    entity_id = "button.fake_brand_homeappliance_abortprogram"
    assert await setup_config_entry(hass, CONFIG_ENTRIES[0])

    await hass.services.async_call(
        domain=BUTTON_DOMAIN,
        service=SERVICE_PRESS,
        service_data={ATTR_ENTITY_ID: entity_id},
        blocking=True,
    )

    mock_appliance.session.send_sync.assert_awaited_once_with(
        Message(
            resource="/ro/values",
            action=Action.POST,
            data={"uid": 300, "value": True},
        )
    )
