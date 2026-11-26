"""Test the Nina services."""

from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.homeconnect_ws.const import (
    DOMAIN,
    SERVICE_SET_FINISH_IN,
    SERVICE_SET_START_IN,
    SERVICE_START_PROGRAM,
)
from homeassistant.const import ATTR_DEVICE_ID
from homeconnect_websocket.message import Action, Message

from . import setup_config_entry
from .const import CONFIG_ENTRIES

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.device_registry import DeviceRegistry
    from homeconnect_websocket.testutils import MockAppliance


async def test_service_registration(hass: HomeAssistant) -> None:
    """Test servicess registration."""
    assert await setup_config_entry(hass, CONFIG_ENTRIES[0])

    services = hass.services.async_services_for_domain(DOMAIN)

    assert len(services) == 3
    assert SERVICE_START_PROGRAM in services
    assert SERVICE_SET_START_IN in services
    assert SERVICE_SET_FINISH_IN in services


async def test_start_program(
    hass: HomeAssistant,
    mock_appliance: MockAppliance,
    device_registry: DeviceRegistry,
) -> None:
    """Test start_program service."""
    await mock_appliance.entities["Test.SelectedProgram"].update({"value": 500})
    config_entry = await setup_config_entry(hass, CONFIG_ENTRIES[0])
    await hass.services.async_call(
        DOMAIN,
        SERVICE_START_PROGRAM,
        {
            ATTR_DEVICE_ID: config_entry.entry_id,
            "start_in": {"hours": 1, "minutes": 10, "seconds": 15},
            "finish_in": {"hours": 1, "minutes": 10, "seconds": 15},
        },
        blocking=True,
    )
    mock_appliance.session.send_sync.assert_awaited_once_with(
        Message(
            resource="/ro/activeProgram",
            action=Action.POST,
            data={
                "program": 500,
                "options": [
                    {"uid": 405, "value": 4215},
                    {"uid": 406, "value": 4215},
                    {"uid": 401, "value": None},
                    {"uid": 402, "value": None},
                ],
            },
        )
    )


async def test_set_start_in(
    hass: HomeAssistant,
    mock_appliance: MockAppliance,
    device_registry: DeviceRegistry,
) -> None:
    """Test set_start_in service."""
    config_entry = await setup_config_entry(hass, CONFIG_ENTRIES[0])
    await hass.services.async_call(
        DOMAIN,
        SERVICE_SET_START_IN,
        {
            ATTR_DEVICE_ID: config_entry.entry_id,
            "start_in": {"hours": 1, "minutes": 10, "seconds": 15},
        },
        blocking=True,
    )

    mock_appliance.session.send_sync.assert_awaited_with(
        Message(
            resource="/ro/values",
            action=Action.POST,
            data={"uid": 405, "value": 4215},
        )
    )


async def test_set_finish_in(
    hass: HomeAssistant,
    mock_appliance: MockAppliance,
    device_registry: DeviceRegistry,
) -> None:
    """Test set_finish_in service."""
    config_entry = await setup_config_entry(hass, CONFIG_ENTRIES[0])
    await hass.services.async_call(
        DOMAIN,
        SERVICE_SET_FINISH_IN,
        {
            ATTR_DEVICE_ID: config_entry.entry_id,
            "finish_in": {"hours": 1, "minutes": 10, "seconds": 15},
        },
        blocking=True,
    )
    mock_appliance.session.send_sync.assert_awaited_once_with(
        Message(
            resource="/ro/values",
            action=Action.POST,
            data={"uid": 406, "value": 4215},
        )
    )
