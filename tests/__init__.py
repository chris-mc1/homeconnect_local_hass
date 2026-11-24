"""Tests init."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from custom_components.homeconnect_ws import HCConfigEntry
    from homeassistant.core import HomeAssistant
    from pytest_homeassistant.common import MockConfigEntry


async def setup_config_entry(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
) -> MockConfigEntry | HCConfigEntry:
    """Do setup of a MockConfigEntry."""
    config_entry.add_to_hass(hass)
    result = await hass.config_entries.async_setup(config_entry.entry_id)
    assert result
    await hass.async_block_till_done()
    return config_entry
