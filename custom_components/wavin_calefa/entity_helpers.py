"""Shared entity naming and device grouping helpers."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity import DeviceInfo

from .const import (
    CONF_LANGUAGE,
    DEFAULT_LANGUAGE,
    DOMAIN,
    LANGUAGE_AUTO,
    LANGUAGE_DA,
)

GROUP_SYSTEM = "system"
GROUP_HEATING = "heating"
GROUP_ROOM = "room"
GROUP_DHW = "dhw"

GROUP_LABELS = {
    GROUP_HEATING: ("Varme", "Heating"),
    GROUP_ROOM: ("RUM", "Room"),
    GROUP_DHW: ("Brugsvand", "Domestic hot water"),
}


def is_danish(hass: object, entry: ConfigEntry) -> bool:
    """Return whether this entry should use Danish entity names."""
    choice = entry.data.get(CONF_LANGUAGE, DEFAULT_LANGUAGE)
    if choice == LANGUAGE_AUTO:
        language = str(getattr(getattr(hass, "config", None), "language", "en"))
        return language.lower().startswith("da")
    return choice == LANGUAGE_DA


def localized_name(
    hass: object, entry: ConfigEntry, danish: str, english: str
) -> str:
    """Return an explicit localized name, independent of translation cache."""
    return danish if is_danish(hass, entry) else english


def control_device_info(
    hass: object, entry: ConfigEntry, group: str
) -> DeviceInfo:
    """Place controls on clear native subdevices."""
    if group == GROUP_SYSTEM:
        return DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="Wavin",
            model="Calefa / Sentio",
        )

    da_label, en_label = GROUP_LABELS[group]
    label = localized_name(hass, entry, da_label, en_label)
    return DeviceInfo(
        identifiers={(DOMAIN, f"{entry.entry_id}_{group}")},
        name=f"{entry.title} · {label}",
        manufacturer="Wavin",
        model=f"Calefa {label}",
    )


@callback
def async_link_control_devices(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Link the control subdevices to the main unit in the device registry.

    This replaces `via_device` in DeviceInfo, which Home Assistant deprecates
    from 2026.8 and removes in 2027.8. Its replacement, DeviceInfo
    `via_device_id`, does not exist before 2026.8, whereas
    `async_update_device(via_device_id=...)` works on every supported version.
    """
    device_registry = dr.async_get(hass)
    devices = {
        identifier: device
        for device in dr.async_entries_for_config_entry(
            device_registry, entry.entry_id
        )
        for domain, identifier in device.identifiers
        if domain == DOMAIN
    }
    if (unit := devices.get(entry.entry_id)) is None:
        return
    for group in GROUP_LABELS:
        device = devices.get(f"{entry.entry_id}_{group}")
        if device is not None and device.via_device_id != unit.id:
            device_registry.async_update_device(device.id, via_device_id=unit.id)
