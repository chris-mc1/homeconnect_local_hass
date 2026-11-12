"""Tests of the real library against a fake appliance that misbehaves on the network."""

from __future__ import annotations

import asyncio
import json
import ssl
import time
from base64 import urlsafe_b64decode
from copy import deepcopy
from itertools import pairwise
from typing import TYPE_CHECKING
from unittest.mock import Mock

import pytest
import yarl
from aiohttp import web
from custom_components import homeconnect_ws
from custom_components.homeconnect_ws import const
from custom_components.homeconnect_ws.const import CONF_AES_IV, CONF_PSK, DOMAIN
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_HOST
from homeassistant.helpers import issue_registry as ir
from homeconnect_websocket import hc_socket
from homeconnect_websocket.testutils import TEST_PSK64
from pytest_homeassistant_custom_component.common import MockConfigEntry

from .const import DEVICE_DESCRIPTION, MOCK_CONFIG_DATA_2, MOCK_TLS_DEVICE_ID
from .test_coordinator import LoopMonitor, connection_tasks, wait_for

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Awaitable, Callable

    from homeassistant.core import HomeAssistant

OTHER_PSK64 = "c29tZSBvdGhlciBhcHBsaWFuY2UgYW5vdGhlciBrZXkh"
MAX_LOOP_BLOCK = 0.1
INIT_MESSAGE = {
    "sID": 1,
    "msgID": 1,
    "resource": "/ei/initialValues",
    "version": 2,
    "action": "POST",
    "data": [{"edMsgID": 10}],
}
SERVICES = [{"service": "ci", "version": 3}, {"service": "ei", "version": 2}]


class FakeAppliance:
    """
    TLS-PSK appliance with selectable behaviour.

    close:        close the connection right after accepting it
    silent:       accept the connection, then do nothing at all
    no_handshake: accept the websocket, never answer the handshake
    drop:         close the connection as soon as it is completely set up
    wrong_mac:    complete the handshake, report another MAC address
    ok:           behave
    """

    def __init__(self, behaviour: str) -> None:
        """Create the appliance."""
        self.behaviour = behaviour
        self.port = 0
        self.connect_times: list[float] = []
        self.open_connections = 0

    @property
    def connections(self) -> int:
        """Number of connections made."""
        return len(self.connect_times)

    async def handler(self, request: web.Request) -> web.StreamResponse:
        """Handle a connection."""
        self.connect_times.append(time.monotonic())
        if self.behaviour == "close":
            request.transport.close()
            return web.Response()
        self.open_connections += 1
        ws = web.WebSocketResponse()
        try:
            if self.behaviour == "silent":
                await asyncio.Event().wait()
            await ws.prepare(request)
            if self.behaviour != "no_handshake":
                await ws.send_str(json.dumps(INIT_MESSAGE))
            async for raw in ws:
                if self.behaviour == "no_handshake":
                    continue
                message = json.loads(raw.data)
                if message["action"] != "GET":
                    continue
                message["action"] = "RESPONSE"
                message["data"] = []
                if message["resource"] == "/ci/services":
                    message["data"] = SERVICES
                    if self.behaviour == "wrong_mac":
                        message["data"] = [*SERVICES, {"service": "iz", "version": 1}]
                elif message["resource"] == "/iz/info":
                    message["data"] = [{"mac": "00-11-22-33-44-55"}]
                await ws.send_str(json.dumps(message))
                if self.behaviour == "drop" and message["resource"] == "/ro/allMandatoryValues":
                    break  # Last request after connecting
        finally:
            self.open_connections -= 1
        return ws


@pytest.fixture
def expected_lingering_timers() -> bool:
    """Allow timers: aiohttp re-arms a websocket's heartbeat when data arrives while closing."""
    return True


@pytest.fixture
async def setup_appliance(
    hass: HomeAssistant,
    monkeypatch: pytest.MonkeyPatch,
    socket_enabled: None,
) -> AsyncGenerator[Callable[..., Awaitable[tuple[FakeAppliance, MockConfigEntry]]]]:
    """Set up a config entry connected to a fake appliance on localhost."""
    monkeypatch.setattr(const, "RECONNECT_DELAY_INITIAL", 0.05)
    monkeypatch.setattr(const, "RECONNECT_DELAY_MAX", 0.4)
    monkeypatch.setattr(const, "RECONNECT_JITTER", 0)
    monkeypatch.setattr(const, "CONNECT_TIMEOUT", 0.3)
    monkeypatch.setattr(const, "IDENTITY_RETRY_DELAY", 1)
    monkeypatch.setattr(const, "MAX_CONNECTS_PER_MINUTE", 10**9)
    runners: list[web.AppRunner] = []

    # The fake appliance runs in the same event loop: a TLS handshake it rejects
    # (wrong key) is reported to the loop's exception handler.
    handler = hass.loop.get_exception_handler()

    def ignore_server_tls_errors(loop: asyncio.AbstractEventLoop, context: dict) -> None:
        if not isinstance(context.get("exception"), ssl.SSLError):
            handler(loop, context)

    hass.loop.set_exception_handler(ignore_server_tls_errors)
    entries: list[MockConfigEntry] = []

    async def go(
        behaviour: str, server_psk64: str = TEST_PSK64
    ) -> tuple[FakeAppliance, MockConfigEntry]:
        appliance = FakeAppliance(behaviour)
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ssl_context.maximum_version = ssl.TLSVersion.TLSv1_2
        ssl_context.set_ciphers("ALL")
        psk = urlsafe_b64decode(server_psk64 + "===")
        ssl_context.set_psk_server_callback(lambda _: psk)

        app = web.Application()
        app.add_routes([web.get("/homeconnect", appliance.handler)])
        runner = web.AppRunner(app, handler_cancellation=True)
        await runner.setup()
        site = web.TCPSite(runner, "127.0.0.1", 0, ssl_context=ssl_context)
        await site.start()
        runners.append(runner)
        appliance.port = site._server.sockets[0].getsockname()[1]
        monkeypatch.setattr(
            hc_socket,
            "_make_url",
            lambda host, ssl: yarl.URL.build(  # noqa: ARG005
                scheme="wss", host=host, port=appliance.port, path="/homeconnect"
            ),
        )

        description = deepcopy(DEVICE_DESCRIPTION)
        description["info"]["mac"] = "C8-D7-78-43-F2-23"
        monkeypatch.setattr(homeconnect_ws, "load_description", Mock(return_value=description))
        data = dict(MOCK_CONFIG_DATA_2) | {CONF_HOST: "127.0.0.1", CONF_PSK: TEST_PSK64}
        data.pop(CONF_AES_IV)
        entry = MockConfigEntry(domain=DOMAIN, data=data, unique_id=MOCK_TLS_DEVICE_ID, version=2)
        entry.add_to_hass(hass)
        assert await hass.config_entries.async_setup(entry.entry_id)
        entries.append(entry)
        return appliance, entry

    yield go

    for entry in entries:
        if entry.state is ConfigEntryState.LOADED:
            await hass.config_entries.async_unload(entry.entry_id)
    for runner in runners:
        await runner.cleanup()
    hass.loop.set_exception_handler(handler)


