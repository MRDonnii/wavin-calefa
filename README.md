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

### Setting it up

1. Go to **Settings > Devices & services > Wavin Calefa > Configure**.
2. Choose **Heat call (optional Sentio emulation)**.
3. Enable it, pick the thermostats to monitor, and optionally pick AC/cooling entities that should suppress demand while actively cooling.
4. Adjust the hysteresis, debounce, summer-stop values, RUM target, and the safety time limit if the defaults don't suit your installation.

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
