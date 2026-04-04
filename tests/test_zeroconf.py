"""Test for config flow zeroconf discovery."""

from __future__ import annotations

from ipaddress import ip_address
from typing import TYPE_CHECKING
from unittest.mock import ANY, Mock
from uuid import uuid4

from custom_components.homeconnect_ws import config_flow
from custom_components.homeconnect_ws.const import (
    CONF_AES_IV,
    CONF_FILE,
    CONF_MANUAL_HOST,
    CONF_PSK,
    DOMAIN,
)
from homeassistant.config_entries import SOURCE_ZEROCONF
from homeassistant.const import CONF_DESCRIPTION, CONF_DEVICE_ID, CONF_HOST, CONF_NAME
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo
from pytest_homeassistant_custom_component.common import MockConfigEntry

from . import MockAppliance
from .const import (
    MOCK_CONFIG_DATA,
    MOCK_TLS_DEVICE_DESCRIPTION,
    MOCK_TLS_DEVICE_ID,
    MOCK_TLS_DEVICE_INFO,
)

if TYPE_CHECKING:
    from unittest.mock import AsyncMock, MagicMock

    import pytest
    from homeassistant.core import HomeAssistant

MOCK_ZEROCONF_DATA = ZeroconfServiceInfo(
    ip_address=ip_address("127.0.0.2"),
    ip_addresses=[ip_address("127.0.0.2")],
    hostname=f"test_brand-test_tls-{MOCK_TLS_DEVICE_ID}.local.",
    name="Test_TLS Test_Brand Test_vib._homeconnect._tcp.local.",
    port=443,
    properties={
        "txtvers": "2",
        "vers": "5.4-3.11.4.1",
        "id": MOCK_TLS_DEVICE_ID,
        "mac": "000000000001",
        "brand": "Test_Brand",
        "type": "Test_TLS",
        "vib": "Test_vib",
        "info": None,
        "tls": "true",
    },
    type="_homeconnect._tcp.local.",
)

UPLOADED_FILE = str(uuid4())


async def test_zeroconf_init(
    hass: HomeAssistant,
    mock_process_profile_file: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
    mock_setup_entry: AsyncMock,
) -> None:
    """Test setup from zeroconf discovery."""
    appliance = MockAppliance(MOCK_TLS_DEVICE_INFO)
    monkeypatch.setattr(config_flow, "HomeAppliance", appliance)

    randbytes = Mock()
    randbytes.return_value = bytes.fromhex("01020304")
    monkeypatch.setattr(config_flow.random, "randbytes", randbytes)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_ZEROCONF}, data=MOCK_ZEROCONF_DATA
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "upload"
    assert not result["errors"]

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_FILE: UPLOADED_FILE,
        },
    )
    assert appliance.description == MOCK_TLS_DEVICE_DESCRIPTION
    assert appliance.host == "127.0.0.2"
    assert appliance.app_name == "Homeassistant"
    assert appliance.app_id == "01020304"
    assert appliance.psk64 == MOCK_TLS_DEVICE_INFO["key"]
    assert appliance.iv64 is None
    assert appliance.connection_callback == ANY

    appliance._connect.assert_awaited_once()
    appliance._close.assert_awaited_once()

    mock_process_profile_file.assert_called_once_with(UPLOADED_FILE)

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Test_Brand Test_TLS"
    assert result["data"][CONF_DESCRIPTION] == {
        "info": MOCK_TLS_DEVICE_INFO,
        "MOCK_TLS_DEVICE_DESCRIPTION": None,
    }
    assert result["data"][CONF_HOST] == "127.0.0.2"
    assert result["data"][CONF_PSK] == MOCK_TLS_DEVICE_INFO["key"]
    assert CONF_AES_IV not in result["data"]
    assert result["data"][CONF_NAME] == "Test_Brand Test_TLS"

    mock_setup_entry.assert_awaited_once()


async def test_zeroconf_duplicate_entry(
    hass: HomeAssistant,
    mock_setup_entry: AsyncMock,
) -> None:
    """Test zeroconf discovered duplicate entry."""
    mock_config = MockConfigEntry(
        domain=DOMAIN,
        data=MOCK_CONFIG_DATA,
        unique_id=MOCK_TLS_DEVICE_ID,
    )
    mock_config.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_ZEROCONF}, data=MOCK_ZEROCONF_DATA
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    mock_setup_entry.assert_not_awaited()


async def test_zeroconf_update_host(
    hass: HomeAssistant,
    mock_setup_entry: AsyncMock,
) -> None:
    """Test updating host from zeroconf discovery."""
    mock_config = MockConfigEntry(
        domain=DOMAIN,
        data=MOCK_CONFIG_DATA,
        unique_id=MOCK_TLS_DEVICE_ID,
    )
    mock_config.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_ZEROCONF}, data=MOCK_ZEROCONF_DATA
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    assert mock_config.data[CONF_HOST] == "127.0.0.2"
    mock_setup_entry.assert_not_awaited()


async def test_zeroconf_update_manual_host(
    hass: HomeAssistant,
    mock_setup_entry: AsyncMock,
) -> None:
    """Test updating host from zeroconf discovery when manual host is set."""
    mock_config = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_DESCRIPTION: "description",
            CONF_HOST: "1.2.3.4",
            CONF_PSK: "PSK_KEY",
            CONF_AES_IV: "AES_IV",
            CONF_DEVICE_ID: "Test_Device_ID",
            CONF_NAME: "Fake_Brand HomeAppliance",
            CONF_MANUAL_HOST: True,
        },
        unique_id=MOCK_TLS_DEVICE_ID,
    )
    mock_config.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_ZEROCONF}, data=MOCK_ZEROCONF_DATA
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    assert mock_config.data[CONF_HOST] == "1.2.3.4"
    mock_setup_entry.assert_not_awaited()


async def test_zeroconf_invalid_discovery_info(
    hass: HomeAssistant,
    mock_setup_entry: AsyncMock,
) -> None:
    """Test zeroconf with invalid_discovery_info."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_ZEROCONF},
        data=ZeroconfServiceInfo(
            ip_address=ip_address("127.0.0.2"),
            ip_addresses=[ip_address("127.0.0.2")],
            hostname=f"test_brand-test_tls-{MOCK_TLS_DEVICE_ID}.local.",
            name="Test_TLS Test_Brand Test_vib._homeconnect._tcp.local.",
            port=443,
            properties={},
            type="_homeconnect._tcp.local.",
        ),
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "invalid_discovery_info"
    mock_setup_entry.assert_not_awaited()
