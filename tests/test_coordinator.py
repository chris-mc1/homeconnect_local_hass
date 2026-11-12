"""Tests for the connection handling of the coordinator."""

from __future__ import annotations

import asyncio
import logging
import ssl
import time
from copy import deepcopy
from ipaddress import ip_address
from typing import TYPE_CHECKING
from unittest.mock import Mock

import aiohttp
import pytest
from custom_components import homeconnect_ws
from custom_components.homeconnect_ws import const
from custom_components.homeconnect_ws.const import DOMAIN
from custom_components.homeconnect_ws.coordinator import HomeConnectCoordinator, _is_psk_mismatch
from homeassistant.config_entries import SOURCE_REAUTH, SOURCE_ZEROCONF, ConfigEntryState
from homeassistant.const import CONF_HOST
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import issue_registry as ir
from homeconnect_websocket import (
    AuthenticationError,
    ConnectionFailedError,
    ConnectionState,
    HCHandshakeError,
)
from homeconnect_websocket.testutils import MockAppliance
from pytest_homeassistant_custom_component.common import MockConfigEntry

from .const import DEVICE_DESCRIPTION, MOCK_CONFIG_DATA_2, MOCK_TLS_DEVICE_ID
from .test_zeroconf import MOCK_ZEROCONF_DATA

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Awaitable, Callable

    from homeassistant.core import HomeAssistant

EXPECTED_MAC = "C8-D7-78-43-F2-23"
MAX_LOOP_BLOCK = 0.1

type Behaviour = Callable[["FakeDevice"], Awaitable[None]]


class FakeDevice:
    """Scripted appliance. Creates one MockAppliance per coordinator."""

    def __init__(self, behaviour: Behaviour) -> None:
        self.behaviour = behaviour
        self.appliances: list[MockAppliance] = []
        self.callbacks: list[Callable[[ConnectionState], Awaitable[None]]] = []
        self.connect_times: list[float] = []
        self.closes = 0

    def __call__(self, **kwargs: object) -> MockAppliance:
        description = deepcopy(kwargs["description"])
        appliance = MockAppliance(description, kwargs["host"], "app", "app_id", "PSK")
        appliance.session.connected = False
        appliance.session.connect.side_effect = self._connect
        appliance.session.close.side_effect = self._close
        self.appliances.append(appliance)
        self.callbacks.append(kwargs["connection_callback"])
        return appliance

    @property
    def appliance(self) -> MockAppliance:
        """The appliance of the current coordinator."""
        return self.appliances[-1]

    @property
    def connects(self) -> int:
        return len(self.connect_times)

    async def _connect(self) -> None:
        self.connect_times.append(time.monotonic())
        await self.behaviour(self)

    async def _close(self) -> None:
        self.closes += 1
        self.appliance.session.connected = False

    async def drop(self) -> None:
        """Simulate the appliance closing an established connection."""
        self.appliance.session.connected = False
        await self.callbacks[-1](ConnectionState.ABNORMAL_CLOSURE)


async def refuse(device: FakeDevice) -> None:
    """Fail right away: connection refused / closed right after accept."""
    raise ConnectionFailedError


async def handshake_error(device: FakeDevice) -> None:
    """Close the connection during the handshake."""
    raise HCHandshakeError


async def hang(device: FakeDevice) -> None:
    """Accept the connection and never answer."""
    await asyncio.Event().wait()


async def auth_error(device: FakeDevice) -> None:
    """Reject the PSK."""
    msg = "Authentication with Appliance failed"
    raise AuthenticationError(msg)


async def psk_mismatch(device: FakeDevice) -> None:
    """Reject the PSK, reported as in production by homeconnect-websocket 1.5.5."""
    os_error = ssl.SSLError(1, "[SSL: SSLV3_ALERT_BAD_RECORD_MAC] ssl/tls alert bad record mac")
    os_error.reason = "SSLV3_ALERT_BAD_RECORD_MAC"
    msg = "Failed to connect to Appliance"
    raise ConnectionFailedError(msg) from aiohttp.ClientConnectorSSLError(Mock(ssl=True), os_error)


async def accept(device: FakeDevice) -> None:
    """Connect successfully."""
    device.appliance.session.connected = True


async def wrong_identity(device: FakeDevice) -> None:
    """Handshake works, but another appliance answers."""
    device.appliance.session.connected = True
    device.appliance.info["mac"] = "00-11-22-33-44-55"


async def accept_then_drop(device: FakeDevice) -> None:
    """Complete the handshake, then close the connection right away."""
    device.appliance.session.connected = True
    asyncio.get_running_loop().call_soon(lambda: asyncio.ensure_future(device.drop()))


