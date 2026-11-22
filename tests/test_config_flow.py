"""Tests for config flow."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import ANY, AsyncMock, MagicMock, Mock
from uuid import uuid4

from custom_components.homeconnect_ws import config_flow
from custom_components.homeconnect_ws.const import (
    CONF_AES_IV,
    CONF_APPLIANCE_INFO,
    CONF_DESCRIPTION_FILENAME,
    CONF_FEATURE_FILENAME,
    CONF_FILE,
    CONF_MANUAL_HOST,
    CONF_PSK,
    DOMAIN,
)
from homeassistant.config_entries import SOURCE_IGNORE, SOURCE_USER
from homeassistant.const import CONF_DEVICE, CONF_DEVICE_ID, CONF_HOST, CONF_NAME
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers.selector import SelectOptionDict
from homeconnect_websocket import AuthenticationError, ConnectionFailedError, ParserError
from pytest_homeassistant.common import MockConfigEntry

from .const import (
    MOCK_AES_DEVICE_ID,
    MOCK_AES_DEVICE_INFO,
    MOCK_APPLIANCE_INFO,
    MOCK_TLS_DEVICE_ID,
    MOCK_TLS_DEVICE_ID_2,
    MOCK_TLS_DEVICE_INFO,
)
from .const import MOCK_CONFIG_DATA_1 as MOCK_CONFIG_DATA

if TYPE_CHECKING:
    import pytest
    from homeassistant.core import HomeAssistant
    from homeconnect_websocket.testutils import MockAppliance

UPLOADED_FILE = str(uuid4())


async def test_user_init(
    hass: HomeAssistant,
    mock_process_profile_file: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
    mock_setup_entry: AsyncMock,
    patch_create_appliance: Mock,
) -> None:
    """Test config flow init."""
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "upload"
    assert not result["errors"]

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_FILE: UPLOADED_FILE,
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "device_select"
    assert not result["errors"]
    assert result["data_schema"].schema.get("device").config["options"] == [
        SelectOptionDict(
            value=MOCK_TLS_DEVICE_ID,
            label="Test_Brand Test_TLS (Test_vib)",
        ),
        SelectOptionDict(
            value=MOCK_AES_DEVICE_ID,
            label="Test_Brand Test_AES (Test_vib)",
        ),
        SelectOptionDict(
            value=MOCK_TLS_DEVICE_ID_2,
            label="Test_Brand Test_TLS (Test_vib)",
        ),
    ]

    hass.config_entries.flow.async_abort(result["flow_id"])
    mock_setup_entry.assert_not_awaited()


async def test_user_tls(
    hass: HomeAssistant,
    mock_process_profile_file: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
    mock_setup_entry: AsyncMock,
    mock_write_file: MagicMock,
    mock_parse_device_description: Mock,
    patch_create_appliance: Mock,
) -> None:
    """Test config flow compleate for TLS Appliance."""
    randbytes = Mock()
    randbytes.return_value = bytes.fromhex("01020304")
    monkeypatch.setattr(config_flow.random, "randbytes", randbytes)

    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "upload"
    assert not result["errors"]

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_FILE: UPLOADED_FILE,
        },
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_DEVICE: MOCK_TLS_DEVICE_ID,
        },
    )

    patch_create_appliance.assert_called_once_with(
        description=mock_parse_device_description.return_value,
        host="Test_Brand-Test_TLS-010203040506070809",
        app_id="01020304",
        psk64=MOCK_TLS_DEVICE_INFO["key"],
        iv64=None,
        connection_callback=ANY,
    )

    appliance: MockAppliance = patch_create_appliance.return_value
    appliance.session._connect.assert_awaited_once()
    appliance.session._close.assert_awaited_once()
    mock_parse_device_description.assert_called_once_with(
        b"TLS_DeviceDescription",
        b"TLS_FeatureMapping",
    )
    mock_process_profile_file.assert_called_once_with(ANY, UPLOADED_FILE)

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Test_Brand Test_TLS"
    assert result["data"][CONF_DESCRIPTION_FILENAME] == "01020304/DeviceDescription.xml"
    assert result["data"][CONF_FEATURE_FILENAME] == "01020304/FeatureMapping.xml"
    assert result["data"][CONF_HOST] == "Test_Brand-Test_TLS-010203040506070809"
    assert result["data"][CONF_PSK] == MOCK_TLS_DEVICE_INFO["key"]
    assert CONF_AES_IV not in result["data"]
    assert result["data"][CONF_NAME] == "Test_Brand Test_TLS"
    assert result["data"][CONF_DEVICE_ID] == "01020304"
    assert result["data"][CONF_APPLIANCE_INFO] == MOCK_APPLIANCE_INFO

    mock_write_file.assert_any_call(
        ANY,
        "01020304/DeviceDescription.xml",
        b"TLS_DeviceDescription",
    )

    mock_write_file.assert_any_call(
        ANY,
        "01020304/FeatureMapping.xml",
        b"TLS_FeatureMapping",
    )

    mock_setup_entry.assert_awaited_once()


async def test_user_aes(
    hass: HomeAssistant,
    mock_process_profile_file: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
    mock_setup_entry: AsyncMock,
    mock_write_file: MagicMock,
    mock_parse_device_description: Mock,
    patch_create_appliance: Mock,
) -> None:
    """Test config flow compleate for AES Appliance."""
    randbytes = Mock()
    randbytes.return_value = bytes.fromhex("01020304")
    monkeypatch.setattr(config_flow.random, "randbytes", randbytes)

    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "upload"
    assert not result["errors"]

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_FILE: UPLOADED_FILE,
        },
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_DEVICE: MOCK_AES_DEVICE_ID,
        },
    )

    patch_create_appliance.assert_called_once_with(
        description=mock_parse_device_description.return_value,
        host=MOCK_AES_DEVICE_ID,
        app_id="01020304",
        psk64=MOCK_AES_DEVICE_INFO["key"],
        iv64=MOCK_AES_DEVICE_INFO["iv"],
        connection_callback=ANY,
    )

    appliance: MockAppliance = patch_create_appliance.return_value
    appliance.session._connect.assert_awaited_once()
    appliance.session._close.assert_awaited_once()
    mock_parse_device_description.assert_called_once_with(
        b"AES_DeviceDescription",
        b"AES_FeatureMapping",
    )
    mock_process_profile_file.assert_called_once_with(ANY, UPLOADED_FILE)

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Test_Brand Test_AES"
    assert result["data"][CONF_DESCRIPTION_FILENAME] == "01020304/DeviceDescription.xml"
    assert result["data"][CONF_FEATURE_FILENAME] == "01020304/FeatureMapping.xml"
    assert result["data"][CONF_HOST] == "101112131415161718"
    assert result["data"][CONF_PSK] == MOCK_AES_DEVICE_INFO["key"]
    assert result["data"][CONF_AES_IV] == MOCK_AES_DEVICE_INFO["iv"]
    assert result["data"][CONF_NAME] == "Test_Brand Test_AES"
    assert result["data"][CONF_DEVICE_ID] == "01020304"
    assert result["data"][CONF_APPLIANCE_INFO] == MOCK_APPLIANCE_INFO

    mock_write_file.assert_any_call(
        ANY,
        "01020304/DeviceDescription.xml",
        b"AES_DeviceDescription",
    )

    mock_write_file.assert_any_call(
        ANY,
        "01020304/FeatureMapping.xml",
        b"AES_FeatureMapping",
    )

    mock_setup_entry.assert_awaited_once()


async def test_user_select_device(
    hass: HomeAssistant,
    mock_process_profile_file: MagicMock,
) -> None:
    """Test select device."""
    mock_config = MockConfigEntry(
        domain=DOMAIN,
        data=MOCK_CONFIG_DATA,
        unique_id=MOCK_TLS_DEVICE_ID,
    )
    mock_config.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "upload"
    assert not result["errors"]

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_FILE: UPLOADED_FILE,
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "device_select"
    assert not result["errors"]
    assert result["data_schema"].schema.get("device").config["options"] == [
        SelectOptionDict(
            value=MOCK_AES_DEVICE_ID,
            label="Test_Brand Test_AES (Test_vib)",
        ),
        SelectOptionDict(
            value=MOCK_TLS_DEVICE_ID_2,
            label="Test_Brand Test_TLS (Test_vib)",
        ),
    ]
    hass.config_entries.flow.async_abort(result["flow_id"])


async def test_user_select_device_one(
    hass: HomeAssistant,
    mock_process_profile_file: MagicMock,
    mock_setup_entry: AsyncMock,
    monkeypatch: pytest.MonkeyPatch,
    mock_write_file: MagicMock,
    mock_parse_device_description: Mock,
    patch_create_appliance: Mock,
) -> None:
    """Test select device when only one device left to setup."""
    randbytes = Mock()
    randbytes.return_value = bytes.fromhex("01020304")
    monkeypatch.setattr(config_flow.random, "randbytes", randbytes)

    mock_config = MockConfigEntry(
        domain=DOMAIN,
        data=MOCK_CONFIG_DATA,
        unique_id=MOCK_TLS_DEVICE_ID,
    )
    mock_config.add_to_hass(hass)
    mock_config = MockConfigEntry(
        domain=DOMAIN,
        data=MOCK_CONFIG_DATA,
        unique_id=MOCK_TLS_DEVICE_ID_2,
    )
    mock_config.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "upload"
    assert not result["errors"]

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_FILE: UPLOADED_FILE,
        },
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Test_Brand Test_AES"
    assert result["data"][CONF_DESCRIPTION_FILENAME] == "01020304/DeviceDescription.xml"
    assert result["data"][CONF_FEATURE_FILENAME] == "01020304/FeatureMapping.xml"
    assert result["data"][CONF_HOST] == "101112131415161718"
    assert result["data"][CONF_PSK] == MOCK_AES_DEVICE_INFO["key"]
    assert result["data"][CONF_AES_IV] == MOCK_AES_DEVICE_INFO["iv"]
    assert result["data"][CONF_NAME] == "Test_Brand Test_AES"
    assert result["data"][CONF_DEVICE_ID] == "01020304"
    assert result["data"][CONF_APPLIANCE_INFO] == MOCK_APPLIANCE_INFO

    mock_write_file.assert_any_call(
        ANY,
        "01020304/DeviceDescription.xml",
        b"AES_DeviceDescription",
    )

    mock_write_file.assert_any_call(
        ANY,
        "01020304/FeatureMapping.xml",
        b"AES_FeatureMapping",
    )


async def test_user_select_device_ignore(
    hass: HomeAssistant,
    mock_process_profile_file: MagicMock,
) -> None:
    """Test select device when one discovered device was ignored."""
    mock_config = MockConfigEntry(
        domain=DOMAIN,
        data=MOCK_CONFIG_DATA,
        unique_id=MOCK_TLS_DEVICE_ID,
        source=SOURCE_IGNORE,
    )
    mock_config.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "upload"
    assert not result["errors"]

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_FILE: UPLOADED_FILE,
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "device_select"
    assert not result["errors"]
    assert result["data_schema"].schema.get("device").config["options"] == [
        SelectOptionDict(
            value=MOCK_TLS_DEVICE_ID,
            label="Test_Brand Test_TLS (Test_vib)",
        ),
        SelectOptionDict(
            value=MOCK_AES_DEVICE_ID,
            label="Test_Brand Test_AES (Test_vib)",
        ),
        SelectOptionDict(
            value=MOCK_TLS_DEVICE_ID_2,
            label="Test_Brand Test_TLS (Test_vib)",
        ),
    ]
    hass.config_entries.flow.async_abort(result["flow_id"])


async def test_user_set_host(
    hass: HomeAssistant,
    mock_process_profile_file: MagicMock,
    mock_setup_entry: AsyncMock,
    monkeypatch: pytest.MonkeyPatch,
    mock_write_file: MagicMock,
    mock_parse_device_description: Mock,
    patch_create_appliance: Mock,
) -> None:
    """Test set host."""
    appliance: MockAppliance = patch_create_appliance.return_value
    appliance.session._connect.side_effect = ConnectionFailedError()

    randbytes = Mock()
    randbytes.return_value = bytes.fromhex("01020304")
    monkeypatch.setattr(config_flow.random, "randbytes", randbytes)

    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_FILE: UPLOADED_FILE,
        },
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_DEVICE: MOCK_TLS_DEVICE_ID,
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "host"
    assert result["errors"]["base"] == "cannot_connect"

    assert (
        patch_create_appliance.call_args.kwargs[CONF_HOST]
        == "Test_Brand-Test_TLS-010203040506070809"
    )

    appliance.session._connect.assert_awaited_once()
    appliance.session._close.assert_awaited_once()

    appliance.session._connect.reset_mock()
    appliance.session._close.reset_mock()

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_HOST: "1.2.3.4",
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "host"
    assert result["errors"]["base"] == "cannot_connect"

    assert patch_create_appliance.call_args.kwargs[CONF_HOST] == "1.2.3.4"

    appliance.session._connect.assert_awaited_once()
    appliance.session._close.assert_awaited_once()

    appliance.session._connect.reset_mock(side_effect=True)
    appliance.session._close.reset_mock()

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_HOST: "5.6.7.8",
        },
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_HOST] == "5.6.7.8"
    assert result["data"][CONF_MANUAL_HOST] is True

    assert patch_create_appliance.call_args.kwargs[CONF_HOST] == "5.6.7.8"

    appliance.session._connect.assert_awaited_once()
    appliance.session._close.assert_awaited_once()

    mock_write_file.assert_any_call(
        ANY,
        "01020304/DeviceDescription.xml",
        b"TLS_DeviceDescription",
    )

    mock_write_file.assert_any_call(
        ANY,
        "01020304/FeatureMapping.xml",
        b"TLS_FeatureMapping",
    )

    mock_setup_entry.assert_awaited_once()


async def test_user_auth_failed_ssl_error(
    hass: HomeAssistant,
    mock_process_profile_file: MagicMock,
    mock_setup_entry: AsyncMock,
    monkeypatch: pytest.MonkeyPatch,
    mock_parse_device_description: Mock,
    patch_create_appliance: Mock,
) -> None:
    """Test a config flow with ClientConnectorSSLError."""
    appliance: MockAppliance = patch_create_appliance.return_value
    appliance.session._connect.side_effect = AuthenticationError()

    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_FILE: UPLOADED_FILE,
        },
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_DEVICE: MOCK_TLS_DEVICE_ID,
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "host"
    assert result["errors"]["base"] == "cannot_connect"

    appliance.session._close.assert_awaited_once()
    hass.config_entries.flow.async_abort(result["flow_id"])
    mock_setup_entry.assert_not_awaited()


async def test_user_connection_failed_timeout(
    hass: HomeAssistant,
    mock_process_profile_file: MagicMock,
    mock_setup_entry: AsyncMock,
    monkeypatch: pytest.MonkeyPatch,
    mock_parse_device_description: Mock,
    patch_create_appliance: Mock,
) -> None:
    """Test a config flow with TimeoutError."""
    appliance: MockAppliance = patch_create_appliance.return_value
    appliance.session._connect.side_effect = TimeoutError()

    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_FILE: UPLOADED_FILE,
        },
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_DEVICE: MOCK_TLS_DEVICE_ID,
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "host"
    assert result["errors"]["base"] == "cannot_connect"

    appliance.session._close.assert_awaited_once()
    hass.config_entries.flow.async_abort(result["flow_id"])
    mock_setup_entry.assert_not_awaited()


async def test_user_connection_failed_connection_error(
    hass: HomeAssistant,
    mock_process_profile_file: MagicMock,
    mock_setup_entry: AsyncMock,
    monkeypatch: pytest.MonkeyPatch,
    mock_parse_device_description: Mock,
    patch_create_appliance: Mock,
) -> None:
    """Test a config flow with ClientConnectionError."""
    appliance: MockAppliance = patch_create_appliance.return_value
    appliance.session._connect.side_effect = ConnectionFailedError()

    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_FILE: UPLOADED_FILE,
        },
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_DEVICE: MOCK_TLS_DEVICE_ID,
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "host"
    assert result["errors"]["base"] == "cannot_connect"

    appliance.session._close.assert_awaited_once()
    hass.config_entries.flow.async_abort(result["flow_id"])
    mock_setup_entry.assert_not_awaited()


async def test_user_invalid_config_parser(
    hass: HomeAssistant,
    mock_process_profile_file: MagicMock,
    mock_setup_entry: AsyncMock,
) -> None:
    """Test a config flow with error in config parser."""
    mock_process_profile_file.side_effect = ParserError("Test Error")

    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
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


async def test_user_invalid_profile_no_info(
    hass: HomeAssistant,
    mock_process_profile_file: MagicMock,
    mock_setup_entry: AsyncMock,
) -> None:
    """Test a reauthentication flow with no profile info."""
    mock_process_profile_file.return_value[MOCK_AES_DEVICE_ID] = {}

    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_FILE: UPLOADED_FILE,
        },
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "invalid_profile_file"
    mock_setup_entry.assert_not_awaited()

    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_FILE: UPLOADED_FILE,
        },
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "invalid_profile_file"
    mock_setup_entry.assert_not_awaited()


async def test_user_invalid_profile_info(
    hass: HomeAssistant,
    mock_process_profile_file: MagicMock,
    mock_setup_entry: AsyncMock,
) -> None:
    """Test a reauthentication flow with invalid info."""
    mock_process_profile_file.return_value[MOCK_AES_DEVICE_ID]["info"].pop("key")

    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_FILE: UPLOADED_FILE,
        },
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_DEVICE: MOCK_AES_DEVICE_ID,
        },
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "invalid_profile_file"
    mock_setup_entry.assert_not_awaited()


async def test_user_select_all_setup(
    hass: HomeAssistant,
    mock_process_profile_file: MagicMock,
    mock_setup_entry: AsyncMock,
) -> None:
    """Test a config flow with all devices setup."""
    mock_config = MockConfigEntry(
        domain=DOMAIN,
        data=MOCK_CONFIG_DATA,
        unique_id=MOCK_TLS_DEVICE_ID,
    )
    mock_config.add_to_hass(hass)
    mock_config = MockConfigEntry(
        domain=DOMAIN,
        data=MOCK_CONFIG_DATA,
        unique_id=MOCK_TLS_DEVICE_ID_2,
    )
    mock_config.add_to_hass(hass)
    mock_config = MockConfigEntry(
        domain=DOMAIN,
        data=MOCK_CONFIG_DATA,
        unique_id=MOCK_AES_DEVICE_ID,
    )
    mock_config.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_FILE: UPLOADED_FILE,
        },
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "all_setup"
    mock_setup_entry.assert_not_awaited()


async def test_process_profile(
    hass: HomeAssistant,
    mock_process_uploaded_file: MagicMock,
) -> None:
    """Test processing profile file."""
    result = config_flow.process_profile_file(hass, UPLOADED_FILE)

    assert result == {
        MOCK_TLS_DEVICE_ID: config_flow.ProfileFileEntry(
            info=MOCK_TLS_DEVICE_INFO,
            device_description=b"TLS_DeviceDescription",
            feature_mapping=b"TLS_FeatureMapping",
        ),
        MOCK_AES_DEVICE_ID: config_flow.ProfileFileEntry(
            info=MOCK_AES_DEVICE_INFO,
            device_description=b"AES_DeviceDescription",
            feature_mapping=b"AES_FeatureMapping",
        ),
    }

    mock_process_uploaded_file.assert_called_with(hass, UPLOADED_FILE)
