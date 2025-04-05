"""Tests init."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import Mock

from custom_components.homeconnect_ws import HCData
from custom_components.homeconnect_ws.const import DOMAIN
from pytest_homeassistant_custom_component.common import MockConfigEntry

from .const import DEVICE_DESCRIPTION

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .conftest import MockAppliance


async def setup_config_entry(
    hass: HomeAssistant,
    data: dict[str, Any],
    appliance: MockAppliance,
    unique_id: str = "any",
) -> bool:
    """Do setup of a MockConfigEntry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=data,
        unique_id=unique_id,
    )
    entry.runtime_data = HCData(appliance, Mock(), DEVICE_DESCRIPTION)
    entry.add_to_hass(hass)
    result = await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return result
