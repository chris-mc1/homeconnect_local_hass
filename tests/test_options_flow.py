"""Tests for options flow."""

from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.homeconnect_ws.const import CONF_START_WITHOUT_OPTIONS, DOMAIN
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from .const import MOCK_AES_DEVICE_ID, MOCK_CONFIG_DATA_2

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


async def test_options_flow(hass: HomeAssistant) -> None:
    """Test changing the options."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data=MOCK_CONFIG_DATA_2,
        unique_id=MOCK_AES_DEVICE_ID,
        version=2,
    )
    config_entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(config_entry.entry_id)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={CONF_START_WITHOUT_OPTIONS: True}
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert config_entry.options == {CONF_START_WITHOUT_OPTIONS: True}
