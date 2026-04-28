"""Constants for the Wavin Calefa integration."""

from __future__ import annotations

from datetime import timedelta

DOMAIN = "wavin_calefa"

CONF_HOST = "host"
CONF_PORT = "port"
CONF_UNIT_ID = "unit_id"
CONF_SCAN_INTERVAL = "scan_interval"

DEFAULT_NAME = "Wavin Calefa"
DEFAULT_PORT = 0
DEFAULT_UNIT_ID = 1
DEFAULT_SCAN_INTERVAL = 30
MIN_SCAN_INTERVAL = 10

PORT_SCAN_TIMEOUT = 1.0
PORT_SCAN_CANDIDATES = (10223, 502, 5020, 5021, 5022, 5023, 1502, 10502, 2000)

PLATFORMS = ["sensor", "binary_sensor"]

UPDATE_INTERVAL = timedelta(seconds=DEFAULT_SCAN_INTERVAL)
