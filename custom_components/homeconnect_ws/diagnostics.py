"""Diagnostics support."""

from __future__ import annotations

import base64
import zlib
from pathlib import Path
from typing import TYPE_CHECKING, Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_DEVICE_ID
from homeassistant.helpers.storage import STORAGE_DIR

from .const import CONF_AES_IV, CONF_DESCRIPTION_FILENAME, CONF_FEATURE_FILENAME, CONF_PSK, DOMAIN

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from . import HCConfigEntry

TO_REDACT = [CONF_PSK, CONF_AES_IV, CONF_DEVICE_ID, "serialNumber", "deviceID", "shipSki", "mac"]


def compress_description(storage_dir: Path, config_entry: HCConfigEntry) -> dict[str, bytes]:
    """Compress device description files."""
    with Path(storage_dir / config_entry.data[CONF_DESCRIPTION_FILENAME]).open("rb") as file:
        device_description_bin = zlib.compress(file.read())
    with Path(storage_dir / config_entry.data[CONF_FEATURE_FILENAME]).open("rb") as file:
        feature_mapping_bin = zlib.compress(file.read())
    device_description_64 = base64.b64encode(device_description_bin).decode()
    feature_mapping_64 = base64.b64encode(feature_mapping_bin).decode()
    return {
        "device_description_64": device_description_64,
        "feature_mapping_64": feature_mapping_64,
    }


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: HCConfigEntry,
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    diagnostics = {
        "entry_data": async_redact_data(entry.data, TO_REDACT),
        "appliance_state": entry.runtime_data.appliance.dump(),
    }
    if entry.version > 1:
        storage_dir = Path(hass.config.path(STORAGE_DIR, DOMAIN))
        diagnostics.update(
            await hass.async_add_executor_job(compress_description, storage_dir, entry)
        )
    return diagnostics
