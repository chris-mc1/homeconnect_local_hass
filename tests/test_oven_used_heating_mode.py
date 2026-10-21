"""Tests for the sensor of the heating mode that an automatic dish uses."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import Mock

from custom_components.homeconnect_ws.entity_descriptions import get_available_entities
from custom_components.homeconnect_ws.sensor import HCSensor
from homeconnect_websocket.entities import Access, DeviceDescription, EntityDescription

if TYPE_CHECKING:
    from homeconnect_websocket.testutils import MockApplianceType

# As on the Gaggenau BO470112 and BS474112: access "none" in the description, the oven makes the
# option available (with a value) only while an automatic dish runs.
USED_HEATING_MODE = DeviceDescription(
    option=[
        EntityDescription(
            uid=5127,
            name="Cooking.Oven.Option.UsedHeatingMode",
            access=Access.NONE,
            available=False,
            enumeration={"0": "AutomaticOperation", "10": "HotAir"},
        )
    ]
)

ENTITY = "Cooking.Oven.Option.UsedHeatingMode"


async def test_sensor_instead_of_select(mock_homeconnect_appliance: MockApplianceType) -> None:
    """The option has a sensor and no select (a select needs write access)."""
    appliance = await mock_homeconnect_appliance(description=USED_HEATING_MODE)

    available = get_available_entities(appliance)

    assert "sensor_oven_used_heating_mode" in {d.key for d in available["sensor"]}
    assert "select_oven_used_heating_mode" not in {d.key for d in available["select"]}


async def test_sensor_follows_the_option(mock_homeconnect_appliance: MockApplianceType) -> None:
    """The sensor is unavailable until the oven makes the option available, then it has a value."""
    appliance = await mock_homeconnect_appliance(description=USED_HEATING_MODE)
    description = next(
        d
        for d in get_available_entities(appliance)["sensor"]
        if d.key == "sensor_oven_used_heating_mode"
    )
    appliance.info = {"deviceID": "Fake_deviceID"}
    runtime_data = Mock()
    runtime_data.appliance = appliance
    runtime_data.coordinator.connected = True
    sensor = HCSensor(description, runtime_data)

    # No automatic dish runs: the oven reports the option as not available.
    assert sensor.available is False
    assert sensor.native_value is None

    # An automatic dish runs: available with the value "AutomaticOperation".
    await appliance.entities[ENTITY].update({"available": True, "value": 0})
    assert sensor.available is True
    assert sensor.native_value == "automaticoperation"
    assert "automaticoperation" in sensor.options
