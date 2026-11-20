"""Connection recovery regression tests."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, Mock, patch

import pytest
from custom_components.homeconnect_ws.coordinator import HomeConnectCoordinator
from homeconnect_websocket import ConnectionFailedError, ConnectionState, HCHandshakeError

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


@pytest.fixture
def recovery_coordinator(hass: HomeAssistant) -> HomeConnectCoordinator:
    """Create a coordinator without starting network traffic."""
    coordinator = object.__new__(HomeConnectCoordinator)
    coordinator.hass = hass
    coordinator.name = "Test appliance"
    coordinator.logger = Mock()
    coordinator.config_entry = Mock(entry_id="test_entry", data={"host": "test-host"})
    coordinator.appliance = Mock()
    coordinator.appliance.session.connected = False
    coordinator.appliance.close = AsyncMock()
    coordinator.appliance.connect = AsyncMock()
    coordinator.async_set_updated_data = Mock()
    coordinator._connecting = True
    coordinator._reconnecting = False
    coordinator.connected = True
    coordinator._reconnect_timer = None
    return coordinator


@pytest.mark.parametrize(
    "terminal_state",
    [ConnectionState.CLOSING, ConnectionState.CLOSED, ConnectionState.ABNORMAL_CLOSURE],
)
async def test_stalled_reconnect_reloads_entry(
    recovery_coordinator: HomeConnectCoordinator, terminal_state: ConnectionState
) -> None:
    """Recover even when a handshake error has stopped the library retry loop."""
    coordinator = recovery_coordinator
    await coordinator._connection_state_callback(ConnectionState.RECONNECTING)
    timer = coordinator._reconnect_timer
    await coordinator._connection_state_callback(terminal_state)
    assert coordinator._reconnect_timer is timer
    timer.cancel()
    with patch.object(coordinator.hass.config_entries, "async_reload", new=AsyncMock()) as reload:
        coordinator._connection_reconnect_callback()
        args = coordinator.config_entry.async_create_background_task.call_args.args
        await args[1]
        reload.assert_awaited_once_with("test_entry")
    assert not coordinator.connected
    assert coordinator._reconnect_timer is None


async def test_recovered_connection_cancels_deadline(
    recovery_coordinator: HomeConnectCoordinator,
) -> None:
    """Do not reload after a normal library reconnect."""
    coordinator = recovery_coordinator
    await coordinator._connection_state_callback(ConnectionState.RECONNECTING)
    timer = coordinator._reconnect_timer
    coordinator.appliance.session.connected = True
    await coordinator._connection_state_callback(ConnectionState.CONNECTED)
    assert timer.cancelled()
    assert coordinator._reconnect_timer is None
    assert not coordinator._reconnecting
    coordinator._connection_reconnect_callback()
    coordinator.config_entry.async_create_background_task.assert_not_called()
    assert coordinator.connected


async def test_close_cancels_recovery(recovery_coordinator: HomeConnectCoordinator) -> None:
    """Late disconnect callbacks after unload cannot schedule a reload."""
    coordinator = recovery_coordinator
    await coordinator._connection_state_callback(ConnectionState.RECONNECTING)
    timer = coordinator._reconnect_timer
    await coordinator.close()
    assert timer.cancelled()
    assert coordinator._reconnect_timer is None
    await coordinator._connection_state_callback(ConnectionState.CLOSED)
    coordinator._connection_reconnect_callback()
    assert coordinator._reconnect_timer is None
    coordinator.config_entry.async_create_background_task.assert_not_called()
    coordinator.appliance.close.assert_awaited_once()


@pytest.mark.parametrize("state", [ConnectionState.CLOSED, ConnectionState.ABNORMAL_CLOSURE])
async def test_terminal_state_without_reconnecting(
    recovery_coordinator: HomeConnectCoordinator, state: ConnectionState
) -> None:
    """Recover terminal closures even without a RECONNECTING notification."""
    coordinator = recovery_coordinator
    await coordinator._connection_state_callback(state)
    assert coordinator._reconnect_timer is not None
    assert not coordinator.connected
    await coordinator.close()


@pytest.mark.parametrize("error", [ConnectionFailedError, HCHandshakeError])
async def test_initial_retry_has_delay(
    recovery_coordinator: HomeConnectCoordinator, error: type[Exception]
) -> None:
    """An unavailable device must not cause an unbounded busy retry loop."""
    coordinator = recovery_coordinator
    coordinator.appliance.connect.side_effect = [error(), None]
    coordinator.appliance.session.connected = True
    with patch(
        "custom_components.homeconnect_ws.coordinator.asyncio.sleep", new=AsyncMock()
    ) as delay:
        await coordinator._connect()
    delay.assert_awaited_once_with(5)
    assert coordinator.appliance.connect.await_count == 2
    await coordinator.close()


async def test_cancel_during_retry(recovery_coordinator: HomeConnectCoordinator) -> None:
    """Task cancellation must propagate rather than retry during unload."""
    coordinator = recovery_coordinator
    coordinator.appliance.connect.side_effect = asyncio.CancelledError
    with pytest.raises(asyncio.CancelledError):
        await coordinator._connect()
    coordinator.appliance.close.assert_not_awaited()
