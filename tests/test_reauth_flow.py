"""Tests for reauthflow."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import ANY, Mock
from uuid import uuid4

from custom_components.homeconnect_ws import config_flow
from custom_components.homeconnect_ws.const import (
    CONF_AES_IV,
    CONF_APPLIANCE_INFO,
    CONF_DESCRIPTION_FILENAME,
    CONF_FEATURE_FILENAME,
    CONF_FILE,
    CONF_PSK,
    DOMAIN,
)
from homeassistant.const import CONF_DESCRIPTION, CONF_DEVICE_ID, CONF_HOST
from homeassistant.data_entry_flow import FlowResultType
from homeconnect_websocket import AuthenticationError, ConnectionFailedError, ParserError
from pytest_homeassistant_custom_component.common import MockConfigEntry

from . import MockAppliance
from .const import MOCK_AES_DEVICE_ID, MOCK_AES_DEVICE_INFO, MOCK_CONFIG_DATA_2
from .const import MOCK_CONFIG_DATA_1 as MOCK_CONFIG_DATA

if TYPE_CHECKING:
    from unittest.mock import AsyncMock, MagicMock

    import pytest
    from homeassistant.core import HomeAssistant

UPLOADED_FILE = str(uuid4())


async def test_reauth_migrates_version_1_entry(
    hass: HomeAssistant,
    mock_process_profile_file: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
    mock_setup_entry: AsyncMock,
    mock_parse_device_description: Mock,
    mock_write_file: MagicMock,
) -> None:
    """Reauth of an entry that stores the description: write the new profile files."""
    appliance = MockAppliance(MOCK_AES_DEVICE_INFO)
    monkeypatch.setattr(config_flow, "HomeAppliance", appliance)
    remove_files = Mock()
    monkeypatch.setattr(config_flow, "remove_profile_files", remove_files)
    mock_process_profile_file.return_value[MOCK_AES_DEVICE_ID]["info"]["key"] = "New_AES_PSK_KEY"

    mock_config = MockConfigEntry(
        domain=DOMAIN, data=MOCK_CONFIG_DATA, unique_id=MOCK_AES_DEVICE_ID, version=1
    )
    mock_config.add_to_hass(hass)

    result = await mock_config.start_reauth_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={CONF_FILE: UPLOADED_FILE}
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert mock_config.version == 2
    assert CONF_DESCRIPTION not in mock_config.data
    assert mock_config.data[CONF_PSK] == "New_AES_PSK_KEY"
    assert mock_config.data[CONF_HOST] == MOCK_CONFIG_DATA[CONF_HOST]
    assert mock_config.data[CONF_APPLIANCE_INFO] == appliance.info
    device_id = mock_config.data[CONF_DEVICE_ID]
    assert mock_config.data[CONF_DESCRIPTION_FILENAME] == f"{device_id}/DeviceDescription.xml"
    mock_write_file.assert_any_call(
        ANY, f"{device_id}/DeviceDescription.xml", b"AES_DeviceDescription"
    )
    mock_write_file.assert_any_call(ANY, f"{device_id}/FeatureMapping.xml", b"AES_FeatureMapping")
    remove_files.assert_not_called()
    mock_setup_entry.assert_awaited_once()


async def test_reauth_version_2_entry_replaces_files(
    hass: HomeAssistant,
    mock_process_profile_file: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
    mock_setup_entry: AsyncMock,
    mock_parse_device_description: Mock,
    mock_write_file: MagicMock,
) -> None:
    """Reauth of an entry with profile files: new files, old files removed."""
    appliance = MockAppliance(MOCK_AES_DEVICE_INFO)
    monkeypatch.setattr(config_flow, "HomeAppliance", appliance)
    remove_files = Mock()
    monkeypatch.setattr(config_flow, "remove_profile_files", remove_files)

    mock_config = MockConfigEntry(
        domain=DOMAIN, data=MOCK_CONFIG_DATA_2, unique_id=MOCK_AES_DEVICE_ID, version=2
    )
    mock_config.add_to_hass(hass)

    result = await mock_config.start_reauth_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={CONF_FILE: UPLOADED_FILE}
    )
    await hass.async_block_till_done()

    assert result["reason"] == "reauth_successful"
    assert mock_config.version == 2
    device_id = mock_config.data[CONF_DEVICE_ID]
    assert mock_config.data[CONF_FEATURE_FILENAME] == f"{device_id}/FeatureMapping.xml"
    assert mock_write_file.call_count == 2
    remove_files.assert_called_once_with(ANY, dict(MOCK_CONFIG_DATA_2))
    mock_setup_entry.assert_awaited_once()


async def test_reauth(
    hass: HomeAssistant,
    mock_process_profile_file: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
    mock_setup_entry: AsyncMock,
    mock_parse_device_description: Mock,
    mock_write_file: MagicMock,
) -> None:
    """Test a reauthentication flow."""
    appliance = MockAppliance(MOCK_AES_DEVICE_INFO)
    monkeypatch.setattr(config_flow, "HomeAppliance", appliance)

    mock_process_profile_file.return_value[MOCK_AES_DEVICE_ID]["info"]["key"] = "New_AES_PSK_KEY"
    mock_process_profile_file.return_value[MOCK_AES_DEVICE_ID]["info"]["iv"] = "New_AES_IV"

    mock_config = MockConfigEntry(
        domain=DOMAIN,
        data=MOCK_CONFIG_DATA,
        unique_id=MOCK_AES_DEVICE_ID,
    )
    mock_config.add_to_hass(hass)

    result = await mock_config.start_reauth_flow(hass)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "upload"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_FILE: UPLOADED_FILE,
        },
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert mock_config.data[CONF_PSK] == "New_AES_PSK_KEY"
    assert mock_config.data[CONF_AES_IV] == "New_AES_IV"

    appliance._connect.assert_awaited_once()
    appliance._close.assert_awaited_once()
    mock_setup_entry.assert_awaited_once()


async def test_reauth_appliance_not_in_profile(
    hass: HomeAssistant,
    mock_process_profile_file: MagicMock,
    mock_setup_entry: AsyncMock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test a reauthentication flow when appliance not in profile."""
    appliance = MockAppliance(MOCK_AES_DEVICE_INFO)
    monkeypatch.setattr(config_flow, "HomeAppliance", appliance)

    mock_config = MockConfigEntry(
        domain=DOMAIN,
        data=MOCK_CONFIG_DATA,
        unique_id="other_id",
    )
    mock_config.add_to_hass(hass)
    result = await mock_config.start_reauth_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_FILE: UPLOADED_FILE,
        },
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "appliance_not_in_profile_file"
    mock_setup_entry.assert_not_awaited()


