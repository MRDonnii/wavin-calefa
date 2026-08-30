"""Wavin Calefa integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .auto_standby import WavinCalefaAutoStandbyManager
from .const import AUTO_STANDBY_DATA, DOMAIN, HEAT_CALL_DATA, PLATFORMS
from .coordinator import WavinCalefaCoordinator
from .heat_call import WavinCalefaHeatCallManager


OBSOLETE_SENSOR_KEYS = {
    "boost_pump_state",
    "circulation_inlet_temperature",
    "cvv_flow",
    "cvv_heat_request",
    "cvv_pump_state",
    "cvv_room_setpoint",
    "source_flow",
    "source_power",
}

UNSUPPORTED_SENSOR_KEYS_BY_DEVICE_TYPE = {
    3: {
        "ch_desired_inlet_temperature",
        "hc_supply_temperature",
        "hc_return_temperature",
        "hc_delta_temperature",
    }
}


async def _async_remove_obsolete_entities(
    hass: HomeAssistant, entry: ConfigEntry
) -> None:
    """Remove legacy entities that are no longer provided by the integration."""
    entity_registry = er.async_get(hass)
    device_type = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    unsupported_sensor_keys = set(OBSOLETE_SENSOR_KEYS)
    if device_type is not None:
        reported_device_type = device_type.data.get("device_type")
        unsupported_sensor_keys.update(
            UNSUPPORTED_SENSOR_KEYS_BY_DEVICE_TYPE.get(reported_device_type, set())
        )

    for entity_entry in er.async_entries_for_config_entry(entity_registry, entry.entry_id):
        if entity_entry.domain != "sensor":
            continue
        if entity_entry.unique_id not in {
            f"{entry.entry_id}_{key}" for key in unsupported_sensor_keys
        }:
            continue
        entity_registry.async_remove(entity_entry.entity_id)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Wavin Calefa from a config entry."""
    coordinator = WavinCalefaCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await _async_remove_obsolete_entities(hass, entry)

    heat_call = WavinCalefaHeatCallManager(hass, entry, coordinator)
    hass.data.setdefault(HEAT_CALL_DATA, {})[entry.entry_id] = heat_call
    await heat_call.async_setup()

    auto_standby = WavinCalefaAutoStandbyManager(hass, entry, coordinator, heat_call)
    hass.data.setdefault(AUTO_STANDBY_DATA, {})[entry.entry_id] = auto_standby
    await auto_standby.async_setup()

    # Reload once the options flow manager has actually applied new options
    # (see config_flow.py) rather than reloading from within the flow
    # itself, which would run before that apply happens and pick up the
    # old options.
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the entry after its options have changed."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
        heat_call: WavinCalefaHeatCallManager | None = hass.data.get(
            HEAT_CALL_DATA, {}
        ).pop(entry.entry_id, None)
        if heat_call is not None:
            heat_call.async_unload()
        auto_standby: WavinCalefaAutoStandbyManager | None = hass.data.get(
            AUTO_STANDBY_DATA, {}
        ).pop(entry.entry_id, None)
        if auto_standby is not None:
            auto_standby.async_unload()
    return unload_ok
