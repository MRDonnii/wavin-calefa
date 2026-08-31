"""Non-secret live diagnostics for heat demand and communication."""

from .const import AUTO_STANDBY_DATA, DOMAIN, HEAT_CALL_DATA


async def async_get_config_entry_diagnostics(hass, entry):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    heat = hass.data.get(HEAT_CALL_DATA, {}).get(entry.entry_id)
    standby = hass.data.get(AUTO_STANDBY_DATA, {}).get(entry.entry_id)
    return {
        "data": coordinator.data,
        "last_update_success": coordinator.last_update_success,
        "heat_call": None if heat is None else {
            "active": heat.active,
            "call_active": heat.call_active,
            "demand": heat.evaluate_demand(),
            "sources": heat.climate_entities,
            "sensor_rooms": heat.sensor_rooms,
            "valves": heat.valve_entities,
            "restart_delay_minutes": heat.restart_delay_minutes(),
            "write_failed": heat._write_failed,
        },
        "auto_standby": None if standby is None else {
            "active": standby.active,
            "owned": standby._engaged,
            "status": standby.status_text(False),
        },
    }
