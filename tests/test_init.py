"""Tests for integration init."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import ANY, Mock

import pytest
from custom_components import homeconnect_ws
from custom_components.homeconnect_ws.const import DOMAIN
from homeassistant.config_entries import SOURCE_REAUTH, ConfigEntryState
from homeconnect_websocket.errors import AuthenticationError
from homeconnect_websocket.session import ConnectionState
from pytest_homeassistant.common import MockConfigEntry

from . import setup_config_entry
from .const import CONFIG_ENTRIES, DEVICE_DESCRIPTION, MOCK_TLS_DEVICE_ID
from .const import MOCK_CONFIG_DATA_1 as MOCK_CONFIG_DATA

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeconnect_websocket.testutils import MockAppliance


@pytest.mark.parametrize(("config_entry"), CONFIG_ENTRIES)
async def test_load_unload_entry(
    config_entry: MockConfigEntry,
    hass: HomeAssistant,
    monkeypatch: pytest.MonkeyPatch,
    patch_create_appliance: Mock,
) -> None:
    """Test setup and unload config entry."""
    load_description_mock = Mock(return_value=DEVICE_DESCRIPTION)
    monkeypatch.setattr(homeconnect_ws, "load_description", load_description_mock)

    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    assert config_entry.state is ConfigEntryState.LOADED

    patch_create_appliance.assert_called_once_with(
        description=DEVICE_DESCRIPTION,
        host="1.2.3.4",
        app_id="Test_Device_ID",
        psk64="PSK_KEY",
        iv64="AES_IV",
        connection_callback=ANY,
    )

    assert await hass.config_entries.async_unload(config_entry.entry_id)
    await hass.async_block_till_done()

    assert config_entry.state is ConfigEntryState.NOT_LOADED

    appliance: MockAppliance = patch_create_appliance.return_value
    appliance.session._close.assert_awaited_once()


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


async def test_reauth_callback(
    hass: HomeAssistant,
    monkeypatch: pytest.MonkeyPatch,
    patch_create_appliance: Mock,
) -> None:
    """Test start of reauth flow from connection state callback."""
    load_description_mock = Mock(return_value=DEVICE_DESCRIPTION)
    monkeypatch.setattr(homeconnect_ws, "load_description", load_description_mock)
    appliance: MockAppliance = patch_create_appliance.return_value
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data=MOCK_CONFIG_DATA,
        unique_id=MOCK_TLS_DEVICE_ID,
    )
    await setup_config_entry(hass, config_entry)

    await appliance.session.set_connection_state(ConnectionState.AUTHENTICATION_ERROR)
    await hass.async_block_till_done()
    assert any(config_entry.async_get_active_flows(hass, {SOURCE_REAUTH}))


async def test_reauth_setup(
    hass: HomeAssistant,
    monkeypatch: pytest.MonkeyPatch,
    patch_create_appliance: Mock,
) -> None:
    """Test start of reauth flow from setup."""
    load_description_mock = Mock(return_value=DEVICE_DESCRIPTION)
    monkeypatch.setattr(homeconnect_ws, "load_description", load_description_mock)
    appliance: MockAppliance = patch_create_appliance.return_value
    appliance.session._connect.side_effect = AuthenticationError()

    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data=MOCK_CONFIG_DATA,
        unique_id=MOCK_TLS_DEVICE_ID,
    )
    await setup_config_entry(hass, config_entry)

    assert any(config_entry.async_get_active_flows(hass, {SOURCE_REAUTH}))
