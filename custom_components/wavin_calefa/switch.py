"""Writable on/off controls for Wavin Calefa."""

from __future__ import annotations

import time

from homeassistant.components.switch import SwitchEntity
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
    GROUP_SYSTEM,
    control_device_info,
    localized_name,
)


def _set_presentation(
    entity: SwitchEntity,
    coordinator: WavinCalefaCoordinator,
    entry: ConfigEntry,
    group: str,
    danish: str,
    english: str,
) -> None:
    """Set a reliable localized name and native device group."""
    entity._attr_name = localized_name(
        coordinator.hass, entry, danish, english
    )
    entity._attr_device_info = control_device_info(
        coordinator.hass, entry, group
    )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up verified Calefa switches."""
    coordinator: WavinCalefaCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            WavinCalefaStandbySwitch(coordinator, entry),
            WavinCalefaVacationSwitch(coordinator, entry),
            WavinCalefaVacationForDhwSwitch(coordinator, entry),
            WavinCalefaVacationForChSwitch(coordinator, entry),
            WavinCalefaRoomScheduleSwitch(coordinator, entry),
            WavinCalefaRoomTemporaryModeSwitch(coordinator, entry),
            WavinCalefaReturnLimiterPrioritySwitch(coordinator, entry),
        ]
    )


class WavinCalefaStandbySwitch(
    CoordinatorEntity[WavinCalefaCoordinator], SwitchEntity
):
    """Block or release space heating using Calefa standby mode."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:power-sleep"

    def __init__(
        self, coordinator: WavinCalefaCoordinator, entry: ConfigEntry
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_standby_control"
        _set_presentation(
            self, coordinator, entry, GROUP_SYSTEM, "Standby", "Standby"
        )

    @property
    def is_on(self) -> bool | None:
        """Return whether Calefa standby is active."""
        value = self.coordinator.data.get("standby")
        return bool(value) if isinstance(value, int) else None

    async def async_turn_on(self, **kwargs: object) -> None:
        """Activate standby and block space heating."""
        await self.coordinator.async_write_holding_register(26, 1)

    async def async_turn_off(self, **kwargs: object) -> None:
        """Release standby and allow space heating."""
        await self.coordinator.async_write_holding_register(26, 0)


class WavinCalefaVacationSwitch(
    CoordinatorEntity[WavinCalefaCoordinator], SwitchEntity
):
    """Control the global Calefa vacation mode."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:beach"

    def __init__(
        self, coordinator: WavinCalefaCoordinator, entry: ConfigEntry
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_vacation_control"
        _set_presentation(
            self, coordinator, entry, GROUP_SYSTEM, "Ferie", "Vacation"
        )

    @property
    def is_on(self) -> bool | None:
        """Return whether global vacation mode is active."""
        value = self.coordinator.data.get("vacation")
        return bool(value) if isinstance(value, int) else None

    async def async_turn_on(self, **kwargs: object) -> None:
        """Activate vacation mode."""
        await self.coordinator.async_write_holding_register(27, 1)

    async def async_turn_off(self, **kwargs: object) -> None:
        """Deactivate vacation mode."""
        await self.coordinator.async_write_holding_register(27, 0)


class WavinCalefaVacationForDhwSwitch(
    CoordinatorEntity[WavinCalefaCoordinator], SwitchEntity
):
    """Control whether vacation mode applies to domestic hot water."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:water-boiler"

    def __init__(
        self, coordinator: WavinCalefaCoordinator, entry: ConfigEntry
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_vacation_for_dhw"
        _set_presentation(
            self,
            coordinator,
            entry,
            GROUP_DHW,
            "Ferie BV",
            "Vacation HW",
        )

    @property
    def is_on(self) -> bool | None:
        """Return whether vacation mode applies to domestic hot water."""
        value = self.coordinator.data.get("vacation_for_dhw")
        return bool(value) if isinstance(value, int) else None

    async def async_turn_on(self, **kwargs: object) -> None:
        """Apply vacation mode to domestic hot water."""
        await self.coordinator.async_write_holding_register(6525, 1)

    async def async_turn_off(self, **kwargs: object) -> None:
        """Exclude domestic hot water from vacation mode."""
        await self.coordinator.async_write_holding_register(6525, 0)


class WavinCalefaVacationForChSwitch(
    CoordinatorEntity[WavinCalefaCoordinator], SwitchEntity
):
    """Control whether vacation mode applies to central heating."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:radiator"

    def __init__(
        self, coordinator: WavinCalefaCoordinator, entry: ConfigEntry
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_vacation_for_ch"
        _set_presentation(
            self,
            coordinator,
            entry,
            GROUP_HEATING,
            "Ferie CV",
            "Vacation CH",
        )

    @property
    def is_on(self) -> bool | None:
        """Return whether vacation mode applies to central heating."""
        value = self.coordinator.data.get("vacation_for_ch")
        return bool(value) if isinstance(value, int) else None

    async def async_turn_on(self, **kwargs: object) -> None:
        """Apply vacation mode to central heating."""
        await self.coordinator.async_write_holding_register(7505, 1)

    async def async_turn_off(self, **kwargs: object) -> None:
        """Exclude central heating from vacation mode."""
        await self.coordinator.async_write_holding_register(7505, 0)


class WavinCalefaRoomScheduleSwitch(
    CoordinatorEntity[WavinCalefaCoordinator], SwitchEntity
):
    """Control the room heating schedule with its inverted register logic."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:calendar-clock"

    def __init__(
        self, coordinator: WavinCalefaCoordinator, entry: ConfigEntry
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_room_schedule"
        _set_presentation(
            self,
            coordinator,
            entry,
            GROUP_ROOM,
            "Skema",
            "Schedule",
        )

    @property
    def is_on(self) -> bool | None:
        """Return whether the room schedule is enabled."""
        value = self.coordinator.data.get("room_schedule_disabled")
        return value == 0 if isinstance(value, int) else None

    async def async_turn_on(self, **kwargs: object) -> None:
        """Enable the room schedule."""
        await self.coordinator.async_write_holding_register(7508, 0)

    async def async_turn_off(self, **kwargs: object) -> None:
        """Disable the room schedule."""
        await self.coordinator.async_write_holding_register(7508, 1)


class WavinCalefaRoomTemporaryModeSwitch(
    CoordinatorEntity[WavinCalefaCoordinator], SwitchEntity
):
    """Control a temporary room-temperature override."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:timer-cog-outline"

    def __init__(
        self, coordinator: WavinCalefaCoordinator, entry: ConfigEntry
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_room_temporary_mode"
        _set_presentation(
            self,
            coordinator,
            entry,
            GROUP_ROOM,
            "Midl. mode",
            "Temp. mode",
        )

    @property
    def is_on(self) -> bool | None:
        """Return whether a temporary room override is active."""
        value = self.coordinator.data.get("room_temporary_mode")
        return bool(value) if isinstance(value, int) else None

    async def async_turn_on(self, **kwargs: object) -> None:
        """Activate a temporary override for the default 15 minutes."""
        expiry = int(time.time()) + 15 * 60
        await self.coordinator.async_write_holding_registers(
            {
                7510: (expiry >> 16) & 0xFFFF,
                7511: expiry & 0xFFFF,
                7509: 1,
            }
        )

    async def async_turn_off(self, **kwargs: object) -> None:
        """Deactivate the temporary override."""
        await self.coordinator.async_write_holding_register(7509, 0)


class WavinCalefaReturnLimiterPrioritySwitch(
    CoordinatorEntity[WavinCalefaCoordinator], SwitchEntity
):
    """Allow the return limiter to override minimum supply temperature."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:call-merge"

    def __init__(
        self, coordinator: WavinCalefaCoordinator, entry: ConfigEntry
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self._attr_unique_id = (
            f"{entry.entry_id}_return_limiter_priority_over_supply"
        )
        _set_presentation(
            self,
            coordinator,
            entry,
            GROUP_HEATING,
            "Returprioritet",
            "Return priority",
        )

    @property
    def is_on(self) -> bool | None:
        """Return whether return limiting has priority over supply control."""
        value = self.coordinator.data.get(
            "return_limiter_priority_over_supply"
        )
        return bool(value) if isinstance(value, int) else None

    async def async_turn_on(self, **kwargs: object) -> None:
        """Give return limiting priority over supply control."""
        await self.coordinator.async_write_holding_register(7718, 1)

    async def async_turn_off(self, **kwargs: object) -> None:
        """Remove return limiting priority over supply control."""
        await self.coordinator.async_write_holding_register(7718, 0)
