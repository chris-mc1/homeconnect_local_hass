"""Tests for the coordinator."""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING
from unittest.mock import Mock

from custom_components import homeconnect_ws
from custom_components.homeconnect_ws.const import DOMAIN
from homeassistant.util import dt as dt_util
from homeconnect_websocket import ConnectionState
from homeconnect_websocket.testutils import MockAppliance
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_fire_time_changed

from .const import DEVICE_DESCRIPTION, MOCK_AES_DEVICE_ID, MOCK_CONFIG_DATA_2

if TYPE_CHECKING:
    import pytest
    from homeassistant.core import HomeAssistant


async def setup_appliance(hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch) -> tuple:
    """Set up the integration and return the appliance, coordinator and connection callback."""
    appliance = MockAppliance(DEVICE_DESCRIPTION, "host", "mock_app", "mock_app_id", "PSK_KEY")
    appliance.session.connected = True
    appliance_mock = Mock(return_value=appliance)
    monkeypatch.setattr(homeconnect_ws.coordinator, "HomeAppliance", appliance_mock)
    monkeypatch.setattr(homeconnect_ws, "load_description", Mock(return_value=DEVICE_DESCRIPTION))

    config_entry = MockConfigEntry(
        domain=DOMAIN, data=MOCK_CONFIG_DATA_2, unique_id=MOCK_AES_DEVICE_ID, version=2
    )
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    connection_callback = appliance_mock.call_args.kwargs["connection_callback"]
    return appliance, config_entry.runtime_data.coordinator, connection_callback


async def test_reconnect_timeout_cancelled_after_reconnect(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A timeout from an earlier, already recovered outage does not mark a later short one."""
    appliance, coordinator, connection_callback = await setup_appliance(hass, monkeypatch)

    appliance.session.connected = False
    await connection_callback(ConnectionState.RECONNECTING)
    appliance.session.connected = True
    await connection_callback(ConnectionState.CONNECTED)
    # next short outage, still within its own timeout
    appliance.session.connected = False

    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=301))
    await hass.async_block_till_done()

    assert coordinator.connected


async def test_reconnect_timeout_marks_disconnected(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An outage longer than the reconnect timeout marks the appliance disconnected."""
    appliance, coordinator, connection_callback = await setup_appliance(hass, monkeypatch)

    appliance.session.connected = False
    await connection_callback(ConnectionState.RECONNECTING)

    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=301))
    await hass.async_block_till_done()

    assert not coordinator.connected
