# Wavin Calefa

Home Assistant custom integration for Wavin Calefa / Sentio units using local
Modbus TCP.

## Features

- Config flow with IP address, port, unit ID and unit name.
- Local polling, no cloud dependency.
- Sensors for domestic hot water (BVV), radiator heat (CVV), district heating
  (FJF/FJR), outdoor temperature (UT), valve positions, flows, calculated
  cooling, calculated power, system pressure (PRE) and diagnostics.
- Binary sensors for Calefa warnings and errors.
- Local icon/logo assets for Home Assistant and HACS.

## Notes

`Anlægstryk` uses register `7310` with scale `0.01`, because this has been
observed to match the pressure shown on the local Calefa display. The documented
secondary pressure register `6508` is also available as a disabled diagnostic
sensor for comparison.

The hot-water display page has been matched as:

- `BV` -> `Varmt vand ud (BV)`, input register `6505`, scale `0.01`.
- `KV` -> `Koldt vand ind (KV)`, input register `6509`, scale `0.01`.
- `FJF` -> `Fjernvarme fremløb (FJF)`, input register `6506`, scale `0.01`.
- `FJR` -> `Fjernvarme retur (FJR)`, input register `6507`, scale `0.01`.
- `FLOW` -> `Varmtvandsflow (BVV)`, input register `6510`, L/h.
- `BVV` -> `Varmtvandsventil (BVV)`, input register `6511`, scale `0.01`.

`BVV bypass status` is derived from `BVV status`: when the status is `Bypass`,
the bypass status is `Til`. `BVV blokeret af` uses input register `6503`; value
`0` means `Ingen`.

`Varmtvandsflow (BVV)` uses input register `6510` in L/h. `Radiator flow (CVV)`
uses input register `7306` in L/h. `Fjernvarme flow` uses input register `7307`
in L/h.

`Fjernvarme effekt` is calculated from `Fjernvarme flow` and `Fjernvarme
afkøling` as L/h × °C × 1.163 / 1000. It is an operational estimate, not an
official billing meter.

`Radiatorventil (CVV)` uses input register `7304` with scale `0.01`. CVV is the
central-heating valve for the heating/radiator circuit. This has been observed
to match the heating valve opening shown on the local Calefa display.

The radiator display page has been matched as:

- `UT:` -> `Udetemperatur (UT)`, input register `20`, scale `0.01`.
- `ØVF:` -> `Radiator ønsket fremløb (ØVF)`, input register `7703`, scale `0.01`.
- `VF:` -> `Radiator fremløb (CVV)`, input register `7701`, scale `0.01`.
- `VR:` -> `Radiator retur (CVV)`, input register `7702`, scale `0.01`.
- `PUM:` -> `Radiatorpumpe status (CVV)`, input register `7704`.
- Radiator heat request -> `Radiator varmekald (CVV)`, input register `7705`.
- `CVV:` -> `Radiatorventil (CVV)`, input register `7304`, scale `0.01`.
- `SÆT:` -> `Radiator setpunkt (SÆT)`, holding register `38`, scale `0.01`.
- `PRE:` -> `Anlægstryk`, input register `7310`, scale `0.01`.

The cold-water temperature sensor can be warmed by the heat exchanger when no
water is flowing. The `Varmtvand effekt estimat` sensor therefore only uses it
as a calculation input when there is flow and the value looks like a realistic
cold-water temperature; otherwise it falls back to 10 °C.

`Varmtvand energi estimat` integrates the hot-water power estimate over time and
restores its previous value after Home Assistant restarts. It is an operational
estimate, not an official billing meter.

## HACS

For HACS, the repository should contain:

- `custom_components/wavin_calefa/`
- root `hacs.json`
- root `README.md`

This working copy currently contains the integration under
`custom_components/wavin_calefa/`.
