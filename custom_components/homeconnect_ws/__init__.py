"""The Home Connect Websocket integration."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

import voluptuous as vol
from aiohttp import ClientConnectionError, ClientConnectorSSLError
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_DESCRIPTION, CONF_DEVICE_ID, CONF_HOST
from homeassistant.exceptions import (
    ConfigEntryAuthFailed,
    ConfigEntryError,
    ConfigEntryNotReady,
    ServiceValidationError,
)
from homeassistant.helpers.device_registry import (
    CONNECTION_NETWORK_MAC,
    DeviceInfo,
    format_mac,
)
from homeassistant.util.hass_dict import HassKey
from homeconnect_websocket import HomeAppliance

from .const import (
    CONF_AES_IV,
    CONF_DEV_OVERRIDE_HOST,
    CONF_DEV_OVERRIDE_PSK,
    CONF_DEV_SETUP_FROM_DUMP,
    CONF_PSK,
    DOMAIN,
    PLATFORMS,
)
from .entity_descriptions import get_available_entities
from .helpers import error_decorator, get_config_entry_from_call

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant, ServiceCall, ServiceResponse
    from homeassistant.helpers.typing import ConfigType

    from .entity_descriptions import _EntityDescriptionsType

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: {
            vol.Optional(CONF_DEV_SETUP_FROM_DUMP, default=False): vol.Boolean(),
            vol.Optional(CONF_DEV_OVERRIDE_HOST): str,
            vol.Optional(CONF_DEV_OVERRIDE_PSK): str,
        }
    },
    extra=vol.ALLOW_EXTRA,
)


@dataclass
class HCData:
    """Dataclass for runtime data."""

    appliance: HomeAppliance
    device_info: DeviceInfo
    available_entity_descriptions: _EntityDescriptionsType


@dataclass
class HCConfig:
    """Dataclass for hass.data."""

    setup_from_dump: bool = False
    override_host: str | None = None
    override_psk: str | None = None


type HCConfigEntry = ConfigEntry[HCData]

HC_KEY: HassKey[HCConfig] = HassKey(DOMAIN)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up integration global config."""
    hass.data.setdefault(DOMAIN, HCConfig())
    if DOMAIN in config:
        hass.data[HC_KEY].setup_from_dump = config[DOMAIN].get(CONF_DEV_SETUP_FROM_DUMP, False)
        hass.data[HC_KEY].override_host = config[DOMAIN].get(CONF_DEV_OVERRIDE_HOST)
        hass.data[HC_KEY].override_psk = config[DOMAIN].get(CONF_DEV_OVERRIDE_PSK)

    @error_decorator
    async def handle_start_program(call: ServiceCall) -> ServiceResponse:
        config_entry = await get_config_entry_from_call(hass, call)

        options = {}
        appliance = config_entry.runtime_data.appliance
        if "start_in" in call.data:
            if start_in_entity := appliance.entities.get("BSH.Common.Option.StartInRelative"):
                relative_time_in_seconds = (
                    int(call.data["start_in"].get("hours", 0)) * 3600
                    + int(call.data["start_in"].get("minutes", 0)) * 60
                    + int(call.data["start_in"].get("seconds", 0))
                )
                options[start_in_entity.uid] = relative_time_in_seconds
            else:
                raise ServiceValidationError(
                    translation_domain=DOMAIN,
                    translation_key="start_in_not_available",
                )
        if "finish_in" in call.data:
            if finish_in_entity := appliance.entities.get("BSH.Common.Option.FinishInRelative"):
                relative_time_in_seconds = (
                    int(call.data["finish_in"].get("hours", 0)) * 3600
                    + int(call.data["finish_in"].get("minutes", 0)) * 60
                    + int(call.data["finish_in"].get("seconds", 0))
                )
                options[finish_in_entity.uid] = relative_time_in_seconds
            else:
                raise ServiceValidationError(
                    translation_domain=DOMAIN,
                    translation_key="finish_in_not_available",
                )
        if appliance.selected_program:
            await appliance.selected_program.start(options)
        else:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="no_program_selected",
            )

    @error_decorator
    async def handle_set_start_in(call: ServiceCall) -> ServiceResponse:
        config_entry = await get_config_entry_from_call(hass, call)
        appliance = config_entry.runtime_data.appliance
        if start_in_entity := appliance.entities.get("BSH.Common.Option.StartInRelative"):
            relative_time_in_seconds = (
                int(call.data["start_in"].get("hours", 0)) * 3600
                + int(call.data["start_in"].get("minutes", 0)) * 60
                + int(call.data["start_in"].get("seconds", 0))
            )
            await start_in_entity.set_value(relative_time_in_seconds)
        else:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="start_in_not_available",
            )

    @error_decorator
    async def handle_set_finish_in(call: ServiceCall) -> ServiceResponse:
        config_entry = await get_config_entry_from_call(hass, call)
        appliance = config_entry.runtime_data.appliance
        if finish_in_entity := appliance.entities.get("BSH.Common.Option.FinishInRelative"):
            relative_time_in_seconds = (
                int(call.data["finish_in"].get("hours", 0)) * 3600
                + int(call.data["finish_in"].get("minutes", 0)) * 60
                + int(call.data["finish_in"].get("seconds", 0))
            )
            await finish_in_entity.set_value(relative_time_in_seconds)
        else:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="finish_in_not_available",
            )

    hass.services.async_register(DOMAIN, "start_program", handle_start_program)
    hass.services.async_register(DOMAIN, "set_start_in", handle_set_start_in)
    hass.services.async_register(DOMAIN, "set_finish_in", handle_set_finish_in)
    return True


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
        raise ConfigEntryAuthFailed(
            translation_domain=DOMAIN,
            translation_key="auth_failed",
            translation_placeholders={"host": config_entry.data[CONF_HOST]},
        ) from ex
    except (TimeoutError, ClientConnectionError) as ex:
        await appliance.close()
        raise ConfigEntryNotReady(
            translation_domain=DOMAIN,
            translation_key="cannot_connect",
            translation_placeholders={"host": config_entry.data[CONF_HOST]},
        ) from ex
    except Exception:
        await appliance.close()
        raise

    _LOGGER.debug("Connected to %s", config_entry.data[CONF_DESCRIPTION]["info"].get("vib"))
    if not appliance.info:
        raise ConfigEntryError(
            translation_domain=DOMAIN,
            translation_key="no_device_info",
        )

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
