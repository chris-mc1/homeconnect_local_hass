"""Tests init."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Self
from unittest.mock import AsyncMock

from custom_components.homeconnect_ws.const import DOMAIN
from homeconnect_websocket import ConnectionState, DeviceDescription
from pytest_homeassistant_custom_component.common import MockConfigEntry

from .const import MOCK_TLS_DEVICE_INFO

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from homeassistant.core import HomeAssistant


class MockAppliance:
    """Mock Appliance for config flow."""

    info = MOCK_TLS_DEVICE_INFO

    def __init__(self, info: dict) -> None:
        self.info = info
        self._connect = AsyncMock()
        self._close = AsyncMock()

    def __call__(  # noqa: PLR0913
        self,
        description: DeviceDescription,
        host: str,
        app_name: str,
        app_id: str,
        psk64: str,
        iv64: str | None = None,
        *,
        connection_callback: Callable[[ConnectionState], Awaitable[None]] | None = None,
    ) -> Self:
        self.description = description
        self.host = host
        self.app_name = app_name
        self.app_id = app_id
        self.psk64 = psk64
        self.iv64 = iv64
        self.connection_callback = connection_callback
        return self

    async def connect(self) -> None:
        await self.connection_callback(ConnectionState.CONNECTING)
        await self.connection_callback(ConnectionState.CONNECTED)
        await self._connect()

    async def close(self) -> None:
        await self.connection_callback(ConnectionState.CLOSING)
        await self.connection_callback(ConnectionState.CLOSED)
        await self._close()


async def setup_config_entry(
    hass: HomeAssistant,
    data: dict[str, Any],
    unique_id: str = "any",
) -> bool:
    """Do setup of a MockConfigEntry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=data,
        unique_id=unique_id,
    )
    entry.add_to_hass(hass)
    result = await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return result
