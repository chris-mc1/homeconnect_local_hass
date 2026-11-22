"""Tests for appliance connection retries."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, call

import pytest
from custom_components.homeconnect_ws import coordinator


@pytest.mark.parametrize("refused", [True, False])
async def test_connect_backs_off_until_connected(
    *, refused: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Back off on immediate refusal or a return without a connected session."""
    sleep = AsyncMock()
    monkeypatch.setattr(coordinator, "asyncio", SimpleNamespace(sleep=sleep))
    session = SimpleNamespace(connected=False)
    attempts = 0

    async def connect() -> None:
        nonlocal attempts
        attempts += 1
        if attempts == 9:
            session.connected = True
        elif refused:
            raise coordinator.ConnectionFailedError

    instance = coordinator.HomeConnectCoordinator.__new__(coordinator.HomeConnectCoordinator)
    instance.appliance = SimpleNamespace(
        info={}, session=session, connect=connect, close=AsyncMock()
    )
    instance.config_entry = SimpleNamespace(data={"host": "appliance"})
    instance.logger = Mock()
    instance.async_set_updated_data = Mock()

    await instance._connect()

    assert sleep.await_args_list == [call(delay) for delay in (1, 2, 4, 8, 16, 32, 60, 60)]
    assert attempts == 9
    assert instance.connected
    instance.async_set_updated_data.assert_called_once_with(None)
