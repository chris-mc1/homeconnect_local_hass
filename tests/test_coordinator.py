"""Tests for the coordinator connect/reconnect backoff."""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import aiohttp
import pytest
from custom_components import homeconnect_ws
from custom_components.homeconnect_ws import coordinator as coordinator_module
from custom_components.homeconnect_ws.const import DOMAIN, MAX_RECONECT_TIME
from custom_components.homeconnect_ws.coordinator import (
    HomeConnectCoordinator,
    reconnect_delay,
)
from homeassistant.config_entries import ConfigEntryState
from homeassistant.util import dt as dt_util
from homeconnect_websocket import ConnectionFailedError, ConnectionState, HCHandshakeError
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_fire_time_changed

from .const import DEVICE_DESCRIPTION, MOCK_AES_DEVICE_ID, MOCK_CONFIG_DATA_2

if TYPE_CHECKING:
    from collections.abc import Callable

    from homeassistant.core import HomeAssistant

HOST = MOCK_CONFIG_DATA_2["host"]
WINDOW = 3600


def handshake_503() -> aiohttp.WSServerHandshakeError:
    """Error raised by aiohttp when the appliance answers the upgrade with 503."""
    return aiohttp.WSServerHandshakeError(
        request_info=Mock(real_url=f"ws://{HOST}/homeconnect"),
        history=(),
        status=503,
        message="Invalid response status",
    )


def connection_failed() -> ConnectionFailedError:
    """Error raised by the library when the TCP connect fails."""
    exc = ConnectionFailedError("Failed to connect to Appliance")
    exc.__cause__ = OSError(113, "No route to host")
    return exc


ERRORS: dict[str, Callable[[], BaseException]] = {
    "oserror": lambda: OSError(113, "No route to host"),
    "connection_failed": connection_failed,
    "handshake_503": handshake_503,
    "hc_handshake": lambda: HCHandshakeError("Invalid init message: None"),
    "timeout": TimeoutError,
}


@pytest.fixture(autouse=True)
def no_jitter() -> None:
    """Make the backoff deterministic."""
    with patch.object(coordinator_module.random, "uniform", return_value=0):
        yield


@pytest.fixture
def config_entry(hass: HomeAssistant) -> MockConfigEntry:
    """Config entry."""
    entry = MockConfigEntry(
        domain=DOMAIN, data=MOCK_CONFIG_DATA_2, unique_id=MOCK_AES_DEVICE_ID, version=2
    )
    entry.add_to_hass(hass)
    return entry


@pytest.fixture
def appliance() -> MagicMock:
    """Appliance whose connect() result is set per test."""
    appliance = MagicMock()
    appliance.info = DEVICE_DESCRIPTION["info"]
    appliance.session.connected = False
    appliance.close = AsyncMock()
    appliance._task_manager._tasks = set()
    appliance._task_manager._background_tasks = set()
    return appliance


@pytest.fixture
async def coordinator(
    hass: HomeAssistant, config_entry: MockConfigEntry, appliance: MagicMock
) -> HomeConnectCoordinator:
    """Coordinator with a mocked appliance."""
    with patch.object(coordinator_module, "HomeAppliance", Mock(return_value=appliance)):
        coordinator = HomeConnectCoordinator(hass, config_entry, DEVICE_DESCRIPTION)
    yield coordinator
    await coordinator.close()


def connect_side_effect(appliance: MagicMock, results: list[BaseException | None]) -> AsyncMock:
    """Raise the given errors in order, None means successful connect."""
    results = iter(results)

    async def connect() -> None:
        result = next(results)
        if result is not None:
            appliance.session.connected = False
            raise result
        appliance.session.connected = True

    return AsyncMock(side_effect=connect)


class FakeClock:
    """Replacement for asyncio.sleep that only advances a virtual clock."""

    def __init__(self, coordinator: HomeConnectCoordinator, window: float) -> None:
        self.coordinator = coordinator
        self.window = window
        self.now = 0.0
        self.delays: list[float] = []

    async def sleep(self, delay: float) -> None:
        self.delays.append(delay)
        self.now += delay
        if self.now > self.window:
            # Stop the loop once the window is over
            self.coordinator._closing = True


def expected_attempts(window: float) -> int:
    """Return the number of attempts in window with 5 s, 10 s, ... 300 s backoff."""
    attempts, now = 1, 0
    while (now := now + reconnect_delay(attempts)) <= window:
        attempts += 1
    return attempts


def test_reconnect_delay() -> None:
    """Delay doubles from 5 s and is capped at 300 s."""
    assert [reconnect_delay(n) for n in range(1, 10)] == [5, 10, 20, 40, 80, 160, 300, 300, 300]
    assert reconnect_delay(1000) == 300


