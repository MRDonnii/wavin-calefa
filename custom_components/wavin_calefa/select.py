"""Writable mode controls for Wavin Calefa."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
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


DHW_MODES = {
    "schedule": 0,
    "adaptive_schedule": 1,
    "eco": 2,
    "comfort": 3,
}

HEAT_CURVE_TYPES = {
    "manual": 0,
    "floor_heating": 2,
    "radiator": 3,
}

RETURN_LIMITER_MODES = {
    "off": 0,
    "maximum": 2,
}

ROOM_MODE_SOURCES = {
    "eco": "room_eco_temperature",
    "comfort": "room_comfort_temperature",
    "extra_comfort": "room_extra_comfort_temperature",
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up verified Calefa mode controls."""
    coordinator: WavinCalefaCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            WavinCalefaDhwModeSelect(coordinator, entry),
            WavinCalefaHeatCurveTypeSelect(coordinator, entry),
            WavinCalefaReturnLimiterModeSelect(coordinator, entry),
            WavinCalefaRoomModeSelect(coordinator, entry),
        ]
    )


class WavinCalefaDhwModeSelect(
    CoordinatorEntity[WavinCalefaCoordinator], SelectEntity
):
    """Control the domestic hot-water operating mode."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:water-boiler-cog"
    _attr_options = list(DHW_MODES)

    def __init__(
        self, coordinator: WavinCalefaCoordinator, entry: ConfigEntry
    ) -> None:
        """Initialize the control."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_dhw_mode_control"
        self._attr_name = localized_name(
            coordinator.hass, entry, "Bypass-mode", "Bypass mode"
        )
        self._attr_device_info = control_device_info(
            coordinator.hass, entry, GROUP_DHW
        )

    @property
    def current_option(self) -> str | None:
        """Return the mode read directly from the unit."""
        raw_mode = self.coordinator.data.get("dhw_mode")
        return next(
            (option for option, raw in DHW_MODES.items() if raw == raw_mode),
            None,
        )

    async def async_select_option(self, option: str) -> None:
        """Write the selected mode and verify it directly on the unit."""
        if option not in DHW_MODES:
            raise ValueError(f"Unsupported DHW mode: {option}")
        await self.coordinator.async_write_holding_register(
            6517, DHW_MODES[option]
        )


class WavinCalefaHeatCurveTypeSelect(
    CoordinatorEntity[WavinCalefaCoordinator], SelectEntity
):
    """Select the heating curve profile."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:chart-bell-curve"
    _attr_options = list(HEAT_CURVE_TYPES)

    def __init__(
        self, coordinator: WavinCalefaCoordinator, entry: ConfigEntry
    ) -> None:
        """Initialize the control."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_heat_curve_type"
        self._attr_name = localized_name(
            coordinator.hass,
            entry,
            "Kurvetype",
            "Curve type",
        )
        self._attr_device_info = control_device_info(
            coordinator.hass, entry, GROUP_HEATING
        )

    @property
    def current_option(self) -> str | None:
        """Return the profile read directly from the unit."""
        raw_type = self.coordinator.data.get("heat_curve_type")
        return next(
            (option for option, raw in HEAT_CURVE_TYPES.items() if raw == raw_type),
            None,
        )

    async def async_select_option(self, option: str) -> None:
        """Select a profile and let Calefa apply its profile presets."""
        if option not in HEAT_CURVE_TYPES:
            raise ValueError(f"Unsupported heat curve type: {option}")
        await self.coordinator.async_write_holding_register(
            7702, HEAT_CURVE_TYPES[option]
        )


class WavinCalefaReturnLimiterModeSelect(
    CoordinatorEntity[WavinCalefaCoordinator], SelectEntity
):
    """Select the supported return-limiter mode."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:thermometer-chevron-down"
    _attr_options = list(RETURN_LIMITER_MODES)

    def __init__(
        self, coordinator: WavinCalefaCoordinator, entry: ConfigEntry
    ) -> None:
        """Initialize the control."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_return_limiter_mode"
        self._attr_name = localized_name(
            coordinator.hass,
            entry,
            "Returmode",
            "Return mode",
        )
        self._attr_device_info = control_device_info(
            coordinator.hass, entry, GROUP_HEATING
        )

    @property
    def current_option(self) -> str | None:
        """Return the mode read directly from the unit."""
        raw_mode = self.coordinator.data.get("return_limiter_mode")
        return next(
            (option for option, raw in RETURN_LIMITER_MODES.items() if raw == raw_mode),
            None,
        )

    async def async_select_option(self, option: str) -> None:
        """Write and verify the selected return-limiter mode."""
        if option not in RETURN_LIMITER_MODES:
            raise ValueError(f"Unsupported return-limiter mode: {option}")
        await self.coordinator.async_write_holding_register(
            7713, RETURN_LIMITER_MODES[option]
        )


class WavinCalefaRoomModeSelect(
    CoordinatorEntity[WavinCalefaCoordinator], SelectEntity
):
    """Select a Calefa room comfort preset."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:home-thermometer"
    _attr_options = list(ROOM_MODE_SOURCES)

    def __init__(
        self, coordinator: WavinCalefaCoordinator, entry: ConfigEntry
    ) -> None:
        """Initialize the control."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_room_mode"
        self._attr_name = localized_name(
            coordinator.hass, entry, "Komfortprofil", "Comfort profile"
        )
        self._attr_device_info = control_device_info(
            coordinator.hass, entry, GROUP_ROOM
        )

    @property
    def current_option(self) -> str | None:
        """Return the preset matching the active room temperature."""
        active = self.coordinator.data.get("room_mode_temperature")
        if not isinstance(active, (int, float)):
            return None
        return next(
            (
                option
                for option, source_key in ROOM_MODE_SOURCES.items()
                if self.coordinator.data.get(source_key) == active
            ),
            None,
        )

    async def async_select_option(self, option: str) -> None:
        """Write the current temperature of the selected preset."""
        source_key = ROOM_MODE_SOURCES.get(option)
        if source_key is None:
            raise ValueError(f"Unsupported room mode: {option}")
        temperature = self.coordinator.data.get(source_key)
        if not isinstance(temperature, (int, float)):
            raise ValueError(f"Room preset unavailable: {option}")
        await self.coordinator.async_write_holding_register(
            7501, round(temperature * 100) & 0xFFFF
        )
