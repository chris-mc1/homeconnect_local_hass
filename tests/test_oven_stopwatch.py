"""Tests for the stopwatch oven entity descriptions."""

from __future__ import annotations

import pytest
from custom_components.homeconnect_ws import entity_descriptions

# (description type, key, entity) of the descriptions that must exist.
EXPECTED = [
    ("sensor", "sensor_stopwatch_time", "BSH.Common.Status.StopWatchTime"),
    ("sensor", "sensor_stopwatch_state", "BSH.Common.Status.StopWatchState"),
    (
        "button",
        "button_stopwatch_start_pause_resume",
        "BSH.Common.Command.StopWatchStartPauseResume",
    ),
    ("button", "button_stopwatch_reset", "BSH.Common.Command.StopWatchReset"),
]


@pytest.mark.parametrize(("description_type", "key", "entity"), EXPECTED)
def test_description_exists(description_type: str, key: str, entity: str) -> None:
    """Test the description exists and points to the entity the oven reports."""
    descriptions = entity_descriptions.get_all_entity_description()

    description = next(
        d for d in descriptions[description_type] if not callable(d) and d.key == key
    )
    assert description.entity == entity
