"""Tests for reauthflow."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import ANY
from uuid import uuid4

import pytest
from custom_components.homeconnect_ws.const import (
    CONF_AES_IV,
    CONF_APPLIANCE_INFO,
    CONF_DESCRIPTION_FILENAME,
    CONF_FEATURE_FILENAME,
    CONF_FILE,
    CONF_PSK,
    DOMAIN,
)
from homeassistant.const import CONF_DESCRIPTION, CONF_DEVICE_ID, CONF_HOST, CONF_NAME
from homeassistant.data_entry_flow import FlowResultType
from homeconnect_websocket import AuthenticationError, ConnectionFailedError, ParserError
from pytest_homeassistant.common import MockConfigEntry

from .const import (
    DEVICE_DESCRIPTION,
    MOCK_AES_DEVICE_ID,
    MOCK_CONFIG_DATA_1,
    MOCK_CONFIG_DATA_2,
)

if TYPE_CHECKING:
    from unittest.mock import AsyncMock, MagicMock, Mock

    from homeassistant.core import HomeAssistant
    from homeconnect_websocket.testutils import MockAppliance

UPLOADED_FILE = str(uuid4())


@pytest.mark.parametrize(
    ("config_entry"),
    [
        MockConfigEntry(
            domain=DOMAIN,
            data=MOCK_CONFIG_DATA_1,
            unique_id=MOCK_AES_DEVICE_ID,
            version=1,
        ),
        MockConfigEntry(
            domain=DOMAIN,
            data=MOCK_CONFIG_DATA_2,
            unique_id=MOCK_AES_DEVICE_ID,
            version=2,
        ),
    ],
)
async def test_reauth(
    config_entry: MockConfigEntry,
    hass: HomeAssistant,
    mock_process_profile_file: MagicMock,
    mock_setup_entry: AsyncMock,
    mock_write_file: MagicMock,
    mock_parse_device_description: Mock,
    patch_create_appliance: Mock,
) -> None:
    """Test a reauthentication flow."""
    mock_process_profile_file.return_value[MOCK_AES_DEVICE_ID]["info"]["key"] = "New_AES_PSK_KEY"
    mock_process_profile_file.return_value[MOCK_AES_DEVICE_ID]["info"]["iv"] = "New_AES_IV"

    config_entry.add_to_hass(hass)

    result = await config_entry.start_reauth_flow(hass)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "upload"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_FILE: UPLOADED_FILE,
        },
    )

    patch_create_appliance.assert_called_once_with(
        description=DEVICE_DESCRIPTION,
        host="1.2.3.4",
        app_id="Test_Device_ID",
        psk64="New_AES_PSK_KEY",
        iv64="New_AES_IV",
        connection_callback=ANY,
    )

    appliance: MockAppliance = patch_create_appliance.return_value
    appliance.session._connect.assert_awaited_once()
    appliance.session._close.assert_awaited_once()

    mock_process_profile_file.assert_called_once_with(ANY, UPLOADED_FILE)

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert config_entry.data[CONF_PSK] == "New_AES_PSK_KEY"
    assert config_entry.data[CONF_AES_IV] == "New_AES_IV"
    assert config_entry.data[CONF_HOST] == "1.2.3.4"
    assert config_entry.data[CONF_DEVICE_ID] == "Test_Device_ID"
    assert config_entry.data[CONF_NAME] == "Fake_Brand HomeAppliance"
    if config_entry.version == 1:
        assert config_entry.data[CONF_DESCRIPTION] == DEVICE_DESCRIPTION
    else:
        assert (
            config_entry.data[CONF_DESCRIPTION_FILENAME] == "Test_Device_ID/DeviceDescription.xml"
        )
        assert config_entry.data[CONF_FEATURE_FILENAME] == "Test_Device_ID/FeatureMapping.xml"
        assert config_entry.data[CONF_APPLIANCE_INFO] == DEVICE_DESCRIPTION["info"]

    mock_setup_entry.assert_awaited_once()


async def test_reauth_appliance_not_in_profile(
    hass: HomeAssistant,
    mock_process_profile_file: MagicMock,
    mock_setup_entry: AsyncMock,
    monkeypatch: pytest.MonkeyPatch,
    patch_create_appliance: MockAppliance,
) -> None:
    """Test a reauthentication flow when appliance not in profile."""
    mock_config = MockConfigEntry(
        domain=DOMAIN,
        data=MOCK_CONFIG_DATA_1,
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
    mock_appliance: MockAppliance,
) -> None:
    """Test a reauthentication flow with ClientConnectorSSLError."""
    mock_config = MockConfigEntry(
        domain=DOMAIN,
        data=MOCK_CONFIG_DATA_1,
        unique_id=MOCK_AES_DEVICE_ID,
    )
    mock_config.add_to_hass(hass)

    mock_appliance.session._connect.side_effect = AuthenticationError()

    result = await mock_config.start_reauth_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_FILE: UPLOADED_FILE,
        },
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "auth_failed"
    mock_appliance.session._close.assert_awaited_once()
    mock_setup_entry.assert_not_awaited()


async def test_reauth_connection_failed_timeout(
    hass: HomeAssistant,
    mock_process_profile_file: MagicMock,
    mock_setup_entry: AsyncMock,
    monkeypatch: pytest.MonkeyPatch,
    mock_parse_device_description: Mock,
    mock_appliance: MockAppliance,
) -> None:
    """Test a reauthentication flow with TimeoutError."""
    mock_config = MockConfigEntry(
        domain=DOMAIN,
        data=MOCK_CONFIG_DATA_1,
        unique_id=MOCK_AES_DEVICE_ID,
    )
    mock_config.add_to_hass(hass)

    mock_appliance.session._connect.side_effect = TimeoutError()

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

    mock_appliance.session._close.assert_awaited_once()
    hass.config_entries.flow.async_abort(result["flow_id"])
    mock_setup_entry.assert_not_awaited()


async def test_reauth_connection_failed_connection_error(
    hass: HomeAssistant,
    mock_process_profile_file: MagicMock,
    mock_setup_entry: AsyncMock,
    monkeypatch: pytest.MonkeyPatch,
    mock_parse_device_description: Mock,
    mock_appliance: MockAppliance,
) -> None:
    """Test a reauthentication flow with ClientConnectionError."""
    mock_config = MockConfigEntry(
        domain=DOMAIN,
        data=MOCK_CONFIG_DATA_1,
        unique_id=MOCK_AES_DEVICE_ID,
    )
    mock_config.add_to_hass(hass)

    mock_appliance.session._connect.side_effect = ConnectionFailedError()

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

    mock_appliance.session._close.assert_awaited_once()
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
        data=MOCK_CONFIG_DATA_1,
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
        data=MOCK_CONFIG_DATA_1,
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
        data=MOCK_CONFIG_DATA_1,
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
