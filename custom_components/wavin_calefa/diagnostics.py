"""Non-secret live diagnostics for heat demand and communication."""

from .const import AUTO_STANDBY_DATA, DEMAND_DATA, DOMAIN


async def async_get_config_entry_diagnostics(hass, entry):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    demand = hass.data.get(DEMAND_DATA, {}).get(entry.entry_id)
    standby = hass.data.get(AUTO_STANDBY_DATA, {}).get(entry.entry_id)
    return {
        "data": coordinator.data,
        "last_update_success": coordinator.last_update_success,
        "demand": None if demand is None else {
            "demand": demand.evaluate_demand(),
            "all_warm": demand.evaluate_all_warm(),
            "sources": demand.climate_entities,
            "sensor_rooms": demand.sensor_rooms,
            "valves": demand.valve_entities,
            "restart_delay_minutes": demand.restart_delay_minutes(),
        },
        "auto_standby": None if standby is None else {
            "active": standby.active,
            "owned": standby._engaged,
            "status": standby.status_text(False),
        },
    }
