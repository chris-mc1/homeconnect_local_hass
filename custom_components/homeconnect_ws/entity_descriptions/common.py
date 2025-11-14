"""Description for BSH.Common Entities."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
)
from homeassistant.components.number import NumberDeviceClass, NumberMode
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.components.switch import SwitchDeviceClass
from homeassistant.const import (
    PERCENTAGE,
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    EntityCategory,
    UnitOfTime,
)
from homeconnect_websocket.entities import Execution

from .descriptions_definitions import (
    EntityDescriptions,
    HCBinarySensorEntityDescription,
    HCButtonEntityDescription,
    HCNumberEntityDescription,
    HCSelectEntityDescription,
    HCSensorEntityDescription,
    HCSwitchEntityDescription,
    _EntityDescriptionsDefinitionsType,
)

if TYPE_CHECKING:
    from homeconnect_websocket import HomeAppliance


POWER_SWITCH_VALUE_MAPINGS = (
    ("On", "MainsOff"),
    ("Standby", "MainsOff"),
    ("On", "Off"),
    ("On", "Standby"),
    ("Standby", "Off"),
)


def generate_start_button(appliance: HomeAppliance) -> EntityDescriptions:
    """Get Start Button description."""
    programs = list(
        filter(
            lambda program: program.execution == Execution.SELECT_AND_START,
            appliance.programs.values(),
        )
    )
    if len(programs) > 0:
        return HCButtonEntityDescription(
            key="button_start_program",
            entity="BSH.Common.Root.ActiveProgram",
        )
    return None


def generate_power_switch(appliance: HomeAppliance) -> EntityDescriptions:
    """Get Power switch description."""
    entity_descriptions = EntityDescriptions()
    if entity := appliance.entities.get("BSH.Common.Setting.PowerState"):
        if entity.min and entity.max:
            # has min/max
            settable_states = set()
            for key, value in entity.enum.items():
                if int(key) >= entity.min and int(key) <= entity.max:
                    settable_states.add(value)
        else:
            settable_states = set(entity.enum.values())

        if len(settable_states) == 2:
            # only two power states
            for mapping in POWER_SWITCH_VALUE_MAPINGS:
                if settable_states == set(mapping):
                    entity_descriptions["switch"] = [
                        HCSwitchEntityDescription(
                            key="switch_power_state",
                            entity="BSH.Common.Setting.PowerState",
                            device_class=SwitchDeviceClass.SWITCH,
                            value_mapping=mapping,
                        )
                    ]

        entity_descriptions["select"] = [
            HCSelectEntityDescription(
                key="select_power_state",
                entity="BSH.Common.Setting.PowerState",
                options=[value.lower() for value in settable_states],
                has_state_translation=True,
                # more then two power states
                entity_registry_enabled_default=len(settable_states) > 2,
            )
        ]
    return entity_descriptions


def generate_door_state(appliance: HomeAppliance) -> HCSensorEntityDescription | None:
    """Get Door sensor description."""
    entity = appliance.entities.get("BSH.Common.Status.DoorState")
    if entity and len(entity.enum) > 2:
        return HCSensorEntityDescription(
            key="sensor_door_state",
            entity="BSH.Common.Status.DoorState",
            device_class=SensorDeviceClass.ENUM,
            has_state_translation=True,
        )
    return None


def generate_program(appliance: HomeAppliance) -> EntityDescriptions:
    """Get Door program select and sensor description."""
    pattern = re.compile(r"^BSH\.Common\.Program\.Favorite\.(.*)$")

    programs = {}

    for program in appliance.programs:
        if match := pattern.match(program):
            favorite_name_entity = appliance.settings.get(
                f"BSH.Common.Setting.Favorite.{match.groups()[0]}.Name"
            )
            if favorite_name_entity and favorite_name_entity.value:
                program_name = favorite_name_entity.value
            else:
                program_name = f"favorite_{match.groups()[0]}"
        else:
            program_name = program.lower().replace(".", "_")

        programs[program] = program_name

    # sort programs
    programs_keys = list(programs.keys())
    programs_keys.sort()
    sorted_programs = {i: programs[i] for i in programs_keys}

    descriptions = EntityDescriptions()
    if programs:
        descriptions["active_program"] = [
            HCSensorEntityDescription(
                key="sensor_active_program",
                entity="BSH.Common.Root.ActiveProgram",
                device_class=SensorDeviceClass.ENUM,
                has_state_translation=False,
                mapping=sorted_programs,
            )
        ]
        descriptions["program"] = [
            HCSelectEntityDescription(
                key="select_program",
                entity="BSH.Common.Root.SelectedProgram",
                has_state_translation=False,
                mapping=sorted_programs,
            )
        ]

    return descriptions


def generate_wifi(appliance: HomeAppliance) -> EntityDescriptions:
    """Get WiFi sensor description."""
    entity = appliance.entities.get("BSH.Common.Status.WiFiSignalStrength")
    if entity is None:
        return HCSensorEntityDescription(
            key="sensor_wifi_signal_strength",
            device_class=SensorDeviceClass.SIGNAL_STRENGTH,
            native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
            entity_category=EntityCategory.DIAGNOSTIC,
            entity_registry_enabled_default=False,
        )
    return None


COMMON_ENTITY_DESCRIPTIONS: _EntityDescriptionsDefinitionsType = {
    "button": [
        HCButtonEntityDescription(
            key="button_abort_program",
            entity="BSH.Common.Command.AbortProgram",
        ),
        HCButtonEntityDescription(
            key="button_pause_program",
            entity="BSH.Common.Command.PauseProgram",
        ),
        HCButtonEntityDescription(
            key="button_resume_program",
            entity="BSH.Common.Command.ResumeProgram",
        ),
        HCButtonEntityDescription(
            key="button_mains_power_off",
            entity="BSH.Common.Command.MainsPowerOff",
        ),
    ],
    "binary_sensor": [
        HCBinarySensorEntityDescription(
            key="binary_sensor_door_state",
            entity="BSH.Common.Status.DoorState",
            device_class=BinarySensorDeviceClass.DOOR,
            value_on={"Open", "Ajar"},
            value_off={"Closed", "Locked"},
        ),
        HCBinarySensorEntityDescription(
            key="binary_sensor_aqua_stop",
            device_class=BinarySensorDeviceClass.PROBLEM,
            entity="BSH.Common.Event.AquaStopOccured",
            entity_registry_enabled_default=False,
            value_on={"Present"},
            value_off={"Off", "Confirmed"},
            entity_category=EntityCategory.DIAGNOSTIC,
        ),
        HCBinarySensorEntityDescription(
            key="binary_sensor_low_water_pressure",
            device_class=BinarySensorDeviceClass.PROBLEM,
            entity="BSH.Common.Event.LowWaterPressure",
            entity_registry_enabled_default=False,
            value_on={"Present"},
            value_off={"Off", "Confirmed"},
            entity_category=EntityCategory.DIAGNOSTIC,
        ),
        HCBinarySensorEntityDescription(
            key="binary_remote_start_allowed",
            entity="BSH.Common.Status.RemoteControlStartAllowed",
            entity_registry_enabled_default=False,
            entity_category=EntityCategory.DIAGNOSTIC,
        ),
        HCBinarySensorEntityDescription(
            key="binary_sensor_program_aborted",
            entity="BSH.Common.Event.ProgramAborted",
            entity_category=EntityCategory.DIAGNOSTIC,
            device_class=BinarySensorDeviceClass.PROBLEM,
            value_on={"Present", "Confirmed"},
            value_off={"Off"},
        ),
        HCBinarySensorEntityDescription(
            key="binary_sensor_program_finished",
            entity="BSH.Common.Event.ProgramFinished",
            entity_category=EntityCategory.DIAGNOSTIC,
            value_on={"Present", "Confirmed"},
            value_off={"Off"},
        ),
        HCBinarySensorEntityDescription(
            key="binary_sensor_interior_illumination",
            entity="BSH.Common.Status.InteriorIlluminationActive",
            entity_category=EntityCategory.DIAGNOSTIC,
        ),
    ],
    "select": [
        HCSelectEntityDescription(
            key="select_remote_control_level",
            entity="BSH.Common.Setting.RemoteControlLevel",
            entity_category=EntityCategory.CONFIG,
            entity_registry_enabled_default=False,
            has_state_translation=True,
        ),
    ],
    "sensor": [
        HCSensorEntityDescription(
            key="sensor_remaining_program_time",
            entity="BSH.Common.Option.RemainingProgramTime",
            device_class=SensorDeviceClass.DURATION,
            native_unit_of_measurement=UnitOfTime.SECONDS,
            suggested_unit_of_measurement=UnitOfTime.HOURS,
            extra_attributes=[
                {
                    "name": "Is Estimated",
                    "entity": "BSH.Common.Option.RemainingProgramTimeIsEstimated",
                }
            ],
        ),
        HCSensorEntityDescription(
            key="sensor_program_progress",
            entity="BSH.Common.Option.ProgramProgress",
            native_unit_of_measurement=PERCENTAGE,
        ),
        HCSensorEntityDescription(
            key="sensor_water_forecast",
            entity="BSH.Common.Option.WaterForecast",
            native_unit_of_measurement=PERCENTAGE,
            entity_category=EntityCategory.DIAGNOSTIC,
        ),
        HCSensorEntityDescription(
            key="sensor_energy_forecast",
            entity="BSH.Common.Option.EnergyForecast",
            native_unit_of_measurement=PERCENTAGE,
            entity_category=EntityCategory.DIAGNOSTIC,
        ),
        HCSensorEntityDescription(
            key="sensor_operation_state",
            entity="BSH.Common.Status.OperationState",
            device_class=SensorDeviceClass.ENUM,
            has_state_translation=True,
        ),
        HCSensorEntityDescription(
            key="sensor_start_in",
            entity="BSH.Common.Option.StartInRelative",
            device_class=SensorDeviceClass.DURATION,
            native_unit_of_measurement=UnitOfTime.SECONDS,
            suggested_unit_of_measurement=UnitOfTime.HOURS,
        ),
        HCSensorEntityDescription(
            key="sensor_finish_in",
            entity="BSH.Common.Option.FinishInRelative",
            device_class=SensorDeviceClass.DURATION,
            native_unit_of_measurement=UnitOfTime.SECONDS,
            suggested_unit_of_measurement=UnitOfTime.HOURS,
        ),
        HCSensorEntityDescription(
            key="sensor_count_started",
            entity="BSH.Common.Status.Program.All.Count.Started",
            entity_category=EntityCategory.DIAGNOSTIC,
            entity_registry_enabled_default=False,
            state_class=SensorStateClass.TOTAL_INCREASING,
            extra_attributes=[
                {
                    "name": "Last Start",
                    "entity": "BSH.Common.Status.ProgramSessionSummary.Latest",
                    "value_fn": lambda entity: entity.value["start"]
                    if entity.value is not None
                    else None,
                },
                {
                    "name": "Last End",
                    "entity": "BSH.Common.Status.ProgramSessionSummary.Latest",
                    "value_fn": lambda entity: entity.value["end"]
                    if entity.value is not None
                    else None,
                },
            ],
        ),
        HCSensorEntityDescription(
            key="sensor_count_completed",
            entity="BSH.Common.Status.Program.All.Count.Completed",
            entity_category=EntityCategory.DIAGNOSTIC,
            entity_registry_enabled_default=False,
            state_class=SensorStateClass.TOTAL_INCREASING,
        ),
        HCSensorEntityDescription(
            key="sensor_end_trigger",
            entity="BSH.Common.Status.ProgramRunDetail.EndTrigger",
            device_class=SensorDeviceClass.ENUM,
            entity_category=EntityCategory.DIAGNOSTIC,
            entity_registry_enabled_default=False,
            has_state_translation=True,
        ),
        HCSensorEntityDescription(
            key="sensor_power_state",
            entity="BSH.Common.Setting.PowerState",
            device_class=SensorDeviceClass.ENUM,
            has_state_translation=True,
        ),
        HCSensorEntityDescription(
            key="sensor_flex_start",
            entity="BSH.Common.Status.FlexStart",
            device_class=SensorDeviceClass.ENUM,
            has_state_translation=True,
        ),
        HCSensorEntityDescription(
            key="sensor_estimated_remaining_program_time",
            entity="BSH.Common.Option.EstimatedTotalProgramTime",
            device_class=SensorDeviceClass.DURATION,
            native_unit_of_measurement=UnitOfTime.SECONDS,
            suggested_unit_of_measurement=UnitOfTime.HOURS,
        ),
        HCSensorEntityDescription(
            key="sensor_wifi_signal_strength",
            entity="BSH.Common.Status.WiFiSignalStrength",
            device_class=SensorDeviceClass.SIGNAL_STRENGTH,
            native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
            entity_category=EntityCategory.DIAGNOSTIC,
            entity_registry_enabled_default=False,
        ),
        generate_door_state,
    ],
    "start_button": [generate_start_button],
    "switch": [
        HCSwitchEntityDescription(
            key="switch_child_lock",
            entity="BSH.Common.Setting.ChildLock",
            device_class=SwitchDeviceClass.SWITCH,
        ),
    ],
    "number": [
        HCNumberEntityDescription(
            key="number_duration",
            entity="BSH.Common.Option.Duration",
            device_class=NumberDeviceClass.DURATION,
            native_unit_of_measurement=UnitOfTime.SECONDS,
            mode=NumberMode.AUTO,
        ),
        HCNumberEntityDescription(
            key="number_start_in",
            entity="BSH.Common.Option.StartInRelative",
            device_class=NumberDeviceClass.DURATION,
            native_unit_of_measurement=UnitOfTime.SECONDS,
            mode=NumberMode.AUTO,
            entity_registry_enabled_default=False,
        ),
        HCNumberEntityDescription(
            key="number_finish_in",
            entity="BSH.Common.Option.FinishInRelative",
            device_class=NumberDeviceClass.DURATION,
            native_unit_of_measurement=UnitOfTime.SECONDS,
            mode=NumberMode.AUTO,
            entity_registry_enabled_default=False,
        ),
    ],
    "wifi": [generate_wifi],
    "dynamic": [generate_power_switch, generate_program],
}
