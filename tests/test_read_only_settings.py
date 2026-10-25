"""Tests for leaving out switch, select and number of settings that can not be changed."""

from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.homeconnect_ws import entity_descriptions
from homeconnect_websocket.entities import Access, DeviceDescription, EntityDescription

if TYPE_CHECKING:
    from homeconnect_websocket.testutils import MockApplianceType


def _description(power_state_access: Access) -> DeviceDescription:
    """Appliance with a power state (Off, On), a setting, and an option as on a dishwasher."""
    return DeviceDescription(
        setting=[
            EntityDescription(
                uid=539,
                name="BSH.Common.Setting.PowerState",
                access=power_state_access,
                available=True,
                enumeration={"1": "Off", "2": "On"},
            ),
        ],
        option=[
            # Read only in the description of a dishwasher, writable when a program is selected
            EntityDescription(
                uid=558,
                name="BSH.Common.Option.StartInRelative",
                access=Access.READ,
                available=True,
            ),
        ],
    )


def _keys(descriptions: list) -> set[str]:
    return {description.key for description in descriptions}


async def test_read_only_setting_has_no_switch_or_select(
    mock_homeconnect_appliance: MockApplianceType,
) -> None:
    """A power state that is read only (Gaggenau oven and hob) has only the sensor."""
    appliance = await mock_homeconnect_appliance(description=_description(Access.READ))

    available = entity_descriptions.get_available_entities(appliance)

    assert "switch_power_state" not in _keys(available["switch"])
    assert "select_power_state" not in _keys(available["select"])
    assert "sensor_power_state" in _keys(available["sensor"])


async def test_writable_setting_keeps_switch(
    mock_homeconnect_appliance: MockApplianceType,
) -> None:
    """A power state that can be changed keeps its switch."""
    appliance = await mock_homeconnect_appliance(description=_description(Access.READ_WRITE))

    available = entity_descriptions.get_available_entities(appliance)

    assert "switch_power_state" in _keys(available["switch"])


async def test_read_only_option_keeps_number(
    mock_homeconnect_appliance: MockApplianceType,
) -> None:
    """An option is left in: its access changes with the selected program."""
    appliance = await mock_homeconnect_appliance(description=_description(Access.READ))

    available = entity_descriptions.get_available_entities(appliance)

    assert "number_start_in" in _keys(available["number"])
