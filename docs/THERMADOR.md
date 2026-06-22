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

## Verification commands (production)

```bash
# Oven API keys present locally
docker exec home-assistant python3 -c "
import json
ce=json.load(open('/config/.storage/core.config_entries'))
for e in ce['data']['entries']:
    if 'Oven' in e.get('title',''):
        desc=e['data']['description']
        for s in desc.get('status',[])+desc.get('option',[]):
            if 'Temperature' in s.get('name','') and s.get('available'):
                print(s['name'])
"

# Entity count after deploying fork build
docker exec home-assistant python3 -c "
import json
er=json.load(open('/config/.storage/core.entity_registry'))
print(len([e for e in er['data']['entities'] if e.get('platform')=='homeconnect_ws']))
"
```

## PR checklist

- [ ] Attach config-entry diagnostics for all three appliances
- [ ] `pytest` passes
- [ ] Reload integration on HA test host; confirm cavity temp + fridge door-assistant entities appear
