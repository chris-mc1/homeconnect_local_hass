"""Test diagnostics."""

from __future__ import annotations

import base64
import zlib
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import Mock

from custom_components import homeconnect_ws
from custom_components.homeconnect_ws import diagnostics
from custom_components.homeconnect_ws.const import (
    CONF_AES_IV,
    CONF_APPLIANCE_INFO,
    CONF_DESCRIPTION_FILENAME,
    CONF_FEATURE_FILENAME,
    CONF_PSK,
    DOMAIN,
)
from custom_components.homeconnect_ws.diagnostics import compress_description
from homeassistant.components.diagnostics import REDACTED
from homeassistant.const import (
    CONF_DESCRIPTION,
    CONF_DEVICE_ID,
    CONF_HOST,
    CONF_NAME,
)
from pytest_homeassistant.common import ANY, MockConfigEntry
from pytest_homeassistant.components.diagnostics import (
    get_diagnostics_for_config_entry,
)

from . import setup_config_entry
from .const import CONFIG_ENTRIES, DEVICE_DESCRIPTION, REDACTED_APPLIANCE_INFO

if TYPE_CHECKING:
    import pytest
    from homeassistant.core import HomeAssistant
    from homeconnect_websocket.testutils import MockAppliance
    from pytest_homeassistant.typing import ClientSessionGenerator


async def test_entry_diagnostics_v1(
    hass: HomeAssistant,
    hass_client: ClientSessionGenerator,
    mock_appliance: MockAppliance,
    patch_entity_description: None,
) -> None:
    """Test config entry diagnostics."""
    config_entry = await setup_config_entry(hass, CONFIG_ENTRIES[0])
    diagnostics = await get_diagnostics_for_config_entry(hass, hass_client, config_entry)
    assert diagnostics == {
        "entry_data": {
            CONF_DESCRIPTION: ANY,
            CONF_HOST: "1.2.3.4",
            CONF_PSK: REDACTED,
            CONF_AES_IV: REDACTED,
            CONF_DEVICE_ID: REDACTED,
            CONF_NAME: "Fake_Brand HomeAppliance",
        },
        "appliance_state": ANY,
    }
    assert diagnostics["entry_data"][CONF_DESCRIPTION]["info"] == REDACTED_APPLIANCE_INFO


async def test_entry_diagnostics_v2(
    hass: HomeAssistant,
    hass_client: ClientSessionGenerator,
    monkeypatch: pytest.MonkeyPatch,
    mock_appliance: MockAppliance,
    patch_entity_description: None,
) -> None:
    """Test config entry diagnostics."""
    compress_description_mock = Mock(
        return_value={
            "device_description_64": "compress_device_description",
            "feature_mapping_64": "compress_feature_mapping",
        }
    )
    monkeypatch.setattr(diagnostics, "compress_description", compress_description_mock)
    load_description_mock = Mock(return_value=DEVICE_DESCRIPTION)
    monkeypatch.setattr(homeconnect_ws, "load_description", load_description_mock)

    config_entry = await setup_config_entry(hass, CONFIG_ENTRIES[1])
    _diagnostics = await get_diagnostics_for_config_entry(hass, hass_client, config_entry)
    assert _diagnostics == {
        "entry_data": {
            CONF_HOST: "1.2.3.4",
            CONF_PSK: REDACTED,
            CONF_AES_IV: REDACTED,
            CONF_DEVICE_ID: REDACTED,
            CONF_NAME: "Fake_Brand HomeAppliance",
            CONF_DESCRIPTION_FILENAME: "Test_Device_ID/FeatureMapping.xml",
            CONF_FEATURE_FILENAME: "Test_Device_ID/DeviceDescription.xml",
            CONF_APPLIANCE_INFO: REDACTED_APPLIANCE_INFO,
        },
        "appliance_state": ANY,
        "device_description_64": "compress_device_description",
        "feature_mapping_64": "compress_feature_mapping",
    }
    compress_description_mock.assert_called_once_with(ANY, config_entry)


def test_compress_description() -> None:
    """Test compress_description."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_DESCRIPTION_FILENAME: "DeviceDescription.xml",
            CONF_FEATURE_FILENAME: "FeatureMapping.xml",
        },
        version=2,
    )
    storage_dir = Path.cwd() / "tests/test_files"
    description = compress_description(storage_dir, config_entry)

    assert type(description["device_description_64"]) is str
    assert type(description["feature_mapping_64"]) is str

    device_description_bin = base64.decodebytes(description["device_description_64"].encode())
    feature_mapping_bin = base64.decodebytes(description["feature_mapping_64"].encode())

    device_description = zlib.decompress(device_description_bin)
    feature_mapping = zlib.decompress(feature_mapping_bin)

    assert device_description == b"device_description"
    assert feature_mapping == b"feature_mapping"
