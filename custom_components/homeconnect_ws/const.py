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

# Connection handling. All values in seconds.
CONNECT_TIMEOUT: Final = 60
"""Hard limit for TCP connect + TLS + websocket upgrade + handshake."""
CLOSE_TIMEOUT: Final = 45
"""Hard limit for closing a session."""
RECONNECT_DELAY_INITIAL: Final = 1
RECONNECT_DELAY_MAX: Final = 300
RECONNECT_JITTER: Final = 0.2
"""Delays are randomized by +/- this fraction."""
STABLE_CONNECTION_TIME: Final = 60
"""A connection must stay up this long before the backoff is reset."""
LIVENESS_POLL_INTERVAL: Final = 30
"""Safety net: check the session state this often while connected."""
IDENTITY_FAILURE_THRESHOLD: Final = 3
"""Consecutive authentication/identity failures before a repair issue is raised."""
IDENTITY_RETRY_DELAY: Final = 600
"""Minimum delay between attempts once the appliance failed the identity check."""
MAX_CONNECTS_PER_MINUTE: Final = 10
"""Watchdog: more connection attempts than this pause the entry."""
RECONNECT_STORM_PAUSE: Final = 600
ISSUE_WRONG_DEVICE: Final = "wrong_device"
ISSUE_RECONNECT_STORM: Final = "reconnect_storm"
