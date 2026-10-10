"""Tests for oven meat probe discovery, readings and target selection."""

from __future__ import annotations

from copy import deepcopy
from typing import TYPE_CHECKING
from unittest.mock import Mock

import pytest
from custom_components.homeconnect_ws import coordinator
from custom_components.homeconnect_ws.const import DOMAIN
from custom_components.homeconnect_ws.entity_descriptions import get_available_entities
from custom_components.homeconnect_ws.entity_descriptions.cooking import generate_oven_status
from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.components.select import ATTR_OPTION, ATTR_OPTIONS, SERVICE_SELECT_OPTION
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.const import (
    ATTR_DEVICE_CLASS,
    ATTR_ENTITY_ID,
    ATTR_UNIT_OF_MEASUREMENT,
    STATE_OFF,
    STATE_ON,
    STATE_UNAVAILABLE,
    UnitOfTemperature,
)
from homeassistant.helpers import entity_registry as er
from homeconnect_websocket.entities import Access, DeviceDescription, EntityDescription
from homeconnect_websocket.message import Action, Message

from . import setup_config_entry
from .const import CONFIG_ENTRIES, DEVICE_DESCRIPTION

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeconnect_websocket.testutils import MockAppliance, MockApplianceType

CURRENT_TEMPERATURE = "Cooking.Oven.Status.Cavity.001.CurrentMeatprobeTemperature"
PROBE_PLUGGED = "Cooking.Oven.Status.Cavity.001.MeatprobePlugged"
TARGET_TEMPERATURE = "Cooking.Oven.Option.MeatProbeTemperatureV2"
TARGET_ENUM = {"0": "Off", **{str(value): f"{value}dC" for value in range(30, 100)}}


def probe_status(cavity: str, uid: int) -> list[EntityDescription]:
    """Return public probe status fields, initially unplugged."""
    return [
        EntityDescription(
            uid=uid,
            name=f"Cooking.Oven.Status.Cavity.{cavity}.CurrentMeatprobeTemperature",
            access=Access.READ,
            available=False,
        ),
        EntityDescription(
            uid=uid + 2,
            name=f"Cooking.Oven.Status.Cavity.{cavity}.MeatprobePlugged",
            access=Access.READ,
            available=True,
            default=False,
        ),
    ]


@pytest.fixture
async def oven_appliance(
    mock_homeconnect_appliance: MockApplianceType, monkeypatch: pytest.MonkeyPatch
) -> MockAppliance:
    """Set up an oven advertising the probe fields used by a Bosch HMG778NB1."""
    description = deepcopy(DEVICE_DESCRIPTION)
    description["status"].extend(probe_status("001", 0x17C6))
    # This enumerated status must not be mistaken for the measured core temperature.
    description["status"].append(
        EntityDescription(
            uid=0x18B5,
            name="Cooking.Oven.Status.Cavity.001.MeatProbeTemperatureV2",
            access=Access.READ,
            available=True,
            enumeration=TARGET_ENUM,
        )
    )
    description["option"].append(
        EntityDescription(
            uid=0x1418,
            name=TARGET_TEMPERATURE,
            access=Access.READ_WRITE,
            available=True,
            min=0,
            max=99,
            enumeration=TARGET_ENUM,
        )
    )
    appliance = await mock_homeconnect_appliance(description=description)
    appliance.session.connected = True
    monkeypatch.setattr(coordinator, "HomeAppliance", Mock(return_value=appliance))
    monkeypatch.setattr(coordinator.HomeConnectCoordinator, "connected", True)
    return appliance


def entity_id(hass: HomeAssistant, appliance: MockAppliance, domain: str, key: str) -> str:
    """Find a probe entity by its stable unique ID."""
    result = er.async_get(hass).async_get_entity_id(
        domain, DOMAIN, f"{appliance.info['deviceID']}-{key}"
    )
    assert result is not None
    return result


