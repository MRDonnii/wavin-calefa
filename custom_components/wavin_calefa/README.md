<p align="center">
  <img src="brand/logo.png" alt="Wavin Calefa logo" width="300">
</p>

# Wavin Calefa

Local Home Assistant integration for Wavin Calefa 2 and Sentio over Modbus TCP.

Version 0.7.0 removes the optional heat-call (Sentio emulation) feature from 0.4.0-0.6.1: it forced Calefa's RUM temporary-room override fully open on any demand, which had no way to modulate proportionally without a real per-room reading. Automatic standby remains, sharing the same demand sources. The integration provides verified writable controls for heating curves, return limiting, room comfort, vacation/standby, and domestic hot water, plus 43 sensors and 17 fault or warning binary sensors.

For installation, configuration, safety notes, and the full feature list, see the [project README](https://github.com/MRDonnii/wavin-calefa#readme).
