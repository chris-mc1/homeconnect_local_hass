"""The Home Connect Websocket integration."""

from __future__ import annotations

import contextlib
import logging
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Never

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_DESCRIPTION
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.device_registry import (
    CONNECTION_NETWORK_MAC,
    DeviceInfo,
    format_mac,
)
from homeassistant.helpers.storage import STORAGE_DIR
from homeassistant.util.hass_dict import HassKey
from homeconnect_websocket import (
    CodeResponsError,
    DeviceDescription,
    Entity,
    parse_device_description,
)

from .const import (
    CONF_APPLIANCE_INFO,
    CONF_DESCRIPTION_FILENAME,
    CONF_DEV_OVERRIDE_HOST,
    CONF_DEV_OVERRIDE_PSK,
    CONF_FEATURE_FILENAME,
    DOMAIN,
    PLATFORMS,
)
from .coordinator import HomeConnectCoordinator
from .entity_descriptions import get_available_entities
from .helpers import error_decorator, get_config_entry_from_call

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant, ServiceCall, ServiceResponse
    from homeassistant.helpers.typing import ConfigType
    from homeconnect_websocket import HomeAppliance

    from .entity_descriptions import _EntityDescriptionsType

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: {
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
    coordinator: HomeConnectCoordinator


@dataclass
class HCConfig:
    """Dataclass for hass.data."""

    override_host: str | None = None
    override_psk: str | None = None


type HCConfigEntry = ConfigEntry[HCData]

HC_KEY: HassKey[HCConfig] = HassKey(DOMAIN)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up integration global config."""
    hass.data.setdefault(DOMAIN, HCConfig())
    if DOMAIN in config:
        hass.data[HC_KEY].override_host = config[DOMAIN].get(CONF_DEV_OVERRIDE_HOST)
        hass.data[HC_KEY].override_psk = config[DOMAIN].get(CONF_DEV_OVERRIDE_PSK)

    def _get_entity_or_raise(appliance: HomeAppliance, key: str, error_key: str) -> Entity:
        entity = appliance.entities.get(key)
        if not entity:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key=error_key,
            )
        return entity

    def _duration_to_seconds(data: dict) -> int:
        return (
            int(data.get("hours", 0)) * 3600
            + int(data.get("minutes", 0)) * 60
            + int(data.get("seconds", 0))
        )

    def _raise_start_error(err: CodeResponsError) -> Never:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="start_program_error",
            translation_placeholders={"code": err.code, "resource": err.resource},
        ) from None

    async def _set_value_or_raise(entity: Entity, relative_time_in_seconds: int) -> None:
        try:
            await entity.set_value(relative_time_in_seconds)
        except CodeResponsError as exc:
            _raise_start_error(exc)

    @error_decorator
    async def handle_start_program(call: ServiceCall) -> ServiceResponse:
        config_entry = await get_config_entry_from_call(hass, call)

        options = {}
        appliance = config_entry.runtime_data.appliance
        if "start_in" in call.data:
            entity = _get_entity_or_raise(
                appliance, "BSH.Common.Option.StartInRelative", "start_in_not_available"
            )
            options[entity.uid] = _duration_to_seconds(call.data["start_in"])

        if "finish_in" in call.data:
            entity = _get_entity_or_raise(
                appliance, "BSH.Common.Option.FinishInRelative", "finish_in_not_available"
            )
            options[entity.uid] = _duration_to_seconds(call.data["finish_in"])

        if appliance.selected_program:
            try:
                await appliance.selected_program.start(options)
            except CodeResponsError as exc:
                _raise_start_error(exc)
        else:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="no_program_selected",
            )

    @error_decorator
    async def handle_set_start_in(call: ServiceCall) -> ServiceResponse:
        config_entry = await get_config_entry_from_call(hass, call)
        appliance = config_entry.runtime_data.appliance
        _set_value_or_raise(
            _get_entity_or_raise(
                appliance, "BSH.Common.Option.StartInRelative", "start_in_not_available"
            ),
            _duration_to_seconds(call.data["start_in"]),
        )

    @error_decorator
    async def handle_set_finish_in(call: ServiceCall) -> ServiceResponse:
        config_entry = await get_config_entry_from_call(hass, call)
        appliance = config_entry.runtime_data.appliance
        _set_value_or_raise(
            _get_entity_or_raise(
                appliance, "BSH.Common.Option.FinishInRelative", "finish_in_not_available"
            ),
            _duration_to_seconds(call.data["finish_in"]),
        )

    hass.services.async_register(DOMAIN, "start_program", handle_start_program)
    hass.services.async_register(DOMAIN, "set_start_in", handle_set_start_in)
    hass.services.async_register(DOMAIN, "set_finish_in", handle_set_finish_in)
    return True


def load_description(storage_dir: Path, config_entry: HCConfigEntry) -> DeviceDescription:
    """Load device description from file."""
    with (storage_dir / config_entry.data[CONF_DESCRIPTION_FILENAME]).open() as file:
        device_description_xml = file.read()
    with (storage_dir / config_entry.data[CONF_FEATURE_FILENAME]).open() as file:
        feature_mapping_xml = file.read()
    description = parse_device_description(device_description_xml, feature_mapping_xml)
    description["info"].update(config_entry.data[CONF_APPLIANCE_INFO])
    return description


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: HCConfigEntry,
) -> bool:
    """Set up this integration using config entry."""
    if config_entry.version == 1:
        _LOGGER.debug("Setting up %s", config_entry.data[CONF_DESCRIPTION]["info"].get("model"))
        description = deepcopy(config_entry.data[CONF_DESCRIPTION])
    else:
        _LOGGER.debug("Setting up %s", config_entry.data[CONF_APPLIANCE_INFO].get("model"))
        storage_dir = Path(hass.config.path(STORAGE_DIR, DOMAIN))
        description = await hass.async_add_executor_job(load_description, storage_dir, config_entry)

    coordinator = HomeConnectCoordinator(hass, config_entry, description)

    appliance = coordinator.appliance
    device_info = DeviceInfo(
        hw_version=appliance.info.get("hwVersion"),
        identifiers={(DOMAIN, config_entry.unique_id)},
        model=f"{appliance.info.get('type')}",
        model_id=appliance.info.get("vib"),
        sw_version=appliance.info.get("swVersion"),
    )

    if mac := appliance.info.get("mac"):
        device_info["connections"] = {(CONNECTION_NETWORK_MAC, format_mac(mac))}

    if brand := appliance.info.get("brand"):
        device_info["manufacturer"] = brand.capitalize()

    if (type_ := appliance.info.get("type")) and brand:
        device_info["name"] = f"{brand.capitalize()} {type_}"

    available_entities = get_available_entities(appliance)

    config_entry.runtime_data = HCData(
        appliance=appliance,
        device_info=device_info,
        available_entity_descriptions=available_entities,
        coordinator=coordinator,
    )

    await coordinator.async_config_entry_first_refresh()
    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: HCConfigEntry) -> bool:
    """Unload a config entry."""
    if entry.version == 1:
        _LOGGER.debug("Unloading %s", entry.data[CONF_DESCRIPTION]["info"].get("vib"))
    else:
        _LOGGER.debug("Unloading %s", entry.data[CONF_APPLIANCE_INFO].get("vib"))

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        await entry.runtime_data.coordinator.close()
    return unload_ok


async def async_migrate_entry(hass: HomeAssistant, config_entry: HCConfigEntry) -> bool:  # noqa: ARG001
    """Migrate config entry."""
    return True


async def async_remove_entry(hass: HomeAssistant, config_entry: HCConfigEntry) -> None:
    """Remove a config entry."""

    def remove_files(storage_dir: Path, config_entry: HCConfigEntry) -> None:
        """Remove profile files."""
        with contextlib.suppress(FileNotFoundError):
            (storage_dir / Path(config_entry.data[CONF_DESCRIPTION_FILENAME])).unlink()
        with contextlib.suppress(FileNotFoundError):
            (storage_dir / Path(config_entry.data[CONF_FEATURE_FILENAME])).unlink()
        with contextlib.suppress(FileNotFoundError, OSError):
            (storage_dir / Path(config_entry.data[CONF_DESCRIPTION_FILENAME])).parent.rmdir()

    if config_entry.version >= 2:
        storage_dir = Path(hass.config.path(STORAGE_DIR, DOMAIN))
        await hass.async_add_executor_job(remove_files, storage_dir, config_entry)
