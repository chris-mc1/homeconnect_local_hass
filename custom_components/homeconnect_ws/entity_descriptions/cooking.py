"""Description for Cooking Entities."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from homeassistant.components.number import NumberDeviceClass, NumberMode
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.components.switch import SwitchDeviceClass
from homeassistant.const import PERCENTAGE, EntityCategory, UnitOfTemperature, UnitOfTime

from custom_components.homeconnect_ws.helpers import get_groups_from_regex

from .descriptions_definitions import (
    EntityDescriptions,
    HCFanEntityDescription,
    HCLightEntityDescription,
    HCNumberEntityDescription,
    HCSelectEntityDescription,
    HCSensorEntityDescription,
    HCSwitchEntityDescription,
    _EntityDescriptionsDefinitionsType,
)

if TYPE_CHECKING:
    from homeconnect_websocket import HomeAppliance


def generate_oven_status(appliance: HomeAppliance) -> EntityDescriptions:
    """Get Oven status descriptions."""
    pattern = re.compile(r"^Cooking\.Oven\.Status\.Cavity\.([0-9]*)\..*$")
    groups = get_groups_from_regex(appliance, pattern)
    descriptions = EntityDescriptions(event_sensor=[], sensor=[])
    for group in groups:
        group_name = f" {int(group[0])}"
        if len(groups) == 1:
            group_name = ""

        # Water Tank
        entities = (
            f"Cooking.Oven.Status.Cavity.{group[0]}.WaterTankUnplugged",
            f"Cooking.Oven.Status.Cavity.{group[0]}.WaterTankEmpty",
        )
        if all(entity in appliance.entities for entity in entities):
            descriptions["event_sensor"].append(
                HCSensorEntityDescription(
                    key=f"sensor_oven_water_tank_{group[0]}",
                    translation_key="sensor_oven_water_tank",
                    translation_placeholders={"group_name": group_name},
                    entities=entities,
                    device_class=SensorDeviceClass.ENUM,
                    options=["unplugged", "empty", "ok"],
                )
            )

        # Temperatur
        entity = f"Cooking.Oven.Status.Cavity.{group[0]}.CurrentTemperature"
        if entity in appliance.entities:
            descriptions["sensor"].append(
                HCSensorEntityDescription(
                    key=f"sensor_oven_current_temperature_{group[0]}",
                    translation_key="sensor_oven_current_temperature",
                    translation_placeholders={"group_name": group_name},
                    entity=entity,
                    device_class=SensorDeviceClass.TEMPERATURE,
                    native_unit_of_measurement=UnitOfTemperature.CELSIUS,
                )
            )

    return descriptions


HOOD_FAN_ENTITIES = [
    "Cooking.Common.Option.Hood.VentingLevel",
    "Cooking.Common.Option.Hood.IntensiveLevel",
]


def generate_hood_fan(appliance: HomeAppliance) -> HCFanEntityDescription:
    """Get Hood Fan description."""
    available_entities = [entity for entity in HOOD_FAN_ENTITIES if entity in appliance.entities]
    if available_entities:
        return HCFanEntityDescription(key="fan_hood", entities=available_entities)
    return None


def generate_hob_zones(appliance: HomeAppliance) -> HCFanEntityDescription:
    """Get Oven status descriptions."""
    pattern = re.compile(r"^Cooking\.Hob\.Status\.Zone\.([0-9]*)\..*$")
    groups = get_groups_from_regex(appliance, pattern)
    descriptions = EntityDescriptions(sensor=[])
    for group in groups:
        group_name = f" {int(group[0])}"

        # State
        entity = f"Cooking.Hob.Status.Zone.{group[0]}.State"
        if entity in appliance.entities:
            descriptions["sensor"].append(
                HCSensorEntityDescription(
                    key=f"sensor_hob_zone_{group[0]}_state",
                    translation_key="sensor_hob_zone_state",
                    translation_placeholders={"group_name": group_name},
                    entity=entity,
                    device_class=SensorDeviceClass.ENUM,
                    has_state_translation=True,
                    extra_attributes=[
                        {
                            "name": "Type",
                            "entity": f"Cooking.Hob.Status.Zone.{group[0]}.Type",
                        }
                    ],
                )
            )

        # OperationState
        entity = f"Cooking.Hob.Status.Zone.{group[0]}.OperationState"
        if entity in appliance.entities:
            descriptions["sensor"].append(
                HCSensorEntityDescription(
                    key=f"sensor_hob_zone_{group[0]}_operationstate",
                    translation_key="sensor_hob_zone_operationstate",
                    translation_placeholders={"group_name": group_name},
                    entity=entity,
                    device_class=SensorDeviceClass.ENUM,
                    has_state_translation=True,
                )
            )

        # PowerLevel
        entity = f"Cooking.Hob.Status.Zone.{group[0]}.PowerLevel"
        if entity in appliance.entities:
            descriptions["sensor"].append(
                HCSensorEntityDescription(
                    key=f"sensor_hob_zone_{group[0]}_power_level",
                    translation_key="sensor_hob_zone_power_level",
                    translation_placeholders={"group_name": group_name},
                    entity=entity,
                    device_class=SensorDeviceClass.ENUM,
                    has_state_translation=True,
                )
            )

        # FryingSensorLevel
        entity = f"Cooking.Hob.Status.Zone.{group[0]}.FryingSensorLevel"
        if entity in appliance.entities:
            descriptions["sensor"].append(
                HCSensorEntityDescription(
                    key=f"sensor_hob_zone_{group[0]}_frying_sensor_level",
                    translation_key="sensor_hob_zone_frying_sensor_level",
                    translation_placeholders={"group_name": group_name},
                    entity=entity,
                    device_class=SensorDeviceClass.ENUM,
                    has_state_translation=True,
                )
            )

        # CurrentTemperature
        entity = f"Cooking.Hob.Status.Zone.{group[0]}.CurrentTemperature"
        if entity in appliance.entities:
            descriptions["sensor"].append(
                HCSensorEntityDescription(
                    key=f"sensor_hob_zone_{group[0]}_current_temperature",
                    translation_key="sensor_hob_zone_current_temperature",
                    translation_placeholders={"group_name": group_name},
                    entity=entity,
                    device_class=SensorDeviceClass.TEMPERATURE,
                    native_unit_of_measurement=UnitOfTemperature.CELSIUS,
                )
            )

        # HeatupProgress
        entity = f"Cooking.Hob.Status.Zone.{group[0]}.HeatupProgress"
        if entity in appliance.entities:
            descriptions["sensor"].append(
                HCSensorEntityDescription(
                    key=f"sensor_hob_zone_{group[0]}_heatup_progress",
                    translation_key="sensor_hob_zone_heatup_progress",
                    translation_placeholders={"group_name": group_name},
                    entity=entity,
                    native_unit_of_measurement=PERCENTAGE,
                )
            )

        # Duration
        entity = f"Cooking.Hob.Status.Zone.{group[0]}.Duration"
        if entity in appliance.entities:
            descriptions["sensor"].append(
                HCSensorEntityDescription(
                    key=f"sensor_hob_zone_{group[0]}_duration",
                    translation_key="sensor_hob_zone_duration",
                    translation_placeholders={"group_name": group_name},
                    entity=entity,
                    device_class=SensorDeviceClass.DURATION,
                    native_unit_of_measurement=UnitOfTime.SECONDS,
                    suggested_unit_of_measurement=UnitOfTime.MINUTES,
                )
            )

        # ElapsedProgramTime
        entity = f"Cooking.Hob.Status.Zone.{group[0]}.ElapsedProgramTime"
        extra_entity = f"Cooking.Hob.Status.Zone.{group[0]}.ElapsedProgramTime.AutoCounting"
        if entity in appliance.entities:
            descriptions["sensor"].append(
                HCSensorEntityDescription(
                    key=f"sensor_hob_zone_{group[0]}_elapsed_program_time",
                    translation_key="sensor_hob_zone_elapsed_program_time",
                    translation_placeholders={"group_name": group_name},
                    entity=entity,
                    device_class=SensorDeviceClass.DURATION,
                    native_unit_of_measurement=UnitOfTime.SECONDS,
                    suggested_unit_of_measurement=UnitOfTime.MINUTES,
                    extra_attributes=[{"name": "Auto Counting", "entity": extra_entity}],
                )
            )

        # RemainingProgramTime
        entity = f"Cooking.Hob.Status.Zone.{group[0]}.RemainingProgramTime"
        extra_entity = f"Cooking.Hob.Status.Zone.{group[0]}.RemainingProgramTime.AutoCounting"
        if entity in appliance.entities:
            descriptions["sensor"].append(
                HCSensorEntityDescription(
                    key=f"sensor_hob_zone_{group[0]}_remaining_program_time",
                    translation_key="sensor_hob_zone_remaining_program_time",
                    translation_placeholders={"group_name": group_name},
                    entity=entity,
                    device_class=SensorDeviceClass.DURATION,
                    native_unit_of_measurement=UnitOfTime.SECONDS,
                    suggested_unit_of_measurement=UnitOfTime.MINUTES,
                    extra_attributes=[{"name": "Auto Counting", "entity": extra_entity}],
                )
            )

        # ProgramProgress
        entity = f"Cooking.Hob.Status.Zone.{group[0]}.ProgramProgress"
        if entity in appliance.entities:
            descriptions["sensor"].append(
                HCSensorEntityDescription(
                    key=f"sensor_hob_zone_{group[0]}_program_progress",
                    translation_key="sensor_hob_zone_program_progress",
                    translation_placeholders={"group_name": group_name},
                    entity=entity,
                    native_unit_of_measurement=PERCENTAGE,
                )
            )

    return descriptions


def generate_hood_light(appliance: HomeAppliance) -> HCFanEntityDescription:
    """Get Hood light descriptions."""
    if "Cooking.Hood.Setting.ColorTemperaturePercent" in appliance.entities:
        return HCLightEntityDescription(
            key="light_cooking_lighting",
            entity="Cooking.Common.Setting.Lighting",
            brightness_entity="Cooking.Common.Setting.LightingBrightness",
            color_temperature_entity="Cooking.Hood.Setting.ColorTemperaturePercent",
        )
    return HCLightEntityDescription(
        key="light_cooking_lighting",
        entity="Cooking.Common.Setting.Lighting",
        brightness_entity="Cooking.Common.Setting.LightingBrightness",
    )


COOKING_ENTITY_DESCRIPTIONS: _EntityDescriptionsDefinitionsType = {
    "sensor": [
        HCSensorEntityDescription(
            key="sensor_interval_time_off",
            entity="Cooking.Hood.Setting.IntervalTimeOff",
            device_class=SensorDeviceClass.DURATION,
            native_unit_of_measurement=UnitOfTime.SECONDS,
            entity_registry_enabled_default=False,
        ),
        HCSensorEntityDescription(
            key="sensor_interval_time_on",
            entity="Cooking.Hood.Setting.IntervalTimeOn",
            device_class=SensorDeviceClass.DURATION,
            native_unit_of_measurement=UnitOfTime.SECONDS,
            entity_registry_enabled_default=False,
        ),
        HCSensorEntityDescription(
            key="sensor_delayed_shutoff_time",
            entity="Cooking.Hood.Setting.DelayedShutOffTime",
            device_class=SensorDeviceClass.DURATION,
            native_unit_of_measurement=UnitOfTime.SECONDS,
            entity_registry_enabled_default=False,
        ),
        HCSensorEntityDescription(
            key="sensor_heatup_progress",
            entity="Cooking.Oven.Option.HeatupProgress",
            native_unit_of_measurement=PERCENTAGE,
        ),
        HCSensorEntityDescription(
            key="sensor_grease_filter_saturation",
            entity="Cooking.Hood.Status.GreaseFilterSaturation",
            native_unit_of_measurement=PERCENTAGE,
        ),
        HCSensorEntityDescription(
            key="sensor_carbon_filter_saturation",
            entity="Cooking.Hood.Status.CarbonFilterSaturation",
            native_unit_of_measurement=PERCENTAGE,
        ),
    ],
    "dynamic": [generate_oven_status, generate_hob_zones],
    "number": [
        HCNumberEntityDescription(
            key="number_oven_setpoint_temperature",
            entity="Cooking.Oven.Option.SetpointTemperature",
            device_class=NumberDeviceClass.TEMPERATURE,
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            mode=NumberMode.AUTO,
        ),
        HCNumberEntityDescription(
            key="number_oven_display_brightness",
            entity="Cooking.Oven.Setting.DisplayBrightness",
            entity_category=EntityCategory.CONFIG,
            mode=NumberMode.AUTO,
        ),
        HCNumberEntityDescription(
            key="number_hood_interval_off",
            entity="Cooking.Hood.Setting.IntervalTimeOn",
            native_unit_of_measurement=UnitOfTime.SECONDS,
            mode=NumberMode.AUTO,
        ),
        HCNumberEntityDescription(
            key="number_hood_interval_on",
            entity="Cooking.Hood.Setting.IntervalTimeOff",
            native_unit_of_measurement=UnitOfTime.SECONDS,
            mode=NumberMode.AUTO,
        ),
    ],
    "select": [
        HCSelectEntityDescription(
            key="select_oven_level",
            entity="Cooking.Oven.Option.Level",
            has_state_translation=True,
        ),
        HCSelectEntityDescription(
            key="select_oven_used_heating_mode",
            entity="Cooking.Oven.Option.UsedHeatingMode",
            has_state_translation=True,
        ),
        HCSelectEntityDescription(
            key="select_pyrolysis_level",
            entity="Cooking.Oven.Option.PyrolysisLevel",
            has_state_translation=True,
        ),
        HCSelectEntityDescription(
            key="select_oven_child_lock_setting",
            entity="Cooking.Oven.Setting.ConfigureChildLock",
            has_state_translation=True,
            entity_category=EntityCategory.CONFIG,
        ),
        HCSelectEntityDescription(
            key="select_oven_switch_on_delay",
            entity="Cooking.Oven.Setting.SwitchOnDelay",
            has_state_translation=True,
            entity_category=EntityCategory.CONFIG,
        ),
        HCSelectEntityDescription(
            key="select_oven_cooling_fan_runtime",
            entity="Cooking.Oven.Setting.CoolingFanRunOnTime",
            has_state_translation=True,
            entity_category=EntityCategory.CONFIG,
        ),
        HCSelectEntityDescription(
            key="select_oven_signal_duration",
            entity="Cooking.Oven.Setting.SignalDuration",
            has_state_translation=True,
            entity_category=EntityCategory.CONFIG,
        ),
        HCSelectEntityDescription(
            key="select_hood_interval_stage",
            entity="Cooking.Hood.Setting.IntervalStage",
            has_state_translation=True,
        ),
        HCSelectEntityDescription(
            key="select_hob_ventilation",
            entity="Cooking.Hob.Setting.Ventilation",
            has_state_translation=True,
            entity_category=EntityCategory.CONFIG,
        ),
    ],
    "switch": [
        HCSwitchEntityDescription(
            key="switch_oven_fast_pre_heat",
            entity="Cooking.Oven.Option.FastPreHeat",
            device_class=SwitchDeviceClass.SWITCH,
        ),
        HCSwitchEntityDescription(
            key="switch_oven_button_tones",
            entity="Cooking.Oven.Setting.ButtonTones",
            device_class=SwitchDeviceClass.SWITCH,
            entity_category=EntityCategory.CONFIG,
        ),
        HCSwitchEntityDescription(
            key="switch_oven_light_during_operation",
            entity="Cooking.Oven.Setting.OvenLightDuringOperation",
            device_class=SwitchDeviceClass.SWITCH,
            entity_category=EntityCategory.CONFIG,
        ),
        HCSwitchEntityDescription(
            key="switch_oven_sabbath_mode",
            entity="Cooking.Oven.Setting.SabbathMode",
            device_class=SwitchDeviceClass.SWITCH,
            entity_category=EntityCategory.CONFIG,
        ),
        HCSwitchEntityDescription(
            key="switch_hood_boost",
            entity="Cooking.Common.Option.Hood.Boost",
            device_class=SwitchDeviceClass.SWITCH,
        ),
    ],
    "light": [generate_hood_light],
    "fan": [generate_hood_fan],
}
