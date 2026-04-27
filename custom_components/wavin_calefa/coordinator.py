"""Data coordinator for Wavin Calefa."""

from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_HOST,
    CONF_PORT,
    CONF_SCAN_INTERVAL,
    CONF_UNIT_ID,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_UNIT_ID,
    DOMAIN,
)
from .modbus import WavinCalefaClient, WavinCalefaError, signed16

LOGGER = logging.getLogger(__name__)


INPUT_REGISTERS: dict[str, tuple[int, str]] = {
    "device_type": (10, "uint16"),
    "hardware_version": (11, "uint16"),
    "software_version": (12, "uint16"),
    "software_version_minor": (13, "uint16"),
    "serial_prefix": (14, "uint16"),
    "heating_cooling_mode": (20, "uint16"),
    "dhw_state": (6502, "uint16"),
    "dhw_blocking_source": (6503, "uint16"),
    "circulation_state": (6504, "uint16"),
    "dhw_out_temperature": (6505, "temp100"),
    "source_inlet_temperature": (6506, "temp100"),
    "source_return_temperature": (6507, "temp100"),
    "documented_secondary_pressure": (6508, "pressure100"),
    "dcw_sensor_temperature": (6509, "temp100"),
    "domestic_cold_water_flow": (6510, "int16"),
    "valve_position": (6511, "percent100"),
    "boost_pump_state": (6512, "uint16"),
    "cvv_valve_position": (7304, "percent100"),
    "cvv_flow": (7306, "int16"),
    "source_flow": (7307, "int16"),
    "system_pressure": (7310, "pressure100"),
}

HOLDING_REGISTERS: dict[str, tuple[int, str]] = {
    "cvv_supply_temperature": (32, "temp100"),
    "cvv_return_temperature": (43, "temp1"),
    "dhw_mode": (6517, "uint16"),
    "dhw_block_request": (6519, "uint16"),
    "dhw_temperature_setpoint": (6521, "temp100"),
    "dhw_bypass_temperature": (6522, "temp100"),
    "circulation_pump_present": (6523, "uint16"),
    "circulation_inlet_temperature": (6524, "temp100"),
    "exclude_from_vacation": (6525, "uint16"),
    "exclude_from_standby": (6526, "uint16"),
    "boost_pump_mode": (6527, "uint16"),
}

DISCRETE_INPUTS: dict[str, int] = {
    "warning_low_energy": 6503,
    "error_dhw_temperature_high": 6504,
    "error_motor_failure": 6505,
    "error_source_inlet_sensor": 6506,
    "error_source_return_sensor": 6507,
    "error_dhw_sensor": 6508,
    "error_dcw_sensor": 6509,
    "warning_pressure_high": 6510,
    "warning_pressure_low": 6511,
    "error_pressure_critical_low": 6512,
    "error_flow_sensor": 6513,
}


def _convert(raw: int, kind: str) -> int | float:
    """Convert a raw register value."""
    if kind == "uint16":
        return raw
    value = signed16(raw)
    if kind in {"temp100", "pressure100", "percent100"}:
        return round(value * 0.01, 2)
    if kind == "temp1":
        return value
    if kind == "int16":
        return value
    return raw


class WavinCalefaCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Fetch Wavin Calefa data."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        self.entry = entry
        self.client = WavinCalefaClient(
            host=entry.data[CONF_HOST],
            port=entry.data.get(CONF_PORT, DEFAULT_PORT),
            unit_id=entry.data.get(CONF_UNIT_ID, DEFAULT_UNIT_ID),
        )
        scan_interval = entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        super().__init__(
            hass,
            LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Update data from the unit."""
        try:
            return await self.hass.async_add_executor_job(self._read_all)
        except WavinCalefaError as err:
            raise UpdateFailed(str(err)) from err

    def _read_all(self) -> dict[str, Any]:
        """Read all known registers."""
        data: dict[str, Any] = {}
        unavailable: dict[str, str] = {}

        for key, (address, kind) in INPUT_REGISTERS.items():
            try:
                raw = self.client.read_register(address, input_type="input")
            except WavinCalefaError as err:
                unavailable[key] = str(err)
                continue
            data[key] = _convert(raw, kind)
            data[f"{key}_raw"] = raw

        for key, (address, kind) in HOLDING_REGISTERS.items():
            try:
                raw = self.client.read_register(address, input_type="holding")
            except WavinCalefaError as err:
                unavailable[key] = str(err)
                continue
            data[key] = _convert(raw, kind)
            data[f"{key}_raw"] = raw

        for key, address in DISCRETE_INPUTS.items():
            try:
                data[key] = self.client.read_discrete_input(address)
            except WavinCalefaError as err:
                unavailable[key] = str(err)

        inlet = data.get("source_inlet_temperature")
        ret = data.get("source_return_temperature")
        if isinstance(inlet, (int, float)) and isinstance(ret, (int, float)):
            data["source_delta_temperature"] = round(inlet - ret, 2)

        source_flow = data.get("source_flow")
        source_delta = data.get("source_delta_temperature")
        if isinstance(source_flow, (int, float)) and isinstance(source_delta, (int, float)):
            data["source_power"] = round(max(0.0, source_flow * source_delta * 1.163 / 1000), 3)

        flow = data.get("domestic_cold_water_flow")
        dhw = data.get("dhw_out_temperature")
        dcw = data.get("dcw_sensor_temperature")
        if isinstance(flow, (int, float)) and isinstance(dhw, (int, float)):
            dcw_for_calc = dcw if isinstance(dcw, (int, float)) and flow > 0 and 2 <= dcw <= 25 else 10
            power = max(0.0, flow * (dhw - dcw_for_calc) * 1.163 / 1000)
            data["dhw_power_estimate"] = round(power, 3)
            data["dcw_temperature_for_calculation"] = round(dcw_for_calc, 2)

        if unavailable:
            data["unavailable"] = unavailable

        return data
