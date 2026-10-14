"""Tests for the options that are sent when a program is selected or started."""

from __future__ import annotations

from unittest.mock import Mock

from custom_components.homeconnect_ws.helpers import valid_program_options
from homeconnect_websocket.entities import Access


def _option(
    uid: int,
    value: object = None,
    *,
    access: Access = Access.READ_WRITE,
    available: bool | None = True,
    minimum: float | None = None,
    maximum: float | None = None,
) -> Mock:
    """Create a mocked option entity."""
    return Mock(
        uid=uid,
        value_shadow=value,
        access=access,
        available=available,
        min=minimum,
        max=maximum,
    )


def test_valid_program_options() -> None:
    """Test only the options the appliance accepts are sent."""
    program = Mock(
        _options=[
            _option(5120, 170, minimum=30, maximum=300),  # setpoint, in range
            _option(5130, None, minimum=85, maximum=550),  # Fahrenheit setpoint, no value
            _option(548, 0, minimum=1, maximum=86400),  # duration below the minimum
            _option(549, 100000, minimum=1, maximum=86400),  # duration above the maximum
            _option(558, 0, minimum=0, maximum=86340),  # start in, 0 is in range
            _option(5131, value=False),  # bool is kept, also when False
            _option(5144, 0, available=False),  # not available (meat probe not plugged in)
            _option(5145, 1, access=Access.READ),  # not writable
            _option(5146, "Medium", available=None),  # availability unknown is not "not available"
        ]
    )

    assert valid_program_options(program) == {
        5120: 170,
        558: 0,
        5131: False,
        5146: "Medium",
    }


def test_gaggenau_gets_no_options() -> None:
    """Test a Gaggenau oven gets no options, it uses the values of the program."""
    program = Mock(
        _options=[_option(5120, 50, minimum=30, maximum=300), _option(5131, value=False)]
    )

    assert valid_program_options(program, "GAGGENAU") == {}
    assert valid_program_options(program, "Gaggenau") == {}
    assert valid_program_options(program, "BOSCH") == {5120: 50, 5131: False}
