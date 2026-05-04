<p align="center">
	<img src="brand/logo.svg" alt="Wavin Calefa logo" width="180" />
</p>

<h1 align="center">Wavin Calefa</h1>

<p align="center">
	Local Home Assistant integration for Wavin Calefa 2 and Sentio via Modbus TCP.<br>
	Fast overview, operational status, fault indicators, and data for smarter heating control.
</p>

<p align="center">
	<a href="https://github.com/hacs/integration"><img src="https://img.shields.io/badge/HACS-Custom-orange.svg" alt="HACS"></a>
	<a href="https://github.com/MRDonnii/wavin-calefa/releases"><img src="https://img.shields.io/github/release/MRDonnii/wavin-calefa.svg" alt="GitHub Release"></a>
	<a href="https://www.home-assistant.io/"><img src="https://img.shields.io/badge/HA-2024.8%2B-blue.svg" alt="HA Min Version"></a>
	<img src="https://img.shields.io/badge/Local-No%20Cloud-success" alt="Local Only">
</p>

---

## What This Integration Is For

The Wavin Calefa integration exposes your district heating unit in Home Assistant with a focus on everyday operations:

- Temperatures, pressure, valves, and flow in both DHW and heating circuits
- Diagnostics and alarm states as binary sensors
- Data for dashboards, automations, and notifications
- Fully local polling with no cloud account required

In short: you get a clear view of whether your system is running normally, and when action is needed.

---

## Highlights

- Automatic port detection (including 10223 and 502)
- 42 sensors and 21 binary sensors
- Danish, English, or Auto language mode (follows HA language)
- HACS-ready installation
- Designed for Calefa 2 and Sentio setups

---

## Supported Hardware

| Device | Status |
|---|---|
| Wavin Calefa 2 with Sentio controller | Tested |
| DHW-201 Calefa | Expected to work |

---

## Installation

### HACS (recommended)

1. Open HACS and go to Integrations
2. Open the three-dot menu and choose Custom repositories
3. Add this repository URL as type Integration:
	 https://github.com/MRDonnii/wavin-calefa
4. Search for Wavin Calefa and install
5. Restart Home Assistant

### Manual installation

1. Copy custom_components/wavin_calefa into your HA config under custom_components
2. Restart Home Assistant

---

## Configuration

Add the integration via:

Settings -> Devices & Services -> Add Integration -> Wavin Calefa

| Field | Description | Default |
|---|---|---|
| Name | Friendly name in Home Assistant | Wavin Calefa |
| IP address | Local IP of the Calefa/Sentio unit | None |
| Sensor language | Auto, Danish, or English | Auto |
| Port | Modbus TCP port, 0 means auto-scan | 0 |
| Modbus unit ID | Usually 1 | 1 |
| Scan interval | Polling interval in seconds | 30 |

All settings can be changed later via Options on the integration card.

---

## What You Get In Home Assistant

### Operational sensors

Examples of core sensors:

- DHW status, bypass, mode, and regulator state
- District heating supply, return, and cooling delta
- Heating circuit state, desired supply, and return
- System pressure and valve positions

### Faults and warnings

Binary sensors with device class problem show active fault state, for example:

- Pressure and flow faults
- Sensor faults on DHW, district heating, and heating circuits
- Motor faults and frost protection states

---

## Important Notes

- Some sensors may be unavailable on units where physical probes are not installed
- Sentio uses special value 0x7FFF for missing measurements; this integration converts it to unavailable instead of showing false temperatures
- Energy and power estimates are informative only, not billing-grade metering

---

## Quick Troubleshooting

1. Verify IP address and Modbus TCP connectivity
2. Use Port 0 to let the integration auto-detect the correct port
3. Verify Unit ID (normally 1)
4. If specific sensors are unavailable, they may be unsupported or physically not connected

---

## Version 0.2.1

This release includes a major mapping cleanup against the official register specification:

- Corrected register mappings across DHW and CH/HC areas
- More diagnostic and operational sensors
- More binary sensors for faults and warnings
- Improved INVALID_VALUE handling
- Improved language support (DA, EN, Auto)

---

## Links

- Documentation and source: https://github.com/MRDonnii/wavin-calefa
- Releases: https://github.com/MRDonnii/wavin-calefa/releases
- Issues: https://github.com/MRDonnii/wavin-calefa/issues