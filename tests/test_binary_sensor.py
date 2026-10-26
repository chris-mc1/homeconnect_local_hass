"""Tests for binary sensor entity."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.const import ATTR_FRIENDLY_NAME, STATE_OFF, STATE_ON, STATE_UNKNOWN

from . import setup_config_entry
from .const import CONFIG_ENTRIES

if TYPE_CHECKING:
    import pytest
    from homeassistant.core import HomeAssistant
    from homeconnect_websocket.testutils import MockAppliance


async def test_setup(
    hass: HomeAssistant,
    mock_appliance: MockAppliance,
    patch_entity_description: None,
) -> None:
    """Test setting up entity."""
    assert await setup_config_entry(hass, CONFIG_ENTRIES[0])

    state = hass.states.get("binary_sensor.fake_brand_homeappliance_binarysensor")
    assert state
    assert state.state == STATE_OFF
    assert state.name == "Fake_brand HomeAppliance BinarySensor"
    assert state.attributes[ATTR_FRIENDLY_NAME] == "Fake_brand HomeAppliance BinarySensor"

    state = hass.states.get("binary_sensor.fake_brand_homeappliance_binarysensor_enum")
    assert state
    assert state.state == STATE_UNKNOWN
    assert state.name == "Fake_brand HomeAppliance BinarySensor.Enum"
    assert state.attributes[ATTR_FRIENDLY_NAME] == "Fake_brand HomeAppliance BinarySensor.Enum"


async def test_update(
    hass: HomeAssistant,
    mock_appliance: MockAppliance,
    patch_entity_description: None,
) -> None:
    """Test updating entity."""
    entity_id = "binary_sensor.fake_brand_homeappliance_binarysensor"
    assert await setup_config_entry(hass, CONFIG_ENTRIES[0])

    await mock_appliance.entities["Test.BinarySensor"].update({"value": True})
    await hass.async_block_till_done()

    state = hass.states.get(entity_id)
    assert state.state == STATE_ON

    await mock_appliance.entities["Test.BinarySensor"].update({"value": False})
    await hass.async_block_till_done()

    state = hass.states.get(entity_id)
    assert state.state == STATE_OFF


async def test_update_enum(
    hass: HomeAssistant,
    mock_appliance: MockAppliance,
    patch_entity_description: None,
) -> None:
    """Test updating entity with enum."""
    entity_id = "binary_sensor.fake_brand_homeappliance_binarysensor_enum"
    assert await setup_config_entry(hass, CONFIG_ENTRIES[0])

    await mock_appliance.entities["Test.BinarySensor.Enum"].update({"value": 0})
    await hass.async_block_till_done()

    state = hass.states.get(entity_id)
    assert state.state == STATE_OFF

    await mock_appliance.entities["Test.BinarySensor.Enum"].update({"value": 1})
    await hass.async_block_till_done()

    state = hass.states.get(entity_id)
    assert state.state == STATE_ON


async def test_off_when_zero(
    hass: HomeAssistant,
    mock_appliance: MockAppliance,
    patch_entity_description: None,
) -> None:
    """Test the sensor is off when the other entity is 0, even if the event is Present."""
    entity_id = "binary_sensor.fake_brand_homeappliance_binarysensor_offwhenzero"
    assert await setup_config_entry(hass, CONFIG_ENTRIES[0])
    event = mock_appliance.entities["Test.Event1"]
    alarm_clock = mock_appliance.entities["Test.AlarmClock"]

    # A timer is started and the alarm elapses (the appliance reports Present)
    await alarm_clock.update({"value": 10})
    await event.update({"value": 1})  # Present
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state == STATE_ON

    # Confirmed on the appliance, the appliance leaves the event on Present
    await alarm_clock.update({"value": 0})
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state == STATE_OFF

    # Event reset
    await event.update({"value": 0})  # Off
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state == STATE_OFF


async def test_off_when_timer_started_after_event(
    hass: HomeAssistant,
    mock_appliance: MockAppliance,
    patch_entity_description: None,
) -> None:
    """Test an old Present is not reported as a new alarm when a timer is started."""
    entity_id = "binary_sensor.fake_brand_homeappliance_binarysensor_offwhenzero"
    assert await setup_config_entry(hass, CONFIG_ENTRIES[0])
    event = mock_appliance.entities["Test.Event1"]
    alarm_clock = mock_appliance.entities["Test.AlarmClock"]

    # First alarm: timer, elapsed, confirmed on the appliance. The event stays Present.
    await alarm_clock.update({"value": 10})
    await event.update({"value": 1})  # Present
    await alarm_clock.update({"value": 0})
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state == STATE_OFF

    # A new timer is started, the appliance still has the event on Present
    await alarm_clock.update({"value": 60})
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state == STATE_OFF

    # The appliance repeats the same value of the alarm clock, still no new alarm
    await alarm_clock.update({"value": 60})
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state == STATE_OFF

    # The appliance reports a new alarm: the event was reset and is Present again
    await event.update({"value": 0})  # Off
    await event.update({"value": 1})  # Present
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state == STATE_ON


async def test_off_when_zero_entity_missing(
    hass: HomeAssistant,
    mock_appliance: MockAppliance,
    patch_entity_description: None,
) -> None:
    """Test the sensor only uses the event when the appliance does not have the other entity."""
    entity_id = "binary_sensor.fake_brand_homeappliance_binarysensor_offwhenzero"
    mock_appliance.entities.pop("Test.AlarmClock")
    assert await setup_config_entry(hass, CONFIG_ENTRIES[0])

    await mock_appliance.entities["Test.Event1"].update({"value": 1})  # Present
    await hass.async_block_till_done()

    assert hass.states.get(entity_id).state == STATE_ON


async def test_hob_event_decides(
    hass: HomeAssistant,
    mock_appliance: MockAppliance,
    patch_entity_description: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test a hob: the alarm clock is 0 when the alarm elapses, the event alone decides."""
    # setitem: the info dict is shared by all tests, monkeypatch puts the old value back
    monkeypatch.setitem(mock_appliance.info, "type", "Hob")
    # The entity id contains the type of the appliance
    entity_id = "binary_sensor.fake_brand_hob_binarysensor_offwhenzero"
    assert await setup_config_entry(hass, CONFIG_ENTRIES[0])
    event = mock_appliance.entities["Test.Event1"]
    alarm_clock = mock_appliance.entities["Test.AlarmClock"]

    # The alarm elapses: the hob sets the alarm clock to 0 and reports Present
    await alarm_clock.update({"value": 0})
    await event.update({"value": 1})  # Present
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state == STATE_ON

    # Confirmed on the hob: the event is Off
    await event.update({"value": 0})  # Off
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state == STATE_OFF
