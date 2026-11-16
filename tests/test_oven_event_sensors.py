"""Tests for the event_sensors oven entity descriptions."""

from __future__ import annotations

import pytest
from custom_components.homeconnect_ws import entity_descriptions

# (description type, key, entity) of the descriptions that must exist.
EXPECTED = [
    (
        "binary_sensor",
        "binary_sensor_software_update_available",
        "BSH.Common.Event.SoftwareUpdateAvailable",
    ),
    (
        "binary_sensor",
        "binary_sensor_software_download_available",
        "BSH.Common.Event.SoftwareDownloadAvailable",
    ),
    (
        "binary_sensor",
        "binary_sensor_software_update_successful",
        "BSH.Common.Event.SoftwareUpdateSuccessful",
    ),
    (
        "binary_sensor",
        "binary_sensor_customer_service_request",
        "BSH.Common.Event.CustomerServiceRequest",
    ),
    (
        "binary_sensor",
        "binary_sensor_oven_lock_while_cooling_down",
        "Cooking.Oven.Event.OvenLockWhileCoolingDown",
    ),
    (
        "binary_sensor",
        "binary_sensor_oven_cavity_temperature_too_high",
        "Cooking.Oven.Event.CavityTemperatureTooHigh",
    ),
    (
        "binary_sensor",
        "binary_sensor_oven_user_interaction_required",
        "Cooking.Oven.Event.UserInteractionRequired",
    ),
    ("binary_sensor", "binary_sensor_oven_cavity_heatup", "Cooking.Oven.Event.CavityHeatup"),
    (
        "binary_sensor",
        "binary_sensor_oven_operating_time_limit_reached",
        "Cooking.Oven.Event.OperatingTimeLimitReached",
    ),
    ("binary_sensor", "binary_sensor_oven_cleaning_request", "Cooking.Oven.Event.CleaningRequest"),
    ("binary_sensor", "binary_sensor_oven_force_flushing", "Cooking.Oven.Event.ForceFlushing"),
    (
        "binary_sensor",
        "binary_sensor_oven_descaling_request",
        "Cooking.Oven.Event.DescalingRequest",
    ),
    (
        "binary_sensor",
        "binary_sensor_oven_empty_water_container",
        "Cooking.Oven.Event.EmptyWaterContainer",
    ),
    (
        "binary_sensor",
        "binary_sensor_oven_water_supply_closed",
        "Cooking.Oven.Event.WaterSupplyClosed",
    ),
    (
        "binary_sensor",
        "binary_sensor_cooking_appliance_module_error",
        "Cooking.Common.Event.ApplianceModuleError",
    ),
]


@pytest.mark.parametrize(("description_type", "key", "entity"), EXPECTED)
def test_description_exists(description_type: str, key: str, entity: str) -> None:
    """Test the description exists and points to the entity the oven reports."""
    descriptions = entity_descriptions.get_all_entity_description()

    description = next(
        d for d in descriptions[description_type] if not callable(d) and d.key == key
    )
    assert description.entity == entity


def test_events_report_none_as_off() -> None:
    """Test that every event reports null (not yet occurred) as off."""
    descriptions = entity_descriptions.get_all_entity_description()
    keys = {key for _type, key, _entity in EXPECTED}

    for description in descriptions["binary_sensor"]:
        if not callable(description) and description.key in keys:
            assert description.value_off == {"Off", None}
            assert description.value_on == {"Present", "Confirmed"}
