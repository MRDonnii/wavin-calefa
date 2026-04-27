# Wavin Calefa

Home Assistant custom integration for Wavin Calefa / Sentio units using local
Modbus TCP.

## Features

- Config flow with IP address, port, unit ID and unit name.
- Local polling, no cloud dependency.
- Sensors for domestic hot water, district heating temperatures, valve
  position, calculated cooling, system pressure and diagnostics.
- Binary sensors for Calefa warnings and errors.

## Notes

`Anlægstryk` uses register `7310` with scale `0.01`, because this has been
observed to match the pressure shown on the local Calefa display. The documented
secondary pressure register `6508` is also available as a disabled diagnostic
sensor for comparison.

The cold-water temperature sensor can be warmed by the heat exchanger when no
water is flowing. The `Varmtvand effekt estimat` sensor therefore only uses it
as a calculation input when there is flow and the value looks like a realistic
cold-water temperature; otherwise it falls back to 10 °C.

## HACS

For HACS, the repository should contain:

- `custom_components/wavin_calefa/`
- root `hacs.json`
- root `README.md`

This working copy currently contains the integration under
`custom_components/wavin_calefa/`.