async def test_reauth_auth_failed_ssl_error(
    hass: HomeAssistant,
    mock_process_profile_file: MagicMock,
    mock_setup_entry: AsyncMock,
    monkeypatch: pytest.MonkeyPatch,
    mock_parse_device_description: Mock,
) -> None:
    """Test a reauthentication flow with ClientConnectorSSLError."""
    appliance = MockAppliance(MOCK_AES_DEVICE_INFO)
    monkeypatch.setattr(config_flow, "HomeAppliance", appliance)

    mock_config = MockConfigEntry(
        domain=DOMAIN,
        data=MOCK_CONFIG_DATA,
        unique_id=MOCK_AES_DEVICE_ID,
    )
    mock_config.add_to_hass(hass)

    appliance._connect.side_effect = AuthenticationError()

    result = await mock_config.start_reauth_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_FILE: UPLOADED_FILE,
        },
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "auth_failed"
    appliance._close.assert_awaited_once()
    mock_setup_entry.assert_not_awaited()


async def test_reauth_connection_failed_timeout(
    hass: HomeAssistant,
    mock_process_profile_file: MagicMock,
    mock_setup_entry: AsyncMock,
    monkeypatch: pytest.MonkeyPatch,
    mock_parse_device_description: Mock,
) -> None:
    """Test a reauthentication flow with TimeoutError."""
    appliance = MockAppliance(MOCK_AES_DEVICE_INFO)
    monkeypatch.setattr(config_flow, "HomeAppliance", appliance)

    mock_config = MockConfigEntry(
        domain=DOMAIN,
        data=MOCK_CONFIG_DATA,
        unique_id=MOCK_AES_DEVICE_ID,
    )
    mock_config.add_to_hass(hass)

    appliance._connect.side_effect = TimeoutError()

    result = await mock_config.start_reauth_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_FILE: UPLOADED_FILE,
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "host"
    assert result["errors"]["base"] == "cannot_connect"

    appliance._close.assert_awaited_once()
    hass.config_entries.flow.async_abort(result["flow_id"])
    mock_setup_entry.assert_not_awaited()


