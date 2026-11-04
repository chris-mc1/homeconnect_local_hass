"""Tests for entity descriptions."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import Mock

import pytest
from custom_components.homeconnect_ws import entity_descriptions
from custom_components.homeconnect_ws.entity_descriptions import (
    HCBinarySensorEntityDescription,
    HCButtonEntityDescription,
    HCLightEntityDescription,
    HCSelectEntityDescription,
    HCSensorEntityDescription,
    HCSwitchEntityDescription,
)
from custom_components.homeconnect_ws.entity_descriptions.common import (
    generate_power_switch,
    generate_program,
    generate_start_button,
)
from custom_components.homeconnect_ws.entity_descriptions.refrigeration import (
    generate_internal_light,
    generate_internal_light_brightness,
)
from custom_components.homeconnect_ws.helpers import merge_dicts
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.components.switch import SwitchDeviceClass
from homeconnect_websocket.entities import (
    Access,
    DeviceDescription,
    EntityDescription,
    Execution,
)

if TYPE_CHECKING:
    from homeconnect_websocket.testutils import MockAppliance, MockApplianceType


def test_merge_dicts() -> None:
    """Test merge dicts."""
    dict1 = {"a": [1, 2], "b": [3, 4]}
    dict2 = {"b": [5, 6], "c": [7, 8]}
    out_dict = merge_dicts(dict1, dict2)
    assert out_dict == {"a": [1, 2], "b": [3, 4, 5, 6], "c": [7, 8]}


MOCK_ENTITY_DESCRIPTIONS = {
    "binary_sensor": [
        HCBinarySensorEntityDescription(key="binary_sensor_available", entity="Test.BinarySensor"),
        HCBinarySensorEntityDescription(
            key="binary_sensor_not_available", entity="Test.BinarySensor2"
        ),
    ],
    "event_sensor": [
        HCSensorEntityDescription(
            key="sensor_event_available",
            entities=[
                "Test.Event1",
                "Test.Event2",
            ],
        ),
        HCSensorEntityDescription(
            key="sensor_event_not_available",
            entities=[
                "Test.Event1",
                "Test.Event3",
            ],
        ),
    ],
}


def test_get_available_entities(
    mock_appliance: MockAppliance, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test get_available_entities."""
    monkeypatch.setattr(
        entity_descriptions,
        "get_all_entity_description",
        Mock(return_value=MOCK_ENTITY_DESCRIPTIONS),
    )
    entities = entity_descriptions.get_available_entities(mock_appliance)
    assert entities["binary_sensor"] == [
        HCBinarySensorEntityDescription(key="binary_sensor_available", entity="Test.BinarySensor")
    ]
    assert entities["event_sensor"] == [
        HCSensorEntityDescription(
            key="sensor_event_available",
            entities=[
                "Test.Event1",
                "Test.Event2",
            ],
        )
    ]


POWER_SWITCH = {
    "setting": [
        {
            "access": "readwrite",
            "available": True,
            "enumeration": {"0": "MainsOff", "1": "Off", "2": "On", "3": "Standby"},
            "min": 0,
            "max": 2,
            "uid": 539,
            "name": "BSH.Common.Setting.PowerState",
        },
    ]
}


