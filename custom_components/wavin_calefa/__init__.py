"""Wavin Calefa integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN, PLATFORMS
from .coordinator import WavinCalefaCoordinator


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

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
