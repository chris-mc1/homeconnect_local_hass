"""Tests for the names of the oven programs in the translations."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

TRANSLATIONS = Path(__file__).parent.parent / "custom_components/homeconnect_ws/translations"

# Heating modes and the cleaning programme of the Gaggenau BO470112 and BS474112 that had no
# name (the program select showed the raw key). The names are from the Gaggenau manuals.
OVEN_PROGRAMS = (
    "cooking_oven_program_heatingmode_topheat",
    "cooking_oven_program_heatingmode_topthirdbottomheat",
    "cooking_oven_program_heatingmode_thirdtopbottomheat",
    "cooking_oven_program_heatingmode_hotairbottomheat",
    "cooking_oven_program_heatingmode_hotairthirdbottomheat",
    "cooking_oven_program_heatingmode_roaster",
    "cooking_oven_program_heatingmode_doughproving",
    "cooking_oven_program_heatingmode_hotair100steam",
    "cooking_oven_program_heatingmode_hotair80steam",
    "cooking_oven_program_heatingmode_hotair60steam",
    "cooking_oven_program_heatingmode_hotair30steam",
    "cooking_oven_program_heatingmode_slowcooksteam",
    "cooking_oven_program_heatingmode_vaccumcooking",
    "cooking_oven_program_heatingmode_fullgrill01steam",
    "cooking_oven_program_heatingmode_fullgrill02steam",
    "cooking_oven_program_heatingmode_regenerating",
    "cooking_oven_program_heatingmode_defrost",
    "cooking_oven_program_cleaning_cleaningprogram",
    "cooking_oven_program_cleaning_descale",
)


@pytest.mark.parametrize("language", ["en", "nl"])
@pytest.mark.parametrize(
    ("platform", "entity"),
    [("select", "select_program"), ("sensor", "sensor_active_program")],
)
def test_oven_program_names(language: str, platform: str, entity: str) -> None:
    """The program select and the active program sensor have a name for each oven program."""
    translations = json.loads((TRANSLATIONS / f"{language}.json").read_text(encoding="utf-8"))
    states = translations["entity"][platform][entity]["state"]

    missing = [program for program in OVEN_PROGRAMS if not states.get(program)]

    assert not missing