def test_reconnect_delay_jitter() -> None:
    """Jitter reduces the delay by up to 20 %, never exceeds the cap."""
    with patch.object(coordinator_module.random, "uniform", return_value=0.2):
        assert reconnect_delay(1) == pytest.approx(4)
        assert reconnect_delay(100) == pytest.approx(240)
    for failures in range(1, 20):
        assert reconnect_delay(failures) <= 300


@pytest.mark.parametrize("error", ERRORS.keys())
async def test_unreachable_backoff(
    coordinator: HomeConnectCoordinator,
    appliance: MagicMock,
    caplog: pytest.LogCaptureFixture,
    error: str,
) -> None:
    """Permanently unreachable appliance is retried with capped backoff, not in a loop."""
    caplog.set_level(logging.DEBUG, logger=coordinator_module.__name__)
    appliance.connect = AsyncMock(side_effect=lambda: (_ for _ in ()).throw(ERRORS[error]()))
    clock = FakeClock(coordinator, WINDOW)

    with patch.object(coordinator_module.asyncio, "sleep", clock.sleep):
        await coordinator._connect()

    # 1 + 6 increasing delays (5..160 s, 315 s total) + 10 * 300 s = 17 attempts per hour
    assert expected_attempts(WINDOW) == 17
    assert appliance.connect.await_count == 17
    assert clock.delays[:8] == [5, 10, 20, 40, 80, 160, 300, 300]
    assert max(clock.delays) == 300
    assert appliance.close.await_count == appliance.connect.await_count
    assert not coordinator.connected

    records = [r for r in caplog.records if r.name == coordinator_module.__name__]
    warnings = [r for r in records if r.levelno >= logging.WARNING]
    assert len(warnings) == 1
    assert warnings[0].levelno == logging.WARNING
    assert HOST in warnings[0].getMessage()
    assert not warnings[0].exc_info
    retries = [r for r in records if "attempt" in r.getMessage()]
    assert len(retries) == 16
    assert all(r.levelno == logging.DEBUG for r in retries)


async def test_unreachable_log_reason(
    coordinator: HomeConnectCoordinator, appliance: MagicMock, caplog: pytest.LogCaptureFixture
) -> None:
    """The warning names host and reason of the failure."""
    appliance.connect = AsyncMock(side_effect=handshake_503())
    with patch.object(coordinator_module.asyncio, "sleep", FakeClock(coordinator, 1).sleep):
        await coordinator._connect()
    assert f"Can't connect to {HOST}: HTTP 503 Invalid response status, retrying in 5 s" in (
        caplog.text
    )

    caplog.clear()
    coordinator._closing = False
    appliance.connect = AsyncMock(side_effect=connection_failed())
    with patch.object(coordinator_module.asyncio, "sleep", FakeClock(coordinator, 1).sleep):
        await coordinator._connect()
    assert "ConnectionFailedError: Failed to connect to Appliance" in caplog.text
    assert "No route to host" in caplog.text


async def test_unexpected_exception_logged_once(
    coordinator: HomeConnectCoordinator, appliance: MagicMock, caplog: pytest.LogCaptureFixture
) -> None:
    """Unexpected exceptions are retried with backoff, traceback logged once."""
    caplog.set_level(logging.DEBUG, logger=coordinator_module.__name__)
    appliance.connect = AsyncMock(side_effect=ValueError("boom"))
    clock = FakeClock(coordinator, WINDOW)

    with patch.object(coordinator_module.asyncio, "sleep", clock.sleep):
        await coordinator._connect()

    assert appliance.connect.await_count == 17
    with_traceback = [r for r in caplog.records if r.exc_info]
    assert len(with_traceback) == 1
    assert with_traceback[0].levelno == logging.WARNING
    assert caplog.text.count("Traceback") == 1


