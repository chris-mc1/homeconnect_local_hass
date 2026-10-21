"""Tests for current, unambiguous favourite program labels."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from custom_components.homeconnect_ws.program_names import program_labels


@pytest.mark.parametrize("value", [None, "", "  ", 123, {}])
def test_missing_name(value: object) -> None:
    """Retain the slot fallback for missing or invalid names."""
    appliance = Mock()
    appliance.settings = {"BSH.Common.Setting.Favorite.001.Name": SimpleNamespace(value=value)}
    assert program_labels(appliance, {"BSH.Common.Program.Favorite.001": "Old Name"}) == {
        "BSH.Common.Program.Favorite.001": "favorite_001"
    }


def test_duplicate_names() -> None:
    """Disambiguate favourites without changing ordinary program identifiers."""
    appliance = Mock()
    appliance.settings = {
        "BSH.Common.Setting.Favorite.001.Name": SimpleNamespace(value="coffee"),
        "BSH.Common.Setting.Favorite.002.Name": SimpleNamespace(value="coffee"),
    }
    labels = program_labels(
        appliance,
        {
            "BSH.Common.Program.Favorite.001": "favorite_001",
            "BSH.Common.Program.Favorite.002": "favorite_002",
            "Coffee": "coffee",
            "Other": "coffee (001)",
        },
    )
    assert len(set(labels.values())) == len(labels)
    assert labels["Coffee"] == "coffee"
    assert labels["Other"] == "coffee (001)"
    assert labels["BSH.Common.Program.Favorite.002"] == "coffee (002)"
