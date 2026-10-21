"""Tests for button entity."""

from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.homeconnect_ws import button
from homeassistant.components.button import DOMAIN as BUTTON_DOMAIN
from homeassistant.components.button import SERVICE_PRESS
from homeassistant.const import ATTR_ENTITY_ID, ATTR_FRIENDLY_NAME, STATE_UNAVAILABLE
from homeconnect_websocket.errors import CodeResponsError
from homeconnect_websocket.message import Action, Message

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

    state = hass.states.get("button.fake_brand_homeappliance_activeprogram")
    assert state
    assert state.name == "Fake_brand HomeAppliance ActiveProgram"
    assert state.attributes[ATTR_FRIENDLY_NAME] == "Fake_brand HomeAppliance ActiveProgram"

    state = hass.states.get("button.fake_brand_homeappliance_abortprogram")
    assert state
    assert state.name == "Fake_brand HomeAppliance AbortProgram"
    assert state.attributes[ATTR_FRIENDLY_NAME] == "Fake_brand HomeAppliance AbortProgram"


async def test_start(
    hass: HomeAssistant,
    mock_appliance: MockAppliance,
    patch_entity_description: None,
) -> None:
    """Test pressing start button."""
    entity_id = "button.fake_brand_homeappliance_activeprogram"
    assert await setup_config_entry(hass, CONFIG_ENTRIES[0])
    await mock_appliance.entities["Test.SelectedProgram"].update({"value": 500})
    await hass.async_block_till_done()

    await hass.services.async_call(
        domain=BUTTON_DOMAIN,
        service=SERVICE_PRESS,
        service_data={ATTR_ENTITY_ID: entity_id},
        blocking=True,
    )

    mock_appliance.session.send_sync.assert_awaited_once_with(
        Message(
            resource="/ro/activeProgram",
            action=Action.POST,
            data={
                "program": 500,
                "options": [{"uid": 401, "value": None}, {"uid": 402, "value": None}],
            },
        )
    )


async def test_abort(
    hass: HomeAssistant,
    mock_appliance: MockAppliance,
    patch_entity_description: None,
) -> None:
    """Test pressing abort button."""
    entity_id = "button.fake_brand_homeappliance_abortprogram"
    assert await setup_config_entry(hass, CONFIG_ENTRIES[0])

    await hass.services.async_call(
        domain=BUTTON_DOMAIN,
        service=SERVICE_PRESS,
        service_data={ATTR_ENTITY_ID: entity_id},
        blocking=True,
    )

    mock_appliance.session.send_sync.assert_awaited_once_with(
        Message(
            resource="/ro/values",
            action=Action.POST,
            data={"uid": 300, "value": True},
        )
    )


ACKNOWLEDGE_ENTITY = "button.fake_brand_homeappliance_acknowledgeevent"
CANCEL_ENTITY = "button.fake_brand_homeappliance_cancelevent"
# AcknowledgeEvent (uid 6) is called with the uid of the event (Test.Event1, uid 800)
ACKNOWLEDGE_MESSAGE = Message(
    resource="/ro/values",
    action=Action.POST,
    data={"uid": 6, "value": 800},
)


async def _press(hass: HomeAssistant, entity_id: str) -> None:
    await hass.services.async_call(
        domain=BUTTON_DOMAIN,
        service=SERVICE_PRESS,
        service_data={ATTR_ENTITY_ID: entity_id},
        blocking=True,
    )


async def _set(hass: HomeAssistant, mock_appliance: MockAppliance, name: str, value: int) -> None:
    """Update an entity of the appliance like a separate message of the appliance."""
    await mock_appliance.entities[name].update({"value": value})
    await hass.async_block_till_done()


async def test_acknowledge_alarm_clock(
    hass: HomeAssistant,
    mock_appliance: MockAppliance,
    patch_entity_description: None,
) -> None:
    """Test the acknowledge button for an alarm that has elapsed."""
    assert await setup_config_entry(hass, CONFIG_ENTRIES[0])
    await _set(hass, mock_appliance, "Test.AlarmClock", 10)
    await _set(hass, mock_appliance, "Test.Event1", 1)  # Present: the alarm has elapsed

    assert hass.states.get(ACKNOWLEDGE_ENTITY).state != STATE_UNAVAILABLE
    assert hass.states.get(CANCEL_ENTITY).state == STATE_UNAVAILABLE

    await _press(hass, ACKNOWLEDGE_ENTITY)

    mock_appliance.session.send_sync.assert_awaited_once_with(ACKNOWLEDGE_MESSAGE)


