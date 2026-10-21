"""Tests for date/time entity."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

from homeassistant.components.datetime import (
    ATTR_DATETIME,
    DOMAIN as DATETIME_DOMAIN,
    SERVICE_SET_VALUE,
)
from homeassistant.const import ATTR_ENTITY_ID, ATTR_FRIENDLY_NAME
from homeconnect_websocket.message import Action, Message

from . import setup_config_entry
from .const import CONFIG_ENTRIES

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeconnect_websocket.testutils import MockAppliance


async def test_setup(
    hass: HomeAssistant,
    mock_appliance: MockAppliance,
    patch_entity_description: None,
) -> None:
    """Test setting up date/time entity."""
    assert await setup_config_entry(hass, CONFIG_ENTRIES[0])

    state = hass.states.get("datetime.fake_brand_homeappliance_local_time")
    assert state
    assert state.name == "Fake_brand HomeAppliance Local time"
    assert state.attributes[ATTR_FRIENDLY_NAME] == "Fake_brand HomeAppliance Local time"


async def test_update(
    hass: HomeAssistant,
    mock_appliance: MockAppliance,
    patch_entity_description: None,
) -> None:
    """Test updating date/time entity."""
    entity_id = "datetime.fake_brand_homeappliance_local_time"
    assert await setup_config_entry(hass, CONFIG_ENTRIES[0])

    await mock_appliance.entities["BSH.Common.Setting.LocalTime"].update(
        {"value": "2027-12-15T18:45:30"}
    )
    await hass.async_block_till_done()

    state = hass.states.get(entity_id)
    assert state
    assert state.state == "2027-12-15T18:45:30+00:00"


async def test_set_value(
    hass: HomeAssistant,
    mock_appliance: MockAppliance,
    patch_entity_description: None,
) -> None:
    """Test setting appliance-local date/time."""
    entity_id = "datetime.fake_brand_homeappliance_local_time"
    assert await setup_config_entry(hass, CONFIG_ENTRIES[0])

    await hass.services.async_call(
        DATETIME_DOMAIN,
        SERVICE_SET_VALUE,
        {
            ATTR_ENTITY_ID: entity_id,
            ATTR_DATETIME: datetime(
                2027,
                12,
                15,
                18,
                45,
                30,
                tzinfo=ZoneInfo("UTC"),
            ),
        },
        blocking=True,
    )

    mock_appliance.session.send_sync.assert_awaited_once_with(
        Message(
            resource="/ro/values",
            action=Action.POST,
            data={"uid": 205, "value": "2027-12-15T18:45:30"},
        )
    )
