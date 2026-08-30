# Changelog

All notable changes to Wavin Calefa are documented in this file.

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
