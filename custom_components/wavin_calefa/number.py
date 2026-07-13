"""Writable numeric controls for Wavin Calefa."""

from __future__ import annotations

from dataclasses import dataclass
import math
import time

from homeassistant.components.number import (
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory, UnitOfTemperature, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import WavinCalefaCoordinator
from .entity_helpers import (
    GROUP_DHW,
    GROUP_HEATING,
    GROUP_ROOM,
    control_device_info,
    localized_name,
)


@dataclass(frozen=True, kw_only=True)
class WavinCalefaNumberDescription(NumberEntityDescription):
    """Describe a verified writable Calefa number."""

    source_key: str
    register: int
    scale: int = 100
    mirror_register: int | None = None


NUMBER_PRESENTATION: dict[str, tuple[str, str, str]] = {
    "room_eco_temperature": (GROUP_ROOM, "Øko", "Eco"),
    "room_comfort_temperature": (
        GROUP_ROOM,
        "Komfort",
        "Comfort",
    ),
    "room_extra_comfort_temperature": (
        GROUP_ROOM,
        "Ekstra komfort",
        "Extra comfort",
    ),
    "room_temporary_temperature": (
        GROUP_ROOM,
        "Midl. temperatur",
        "Temp. temperature",
    ),
    "heat_curve_manual_slope": (
        GROUP_HEATING,
        "Hældning",
        "Slope",
    ),
    "summer_shutdown_temperature": (
        GROUP_HEATING,
        "Sommerstop",
        "Summer stop",
    ),
    "heat_curve_parallel_shift": (
        GROUP_HEATING,
        "Forskydning",
        "Shift",
    ),
    "heat_curve_min_supply_temperature": (
        GROUP_HEATING,
        "Min. fremløb",
        "Min. supply",
    ),
    "heat_curve_max_supply_temperature": (
        GROUP_HEATING,
        "Maks. fremløb",
        "Max. supply",
    ),
    "return_limiter_max_temperature": (
        GROUP_HEATING,
        "Maks. retur",
        "Max. return",
    ),
    "return_limiter_max_gain": (
        GROUP_HEATING,
        "Returforstærkning",
        "Return gain",
    ),
    "dhw_temperature_setpoint_control": (
        GROUP_DHW,
        "BV temperatur",
        "HW temperature",
    ),
    "dhw_bypass_temperature_control": (
        GROUP_DHW,
        "Bypass-temperatur",
        "Bypass temperature",
    ),
    "circulation_temperature_control": (
        GROUP_DHW,
        "Cirk. temperatur",
        "Circ. temperature",
    ),
}


NUMBERS: tuple[WavinCalefaNumberDescription, ...] = (
    WavinCalefaNumberDescription(
        key="room_temporary_temperature",
        source_key="room_temporary_temperature",
        register=7512,
        icon="mdi:timer-thermometer",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=5.0,
        native_max_value=30.0,
        native_step=0.5,
        mode=NumberMode.BOX,
    ),
    WavinCalefaNumberDescription(
        key="heat_curve_manual_slope",
        source_key="heat_curve_manual_slope",
        register=7701,
        mirror_register=7703,
        scale=10,
        icon="mdi:chart-line",
        native_min_value=0.3,
        native_max_value=1.8,
        native_step=0.1,
        mode=NumberMode.BOX,
    ),
    WavinCalefaNumberDescription(
        key="summer_shutdown_temperature",
        source_key="itc_max_outdoor_temp",
        register=38,
        icon="mdi:sun-thermometer",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=10.0,
        native_max_value=25.0,
        native_step=0.5,
        mode=NumberMode.BOX,
    ),
    WavinCalefaNumberDescription(
        key="heat_curve_parallel_shift",
        source_key="heat_curve_parallel_shift",
        register=7705,
        icon="mdi:chart-bell-curve-cumulative",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=-9.0,
        native_max_value=9.0,
        native_step=1.0,
        mode=NumberMode.BOX,
    ),
    WavinCalefaNumberDescription(
        key="heat_curve_min_supply_temperature",
        source_key="heat_curve_min_supply_temperature",
        register=7706,
        icon="mdi:thermometer-low",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=15.0,
        native_max_value=40.0,
        native_step=1.0,
        mode=NumberMode.BOX,
    ),
    WavinCalefaNumberDescription(
        key="heat_curve_max_supply_temperature",
        source_key="heat_curve_max_supply_temperature",
        register=7707,
        icon="mdi:thermometer-high",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=30.0,
        native_max_value=65.0,
        native_step=1.0,
        mode=NumberMode.BOX,
    ),
    WavinCalefaNumberDescription(
        key="return_limiter_max_temperature",
        source_key="return_limiter_max_temperature",
        register=7716,
        icon="mdi:thermometer-chevron-down",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=25.0,
        native_max_value=50.0,
        native_step=1.0,
        mode=NumberMode.BOX,
        entity_category=EntityCategory.CONFIG,
    ),
    WavinCalefaNumberDescription(
        key="return_limiter_max_gain",
        source_key="return_limiter_max_gain",
        register=7717,
        scale=10,
        icon="mdi:tune-vertical",
        native_min_value=-10.0,
        native_max_value=0.0,
        native_step=0.1,
        mode=NumberMode.BOX,
        entity_category=EntityCategory.CONFIG,
    ),
    WavinCalefaNumberDescription(
        key="dhw_temperature_setpoint_control",
        source_key="dhw_temperature_setpoint",
        register=6521,
        icon="mdi:thermometer-water",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=45.0,
        native_max_value=60.0,
        native_step=0.5,
        mode=NumberMode.BOX,
    ),
    WavinCalefaNumberDescription(
        key="dhw_bypass_temperature_control",
        source_key="dhw_bypass_temperature",
        register=6522,
        icon="mdi:pipe-valve",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=30.0,
        native_max_value=55.0,
        native_step=0.5,
        mode=NumberMode.BOX,
        entity_category=EntityCategory.CONFIG,
    ),
    WavinCalefaNumberDescription(
        key="circulation_temperature_control",
        source_key="circulation_temperature",
        register=6524,
        icon="mdi:pump",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=35.0,
        native_max_value=55.0,
        native_step=0.5,
        mode=NumberMode.BOX,
        entity_category=EntityCategory.CONFIG,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up verified Calefa numeric controls."""
    coordinator: WavinCalefaCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        WavinCalefaNumber(coordinator, entry, description)
        for description in NUMBERS
    )
    async_add_entities(
        [WavinCalefaRoomTemporaryDurationNumber(coordinator, entry)]
    )


class WavinCalefaNumber(
    CoordinatorEntity[WavinCalefaCoordinator], NumberEntity
):
    """Control a verified numeric Calefa setting."""

    entity_description: WavinCalefaNumberDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: WavinCalefaCoordinator,
        entry: ConfigEntry,
        description: WavinCalefaNumberDescription,
    ) -> None:
        """Initialize the control."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        group, danish, english = NUMBER_PRESENTATION[description.key]
        self._attr_name = localized_name(
            coordinator.hass, entry, danish, english
        )
        self._attr_device_info = control_device_info(
            coordinator.hass, entry, group
        )

    @property
    def native_value(self) -> float | None:
        """Return the setting read directly from the unit."""
        value = self.coordinator.data.get(self.entity_description.source_key)
        return float(value) if isinstance(value, (int, float)) else None

    async def async_set_native_value(self, value: float) -> None:
        """Write a bounded setting and verify it directly on the unit."""
        if not self.native_min_value <= value <= self.native_max_value:
            raise ValueError(f"{self.entity_description.key} outside safe range")
        raw_value = round(value * self.entity_description.scale) & 0xFFFF
        registers = {self.entity_description.register: raw_value}
        if self.entity_description.mirror_register is not None:
            registers[self.entity_description.mirror_register] = raw_value
        await self.coordinator.async_write_holding_registers(registers)


class WavinCalefaRoomTemporaryDurationNumber(
    CoordinatorEntity[WavinCalefaCoordinator], NumberEntity
):
    """Control temporary room override duration as a relative time."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:timer-outline"
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES
    _attr_native_min_value = 0.0
    _attr_native_max_value = 1440.0
    _attr_native_step = 15.0
    _attr_mode = NumberMode.BOX

    def __init__(
        self, coordinator: WavinCalefaCoordinator, entry: ConfigEntry
    ) -> None:
        """Initialize the duration control."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_room_temporary_duration"
        self._attr_name = localized_name(
            coordinator.hass,
            entry,
            "Midl. varighed",
            "Temp. duration",
        )
        self._attr_device_info = control_device_info(
            coordinator.hass, entry, GROUP_ROOM
        )

    @property
    def native_value(self) -> float:
        """Return remaining duration rounded up to a 15-minute step."""
        if self.coordinator.data.get("room_temporary_mode") != 1:
            return 0.0
        high = self.coordinator.data.get("room_temporary_expiry_high")
        low = self.coordinator.data.get("room_temporary_expiry_low")
        if not isinstance(high, int) or not isinstance(low, int):
            return 0.0
        expiry = (high << 16) | low
        remaining = max(0, expiry - int(time.time()))
        return float(min(1440, math.ceil(remaining / 900) * 15))

    async def async_set_native_value(self, value: float) -> None:
        """Set duration, expiry and mode as one verified operation."""
        minutes = max(0, min(1440, round(value / 15) * 15))
        if minutes == 0:
            await self.coordinator.async_write_holding_register(7509, 0)
            return
        expiry = int(time.time()) + minutes * 60
        await self.coordinator.async_write_holding_registers(
            {
                7510: (expiry >> 16) & 0xFFFF,
                7511: expiry & 0xFFFF,
                7509: 1,
            }
        )
