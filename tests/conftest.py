"""Fixtures for testing."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from zipfile import ZipFile

import pytest
from custom_components import homeconnect_ws
from custom_components.homeconnect_ws import entity_descriptions
from homeconnect_websocket.testutils import MockAppliance

if TYPE_CHECKING:
    from collections.abc import Generator
    from pathlib import Path

from .const import (
    DEVICE_DESCRIPTION,
    ENTITY_DESCRIPTIONS,
    MOCK_AES_DEVICE_DESCRIPTION,
    MOCK_AES_DEVICE_ID,
    MOCK_AES_DEVICE_INFO,
    MOCK_TLS_DEVICE_DESCRIPTION,
    MOCK_TLS_DEVICE_ID,
    MOCK_TLS_DEVICE_INFO,
)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:  # noqa: ARG001
    """Enable custom integrations defined in the test dir."""
    return


@pytest.fixture
def patch_entity_description(monkeypatch: pytest.MonkeyPatch) -> None:
    """Patch entity_description for testing."""
    monkeypatch.setattr(
        entity_descriptions, "get_available_entities", Mock(return_value=ENTITY_DESCRIPTIONS)
    )
    monkeypatch.setattr(
        homeconnect_ws, "get_available_entities", Mock(return_value=ENTITY_DESCRIPTIONS)
    )


@pytest.fixture
def mock_setup_entry() -> Generator[AsyncMock]:
    """Override async_setup_entry."""
    with patch(
        "custom_components.homeconnect_ws.async_setup_entry", return_value=True
    ) as mock_setup_entry:
        yield mock_setup_entry


@pytest.fixture
def create_profile_file(tmp_path: Path) -> Path:
    """Create a test profile file."""
    file_path = tmp_path / "TestProfileFile.zip"

    with ZipFile(file_path, mode="w") as file:
        # TLS Appliance
        file.writestr("010203040506070809_FeatureMapping.xml", "TLS_FeatureMapping")
        file.writestr("010203040506070809_DeviceDescription.xml", "TLS_DeviceDescription")
        file.writestr("010203040506070809.json", json.dumps(MOCK_TLS_DEVICE_INFO))
        # AES Appliance
        file.writestr("101112131415161718_FeatureMapping.xml", "AES_FeatureMapping")
        file.writestr("101112131415161718_DeviceDescription.xml", "AES_DeviceDescription")
        file.writestr("101112131415161718.json", json.dumps(MOCK_AES_DEVICE_INFO))
    return file_path


@pytest.fixture
def mock_process_uploaded_file(
    create_profile_file: Path,
) -> Generator[MagicMock]:
    """Mock upload profile files."""
    ctx_mock = MagicMock()
    ctx_mock.__enter__.return_value = create_profile_file
    with patch(
        "custom_components.homeconnect_ws.config_flow.process_uploaded_file",
        return_value=ctx_mock,
    ) as mock_upload:
        yield mock_upload


@pytest.fixture
def mock_process_profile_file() -> Generator[MagicMock]:
    """Mock process profile files."""
    device_description = {
        MOCK_TLS_DEVICE_ID: {
            "info": MOCK_TLS_DEVICE_INFO,
            "description": MOCK_TLS_DEVICE_DESCRIPTION,
        },
        MOCK_AES_DEVICE_ID: {
            "info": MOCK_AES_DEVICE_INFO,
            "description": MOCK_AES_DEVICE_DESCRIPTION,
        },
    }
    with patch(
        "custom_components.homeconnect_ws.config_flow.HomeConnectConfigFlow._process_profile_file",
        return_value=device_description,
    ) as mock_upload:
        yield mock_upload


@pytest.fixture
def mock_appliance(
    request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch
) -> MockAppliance:
    """Mock HomeAppliance."""
    if "mock_appliance" in request.keywords:
        psk64 = request.keywords["mock_appliance"].kwargs.get("psk")
        iv64 = request.keywords["mock_appliance"].kwargs.get("iv")
    else:
        psk64 = None
        iv64 = None
    appliance = MockAppliance(DEVICE_DESCRIPTION, "host", "mock_app", "mock_app_id", psk64, iv64)
    monkeypatch.setattr(homeconnect_ws, "HomeAppliance", Mock(return_value=appliance))
    return appliance
