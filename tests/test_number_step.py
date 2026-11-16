"""Tests for the number step that differs from the step the appliance reports."""

from __future__ import annotations

from unittest.mock import Mock

import pytest
from custom_components.homeconnect_ws import entity_descriptions
from custom_components.homeconnect_ws.number import HCNumber


def _setpoint_number(brand: str, appliance_step: float | None) -> HCNumber:
    """Create the oven setpoint number around a mocked appliance."""
    descriptions = entity_descriptions.get_all_entity_description()
    description = next(
        d
        for d in descriptions["number"]
        if not callable(d) and d.key == "number_oven_setpoint_temperature"
    )
    number = object.__new__(HCNumber)  # skip the Home Assistant setup of the entity
    number.entity_description = description
    number._entity = Mock(step=appliance_step)
    number._runtime_data = Mock()
    number._runtime_data.appliance.info = {"brand": brand}
    return number


@pytest.mark.parametrize(
    ("brand", "expected"),
    [
        ("GAGGENAU", 5),  # reports step 1 but rounds up to a multiple of 5
        ("Gaggenau", 5),
        ("BOSCH", 1),  # step reported by the appliance
    ],
)
def test_setpoint_step(brand: str, expected: float) -> None:
    """Test the setpoint step of the oven depends on the brand."""
    assert _setpoint_number(brand, 1).native_step == expected
