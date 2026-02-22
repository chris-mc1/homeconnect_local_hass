"""Test Constants."""

from __future__ import annotations

from custom_components.homeconnect_ws.const import (
    CONF_AES_IV,
    CONF_PSK,
)
from custom_components.homeconnect_ws.entity_descriptions import (
    HCBinarySensorEntityDescription,
    HCButtonEntityDescription,
    HCFanEntityDescription,
    HCLightEntityDescription,
    HCNumberEntityDescription,
    HCSelectEntityDescription,
    HCSensorEntityDescription,
    HCSwitchEntityDescription,
    _EntityDescriptionsType,
)
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.const import CONF_DESCRIPTION, CONF_DEVICE_ID, CONF_HOST, CONF_NAME
from homeconnect_websocket.entities import (
    Access,
    DeviceDescription,
    EntityDescription,
    Execution,
    OptionDescription,
)

MOCK_APPLIANCE_INFO = {
    "brand": "Fake_Brand",
    "type": "HomeAppliance",
    "deviceID": "Fake_deviceID",
    "vib": "Fake_vib",
    "haVersion": "1.1",
    "hwVersion": "2.2",
    "swVersion": "3.3",
    "mac": "78-43-F2-23-C8-D7",
    "serialNumber": "Fake_serialNumber",
}

MOCK_TLS_DEVICE_ID = "010203040506070809"
MOCK_TLS_DEVICE_ID_2 = "102030405060708090"
MOCK_TLS_DEVICE_DESCRIPTION = "MOCK_TLS_DEVICE_DESCRIPTION"
MOCK_TLS_DEVICE_INFO = {
    "haId": MOCK_TLS_DEVICE_ID,
    "type": "Test_TLS",
    "serialNumber": MOCK_TLS_DEVICE_ID,
    "brand": "Test_Brand",
    "vib": "Test_vib",
    "mac": "00-00-00-00-00-01",
    "featureMappingFileName": "010203040506070809_FeatureMapping.xml",
    "deviceDescriptionFileName": "010203040506070809_DeviceDescription.xml",
    "created": "2025-01-07T11:34:30.833000000+01:00",
    "connectionType": "TLS",
    "key": "TLS_PSK_KEY",
}


MOCK_AES_DEVICE_ID = "101112131415161718"
MOCK_AES_DEVICE_DESCRIPTION = "MOCK_AES_DEVICE_DESCRIPTION"
MOCK_AES_DEVICE_INFO = {
    "haId": MOCK_AES_DEVICE_ID,
    "type": "Test_AES",
    "serialNumber": MOCK_AES_DEVICE_ID,
    "brand": "Test_Brand",
    "vib": "Test_vib",
    "mac": "00-00-00-00-00-02",
    "featureMappingFileName": "101112131415161718_FeatureMapping.xml",
    "deviceDescriptionFileName": "101112131415161718_DeviceDescription.xml",
    "created": "2025-01-07T11:34:30.833000000+01:00",
    "connectionType": "AES",
    "key": "AES_PSK_KEY",
    "iv": "AES_IV",
}

