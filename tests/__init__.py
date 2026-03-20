"""Tests init."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from custom_components.homeconnect_ws.const import DOMAIN
from pytest_homeassistant_custom_component.common import MockConfigEntry

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


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
