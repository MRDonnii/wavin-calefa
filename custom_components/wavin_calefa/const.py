"""Constants for the Wavin Calefa integration."""

from __future__ import annotations

from datetime import timedelta

DOMAIN = "wavin_calefa"
DEMAND_DATA = f"{DOMAIN}_demand"

CONF_HOST = "host"
CONF_PORT = "port"
CONF_UNIT_ID = "unit_id"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_LANGUAGE = "language"

LANGUAGE_AUTO = "auto"
LANGUAGE_DA = "da"
LANGUAGE_EN = "en"
LANGUAGE_CHOICES = (LANGUAGE_AUTO, LANGUAGE_DA, LANGUAGE_EN)
LANGUAGE_LABELS = {
	LANGUAGE_AUTO: "Auto",
	LANGUAGE_DA: "Dansk",
	LANGUAGE_EN: "English",
}

DEFAULT_NAME = "Wavin Calefa"
DEFAULT_PORT = 0
DEFAULT_UNIT_ID = 1
DEFAULT_SCAN_INTERVAL = 30
DEFAULT_LANGUAGE = LANGUAGE_AUTO
MIN_SCAN_INTERVAL = 10

PORT_SCAN_TIMEOUT = 1.0
PORT_SCAN_CANDIDATES = (10223, 502, 5020, 5021, 5022, 5023, 1502, 10502, 2000)

PLATFORMS = ["sensor", "binary_sensor", "number", "select", "switch"]

UPDATE_INTERVAL = timedelta(seconds=DEFAULT_SCAN_INTERVAL)

# Demand detection: watches a set of existing HA thermostats/sensors/valves
# and decides whether *something* currently needs heat. This used to also
# drive a Sentio-emulation "heat call" that forced Calefa's RUM temporary-
# room override open - that mechanism has been removed (see CHANGELOG):
# Calefa has no live per-room reading to modulate against, so it always
# just drove the CVV valve fully open regardless of how small the real
# deficit was, which made it both blunt and hard on afkoling. What's left
# here is purely the shared demand signal auto_standby.py uses to decide
# when it's safe to put the whole unit into standby. Config keys keep their
# historical "heat_call_*" string values so existing installations don't
# lose their configured rooms on upgrade; only the Python-side names changed.
CONF_DEMAND_CLIMATE_ENTITIES = "heat_call_climate_entities"
CONF_DEMAND_AC_ENTITIES = "heat_call_ac_entities"
CONF_DEMAND_HYSTERESIS = "heat_call_hysteresis"
CONF_DEMAND_RESTART_DELAY_MINUTES = "heat_call_restart_delay_minutes"
# For rooms with no thermostat at all (e.g. floor heating on a plain
# sensor): one "entity_id:target_temperature" pair per line.
CONF_DEMAND_SENSOR_ROOMS = "heat_call_sensor_rooms"
# For actuator-driven demand sources with no thermostat concept, such as a
# ventilation unit's water-coil after-heater valve: demand is signalled by
# the opening percentage crossing a threshold, not a temperature vs target.
CONF_DEMAND_VALVE_ENTITIES = "heat_call_valve_entities"
CONF_DEMAND_VALVE_THRESHOLD = "heat_call_valve_threshold"

DEFAULT_DEMAND_HYSTERESIS = 0.5
DEFAULT_DEMAND_RESTART_DELAY_MINUTES = 2
DEFAULT_DEMAND_VALVE_THRESHOLD = 5.0

# Optional automatic-standby feature: shares the demand tracker's configured
# thermostats/sensor-rooms/valve entities as its demand signal, and puts the
# whole Calefa unit into standby once every one of them is warm enough for
# long enough, releasing it again the moment real demand returns. Used by
# both auto_standby.py and the existing standby switch in switch.py, so the
# register is a shared constant rather than a literal in two places.
REGISTER_STANDBY = 26

AUTO_STANDBY_DATA = f"{DOMAIN}_auto_standby"
CONF_AUTO_STANDBY_ENABLED = "auto_standby_enabled"
CONF_AUTO_STANDBY_DELAY_MINUTES = "auto_standby_delay_minutes"
DEFAULT_AUTO_STANDBY_DELAY_MINUTES = 15

# Fixed (non-configurable) pump-stop confirmation behaviour after engaging
# standby: retried this many times, this many seconds apart, before the
# feature reports a fault instead of silently holding standby unconfirmed.
# Calefa can keep the physical pump running for roughly 100 seconds after
# demand and valve have closed. Six retries give that normal overrun time to
# finish before reporting a fault (fault after about 140 seconds).
AUTO_STANDBY_PUMPSTOP_RETRY_COUNT = 6
AUTO_STANDBY_PUMPSTOP_RETRY_DELAY_SECONDS = 20
