"""Tests for integration services."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from custom_components.homeconnect_ws.const import DOMAIN
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import device_registry as dr
from homeconnect_websocket.message import Action, Message

from . import setup_config_entry
from .const import CONFIG_ENTRIES

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeconnect_websocket.testutils import MockAppliance


async def _setup_device(hass: HomeAssistant) -> str:
    config_entry = CONFIG_ENTRIES[0]
    assert await setup_config_entry(hass, config_entry)
    device_registry = dr.async_get(hass)
    devices = dr.async_entries_for_config_entry(device_registry, config_entry.entry_id)
    return devices[0].id


async def test_start_program_named_with_options(
    hass: HomeAssistant,
    mock_appliance: MockAppliance,
    patch_entity_description: None,
) -> None:
    """Test starting a named program sends only the given options."""
    device_id = await _setup_device(hass)

    await hass.services.async_call(
        DOMAIN,
        "start_program",
        {
            "device_id": device_id,
            "program": "Test.Program.Program3",
            "options": {"Test.Option1": 3},
        },
        blocking=True,
    )

    mock_appliance.session.send_sync.assert_awaited_once_with(
        Message(
            resource="/ro/activeProgram",
            action=Action.POST,
            data={"program": 502, "options": [{"uid": 401, "value": 3}]},
        )
    )


async def test_start_program_named_without_options(
    hass: HomeAssistant,
    mock_appliance: MockAppliance,
    patch_entity_description: None,
) -> None:
    """Test starting a named program without options sends no option values."""
    device_id = await _setup_device(hass)

    await hass.services.async_call(
        DOMAIN,
        "start_program",
        {"device_id": device_id, "program": "Test.Program.Program1"},
        blocking=True,
    )

    mock_appliance.session.send_sync.assert_awaited_once_with(
        Message(
            resource="/ro/activeProgram",
            action=Action.POST,
            data={"program": 500, "options": []},
        )
    )


async def test_start_program_unknown_program(
    hass: HomeAssistant,
    mock_appliance: MockAppliance,
    patch_entity_description: None,
) -> None:
    """Test starting an unknown program raises."""
    device_id = await _setup_device(hass)

    with pytest.raises(ServiceValidationError) as exc_info:
        await hass.services.async_call(
            DOMAIN,
            "start_program",
            {"device_id": device_id, "program": "Test.Program.Unknown"},
            blocking=True,
        )
    assert exc_info.value.translation_key == "program_not_available"
    mock_appliance.session.send_sync.assert_not_awaited()


async def test_start_program_unknown_option(
    hass: HomeAssistant,
    mock_appliance: MockAppliance,
    patch_entity_description: None,
) -> None:
    """Test passing an unknown option raises."""
    device_id = await _setup_device(hass)

    with pytest.raises(ServiceValidationError) as exc_info:
        await hass.services.async_call(
            DOMAIN,
            "start_program",
            {
                "device_id": device_id,
                "program": "Test.Program.Program1",
                "options": {"Test.Option.Unknown": 1},
            },
            blocking=True,
        )
    assert exc_info.value.translation_key == "option_not_available"
    mock_appliance.session.send_sync.assert_not_awaited()
