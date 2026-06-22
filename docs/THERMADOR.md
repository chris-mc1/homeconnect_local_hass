# Thermador / US Home Connect Local gaps

Verified against Bowman Mtn production appliances (2026-06-22):

| Appliance | Model path | Integration entry |
|-----------|------------|-------------------|
| FridgeFreezer | T36IB905SP | `homeconnect_ws` zeroconf |
| Oven | PRG366WH | `homeconnect_ws` zeroconf |
| Hood | HMWB361WS | `homeconnect_ws` zeroconf |

## Root causes of “missing” entities

1. **Locale-specific API keys** — US Thermador LAN profiles expose `*Fahrenheit` temperature
   keys, not `CurrentTemperature` / `SetpointTemperature` (Celsius). The integration must map
   both.
2. **Incomplete refrigeration mappings** — Fridge door-assistant settings exist on the appliance
   but were only mapped for the freezer compartment.
3. **Hood fan control** — Speed changes require starting the venting program first; turning off
   uses `DELETE /ro/activeProgram` on Thermador hoods.

## Fixes in `fix/thermador-us-appliances`

- `cooking.py`: Fahrenheit fallbacks for cavity temperature, meat probe, setpoint; hood
  `default_program`.
- `refrigeration.py`: Fridge door-assistant switch/select/number entities.
- `fan.py`: `turn_on`, program-based speed control, `DELETE` turn-off.

## Production deploy (Bowman Mtn, 2026-06-22)

Deployed fork branch `fix/thermador-us-appliances` to
`/home/ntableman/docker/ha/config/custom_components/homeconnect_ws`.
Backup: `homeconnect_ws.bak-20260622-110851`.

| Metric | Before | After |
|--------|--------|-------|
| `homeconnect_ws` entity count | 84 | 92 |

New entities confirmed in `core.entity_registry`:

- `sensor.kitchen_thermador_oven_current_temperature` (cavity °F)
- `sensor.kitchen_thermador_oven_current_meatprobe_temperature`
- `number.kitchen_thermador_oven_setpoint_temperature` (°F option)
- Fridge door-assistant switch/select/number (entity_id suffixes truncated by HA naming — see registry unique_ids `*assistant_fridge*`)

Upstream PR: https://github.com/chris-mc1/homeconnect_local_hass/pull/408

## Verification commands (production)

```bash
# Entity count
docker exec home-assistant python3 -c "
import json
er=json.load(open('/config/.storage/core.entity_registry'))
hc=[e for e in er['data']['entities'] if e.get('platform')=='homeconnect_ws']
print(len(hc))
for e in sorted(hc, key=lambda x: x['entity_id']):
    if any(k in e['entity_id'] for k in ['current_temperature','meatprobe','setpoint','assistant']):
        print(e['entity_id'])
"

# Oven Fahrenheit API keys on LAN profile
docker exec home-assistant python3 -c "
import json
ce=json.load(open('/config/.storage/core.config_entries'))
for e in ce['data']['entries']:
    if 'Oven' in e.get('title',''):
        for s in e['data']['description'].get('status',[])+e['data']['description'].get('option',[]):
            if 'Temperature' in s.get('name','') and s.get('available'):
                print(s['name'])
"
```

## PR checklist

- [x] `pytest` — 84 passed (Python 3.14 / HA 2026.5 container)
- [x] Deploy + reload on Bowman Mtn HA; entity count 84 → 92
- [x] Oven cavity temp + setpoint + meat-probe entities in registry
- [x] Fridge door-assistant entities in registry
- [ ] Attach full config-entry diagnostics export to upstream PR (UI download)
- [ ] Live hood fan on/off/speed UI test
