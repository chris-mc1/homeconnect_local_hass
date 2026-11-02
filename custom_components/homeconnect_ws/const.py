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
CONF_DESCRIPTION_FILENAME: Final = "description_filename"
CONF_FEATURE_FILENAME: Final = "feature_filename"
CONF_APPLIANCE_INFO: Final = "appliance_info"
CONF_DEV_OVERRIDE_HOST: Final = "override_host"
CONF_DEV_OVERRIDE_PSK: Final = "override_psk"

MAX_RECONECT_TIME: Final = 300

# Backoff for the connect/reconnect loop in HomeConnectCoordinator (based on PR #490).
# Without a delay the loop retries as fast as the network stack fails, pegging a CPU core.
# Delays: 5 s, 10 s, 20 s, ... capped at 300 s, each reduced by up to RECONNECT_JITTER.
INITIAL_RECONNECT_DELAY: Final = 5
MAX_RECONNECT_DELAY: Final = 300
RECONNECT_JITTER: Final = 0.2
# A connection lost earlier than this after connecting doesn't reset the backoff.
MIN_STABLE_CONNECTION_TIME: Final = 60
# Upper bound for a single connect attempt incl. handshake.
CONNECT_TIMEOUT: Final = 60
# Must stay below homeconnect_websocket's TaskManager BLOCK_TIMEOUT (20 s): once that timeout
# is hit, TaskManager.shutdown() cancels tasks in a loop without awaiting and blocks the event loop.
CLOSE_TIMEOUT: Final = 15
