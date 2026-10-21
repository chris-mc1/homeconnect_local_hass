"""Tests for the settings oven entity descriptions."""

from __future__ import annotations

import pytest
from custom_components.homeconnect_ws import entity_descriptions

# (description type, key, entity) of the descriptions that must exist.
EXPECTED = [
    ("switch", "switch_oven_heating_signal", "Cooking.Oven.Setting.HeatingSignal"),
    ("switch", "switch_oven_door_opener_delay", "Cooking.Oven.Setting.DoorOpenerDelay"),
    ("switch", "switch_oven_rotary_spit", "Cooking.Oven.Option.RotarySpit"),
    ("switch", "switch_oven_quick_roast", "Cooking.Oven.Option.QuickRoast"),
    (
        "switch",
        "switch_synchronize_with_time_server",
        "BSH.Common.Setting.SynchronizeWithTimeServer",
    ),
    ("select", "select_oven_idle_screen", "Cooking.Oven.Setting.IdleScreen"),
    ("select", "select_oven_touchkey_color", "Cooking.Oven.Setting.TouchkeyColor"),
    ("select", "select_oven_standby_display", "Cooking.Oven.Setting.StandbyDisplay"),
    ("select", "select_date_format", "BSH.Common.Setting.DateFormat"),
    ("select", "select_time_format", "BSH.Common.Setting.TimeFormat"),
    ("select", "select_weight_unit", "BSH.Common.Setting.WeightUnit"),
    ("select", "select_language", "BSH.Common.Setting.Language"),
]


@pytest.mark.parametrize(("description_type", "key", "entity"), EXPECTED)
def test_description_exists(description_type: str, key: str, entity: str) -> None:
    """Test the description exists and points to the entity the oven reports."""
    descriptions = entity_descriptions.get_all_entity_description()

    description = next(
        d for d in descriptions[description_type] if not callable(d) and d.key == key
    )
    assert description.entity == entity


@pytest.mark.parametrize("key", ["switch_oven_rotary_spit", "switch_oven_quick_roast"])
def test_options_switches_need_oven_on_and_not_operated_locally(key: str) -> None:
    """Test Rotary spit and Quick roast (options) are unavailable when the oven refuses writes."""
    descriptions = entity_descriptions.get_all_entity_description()

    description = next(d for d in descriptions["switch"] if not callable(d) and d.key == key)
    assert description.available_when == [
        ("BSH.Common.Setting.PowerState", {"On"}),
        ("BSH.Common.Status.LocalControlActive", {False}),
    ]
