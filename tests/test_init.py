"""Tests for integration init."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import ANY, AsyncMock, Mock

import pytest
from custom_components import homeconnect_ws
from homeassistant.config_entries import ConfigEntryState
from homeassistant.helpers import device_registry as dr
from homeconnect_websocket.testutils import MockAppliance

from . import setup_config_entry
from .const import CONFIG_ENTRIES, DEVICE_DESCRIPTION

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from pytest_homeassistant_custom_component.common import MockConfigEntry


@pytest.mark.parametrize(("config_entry"), CONFIG_ENTRIES)
async def test_load_unload_entry(
    config_entry: MockConfigEntry,
    hass: HomeAssistant,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test setup and unload config entry."""
    appliance = MockAppliance(DEVICE_DESCRIPTION, "host", "mock_app", "mock_app_id", "PSK_KEY")
    appliance_mock = Mock(return_value=appliance)
    monkeypatch.setattr(homeconnect_ws.coordinator, "HomeAppliance", appliance_mock)

    load_description_mock = Mock(return_value=DEVICE_DESCRIPTION)
    monkeypatch.setattr(homeconnect_ws, "load_description", load_description_mock)

    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    assert config_entry.state is ConfigEntryState.LOADED

    appliance_mock.assert_called_once_with(
        description=DEVICE_DESCRIPTION,
        host="1.2.3.4",
        app_name="Homeassistant",
        app_id="Test_Device_ID",
        psk64="PSK_KEY",
        iv64="AES_IV",
        connection_callback=ANY,
    )

    assert await hass.config_entries.async_unload(config_entry.entry_id)
    await hass.async_block_till_done()

    assert config_entry.state is ConfigEntryState.NOT_LOADED

    appliance.session.close.assert_awaited_once()


@pytest.mark.parametrize(
    ("service", "entity_key", "field"),
    [
        ("set_start_in", "BSH.Common.Option.StartInRelative", "start_in"),
        ("set_finish_in", "BSH.Common.Option.FinishInRelative", "finish_in"),
    ],
)
async def test_set_relative_time_services(
    service: str,
    entity_key: str,
    field: str,
    hass: HomeAssistant,
    mock_appliance: MockAppliance,
    patch_entity_description: None,
) -> None:
    """Test setting a relative time through each service."""
    config_entry = CONFIG_ENTRIES[0]
    assert await setup_config_entry(hass, config_entry)

    entity = Mock(uid=205, set_value=AsyncMock())
    mock_appliance.entities[entity_key] = entity
    device = dr.async_get(hass).async_get_device(
        identifiers={(homeconnect_ws.DOMAIN, config_entry.unique_id)}, connections=set()
    )
    assert device is not None

    await hass.services.async_call(
        domain=homeconnect_ws.DOMAIN,
        service=service,
        service_data={
            "device_id": device.id,
            field: {"hours": 1, "minutes": 2, "seconds": 3},
        },
        blocking=True,
    )

    entity.set_value.assert_awaited_once_with(3723)


@pytest.mark.parametrize(("config_entry"), CONFIG_ENTRIES)
async def test_remove_entry(
    config_entry: MockConfigEntry,
    hass: HomeAssistant,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test remove config entry."""
    unlink_mock = Mock()
    rmdir_mock = Mock()
    monkeypatch.setattr(Path, "unlink", unlink_mock)
    monkeypatch.setattr(Path, "rmdir", rmdir_mock)

    config_entry.add_to_hass(hass)

    assert await hass.config_entries.async_remove(config_entry.entry_id)
    if config_entry.version == 2:
        assert unlink_mock.call_count == 2
        rmdir_mock.assert_called_once()
    if config_entry.version == 1:
        unlink_mock.assert_not_called()
        rmdir_mock.assert_not_called()