@pytest.fixture
def fast(monkeypatch: pytest.MonkeyPatch) -> None:
    """Shrink all delays so that many cycles run within a test."""
    monkeypatch.setattr(const, "RECONNECT_DELAY_INITIAL", 0.0001)
    monkeypatch.setattr(const, "RECONNECT_DELAY_MAX", 0.001)
    monkeypatch.setattr(const, "CONNECT_TIMEOUT", 0.02)
    monkeypatch.setattr(const, "MAX_CONNECTS_PER_MINUTE", 10**9)
    monkeypatch.setattr(const, "IDENTITY_RETRY_DELAY", 0.3)


@pytest.fixture
async def setup_device(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> AsyncGenerator[Callable[[Behaviour], Awaitable[tuple[FakeDevice, MockConfigEntry]]]]:
    """Set up a config entry connected to a scripted appliance."""
    entries: list[MockConfigEntry] = []

    async def go(behaviour: Behaviour) -> tuple[FakeDevice, MockConfigEntry]:
        device = FakeDevice(behaviour)
        description = deepcopy(DEVICE_DESCRIPTION)
        description["info"]["mac"] = EXPECTED_MAC
        monkeypatch.setattr(homeconnect_ws.coordinator, "HomeAppliance", device)
        monkeypatch.setattr(homeconnect_ws, "load_description", Mock(return_value=description))
        entry = MockConfigEntry(
            domain=DOMAIN,
            data=dict(MOCK_CONFIG_DATA_2),
            unique_id=MOCK_TLS_DEVICE_ID,
            version=2,
            title="Fake_Brand HomeAppliance",
        )
        entry.add_to_hass(hass)
        assert await hass.config_entries.async_setup(entry.entry_id)
        entries.append(entry)
        return device, entry

    yield go

    for entry in entries:
        if entry.state is ConfigEntryState.LOADED:
            await hass.config_entries.async_unload(entry.entry_id)


class LoopMonitor:
    """Measure the longest time the event loop did not run."""

    def __init__(self) -> None:
        self.max_block = 0.0
        self.ticks = 0
        self._task = asyncio.ensure_future(self._run())

    async def _run(self) -> None:
        last = time.monotonic()
        while True:
            await asyncio.sleep(0.001)
            now = time.monotonic()
            self.max_block = max(self.max_block, now - last)
            self.ticks += 1
            last = now

    def stop(self) -> None:
        self._task.cancel()


async def wait_for(condition: Callable[[], bool], timeout: float = 10) -> None:  # noqa: ASYNC109
    """Wait until condition is true."""
    async with asyncio.timeout(timeout):
        while not condition():  # noqa: ASYNC110
            await asyncio.sleep(0.001)


def connection_tasks() -> list[asyncio.Task]:
    """Return the running connection loops."""
    return [
        task
        for task in asyncio.all_tasks()
        if task.get_name().startswith("homeconnect_ws_") and not task.done()
    ]


def issue_exists(hass: HomeAssistant, issue: str, entry: MockConfigEntry) -> bool:
    """Return if a repair issue exists for the entry."""
    return ir.async_get(hass).async_get_issue(DOMAIN, f"{issue}_{entry.entry_id}") is not None


def test_backoff_delay(monkeypatch: pytest.MonkeyPatch) -> None:
    """Delays double from 1 s up to 5 min and are randomized."""
    monkeypatch.setattr(const, "RECONNECT_JITTER", 0)
    delays = [HomeConnectCoordinator._backoff_delay(failures) for failures in range(1, 13)]
    assert delays == [1, 2, 4, 8, 16, 32, 64, 128, 256, 300, 300, 300]
    assert HomeConnectCoordinator._backoff_delay(10**6) == 300

    monkeypatch.setattr(const, "RECONNECT_JITTER", 0.2)
    jittered = {HomeConnectCoordinator._backoff_delay(4) for _ in range(50)}
    assert len(jittered) > 1
    assert all(8 * 0.8 <= delay <= 8 * 1.2 for delay in jittered)


@pytest.mark.parametrize("behaviour", [refuse, handshake_error, auth_error, accept_then_drop])
async def test_failing_appliance_is_harmless(
    hass: HomeAssistant,
    setup_device: Callable[[Behaviour], Awaitable[tuple[FakeDevice, MockConfigEntry]]],
    monkeypatch: pytest.MonkeyPatch,
    fast: None,
    behaviour: Behaviour,
) -> None:
    """1000 failed cycles: loop stays responsive, nothing accumulates."""
    monkeypatch.setattr(const, "IDENTITY_RETRY_DELAY", 0)
    backoff_failures: list[int] = []
    real_backoff = HomeConnectCoordinator._backoff_delay

    def spy(failures: int) -> float:
        backoff_failures.append(failures)
        return real_backoff(failures)

    monkeypatch.setattr(HomeConnectCoordinator, "_backoff_delay", staticmethod(spy))

    device, entry = await setup_device(behaviour)
    await wait_for(lambda: device.connects >= 20)
    tasks_before = len(asyncio.all_tasks())
    monitor = LoopMonitor()

    await wait_for(lambda: device.connects >= 1000, timeout=60)

    monitor.stop()
    assert monitor.max_block < MAX_LOOP_BLOCK
    assert monitor.ticks > 100
    # No task leak, one loop, every attempt was closed again
    assert len(asyncio.all_tasks()) <= tasks_before + 2
    assert len(connection_tasks()) == 1
    assert device.closes >= device.connects - 1
    # The backoff never resets: the failure count only grows
    assert backoff_failures[:50] == list(range(1, 51))
    assert entry.state is ConfigEntryState.LOADED
    if behaviour is not accept_then_drop:
        assert not entry.runtime_data.coordinator.connected


async def test_silent_appliance_times_out(
    hass: HomeAssistant,
    setup_device: Callable[[Behaviour], Awaitable[tuple[FakeDevice, MockConfigEntry]]],
    fast: None,
) -> None:
    """An appliance that accepts and never answers is cut off by the timeout."""
    device, entry = await setup_device(hang)
    monitor = LoopMonitor()

    await wait_for(lambda: device.connects >= 20)

    monitor.stop()
    assert monitor.max_block < MAX_LOOP_BLOCK
    assert device.closes >= device.connects - 1
    assert len(connection_tasks()) == 1

    # Unloading while an attempt hangs works and stops the loop
    assert await hass.config_entries.async_unload(entry.entry_id)
    assert entry.state is ConfigEntryState.NOT_LOADED
    assert not connection_tasks()
    connects = device.connects
    await asyncio.sleep(0.1)
    assert device.connects == connects


async def test_slow_close_is_cut_off(
    hass: HomeAssistant,
    setup_device: Callable[[Behaviour], Awaitable[tuple[FakeDevice, MockConfigEntry]]],
    monkeypatch: pytest.MonkeyPatch,
    fast: None,
) -> None:
    """A close that never returns neither stops the loop nor the unload."""
    monkeypatch.setattr(const, "CLOSE_TIMEOUT", 0.02)
    device, entry = await setup_device(refuse)
    device.appliance.session.close.side_effect = hang

    await wait_for(lambda: device.connects >= 5)
    assert await hass.config_entries.async_unload(entry.entry_id)
    assert not connection_tasks()


def reauth_flows(hass: HomeAssistant, entry: MockConfigEntry) -> list[dict]:
    """Return the reauth flows in progress for entry."""
    return [
        flow
        for flow in hass.config_entries.flow.async_progress_by_handler(DOMAIN)
        if flow["context"].get("source") == SOURCE_REAUTH
        and flow["context"].get("entry_id") == entry.entry_id
    ]


@pytest.mark.parametrize("behaviour", [auth_error, psk_mismatch])
async def test_rejected_key_starts_reauth(
    hass: HomeAssistant,
    setup_device: Callable[[Behaviour], Awaitable[tuple[FakeDevice, MockConfigEntry]]],
    fast: None,
    behaviour: Behaviour,
) -> None:
    """The appliance rejects the key: ask for a new profile file, retry rarely."""
    device, entry = await setup_device(behaviour)
    coordinator = entry.runtime_data.coordinator

    await wait_for(lambda: device.connects >= 2)
    assert not reauth_flows(hass, entry)

    await wait_for(lambda: bool(reauth_flows(hass, entry)))
    assert device.connects == const.IDENTITY_FAILURE_THRESHOLD
    assert not coordinator.connected
    assert not issue_exists(hass, const.ISSUE_WRONG_DEVICE, entry)

    # Following attempts are rare and don't start more flows
    await wait_for(lambda: device.connects >= const.IDENTITY_FAILURE_THRESHOLD + 2)
    gaps = [b - a for a, b in zip(device.connect_times[2:], device.connect_times[3:], strict=False)]
    assert all(gap >= const.IDENTITY_RETRY_DELAY * 0.8 for gap in gaps)
    assert len(reauth_flows(hass, entry)) == 1
    assert not issue_exists(hass, const.ISSUE_WRONG_DEVICE, entry)

    # The key works again (e.g. the appliance was paired back)
    device.behaviour = accept
    await wait_for(lambda: coordinator.connected)


def test_psk_mismatch_detection() -> None:
    """Only TLS alerts about the key count as a rejected key."""

    def failed(reason: str | None) -> ConnectionFailedError:
        os_error = ssl.SSLError(1, f"[SSL: {reason}] alert")
        if reason:
            os_error.reason = reason
        exc = ConnectionFailedError("Failed to connect to Appliance")
        exc.__cause__ = aiohttp.ClientConnectorSSLError(Mock(ssl=True), os_error)
        return exc

    assert _is_psk_mismatch(failed("SSLV3_ALERT_BAD_RECORD_MAC"))
    assert _is_psk_mismatch(failed("TLSV1_ALERT_DECRYPT_ERROR"))
    assert not _is_psk_mismatch(failed("CERTIFICATE_VERIFY_FAILED"))
    assert not _is_psk_mismatch(failed(None))
    assert not _is_psk_mismatch(ConnectionFailedError())
    refused = ConnectionRefusedError(61, "Connection refused")
    assert not _is_psk_mismatch(aiohttp.ClientConnectorError(Mock(ssl=True), refused))


@pytest.mark.parametrize("behaviour", [wrong_identity])
async def test_wrong_device_creates_issue(
    hass: HomeAssistant,
    setup_device: Callable[[Behaviour], Awaitable[tuple[FakeDevice, MockConfigEntry]]],
    fast: None,
    behaviour: Behaviour,
) -> None:
    """Another device at the configured address: repair issue and rare retries."""
    device, entry = await setup_device(behaviour)
    coordinator = entry.runtime_data.coordinator

    await wait_for(lambda: device.connects >= 2)
    assert not issue_exists(hass, const.ISSUE_WRONG_DEVICE, entry)

    await wait_for(lambda: issue_exists(hass, const.ISSUE_WRONG_DEVICE, entry))
    assert device.connects == const.IDENTITY_FAILURE_THRESHOLD
    assert not coordinator.connected
    # The wrong appliance is disconnected again
    assert device.closes == device.connects
    assert not device.appliance.session.connected

    # Following attempts are rare
    await wait_for(lambda: device.connects >= const.IDENTITY_FAILURE_THRESHOLD + 2)
    gaps = [b - a for a, b in zip(device.connect_times[2:], device.connect_times[3:], strict=False)]
    assert all(gap >= const.IDENTITY_RETRY_DELAY * 0.8 for gap in gaps)

    # The right appliance is back
    device.appliance.info["mac"] = EXPECTED_MAC
    device.behaviour = accept
    await wait_for(lambda: coordinator.connected)
    assert not issue_exists(hass, const.ISSUE_WRONG_DEVICE, entry)


async def test_reconnect_after_stable_connection(
    hass: HomeAssistant,
    setup_device: Callable[[Behaviour], Awaitable[tuple[FakeDevice, MockConfigEntry]]],
    monkeypatch: pytest.MonkeyPatch,
    fast: None,
) -> None:
    """A dropped connection is re-established, the backoff resets after a stable one."""
    monkeypatch.setattr(const, "STABLE_CONNECTION_TIME", 0)
    backoff_failures: list[int] = []
    real_backoff = HomeConnectCoordinator._backoff_delay
    monkeypatch.setattr(
        HomeConnectCoordinator,
        "_backoff_delay",
        staticmethod(lambda failures: backoff_failures.append(failures) or real_backoff(failures)),
    )

    device, entry = await setup_device(refuse)
    coordinator = entry.runtime_data.coordinator
    await wait_for(lambda: device.connects >= 5)

    device.behaviour = accept
    await wait_for(lambda: coordinator.connected)
    connects = device.connects
    await asyncio.sleep(0.05)
    assert device.connects == connects  # No reconnects while connected

    backoff_failures.clear()
    await device.drop()
    await wait_for(lambda: device.connects == connects + 1)
    await wait_for(lambda: device.appliance.session.connected)
    assert backoff_failures == [0]
    assert coordinator.connected  # Short interruptions do not make entities unavailable
    assert len(connection_tasks()) == 1


async def test_reconnect_watchdog(
    hass: HomeAssistant,
    setup_device: Callable[[Behaviour], Awaitable[tuple[FakeDevice, MockConfigEntry]]],
    monkeypatch: pytest.MonkeyPatch,
    fast: None,
) -> None:
    """Too many connection attempts per minute pause the entry."""
    monkeypatch.setattr(const, "MAX_CONNECTS_PER_MINUTE", 5)
    monkeypatch.setattr(const, "RECONNECT_STORM_PAUSE", 0.3)
    device, entry = await setup_device(accept_then_drop)

    await wait_for(lambda: issue_exists(hass, const.ISSUE_RECONNECT_STORM, entry))
    assert device.connects == 5
    assert not entry.runtime_data.coordinator.connected
    await asyncio.sleep(0.1)
    assert device.connects == 5  # paused

    device.behaviour = accept
    await wait_for(lambda: entry.runtime_data.coordinator.connected)
    assert not issue_exists(hass, const.ISSUE_RECONNECT_STORM, entry)


async def test_log_throttling(
    hass: HomeAssistant,
    setup_device: Callable[[Behaviour], Awaitable[tuple[FakeDevice, MockConfigEntry]]],
    caplog: pytest.LogCaptureFixture,
    fast: None,
) -> None:
    """A long outage only logs when it starts and when the maximum delay is reached."""
    device, _ = await setup_device(refuse)
    await wait_for(lambda: device.connects >= 200)

    records = [
        record
        for record in caplog.records
        if record.name == "custom_components.homeconnect_ws.coordinator"
        and record.levelno >= logging.INFO
    ]
    assert len(records) == 2
    assert "attempt 1," in records[0].getMessage()


async def test_only_one_connection_loop(
    hass: HomeAssistant,
    setup_device: Callable[[Behaviour], Awaitable[tuple[FakeDevice, MockConfigEntry]]],
    fast: None,
) -> None:
    """Starting the loop again does not create a second loop."""
    _, entry = await setup_device(refuse)
    coordinator = entry.runtime_data.coordinator
    task = coordinator._connection_task

    coordinator._start_connection_loop()
    await coordinator._async_setup()

    assert coordinator._connection_task is task
    assert len(connection_tasks()) == 1


@pytest.mark.parametrize("behaviour", [accept, refuse, hang])
async def test_zeroconf_host_update(
    hass: HomeAssistant,
    setup_device: Callable[[Behaviour], Awaitable[tuple[FakeDevice, MockConfigEntry]]],
    fast: None,
    behaviour: Behaviour,
) -> None:
    """A new address reloads the entry: old loop stopped, exactly one new loop."""
    device, entry = await setup_device(behaviour)
    await wait_for(lambda: device.connects >= 1)
    old_coordinator = entry.runtime_data.coordinator
    old_task = old_coordinator._connection_task

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_ZEROCONF}, data=MOCK_ZEROCONF_DATA
    )
    assert result["type"] is FlowResultType.ABORT
    await hass.async_block_till_done()

    assert entry.data[CONF_HOST] == "127.0.0.2"
    assert entry.state is ConfigEntryState.LOADED
    assert entry.runtime_data.coordinator is not old_coordinator
    assert old_task.done()
    assert len(device.appliances) == 2
    assert device.appliances[0].session.close.await_count >= 1
    assert len(connection_tasks()) == 1


