#!/usr/bin/env python3
"""Verify Thermador hood fan state: appliance truth vs HA entity.

Run inside the Home Assistant container:
  python3 /config/scripts/verify_thermador_hood.py

Optional: put a long-lived access token in /config/.ha_api_token for HA UI
cross-check (gitignored on the host). Without it, only appliance truth is checked.
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
    operation = app.entities.get(OPERATION_STATE)
    if operation is not None and operation.value_raw == 0:
        return False, 0

    venting = app.entities.get(VENTING_LEVEL)
    if venting is None or venting.value_raw in (None, 0):
        return False, 0

    if VENTING_PROGRAM not in app.programs:
        return True, 0

    speed_count = 0
    speed_range: tuple[int, int] | None = None
    speed_mapping: list[tuple[int, int]] = []
    for option in venting.enum:
        if option == 0:
            continue
        speed_count += 1
        speed_mapping.append((option, speed_count))
    if speed_count:
        speed_range = (1, speed_count)

    if speed_range is None:
        return True, 0

    for enum_value, speed in speed_mapping:
        if venting.value_raw == enum_value:
            low, high = speed_range
            return True, math.ceil((speed - low) / (high - low) * 100)
    return True, 0


def ha_fan_state(token: str) -> tuple[str, int | None]:
    request = urllib.request.Request(
        f"{HA_URL}/api/states/{FAN_ENTITY}",
        headers={"Authorization": f"Bearer {token}"},
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        payload = json.load(response)
    percentage = payload.get("attributes", {}).get("percentage")
    return payload["state"], percentage


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

    token = os.environ.get("HA_TOKEN")
    if not token and TOKEN_FILE.is_file():
        token = TOKEN_FILE.read_text().strip()

    if not token:
        print("ha: skipped (set HA_TOKEN or /config/.ha_api_token for UI cross-check)")
        return 0

    try:
        ha_state, ha_pct = ha_fan_state(token)
    except urllib.error.HTTPError as exc:
        print(f"ha: HTTP {exc.code} — token invalid or expired", file=sys.stderr)
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
