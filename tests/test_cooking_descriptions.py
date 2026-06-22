"""Tests for cooking entity description helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.homeconnect_ws.entity_descriptions.cooking import generate_oven_status
from homeassistant.const import UnitOfTemperature
from homeconnect_websocket.entities import Access, DeviceDescription, EntityDescription

if TYPE_CHECKING:
    from homeconnect_websocket.testutils import MockApplianceType


async def test_generate_oven_status_fahrenheit_cavity(
    mock_homeconnect_appliance: MockApplianceType,
) -> None:
    """US ovens expose Fahrenheit cavity temperatures on the local API."""
    description = DeviceDescription(
        status=[
            EntityDescription(
                uid=1,
                name="Cooking.Oven.Status.Cavity.001.CurrentTemperatureFahrenheit",
                available=True,
                access=Access.READ,
            ),
            EntityDescription(
                uid=2,
                name="Cooking.Oven.Status.Cavity.001.MeatProbeTemperatureFahrenheit",
                available=True,
                access=Access.READ,
            ),
        ]
    )
    appliance = await mock_homeconnect_appliance(description=description)
    descriptions = generate_oven_status(appliance)

    assert len(descriptions["sensor"]) == 2
    assert (
        descriptions["sensor"][0].entity
        == "Cooking.Oven.Status.Cavity.001.CurrentTemperatureFahrenheit"
    )
    assert descriptions["sensor"][0].native_unit_of_measurement == UnitOfTemperature.FAHRENHEIT
    assert (
        descriptions["sensor"][1].entity
        == "Cooking.Oven.Status.Cavity.001.MeatProbeTemperatureFahrenheit"
    )
    assert descriptions["sensor"][1].native_unit_of_measurement == UnitOfTemperature.FAHRENHEIT


async def test_generate_oven_status_prefers_celsius_cavity(
    mock_homeconnect_appliance: MockApplianceType,
) -> None:
    """Celsius cavity temperature is used when both units are present."""
    description = DeviceDescription(
        status=[
            EntityDescription(
                uid=1,
                name="Cooking.Oven.Status.Cavity.001.CurrentTemperature",
                available=True,
                access=Access.READ,
            ),
            EntityDescription(
                uid=2,
                name="Cooking.Oven.Status.Cavity.001.CurrentTemperatureFahrenheit",
                available=True,
                access=Access.READ,
            ),
        ]
    )
    appliance = await mock_homeconnect_appliance(description=description)
    descriptions = generate_oven_status(appliance)

    assert len(descriptions["sensor"]) == 1
    assert descriptions["sensor"][0].entity == "Cooking.Oven.Status.Cavity.001.CurrentTemperature"
    assert descriptions["sensor"][0].native_unit_of_measurement == UnitOfTemperature.CELSIUS