ENTITY_DESCRIPTIONS: _EntityDescriptionsType = {
    "button": [
        HCButtonEntityDescription(
            key="Test.AbortProgram", name="AbortProgram", entity="Test.AbortProgram"
        )
    ],
    "active_program": [
        HCSensorEntityDescription(
            key="Test.ActiveProgram",
            name="ActiveProgram",
            entity="Test.ActiveProgram",
            has_state_translation=False,
            device_class=SensorDeviceClass.ENUM,
            mapping={
                "BSH.Common.Program.Favorite.001": "Named Favorite",
                "BSH.Common.Program.Favorite.002": "favorite_002",
                "Test.Program.Program1": "test_program_program1",
                "Test.Program.Program2": "test_program_program2",
            },
        )
    ],
    "binary_sensor": [
        HCBinarySensorEntityDescription(
            key="Test.BinarySensor", name="BinarySensor", entity="Test.BinarySensor"
        ),
        HCBinarySensorEntityDescription(
            key="Test.BinarySensor.Enum",
            name="BinarySensor.Enum",
            entity="Test.BinarySensor.Enum",
            value_on={"On"},
            value_off={"Off"},
        ),
    ],
    "event_sensor": [
        HCSensorEntityDescription(
            key="Test.Event",
            name="Sensor.Event",
            entities=[
                "Test.Event2",
                "Test.Event1",
            ],
            device_class=SensorDeviceClass.ENUM,
            options=["Event2", "Event1", "No Event"],
        ),
    ],
    "number": [HCNumberEntityDescription(key="Test.Number", name="Number", entity="Test.Number")],
    "program": [
        HCSelectEntityDescription(
            key="Test.SelectedProgram",
            name="SelectedProgram",
            entity="Test.SelectedProgram",
            mapping={
                "BSH.Common.Program.Favorite.001": "Named Favorite",
                "BSH.Common.Program.Favorite.002": "favorite_002",
                "Test.Program.Program1": "test_program_program1",
                "Test.Program.Program2": "test_program_program2",
                "Test.Program.Program3": "test_program_program3",
            },
        )
    ],
    "select": [
        HCSelectEntityDescription(key="Test.Select", name="Select", entity="Test.Select"),
        HCSelectEntityDescription(
            key="Test.Select.Translated",
            name="Select.Translated",
            entity="Test.Select",
            has_state_translation=True,
        ),
        HCSelectEntityDescription(
            key="Test.Select.Options",
            name="Select.Options",
            entity="Test.Select",
            has_state_translation=True,
            options=["option2"],
        ),
    ],
    "sensor": [
        HCSensorEntityDescription(key="Test.Sensor", name="Sensor", entity="Test.Sensor"),
        HCSensorEntityDescription(
            key="Test.Sensor.Enum",
            name="Sensor.Enum",
            entity="Test.Sensor.Enum",
            device_class=SensorDeviceClass.ENUM,
        ),
    ],
    "start_button": [
        HCButtonEntityDescription(
            key="Test.ActiveProgram", name="ActiveProgram", entity="Test.ActiveProgram"
        )
    ],
    "switch": [
        HCSwitchEntityDescription(key="Test.Switch", name="Switch", entity="Test.Switch"),
        HCSwitchEntityDescription(
            key="Test.Switch.Enum",
            name="Switch.Enum",
            entity="Test.Switch.Enum",
            value_mapping=("On", "Off"),
        ),
    ],
    "fan": [
        HCFanEntityDescription(
            key="Test.Fan",
            name="Fan",
            entities=["Test.FanSpeed1", "Test.FanSpeed2"],
        )
    ],
    "light": [
        HCLightEntityDescription(
            key="Test.Light.1",
            name="Light.1",
            entity="Test.Lighting",
        ),
        HCLightEntityDescription(
            key="Test.Light.2",
            name="Light.2",
            entity="Test.Lighting",
            brightness_entity="Test.LightingBrightness",
        ),
        HCLightEntityDescription(
            key="Test.Light.3",
            name="Light.3",
            entity="Test.Lighting",
            brightness_entity="Test.LightingBrightness",
            color_temperature_entity="Test.LightingColorTempPercent",
        ),
        HCLightEntityDescription(
            key="Test.Light.4",
            name="Light.4",
            entity="Test.Lighting",
            color_entity="Test.LightingCustomColor",
            color_mode_entity="Test.LightingColor",
        ),
    ],
}
DEVICE_DESCRIPTION = DeviceDescription(
    status=[
        EntityDescription(
            uid=100,
            name="Test.BinarySensor",
            available=True,
            access=Access.READ_WRITE,
        ),
        EntityDescription(
            uid=101,
            name="Test.BinarySensor.Enum",
            enumeration={"0": "Off", "1": "On"},
            available=True,
            access=Access.READ_WRITE,
        ),
        EntityDescription(
            uid=102,
            name="Test.Sensor",
            available=True,
            access=Access.READ_WRITE,
        ),
        EntityDescription(
            uid=103,
            name="Test.Sensor.Enum",
            enumeration={
                "0": "Off",
                "1": "On",
            },
            available=True,
            access=Access.READ_WRITE,
        ),
        EntityDescription(
            uid=104,
            name="Test.RegEx.001.Sensor",
            available=True,
            access=Access.READ,
        ),
        EntityDescription(
            uid=105,
            name="Test.RegEx.002.Sensor",
            available=True,
            access=Access.READ,
        ),
    ],
    setting=[
        EntityDescription(
            uid=200,
            name="Test.PowerState",
            enumeration={"1": "Off", "2": "On"},
            available=True,
            access=Access.READ_WRITE,
        ),
        EntityDescription(
            uid=201,
            name="Test.Switch",
            available=True,
            access=Access.READ_WRITE,
        ),
        EntityDescription(
            uid=202,
            name="Test.Switch.Enum",
            enumeration={"0": "Off", "1": "On"},
            available=True,
            access=Access.READ_WRITE,
        ),
        EntityDescription(
            uid=203,
            name="Test.Select",
            enumeration={"0": "Option1", "1": "Option2", "2": "Option3"},
            available=True,
            access=Access.READ_WRITE,
        ),
        EntityDescription(
            uid=204,
            name="Test.Number",
            min=0,
            max=20,
            stepSize=2,
            available=True,
            access=Access.READ_WRITE,
        ),
        EntityDescription(
            uid=104,
            name="Test.RegEx.001.Switch",
            available=True,
            access=Access.READ_WRITE,
        ),
        EntityDescription(
            uid=105,
            name="Test.RegEx.002.Switch",
            available=True,
            access=Access.READ_WRITE,
        ),
        EntityDescription(
            uid=106,
            name="BSH.Common.Setting.Favorite.001.Name",
            access=Access.READ_WRITE,
            available=True,
            default="Named Favorite",
        ),
        EntityDescription(
            uid=107,
            name="BSH.Common.Setting.Favorite.002.Name",
            access=Access.READ_WRITE,
            available=True,
            default="",
        ),
        EntityDescription(
            uid=108,
            name="Test.Lighting",
            access=Access.READ_WRITE,
            available=True,
            protocolType="Boolean",
        ),
        EntityDescription(
            uid=109,
            name="Test.LightingBrightness",
            access=Access.READ_WRITE,
            available=True,
            default=0,
            min=2,
            max=100,
            protocolType="Float",
        ),
        EntityDescription(
            uid=110,
            name="Test.LightingColorTempPercent",
            access=Access.READ_WRITE,
            available=True,
            default=0,
            min=0,
            max=100,
            protocolType="Float",
        ),
        EntityDescription(
            uid=111,
            name="Test.LightingCustomColor",
            access=Access.READ_WRITE,
            available=True,
            default="#000000",
            protocolType="String",
        ),
        EntityDescription(
            uid=112,
            name="Test.LightingColor",
            access=Access.READ_WRITE,
            available=True,
            default=0,
            enumeration={
                "1": "CustomColor",
                "33": "Color32",
                "34": "Color33",
            },
            protocolType="Integer",
        ),
        EntityDescription(
            uid=113,
            name="Cooking.Hood.Setting.ColorTemperature",
            access=Access.READ_WRITE,
            available=True,
            default=0,
            enumeration={
                "0": "custom",
                "1": "warm",
                "2": "warmToNeutral",
                "3": "neutral",
                "4": "neutralToCold",
                "5": "cold",
            },
            protocolType="Integer",
        ),
    ],
    event=[
        EntityDescription(
            uid=800,
            name="Test.Event1",
            enumeration={"0": "Off", "1": "Present", "2": "Confirmed"},
        ),
        EntityDescription(
            uid=801,
            name="Test.Event2",
            enumeration={"0": "Off", "1": "Present", "2": "Confirmed"},
        ),
    ],
    command=[
        EntityDescription(
            uid=300,
            name="Test.AbortProgram",
            available=True,
            access=Access.READ_WRITE,
        )
    ],
    option=[
        EntityDescription(
            uid=401,
            name="Test.Option1",
            available=True,
            access=Access.READ_WRITE,
        ),
        EntityDescription(
            uid=402,
            name="Test.Option2",
            available=True,
            access=Access.READ_WRITE,
        ),
        EntityDescription(
            uid=403,
            name="Test.FanSpeed1",
            available=True,
            access=Access.READ_WRITE,
            enumeration={"0": "Off", "1": "Speed1", "2": "Speed1"},
            default=0,
        ),
        EntityDescription(
            uid=404,
            name="Test.FanSpeed2",
            available=True,
            access=Access.READ_WRITE,
            enumeration={"0": "Off", "1": "Speed1", "2": "Speed1"},
            default=0,
        ),
    ],
    program=[
        EntityDescription(
            uid=500,
            name="Test.Program.Program1",
            options=[
                OptionDescription(access=Access.READ_WRITE, available=True, refUID=401),
                OptionDescription(access=Access.READ_WRITE, available=True, refUID=402),
            ],
        ),
        EntityDescription(
            uid=501,
            name="Test.Program.Program2",
            options=[
                OptionDescription(access=Access.READ_WRITE, available=True, refUID=401),
                OptionDescription(access=Access.READ_WRITE, available=True, refUID=402),
            ],
        ),
        EntityDescription(
            uid=502,
            name="Test.Program.Program3",
            options=[
                OptionDescription(access=Access.READ_WRITE, available=True, refUID=401),
                OptionDescription(access=Access.READ_WRITE, available=True, refUID=402),
            ],
            execution=Execution.START_ONLY,
        ),
        EntityDescription(
            uid=502,
            name="BSH.Common.Program.Favorite.001",
            available=True,
        ),
        EntityDescription(
            uid=503,
            name="BSH.Common.Program.Favorite.002",
            available=True,
        ),
    ],
    selectedProgram=EntityDescription(
        uid=600,
        name="Test.SelectedProgram",
        access=Access.READ_WRITE,
    ),
    activeProgram=EntityDescription(
        uid=700,
        name="Test.ActiveProgram",
        access=Access.READ_WRITE,
    ),
    info=MOCK_APPLIANCE_INFO,
)

MOCK_CONFIG_DATA = {
    CONF_DESCRIPTION: DEVICE_DESCRIPTION,
    CONF_HOST: "1.2.3.4",
    CONF_PSK: "PSK_KEY",
    CONF_AES_IV: "AES_IV",
    CONF_DEVICE_ID: "Test_Device_ID",
    CONF_NAME: "Fake_Brand HomeAppliance",
}
