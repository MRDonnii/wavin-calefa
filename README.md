<p align="center">
  <img src="custom_components/wavin_calefa/brand/logo.png" alt="Wavin Calefa logo" width="300">
</p>

<h1 align="center">Wavin Calefa</h1>

<p align="center">
  Local Home Assistant integration for Wavin Calefa 2 and Sentio over Modbus TCP.
</p>

<p align="center">
  <a href="https://github.com/MRDonnii/wavin-calefa/releases"><img src="https://img.shields.io/github/v/release/MRDonnii/wavin-calefa" alt="Latest release"></a>
  <a href="https://github.com/hacs/integration"><img src="https://img.shields.io/badge/HACS-Custom-orange.svg" alt="HACS custom repository"></a>
  <a href="https://www.home-assistant.io/"><img src="https://img.shields.io/badge/Home%20Assistant-2024.8%2B-41BDF5" alt="Home Assistant 2024.8 or newer"></a>
  <img src="https://img.shields.io/badge/Cloud-Not%20required-success" alt="No cloud required">
</p>

## Features

- Fully local Modbus TCP communication with automatic port detection
- 43 operational and diagnostic sensors
- 17 fault and warning binary sensors
- 23 verified writable controls with direct readback
- Danish and English entity presentation
- Separate Home Assistant devices for system, heating, room control, and domestic hot water
- Local icon and logo assets for Home Assistant 2026.3 and newer

## Writable controls in 0.3.1

### Heating and heat curve

- Standby and vacation mode
- Vacation for central heating
- Heat-curve type: manual, floor heating, or radiator, localized for Danish installations
- Manual slope
- Parallel shift
- Minimum and maximum supply temperature
- Summer shutdown temperature
- Return-limiter mode, maximum return temperature, gain, and priority

### Room control

- Eco, comfort, and extra-comfort temperatures
- Active comfort profile with localized selectable values
- Schedule on or off
- Temporary temperature, duration, and mode

### Domestic hot water

- Operating mode
- Hot-water setpoint
- Bypass temperature
- Circulation temperature
- Vacation for domestic hot water

All writes are serialized and checked by reading the value back from the Calefa unit. Multi-register changes are rolled back if verification fails.

> [!CAUTION]
> Writable entities change the heating unit itself. Use values suitable for your installation. Available registers can vary by Calefa/Sentio model and firmware.

> [!NOTE]
> Versions 0.4.0-0.6.1 included an optional "heat call" feature that used a set of HA thermostats to force Calefa's RUM temporary-room override open when they showed demand, as a stand-in for a physical Sentio room controller. It has been removed as of 0.7.0: Calefa has no live per-room reading to modulate the CVV valve against, so engaging the override always drove it fully open regardless of how small the real deficit was - blunt, and hard on afkoling for no proportionate benefit. See CHANGELOG for details. The demand sources below still exist, purely to feed automatic standby.

## Optional: automatic standby

Puts the **whole Calefa unit into standby** once every configured thermostat/sensor-room/valve is warm enough for long enough, and releases it again the moment real demand returns or the data becomes invalid.

Three kinds of demand source can be combined:

- **Thermostats** (`climate` entities) - compared against their own current/target temperature.
- **Sensor-only rooms** - for spaces with no thermostat at all (e.g. floor heating on a plain sensor): one `sensor_entity:target` per line. The target can be a fixed temperature or an `input_number` entity, allowing a house/vacation mode to change the target live.
- **Valve/actuator entities** - for demand sources with no temperature-vs-target concept, such as a ventilation unit's water-coil after-heater: demand is signalled by the reported opening percentage crossing a configurable threshold. These are treated as best-effort - an unavailable valve sensor never blocks demand detection for everything else.

These sources are only ever read - nothing about Calefa's own regulation is written to or bypassed.

Before actually engaging standby, and again after, it confirms the unit's own pump call, pump status, and CVV valve position have genuinely settled - retrying a few times before reporting a fault rather than holding an unconfirmed standby indefinitely. If standby is ever released manually (or by something else), that's always respected; the feature only ever acts on standby it engaged itself.

### Setting it up

1. Go to **Settings > Devices & services > Wavin Calefa > Configure**.
2. Configure at least one thermostat or sensor-only room as a demand source (automatic standby needs that as its demand signal), and optionally pick AC/cooling entities that should suppress demand while actively cooling.
3. Optionally add sensor-only rooms (one `sensor_entity:target` per line, for example `sensor.bathroom_temperature:input_number.bathroom_target`) and valve/actuator entities for demand sources with no thermostat.
4. Enable automatic standby and adjust the hysteresis, debounce, and how long everything must stay warm before it engages, if the defaults don't suit your installation.

This adds a few more entities under the Calefa device:

| Entity | Purpose |
|---|---|
| Automatic standby (switch) | Pause or resume the feature at any time, independent of the setup above |
| Automatic standby status (sensor) | Human-readable current state |
| Automatic standby active (binary sensor) | On while standby is being held by the automation |
| Automatic standby fault (binary sensor) | On if the pump stop couldn't be confirmed after standby was engaged |
| Automatic standby data valid (binary sensor, diagnostic) | On while the configured demand sources report usable data |
| All rooms warm enough (binary sensor, diagnostic) | On while every configured room is warm enough to allow standby |

## Installation with HACS

1. Open HACS and select **Integrations**.
2. Open the menu and select **Custom repositories**.
3. Add `https://github.com/MRDonnii/wavin-calefa` as an **Integration**.
4. Open **Wavin Calefa**, select **Download**, and restart Home Assistant.
5. Go to **Settings > Devices & services > Add integration**, then search for **Wavin Calefa**.

[![Open your Home Assistant instance and add this repository to HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=MRDonnii&repository=wavin-calefa&category=integration)

## Manual installation

Copy `custom_components/wavin_calefa` to the `custom_components` directory in your Home Assistant configuration, then restart Home Assistant.

## Configuration

| Setting | Description | Default |
|---|---|---|
| Name | Name shown in Home Assistant | Wavin Calefa |
| Host | Local address of the Calefa/Sentio unit | Required |
| Language | Auto, Danish, or English | Auto |
| Port | `0` scans supported Modbus TCP ports automatically | 0 |
| Unit ID | Modbus unit identifier | 1 |
| Scan interval | Seconds between updates | 30 |

The options can be changed later from the integration card.

## Supported hardware

| Device | Status |
|---|---|
| Wavin Calefa 2 with Sentio controller | Tested |
| DHW-201 Calefa | Expected to work |

Some entities can be unavailable when a sensor or feature is not installed on the unit. The integration converts the documented `0x7FFF` missing-value marker to unavailable instead of showing an incorrect measurement.

## Troubleshooting

- Confirm that Home Assistant can reach the Calefa unit over the local network.
- Leave the port at `0` to use automatic detection, or enter the known Modbus TCP port.
- Confirm that the Unit ID is correct, normally `1`.
- After installing or updating through HACS, restart Home Assistant.
- If only individual entities are unavailable, the corresponding hardware feature may not be present.

## Release history

See [CHANGELOG.md](CHANGELOG.md) for all release notes.

## Links

- [Releases](https://github.com/MRDonnii/wavin-calefa/releases)
- [Issues](https://github.com/MRDonnii/wavin-calefa/issues)
