"""Tests for the availability of options that the program does not use."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import Mock

import pytest
from custom_components import homeconnect_ws
from custom_components.homeconnect_ws import entity_descriptions
from custom_components.homeconnect_ws.entity_descriptions.descriptions_definitions import (
    HCNumberEntityDescription,
)
from homeassistant.const import STATE_UNAVAILABLE

from . import setup_config_entry
from .const import CONFIG_ENTRIES, ENTITY_DESCRIPTIONS

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeconnect_websocket.testutils import MockAppliance

# Test.Option1 (401) is an option of the test programs 500-502, Test.FanSpeed1 (403) is not
USED_OPTION = "number.fake_brand_homeappliance_used_option"
UNUSED_OPTION = "number.fake_brand_homeappliance_unused_option"


@pytest.fixture
def patch_option_numbers(monkeypatch: pytest.MonkeyPatch) -> None:
    """Add a number for an option that the programs use and one they don't."""
    descriptions = {
        **ENTITY_DESCRIPTIONS,
        "number": [
            HCNumberEntityDescription(
                key="Test.UsedOption", name="Used Option", entity="Test.Option1"
            ),
            HCNumberEntityDescription(
                key="Test.UnusedOption", name="Unused Option", entity="Test.FanSpeed1"
            ),
        ],
    }
    monkeypatch.setattr(
        entity_descriptions, "get_available_entities", Mock(return_value=descriptions)
    )
    monkeypatch.setattr(homeconnect_ws, "get_available_entities", Mock(return_value=descriptions))


async def test_no_program(
    hass: HomeAssistant,
    mock_appliance: MockAppliance,
    patch_option_numbers: None,
) -> None:
    """Without a selected or active program, options are available as before."""
    assert await setup_config_entry(hass, CONFIG_ENTRIES[0])
    await mock_appliance.entities["Test.SelectedProgram"].update({"value": 0})
    await mock_appliance.entities["Test.ActiveProgram"].update({"value": 0})
    await hass.async_block_till_done()

    assert hass.states.get(USED_OPTION).state != STATE_UNAVAILABLE
    assert hass.states.get(UNUSED_OPTION).state != STATE_UNAVAILABLE


async def test_selected_program(
    hass: HomeAssistant,
    mock_appliance: MockAppliance,
    patch_option_numbers: None,
) -> None:
    """An option the selected program does not use is unavailable."""
    assert await setup_config_entry(hass, CONFIG_ENTRIES[0])

    await mock_appliance.entities["Test.SelectedProgram"].update({"value": 500})
    await hass.async_block_till_done()
    assert hass.states.get(USED_OPTION).state != STATE_UNAVAILABLE
    assert hass.states.get(UNUSED_OPTION).state == STATE_UNAVAILABLE

    # Deselecting the program makes it available again
    await mock_appliance.entities["Test.SelectedProgram"].update({"value": 0})
    await hass.async_block_till_done()
    assert hass.states.get(UNUSED_OPTION).state != STATE_UNAVAILABLE


async def test_active_program(
    hass: HomeAssistant,
    mock_appliance: MockAppliance,
    patch_option_numbers: None,
) -> None:
    """An option the active program does not use is unavailable."""
    assert await setup_config_entry(hass, CONFIG_ENTRIES[0])

    await mock_appliance.entities["Test.SelectedProgram"].update({"value": 0})
    await mock_appliance.entities["Test.ActiveProgram"].update({"value": 501})
    await hass.async_block_till_done()

    assert hass.states.get(USED_OPTION).state != STATE_UNAVAILABLE
    assert hass.states.get(UNUSED_OPTION).state == STATE_UNAVAILABLE


async def test_unavailable_option_stays_unavailable(
    hass: HomeAssistant,
    mock_appliance: MockAppliance,
    patch_option_numbers: None,
) -> None:
    """An option the program uses still follows the availability the appliance reports."""
    assert await setup_config_entry(hass, CONFIG_ENTRIES[0])

    await mock_appliance.entities["Test.SelectedProgram"].update({"value": 500})
    await mock_appliance.entities["Test.Option1"].update({"available": False})
    await hass.async_block_till_done()

    assert hass.states.get(USED_OPTION).state == STATE_UNAVAILABLE
