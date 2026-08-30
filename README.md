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
- 44 operational and diagnostic sensors
- 21 fault and warning binary sensors
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

## Optional: heat call (Sentio emulation)

Some Calefa installations have no physical Sentio room controller attached. Without one, the unit never receives a genuine room heat-call signal, so space heating stays gated by the unit's own summer-stop threshold with nothing to release it.

Since 0.4.0, the integration can use a set of your existing Home Assistant thermostats (`climate` entities) as a stand-in for that missing controller. When they show real, sustained heat demand, it:

1. Temporarily raises Calefa's own summer-stop threshold - but **only** when the threshold is actually the thing blocking heat right now (compared against the live outdoor temperature); otherwise it's left alone entirely.
2. Engages the unit's RUM temporary-room override with a configurable target temperature.

Both are the same two settings a real Sentio controller's demand would otherwise release - nothing about Calefa's own regulation, safety limits, or blocking logic is bypassed or written around. Everything reverts automatically the moment demand clears, the thermostats' data becomes invalid or unavailable, or the feature is turned off, and a hard safety limit force-restarts the call if it's ever held longer than expected.

Three kinds of demand source can be combined:

- **Thermostats** (`climate` entities) - compared against their own current/target temperature.
- **Sensor-only rooms** - for spaces with no thermostat at all (e.g. floor heating on a plain sensor): one `entity_id:target_temperature` per line, compared against a plain temperature sensor's state with the same hysteresis as the thermostats.
- **Valve/actuator entities** - for demand sources with no temperature-vs-target concept, such as a ventilation unit's water-coil after-heater: demand is signalled by the reported opening percentage crossing a configurable threshold. These are treated as best-effort - an unavailable valve sensor never blocks demand detection for everything else.

A demand source has to hold steady for the configured delay (default 2 minutes) before a call starts the first time, so a brief dip - a window aired out in a sensor-only room, for instance - doesn't itself trigger anything.

### Setting it up

1. Go to **Settings > Devices & services > Wavin Calefa > Configure**.
2. Enable heat call, pick the thermostats to monitor, and optionally pick AC/cooling entities that should suppress demand while actively cooling.
3. Optionally add sensor-only rooms (one `entity_id:target_temperature` per line) and valve/actuator entities for demand sources with no thermostat.
4. Adjust the hysteresis, debounce, summer-stop values, RUM target, valve threshold, and the safety time limit if the defaults don't suit your installation.

This adds a few new entities under the Calefa device:

| Entity | Purpose |
|---|---|
| Heat call (switch) | Pause or resume the feature at any time, independent of the setup above |
| Heat call status (sensor) | Human-readable current state |
| Heat call in progress (binary sensor) | On while an override is being held active |
| Heat call fault (binary sensor) | On if Calefa hasn't responded to an active call for 20 minutes |
| Heat call data valid (binary sensor, diagnostic) | On while the configured thermostats report usable data |
| Summer stop blocking (binary sensor, diagnostic) | On when summer-stop is what's currently blocking heat |

> [!NOTE]
> This reproduces the *effect* of a Sentio controller's demand signal by using the same writable settings a real one relies on - it does not emulate Sentio's own communication protocol. If you have (or add) a real Sentio room controller, prefer that; this feature is meant for installations that don't have one.

## Optional: automatic standby

A separate, independent feature from heat call: instead of raising summer-stop, it puts the **whole Calefa unit into standby** once every configured thermostat/sensor-room/valve is warm enough for long enough, and releases it again the moment real demand returns or the data becomes invalid. It shares heat call's configured demand sources (so nothing has to be set up twice) but works whether or not heat call itself is enabled - useful, for example, if a physical Sentio controller already handles summer-stop and RUM, but the unit should still power down between heating cycles.

Before actually engaging standby, and again after, it confirms the unit's own pump call, pump status, and CVV valve position have genuinely settled - retrying a few times before reporting a fault rather than holding an unconfirmed standby indefinitely. If standby is ever released manually (or by something else), that's always respected; the feature only ever acts on standby it engaged itself.

The two features are coordinated so they can't work against each other: heat call never starts a call while automatic standby has the unit blocked, and automatic standby never engages standby while a heat call is active.

### Setting it up

1. Go to **Settings > Devices & services > Wavin Calefa > Configure**.
2. Configure at least one thermostat or sensor-only room under heat call above (automatic standby needs that as its demand signal, even with heat call itself left disabled).
3. Enable automatic standby and adjust how long everything must stay warm before it engages, if the default doesn't suit your installation.

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
