"""Tests for integration init."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import ANY, Mock

import pytest
from custom_components.homeconnect_ws import coordinator
from homeassistant.config_entries import ConfigEntryState
from homeconnect_websocket.testutils import MockAppliance

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
    monkeypatch.setattr(coordinator, "HomeAppliance", appliance_mock)

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
