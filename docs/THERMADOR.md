# Thermador / US Home Connect Local gaps

Verified against Bowman Mtn production appliances (2026-06-22):

| Appliance | Model | Integration |
|-----------|-------|-------------|
| FridgeFreezer | T36IB905SP | `homeconnect_ws` zeroconf |
| Oven | PRG366WH | `homeconnect_ws` zeroconf |
| Hood | HMWB361WS | `homeconnect_ws` zeroconf |

## Root causes of “missing” entities

1. **Locale-specific API keys** — US Thermador LAN profiles expose `*Fahrenheit` keys, not Celsius.
2. **Incomplete refrigeration mappings** — Fridge door-assistant settings were freezer-only.
3. **Hood fan control** — Speed uses venting program options; off sets VentingLevel to FanOff (0).
   Program `0` POST is rejected (`UnknownUID`).

## Hood fan (`fan.thermador_hood_fan`)

- **On/off** — derived from `active_program` + VentingLevel, not power switch.
- **Off command** — sets VentingLevel to 0 on active venting program (not program clear).
- **UI stale state fix** — fan listens to `ActiveProgram` + `OperationState`; `is_on` is false when
  `active_program` is None even if VentingLevel is stale.
- **Do not use** `switch.thermador_hood_power` (disabled in registry; returns 400 while venting).

## Hood select (`select.thermador_hood_delayed_shutoff_stage`)

- Enum includes FanOff (0) but appliance `min=1` — selecting Off caused `InvalidUIDValue`.
- Fix: HCSelect filters options by entity min/max.

## Deploy / verify (Bowman Mtn)

```bash
# From fork repo on dev machine:
./scripts/run_tests.sh          # 86 tests in HA container
./scripts/deploy_bowman.sh      # rsync, restart, reload hood entry, verify

# Manual verify inside container:
docker exec home-assistant python3 /config/scripts/verify_thermador_hood.py
```

Verification reads long-lived tokens from `/config/.storage/auth` for HA API cross-check.

## Production path

`/home/ntableman/docker/ha/config/custom_components/homeconnect_ws`

Branch: `fix/thermador-us-appliances`  
Upstream PR: https://github.com/chris-mc1/homeconnect_local_hass/pull/408

## Verification commands

```bash
# Entity count
docker exec home-assistant python3 -c "
import json
er=json.load(open('/config/.storage/core.entity_registry'))
hc=[e for e in er['data']['entities'] if e.get('platform')=='homeconnect_ws']
print(len(hc))
"

# Hood fan state vs appliance (deployed script)
docker exec home-assistant python3 /config/scripts/verify_thermador_hood.py
```

## Test status

86 passed (Python 3.14 / HA container, 2026-06-22).
