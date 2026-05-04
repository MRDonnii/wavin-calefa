# Wavin Calefa

[![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/release/MRDonnii/wavin-calefa.svg)](https://github.com/MRDonnii/wavin-calefa/releases)
[![HA min version](https://img.shields.io/badge/HA-2024.8%2B-blue.svg)](https://www.home-assistant.io/)

Home Assistant custom integration for **Wavin Calefa 2** and **Sentio** district heating heat exchanger controllers, using local Modbus TCP — no cloud, no account.

## Supported hardware

| Model | Status |
|---|---|
| Wavin Calefa 2 with Sentio controller | ✅ Tested |
| DHW-201 Calefa | Should work |

## Features

- **Automatic port detection** — scans common Modbus TCP ports (10223, 502, …) automatically
- **42 sensors** — temperatures, pressures, flows, valve positions, and operational states for DHW and heating circuits
- **21 binary sensors** — warnings, errors, and fault indicators
- **Language selection** — sensor names in Danish (`da`), English (`en`), or Auto (follows HA language)
- **Local polling only** — no cloud dependency, no account required
- **HACS compatible**

---

## Installation

### Via HACS (recommended)

1. Open **HACS → Integrations**
2. Click the three-dot menu → **Custom repositories**
3. Add `https://github.com/MRDonnii/wavin-calefa` as type **Integration**
4. Search for **Wavin Calefa** and install
5. Restart Home Assistant

### Manual

1. Copy `custom_components/wavin_calefa/` into your HA `config/custom_components/` folder
2. Restart Home Assistant

---

## Configuration

Go to **Settings → Devices & Services → Add Integration** and search for **Wavin Calefa**.

| Field | Description | Default |
|---|---|---|
| Name | Friendly name | Wavin Calefa |
| IP address | Local IP of the Calefa/Sentio unit | — |
| Sensor language | Auto / Dansk / English | Auto |
| Port | Modbus TCP port (0 = auto-scan) | 0 |
| Modbus unit ID | Usually 1 | 1 |
| Scan interval (s) | Poll interval | 30 |

All settings can be changed later via **Options** on the integration card.

---

## Sensors

### Main sensors

| Key | English name | Danish name | Unit | Notes |
|---|---|---|---|---|
| `dhw_state` | DHW status | BVV status | — | Standby / Heating / Bypass / Purge / Suspended |
| `dhw_bypass_active` | DHW bypass | BVV bypass | — | On / Off |
| `dhw_blocking_source` | DHW blocked by | BVV blokeret af | — | None / CH / Standby / Holiday |
| `dhw_out_temperature` | Hot water outlet (HW) | Varmt vand ud (BV) | °C | |
| `dcw_sensor_temperature` | Cold water inlet (CW) | Koldt vand ind (KV) | °C | |
| `domestic_cold_water_flow` | Hot water flow (FLW) | Varmtvandsflow (FLW) | L/h | |
| `outdoor_temperature` | Outdoor temperature (OT) | Udetemperatur (UT) | °C | |
| `source_inlet_temperature` | District heating supply (DHS) | Fjernvarme fremløb (FJF) | °C | |
| `source_return_temperature` | District heating return (DHR) | Fjernvarme retur (FJR) | °C | |
| `source_delta_temperature` | District heating cooling | Fjernvarme afkøling | °C | Calculated: inlet − return |
| `cvv_supply_temperature` | Heating supply (ITC) | CVV fremløb | °C | |
| `cvv_desired_supply_temperature` | Heating desired supply (ITC) | CVV ønsket fremløb | °C | |
| `cvv_return_temperature` | Heating return (ITC) | CVV retur | °C | |
| `system_pressure` | System pressure | Anlægstryk | bar | Register 7310 |
| `valve_position` | DHW valve position | Varmtvandsventil (BVV) | % | |
| `cvv_valve_position` | Heating valve position (CH) | Radiatorventil (CVV) | % | |
| `dhw_power_estimate` | Hot water power estimate | Varmtvand effekt estimat | kW | Calculated — not a billing meter |
| `dhw_energy_estimate` | Hot water energy estimate | Varmtvand energi estimat | kWh | Accumulated — not a billing meter |

### Diagnostic sensors

| Key | English name | Danish name | Unit |
|---|---|---|---|
| `itc_pump_demand` | Heating pump demand (ITC) | CVV pumpe kald | — |
| `itc_pump_status` | Heating pump status (ITC) | CVV pumpe status | — |
| `dhw_control_mode` | DHW control mode | BVV styre-mode | — |
| `dhw_regulator_state` | DHW regulator state | BVV regulator tilstand | — |
| `dhw_motor_stall_level` | DHW motor stall level | BVV motor stall niveau | mV |
| `ch_state` | Heating state (CH) | Varmekreds status (CH) | — |
| `ch_blocking_source` | Heating blocked by (CH) | Varmekreds blokeret af (CH) | — |
| `ch_regulator_state` | Heating regulator state (CH) | Varme regulator tilstand (CH) | — |
| `ch_desired_inlet_temperature` | Heating desired inlet (CH) | Varme ønsket indløb (CH) | °C |
| `hc_supply_temperature` | Heating supply (HC) | Varme fremløb (HC) | °C |
| `hc_return_temperature` | Heating return (HC) | Varme retur (HC) | °C |
| `itc_max_outdoor_temp` | ITC max outdoor temperature | ITC max udetemperatur | °C |
| `dhw_temperature_setpoint` | DHW temperature setpoint | BVV temperatur setpunkt | °C |
| `dhw_bypass_temperature` | DHW bypass temperature | BVV bypass temperatur | °C |
| `circulation_temperature` | Circulation temperature | Cirkulation temperatur | °C |
| `circulation_state` | Circulation status | Cirkulation status | — |
| `dhw_boost_state` | Boost pump status | Boostpumpe status | — |
| `boost_pump_mode` | Boost pump mode | Boostpumpe tilstand | — |
| `flow_sensor_type` | Flow sensor type | Flowmåler type | — |
| `dhw_mode` | DHW mode | BVV mode | — |
| `documented_secondary_pressure` | Documented secondary pressure | Dokumenteret sekundærtryk | bar |
| `device_type` | Device type | Enhedstype | — |
| `hardware_version` | Hardware version | Hardwareversion | — |
| `software_version` | Software version | Softwareversion | — |

> **Note:** `hc_supply_temperature` and `hc_return_temperature` show as unavailable if those sensors are not physically connected (Sentio returns the special INVALID\_VALUE 0x7FFF = 327.67 °C for missing sensors, which is converted to unavailable).

---

## Binary sensors (problems / alarms)

All binary sensors use the `problem` device class — **on** means the problem is active.

| Key | English name | Danish name |
|---|---|---|
| `warning_low_energy` | Low energy warning | Lav energi advarsel |
| `error_dhw_temperature_high` | DHW temperature high | Brugsvand temperatur høj |
| `dhw_motor_failure` | DHW motor failure | BVV motorfejl |
| `dhi_sensor_failure` | District heating supply sensor failure | Fjernvarme fremløbsføler fejl |
| `dho_sensor_failure` | District heating return sensor failure | Fjernvarme returføler fejl |
| `dhw_sensor_failure` | DHW sensor failure | Brugsvandsføler fejl |
| `dcw_sensor_failure` | Cold water sensor failure | Koldtvandsføler fejl |
| `warning_pressure_high` | High pressure warning | Tryk høj advarsel |
| `warning_pressure_low` | Low pressure warning | Tryk lav advarsel |
| `error_pressure_critical_low` | Critical low pressure | Tryk kritisk lav fejl |
| `no_secondary_pressure` | No secondary pressure | Intet sekundærtryk |
| `pressure_sensor_failure` | Pressure sensor failure | Tryksensor fejl |
| `flow_sensor_failure` | Flow sensor failure | Flowsensor fejl |
| `dhi_frost_protection` | District heating frost protection | Fjernvarme frostbeskyttelse |
| `dhw_motor_stuck` | DHW motor stuck | BVV motor blokeret |
| `itc_hs_sensor_failure` | Heating supply sensor failure (ITC) | CVV fremløbsføler fejl |
| `itc_hr_sensor_failure` | Heating return sensor failure (ITC) | CVV returføler fejl |
| `outdoor_sensor_failure` | Outdoor sensor failure | Udetemperaturføler fejl |
| `itc_motor_failure` | Heating valve motor failure (ITC) | CVV ventilmotor fejl |
| `itc_htco_error` | HTCO error (ITC) | HTCO fejl (ITC) |
| `itc_hs_frost_protection` | Heating frost protection (ITC) | Varme frostbeskyttelse (ITC) |

---

## Changelog

### v0.2.0 — 2026-05-04

Major update: extensive register-map corrections based on the official DHW-21x Modbus specification (TV414 v11), 10+ new sensors, 16 new binary sensors, Danish language support, and INVALID\_VALUE handling.

**Register map corrections:**
- `dhw_control_mode` (IR 6512): was incorrectly mapped to boost pump state — now correctly reads DHW controller mode
- `dhw_regulator_state` (IR 6513): new sensor, replaced incorrect discrete-input mapping
- `dhw_motor_stall_level` (IR 6514): new sensor
- `dhw_boost_state` (IR 6515): new sensor for boost pump on/off
- `boost_pump_mode` (HR 6531): corrected register address
- `flow_sensor_type` (HR 6527): corrected to holding register
- Removed incorrect flow registers 7306/7307 (CVV flow / source flow — not on Sentio)
- Removed incorrect holding registers H32 and H43
- `dhw_bypass_active` now correctly derived from `dhw_state == 2` (Bypass)

**New sensors (CH/HC circuit — IR 7301–7309):**
- `ch_state`, `ch_blocking_source`, `ch_regulator_state`, `ch_desired_inlet_temperature`
- `hc_supply_temperature`, `hc_return_temperature`
- `dhw_control_mode`, `dhw_regulator_state`, `dhw_motor_stall_level`, `dhw_boost_state`

**New binary sensors (16 added):**
- DHW: `dhw_motor_failure`, `dhi_sensor_failure`, `dho_sensor_failure`, `dhw_sensor_failure`, `dcw_sensor_failure`, `dhw_motor_stuck`, `dhi_frost_protection`
- Pressure/flow: `no_secondary_pressure`, `pressure_sensor_failure`, `flow_sensor_failure`
- ITC/CH: `itc_hs_sensor_failure`, `itc_hr_sensor_failure`, `outdoor_sensor_failure`, `itc_motor_failure`, `itc_htco_error`, `itc_hs_frost_protection`

**Language support:**
- Config flow: language selector — Auto / Dansk / English
- Auto mode follows the HA language setting
- Sensor and binary sensor names adapt to the selected language

**Bug fixes:**
- Sensors with INVALID\_VALUE (0x7FFF = 327.67 °C per Modbus spec) now show as unavailable instead of 327.7 °C — affects HC sensors when not physically connected
- Removed `source_power` calculated field (unsupportable estimate)

### v0.1.15 — previous

- Initial public release
- Basic DHW sensors and binary sensors
- Config flow with IP, port, unit ID, scan interval
