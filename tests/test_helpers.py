"""Helper functions."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

import pytest
from custom_components.homeconnect_ws.helpers import (
    EntityMatch,
    error_decorator,
    get_entities_from_regex,
    get_groups_from_regex,
)
from homeassistant.exceptions import HomeAssistantError

from .const import DEVICE_DESCRIPTION

if TYPE_CHECKING:
    from homeconnect_websocket.testutils import MockApplianceType


async def test_get_entities_from_regex(mock_homeconnect_appliance: MockApplianceType) -> None:
    """Test get_entities_from_regex helper."""
    appliance = await mock_homeconnect_appliance(description=DEVICE_DESCRIPTION)
    pattern = re.compile(r"^Test\.RegEx\.(.*)\..*$")
    result = get_entities_from_regex(appliance, pattern)
    assert result == [
        EntityMatch(entity="Test.RegEx.001.Sensor", groups=("001",)),
        EntityMatch(entity="Test.RegEx.002.Sensor", groups=("002",)),
        EntityMatch(entity="Test.RegEx.001.Switch", groups=("001",)),
        EntityMatch(entity="Test.RegEx.002.Switch", groups=("002",)),
    ]


async def test_get_groups_from_regex(mock_homeconnect_appliance: MockApplianceType) -> None:
    """Test get_groups_from_regex helper."""
    appliance = await mock_homeconnect_appliance(description=DEVICE_DESCRIPTION)
    pattern = re.compile(r"^Test\.RegEx\.(.*)\..*$")
    result = get_groups_from_regex(appliance, pattern)
    assert result == {("001",), ("002",)}


async def test_error_decorator_turns_a_timeout_into_a_home_assistant_error() -> None:
    """A command that times out raises HomeAssistantError, so automations can continue."""

    @error_decorator
    async def command() -> None:
        raise TimeoutError

    with pytest.raises(HomeAssistantError):
        await command()