async def test_connect(
    hass: HomeAssistant,
    setup_appliance: Callable[..., Awaitable[tuple[FakeAppliance, MockConfigEntry]]],
) -> None:
    """The fake appliance is usable: connect, stay connected, unload."""
    appliance, entry = await setup_appliance("ok")
    coordinator = entry.runtime_data.coordinator

    await wait_for(lambda: coordinator.connected)
    await asyncio.sleep(0.3)
    assert appliance.connections == 1
    assert coordinator.appliance.session.connected

    assert await hass.config_entries.async_unload(entry.entry_id)
    await wait_for(lambda: appliance.open_connections == 0)


@pytest.mark.parametrize("behaviour", ["close", "silent", "no_handshake", "drop"])
async def test_misbehaving_appliance(
    hass: HomeAssistant,
    setup_appliance: Callable[..., Awaitable[tuple[FakeAppliance, MockConfigEntry]]],
    behaviour: str,
) -> None:
    """The event loop stays responsive, attempts back off, nothing accumulates."""
    appliance, entry = await setup_appliance(behaviour)
    await wait_for(lambda: appliance.connections >= 2)
    tasks_before = len(asyncio.all_tasks())
    monitor = LoopMonitor()

    await wait_for(lambda: appliance.connections >= 12, timeout=30)

    monitor.stop()
    assert monitor.max_block < MAX_LOOP_BLOCK
    # aiohttp retries a request once when the server closes the connection
    # without an answer: only look at the first connection of an attempt.
    attempts = appliance.connect_times[:1]
    for connect_time in appliance.connect_times[1:]:
        if connect_time - attempts[-1] > 0.03:
            attempts.append(connect_time)
    gaps = [b - a for a, b in pairwise(attempts)]
    assert len(gaps) >= 4
    assert all(gap >= 0.045 for gap in gaps), gaps
    assert all(gap >= 0.36 for gap in gaps[4:]), gaps
    assert appliance.open_connections <= 1
    assert len(asyncio.all_tasks()) <= tasks_before + 3
    assert len(connection_tasks()) == 1
    assert entry.state is ConfigEntryState.LOADED

    assert await hass.config_entries.async_unload(entry.entry_id)
    assert not connection_tasks()
    await wait_for(lambda: appliance.open_connections == 0)
    connections = appliance.connections
    await asyncio.sleep(0.3)
    assert appliance.connections == connections


@pytest.mark.parametrize(
    ("behaviour", "server_psk64"), [("ok", OTHER_PSK64), ("wrong_mac", TEST_PSK64)]
)
async def test_other_appliance_answers(
    hass: HomeAssistant,
    setup_appliance: Callable[..., Awaitable[tuple[FakeAppliance, MockConfigEntry]]],
    monkeypatch: pytest.MonkeyPatch,
    behaviour: str,
    server_psk64: str,
) -> None:
    """Another appliance (other key or other MAC) at the address: issue, rare retries."""
    if behaviour == "wrong_mac":
        # homeconnect-websocket 1.5.5 needs 20 s to close a session while its
        # initial requests are unanswered, only wait for that once.
        monkeypatch.setattr(const, "IDENTITY_FAILURE_THRESHOLD", 1)
    appliance, entry = await setup_appliance(behaviour, server_psk64)
    coordinator = entry.runtime_data.coordinator
    issue_id = f"{const.ISSUE_WRONG_DEVICE}_{entry.entry_id}"
    monitor = LoopMonitor()

    await wait_for(
        lambda: ir.async_get(hass).async_get_issue(DOMAIN, issue_id) is not None, timeout=40
    )
    await wait_for(lambda: appliance.open_connections == 0)
    connections = appliance.connections
    await asyncio.sleep(0.5)

    monitor.stop()
    assert monitor.max_block < MAX_LOOP_BLOCK
    assert appliance.connections == connections
    assert not coordinator.connected
    assert not coordinator.appliance.session.connected