async def test_reauth_connection_failed_connection_error(
    hass: HomeAssistant,
    mock_process_profile_file: MagicMock,
    mock_setup_entry: AsyncMock,
    monkeypatch: pytest.MonkeyPatch,
    mock_parse_device_description: Mock,
) -> None:
    """Test a reauthentication flow with ClientConnectionError."""
    appliance = MockAppliance(MOCK_AES_DEVICE_INFO)
    monkeypatch.setattr(config_flow, "HomeAppliance", appliance)

    mock_config = MockConfigEntry(
        domain=DOMAIN,
        data=MOCK_CONFIG_DATA,
        unique_id=MOCK_AES_DEVICE_ID,
    )
    mock_config.add_to_hass(hass)

    appliance._connect.side_effect = ConnectionFailedError()

    result = await mock_config.start_reauth_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_FILE: UPLOADED_FILE,
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "host"
    assert result["errors"]["base"] == "cannot_connect"

    appliance._close.assert_awaited_once()
    hass.config_entries.flow.async_abort(result["flow_id"])
    mock_setup_entry.assert_not_awaited()


async def test_reauth_invalid_config_parser(
    hass: HomeAssistant,
    mock_process_profile_file: MagicMock,
    mock_setup_entry: AsyncMock,
) -> None:
    """Test a reauthentication flow with error in config parser."""
    mock_config = MockConfigEntry(
        domain=DOMAIN,
        data=MOCK_CONFIG_DATA,
        unique_id=MOCK_AES_DEVICE_ID,
    )
    mock_config.add_to_hass(hass)

    mock_process_profile_file.side_effect = ParserError("Test Error")

    result = await mock_config.start_reauth_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_FILE: UPLOADED_FILE,
        },
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "profile_file_parser_error"
    assert result["description_placeholders"] == {"error": "Test Error"}
    mock_setup_entry.assert_not_awaited()


async def test_reauth_invalid_profile_no_info(
    hass: HomeAssistant,
    mock_process_profile_file: MagicMock,
    mock_setup_entry: AsyncMock,
) -> None:
    """Test a reauthentication flow with no profile info."""
    mock_process_profile_file.return_value[MOCK_AES_DEVICE_ID] = {}

    mock_config = MockConfigEntry(
        domain=DOMAIN,
        data=MOCK_CONFIG_DATA,
        unique_id=MOCK_AES_DEVICE_ID,
    )
    mock_config.add_to_hass(hass)

    result = await mock_config.start_reauth_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_FILE: UPLOADED_FILE,
        },
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "invalid_profile_file"
    mock_setup_entry.assert_not_awaited()


async def test_reauth_invalid_profile_info(
    hass: HomeAssistant,
    mock_process_profile_file: MagicMock,
    mock_setup_entry: AsyncMock,
) -> None:
    """Test a reauthentication flow with invalid info."""
    mock_process_profile_file.return_value[MOCK_AES_DEVICE_ID]["info"].pop("key")

    mock_config = MockConfigEntry(
        domain=DOMAIN,
        data=MOCK_CONFIG_DATA,
        unique_id=MOCK_AES_DEVICE_ID,
    )
    mock_config.add_to_hass(hass)

    result = await mock_config.start_reauth_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_FILE: UPLOADED_FILE,
        },
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "invalid_profile_file"
    mock_setup_entry.assert_not_awaited()
