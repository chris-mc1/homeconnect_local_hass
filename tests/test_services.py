"""Tests for services."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, Mock

import pytest
from custom_components.homeconnect_ws.const import DOMAIN
from homeassistant.const import CONF_DEVICE_ID
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import device_registry as dr

from . import setup_config_entry
from .const import CONFIG_ENTRIES

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeconnect_websocket.testutils import MockAppliance


async def _device_id(hass: HomeAssistant) -> str:
    entry = CONFIG_ENTRIES[0]
    assert await setup_config_entry(hass, entry)
    device = dr.async_get(hass).async_get_device(identifiers={(DOMAIN, entry.unique_id)})
    assert device
    return device.id


@pytest.mark.parametrize(
    ("service", "field", "entity"),
    [
        ("set_start_in", "start_in", "BSH.Common.Option.StartInRelative"),
        ("set_finish_in", "finish_in", "BSH.Common.Option.FinishInRelative"),
    ],
)
async def test_set_relative_time(
    hass: HomeAssistant,
    mock_appliance: MockAppliance,
    patch_entity_description: None,
    service: str,
    field: str,
    entity: str,
) -> None:
    """Test set_start_in/set_finish_in write the duration in seconds to the appliance."""
    device_id = await _device_id(hass)
    option = Mock(set_value=AsyncMock())
    mock_appliance.entities[entity] = option

    await hass.services.async_call(
        DOMAIN,
        service,
        {CONF_DEVICE_ID: device_id, field: {"hours": 1, "minutes": 30, "seconds": 5}},
        blocking=True,
    )

    option.set_value.assert_awaited_once_with(5405)


async def test_set_relative_time_not_available(
    hass: HomeAssistant,
    mock_appliance: MockAppliance,
    patch_entity_description: None,
) -> None:
    """Test set_finish_in raises when the appliance has no FinishInRelative option."""
    device_id = await _device_id(hass)
    mock_appliance.entities.pop("BSH.Common.Option.FinishInRelative", None)

    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            DOMAIN,
            "set_finish_in",
            {CONF_DEVICE_ID: device_id, "finish_in": {"minutes": 10}},
            blocking=True,
        )