@pytest.mark.parametrize("cavities", [(), ("001",), ("001", "002")])
async def test_probe_discovery(
    mock_homeconnect_appliance: MockApplianceType, cavities: tuple[str, ...]
) -> None:
    """Discover only advertised probes and distinguish multiple oven cavities."""
    description = DeviceDescription(
        status=[
            entity
            for index, cavity in enumerate(cavities)
            for entity in probe_status(cavity, 100 + index * 4)
        ]
    )
    appliance = await mock_homeconnect_appliance(description=description)
    descriptions = generate_oven_status(appliance)
    assert len(descriptions["sensor"]) == len(cavities)
    assert len(descriptions["binary_sensor"]) == len(cavities)
    assert len({entity.key for entity in descriptions["sensor"]}) == len(cavities)
    assert len({entity.key for entity in descriptions["binary_sensor"]}) == len(cavities)
    sensors = {entity.key: entity for entity in descriptions["sensor"]}
    binary_sensors = {entity.key: entity for entity in descriptions["binary_sensor"]}
    for cavity in cavities:
        group_name = f" {int(cavity)}" if len(cavities) > 1 else ""
        sensor = sensors[f"sensor_oven_current_meatprobe_temperature_{cavity}"]
        assert sensor.device_class == SensorDeviceClass.TEMPERATURE
        assert sensor.native_unit_of_measurement == UnitOfTemperature.CELSIUS
        assert sensor.translation_placeholders == {"group_name": group_name}
        assert binary_sensors[
            f"binary_sensor_oven_meatprobe_plugged_{cavity}"
        ].translation_placeholders == {"group_name": group_name}
    if not cavities:
        available = get_available_entities(appliance)
        assert not available["sensor"]
        assert not available["binary_sensor"]
        assert not available["select"]


async def test_probe_readings(hass: HomeAssistant, oven_appliance: MockAppliance) -> None:
    """Register an unplugged probe and update its availability and measured temperature."""
    assert await setup_config_entry(hass, CONFIG_ENTRIES[0])
    temperature_id = entity_id(
        hass, oven_appliance, "sensor", "sensor_oven_current_meatprobe_temperature_001"
    )
    plugged_id = entity_id(
        hass, oven_appliance, "binary_sensor", "binary_sensor_oven_meatprobe_plugged_001"
    )
    assert hass.states.get(temperature_id).state == STATE_UNAVAILABLE
    assert hass.states.get(plugged_id).state == STATE_OFF
    assert hass.states.get(plugged_id).attributes[ATTR_DEVICE_CLASS] == BinarySensorDeviceClass.PLUG

    await oven_appliance.entities[PROBE_PLUGGED].update({"value": True})
    await oven_appliance.entities[CURRENT_TEMPERATURE].update({"available": True, "value": 61.5})
    await hass.async_block_till_done()
    state = hass.states.get(temperature_id)
    assert state.state == "61.5"
    assert state.attributes[ATTR_UNIT_OF_MEASUREMENT] == UnitOfTemperature.CELSIUS
    assert state.attributes[ATTR_DEVICE_CLASS] == SensorDeviceClass.TEMPERATURE
    assert hass.states.get(plugged_id).state == STATE_ON

    await oven_appliance.entities[PROBE_PLUGGED].update({"value": False})
    await oven_appliance.entities[CURRENT_TEMPERATURE].update({"available": False})
    await hass.async_block_till_done()
    assert hass.states.get(temperature_id).state == STATE_UNAVAILABLE
    assert hass.states.get(plugged_id).state == STATE_OFF


@pytest.mark.parametrize(("option", "value"), [("off", 0), ("60dc", 60)])
async def test_probe_target(
    hass: HomeAssistant, oven_appliance: MockAppliance, option: str, value: int
) -> None:
    """Decode Off and Celsius targets and send the correct raw enum value."""
    assert await setup_config_entry(hass, CONFIG_ENTRIES[0])
    target_id = entity_id(hass, oven_appliance, "select", "select_oven_meat_probe_temperature")
    await oven_appliance.entities[TARGET_TEMPERATURE].update({"value": value})
    await hass.async_block_till_done()
    state = hass.states.get(target_id)
    assert state.state == option
    assert state.attributes[ATTR_OPTIONS] == ["off", *[f"{value}dc" for value in range(30, 100)]]

    await hass.services.async_call(
        "select",
        SERVICE_SELECT_OPTION,
        {ATTR_ENTITY_ID: target_id, ATTR_OPTION: option},
        blocking=True,
    )
    oven_appliance.session.send_sync.assert_awaited_once_with(
        Message(resource="/ro/values", action=Action.POST, data={"uid": 0x1418, "value": value})
    )
