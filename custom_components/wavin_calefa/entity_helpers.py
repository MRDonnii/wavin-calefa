"""Shared entity naming and device grouping helpers."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
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
        via_device=(DOMAIN, entry.entry_id),
    )
