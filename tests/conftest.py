"""Fixtures for testing."""

from __future__ import annotations

import json
from copy import deepcopy
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from zipfile import ZipFile

import pytest
from custom_components import homeconnect_ws
from custom_components.homeconnect_ws import config_flow, coordinator, entity_descriptions
from custom_components.homeconnect_ws.config_flow import ProfileFileEntry
from homeconnect_websocket.testutils import TEST_PSK64, MockAppliance

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Awaitable, Callable, Generator
    from pathlib import Path

    from homeconnect_websocket.entities import DeviceDescription
    from homeconnect_websocket.session import ConnectionState

from .const import (
    DEVICE_DESCRIPTION,
    ENTITY_DESCRIPTIONS,
    MOCK_AES_DEVICE_ID,
    MOCK_AES_DEVICE_INFO,
    MOCK_TLS_DEVICE_ID,
    MOCK_TLS_DEVICE_ID_2,
    MOCK_TLS_DEVICE_INFO,
)

pytest_plugins = ["homeconnect_websocket.testutils"]


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
        MOCK_TLS_DEVICE_ID: ProfileFileEntry(
            info=MOCK_TLS_DEVICE_INFO,
            device_description=b"TLS_DeviceDescription",
            feature_mapping=b"TLS_FeatureMapping",
        ),
        MOCK_AES_DEVICE_ID: ProfileFileEntry(
            info=MOCK_AES_DEVICE_INFO,
            device_description=b"AES_DeviceDescription",
            feature_mapping=b"AES_FeatureMapping",
        ),
        MOCK_TLS_DEVICE_ID_2: ProfileFileEntry(
            info=MOCK_TLS_DEVICE_INFO,
            device_description=b"TLS_DeviceDescription",
            feature_mapping=b"TLS_DeviceDescription",
        ),
    }
    with patch(
        "custom_components.homeconnect_ws.config_flow.process_profile_file",
        return_value=deepcopy(device_description),
    ) as mock_upload:
        yield mock_upload


@pytest.fixture
async def patch_create_appliance(monkeypatch: pytest.MonkeyPatch) -> AsyncGenerator[Mock]:
    """Patch helpers.create_appliance."""
    appliance = MockAppliance(
        DEVICE_DESCRIPTION, "host", "mock_app", "mock_app_id", TEST_PSK64, None
    )
    appliance_mock = Mock(return_value=appliance)

    def create_appliance(
        description: DeviceDescription,
        host: str,
        app_id: str,
        psk64: str,
        iv64: str | None = None,
        connection_callback: Callable[[ConnectionState], Awaitable[None]] | None = None,
    ) -> MockAppliance:
        appliance._ext_connection_state_callback = connection_callback
        return appliance_mock(
            description=description,
            host=host,
            app_id=app_id,
            psk64=psk64,
            iv64=iv64,
            connection_callback=connection_callback,
        )

    monkeypatch.setattr(config_flow, "create_appliance", create_appliance)
    monkeypatch.setattr(coordinator, "create_appliance", create_appliance)

    yield appliance_mock
    await appliance.close()


@pytest.fixture
def mock_appliance(patch_create_appliance: Mock) -> MockAppliance:
    """Mock HomeAppliance."""
    return patch_create_appliance.return_value


@pytest.fixture
def mock_write_file() -> Generator[MagicMock]:
    """Mock write file."""
    with patch(
        "custom_components.homeconnect_ws.config_flow.write_file",
        return_value=None,
    ) as mock_write_file:
        yield mock_write_file


@pytest.fixture
def mock_parse_device_description() -> Generator[MagicMock]:
    """Mock parse_device_description."""
    with patch(
        "custom_components.homeconnect_ws.config_flow.parse_device_description",
        return_value=DEVICE_DESCRIPTION,
    ) as mock_parse_device_description:
        yield mock_parse_device_description
