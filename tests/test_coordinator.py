"""Tests for the HomeConnect coordinator reconnect/watchdog behaviour."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest
from custom_components.homeconnect_ws import coordinator as coordinator_module
from custom_components.homeconnect_ws.const import DOMAIN, RECONNECT_GRACE_TIME
from custom_components.homeconnect_ws.coordinator import HomeConnectCoordinator
from homeconnect_websocket import (
    AllreadyConnectedError,
    ConnectionFailedError,
    ConnectionState,
)
from pytest_homeassistant_custom_component.common import MockConfigEntry

from .const import MOCK_CONFIG_DATA, MOCK_TLS_DEVICE_ID

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


def _make_appliance() -> MagicMock:
    """Build a mock appliance with a controllable session."""
    appliance = MagicMock()
    appliance.info = {"deviceID": "Fake_deviceID", "vib": "Fake_vib"}
    appliance.session = MagicMock()
    appliance.session.connected = True
    appliance.connect = AsyncMock()
    appliance.close = AsyncMock()
    return appliance


@pytest.fixture
def coordinator(
    hass: HomeAssistant,
    monkeypatch: pytest.MonkeyPatch,
) -> HomeConnectCoordinator:
    """Return a coordinator wired to a mock appliance."""
    appliance = _make_appliance()
    monkeypatch.setattr(coordinator_module, "HomeAppliance", Mock(return_value=appliance))
    entry = MockConfigEntry(domain=DOMAIN, data=MOCK_CONFIG_DATA, unique_id=MOCK_TLS_DEVICE_ID)
    entry.add_to_hass(hass)
    return HomeConnectCoordinator(hass, entry)


async def test_watchdog_healthy_no_reconnect(coordinator: HomeConnectCoordinator) -> None:
    """A healthy connection must not trigger a reconnect."""
    coordinator._initial_connect_done = True
    coordinator.connected = True
    coordinator.appliance.session.connected = True

    await coordinator._async_update_data()

    coordinator.appliance.connect.assert_not_called()
    assert coordinator.connected is True


async def test_watchdog_within_grace_does_not_force(
    coordinator: HomeConnectCoordinator,
) -> None:
    """A fresh drop stays available during the grace period (no flapping)."""
    coordinator._initial_connect_done = True
    coordinator.connected = True
    coordinator.appliance.session.connected = False

    await coordinator._async_update_data()

    coordinator.appliance.connect.assert_not_called()
    assert coordinator.connected is True
    assert coordinator._down_since is not None


async def test_watchdog_forces_reconnect_past_grace(
    coordinator: HomeConnectCoordinator,
    hass: HomeAssistant,
) -> None:
    """Once down past the grace period, the watchdog forces a clean reconnect."""
    coordinator._initial_connect_done = True
    coordinator.connected = True
    coordinator.appliance.session.connected = False
    coordinator._down_since = hass.loop.time() - (RECONNECT_GRACE_TIME + 5)

    await coordinator._async_update_data()

    coordinator.appliance.close.assert_awaited_once()
    coordinator.appliance.connect.assert_awaited_once()
    # Reconnect did not succeed (mock stays disconnected) -> report unavailable.
    assert coordinator.connected is False


async def test_watchdog_recovers_on_successful_reconnect(
    coordinator: HomeConnectCoordinator,
    hass: HomeAssistant,
) -> None:
    """A successful forced reconnect restores availability."""
    coordinator._initial_connect_done = True
    coordinator.appliance.session.connected = False
    coordinator._down_since = hass.loop.time() - (RECONNECT_GRACE_TIME + 5)

    async def _reconnect() -> None:
        coordinator.appliance.session.connected = True

    coordinator.appliance.connect.side_effect = _reconnect

    await coordinator._async_update_data()

    coordinator.appliance.connect.assert_awaited_once()
    assert coordinator.connected is True
    assert coordinator._down_since is None


async def test_force_reconnect_swallows_already_connected(
    coordinator: HomeConnectCoordinator,
    hass: HomeAssistant,
) -> None:
    """AllreadyConnectedError from the library must not crash the watchdog."""
    coordinator._initial_connect_done = True
    coordinator.appliance.session.connected = False
    coordinator._down_since = hass.loop.time() - (RECONNECT_GRACE_TIME + 5)
    coordinator.appliance.connect.side_effect = AllreadyConnectedError

    await coordinator._async_update_data()

    coordinator.appliance.connect.assert_awaited_once()
    assert coordinator.connected is False


async def test_state_callback_does_not_flap_on_reconnecting(
    coordinator: HomeConnectCoordinator,
) -> None:
    """A brief RECONNECTING event must not immediately mark entities unavailable."""
    coordinator.connected = True

    await coordinator._connection_state_callback(ConnectionState.RECONNECTING)

    assert coordinator.connected is True
    assert coordinator._reconnecting is True
    assert coordinator._down_since is not None


async def test_state_callback_connected_clears_down(
    coordinator: HomeConnectCoordinator,
) -> None:
    """A CONNECTED event clears the down marker and reconnecting flag."""
    coordinator._reconnecting = True
    coordinator._down_since = 123.0

    await coordinator._connection_state_callback(ConnectionState.CONNECTED)

    assert coordinator.connected is True
    assert coordinator._reconnecting is False
    assert coordinator._down_since is None


async def test_watchdog_skips_when_unloading(coordinator: HomeConnectCoordinator) -> None:
    """The watchdog must do nothing once the entry is being unloaded."""
    coordinator._connecting = False
    coordinator._initial_connect_done = True
    coordinator.appliance.session.connected = False

    await coordinator._async_update_data()

    coordinator.appliance.connect.assert_not_called()
    coordinator.appliance.close.assert_not_called()


async def test_watchdog_noop_before_initial_connect(
    coordinator: HomeConnectCoordinator,
) -> None:
    """The watchdog defers to the initial connect loop until it has finished."""
    coordinator.appliance.session.connected = False
    # _initial_connect_done stays False (class default).

    await coordinator._async_update_data()

    coordinator.appliance.connect.assert_not_called()
    assert coordinator._down_since is None


async def test_force_reconnect_skips_when_lock_held(
    coordinator: HomeConnectCoordinator,
    hass: HomeAssistant,
) -> None:
    """A forced reconnect must not start while the connect lock is held."""
    coordinator._initial_connect_done = True
    coordinator.appliance.session.connected = False
    coordinator._down_since = hass.loop.time() - (RECONNECT_GRACE_TIME + 5)

    async with coordinator._connect_lock:
        await coordinator._async_update_data()

    coordinator.appliance.connect.assert_not_called()


@pytest.mark.parametrize(
    "state",
    [
        ConnectionState.CLOSING,
        ConnectionState.CLOSED,
        ConnectionState.ABNORMAL_CLOSURE,
    ],
)
async def test_state_callback_terminal_states_record_down(
    coordinator: HomeConnectCoordinator,
    state: ConnectionState,
) -> None:
    """Terminal down states record the outage without flapping or flagging reconnect."""
    coordinator.connected = True

    await coordinator._connection_state_callback(state)

    assert coordinator.connected is True  # not cleared by the callback
    assert coordinator._reconnecting is False
    assert coordinator._down_since is not None


async def test_watchdog_clears_down_since_on_healthy_connection(
    coordinator: HomeConnectCoordinator,
) -> None:
    """A healthy check clears a stale down marker."""
    coordinator._initial_connect_done = True
    coordinator._down_since = 123.0
    coordinator.appliance.session.connected = True

    await coordinator._async_update_data()

    assert coordinator._down_since is None
    assert coordinator.connected is True


async def test_force_reconnect_handles_connection_failed(
    coordinator: HomeConnectCoordinator,
    hass: HomeAssistant,
) -> None:
    """A failing reconnect is swallowed and leaves the connection unavailable."""
    coordinator._initial_connect_done = True
    coordinator.appliance.session.connected = False
    coordinator._down_since = hass.loop.time() - (RECONNECT_GRACE_TIME + 5)
    coordinator.appliance.connect.side_effect = ConnectionFailedError

    await coordinator._async_update_data()

    coordinator.appliance.close.assert_awaited_once()
    coordinator.appliance.connect.assert_awaited_once()
    assert coordinator.connected is False


async def test_force_reconnect_tolerates_close_exception(
    coordinator: HomeConnectCoordinator,
    hass: HomeAssistant,
) -> None:
    """A close() failure during a forced reconnect must not abort the reconnect."""
    coordinator._initial_connect_done = True
    coordinator.appliance.session.connected = False
    coordinator._down_since = hass.loop.time() - (RECONNECT_GRACE_TIME + 5)
    coordinator.appliance.close.side_effect = Exception("close failed")

    async def _reconnect() -> None:
        coordinator.appliance.session.connected = True

    coordinator.appliance.connect.side_effect = _reconnect

    await coordinator._async_update_data()

    coordinator.appliance.connect.assert_awaited_once()
    assert coordinator.connected is True
