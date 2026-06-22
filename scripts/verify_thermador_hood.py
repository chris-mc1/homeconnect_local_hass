#!/usr/bin/env python3
"""Verify Thermador hood fan state: appliance truth vs HA entity.

Run inside the Home Assistant container:
  python3 /config/scripts/verify_thermador_hood.py
"""

from __future__ import annotations

import asyncio
import json
import math
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

from homeconnect_websocket import HomeAppliance

HOOD_TITLE = "THERMADOR Hood"
FAN_ENTITY = "fan.thermador_hood_fan"
CONFIG_ENTRIES = Path("/config/.storage/core.config_entries")
TOKEN_FILE = Path("/config/.ha_api_token")
HA_URL = os.environ.get("HA_URL", "http://127.0.0.1:8123")

VENTING_LEVEL = "Cooking.Common.Option.Hood.VentingLevel"
OPERATION_STATE = "BSH.Common.Status.OperationState"
VENTING_PROGRAM = "Cooking.Common.Program.Hood.Venting"


def _load_hood_entry() -> dict:
    with CONFIG_ENTRIES.open() as handle:
        entries = json.load(handle)["data"]["entries"]
    for entry in entries:
        if entry.get("title") == HOOD_TITLE:
            return entry
    msg = f"Config entry {HOOD_TITLE!r} not found"
    raise SystemExit(msg)


def fan_state_from_appliance(app: HomeAppliance) -> tuple[bool, int]:
    """Mirror HCFan.is_on / percentage logic."""
    if app.active_program is None:
        return False, 0

    venting = app.entities.get(VENTING_LEVEL)
    if venting is None or venting.value_raw in (None, 0):
        return False, 0

    if VENTING_PROGRAM not in app.programs:
        return True, 0

    speed_count = 0
    speed_mapping: list[tuple[int, int]] = []
    for option in venting.enum:
        if option == 0:
            continue
        speed_count += 1
        speed_mapping.append((option, speed_count))

    if speed_count == 0:
        return True, 0

    speed_range = (1, speed_count)
    for enum_value, speed in speed_mapping:
        if venting.value_raw == enum_value:
            low, high = speed_range
            return True, math.ceil((speed - low) / (high - low) * 100)
    return True, 0


def _ha_tokens() -> list[str]:
    tokens: list[str] = []
    if token := os.environ.get("HA_TOKEN"):
        tokens.append(token)
    if TOKEN_FILE.is_file():
        tokens.append(TOKEN_FILE.read_text().strip())
    auth_path = CONFIG_ENTRIES.parent / "auth"
    if auth_path.is_file():
        with auth_path.open() as handle:
            auth = json.load(handle)["data"]
        tokens.extend(
            refresh["token"]
            for refresh in auth.get("refresh_tokens", [])
            if refresh.get("token_type") == "long_lived_access_token" and refresh.get("token")
        )
    seen: set[str] = set()
    unique: list[str] = []
    for token in tokens:
        if token not in seen:
            seen.add(token)
            unique.append(token)
    return unique


def ha_fan_state() -> tuple[str, int | None]:
    last_error: urllib.error.HTTPError | None = None
    for token in _ha_tokens():
        request = urllib.request.Request(
            f"{HA_URL}/api/states/{FAN_ENTITY}",
            headers={"Authorization": f"Bearer {token}"},
        )
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                payload = json.load(response)
            return payload["state"], payload.get("attributes", {}).get("percentage")
        except urllib.error.HTTPError as exc:
            last_error = exc
    if last_error is not None:
        raise last_error
    raise urllib.error.HTTPError(FAN_ENTITY, 401, "no HA API token available", {}, None)


async def appliance_truth() -> tuple[bool, int, dict]:
    entry = _load_hood_entry()
    data = entry["data"]
    app = HomeAppliance(
        data["description"],
        data["host"],
        data["device_id"],
        entry["entry_id"],
        data.get("psk"),
        data.get("aes_iv"),
    )
    await app.connect()
    await asyncio.sleep(2)
    on, pct = fan_state_from_appliance(app)
    details = {
        "active_program": app.active_program.name if app.active_program else None,
        "operation_state": app.entities[OPERATION_STATE].value_raw
        if OPERATION_STATE in app.entities
        else None,
        "venting_level": app.entities[VENTING_LEVEL].value_raw
        if VENTING_LEVEL in app.entities
        else None,
    }
    return on, pct, details


async def main() -> int:
    expected_on, expected_pct, details = await appliance_truth()
    print(f"appliance: on={expected_on} percentage={expected_pct} {details}")

    if not _ha_tokens():
        print("ha: skipped (no token available)")
        return 0

    try:
        ha_state, ha_pct = ha_fan_state()
    except urllib.error.HTTPError as exc:
        if exc.code == 401:
            print("ha: skipped (stored tokens unauthorized)")
            return 0
        print(f"ha: HTTP {exc.code} — {exc.reason}", file=sys.stderr)
        return 1

    print(f"ha: state={ha_state} percentage={ha_pct}")
    expected_state = "on" if expected_on else "off"
    errors: list[str] = []
    if ha_state != expected_state:
        errors.append(f"state mismatch: ha={ha_state!r} expected={expected_state!r}")
    if expected_on and ha_pct != expected_pct:
        errors.append(f"percentage mismatch: ha={ha_pct} expected={expected_pct}")
    if not expected_on and ha_pct not in (0, None):
        errors.append(f"percentage should be 0 when off, ha={ha_pct}")

    if errors:
        for error in errors:
            print(f"FAIL: {error}", file=sys.stderr)
        return 1

    print("OK: appliance and HA agree")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
