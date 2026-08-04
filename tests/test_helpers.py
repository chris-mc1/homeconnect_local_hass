"""Helper functions."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from custom_components.homeconnect_ws.helpers import (
    EntityMatch,
    build_program_options,
    entity_is_available,
    get_entities_from_regex,
    get_groups_from_regex,
)
from homeconnect_websocket.entities import Access

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


async def test_entity_is_available(mock_homeconnect_appliance: MockApplianceType) -> None:
    """Test entity_is_available helper."""
    appliance = await mock_homeconnect_appliance(description=DEVICE_DESCRIPTION)
    entity = appliance.entities["Test.Option1"]
    assert entity_is_available(entity, (Access.READ_WRITE,))

    await entity.update({"access": "Read"})
    assert not entity_is_available(entity, (Access.READ_WRITE,))
    assert entity_is_available(entity, (Access.READ, Access.READ_WRITE))

    await entity.update({"access": "readwrite", "available": False})
    assert not entity_is_available(entity, (Access.READ_WRITE,))


async def test_build_program_options(mock_homeconnect_appliance: MockApplianceType) -> None:
    """Test build_program_options helper."""
    appliance = await mock_homeconnect_appliance(description=DEVICE_DESCRIPTION)
    program = appliance.programs["Test.Program.Program1"]

    # no option has a value yet, sending them as null gets the request rejected
    assert build_program_options(program) == {}

    await appliance.entities["Test.Option1"].update({"value": 0})
    assert build_program_options(program) == {401: 0}

    await appliance.entities["Test.Option2"].update({"value": 2})
    assert build_program_options(program) == {401: 0, 402: 2}

    await appliance.entities["Test.Option1"].update({"access": "Read"})
    assert build_program_options(program) == {402: 2}