async def test_cancel_alarm_clock(
    hass: HomeAssistant,
    mock_appliance: MockAppliance,
    patch_entity_description: None,
) -> None:
    """Test the cancel button for a timer that is running."""
    assert await setup_config_entry(hass, CONFIG_ENTRIES[0])
    await _set(hass, mock_appliance, "Test.Event1", 0)  # Off
    await _set(hass, mock_appliance, "Test.AlarmClock", 60)

    assert hass.states.get(CANCEL_ENTITY).state != STATE_UNAVAILABLE
    assert hass.states.get(ACKNOWLEDGE_ENTITY).state == STATE_UNAVAILABLE

    await _press(hass, CANCEL_ENTITY)

    mock_appliance.session.send_sync.assert_awaited_once_with(ACKNOWLEDGE_MESSAGE)


async def test_buttons_unavailable_without_alarm_clock(
    hass: HomeAssistant,
    mock_appliance: MockAppliance,
    patch_entity_description: None,
) -> None:
    """Test no button is available when no timer is set."""
    assert await setup_config_entry(hass, CONFIG_ENTRIES[0])
    await _set(hass, mock_appliance, "Test.Event1", 1)  # Present, left on by the appliance
    await _set(hass, mock_appliance, "Test.AlarmClock", 0)

    assert hass.states.get(ACKNOWLEDGE_ENTITY).state == STATE_UNAVAILABLE
    assert hass.states.get(CANCEL_ENTITY).state == STATE_UNAVAILABLE


async def test_new_timer_after_old_event_is_running(
    hass: HomeAssistant,
    mock_appliance: MockAppliance,
    patch_entity_description: None,
) -> None:
    """Test an event that is still on from an earlier alarm does not make an elapsed alarm."""
    assert await setup_config_entry(hass, CONFIG_ENTRIES[0])
    await _set(hass, mock_appliance, "Test.AlarmClock", 10)
    await _set(hass, mock_appliance, "Test.Event1", 1)  # The alarm elapsed
    await _set(hass, mock_appliance, "Test.AlarmClock", 0)  # Confirmed, the event stays on
    await _set(hass, mock_appliance, "Test.AlarmClock", 60)  # A new timer

    assert hass.states.get(CANCEL_ENTITY).state != STATE_UNAVAILABLE
    assert hass.states.get(ACKNOWLEDGE_ENTITY).state == STATE_UNAVAILABLE

    # The appliance reports the end of the new timer
    await _set(hass, mock_appliance, "Test.Event1", 0)
    await _set(hass, mock_appliance, "Test.Event1", 1)

    assert hass.states.get(ACKNOWLEDGE_ENTITY).state != STATE_UNAVAILABLE
    assert hass.states.get(CANCEL_ENTITY).state == STATE_UNAVAILABLE


async def test_buttons_without_alarm_clock_entity(
    hass: HomeAssistant,
    mock_appliance: MockAppliance,
    patch_entity_description: None,
) -> None:
    """Test the buttons have no restriction when the appliance has no alarm clock entity."""
    mock_appliance.entities.pop("Test.AlarmClock")
    assert await setup_config_entry(hass, CONFIG_ENTRIES[0])

    assert hass.states.get(ACKNOWLEDGE_ENTITY).state != STATE_UNAVAILABLE
    assert hass.states.get(CANCEL_ENTITY).state != STATE_UNAVAILABLE


async def test_cancel_alarm_clock_retries_when_busy(
    hass: HomeAssistant,
    mock_appliance: MockAppliance,
    patch_entity_description: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test a press while the appliance is busy is retried instead of raising an error."""
    monkeypatch.setattr(button, "ACKNOWLEDGE_RETRY_DELAY", 0)
    assert await setup_config_entry(hass, CONFIG_ENTRIES[0])
    await _set(hass, mock_appliance, "Test.AlarmClock", 60)
    mock_appliance.session.send_sync.side_effect = [
        CodeResponsError(516, "/ro/values"),
        CodeResponsError(516, "/ro/values"),
        None,
    ]

    await _press(hass, CANCEL_ENTITY)
    await hass.async_block_till_done(wait_background_tasks=True)

    assert mock_appliance.session.send_sync.await_count == 3


async def test_cancel_alarm_clock_retry_stops_when_alarm_clock_is_0(
    hass: HomeAssistant,
    mock_appliance: MockAppliance,
    patch_entity_description: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test the retry stops when the timer was cancelled on the appliance in the meantime."""
    monkeypatch.setattr(button, "ACKNOWLEDGE_RETRY_DELAY", 0)
    assert await setup_config_entry(hass, CONFIG_ENTRIES[0])
    await _set(hass, mock_appliance, "Test.AlarmClock", 60)
    alarm_clock = mock_appliance.entities["Test.AlarmClock"]

    async def busy_and_cancel_on_appliance(_: Message) -> None:
        await alarm_clock.update({"value": 0})
        raise CodeResponsError(516, "/ro/values")

    mock_appliance.session.send_sync.side_effect = busy_and_cancel_on_appliance

    await _press(hass, CANCEL_ENTITY)
    await hass.async_block_till_done(wait_background_tasks=True)

    assert mock_appliance.session.send_sync.await_count == 1
