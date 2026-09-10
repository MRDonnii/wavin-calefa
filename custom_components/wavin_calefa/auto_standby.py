"""Optional automatic-standby feature for Wavin Calefa.

Puts the whole Calefa unit into standby once every configured demand source
(the same thermostats, sensor-only rooms, and valve entities the demand
tracker is configured with) is warm enough for long enough, then releases it
again the moment any source is below target, actively heating/open, or the
underlying data becomes invalid. Releasing standby is never debounced: heat
always wins immediately.
Standby is only ever engaged after confirming the unit's own pump call, pump
status, and CVV valve position have actually settled - retried a few times
before giving up and reporting a fault instead of holding an unconfirmed
standby indefinitely. Manually toggling the unit's own standby switch is
always respected: this feature never fights a change it didn't make itself.
"""

from __future__ import annotations

from collections.abc import Callable
import asyncio
import logging
import time
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.storage import Store

from .const import (
    AUTO_STANDBY_PUMPSTOP_RETRY_COUNT,
    AUTO_STANDBY_PUMPSTOP_RETRY_DELAY_SECONDS,
    CONF_AUTO_STANDBY_DELAY_MINUTES,
    CONF_AUTO_STANDBY_ENABLED,
    DEFAULT_AUTO_STANDBY_DELAY_MINUTES,
    REGISTER_STANDBY,
)
from .coordinator import WavinCalefaCoordinator
from .demand import WavinCalefaDemandTracker

LOGGER = logging.getLogger(__name__)


