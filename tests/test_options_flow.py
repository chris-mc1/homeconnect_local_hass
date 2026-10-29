"""Tests for saved-favourite display options."""

from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.homeconnect_ws.const import CONF_FILTER_UNSAVED_FAVORITES, DOMAIN
from homeassistant.data_entry_flow import FlowResultType
from homeconnect_websocket.entities import Setting
from pytest_homeassistant_custom_component.common import MockConfigEntry

from . import setup_config_entry
from .const import CONFIG_ENTRIES

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeconnect_websocket.testutils import MockAppliance


async def test_options_default_and_preserve(hass: HomeAssistant) -> None:
    """Default off and preserve unrelated saved options."""
    entry = MockConfigEntry(domain=DOMAIN, data={}, options={"other": "keep"})
    entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    assert result["data_schema"]({}) == {CONF_FILTER_UNSAVED_FAVORITES: False}
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={CONF_FILTER_UNSAVED_FAVORITES: True}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options == {"other": "keep", CONF_FILTER_UNSAVED_FAVORITES: True}
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["data_schema"]({}) == {CONF_FILTER_UNSAVED_FAVORITES: True}


async def test_filter_updates_without_reconnect(
    hass: HomeAssistant,
    mock_appliance: MockAppliance,
    patch_entity_description: None,
) -> None:
    """Toggle filtering and save/delete a slot without reloading the appliance."""
    entry = CONFIG_ENTRIES[0]
    favorite = Setting(
        {
            "uid": 32824,
            "name": "BSH.Common.Setting.Favorite.001.Functionality",
            "enumeration": {"0": "Off", "1": "Program"},
            "access": "readwrite",
            "available": True,
            "protocolType": "Integer",
        },
        mock_appliance,
    )
    mock_appliance.settings[favorite.name] = favorite
    assert await setup_config_entry(hass, entry)
    entity_id = "select.fake_brand_homeappliance_selectedprogram"
    favorite = mock_appliance.settings["BSH.Common.Setting.Favorite.001.Functionality"]
    await favorite.update({"value": 0})
    await hass.async_block_till_done()
    assert "Named Favorite" in hass.states.get(entity_id).attributes["options"]
    appliance = entry.runtime_data.appliance
    result = await hass.config_entries.options.async_init(entry.entry_id)
    await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={CONF_FILTER_UNSAVED_FAVORITES: True}
    )
    await hass.async_block_till_done()
    assert entry.runtime_data.appliance is appliance
    options = hass.states.get(entity_id).attributes["options"]
    assert "Named Favorite" not in options
    assert "favorite_002" not in options
    assert "test_program_program1" in options
    await favorite.update({"value": 1})
    await hass.async_block_till_done()
    assert "Named Favorite" in hass.states.get(entity_id).attributes["options"]
    await favorite.update({"value": 0})
    await hass.async_block_till_done()
    assert "Named Favorite" not in hass.states.get(entity_id).attributes["options"]
    result = await hass.config_entries.options.async_init(entry.entry_id)
    await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={CONF_FILTER_UNSAVED_FAVORITES: False}
    )
    await hass.async_block_till_done()
    assert "Named Favorite" in hass.states.get(entity_id).attributes["options"]
    assert "favorite_002" in hass.states.get(entity_id).attributes["options"]
    assert entry.runtime_data.appliance is appliance
