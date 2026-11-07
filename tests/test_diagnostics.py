"""Tests for diagnostics."""

from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.homeconnect_ws.diagnostics import async_get_config_entry_diagnostics
from homeassistant.components.diagnostics import REDACTED

from . import setup_config_entry
from .const import CONFIG_ENTRIES

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeconnect_websocket.testutils import MockAppliance


async def test_diagnostics(
    hass: HomeAssistant,
    mock_appliance: MockAppliance,
    patch_entity_description: None,
) -> None:
    """Test diagnostics redact secrets and include the appliance state."""
    entry = CONFIG_ENTRIES[0]
    assert await setup_config_entry(hass, entry)

    diagnostics = await async_get_config_entry_diagnostics(hass, entry)

    entry_data = diagnostics["entry_data"]
    assert entry_data["psk"] == REDACTED
    assert entry_data["aes_iv"] == REDACTED
    assert entry_data["device_id"] == REDACTED
    assert entry_data["host"] == "1.2.3.4"
    assert "PSK_KEY" not in str(diagnostics)
    assert "AES_IV" not in str(diagnostics)
    assert diagnostics["appliance_state"] == mock_appliance.dump()
