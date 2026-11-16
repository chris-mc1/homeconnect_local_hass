"""Tests for the WiFi signal strength sensor, which is polled with /ni/info."""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, Mock

from custom_components import homeconnect_ws
from custom_components.homeconnect_ws import entity_descriptions
from custom_components.homeconnect_ws.entity_descriptions import HCSensorEntityDescription
from custom_components.homeconnect_ws.sensor import HCWiFI
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.const import STATE_UNKNOWN
from homeassistant.util import dt as dt_util
from homeconnect_websocket import NotConnectedError
from pytest_homeassistant_custom_component.common import async_fire_time_changed

from . import setup_config_entry
from .const import CONFIG_ENTRIES, ENTITY_DESCRIPTIONS

if TYPE_CHECKING:
    import pytest
    from homeassistant.core import HomeAssistant
    from homeconnect_websocket.testutils import MockAppliance

ENTITY_ID = "sensor.fake_brand_homeappliance_wifi"

# Answer of /ni/info of the Gaggenau DF271101F (list with one element per network interface).
NETWORK_INFO = [{"interfaceID": 0, "type": "WiFi", "ssid": "home", "rssi": -57}]


def test_wifi_sensor_polls() -> None:
    """The sensor has to be polled, a CoordinatorEntity does not poll by default."""
    assert object.__new__(HCWiFI).should_poll is True


async def _setup_wifi_sensor(
    hass: HomeAssistant,
    mock_appliance: MockAppliance,
    monkeypatch: pytest.MonkeyPatch,
    network_config: AsyncMock,
) -> None:
    """Set up an appliance with the WiFi sensor (the one without a Home Connect entity)."""
    descriptions = {
        **ENTITY_DESCRIPTIONS,
        "wifi": [
            HCSensorEntityDescription(
                key="Test.WiFi",
                name="WiFi",
                device_class=SensorDeviceClass.SIGNAL_STRENGTH,
            )
        ],
    }
    monkeypatch.setattr(
        entity_descriptions, "get_available_entities", Mock(return_value=descriptions)
    )
    monkeypatch.setattr(homeconnect_ws, "get_available_entities", Mock(return_value=descriptions))
    mock_appliance.get_network_config = network_config
    assert await setup_config_entry(hass, CONFIG_ENTRIES[0])


async def test_wifi_sensor_value(
    hass: HomeAssistant,
    mock_appliance: MockAppliance,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """After a poll the sensor shows the rssi from /ni/info."""
    network_config = AsyncMock(return_value=NETWORK_INFO)
    await _setup_wifi_sensor(hass, mock_appliance, monkeypatch, network_config)

    # Nothing is polled when the entity is added, only after the scan interval (30 seconds).
    assert hass.states.get(ENTITY_ID).state == STATE_UNKNOWN

    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=31))
    await hass.async_block_till_done()

    network_config.assert_awaited()
    assert hass.states.get(ENTITY_ID).state == "-57"


async def test_wifi_sensor_keeps_value_on_error(
    hass: HomeAssistant,
    mock_appliance: MockAppliance,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A failed poll (appliance not connected) does not raise and keeps the last value."""
    network_config = AsyncMock(return_value=NETWORK_INFO)
    await _setup_wifi_sensor(hass, mock_appliance, monkeypatch, network_config)

    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=31))
    await hass.async_block_till_done()
    assert hass.states.get(ENTITY_ID).state == "-57"

    network_config.side_effect = NotConnectedError
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=62))
    await hass.async_block_till_done()
    assert hass.states.get(ENTITY_ID).state == "-57"
