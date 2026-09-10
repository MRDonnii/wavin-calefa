# Changelog

All notable changes to Wavin Calefa are documented in this file.

## [0.7.4] - 2026-09-10

### Added

- Sensor-only rooms can now use an `input_number` entity as their target
  instead of a fixed number. Target changes are watched live and fail safe if
  the helper becomes unavailable, allowing house modes to change bathroom
  targets without reloading the integration.

## [0.7.3] - 2026-09-10

### Fixed

- Pump-stop confirmation now allows up to five minutes of normal Calefa pump
  overrun before reporting a fault. This avoids the brief false pump-stop fault
  seen when the pump stopped just after the previous retry window expired.

### Changed

- When every configured room is warm and the pump call, physical pump, and CVV
  valve are already stopped, automatic standby engages immediately. The normal
  warm-room delay still applies while the heating circuit is winding down.

## [0.7.2] - 2026-09-10

### Fixed

- A valid radiator heat request now releases Calefa standby immediately,
  including when the room is below target but still inside the configured
  hysteresis band. The legacy restart delay can no longer strand a request in
  standby for up to 30 minutes.
- Valve-only demand configurations are now accepted and count as real demand
  sources.
- A configured valve entity that is missing or unavailable now fails safe by
  releasing automatically owned standby instead of being ignored.
- A stale or restored standby without saved automation ownership is released
  whenever valid heat demand is present.

### Changed

- Automatic standby follows a strict safety rule: valid heat demand always
  wins. Turn Auto Standby off before deliberately placing the Calefa unit in
  service standby.

## [0.7.1] - 2026-09-02

### Fixed

- Upgrading from 0.4.0-0.6.1 with heat call previously engaged could leave the unit's RUM temporary-room override permanently on: the only code that ever released it was removed along with the feature in 0.7.0, so nothing turned it back off, and the CVV valve stayed driven fully open even with every room satisfied - not new demand, just a stale command from before the update. A one-time migration now releases it automatically on upgrade (best-effort - if the unit isn't reachable during migration, the log names the "RUM Midl. mode" switch to turn off by hand). The now-unused `heat_call_enabled`, `heat_call_room_target_temperature`, `heat_call_max_duration_minutes`, `heat_call_summer_stop_normal`, and `heat_call_summer_stop_override` keys are also dropped from the config entry's stored options as part of the same migration.

## [0.7.0] - 2026-09-02

### Removed

- The optional "heat call" (Sentio emulation) feature, added in 0.4.0: on real demand it forced Calefa's RUM temporary-room override open with a configurable target temperature, as a stand-in for a physical Sentio room controller. In practice Calefa has no live per-room reading to modulate the CVV valve against once the override is engaged, so it always drove the valve fully open regardless of how small the actual deficit was - correct in that it reliably got heat moving, but blunt enough to measurably hurt afkoling for no proportionate benefit, and it could not be tuned away by lowering the override target. Removed rather than left in for others to hit the same ceiling. Its entities are gone: the "Heat call" switch, "Heat call status" sensor, and the "Heat call in progress" / "Heat call fault" / "Heat call data valid" / "Summer stop blocking" binary sensors.
- The `heat_call_enabled`, `heat_call_room_target_temperature`, `heat_call_max_duration_minutes`, `heat_call_summer_stop_normal`, and `heat_call_summer_stop_override` options, along with the RUM-override Modbus registers they drove. Any stored values for these on an existing config entry are simply no longer read.

### Changed

- The demand-detection engine (thermostats, sensor-only rooms, valve/actuator entities, hysteresis) that heat call used is kept, since automatic standby depends on it for its own demand signal - it just no longer drives anything by itself. Internally this moved from `heat_call.py`'s `WavinCalefaHeatCallManager` to `demand.py`'s `WavinCalefaDemandTracker`, a much smaller class with no Modbus writes, no listeners, and no setup/teardown of its own. The `heat_call_climate_entities`, `heat_call_ac_entities`, `heat_call_sensor_rooms`, `heat_call_valve_entities`, `heat_call_valve_threshold`, `heat_call_hysteresis`, and `heat_call_restart_delay_minutes` options keep their existing string keys and values, so existing installations don't lose their configured rooms on upgrade - only the Python-side names changed.
- Automatic standby no longer needs to special-case a heat call being active before engaging standby, since there's nothing left that could be active.

## [0.6.1] - 2026-09-01

### Fixed

- Automatic standby now waits for all configured demand conditions, including binary ON/OFF sources such as Dantherm afterheat, before stopping the Calefa unit.
- Pump-stop confirmation allows the Calefa pump's normal run-on time, still reports a genuinely stuck pump, and clears a latched fault when the pump subsequently stops safely.
- Heat-call and standby diagnostics now fail safe while thermostat data is unavailable and recover automatically when valid data returns.

### Changed

- Demand-source selection accepts both percentage sensors and binary sensors, allowing a verified afterheat-active signal to replace an unreliable inferred valve percentage.

