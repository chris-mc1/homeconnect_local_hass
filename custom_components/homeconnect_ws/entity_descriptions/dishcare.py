"""Description for Dishcare.Dishwasher Entities."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.components.sensor import (
    SensorDeviceClass,
)
from homeassistant.components.switch import SwitchDeviceClass
from homeassistant.const import EntityCategory

from .descriptions_definitions import (
    HCBinarySensorEntityDescription,
    HCSelectEntityDescription,
    HCSensorEntityDescription,
    HCSwitchEntityDescription,
    _EntityDescriptionsDefinitionsType,
)

DISHCARE_ENTITY_DESCRIPTIONS: _EntityDescriptionsDefinitionsType = {
    "binary_sensor": [
        HCBinarySensorEntityDescription(
            key="binary_sensor_eco_dry_active",
            entity="Dishcare.Dishwasher.Status.EcoDryActive",
            entity_registry_enabled_default=False,
        ),
        HCBinarySensorEntityDescription(
            key="binary_sensor_machinecarereminder",
            entity="Dishcare.Dishwasher.Event.MachineCareReminder",
            entity_category=EntityCategory.DIAGNOSTIC,
            device_class=BinarySensorDeviceClass.PROBLEM,
            value_on={"Present", "Confirmed"},
            value_off={"Off"},
        ),
        HCBinarySensorEntityDescription(
            key="binary_sensor_low_voltage",
            entity="Dishcare.Dishwasher.Event.LowVoltage",
            entity_category=EntityCategory.DIAGNOSTIC,
            device_class=BinarySensorDeviceClass.PROBLEM,
            entity_registry_enabled_default=False,
            value_on={"Present", "Confirmed"},
            value_off={"Off"},
        ),
        HCBinarySensorEntityDescription(
            key="binary_sensor_machinecareandfiltercleaningreminder",
            entity="Dishcare.Dishwasher.Event.MachineCareAndFilterCleaningReminder",
            entity_category=EntityCategory.DIAGNOSTIC,
            device_class=BinarySensorDeviceClass.PROBLEM,
            value_on={"Present", "Confirmed"},
            value_off={"Off"},
        ),
        HCBinarySensorEntityDescription(
            key="binary_sensor_waterheatercalcified",
            entity="Dishcare.Dishwasher.Event.WaterheaterCalcified",
            entity_category=EntityCategory.DIAGNOSTIC,
            device_class=BinarySensorDeviceClass.PROBLEM,
            value_on={"Present", "Confirmed"},
            value_off={"Off"},
        ),
        HCBinarySensorEntityDescription(
            key="binary_sensor_smartfiltercleaningreminder",
            entity="Dishcare.Dishwasher.Event.SmartFilterCleaningReminder",
            entity_category=EntityCategory.DIAGNOSTIC,
            device_class=BinarySensorDeviceClass.PROBLEM,
            value_on={"Present", "Confirmed"},
            value_off={"Off"},
        ),
        HCBinarySensorEntityDescription(
            key="binary_sensor_checkfiltersystem",
            entity="Dishcare.Dishwasher.Event.CheckFilterSystem",
            entity_category=EntityCategory.DIAGNOSTIC,
            device_class=BinarySensorDeviceClass.PROBLEM,
            entity_registry_enabled_default=False,
            value_on={"Present", "Confirmed"},
            value_off={"Off"},
        ),
        HCBinarySensorEntityDescription(
            key="binary_sensor_drainingnotpossible",
            entity="Dishcare.Dishwasher.Event.DrainingNotPossible",
            entity_category=EntityCategory.DIAGNOSTIC,
            device_class=BinarySensorDeviceClass.PROBLEM,
            entity_registry_enabled_default=False,
            value_on={"Present", "Confirmed"},
            value_off={"Off"},
        ),
        HCBinarySensorEntityDescription(
            key="binary_sensor_drainpumpblocked",
            entity="Dishcare.Dishwasher.Event.DrainPumpBlocked",
            entity_category=EntityCategory.DIAGNOSTIC,
            device_class=BinarySensorDeviceClass.PROBLEM,
            entity_registry_enabled_default=False,
            value_on={"Present", "Confirmed"},
            value_off={"Off"},
        ),
        # FlexSpray error events
        # NOTE: Bosch refers to this feature as "PowerControl" in marketing/UI.
        # The protocol/API objects use the name "FlexSpray", which is kept here.
        HCBinarySensorEntityDescription(
            key="binary_sensor_flexspray_error_blocked",
            entity="Dishcare.Dishwasher.Event.FlexSpray.Error.Blocked",
            entity_category=EntityCategory.DIAGNOSTIC,
            device_class=BinarySensorDeviceClass.PROBLEM,
            entity_registry_enabled_default=False,
            value_on={"Present", "Confirmed"},
            value_off={"Off"},
        ),
        HCBinarySensorEntityDescription(
            key="binary_sensor_flexspray_error_general",
            entity="Dishcare.Dishwasher.Event.FlexSpray.Error.General",
            entity_category=EntityCategory.DIAGNOSTIC,
            device_class=BinarySensorDeviceClass.PROBLEM,
            entity_registry_enabled_default=False,
            value_on={"Present", "Confirmed"},
            value_off={"Off"},
        ),
        HCBinarySensorEntityDescription(
            key="binary_sensor_flexspray_error_spray_arm_not_mounted",
            entity="Dishcare.Dishwasher.Event.FlexSpray.Error.SprayArmNotMounted",
            entity_category=EntityCategory.DIAGNOSTIC,
            device_class=BinarySensorDeviceClass.PROBLEM,
            entity_registry_enabled_default=False,
            value_on={"Present", "Confirmed"},
            value_off={"Off"},
        ),
    ],
    "event_sensor": [
        HCSensorEntityDescription(
            key="sensor_rinse_aid",
            entities=[
                "Dishcare.Dishwasher.Event.RinseAidLack",
                "Dishcare.Dishwasher.Event.RinseAidNearlyEmpty",
            ],
            device_class=SensorDeviceClass.ENUM,
            options=["empty", "nearly_empty", "full"],
        ),
        HCSensorEntityDescription(
            key="sensor_salt",
            entities=[
                "Dishcare.Dishwasher.Event.SaltLack",
                "Dishcare.Dishwasher.Event.SaltNearlyEmpty",
            ],
            device_class=SensorDeviceClass.ENUM,
            options=["empty", "nearly_empty", "full"],
        ),
    ],
    "select": [
        HCSelectEntityDescription(
            key="select_drying_assistant_all_programs",
            entity="Dishcare.Dishwasher.Setting.DryingAssistantAllPrograms",
            entity_category=EntityCategory.CONFIG,
            entity_registry_enabled_default=False,
            has_state_translation=True,
        ),
        HCSelectEntityDescription(
            key="select_hot_water",
            entity="Dishcare.Dishwasher.Setting.HotWater",
            entity_category=EntityCategory.CONFIG,
            entity_registry_enabled_default=False,
            has_state_translation=True,
        ),
        HCSelectEntityDescription(
            key="select_rinse_aid",
            entity="Dishcare.Dishwasher.Setting.RinseAid",
            entity_category=EntityCategory.CONFIG,
            entity_registry_enabled_default=False,
            has_state_translation=True,
        ),
        HCSelectEntityDescription(
            key="select_sound_level_signal",
            entity="Dishcare.Dishwasher.Setting.SoundLevelSignal",
            entity_category=EntityCategory.CONFIG,
            entity_registry_enabled_default=False,
            has_state_translation=True,
        ),
        HCSelectEntityDescription(
            key="select_sound_level_key",
            entity="Dishcare.Dishwasher.Setting.SoundLevelKey",
            entity_category=EntityCategory.CONFIG,
            entity_registry_enabled_default=False,
            has_state_translation=True,
        ),
        HCSelectEntityDescription(
            key="select_water_hardness",
            entity="Dishcare.Dishwasher.Setting.WaterHardness",
            entity_category=EntityCategory.CONFIG,
            entity_registry_enabled_default=False,
            has_state_translation=True,
        ),
        HCSelectEntityDescription(
            key="select_sensitivity_turbidity",
            entity="Dishcare.Dishwasher.Setting.SensitivityTurbidity",
            entity_category=EntityCategory.CONFIG,
            entity_registry_enabled_default=False,
            has_state_translation=True,
        ),
        HCSelectEntityDescription(
            key="select_eco_as_default",
            entity="Dishcare.Dishwasher.Setting.EcoAsDefault",
            entity_category=EntityCategory.CONFIG,
            entity_registry_enabled_default=False,
            has_state_translation=True,
        ),
        # FlexSpray configuration options
        # NOTE: Bosch refers to this feature as "PowerControl" in marketing/UI.
        # The protocol/API objects use the name "FlexSpray", which is kept here.
        HCSelectEntityDescription(
            key="select_flexspray_type",
            entity="Dishcare.Dishwasher.Option.FlexSpray.Type",
            entity_category=EntityCategory.CONFIG,
            entity_registry_enabled_default=False,
            has_state_translation=True,
        ),
        HCSelectEntityDescription(
            key="select_flexspray_front_left",
            entity="Dishcare.Dishwasher.Option.FlexSpray.FrontLeft",
            entity_category=EntityCategory.CONFIG,
            entity_registry_enabled_default=False,
            has_state_translation=True,
        ),
        HCSelectEntityDescription(
            key="select_flexspray_back_left",
            entity="Dishcare.Dishwasher.Option.FlexSpray.BackLeft",
            entity_category=EntityCategory.CONFIG,
            entity_registry_enabled_default=False,
            has_state_translation=True,
        ),
        HCSelectEntityDescription(
            key="select_flexspray_back_right",
            entity="Dishcare.Dishwasher.Option.FlexSpray.BackRight",
            entity_category=EntityCategory.CONFIG,
            entity_registry_enabled_default=False,
            has_state_translation=True,
        ),
        HCSelectEntityDescription(
            key="select_flexspray_front_right",
            entity="Dishcare.Dishwasher.Option.FlexSpray.FrontRight",
            entity_category=EntityCategory.CONFIG,
            entity_registry_enabled_default=False,
            has_state_translation=True,
        ),
        # FlexSpray custom settings
        HCSelectEntityDescription(
            key="select_flexspray_custom_front_left",
            entity="Dishcare.Dishwasher.Setting.FlexSpray.Custom.FrontLeft",
            entity_category=EntityCategory.CONFIG,
            entity_registry_enabled_default=False,
            has_state_translation=True,
        ),
        HCSelectEntityDescription(
            key="select_flexspray_custom_back_left",
            entity="Dishcare.Dishwasher.Setting.FlexSpray.Custom.BackLeft",
            entity_category=EntityCategory.CONFIG,
            entity_registry_enabled_default=False,
            has_state_translation=True,
        ),
        HCSelectEntityDescription(
            key="select_flexspray_custom_back_right",
            entity="Dishcare.Dishwasher.Setting.FlexSpray.Custom.BackRight",
            entity_category=EntityCategory.CONFIG,
            entity_registry_enabled_default=False,
            has_state_translation=True,
        ),
        HCSelectEntityDescription(
            key="select_flexspray_custom_front_right",
            entity="Dishcare.Dishwasher.Setting.FlexSpray.Custom.FrontRight",
            entity_category=EntityCategory.CONFIG,
            entity_registry_enabled_default=False,
            has_state_translation=True,
        ),
    ],
    "sensor": [
        HCSensorEntityDescription(
            key="sensor_program_phase",
            entity="Dishcare.Dishwasher.Status.ProgramPhase",
            device_class=SensorDeviceClass.ENUM,
            has_state_translation=True,
        ),
    ],
    "switch": [
        HCSwitchEntityDescription(
            key="switch_extra_dry_option",
            entity="Dishcare.Dishwasher.Option.ExtraDry",
            device_class=SwitchDeviceClass.SWITCH,
        ),
        HCSwitchEntityDescription(
            key="switch_hygiene_plus",
            entity="Dishcare.Dishwasher.Option.HygienePlus",
            device_class=SwitchDeviceClass.SWITCH,
        ),
        HCSwitchEntityDescription(
            key="switch_intensiv_zone",
            entity="Dishcare.Dishwasher.Option.IntensivZone",
            device_class=SwitchDeviceClass.SWITCH,
        ),
        HCSwitchEntityDescription(
            key="switch_vario_speed_plus",
            entity="Dishcare.Dishwasher.Option.VarioSpeedPlus",
            device_class=SwitchDeviceClass.SWITCH,
        ),
        HCSwitchEntityDescription(
            key="switch_silence_on_demand",
            entity="Dishcare.Dishwasher.Option.SilenceOnDemand",
            device_class=SwitchDeviceClass.SWITCH,
        ),
        HCSwitchEntityDescription(
            key="switch_brilliance_dry",
            entity="Dishcare.Dishwasher.Option.BrillianceDry",
            device_class=SwitchDeviceClass.SWITCH,
        ),
        # Also referred to as "CrystalDry"
        HCSwitchEntityDescription(
            key="switch_zeolite_dry",
            entity="Dishcare.Dishwasher.Option.ZeoliteDry",
            device_class=SwitchDeviceClass.SWITCH,
            entity_category=EntityCategory.CONFIG,
            entity_registry_enabled_default=False,
        ),
        HCSwitchEntityDescription(
            key="switch_extra_dry",
            entity="Dishcare.Dishwasher.Setting.ExtraDry",
            device_class=SwitchDeviceClass.SWITCH,
            entity_category=EntityCategory.CONFIG,
            entity_registry_enabled_default=False,
        ),
        HCSwitchEntityDescription(
            key="switch_speed_on_demand",
            entity="Dishcare.Dishwasher.Setting.SpeedOnDemand",
            device_class=SwitchDeviceClass.SWITCH,
            entity_category=EntityCategory.CONFIG,
            entity_registry_enabled_default=False,
        ),
        HCSwitchEntityDescription(
            key="switch_info_light",
            entity="Dishcare.Dishwasher.Setting.InfoLight",
            device_class=SwitchDeviceClass.SWITCH,
            entity_category=EntityCategory.CONFIG,
            entity_registry_enabled_default=False,
        ),
        HCSwitchEntityDescription(
            key="switch_half_load",
            entity="Dishcare.Dishwasher.Option.HalfLoad",
            device_class=SwitchDeviceClass.SWITCH,
        ),
        HCSwitchEntityDescription(
            key="switch_extra_rinse",
            entity="Dishcare.Dishwasher.Option.ExtraRinse",
            device_class=SwitchDeviceClass.SWITCH,
        ),
    ],
}
