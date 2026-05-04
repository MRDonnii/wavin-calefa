"""Binary sensors for Wavin Calefa."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_LANGUAGE,
    DEFAULT_LANGUAGE,
    DOMAIN,
    LANGUAGE_AUTO,
    LANGUAGE_DA,
    LANGUAGE_EN,
)
from .coordinator import WavinCalefaCoordinator


DEVICE_TYPE_NAMES = {2: "DHW-201 Calefa", 3: "Sentio"}


def _device_model(coordinator: WavinCalefaCoordinator) -> str:
    """Return a generic model name based on the reported device type."""
    device_type = coordinator.data.get("device_type")
    return DEVICE_TYPE_NAMES.get(device_type, "Calefa / Sentio")


@dataclass(frozen=True, kw_only=True)
class WavinCalefaBinarySensorDescription(BinarySensorEntityDescription):
    """Wavin Calefa binary sensor description."""

    source_key: str


BINARY_SENSORS: tuple[WavinCalefaBinarySensorDescription, ...] = (
    WavinCalefaBinarySensorDescription(
        key="warning_low_energy",
        source_key="warning_low_energy",
        name="Lav energi advarsel",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    WavinCalefaBinarySensorDescription(
        key="error_dhw_temperature_high",
        source_key="error_dhw_temperature_high",
        name="Brugsvand temperatur høj fejl",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    WavinCalefaBinarySensorDescription(
        key="dhw_motor_failure",
        source_key="dhw_motor_failure",
        name="DHW motor failure",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    WavinCalefaBinarySensorDescription(
        key="dhi_sensor_failure",
        source_key="dhi_sensor_failure",
        name="District heating supply sensor failure",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    WavinCalefaBinarySensorDescription(
        key="dho_sensor_failure",
        source_key="dho_sensor_failure",
        name="District heating return sensor failure",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    WavinCalefaBinarySensorDescription(
        key="dhw_sensor_failure",
        source_key="dhw_sensor_failure",
        name="DHW sensor failure",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    WavinCalefaBinarySensorDescription(
        key="dcw_sensor_failure",
        source_key="dcw_sensor_failure",
        name="Cold water sensor failure",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    WavinCalefaBinarySensorDescription(
        key="warning_pressure_high",
        source_key="warning_pressure_high",
        name="High pressure warning",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    WavinCalefaBinarySensorDescription(
        key="warning_pressure_low",
        source_key="warning_pressure_low",
        name="Low pressure warning",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    WavinCalefaBinarySensorDescription(
        key="error_pressure_critical_low",
        source_key="error_pressure_critical_low",
        name="Critical low pressure",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    WavinCalefaBinarySensorDescription(
        key="no_secondary_pressure",
        source_key="no_secondary_pressure",
        name="No secondary pressure",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    WavinCalefaBinarySensorDescription(
        key="pressure_sensor_failure",
        source_key="pressure_sensor_failure",
        name="Pressure sensor failure",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    WavinCalefaBinarySensorDescription(
        key="flow_sensor_failure",
        source_key="flow_sensor_failure",
        name="Flow sensor failure",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    WavinCalefaBinarySensorDescription(
        key="dhi_frost_protection",
        source_key="dhi_frost_protection",
        name="District heating frost protection",
        device_class=BinarySensorDeviceClass.COLD,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    WavinCalefaBinarySensorDescription(
        key="dhw_motor_stuck",
        source_key="dhw_motor_stuck",
        name="DHW motor stuck",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    WavinCalefaBinarySensorDescription(
        key="itc_hs_sensor_failure",
        source_key="itc_hs_sensor_failure",
        name="Heating supply sensor failure (ITC)",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    WavinCalefaBinarySensorDescription(
        key="itc_hr_sensor_failure",
        source_key="itc_hr_sensor_failure",
        name="Heating return sensor failure (ITC)",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    WavinCalefaBinarySensorDescription(
        key="outdoor_sensor_failure",
        source_key="outdoor_sensor_failure",
        name="Outdoor sensor failure",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    WavinCalefaBinarySensorDescription(
        key="itc_motor_failure",
        source_key="itc_motor_failure",
        name="Heating valve motor failure (ITC)",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    WavinCalefaBinarySensorDescription(
        key="itc_htco_error",
        source_key="itc_htco_error",
        name="HTCO error (ITC)",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    WavinCalefaBinarySensorDescription(
        key="itc_hs_frost_protection",
        source_key="itc_hs_frost_protection",
        name="Heating frost protection (ITC)",
        device_class=BinarySensorDeviceClass.COLD,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
)

BIN_SENSOR_NAMES_DA: dict[str, str] = {
    "warning_low_energy": "Lav energi advarsel",
    "error_dhw_temperature_high": "Brugsvand temperatur hoj",
    "dhw_motor_failure": "BVV motorfejl",
    "dhi_sensor_failure": "Fjernvarme fremlobsfoler fejl",
    "dho_sensor_failure": "Fjernvarme returfoller fejl",
    "dhw_sensor_failure": "Brugsvandsfoler fejl",
    "dcw_sensor_failure": "Koldtvandsfoler fejl",
    "warning_pressure_high": "Tryk hoj advarsel",
    "warning_pressure_low": "Tryk lav advarsel",
    "error_pressure_critical_low": "Tryk kritisk lav fejl",
    "no_secondary_pressure": "Intet sekundartryk",
    "pressure_sensor_failure": "Tryksensor fejl",
    "flow_sensor_failure": "Flowsensor fejl",
    "dhi_frost_protection": "Fjernvarme frostbeskyttelse",
    "dhw_motor_stuck": "BVV motor blokeret",
    "itc_hs_sensor_failure": "CVV fremlobsfoler fejl",
    "itc_hr_sensor_failure": "CVV returfoller fejl",
    "outdoor_sensor_failure": "Udetemperaturfoler fejl",
    "itc_motor_failure": "CVV ventilmotor fejl",
    "itc_htco_error": "HTCO fejl (ITC)",
    "itc_hs_frost_protection": "Varme frostbeskyttelse (ITC)",
}


def _selected_language(hass: HomeAssistant, entry: ConfigEntry) -> str:
    """Resolve language mode for this integration entry."""
    choice = entry.data.get(CONF_LANGUAGE, DEFAULT_LANGUAGE)
    if choice == LANGUAGE_AUTO:
        hass_lang = str(getattr(hass.config, "language", "en")).lower()
        return LANGUAGE_DA if hass_lang.startswith("da") else LANGUAGE_EN
    return LANGUAGE_DA if choice == LANGUAGE_DA else LANGUAGE_EN


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Wavin Calefa binary sensors."""
    coordinator: WavinCalefaCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        WavinCalefaBinarySensor(coordinator, entry, description)
        for description in BINARY_SENSORS
    )


class WavinCalefaBinarySensor(
    CoordinatorEntity[WavinCalefaCoordinator], BinarySensorEntity
):
    """Wavin Calefa binary sensor."""

    entity_description: WavinCalefaBinarySensorDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: WavinCalefaCoordinator,
        entry: ConfigEntry,
        description: WavinCalefaBinarySensorDescription,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        selected_language = _selected_language(coordinator.hass, entry)
        if selected_language == LANGUAGE_DA:
            self._attr_name = BIN_SENSOR_NAMES_DA.get(description.key, description.name)
        else:
            self._attr_name = description.name
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="Wavin",
            model=_device_model(coordinator),
        )

    @property
    def is_on(self) -> bool | None:
        """Return true if the problem is active."""
        value = self.coordinator.data.get(self.entity_description.source_key)
        return bool(value) if value is not None else None
