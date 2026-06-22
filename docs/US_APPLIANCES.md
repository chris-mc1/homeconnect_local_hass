# US appliance notes (Home Connect local API)

Verified against Thermador LAN profiles (US, °F-only).

## Oven / fridge temperatures

US profiles expose `*Fahrenheit` keys (e.g. `CurrentTemperatureFahrenheit`,
`SetpointTemperatureFahrenheit`) instead of Celsius entity names. Mappings must
include both suffixes.

## Hood fan (e.g. HMWB361WS)

- Speed is controlled via the venting program option `VentingLevel` (FanOff=0,
  FanStage01–04).
- Clearing active program with `POST program: 0` returns `UnknownUID` on tested
  hoods; stop by setting VentingLevel to FanOff on the active venting program.
- `is_on` should treat `active_program is None` as off (VentingLevel can be
  stale briefly after program end).
- Hood power switch can return 400 while venting; fan entity is the control path.

## Hood DelayedShutOffStage

Enum includes FanOff (0) but appliance `min=1`. Select options must respect
entity min/max or `InvalidUIDValue` is returned.
