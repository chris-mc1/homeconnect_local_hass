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
            key="binary_sensor_machinecarefiltercleaningreminder",
            entity="Dishcare.Dishwasher.Event.MachineCareReminder",
            entity_category=EntityCategory.DIAGNOSTIC,
            device_class=BinarySensorDeviceClass.PROBLEM,
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
        ),
        HCSelectEntityDescription(
            key="select_sound_level_signal",
            entity="Dishcare.Dishwasher.Setting.SoundLevelSignal",
            entity_category=EntityCategory.CONFIG,
            entity_registry_enabled_default=False,
            has_state_translation=True,
        ),
        HCSelectEntityDescription(
            key="select_water_hardness",
            entity="Dishcare.Dishwasher.Setting.WaterHardness",
            entity_category=EntityCategory.CONFIG,
            entity_registry_enabled_default=False,
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
    ],
}
