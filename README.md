# Wavin Calefa

Home Assistant custom integration for Wavin Calefa / Sentio units using local
Modbus TCP.

## Features

- Config flow with IP address, port, unit ID and unit name.
- Local polling, no cloud dependency.
- Sensors for domestic hot water, estimated hot-water power and energy,
  district heating temperatures, BVV valve position, CVV valve position,
  BVV/CVV/district-heating flow, CVV flow/return temperatures, calculated
  cooling, system pressure and diagnostics.
- Binary sensors for Calefa warnings and errors.
- Local icon/logo assets for Home Assistant and HACS.

## Notes

`Anlægstryk` uses register `7310` with scale `0.01`, because this has been
observed to match the pressure shown on the local Calefa display. The documented
secondary pressure register `6508` is also available as a disabled diagnostic
sensor for comparison.

`BVV ventilposition` uses input register `6511` with scale `0.01`. BVV is the
domestic hot-water valve for the hot-water heat exchanger.

`BVV flow` uses input register `6510` in L/h. `CVV flow` uses input register
`7306` in L/h. `Fjernvarme flow` uses input register `7307` in L/h.

`CVV ventilposition` uses input register `7304` with scale `0.01`. CVV is the
central-heating valve for the heating/radiator circuit. This has been observed
to match the heating valve opening shown on the local Calefa display.

`CVV fremløb temperatur` uses holding register `32` with scale `0.01`, and
`CVV retur temperatur` uses holding register `43` with scale `1`. They represent
the central-heating/radiator circuit temperatures.

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
