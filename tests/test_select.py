"""Tests for select entity."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.select import (
    ATTR_OPTION,
    ATTR_OPTIONS,
    SERVICE_SELECT_OPTION,
)
from homeassistant.components.select import DOMAIN as SELECT_DOMAIN
from homeassistant.const import ATTR_ENTITY_ID, ATTR_FRIENDLY_NAME, STATE_UNKNOWN
from homeconnect_websocket.message import Action, Message

from . import setup_config_entry
from .const import MOCK_CONFIG_DATA

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeconnect_websocket.testutils import MockAppliance


async def test_setup(
    hass: HomeAssistant,
    mock_appliance: MockAppliance,  # noqa: ARG001
    patch_entity_description: None,  # noqa: ARG001
) -> None:
    """Test setting up entity."""
    assert await setup_config_entry(hass, MOCK_CONFIG_DATA)

    state = hass.states.get("select.fake_brand_homeappliance_select")
    assert state
    assert state.name == "Fake_brand HomeAppliance Select"
    assert state.attributes[ATTR_FRIENDLY_NAME] == "Fake_brand HomeAppliance Select"
    assert state.attributes[ATTR_OPTIONS] == ["Option1", "Option2", "Option3"]

    state = hass.states.get("select.fake_brand_homeappliance_select_translated")
    assert state
    assert state.name == "Fake_brand HomeAppliance Select.Translated"
    assert state.attributes[ATTR_FRIENDLY_NAME] == "Fake_brand HomeAppliance Select.Translated"
    assert state.attributes[ATTR_OPTIONS] == ["option1", "option2", "option3"]

    state = hass.states.get("select.fake_brand_homeappliance_select_options")
    assert state
    assert state.name == "Fake_brand HomeAppliance Select.Options"
    assert state.attributes[ATTR_FRIENDLY_NAME] == "Fake_brand HomeAppliance Select.Options"
    assert state.attributes[ATTR_OPTIONS] == ["option2"]

    state = hass.states.get("select.fake_brand_homeappliance_selectedprogram")
    assert state
    assert state.name == "Fake_brand HomeAppliance SelectedProgram"
    assert state.attributes[ATTR_FRIENDLY_NAME] == "Fake_brand HomeAppliance SelectedProgram"
    assert state.attributes[ATTR_OPTIONS] == [
        "Named Favorite",
        "favorite_002",
        "test_program_program1",
        "test_program_program2",
        "test_program_program3",
    ]


async def test_update(
    hass: HomeAssistant,
    mock_appliance: MockAppliance,
    patch_entity_description: None,  # noqa: ARG001
) -> None:
    """Test updating entity."""
    entity_id = "select.fake_brand_homeappliance_select"
    entity_id_translated = "select.fake_brand_homeappliance_select_translated"
    entity_id_options = "select.fake_brand_homeappliance_select_options"
    assert await setup_config_entry(hass, MOCK_CONFIG_DATA)

    await mock_appliance.entities["Test.Select"].update({"value": 0})
    await hass.async_block_till_done()

    state = hass.states.get(entity_id)
    assert state.state == "Option1"

    state = hass.states.get(entity_id_translated)
    assert state.state == "option1"

    state = hass.states.get(entity_id_options)
    assert state.state == STATE_UNKNOWN

    await mock_appliance.entities["Test.Select"].update({"value": 1})
    await hass.async_block_till_done()

    state = hass.states.get(entity_id)
    assert state.state == "Option2"

    state = hass.states.get(entity_id_translated)
    assert state.state == "option2"

    state = hass.states.get(entity_id_options)
    assert state.state == "option2"


async def test_select(
    hass: HomeAssistant,
    mock_appliance: MockAppliance,
    patch_entity_description: None,  # noqa: ARG001
) -> None:
    """Test selecting an option."""
    entity_id = "select.fake_brand_homeappliance_select"
    entity_id_translated = "select.fake_brand_homeappliance_select_translated"
    entity_id_options = "select.fake_brand_homeappliance_select_options"
    assert await setup_config_entry(hass, MOCK_CONFIG_DATA)

    await hass.services.async_call(
        SELECT_DOMAIN,
        SERVICE_SELECT_OPTION,
        {
            ATTR_ENTITY_ID: entity_id,
            ATTR_OPTION: "Option3",
        },
        blocking=True,
    )

    mock_appliance.session.send_sync.assert_awaited_once_with(
        Message(
            resource="/ro/values",
            action=Action.POST,
            data={"uid": 203, "value": 2},
        )
    )
    mock_appliance.session.send_sync.reset_mock()

    await hass.services.async_call(
        SELECT_DOMAIN,
        SERVICE_SELECT_OPTION,
        {
            ATTR_ENTITY_ID: entity_id_translated,
            ATTR_OPTION: "option3",
        },
        blocking=True,
    )

    mock_appliance.session.send_sync.assert_awaited_once_with(
        Message(
            resource="/ro/values",
            action=Action.POST,
            data={"uid": 203, "value": 2},
        )
    )
    mock_appliance.session.send_sync.reset_mock()

    await hass.services.async_call(
        SELECT_DOMAIN,
        SERVICE_SELECT_OPTION,
        {
            ATTR_ENTITY_ID: entity_id_options,
            ATTR_OPTION: "option2",
        },
        blocking=True,
    )

    mock_appliance.session.send_sync.assert_awaited_once_with(
        Message(
            resource="/ro/values",
            action=Action.POST,
            data={"uid": 203, "value": 1},
        )
    )


async def test_update_program(
    hass: HomeAssistant,
    mock_appliance: MockAppliance,
    patch_entity_description: None,  # noqa: ARG001
) -> None:
    """Test updating program select entity."""
    entity_id = "select.fake_brand_homeappliance_selectedprogram"
    assert await setup_config_entry(hass, MOCK_CONFIG_DATA)
    await mock_appliance.entities["Test.SelectedProgram"].update({"value": 500})
    await hass.async_block_till_done()

    state = hass.states.get(entity_id)
    assert state.state == "test_program_program1"

    await mock_appliance.entities["Test.SelectedProgram"].update({"value": 502})
    await hass.async_block_till_done()

    state = hass.states.get(entity_id)
    assert state.state == "Named Favorite"


async def test_select_program(
    hass: HomeAssistant,
    mock_appliance: MockAppliance,
    patch_entity_description: None,  # noqa: ARG001
) -> None:
    """Test selecting an program."""
    entity_id = "select.fake_brand_homeappliance_selectedprogram"
    assert await setup_config_entry(hass, MOCK_CONFIG_DATA)

    await hass.services.async_call(
        SELECT_DOMAIN,
        SERVICE_SELECT_OPTION,
        {
            ATTR_ENTITY_ID: entity_id,
            ATTR_OPTION: "test_program_program2",
        },
        blocking=True,
    )

    mock_appliance.session.send_sync.assert_awaited_once_with(
        Message(
            resource="/ro/selectedProgram",
            action=Action.POST,
            data={
                "program": 501,
                "options": [],
            },
        )
    )

    mock_appliance.session.send_sync.reset_mock()

    await hass.services.async_call(
        SELECT_DOMAIN,
        SERVICE_SELECT_OPTION,
        {
            ATTR_ENTITY_ID: entity_id,
            ATTR_OPTION: "test_program_program3",
        },
        blocking=True,
    )

    mock_appliance.session.send_sync.assert_awaited_once_with(
        Message(
            resource="/ro/activeProgram",
            action=Action.POST,
            data={
                "program": 502,
                "options": [{"uid": 401, "value": None}, {"uid": 402, "value": None}],
            },
        )
    )
