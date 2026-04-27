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

from .const import DOMAIN
from .coordinator import WavinCalefaCoordinator


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
        key="error_motor_failure",
        source_key="error_motor_failure",
        name="Motorfejl",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    WavinCalefaBinarySensorDescription(
        key="error_source_inlet_sensor",
        source_key="error_source_inlet_sensor",
        name="Fremløbsføler fejl",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    WavinCalefaBinarySensorDescription(
        key="error_source_return_sensor",
        source_key="error_source_return_sensor",
        name="Returføler fejl",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    WavinCalefaBinarySensorDescription(
        key="error_dhw_sensor",
        source_key="error_dhw_sensor",
        name="Brugsvandsføler fejl",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    WavinCalefaBinarySensorDescription(
        key="error_dcw_sensor",
        source_key="error_dcw_sensor",
        name="Koldtvandsføler fejl",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    WavinCalefaBinarySensorDescription(
        key="warning_pressure_high",
        source_key="warning_pressure_high",
        name="Tryk høj advarsel",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    WavinCalefaBinarySensorDescription(
        key="warning_pressure_low",
        source_key="warning_pressure_low",
        name="Tryk lav advarsel",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    WavinCalefaBinarySensorDescription(
        key="error_pressure_critical_low",
        source_key="error_pressure_critical_low",
        name="Tryk kritisk lav fejl",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    WavinCalefaBinarySensorDescription(
        key="error_flow_sensor",
        source_key="error_flow_sensor",
        name="Flowføler fejl",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
)


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
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="Wavin",
            model="Calefa 2",
        )

    @property
    def is_on(self) -> bool | None:
        """Return true if the problem is active."""
        value = self.coordinator.data.get(self.entity_description.source_key)
        return bool(value) if value is not None else None

