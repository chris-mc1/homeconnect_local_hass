"""Tests for the switch that shows or hides the automatic dishes in the program select."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import Mock

from custom_components.homeconnect_ws import switch
from custom_components.homeconnect_ws.const import DOMAIN
from custom_components.homeconnect_ws.helpers import has_dish_programs, is_dish_program
from custom_components.homeconnect_ws.select import HCProgram
from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.components.switch import SERVICE_TURN_OFF, SERVICE_TURN_ON
from homeassistant.const import ATTR_ENTITY_ID, STATE_OFF, STATE_ON
from homeassistant.core import State
from homeassistant.helpers import entity_registry as er
from homeconnect_websocket.entities import DeviceDescription, EntityDescription
from pytest_homeassistant_custom_component.common import mock_restore_cache

from . import setup_config_entry
from .const import CONFIG_ENTRIES

if TYPE_CHECKING:
    import pytest
    from homeassistant.core import HomeAssistant
    from homeconnect_websocket.testutils import MockAppliance, MockApplianceType

# Programs as on the Gaggenau ovens: heating modes and automatic dishes.
OVEN_PROGRAMS = DeviceDescription(
    program=[
        EntityDescription(uid=700, name="Cooking.Oven.Program.HeatingMode.HotAir"),
        EntityDescription(uid=701, name="Cooking.Oven.Program.Dish.Automatic.Conv.SeaBream"),
        EntityDescription(uid=702, name="Cooking.Oven.Program.Dish.Automatic.Steam.Risotto"),
    ],
)

# Appliance without automatic dishes, for example a washing machine.
OTHER_PROGRAMS = DeviceDescription(
    program=[EntityDescription(uid=800, name="LaundryCare.Washer.Program.Cotton")],
)

PROGRAM_NAMES = {
    "Cooking.Oven.Program.HeatingMode.HotAir": "cooking_oven_program_heatingmode_hotair",
    "Cooking.Oven.Program.Dish.Automatic.Conv.SeaBream": (
        "cooking_oven_program_dish_automatic_conv_seabream"
    ),
    "Cooking.Oven.Program.Dish.Automatic.Steam.Risotto": (
        "cooking_oven_program_dish_automatic_steam_risotto"
    ),
}

SWITCH_UNIQUE_ID_SUFFIX = "switch_show_dish_programs"


def test_is_dish_program() -> None:
    """Only the programs under Cooking.Oven.Program.Dish are automatic dishes."""
    assert is_dish_program("Cooking.Oven.Program.Dish.Automatic.Conv.SeaBream")
    assert not is_dish_program("Cooking.Oven.Program.HeatingMode.HotAir")
    assert not is_dish_program("BSH.Common.Program.Favorite.001")
    assert not is_dish_program("DishCare.Dishwasher.Program.Eco50")


async def test_has_dish_programs(mock_homeconnect_appliance: MockApplianceType) -> None:
    """The switch is only relevant for an appliance that has automatic dishes."""
    oven = await mock_homeconnect_appliance(description=OVEN_PROGRAMS)
    other = await mock_homeconnect_appliance(description=OTHER_PROGRAMS)

    assert has_dish_programs(oven)
    assert not has_dish_programs(other)


def _program_select(*, show_dish_programs: bool) -> HCProgram:
    """Program select with the value of the switch, without a real appliance."""
    select = object.__new__(HCProgram)
    select._programs = PROGRAM_NAMES
    select._runtime_data = Mock(show_dish_programs=show_dish_programs)
    return select


def test_select_options_show_dishes() -> None:
    """With the switch on all programs are listed."""
    assert _program_select(show_dish_programs=True).options == list(PROGRAM_NAMES.values())


def test_select_options_hide_dishes() -> None:
    """With the switch off (the default) the dishes are left out, the other programs stay."""
    assert _program_select(show_dish_programs=False).options == [
        "cooking_oven_program_heatingmode_hotair"
    ]


def _switch_entity_id(hass: HomeAssistant) -> str | None:
    """Entity id of the show dish programs switch (found by its unique id)."""
    for entry in er.async_get(hass).entities.values():
        if entry.platform == DOMAIN and entry.unique_id.endswith(SWITCH_UNIQUE_ID_SUFFIX):
            return entry.entity_id
    return None


async def test_no_switch_without_dishes(
    hass: HomeAssistant,
    mock_appliance: MockAppliance,
    patch_entity_description: None,
) -> None:
    """An appliance without automatic dishes has no switch."""
    assert await setup_config_entry(hass, CONFIG_ENTRIES[0])

    assert _switch_entity_id(hass) is None


async def test_switch(
    hass: HomeAssistant,
    mock_appliance: MockAppliance,
    patch_entity_description: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The switch is off by default and changes the value that the program select reads."""
    monkeypatch.setattr(switch, "has_dish_programs", lambda _appliance: True)
    entry = CONFIG_ENTRIES[0]
    assert await setup_config_entry(hass, entry)
    entity_id = _switch_entity_id(hass)
    assert entity_id is not None
    assert hass.states.get(entity_id).state == STATE_OFF
    assert entry.runtime_data.show_dish_programs is False

    await hass.services.async_call(
        SWITCH_DOMAIN, SERVICE_TURN_ON, {ATTR_ENTITY_ID: entity_id}, blocking=True
    )
    assert hass.states.get(entity_id).state == STATE_ON
    assert entry.runtime_data.show_dish_programs is True

    await hass.services.async_call(
        SWITCH_DOMAIN, SERVICE_TURN_OFF, {ATTR_ENTITY_ID: entity_id}, blocking=True
    )
    assert hass.states.get(entity_id).state == STATE_OFF
    assert entry.runtime_data.show_dish_programs is False


async def test_switch_restores_state(
    hass: HomeAssistant,
    mock_appliance: MockAppliance,
    patch_entity_description: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A switch that was on before a restart is on again (the default is off)."""
    monkeypatch.setattr(switch, "has_dish_programs", lambda _appliance: True)
    entry = CONFIG_ENTRIES[0]
    assert await setup_config_entry(hass, entry)
    entity_id = _switch_entity_id(hass)

    # Restart: unload the entry, put the last state in the cache and set the entry up again.
    assert await hass.config_entries.async_unload(entry.entry_id)
    mock_restore_cache(hass, [State(entity_id, STATE_ON)])
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert hass.states.get(entity_id).state == STATE_ON
    assert entry.runtime_data.show_dish_programs is True
