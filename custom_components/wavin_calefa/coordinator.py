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

# DHW-21x docs: val_d2_fp100 uses 0x7FFF as INVALID_VALUE.
INVALID_FP100 = 0x7FFF


INPUT_REGISTERS: dict[str, tuple[int, str]] = {
    "device_type": (10, "uint16"),
    "hardware_version": (11, "uint16"),
    "software_version": (12, "uint16"),
    "software_version_minor": (13, "uint16"),
    "serial_prefix": (14, "uint16"),
    "outdoor_temperature": (20, "temp100"),
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
    "dhw_control_mode": (6512, "uint16"),
    "dhw_regulator_state": (6513, "uint16"),
    "dhw_motor_stall_level": (6514, "uint16"),
    "dhw_boost_state": (6515, "uint16"),
    "ch_state": (7301, "uint16"),
    "ch_blocking_source": (7302, "uint16"),
    "ch_regulator_state": (7303, "uint16"),
    "cvv_valve_position": (7304, "percent100"),
    "ch_desired_inlet_temperature": (7305, "temp100"),
    "hc_supply_temperature": (7308, "temp100"),
    "hc_return_temperature": (7309, "temp100"),
    "system_pressure": (7310, "pressure100"),
    "cvv_supply_temperature": (7701, "temp100"),
    "cvv_return_temperature": (7702, "temp100"),
    "cvv_desired_supply_temperature": (7703, "temp100"),
    "itc_pump_demand": (7704, "uint16"),
    "itc_pump_status": (7705, "uint16"),
}

HOLDING_REGISTERS: dict[str, tuple[int, str]] = {
    "itc_max_outdoor_temp": (38, "temp1"),
    "dhw_mode": (6517, "uint16"),
    "dhw_block_request": (6519, "uint16"),
    "dhw_temperature_setpoint": (6521, "temp100"),
    "dhw_bypass_temperature": (6522, "temp100"),
    "circulation_pump_enable": (6523, "uint16"),
    "circulation_temperature": (6524, "temp100"),
    "allow_vacation": (6525, "uint16"),
    "allow_standby": (6526, "uint16"),
    "flow_sensor_type": (6527, "uint16"),
    "boost_pump_mode": (6531, "uint16"),
}

DISCRETE_INPUTS: dict[str, int] = {
    "warning_low_energy": 6503,
    "error_dhw_temperature_high": 6504,
    "dhw_motor_failure": 6505,
    "dhi_sensor_failure": 6506,
    "dho_sensor_failure": 6507,
    "dhw_sensor_failure": 6508,
    "dcw_sensor_failure": 6509,
    "warning_pressure_high": 6510,
    "warning_pressure_low": 6511,
    "error_pressure_critical_low": 6512,
    "no_secondary_pressure": 6513,
    "pressure_sensor_failure": 6514,
    "flow_sensor_failure": 6515,
    "dhi_frost_protection": 6516,
    "dhw_motor_stuck": 6517,
    "itc_hs_sensor_failure": 7701,
    "itc_hr_sensor_failure": 7702,
    "outdoor_sensor_failure": 7703,
    "itc_motor_failure": 7704,
    "itc_htco_error": 7705,
    "itc_hs_frost_protection": 7706,
}


def _convert(raw: int, kind: str) -> int | float | None:
    """Convert a raw register value."""
    if kind == "uint16":
        return raw
    if kind in {"temp100", "pressure100", "percent100"} and raw == INVALID_FP100:
        return None
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

        dhw_state = data.get("dhw_state")
        if isinstance(dhw_state, int):
            data["dhw_bypass_active"] = 1 if dhw_state == 2 else 0

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
