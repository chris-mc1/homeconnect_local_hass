"""The Home Connect Websocket integration."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from aiohttp import ClientConnectionError, ClientConnectorSSLError
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_DESCRIPTION, CONF_DEVICE_ID, CONF_HOST
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryError, ConfigEntryNotReady
from homeassistant.helpers.device_registry import (
    CONNECTION_NETWORK_MAC,
    DeviceInfo,
    format_mac,
)
from homeconnect_websocket import HomeAppliance

from .const import CONF_AES_IV, CONF_PSK, DOMAIN, PLATFORMS
from .entity_descriptions import get_available_entities

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .entity_descriptions.descriptions_definitions import EntityDescriptions

_LOGGER = logging.getLogger(__name__)


@dataclass
class HCData:
    """Dataclass for runtime data."""

    appliance: HomeAppliance
    device_info: DeviceInfo
    available_entity_descriptions: EntityDescriptions


type HCConfigEntry = ConfigEntry[HCData]


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: HCConfigEntry,
) -> bool:
    """Set up this integration using config entry."""
    _LOGGER.debug("Setting up %s", config_entry.data[CONF_DESCRIPTION]["info"].get("model"))
    appliance = HomeAppliance(
        description=config_entry.data[CONF_DESCRIPTION],
        host=config_entry.data[CONF_HOST],
        app_name="Homeassistant",
        app_id=config_entry.data[CONF_DEVICE_ID],
        psk64=config_entry.data[CONF_PSK],
        iv64=config_entry.data.get(CONF_AES_IV, None),
    )
    try:
        await appliance.connect()
    except ClientConnectorSSLError as ex:
        await appliance.close()
        msg = f"Authentication failed with {config_entry.data[CONF_HOST]}"
        raise ConfigEntryAuthFailed(msg) from ex
    except (TimeoutError, ClientConnectionError) as ex:
        await appliance.close()
        msg = f"Can't connect to {config_entry.data[CONF_HOST]}"
        raise ConfigEntryNotReady(msg) from ex
    except Exception:
        await appliance.close()
        raise

    _LOGGER.debug("Connected to %s", config_entry.data[CONF_DESCRIPTION]["info"].get("vib"))
    if not appliance.info:
        msg = "Appliance has no device info"
        raise ConfigEntryError(msg)

    device_info = DeviceInfo(
        connections={(CONNECTION_NETWORK_MAC, format_mac(appliance.info["mac"]))},
        hw_version=appliance.info["hwVersion"],
        identifiers={(DOMAIN, appliance.info["deviceID"])},
        name=f"{appliance.info['brand'].capitalize()} {appliance.info['type']}",
        manufacturer=appliance.info["brand"].capitalize(),
        model=f"{appliance.info['type']}",
        model_id=appliance.info["vib"],
        sw_version=appliance.info["swVersion"],
    )
    available_entities = get_available_entities(appliance)
    config_entry.runtime_data = HCData(appliance, device_info, available_entities)
    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: HCConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.debug("Unloading %s", entry.data[CONF_DESCRIPTION]["info"].get("vib"))
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        await entry.runtime_data.appliance.close()
    return unload_ok
