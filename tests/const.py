"""Test Constants."""

from __future__ import annotations

from custom_components.homeconnect_ws.const import (
    CONF_AES_IV,
    CONF_PSK,
)
from custom_components.homeconnect_ws.entity_descriptions import (
    HCBinarySensorEntityDescription,
    HCButtonEntityDescription,
    HCNumberEntityDescription,
    HCSelectEntityDescription,
    HCSensorEntityDescription,
    HCSwitchEntityDescription,
)
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.const import CONF_DESCRIPTION, CONF_DEVICE_ID, CONF_HOST, CONF_NAME
from homeconnect_websocket.entities import (
    Access,
    DeviceDescription,
    EntityDescription,
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

ENTITY_DESCRIPTIONS = {
    "abort_button": [
        HCButtonEntityDescription(
            key="Test.AbortProgram", name="AbortProgram", entity="Test.AbortProgram"
        )
    ],
    "active_program": [
        HCSensorEntityDescription(
            key="Test.ActiveProgram",
            name="ActiveProgram",
            entity="Test.ActiveProgram",
            device_class=SensorDeviceClass.ENUM,
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
    "power_switch": [
        HCSwitchEntityDescription(
            key="Test.PowerState", name="PowerState", entity="Test.PowerState"
        )
    ],
    "program": [
        HCSelectEntityDescription(
            key="Test.SelectedProgram", name="SelectedProgram", entity="Test.SelectedProgram"
        )
    ],
    "select": [HCSelectEntityDescription(key="Test.Select", name="Select", entity="Test.Select")],
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
