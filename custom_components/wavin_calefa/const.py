"""Constants for the Wavin Calefa integration."""

from __future__ import annotations

from datetime import timedelta

DOMAIN = "wavin_calefa"

CONF_HOST = "host"
CONF_PORT = "port"
CONF_UNIT_ID = "unit_id"
CONF_SCAN_INTERVAL = "scan_interval"

DEFAULT_NAME = "Wavin Calefa"
DEFAULT_PORT = 10223
DEFAULT_UNIT_ID = 1
DEFAULT_SCAN_INTERVAL = 30
MIN_SCAN_INTERVAL = 10

PLATFORMS = ["sensor", "binary_sensor"]

UPDATE_INTERVAL = timedelta(seconds=DEFAULT_SCAN_INTERVAL)
