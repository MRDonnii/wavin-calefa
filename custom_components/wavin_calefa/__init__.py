"""Wavin Calefa integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .auto_standby import WavinCalefaAutoStandbyManager
from .const import AUTO_STANDBY_DATA, DEMAND_DATA, DOMAIN, PLATFORMS
from .coordinator import WavinCalefaCoordinator
from .demand import WavinCalefaDemandTracker
from .modbus import WavinCalefaClient, WavinCalefaError

LOGGER = logging.getLogger(__name__)

# Removed along with heat call in 0.7.0. Kept here, isolated, purely so
# _async_migrate_stale_room_override below can release a temporary-room
# override a pre-0.7.0 install may have left engaged on the unit - the
# only code that ever cleared it was removed with the feature, so on its
# own it would otherwise sit engaged (CVV driven fully open) forever.
_LEGACY_ROOM_TEMPORARY_MODE_REGISTER = 7509
# Options that only ever drove that removed override; no longer read by
# any code, but worth dropping from storage on upgrade rather than
# leaving them behind as dead weight on the entry.
_LEGACY_HEAT_CALL_OPTION_KEYS = (
    "heat_call_enabled",
    "heat_call_room_target_temperature",
    "heat_call_max_duration_minutes",
    "heat_call_summer_stop_normal",
    "heat_call_summer_stop_override",
)


async def _async_migrate_stale_room_override(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Best-effort release of a temporary-room override left by pre-0.7.0 heat call."""
    client = WavinCalefaClient(host=entry.data["host"], port=entry.data["port"], unit_id=entry.data["unit_id"])
    try:
        await hass.async_add_executor_job(
            client.write_register, _LEGACY_ROOM_TEMPORARY_MODE_REGISTER, 0
        )
    except WavinCalefaError:
        LOGGER.warning(
            "Wavin Calefa: could not release a possible stale temporary-room "
            "override while migrating from a pre-0.7.0 version - if the unit "
            "was left with the CVV valve fully open after this update, turn "
            "off '%s · RUM Midl. mode' by hand once.",
            entry.title,
        )


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate an older config entry."""
    if entry.version < 2:
        await _async_migrate_stale_room_override(hass, entry)
        new_options = {
            key: value
            for key, value in entry.options.items()
            if key not in _LEGACY_HEAT_CALL_OPTION_KEYS
        }
        hass.config_entries.async_update_entry(entry, options=new_options, version=2)
    return True


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

    demand = WavinCalefaDemandTracker(hass, entry)
    hass.data.setdefault(DEMAND_DATA, {})[entry.entry_id] = demand

    auto_standby = WavinCalefaAutoStandbyManager(hass, entry, coordinator, demand)
    hass.data.setdefault(AUTO_STANDBY_DATA, {})[entry.entry_id] = auto_standby

    # Reload once the options flow manager has actually applied new options
    # (see config_flow.py) rather than reloading from within the flow
    # itself, which would run before that apply happens and pick up the
    # old options.
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    # Restore runtime switches before the manager can act on the unit.
    await auto_standby.async_setup()
    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the entry after its options have changed."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
        hass.data.get(DEMAND_DATA, {}).pop(entry.entry_id, None)
        auto_standby: WavinCalefaAutoStandbyManager | None = hass.data.get(
            AUTO_STANDBY_DATA, {}
        ).pop(entry.entry_id, None)
        if auto_standby is not None:
            auto_standby.async_unload()
    return unload_ok
