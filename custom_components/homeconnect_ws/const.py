"""Constants."""

from __future__ import annotations

from typing import Final

from homeassistant.const import Platform

DOMAIN: Final = "homeconnect_ws"
PLATFORMS: Final = [
    Platform.BINARY_SENSOR,
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.SELECT,
    Platform.BUTTON,
    Platform.NUMBER,
    Platform.LIGHT,
    Platform.FAN,
]

CONF_PSK: Final = "psk"
CONF_AES_IV: Final = "aes_iv"
CONF_FILE: Final = "file"
CONF_MANUAL_HOST: Final = "manual_host"
CONF_DEV_SETUP_FROM_DUMP: Final = "setup_from_dump_enabled"
CONF_DEV_OVERRIDE_HOST: Final = "override_host"
CONF_DEV_OVERRIDE_PSK: Final = "override_psk"
