"""Tests for number entities that show the raw value of an enumeration entity."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, Mock

import pytest
from custom_components.homeconnect_ws import entity_descriptions
from custom_components.homeconnect_ws.number import HCNumber
from homeconnect_websocket.entities import Access

if TYPE_CHECKING:
    from custom_components.homeconnect_ws.entity_descriptions import HCNumberEntityDescription


def _meatprobe_description() -> HCNumberEntityDescription:
    """Return the description of the meat probe target temperature."""
    descriptions = entity_descriptions.get_all_entity_description()
    return next(
        d
        for d in descriptions["number"]
        if not callable(d) and d.key == "number_oven_meatprobe_temperature"
    )


def _number(raw_value: int | None) -> HCNumber:
    """Create the meat probe number around a mocked appliance entity."""
    number = object.__new__(HCNumber)  # skip the Home Assistant setup of the entity
    number.entity_description = _meatprobe_description()
    number._entity = Mock(
        value_raw=raw_value,
        value="60dC",  # the label of the enumeration, not a number
        min=None,
        max=None,
        step=None,
        set_value_raw=AsyncMock(),
        set_value=AsyncMock(),
    )
    return number


def test_meatprobe_description() -> None:
    """Test the meat probe temperature is a number for the enumeration entity."""
    description = _meatprobe_description()
    assert description.entity == "Cooking.Oven.Option.MeatProbeTemperatureV2"
    assert description.use_raw_value
    assert description.raw_value_off_below == 15


@pytest.mark.parametrize(
    ("raw_value", "expected"),
    [
        (0, 0),  # Off
        (60, 60),  # "60dC"
        (99, 99),  # highest entry in degrees Celsius
        (1140, None),  # Fahrenheit entry of the enumeration
        (None, None),  # no value known (probe not plugged in)
    ],
)
def test_native_value_is_raw_value(raw_value: int | None, expected: int | None) -> None:
    """Test the number shows the raw value instead of the label of the enumeration."""
    assert _number(raw_value).native_value == expected


@pytest.mark.parametrize(
    ("value", "expected_raw"),
    [
        (60, 60),
        (15, 15),
        (99, 99),
        (14, 0),  # no such entry in the enumeration, 0 is Off
        (0, 0),
    ],
)
async def test_set_native_value_writes_raw_value(value: float, expected_raw: int) -> None:
    """Test the raw value is written, not the label of the enumeration."""
    number = _number(0)

    await number.async_set_native_value(value)

    number._entity.set_value_raw.assert_awaited_once_with(expected_raw)
    number._entity.set_value.assert_not_called()


def _with_power_state(number: HCNumber, power_state: str | None) -> HCNumber:
    """Give the number a mocked appliance with the given PowerState value."""
    power = Mock(value=power_state)
    number._runtime_data = Mock()
    number._runtime_data.coordinator.connected = True
    number._runtime_data.appliance.entities = {"BSH.Common.Setting.PowerState": power}
    number._entity.available = True
    number._entity.access = Access.READ_WRITE
    return number


@pytest.mark.parametrize(
    ("power_state", "expected"),
    [
        ("On", True),
        ("Off", False),  # the oven answers 516 for the meat probe temperature
        ("Standby", False),
        (None, True),  # unknown, do not hide the entity
    ],
)
def test_meatprobe_available_only_when_oven_is_on(
    power_state: str | None,
    expected: bool,  # noqa: FBT001
) -> None:
    """Test the meat probe temperature is unavailable while the oven is switched off."""
    number = _with_power_state(_number(60), power_state)

    assert number.available is expected