class WavinCalefaAutoStandbyManager:
    """Put Calefa into standby when nothing configured needs heat."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        coordinator: WavinCalefaCoordinator,
        demand: WavinCalefaDemandTracker,
    ) -> None:
        """Initialize the manager."""
        self.hass = hass
        self.entry = entry
        self.coordinator = coordinator
        self._demand = demand
        self.runtime_enabled = True
        self._listeners: list[Callable[[], None]] = []
        self._unsub_state: Callable[[], None] | None = None
        self._unsub_coordinator: Callable[[], None] | None = None
        self._engaged = False
        self._evaluation_lock = asyncio.Lock()
        self._stopped = False
        self._store = Store(hass, 1, f"wavin_calefa.{entry.entry_id}.auto_standby", atomic_writes=True)
        self._warm_since: float | None = None
        self._demand_since: float | None = None
        self._pumpstop_confirmed = False
        self._pumpstop_error = False
        self._pumpstop_attempts = 0
        self._pumpstop_next_retry_at: float | None = None
        self.data_valid = False
        self.all_warm = False
        self.demand = False
        self.standby_engaged = False
        self.pumpstop_confirmed = False
        self.fault = False

    @property
    def options(self) -> dict[str, Any]:
        """Return the entry's options."""
        return self.entry.options

    @property
    def configured(self) -> bool:
        """Return whether the feature has been set up and has a demand signal."""
        return bool(
            self.options.get(CONF_AUTO_STANDBY_ENABLED, False)
        ) and self._demand.has_demand_sources

    @property
    def active(self) -> bool:
        """Return whether the feature is both configured and currently enabled."""
        return self.configured and self.runtime_enabled

    def _delay_minutes(self) -> float:
        return float(
            self.options.get(
                CONF_AUTO_STANDBY_DELAY_MINUTES, DEFAULT_AUTO_STANDBY_DELAY_MINUTES
            )
        )

    def async_add_listener(self, update_callback: Callable[[], None]) -> Callable[[], None]:
        """Register a callback invoked whenever the manager's public state changes."""
        self._listeners.append(update_callback)

        def _remove() -> None:
            if update_callback in self._listeners:
                self._listeners.remove(update_callback)

        return _remove

    def _notify_listeners(self) -> None:
        for update_callback in list(self._listeners):
            update_callback()

    async def async_setup(self) -> None:
        """Start watching the demand sources."""
        if not self.configured:
            return
        saved = await self._store.async_load()
        self._engaged = bool(saved and saved.get("engaged"))
        watched = [
            *self._demand.climate_entities,
            *self._demand.ac_entities,
            *[entity_id for entity_id, _ in self._demand.sensor_rooms],
            *self._demand.valve_entities,
        ]
        if watched:
            self._unsub_state = async_track_state_change_event(
                self.hass, watched, self._handle_state_event
            )
        self._unsub_coordinator = self.coordinator.async_add_listener(
            self._handle_coordinator_update
        )
        await self._async_evaluate()

    def async_unload(self) -> None:
        """Stop watching entities and release any held standby."""
        self._stopped = True
        if self._unsub_state is not None:
            self._unsub_state()
            self._unsub_state = None
        if self._unsub_coordinator is not None:
            self._unsub_coordinator()
            self._unsub_coordinator = None

    @callback
    def _handle_state_event(self, event: Event) -> None:
        self.hass.async_create_task(self._async_evaluate())

    @callback
    def _handle_coordinator_update(self) -> None:
        self.hass.async_create_task(self._async_evaluate())

    async def _async_evaluate(self) -> None:
        """Recompute state and engage/release standby as needed."""
        async with self._evaluation_lock:
            if not self._stopped:
                await self._async_evaluate_locked()

    async def _async_evaluate_locked(self) -> None:
        if not self.active:
            self._warm_since = None
            self._demand_since = None
            if self._engaged:
                await self._async_release("deaktiveret")
            self._set_public_state(False, False, False, False, False, False)
            return

        valid_demand, demand = self._demand.evaluate_demand()
        valid_warm, all_warm = self._demand.evaluate_all_warm()
        data_valid = valid_demand and valid_warm

        if not data_valid:
            self._warm_since = None
            self._demand_since = None
            if self._engaged:
                await self._async_release("ugyldige data")
            self._set_public_state(False, False, False, False, False, False)
            return

        # Heat always wins over automatic standby. ``all_warm`` deliberately
        # has no hysteresis, so it also catches a radiator beginning to open
        # in the band between target and target-hysteresis. Do this before
        # the ownership branches: after a restart or lost Store state, a
        # stale standby must not block a real, valid heat request forever.
        needs_heat = demand or not all_warm
        if self.coordinator.data.get("standby") == 1 and needs_heat:
            await self._async_release("varmebehov")
            self._set_public_state(True, all_warm, demand, False, False, False)
            return

        if not self._engaged:
            if not all_warm or demand:
                self._warm_since = None
                self._set_public_state(True, all_warm, demand, False, False, False)
                return
            if self._warm_since is None:
                self._warm_since = time.time()
            if time.time() - self._warm_since < self._delay_minutes() * 60:
                self._set_public_state(True, all_warm, demand, False, False, False)
                return
            if self.coordinator.data.get("standby") == 1:
                # Already in standby but not through us (manual, or set
                # before this feature was enabled) - leave it alone rather
                # than claim ownership of something we didn't engage.
                self._set_public_state(True, all_warm, demand, False, False, False)
                return
            await self._async_engage()
            self._set_public_state(True, all_warm, demand, True, False, False)
            return

        # Engaged from here on.
        if self.coordinator.data.get("standby") == 0:
            # Someone released it manually - respect that instead of
            # fighting it back on.
            self._forget_engagement()
            await self._store.async_save({"engaged": False})
            self._set_public_state(True, all_warm, demand, False, False, False)
            return

        self._demand_since = None

        await self._async_check_pumpstop_safe()
        self._set_public_state(
            True, all_warm, demand, True, self._pumpstop_confirmed, self._pumpstop_error
        )

    def _set_public_state(
        self,
        data_valid: bool,
        all_warm: bool,
        demand: bool,
        standby_engaged: bool,
        pumpstop_confirmed: bool,
        fault: bool,
    ) -> None:
        changed = (
            data_valid != self.data_valid
            or all_warm != self.all_warm
            or demand != self.demand
            or standby_engaged != self.standby_engaged
            or pumpstop_confirmed != self.pumpstop_confirmed
            or fault != self.fault
        )
        self.data_valid = data_valid
        self.all_warm = all_warm
        self.demand = demand
        self.standby_engaged = standby_engaged
        self.pumpstop_confirmed = pumpstop_confirmed
        self.fault = fault
        if changed:
            self._notify_listeners()

    def _pumpstop_safe(self) -> bool | None:
        """Return whether the pump call/status/valve confirm standby actually took, or None if not known yet."""
        demand = self.coordinator.data.get("itc_pump_demand")
        status = self.coordinator.data.get("itc_pump_status")
        valve = self.coordinator.data.get("cvv_valve_position")
        if (
            not isinstance(demand, int)
            or not isinstance(status, int)
            or not isinstance(valve, (int, float))
        ):
            return None
        return demand == 0 and status == 0 and valve <= 1

    async def _async_check_pumpstop_safe(self) -> None:
        """Confirm the pump has actually stopped, retrying standby a few times if not."""
        if self._pumpstop_confirmed:
            return
        safe = self._pumpstop_safe()
        if safe:
            self._pumpstop_confirmed = True
            # A late but successful physical stop is healthy. Do not leave a
            # stale latched fault after Calefa's normal pump overrun finishes.
            self._pumpstop_error = False
            return
        if self._pumpstop_error:
            return
        if safe is None:
            return
        if (
            self._pumpstop_next_retry_at is not None
            and time.time() < self._pumpstop_next_retry_at
        ):
            return
        self._pumpstop_attempts += 1
        if self._pumpstop_attempts > AUTO_STANDBY_PUMPSTOP_RETRY_COUNT:
            self._pumpstop_error = True
            LOGGER.warning(
                "Wavin Calefa auto standby: pump call/status/valve did not "
                "settle after %s attempts, standby is held but unconfirmed",
                AUTO_STANDBY_PUMPSTOP_RETRY_COUNT,
            )
            return
        await self.coordinator.async_write_holding_register(REGISTER_STANDBY, 1)
        self._pumpstop_next_retry_at = time.time() + AUTO_STANDBY_PUMPSTOP_RETRY_DELAY_SECONDS

    async def _async_engage(self) -> None:
        """Put the unit into standby and start confirming the pump stopped."""
        # Save intent first so a restart between the write and readback is safe.
        await self._store.async_save({"engaged": True})
        self._engaged = True
        await self.coordinator.async_write_holding_register(REGISTER_STANDBY, 1)
        self._engaged = True
        self._pumpstop_confirmed = False
        self._pumpstop_error = False
        self._pumpstop_attempts = 0
        self._pumpstop_next_retry_at = (
            time.time() + AUTO_STANDBY_PUMPSTOP_RETRY_DELAY_SECONDS
        )

    async def _async_release(self, reason: str) -> None:
        """Release standby and forget the automation's ownership of it."""
        LOGGER.debug("Wavin Calefa auto standby releasing (%s)", reason)
        await self.coordinator.async_write_holding_register(REGISTER_STANDBY, 0)
        self._forget_engagement()
        await self._store.async_save({"engaged": False})

    async def async_manual_standby(self, enabled: bool) -> None:
        """Serialize a manual choice and stop claiming automatic ownership."""
        async with self._evaluation_lock:
            await self.coordinator.async_write_holding_register(REGISTER_STANDBY, int(enabled))
            self._forget_engagement()
            await self._store.async_save({"engaged": False})

    def _forget_engagement(self) -> None:
        self._engaged = False
        self._warm_since = None
        self._demand_since = None
        self._pumpstop_confirmed = False
        self._pumpstop_error = False
        self._pumpstop_attempts = 0
        self._pumpstop_next_retry_at = None

    def status_text(self, danish: bool) -> str:
        """Return a short, human-readable status string."""
        if not self.configured:
            return "Ikke sat op" if danish else "Not configured"
        if not self.runtime_enabled:
            return "Fra" if danish else "Off"
        if not self.data_valid:
            return "Fejlsikring" if danish else "Failsafe"
        if self.fault:
            return "Pumpestop fejl" if danish else "Pump-stop fault"
        if self.coordinator.data.get("standby") == 1 and not self._engaged:
            return "Standby uden automatisk ejerskab" if danish else "Standby not owned by automation"
        if self.standby_engaged and self.pumpstop_confirmed:
            return "Standby aktiv" if danish else "Standby active"
        if self.standby_engaged:
            return "Bekræfter pumpestop" if danish else "Confirming pump stop"
        if self.all_warm and not self.demand:
            return "Venter" if danish else "Waiting"
        return "Normal drift" if danish else "Normal operation"
