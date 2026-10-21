"""Tests for the status_binary_sensors oven entity descriptions."""

from __future__ import annotations

import pytest
from custom_components.homeconnect_ws import entity_descriptions

# (description type, key, entity) of the descriptions that must exist.
EXPECTED = [
    ("binary_sensor", "binary_sensor_backend_connected", "BSH.Common.Status.BackendConnected"),
    (
        "binary_sensor",
        "binary_sensor_remote_control_active",
        "BSH.Common.Status.RemoteControlActive",
    ),
    ("binary_sensor", "binary_sensor_local_control_active", "BSH.Common.Status.LocalControlActive"),
    (
        "binary_sensor",
        "binary_sensor_oven_meatprobe_plugged",
        "Cooking.Oven.Status.MeatprobePlugged",
    ),
]


@pytest.mark.parametrize(("description_type", "key", "entity"), EXPECTED)
def test_description_exists(description_type: str, key: str, entity: str) -> None:
    """Test the description exists and points to the entity the oven reports."""
    descriptions = entity_descriptions.get_all_entity_description()

    description = next(
        d for d in descriptions[description_type] if not callable(d) and d.key == key
    )
    assert description.entity == entity