async def test_zeroconf_known_address_does_not_reload(
    hass: HomeAssistant,
    setup_device: Callable[[Behaviour], Awaitable[tuple[FakeDevice, MockConfigEntry]]],
    fast: None,
) -> None:
    """The entry is left alone while its host is still announced by the appliance."""
    device, entry = await setup_device(accept)
    await wait_for(lambda: entry.runtime_data.coordinator.connected)
    coordinator = entry.runtime_data.coordinator

    discovery = deepcopy(MOCK_ZEROCONF_DATA)
    discovery.ip_addresses = [ip_address("127.0.0.2"), ip_address("1.2.3.4")]
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_ZEROCONF}, data=discovery
    )
    assert result["type"] is FlowResultType.ABORT
    await hass.async_block_till_done()

    assert entry.data[CONF_HOST] == "1.2.3.4"
    assert entry.runtime_data.coordinator is coordinator
    assert len(device.appliances) == 1


async def test_zeroconf_other_device_does_not_update(
    hass: HomeAssistant,
    setup_device: Callable[[Behaviour], Awaitable[tuple[FakeDevice, MockConfigEntry]]],
    fast: None,
) -> None:
    """An announcement of a different appliance never changes the entry."""
    device, entry = await setup_device(accept)
    coordinator = entry.runtime_data.coordinator

    discovery = deepcopy(MOCK_ZEROCONF_DATA)
    discovery.properties["id"] = "another_appliance"
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_ZEROCONF}, data=discovery
    )
    assert result["type"] is FlowResultType.FORM
    hass.config_entries.flow.async_abort(result["flow_id"])
    await hass.async_block_till_done()

    assert entry.data[CONF_HOST] == "1.2.3.4"
    assert entry.runtime_data.coordinator is coordinator
    assert len(device.appliances) == 1
