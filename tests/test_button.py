"""Tests for button entity."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import Mock

import pytest
from custom_components.homeconnect_ws.button import HCStartButton
from custom_components.homeconnect_ws.entity_descriptions import HCButtonEntityDescription
from custom_components.homeconnect_ws.entity_descriptions.common import REMOTE_START_ALLOWED
from homeassistant.components.button import DOMAIN as BUTTON_DOMAIN
from homeassistant.components.button import SERVICE_PRESS
from homeassistant.const import ATTR_ENTITY_ID, ATTR_FRIENDLY_NAME
from homeconnect_websocket.entities import Access
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


def _start_button(
    *, remote_start: bool | None, has_remote_start: bool = True, access: Access = Access.READ_WRITE
) -> HCStartButton:
    entities = {"BSH.Common.Root.ActiveProgram": Mock(available=True, access=access)}
    if has_remote_start:
        entities[REMOTE_START_ALLOWED] = Mock(value=remote_start)
    appliance = Mock(entities=entities, info={"deviceID": "device"}, selected_program=Mock())
    appliance.session.connected = True
    runtime_data = Mock(appliance=appliance, device_info={})
    runtime_data.coordinator.connected = True
    return HCStartButton(
        HCButtonEntityDescription(
            key="button_start_program", entity="BSH.Common.Root.ActiveProgram"
        ),
        runtime_data,
    )


@pytest.mark.parametrize(
    ("remote_start", "has_remote_start", "access", "available"),
    [
        (True, True, Access.READ_WRITE, True),
        (False, True, Access.READ_WRITE, False),
        (None, True, Access.READ_WRITE, False),
        (None, False, Access.READ_WRITE, True),
        (True, True, Access.READ, False),
    ],
)
def test_start_availability(
    *, remote_start: bool | None, has_remote_start: bool, access: Access, available: bool
) -> None:
    """Test Start button follows Remote Start and ActiveProgram access."""
    button = _start_button(
        remote_start=remote_start, has_remote_start=has_remote_start, access=access
    )
    assert button.available is available


def test_start_unavailable_without_selected_program() -> None:
    """Test Start button is unavailable without a selected Program."""
    button = _start_button(remote_start=True)
    button._runtime_data.appliance.selected_program = None
    assert button.available is False
