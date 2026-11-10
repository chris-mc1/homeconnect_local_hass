"""Tests for selecting a program while a program is running."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from custom_components.homeconnect_ws import select
from custom_components.homeconnect_ws.entity_descriptions import HCSelectEntityDescription
from custom_components.homeconnect_ws.select import HCProgram
from homeassistant.exceptions import HomeAssistantError
from homeconnect_websocket.entities import Execution


def _program_select(brand: str, operation_state: str) -> tuple[HCProgram, Mock]:
    """Create the program select around a mocked appliance."""
    description = HCSelectEntityDescription(
        key="select_program",
        entity="BSH.Common.Root.SelectedProgram",
        block_change_while_running_for_brands={"GAGGENAU"},  # as generate_program
        prefer_active_program_for_brands={"GAGGENAU"},
    )
    program = Mock(execution=Execution.SELECT_AND_START, _options=[], select=AsyncMock())
    entity = object.__new__(HCProgram)  # skip the Home Assistant setup of the entity
    entity.entity_description = description
    entity._programs = {"Program.One": "one"}
    entity._rev_programs = {"one": "Program.One"}
    entity._runtime_data = Mock()
    entity._runtime_data.appliance.info = {"brand": brand}
    entity._runtime_data.appliance.programs = {"Program.One": program}
    entity._runtime_data.appliance.entities = {select.OPERATION_STATE: Mock(value=operation_state)}
    return entity, program


@pytest.mark.parametrize("state", ["Run", "Pause", "DelayedStart", "ActionRequired"])
async def test_program_is_not_changed_while_running(state: str) -> None:
    """Test an error instead of a selection the appliance would ignore."""
    entity, program = _program_select("GAGGENAU", state)

    with pytest.raises(HomeAssistantError) as exc_info:
        await entity.async_select_option("one")

    assert exc_info.value.translation_key == "program_running"
    program.select.assert_not_called()


@pytest.mark.parametrize("state", ["Ready", "Inactive", "Finished"])
async def test_program_is_changed_when_nothing_is_running(state: str) -> None:
    """Test the program is selected when nothing is running."""
    entity, program = _program_select("GAGGENAU", state)

    await entity.async_select_option("one")

    program.select.assert_awaited_once()


async def test_other_brand_is_not_blocked() -> None:
    """Test another brand is not blocked, that was not tried."""
    entity, program = _program_select("BOSCH", "Run")

    await entity.async_select_option("one")

    program.select.assert_awaited_once()


def _with_programs(entity: HCProgram, selected: str | None, active: str | None) -> HCProgram:
    """Give the select a selected and an active program."""
    entity._programs = {"Program.One": "one", "Program.Two": "two"}
    appliance = entity._runtime_data.appliance
    appliance.selected_program = SimpleNamespace(name=selected) if selected else None
    appliance.active_program = SimpleNamespace(name=active) if active else None
    return entity


@pytest.mark.parametrize(
    ("brand", "selected", "active", "expected"),
    [
        # Gaggenau: the oven was switched on with another program than the selected one
        ("GAGGENAU", "Program.Two", "Program.One", "one"),
        ("GAGGENAU", "Program.Two", None, "two"),  # nothing active: the selected program
        ("GAGGENAU", None, None, None),
        ("BOSCH", "Program.Two", "Program.One", "two"),  # other brands: as before
    ],
)
def test_current_option_prefers_the_active_program_of_gaggenau(
    brand: str, selected: str | None, active: str | None, expected: str | None
) -> None:
    """Test the shown program is the program the oven runs, not an older selection."""
    entity, _ = _program_select(brand, "Ready")

    assert _with_programs(entity, selected, active).current_option == expected
