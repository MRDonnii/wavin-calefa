"""Constants for the Wavin Calefa integration."""

from __future__ import annotations

from datetime import timedelta

DOMAIN = "wavin_calefa"
HEAT_CALL_DATA = f"{DOMAIN}_heat_call"

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

# Optional Sentio-style heat-call automation: lets external HA thermostats
# (climate entities) request heat from Calefa the same way a physical Sentio
# room controller would, when no such controller is actually installed.
CONF_HEAT_CALL_ENABLED = "heat_call_enabled"
CONF_HEAT_CALL_CLIMATE_ENTITIES = "heat_call_climate_entities"
CONF_HEAT_CALL_AC_ENTITIES = "heat_call_ac_entities"
CONF_HEAT_CALL_HYSTERESIS = "heat_call_hysteresis"
CONF_HEAT_CALL_RESTART_DELAY_MINUTES = "heat_call_restart_delay_minutes"
CONF_HEAT_CALL_SUMMER_STOP_NORMAL = "heat_call_summer_stop_normal"
CONF_HEAT_CALL_SUMMER_STOP_OVERRIDE = "heat_call_summer_stop_override"
CONF_HEAT_CALL_ROOM_TARGET_TEMPERATURE = "heat_call_room_target_temperature"
CONF_HEAT_CALL_MAX_DURATION_MINUTES = "heat_call_max_duration_minutes"
# For rooms with no thermostat at all (e.g. floor heating on a plain
# sensor): one "entity_id:target_temperature" pair per line.
CONF_HEAT_CALL_SENSOR_ROOMS = "heat_call_sensor_rooms"
# For actuator-driven demand sources with no thermostat concept, such as a
# ventilation unit's water-coil after-heater valve: demand is signalled by
# the opening percentage crossing a threshold, not a temperature vs target.
CONF_HEAT_CALL_VALVE_ENTITIES = "heat_call_valve_entities"
CONF_HEAT_CALL_VALVE_THRESHOLD = "heat_call_valve_threshold"

DEFAULT_HEAT_CALL_HYSTERESIS = 0.5
DEFAULT_HEAT_CALL_RESTART_DELAY_MINUTES = 2
DEFAULT_HEAT_CALL_SUMMER_STOP_NORMAL = 18.0
DEFAULT_HEAT_CALL_SUMMER_STOP_OVERRIDE = 25.0
DEFAULT_HEAT_CALL_ROOM_TARGET_TEMPERATURE = 30.0
DEFAULT_HEAT_CALL_MAX_DURATION_MINUTES = 180
DEFAULT_HEAT_CALL_VALVE_THRESHOLD = 5.0

HEAT_CALL_REGISTER_SUMMER_STOP = 38
HEAT_CALL_REGISTER_ROOM_TEMPORARY_TEMPERATURE = 7512
HEAT_CALL_REGISTER_ROOM_TEMPORARY_MODE = 7509
HEAT_CALL_REGISTER_ROOM_TEMPORARY_EXPIRY_HIGH = 7510
HEAT_CALL_REGISTER_ROOM_TEMPORARY_EXPIRY_LOW = 7511
HEAT_CALL_REFRESH_MINUTES = 30
HEAT_CALL_FAULT_GRACE_MINUTES = 20