async def test_success_resets_backoff(
    hass: HomeAssistant,
    coordinator: HomeConnectCoordinator,
    appliance: MagicMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A successful connect after N failures resets the backoff."""
    caplog.set_level(logging.DEBUG, logger=coordinator_module.__name__)
    appliance.connect = connect_side_effect(
        appliance, [OSError(), OSError(), OSError(), None, OSError(), OSError(), None]
    )
    clock = FakeClock(coordinator, WINDOW)

    with patch.object(coordinator_module.asyncio, "sleep", clock.sleep):
        await coordinator._connect()
        assert coordinator.connected
        assert clock.delays == [5, 10, 20]
        assert f"Connected to {HOST} after 3 failed attempt(s)" in caplog.text
        assert any(
            r.levelno == logging.INFO and "after 3 failed" in r.getMessage() for r in caplog.records
        )

        # Stable connection lost: next outage starts again at 5 s
        caplog.clear()
        coordinator._connected_since -= 120
        appliance.session.connected = False
        await coordinator._connection_state_callback(ConnectionState.ABNORMAL_CLOSURE)
        assert f"Connection to {HOST} lost, reconnecting" in caplog.text
        # Entities stay available during the grace period
        assert coordinator.connected
        await coordinator._connect_task

    assert clock.delays == [5, 10, 20, 5, 10]
    assert coordinator.connected
    assert f"Connected to {HOST} after 2 failed attempt(s)" in caplog.text


async def test_unavailable_after_grace_period(
    hass: HomeAssistant, coordinator: HomeConnectCoordinator, appliance: MagicMock
) -> None:
    """Entities become unavailable when the reconnect takes longer than MAX_RECONECT_TIME."""
    appliance.connect = connect_side_effect(appliance, [None])
    await coordinator._connect()
    assert coordinator.connected

    appliance.connect = AsyncMock(side_effect=OSError())
    appliance.session.connected = False
    await coordinator._connection_state_callback(ConnectionState.ABNORMAL_CLOSURE)
    assert coordinator.connected

    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=MAX_RECONECT_TIME - 10))
    assert coordinator.connected
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=MAX_RECONECT_TIME + 1))
    assert not coordinator.connected


async def test_close_while_waiting(
    hass: HomeAssistant, coordinator: HomeConnectCoordinator, appliance: MagicMock
) -> None:
    """close() during the backoff wait ends the task immediately."""
    appliance.connect = AsyncMock(side_effect=handshake_503())
    coordinator._start_connect()
    task = coordinator._connect_task
    # Let the first attempt fail, the task now sleeps for 5 s
    for _ in range(5):
        await asyncio.sleep(0)
    assert appliance.connect.await_count == 1
    assert not task.done()

    loop = asyncio.get_running_loop()
    start = loop.time()
    async with asyncio.timeout(1):
        await coordinator.close()
    assert loop.time() - start < 1

    assert task.cancelled()
    assert appliance.connect.await_count == 1
    assert coordinator._client_session.closed

    # No further attempts after close
    coordinator._start_connect()
    await asyncio.sleep(0)
    assert appliance.connect.await_count == 1


async def test_close_hanging_library(
    hass: HomeAssistant, coordinator: HomeConnectCoordinator, appliance: MagicMock
) -> None:
    """A hanging appliance.close() is bounded and leftover library tasks are cancelled."""
    leftover = asyncio.create_task(asyncio.sleep(3600))
    appliance._task_manager._background_tasks = {leftover}

    async def hanging_close() -> None:
        await asyncio.sleep(3600)

    appliance.close = AsyncMock(side_effect=hanging_close)
    with patch.object(coordinator_module, "CLOSE_TIMEOUT", 0.05):
        async with asyncio.timeout(1):
            await coordinator.close()
    await asyncio.sleep(0)
    assert leftover.cancelled()


async def test_unload_while_waiting(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    monkeypatch: pytest.MonkeyPatch,
    appliance: MagicMock,
) -> None:
    """Unloading the entry while the appliance is unreachable ends the connect task."""
    appliance.connect = AsyncMock(side_effect=handshake_503())
    monkeypatch.setattr(coordinator_module, "HomeAppliance", Mock(return_value=appliance))
    monkeypatch.setattr(homeconnect_ws, "load_description", Mock(return_value=DEVICE_DESCRIPTION))

    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    assert config_entry.state is ConfigEntryState.LOADED
    coordinator = config_entry.runtime_data.coordinator
    task = coordinator._connect_task
    assert appliance.connect.await_count == 1
    assert not task.done()

    async with asyncio.timeout(1):
        assert await hass.config_entries.async_unload(config_entry.entry_id)
        await hass.async_block_till_done()

    assert config_entry.state is ConfigEntryState.NOT_LOADED
    assert task.done()
    assert appliance.connect.await_count == 1
    assert coordinator._client_session.closed


async def test_unstable_connection_backoff(
    hass: HomeAssistant, coordinator: HomeConnectCoordinator, appliance: MagicMock
) -> None:
    """An appliance dropping the connection right after connecting is not reconnected in a loop."""
    appliance.connect = connect_side_effect(appliance, [None] * 5)
    clock = FakeClock(coordinator, WINDOW)

    with patch.object(coordinator_module.asyncio, "sleep", clock.sleep):
        await coordinator._connect()
        for _ in range(4):
            appliance.session.connected = False
            await coordinator._connection_state_callback(ConnectionState.ABNORMAL_CLOSURE)
            await coordinator._connect_task

    assert appliance.connect.await_count == 5
    assert clock.delays == [5, 10, 20, 40]

    # Connection stable for long enough: immediate reconnect, no delay
    appliance.connect = connect_side_effect(appliance, [None])
    coordinator._connected_since -= 120
    with patch.object(coordinator_module.asyncio, "sleep", clock.sleep):
        await coordinator._connection_state_callback(ConnectionState.ABNORMAL_CLOSURE)
        await coordinator._connect_task
    assert clock.delays == [5, 10, 20, 40]
    assert coordinator.connected
