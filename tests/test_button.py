"""Tests for button entity."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock

from custom_components.homeconnect_ws.button import program_button_is_available
from homeassistant.components.button import DOMAIN as BUTTON_DOMAIN
from homeassistant.components.button import SERVICE_PRESS
from homeassistant.const import ATTR_ENTITY_ID, ATTR_FRIENDLY_NAME
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
    patch_entity_description: None,  # noqa: ARG001
) -> None:
    """Test pressing start button."""
    entity_id = "button.fake_brand_homeappliance_activeprogram"
    assert await setup_config_entry(hass, MOCK_CONFIG_DATA)
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
    patch_entity_description: None,  # noqa: ARG001
) -> None:
    """Test pressing abort button."""
    entity_id = "button.fake_brand_homeappliance_abortprogram"
    assert await setup_config_entry(hass, MOCK_CONFIG_DATA)

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


def test_program_button_unavailable_when_idle() -> None:
    """Abort/pause/resume must not be valid when no program is running."""
    appliance = MagicMock()
    appliance.active_program = None
    operation = MagicMock()
    operation.value = "Inactive"
    appliance.entities = {"BSH.Common.Status.OperationState": operation}

    assert program_button_is_available("button_abort_program", appliance) is False
    assert program_button_is_available("button_pause_program", appliance) is False
    assert program_button_is_available("button_resume_program", appliance) is False
    assert program_button_is_available("button_mains_power_off", appliance) is True


def test_program_button_available_while_running() -> None:
    """Abort and pause are valid during Run; resume is not."""
    appliance = MagicMock()
    appliance.active_program = object()
    operation = MagicMock()
    operation.value = "Run"
    appliance.entities = {"BSH.Common.Status.OperationState": operation}

    assert program_button_is_available("button_abort_program", appliance) is True
    assert program_button_is_available("button_pause_program", appliance) is True
    assert program_button_is_available("button_resume_program", appliance) is False


def test_abort_ignores_stale_active_program() -> None:
    """A leftover active_program must not keep abort available when idle."""
    appliance = MagicMock()
    appliance.active_program = object()
    operation = MagicMock()
    operation.value = "Inactive"
    appliance.entities = {"BSH.Common.Status.OperationState": operation}

    assert program_button_is_available("button_abort_program", appliance) is False


def test_program_button_available_while_paused() -> None:
    """Abort and resume are valid during Pause."""
    appliance = MagicMock()
    appliance.active_program = object()
    operation = MagicMock()
    operation.value = "Pause"
    appliance.entities = {"BSH.Common.Status.OperationState": operation}

    assert program_button_is_available("button_abort_program", appliance) is True
    assert program_button_is_available("button_pause_program", appliance) is False
    assert program_button_is_available("button_resume_program", appliance) is True