## [0.6.0] - 2026-08-30

### Added

- Optional automatic-standby feature: puts the whole Calefa unit into standby once every configured heat-call demand source (thermostats, sensor-rooms, valve entities) is warm enough for long enough, and releases it again the moment real demand returns or data becomes invalid. Shares heat call's configured demand sources instead of asking for them twice, and works independently of whether heat call itself is enabled. Before engaging standby it confirms the unit's own pump call, pump status, and CVV valve position have actually settled, retrying a few times before reporting a fault rather than holding an unconfirmed standby indefinitely. A manually released standby is always respected.

### Changed

- Heat call and automatic standby are now coordinated so they can't work against each other: heat call no longer starts a call while automatic standby has the unit blocked, and automatic standby never engages standby while a heat call is active. Heat call also now reacts to coordinator updates directly, instead of only entity-state changes and its own 30-minute timer, so it notices a released standby promptly.

## [0.5.0] - 2026-08-30

### Added

- Heat call now supports two more demand sources besides thermostats: sensor-only rooms (`entity_id:target_temperature` pairs, for spaces like floor heating with no thermostat) and valve/actuator entities (opening-percentage threshold, for sources like a ventilation unit's after-heater with no temperature-vs-target concept). Valve entities are treated as best-effort and never block demand detection for everything else if unavailable.

### Fixed

- The configured restart delay was defined but never actually applied before starting a first heat call - any demand blip, however brief, started one immediately. Demand now has to hold for the configured delay before the first call starts, so a temporary dip (e.g. a window aired out) doesn't trigger anything.

## [0.4.1] - 2026-08-30

### Fixed

- Heat call options (enable, thermostats, thresholds) were silently discarded on save: the options flow manually applied `entry.options` and then returned an empty `data={}` from `async_create_entry`, which the flow manager immediately re-applied on top, wiping the real values. The flow now returns the real options for the manager to apply, and a config-entry update listener handles the reload afterward instead of reloading from inside the flow (which would have picked up the pre-update options).
- The options flow is now one combined form instead of a menu with separate steps, for more reliable submission from automation/scripting clients as well as the UI.

## [0.4.0] - 2026-08-30

### Added

- Optional heat-call (Sentio emulation) feature: use existing HA thermostats to signal room heat demand on installations with no physical Sentio room controller
- New options-flow step to select thermostats, optional AC/cooling entities, hysteresis, debounce, summer-stop values, RUM target temperature, and a safety time limit
- New entities: heat call enable switch, status sensor, in-progress/fault/data-valid binary sensors, and a summer-stop-blocking diagnostic binary sensor
- The feature only ever raises summer-stop when it's actually blocking heat right now (compared against live outdoor temperature), and always reverts on lost demand, invalid data, or being turned off

### Changed

- Writable-control entities now reflect a verified write immediately instead of waiting for the next full register scan; a complete refresh still runs in the background to reconcile everything else

## [0.3.1] - 2026-07-13

### Fixed

- Restored the writable Eco, Comfort, and Extra comfort room-temperature entities that were missing from the 0.3.0 package
- Localized selectable values for Danish installations, including room profiles, heat-curve types, return-limiter modes, and domestic-hot-water modes
- Prevented blank room-temperature controls after updating through HACS

## [0.3.0] - 2026-07-13

### Added

- Verified Modbus writes with readback, serialized access, and rollback for multi-register changes
- Heating controls for standby, vacation, heat-curve type, manual slope, parallel shift, supply limits, and summer shutdown
- Return-limiter mode, temperature, gain, and priority controls
- Room comfort profiles, schedule control, and temporary temperature override with duration
- Domestic-hot-water mode, setpoint, bypass, circulation, and vacation controls
- Separate Home Assistant device groups for system, heating, room, and domestic hot water
- Local brand icon and logo assets
- Danish names for all new control entities

### Changed

- Expanded the integration from read-only monitoring to verified read/write control
- Increased the maximum heat-curve supply setting to 65 °C
- Improved compact entity names so controls fit better in the Home Assistant interface

## [0.2.2] - 2026-05-04

### Added

- Calculated radiator supply/return temperature difference for the active CVV/ITC circuit

### Changed

- Unsupported HC/CH temperature sensors are hidden instead of remaining unavailable
- Legacy unavailable sensor entities are cleaned up on integration reload

## [0.2.0]

### Changed

- Corrected register mappings across domestic-hot-water and heating circuits
- Expanded diagnostics, operational sensors, and binary fault sensors
- Improved missing-value handling and Danish/English language support

[0.3.1]: https://github.com/MRDonnii/wavin-calefa/compare/v0.3.0...v0.3.1
[0.3.0]: https://github.com/MRDonnii/wavin-calefa/compare/v0.2.2...v0.3.0
[0.2.2]: https://github.com/MRDonnii/wavin-calefa/compare/v0.2.1...v0.2.2
[0.2.0]: https://github.com/MRDonnii/wavin-calefa/releases/tag/v0.2.0