async def test_power_switch(mock_homeconnect_appliance: MockApplianceType) -> None:
    """Test dynamic Power switch."""
    device_description = POWER_SWITCH.copy()

    # On/Off Switch
    device_description["setting"][0]["min"] = 1
    device_description["setting"][0]["max"] = 2
    appliance = await mock_homeconnect_appliance(description=device_description)
    switch_description = generate_power_switch(appliance)

    assert switch_description["switch"][0] == HCSwitchEntityDescription(
        key="switch_power_state",
        entity="BSH.Common.Setting.PowerState",
        device_class=SwitchDeviceClass.SWITCH,
        value_mapping=("On", "Off"),
    )

    # No Switch
    device_description["setting"][0]["min"] = 0
    device_description["setting"][0]["max"] = 4
    appliance = await mock_homeconnect_appliance(description=device_description)
    switch_description = generate_power_switch(appliance)

    assert "switch" not in switch_description

    # On/MainsOff Switch
    device_description["setting"][0]["enumeration"] = {"0": "MainsOff", "2": "On"}
    appliance = await mock_homeconnect_appliance(description=device_description)
    switch_description = generate_power_switch(appliance)

    assert switch_description["switch"][0] == HCSwitchEntityDescription(
        key="switch_power_state",
        entity="BSH.Common.Setting.PowerState",
        device_class=SwitchDeviceClass.SWITCH,
        value_mapping=("On", "MainsOff"),
    )

    # Standby/Off Switch
    device_description["setting"][0]["enumeration"] = {"1": "Off", "3": "Standby"}
    appliance = await mock_homeconnect_appliance(description=device_description)
    switch_description = generate_power_switch(appliance)

    assert switch_description["switch"][0] == HCSwitchEntityDescription(
        key="switch_power_state",
        entity="BSH.Common.Setting.PowerState",
        device_class=SwitchDeviceClass.SWITCH,
        value_mapping=("Standby", "Off"),
    )


PROGRAM = DeviceDescription(
    setting=[
        EntityDescription(
            uid=101,
            name="BSH.Common.Setting.Favorite.001.Name",
            access=Access.READ_WRITE,
            available=True,
            max=30,
            min=0,
            default="Named Favorite",
        ),
        EntityDescription(
            uid=102,
            name="BSH.Common.Setting.Favorite.002.Name",
            access=Access.READ_WRITE,
            available=True,
            max=30,
            min=0,
            default="",
        ),
    ],
    program=[
        EntityDescription(
            uid=201,
            name="BSH.Common.Program.Favorite.001",
            available=True,
        ),
        EntityDescription(
            uid=202,
            name="BSH.Common.Program.Favorite.002",
            available=True,
        ),
        EntityDescription(
            uid=500,
            name="BSH.Common.Program.Program1",
        ),
    ],
)


async def test_program(mock_homeconnect_appliance: MockApplianceType) -> None:
    """Test dynamic Program."""
    appliance = await mock_homeconnect_appliance(description=PROGRAM)
    program_description = generate_program(appliance)
    assert program_description["program"][0] == HCSelectEntityDescription(
        key="select_program",
        entity="BSH.Common.Root.SelectedProgram",
        has_state_translation=False,
        mapping={
            "BSH.Common.Program.Favorite.001": "Named Favorite",
            "BSH.Common.Program.Favorite.002": "favorite_002",
            "BSH.Common.Program.Program1": "bsh_common_program_program1",
        },
    )
    assert program_description["active_program"][0] == HCSensorEntityDescription(
        key="sensor_active_program",
        entity="BSH.Common.Root.ActiveProgram",
        has_state_translation=False,
        device_class=SensorDeviceClass.ENUM,
        mapping={
            "BSH.Common.Program.Favorite.001": "Named Favorite",
            "BSH.Common.Program.Favorite.002": "favorite_002",
            "BSH.Common.Program.Program1": "bsh_common_program_program1",
        },
    )

    appliance = await mock_homeconnect_appliance(description={})


def _start_button_description(*executions: Execution | None) -> DeviceDescription:
    """Build a device description with one program per given execution type."""
    programs = []
    for index, execution in enumerate(executions):
        program = EntityDescription(uid=600 + index, name=f"Test.Program.Program{index}")
        if execution is not None:
            program["execution"] = execution
        programs.append(program)
    return DeviceDescription(
        program=programs,
        activeProgram=EntityDescription(uid=700, name="BSH.Common.Root.ActiveProgram"),
        selectedProgram=EntityDescription(uid=701, name="BSH.Common.Root.SelectedProgram"),
    )


