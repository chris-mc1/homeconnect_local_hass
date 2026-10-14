"""Tests for the availability of the oven setpoint temperature."""

from __future__ import annotations

from unittest.mock import Mock

import pytest
from custom_components.homeconnect_ws import entity_descriptions
from custom_components.homeconnect_ws.number import HCNumber
from homeconnect_websocket.entities import Access


def _setpoint_number(
    brand: str,
    power_state: str | None,
    local_control: bool | None,  # noqa: FBT001
) -> HCNumber:
    """Create the oven setpoint number around a mocked appliance."""
    descriptions = entity_descriptions.get_all_entity_description()
    description = next(
        d
        for d in descriptions["number"]
        if not callable(d) and d.key == "number_oven_setpoint_temperature"
    )
    number = object.__new__(HCNumber)  # skip the Home Assistant setup of the entity
    number.entity_description = description
    number._entity = Mock(available=True, access=Access.READ_WRITE)
    number._runtime_data = Mock()
    number._runtime_data.coordinator.connected = True
    number._runtime_data.appliance.info = {"brand": brand}
    number._runtime_data.appliance.entities = {
        "BSH.Common.Setting.PowerState": Mock(value=power_state),
        "BSH.Common.Status.LocalControlActive": Mock(value=local_control),
    }
    return number


@pytest.mark.parametrize(
    ("brand", "power_state", "local_control", "expected"),
    [
        ("GAGGENAU", "On", False, True),
        ("GAGGENAU", "Off", False, False),  # can only be set while the oven is on
        ("Gaggenau", "Standby", False, False),
        ("GAGGENAU", "On", True, False),  # the oven answers 516 while it is operated locally
        ("GAGGENAU", None, None, True),  # unknown, do not hide the entity
        ("BOSCH", "Off", True, True),  # other brands were not tried, nothing changes
    ],
)
def test_setpoint_available_only_when_gaggenau_oven_is_on_and_not_operated_locally(
    brand: str,
    power_state: str | None,
    local_control: bool | None,  # noqa: FBT001
    expected: bool,  # noqa: FBT001
) -> None:
    """Test the setpoint of a Gaggenau oven is only available when the oven accepts writes."""
    assert _setpoint_number(brand, power_state, local_control).available is expected
