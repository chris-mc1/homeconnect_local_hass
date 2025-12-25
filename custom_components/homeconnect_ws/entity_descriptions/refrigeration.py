"""Description for Refrigeration Entities."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.components.number import NumberDeviceClass, NumberMode
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.components.switch import SwitchDeviceClass
from homeassistant.const import EntityCategory, UnitOfTemperature

from .descriptions_definitions import (
    HCBinarySensorEntityDescription,
    HCLightEntityDescription,
    HCNumberEntityDescription,
    HCSelectEntityDescription,
    HCSensorEntityDescription,
    HCSwitchEntityDescription,
    _EntityDescriptionsDefinitionsType,
)

REFRIGERATION_ENTITY_DESCRIPTIONS: _EntityDescriptionsDefinitionsType = {
    "binary_sensor": [
        HCBinarySensorEntityDescription(
            key="binary_sensor_freezer_door_state",
            entity="Refrigeration.Common.Status.Door.Freezer",
            device_class=BinarySensorDeviceClass.DOOR,
            value_on={"Open"},
            value_off={"Closed"},
        ),
        HCBinarySensorEntityDescription(
            key="binary_sensor_fridge_door_state",
            entity="Refrigeration.Common.Status.Door.Refrigerator",
            device_class=BinarySensorDeviceClass.DOOR,
            value_on={"Open"},
            value_off={"Closed"},
        ),
        HCBinarySensorEntityDescription(
            key="binary_sensor_freezer_door_state",
            entity="Refrigeration.FridgeFreezer.Status.DoorFreezer",
            device_class=BinarySensorDeviceClass.DOOR,
            value_on={"Open"},
            value_off={"Closed"},
        ),
        HCBinarySensorEntityDescription(
            key="binary_sensor_fridge_door_state",
            entity="Refrigeration.FridgeFreezer.Status.DoorRefrigerator",
            device_class=BinarySensorDeviceClass.DOOR,
            value_on={"Open"},
            value_off={"Closed"},
        ),
        HCBinarySensorEntityDescription(
            key="binary_sensor_door_alarm_freezer",
            entity="Refrigeration.FridgeFreezer.Event.DoorAlarmFreezer",
            entity_category=EntityCategory.DIAGNOSTIC,
            device_class=BinarySensorDeviceClass.PROBLEM,
            value_on={"Present", "Confirmed"},
            value_off={"Off"},
        ),
        HCBinarySensorEntityDescription(
            key="binary_sensor_door_alarm_fridge",
            entity="Refrigeration.FridgeFreezer.Event.DoorAlarmRefrigerator",
            entity_category=EntityCategory.DIAGNOSTIC,
            device_class=BinarySensorDeviceClass.PROBLEM,
            value_on={"Present", "Confirmed"},
            value_off={"Off"},
        ),
        HCBinarySensorEntityDescription(
            key="binary_sensor_door_alarm_freezer",
            entity="Refrigeration.Common.Event.Door.AlarmFreezer",
            entity_category=EntityCategory.DIAGNOSTIC,
            device_class=BinarySensorDeviceClass.PROBLEM,
            value_on={"Present", "Confirmed"},
            value_off={"Off"},
        ),
        HCBinarySensorEntityDescription(
            key="binary_sensor_temperature_alarm_freezer",
            entity="Refrigeration.FridgeFreezer.Event.TemperatureAlarmFreezer",
            entity_category=EntityCategory.DIAGNOSTIC,
            device_class=BinarySensorDeviceClass.PROBLEM,
            value_on={"Present", "Confirmed"},
            value_off={"Off"},
        ),
        HCBinarySensorEntityDescription(
            key="binary_sensor_temperature_alarm_freezer",
            entity="Refrigeration.Common.Event.Freezer.TemperatureAlarm",
            entity_category=EntityCategory.DIAGNOSTIC,
            device_class=BinarySensorDeviceClass.PROBLEM,
            value_on={"Present", "Confirmed"},
            value_off={"Off"},
        ),
        HCBinarySensorEntityDescription(
            key="binary_sensor_refrigerator_defrost",
            entity="Refrigeration.Common.Status.Freezer.Defrost",
        ),
        HCBinarySensorEntityDescription(
            key="binary_sensor_water_filter_full",
            entity="Refrigeration.Common.Event.Dispenser.WaterFilterFull",
            entity_category=EntityCategory.DIAGNOSTIC,
            device_class=BinarySensorDeviceClass.PROBLEM,
            value_on={"Present", "Confirmed"},
            value_off={"Off"},
        ),
        HCBinarySensorEntityDescription(
            key="binary_sensor_refrigerator_defrost",
            entity="Refrigeration.FridgeFreezer.Status.DefrostFreezer",
        ),
        HCBinarySensorEntityDescription(
            key="binary_sensor_freezer_appliance_error",
            entity="Refrigeration.FridgeFreezer.Event.ApplianceError",
            entity_category=EntityCategory.DIAGNOSTIC,
            device_class=BinarySensorDeviceClass.PROBLEM,
            value_on={"Present", "Confirmed"},
            value_off={"Off"},
        ),
        HCBinarySensorEntityDescription(
            key="binary_sensor_appliance_error",
            entity="Refrigeration.Common.Event.ApplianceError",
            entity_category=EntityCategory.DIAGNOSTIC,
            device_class=BinarySensorDeviceClass.PROBLEM,
            value_on={"Present", "Confirmed"},
            value_off={"Off"},
        ),
        HCBinarySensorEntityDescription(
            key="binary_sensor_freezer_low_voltage",
            entity="Refrigeration.FridgeFreezer.Event.LowVoltageHint",
            entity_category=EntityCategory.DIAGNOSTIC,
            device_class=BinarySensorDeviceClass.PROBLEM,
            value_on={"Present", "Confirmed"},
            value_off={"Off"},
        ),
    ],
    "sensor": [
        HCSensorEntityDescription(
            key="sensor_temperature_ambient",
            entity="Refrigeration.FridgeFreezer.Status.TemperatureAmbient",
            device_class=SensorDeviceClass.TEMPERATURE,
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        ),
        HCSensorEntityDescription(
            key="sensor_temperature_ambient",
            entity="Refrigeration.Common.Status.TemperatureAmbient",
            device_class=SensorDeviceClass.TEMPERATURE,
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        ),
    ],
    "number": [
        # Legacy/Generic temperature controls
        HCNumberEntityDescription(
            key="number_setpoint_freezer",
            entity="Refrigeration.FridgeFreezer.Setting.SetpointTemperatureFreezer",
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            device_class=NumberDeviceClass.TEMPERATURE,
            mode=NumberMode.AUTO,
            step=1,
        ),
        HCNumberEntityDescription(
            key="number_setpoint_refrigerator",
            entity="Refrigeration.FridgeFreezer.Setting.SetpointTemperatureRefrigerator",
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            device_class=NumberDeviceClass.TEMPERATURE,
            mode=NumberMode.AUTO,
            step=1,
        ),
        # Enhanced Bosch/Siemens Specific Temperature Controls - Celsius
        HCNumberEntityDescription(
            key="number_refrigerator_setpoint_temperature_celsius",
            entity="Refrigeration.Common.Setting.Refrigerator.SetpointTemperature",
            name="Refrigerator Temperature",
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            device_class=NumberDeviceClass.TEMPERATURE,
            mode=NumberMode.AUTO,
            step=1,
            icon="mdi:fridge-outline",
        ),
        HCNumberEntityDescription(
            key="number_freezer_setpoint_temperature_celsius",
            entity="Refrigeration.Common.Setting.Freezer.SetpointTemperature",
            name="Freezer Temperature",
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            device_class=NumberDeviceClass.TEMPERATURE,
            mode=NumberMode.AUTO,
            step=1,
            icon="mdi:snowflake",
        ),
        # Enhanced Temperature Controls - Fahrenheit
        HCNumberEntityDescription(
            key="number_refrigerator_setpoint_temperature_fahrenheit",
            entity="Refrigeration.Common.Setting.Refrigerator.SetpointTemperatureFahrenheit",
            name="Refrigerator Temperature (°F)",
            native_unit_of_measurement=UnitOfTemperature.FAHRENHEIT,
            device_class=NumberDeviceClass.TEMPERATURE,
            mode=NumberMode.AUTO,
            step=1,
            icon="mdi:fridge-outline",
        ),
        HCNumberEntityDescription(
            key="number_freezer_setpoint_temperature_fahrenheit",
            entity="Refrigeration.Common.Setting.Freezer.SetpointTemperatureFahrenheit",
            name="Freezer Temperature (°F)",
            native_unit_of_measurement=UnitOfTemperature.FAHRENHEIT,
            device_class=NumberDeviceClass.TEMPERATURE,
            mode=NumberMode.AUTO,
            step=1,
            icon="mdi:snowflake",
        ),
    ],
    "switch": [
        HCSwitchEntityDescription(
            key="switch_super_freezer",
            entity="Refrigeration.FridgeFreezer.Setting.SuperModeFreezer",
            device_class=SwitchDeviceClass.SWITCH,
        ),
        HCSwitchEntityDescription(
            key="switch_super_freezer",
            entity="Refrigeration.Common.Setting.Freezer.SuperMode",
            name="Super Freeze Mode",
            device_class=SwitchDeviceClass.SWITCH,
            icon="mdi:snowflake-alert",
        ),
        HCSwitchEntityDescription(
            key="switch_super_refrigerator",
            entity="Refrigeration.FridgeFreezer.Setting.SuperModeRefrigerator",
            device_class=SwitchDeviceClass.SWITCH,
        ),
        HCSwitchEntityDescription(
            key="switch_super_refrigerator",
            entity="Refrigeration.Common.Setting.Refrigerator.SuperMode",
            name="Super Cool Mode",
            device_class=SwitchDeviceClass.SWITCH,
            icon="mdi:fridge-alert-outline",
        ),
        HCSwitchEntityDescription(
            key="switch_refrigerator_eco",
            entity="Refrigeration.FridgeFreezer.Setting.EcoMode",
            device_class=SwitchDeviceClass.SWITCH,
        ),
        HCSwitchEntityDescription(
            key="switch_refrigerator_eco",
            entity="Refrigeration.Common.Setting.EcoMode",
            device_class=SwitchDeviceClass.SWITCH,
        ),
        HCSwitchEntityDescription(
            key="switch_refrigerator_vacation",
            entity="Refrigeration.FridgeFreezer.Setting.VacationMode",
            device_class=SwitchDeviceClass.SWITCH,
        ),
        HCSwitchEntityDescription(
            key="switch_refrigerator_vacation",
            entity="Refrigeration.Common.Setting.VacationMode",
            name="Vacation Mode",
            device_class=SwitchDeviceClass.SWITCH,
            icon="mdi:airplane",
        ),
        HCSwitchEntityDescription(
            key="switch_refrigerator_dispenser_enabled",
            entity="Refrigeration.Common.Setting.Dispenser.Enabled",
            device_class=SwitchDeviceClass.SWITCH,
        ),
        HCSwitchEntityDescription(
            key="switch_refrigerator_sabbath_mode",
            entity="Refrigeration.Common.Setting.SabbathMode",
            device_class=SwitchDeviceClass.SWITCH,
            entity_category=EntityCategory.CONFIG,
        ),
        HCSwitchEntityDescription(
            key="switch_refrigerator_door_assistant_freezer",
            entity="Refrigeration.Common.Setting.Door.AssistantFreezer",
            device_class=SwitchDeviceClass.SWITCH,
            entity_category=EntityCategory.CONFIG,
        ),
        HCSwitchEntityDescription(
            key="switch_refrigeration_light_internal",
            entity="Refrigeration.Common.Setting.Light.Internal.Power",
            device_class=SwitchDeviceClass.SWITCH,
            entity_registry_enabled_default=False,
        ),
        HCSwitchEntityDescription(
            key="switch_refrigeration_light_theater_mode",
            entity="Refrigeration.Common.Setting.Light.Internal.EnableTheaterMode",
            device_class=SwitchDeviceClass.SWITCH,
        ),
        HCSwitchEntityDescription(
            key="switch_refrigerator_sabbath_mode",
            entity="Refrigeration.FridgeFreezer.Setting.SabbathMode",
            device_class=SwitchDeviceClass.SWITCH,
            entity_category=EntityCategory.CONFIG,
        ),
        HCSwitchEntityDescription(
            key="switch_refrigerator_fresh_mode",
            entity="Refrigeration.FridgeFreezer.Setting.FreshMode",
            device_class=SwitchDeviceClass.SWITCH,
            entity_category=EntityCategory.CONFIG,
        ),
    ],
    "select": [
        HCSelectEntityDescription(
            key="select_refrigerator_door_assistant_freezer_trigger",
            entity="Refrigeration.Common.Setting.Door.AssistantTriggerFreezer",
            device_class=SensorDeviceClass.ENUM,
            has_state_translation=True,
        ),
        HCSelectEntityDescription(
            key="select_refrigerator_door_assistant_freezer_force",
            entity="Refrigeration.Common.Setting.Door.AssistantForceFreezer",
            device_class=SensorDeviceClass.ENUM,
            has_state_translation=True,
        ),
    ],
    "light": [
        HCLightEntityDescription(
            key="light_internal",
            entity="Refrigeration.Common.Setting.Light.Internal.Power",
        ),
    ],
}
