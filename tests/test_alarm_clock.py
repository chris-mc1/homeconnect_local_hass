"""Tests for the alarm clock cleaner."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from custom_components.homeconnect_ws import alarm_clock
from homeconnect_websocket.errors import CodeResponsError
from homeconnect_websocket.message import Action, Message

from . import setup_config_entry
from .const import CONFIG_ENTRIES

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeconnect_websocket.testutils import MockAppliance

ACKNOWLEDGE_MESSAGE = Message(
    resource="/ro/values",
    action=Action.POST,
    # AcknowledgeEvent (uid 6) is called with the uid of the event (Test.Event1, uid 800)
    data={"uid": 6, "value": 800},
)


@pytest.fixture(autouse=True)
def patch_entities(monkeypatch: pytest.MonkeyPatch) -> None:
    """Use the entities of the test appliance and do not wait between attempts."""
    monkeypatch.setattr(alarm_clock, "EVENT", "Test.Event1")
    monkeypatch.setattr(alarm_clock, "ALARM_CLOCK", "Test.AlarmClock")
    monkeypatch.setattr(alarm_clock, "LOCAL_CONTROL", "Test.LocalControlActive")
    monkeypatch.setattr(alarm_clock, "RETRY_DELAY", 0)
    monkeypatch.setattr(alarm_clock, "COOLDOWN", 0)


class Oven:
    """Updates the entities of the appliance like separate messages of the appliance."""

    def __init__(self, hass: HomeAssistant, mock_appliance: MockAppliance) -> None:
        self._hass = hass
        self._entities = {
            "event": mock_appliance.entities["Test.Event1"],
            "alarm_clock": mock_appliance.entities["Test.AlarmClock"],
            "local": mock_appliance.entities["Test.LocalControlActive"],
        }

    async def set(self, name: str, value: float | bool) -> None:  # noqa: FBT001
        """Update an entity and wait until the callbacks are done."""
        await self._entities[name].update({"value": value})
        await self._hass.async_block_till_done(wait_background_tasks=True)


async def _setup(hass: HomeAssistant, mock_appliance: MockAppliance) -> Oven:
    """Set up the integration and return the oven."""
    assert await setup_config_entry(hass, CONFIG_ENTRIES[0])
    mock_appliance.session.send_sync.assert_not_awaited()
    return Oven(hass, mock_appliance)


async def test_acknowledge(
    hass: HomeAssistant,
    mock_appliance: MockAppliance,
    patch_entity_description: None,
) -> None:
    """Test the event is acknowledged when confirmed on the appliance and it is free."""
    oven = await _setup(hass, mock_appliance)

    await oven.set("local", value=True)
    await oven.set("alarm_clock", 10)
    await oven.set("event", 1)  # Present
    await oven.set("alarm_clock", 0)  # Confirmed on the appliance
    # Still operated locally: the appliance would answer Busy
    mock_appliance.session.send_sync.assert_not_awaited()

    await oven.set("local", value=False)

    mock_appliance.session.send_sync.assert_awaited_once_with(ACKNOWLEDGE_MESSAGE)


async def test_not_acknowledged_before_confirmed(
    hass: HomeAssistant,
    mock_appliance: MockAppliance,
    patch_entity_description: None,
) -> None:
    """Test the alarm is not removed from the appliance before it is confirmed there."""
    oven = await _setup(hass, mock_appliance)

    await oven.set("alarm_clock", 10)
    await oven.set("event", 1)  # Present, not confirmed
    await oven.set("local", value=False)
    await hass.async_block_till_done(wait_background_tasks=True)

    mock_appliance.session.send_sync.assert_not_awaited()


async def test_retry_when_busy(
    hass: HomeAssistant,
    mock_appliance: MockAppliance,
    patch_entity_description: None,
) -> None:
    """Test acknowledging is retried when the appliance answers WriteRequest Busy (516)."""
    mock_appliance.session.send_sync.side_effect = [CodeResponsError(516, "/ro/values"), None]
    oven = await _setup(hass, mock_appliance)

    await oven.set("event", 1)  # Present
    await oven.set("alarm_clock", 0)
    await oven.set("local", value=False)

    assert mock_appliance.session.send_sync.await_count == 2
    mock_appliance.session.send_sync.assert_awaited_with(ACKNOWLEDGE_MESSAGE)


async def test_retry_stops_when_timer_started(
    hass: HomeAssistant,
    mock_appliance: MockAppliance,
    patch_entity_description: None,
) -> None:
    """Test a retry is skipped when a new timer was started in the meantime."""
    oven = await _setup(hass, mock_appliance)

    async def busy_and_start_timer(_: Message) -> None:
        await oven.set("alarm_clock", 10)
        raise CodeResponsError(516, "/ro/values")

    mock_appliance.session.send_sync.side_effect = busy_and_start_timer

    await oven.set("event", 1)  # Present
    await oven.set("alarm_clock", 0)
    await oven.set("local", value=False)
    await hass.async_block_till_done(wait_background_tasks=True)

    # Acknowledging would end the new timer: only the first attempt, no acknowledge afterwards
    assert mock_appliance.session.send_sync.await_count == 1


async def test_nothing_sent_while_new_timer_runs(
    hass: HomeAssistant,
    mock_appliance: MockAppliance,
    patch_entity_description: None,
) -> None:
    """
    Test nothing is sent when a new timer runs while the event is still Present.

    Acknowledging and rejecting both end the running timer.
    """
    oven = await _setup(hass, mock_appliance)

    await oven.set("local", value=False)
    await oven.set("alarm_clock", 10)
    await oven.set("event", 1)  # Present
    await oven.set("alarm_clock", 0)  # Confirmed, acknowledged. The mock leaves the event Present
    mock_appliance.session.send_sync.assert_awaited_once_with(ACKNOWLEDGE_MESSAGE)
    mock_appliance.session.send_sync.reset_mock()

    await oven.set("alarm_clock", 60)  # A new timer
    await oven.set("local", value=False)

    mock_appliance.session.send_sync.assert_not_awaited()


async def test_not_set_up_without_commands(
    hass: HomeAssistant,
    mock_appliance: MockAppliance,
    patch_entity_description: None,
) -> None:
    """Test nothing is done when the appliance cannot acknowledge events."""
    mock_appliance.commands.pop("BSH.Common.Command.AcknowledgeEvent")
    oven = await _setup(hass, mock_appliance)

    await oven.set("event", 1)  # Present
    await oven.set("alarm_clock", 0)
    await oven.set("local", value=False)
    await hass.async_block_till_done(wait_background_tasks=True)

    mock_appliance.session.send_sync.assert_not_awaited()


async def test_not_set_up_for_hob(
    hass: HomeAssistant,
    mock_appliance: MockAppliance,
    patch_entity_description: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test a hob is left alone: it has to be confirmed on the hob, with a beep."""
    monkeypatch.setitem(mock_appliance.info, "type", "Hob")
    oven = await _setup(hass, mock_appliance)

    await oven.set("event", 1)  # Present
    await oven.set("alarm_clock", 0)  # The hob sets this in the same message as the event
    await oven.set("local", value=False)
    await hass.async_block_till_done(wait_background_tasks=True)

    mock_appliance.session.send_sync.assert_not_awaited()