@pytest.mark.parametrize(
    ("executions", "has_start_button"),
    [
        # no execution attribute, library default is "selectandstart"
        ((None,), True),
        ((Execution.SELECT_AND_START,), True),
        # execution "none" in the stored description, the appliance reports
        # the actual execution at runtime (issue #400)
        ((Execution.NONE, Execution.NONE), True),
        ((Execution.START_ONLY, Execution.NONE), True),
        # programs that can't be selected and started remotely
        ((Execution.START_ONLY,), False),
        ((Execution.START_ONLY, Execution.SELECT_ONLY), False),
        ((), False),
    ],
)
async def test_start_button(
    mock_homeconnect_appliance: MockApplianceType,
    executions: tuple[Execution | None, ...],
    *,
    has_start_button: bool,
) -> None:
    """Test dynamic Start button."""
    appliance = await mock_homeconnect_appliance(description=_start_button_description(*executions))
    start_button_description = generate_start_button(appliance)
    if has_start_button:
        assert start_button_description == HCButtonEntityDescription(
            key="button_start_program",
            entity="BSH.Common.Root.ActiveProgram",
        )
    else:
        assert start_button_description is None


INTERNAL_LIGHT = DeviceDescription(
    setting=[
        EntityDescription(
            uid=0x5001,
            name="Refrigeration.Common.Setting.Light.Internal.Power",
            access=Access.READ_WRITE,
            available=True,
        ),
        EntityDescription(
            uid=0x5002,
            name="Refrigeration.Common.Setting.Light.Internal.Brightness",
            access=Access.READ_WRITE,
            available=True,
            max=100,
            min=0,
        ),
    ]
)


async def test_internal_light(mock_homeconnect_appliance: MockApplianceType) -> None:
    """Test dynamic internal light."""
    # Power + Brightness
    appliance = await mock_homeconnect_appliance(description=INTERNAL_LIGHT)
    assert generate_internal_light(appliance) == HCLightEntityDescription(
        key="light_internal",
        entity="Refrigeration.Common.Setting.Light.Internal.Power",
        brightness_entity="Refrigeration.Common.Setting.Light.Internal.Brightness",
    )

    # Power only
    power_only = DeviceDescription(setting=[INTERNAL_LIGHT["setting"][0]])
    appliance = await mock_homeconnect_appliance(description=power_only)
    assert generate_internal_light(appliance) == HCLightEntityDescription(
        key="light_internal",
        entity="Refrigeration.Common.Setting.Light.Internal.Power",
    )

    # No internal light
    appliance = await mock_homeconnect_appliance(description={})
    assert generate_internal_light(appliance) is None


async def test_internal_light_brightness(mock_homeconnect_appliance: MockApplianceType) -> None:
    """Test the brightness number defers to the light entity."""
    # Light entity owns brightness, so the number is opt-in
    appliance = await mock_homeconnect_appliance(description=INTERNAL_LIGHT)
    description = generate_internal_light_brightness(appliance)
    assert description.entity_registry_enabled_default is False

    # No light entity to own it, so the number is the only control
    brightness_only = DeviceDescription(setting=[INTERNAL_LIGHT["setting"][1]])
    appliance = await mock_homeconnect_appliance(description=brightness_only)
    description = generate_internal_light_brightness(appliance)
    assert description.entity_registry_enabled_default is True

    # No brightness at all
    appliance = await mock_homeconnect_appliance(description={})
    assert generate_internal_light_brightness(appliance) is None


TRANSLATION_DOMAINS = {
    "active_program": "sensor",
    "binary_sensor": "binary_sensor",
    "button": "button",
    "event_sensor": "sensor",
    "fan": "fan",
    "light": "light",
    "number": "number",
    "program": "select",
    "select": "select",
    "sensor": "sensor",
    "start_button": "button",
    "switch": "switch",
    "wifi": "sensor",
}


def test_descriptions_have_english_name() -> None:
    """Test every entity description resolves to a name in en.json."""
    translations = json.loads(
        Path("custom_components/homeconnect_ws/translations/en.json").read_text(encoding="utf-8")
    )["entity"]

    missing = []
    for description_type, descriptions in entity_descriptions.get_all_entity_description().items():
        if description_type == "dynamic":
            continue
        domain = TRANSLATION_DOMAINS[description_type]
        for description in descriptions:
            if callable(description):
                continue
            key = description.translation_key or description.key
            if key not in translations.get(domain, {}):
                missing.append(f"{domain}.{key}")

    assert sorted(set(missing)) == []
