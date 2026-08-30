"""Optional Sentio-style heat-call automation for Wavin Calefa.

Some Calefa installations have no physical Sentio room controller attached,
so the unit never receives a genuine room heat-call signal - space heating
stays gated by the unit's own summer-stop threshold with nothing to release
it. This module lets a set of existing Home Assistant climate entities
(thermostats) stand in for that missing controller: when they show real,
sustained heat demand, it temporarily raises summer-stop (only if summer-stop
is actually the thing blocking heat right now) and engages the unit's RUM
temporary-room override, the same two writable settings a real Sentio
controller's demand would otherwise release. Everything is reverted the
moment demand is gone, data becomes invalid, or the feature is turned off -
none of Calefa's own regulation, safety limits, or blocking logic is bypassed
or written around.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import timedelta
import logging
import time
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_time_interval,
)

from .const import (
    CONF_HEAT_CALL_AC_ENTITIES,
    CONF_HEAT_CALL_CLIMATE_ENTITIES,
    CONF_HEAT_CALL_ENABLED,
    CONF_HEAT_CALL_HYSTERESIS,
    CONF_HEAT_CALL_MAX_DURATION_MINUTES,
    CONF_HEAT_CALL_RESTART_DELAY_MINUTES,
    CONF_HEAT_CALL_ROOM_TARGET_TEMPERATURE,
    CONF_HEAT_CALL_SENSOR_ROOMS,
    CONF_HEAT_CALL_SUMMER_STOP_NORMAL,
    CONF_HEAT_CALL_SUMMER_STOP_OVERRIDE,
    CONF_HEAT_CALL_VALVE_ENTITIES,
    CONF_HEAT_CALL_VALVE_THRESHOLD,
    DEFAULT_HEAT_CALL_HYSTERESIS,
    DEFAULT_HEAT_CALL_MAX_DURATION_MINUTES,
    DEFAULT_HEAT_CALL_RESTART_DELAY_MINUTES,
    DEFAULT_HEAT_CALL_ROOM_TARGET_TEMPERATURE,
    DEFAULT_HEAT_CALL_SUMMER_STOP_NORMAL,
    DEFAULT_HEAT_CALL_SUMMER_STOP_OVERRIDE,
    DEFAULT_HEAT_CALL_VALVE_THRESHOLD,
    HEAT_CALL_FAULT_GRACE_MINUTES,
    HEAT_CALL_REFRESH_MINUTES,
    HEAT_CALL_REGISTER_ROOM_TEMPORARY_EXPIRY_HIGH,
    HEAT_CALL_REGISTER_ROOM_TEMPORARY_EXPIRY_LOW,
    HEAT_CALL_REGISTER_ROOM_TEMPORARY_MODE,
    HEAT_CALL_REGISTER_ROOM_TEMPORARY_TEMPERATURE,
    HEAT_CALL_REGISTER_SUMMER_STOP,
)
from .coordinator import WavinCalefaCoordinator

LOGGER = logging.getLogger(__name__)


class WavinCalefaHeatCallManager:
    """Detect thermostat heat demand and emulate a Sentio-style heat call."""

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, coordinator: WavinCalefaCoordinator
    ) -> None:
        """Initialize the manager."""
        self.hass = hass
        self.entry = entry
        self.coordinator = coordinator
        self.runtime_enabled = True
        self._listeners: list[Callable[[], None]] = []
        self._unsub_state: Callable[[], None] | None = None
        self._unsub_timer: Callable[[], None] | None = None
        self._unsub_coordinator: Callable[[], None] | None = None
        self._call_active = False
        self._call_started_at: float | None = None
        self._baseline_summer_stop: float | None = None
        self._fault_since: float | None = None
        self._demand_since: float | None = None
        self.data_valid = False
        self.demand = False
        self.summer_stop_blocking = False
        self.fault = False

    @property
    def options(self) -> dict[str, Any]:
        """Return the entry's options."""
        return self.entry.options

    @property
    def configured(self) -> bool:
        """Return whether the feature has been set up at all."""
        return bool(self.options.get(CONF_HEAT_CALL_ENABLED, False))

    @property
    def climate_entities(self) -> list[str]:
        """Return the configured thermostat entities."""
        return list(self.options.get(CONF_HEAT_CALL_CLIMATE_ENTITIES, []))

    @property
    def ac_entities(self) -> list[str]:
        """Return the configured AC/cooling entities that suppress demand."""
        return list(self.options.get(CONF_HEAT_CALL_AC_ENTITIES, []))

    @property
    def valve_entities(self) -> list[str]:
        """Return actuator entities (e.g. an after-heater valve) that signal demand by opening."""
        return list(self.options.get(CONF_HEAT_CALL_VALVE_ENTITIES, []))

    @property
    def sensor_rooms(self) -> list[tuple[str, float]]:
        """Parse 'entity_id:target_temperature' lines for thermostat-less rooms."""
        raw = self.options.get(CONF_HEAT_CALL_SENSOR_ROOMS, "")
        rooms: list[tuple[str, float]] = []
        for line in str(raw).splitlines():
            line = line.strip()
            if not line or ":" not in line:
                continue
            entity_id, _, target_text = line.partition(":")
            try:
                target = float(target_text.strip())
            except ValueError:
                continue
            rooms.append((entity_id.strip(), target))
        return rooms

    @property
    def has_demand_sources(self) -> bool:
        """Return whether any thermostat or sensor-only room is configured.

        Used by the auto-standby feature to decide whether it has a demand
        signal to work from at all - it shares this manager's entity lists
        rather than collecting its own.
        """
        return bool(self.climate_entities or self.sensor_rooms)

    def _valve_threshold(self) -> float:
        return float(
            self.options.get(
                CONF_HEAT_CALL_VALVE_THRESHOLD, DEFAULT_HEAT_CALL_VALVE_THRESHOLD
            )
        )

    @property
    def call_active(self) -> bool:
        """Return whether a heat call is currently being held active."""
        return self._call_active

    @property
    def active(self) -> bool:
        """Return whether the feature is both configured and currently enabled."""
        return self.configured and self.runtime_enabled

    def _hysteresis(self) -> float:
        return float(
            self.options.get(CONF_HEAT_CALL_HYSTERESIS, DEFAULT_HEAT_CALL_HYSTERESIS)
        )

    def restart_delay_minutes(self) -> float:
        """Return how long demand must hold before acting on it.

        Public: shared by the auto-standby feature as the delay before it
        releases standby once real demand returns, mirroring how both
        behaviours were driven by the same setting in the original
        automation this integration replaces.
        """
        return float(
            self.options.get(
                CONF_HEAT_CALL_RESTART_DELAY_MINUTES,
                DEFAULT_HEAT_CALL_RESTART_DELAY_MINUTES,
            )
        )

    def _summer_stop_override(self) -> float:
        return float(
            self.options.get(
                CONF_HEAT_CALL_SUMMER_STOP_OVERRIDE,
                DEFAULT_HEAT_CALL_SUMMER_STOP_OVERRIDE,
            )
        )

    def _room_target(self) -> float:
        return float(
            self.options.get(
                CONF_HEAT_CALL_ROOM_TARGET_TEMPERATURE,
                DEFAULT_HEAT_CALL_ROOM_TARGET_TEMPERATURE,
            )
        )

    def _max_duration_seconds(self) -> float:
        return (
            float(
                self.options.get(
                    CONF_HEAT_CALL_MAX_DURATION_MINUTES,
                    DEFAULT_HEAT_CALL_MAX_DURATION_MINUTES,
                )
            )
            * 60
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
        """Start watching the configured entities."""
        if not self.configured:
            return
        watched = [
            *self.climate_entities,
            *self.ac_entities,
            *[entity_id for entity_id, _ in self.sensor_rooms],
            *self.valve_entities,
        ]
        if watched:
            self._unsub_state = async_track_state_change_event(
                self.hass, watched, self._handle_state_event
            )
        self._unsub_timer = async_track_time_interval(
            self.hass, self._handle_timer, timedelta(minutes=HEAT_CALL_REFRESH_MINUTES)
        )
        # Also react to coordinator polls (every scan_interval), not just the
        # 30-minute refresh timer above: this is what lets a call notice
        # promptly when the auto-standby feature releases the standby
        # register, instead of waiting up to 30 minutes to retry.
        self._unsub_coordinator = self.coordinator.async_add_listener(
            self._handle_coordinator_update
        )
        await self._async_evaluate()

    def async_unload(self) -> None:
        """Stop watching entities and release any held override."""
        if self._unsub_state is not None:
            self._unsub_state()
            self._unsub_state = None
        if self._unsub_timer is not None:
            self._unsub_timer()
            self._unsub_timer = None
        if self._unsub_coordinator is not None:
            self._unsub_coordinator()
            self._unsub_coordinator = None

    @callback
    def _handle_state_event(self, event: Event) -> None:
        self.hass.async_create_task(self._async_evaluate())

    async def _handle_timer(self, now: Any) -> None:
        await self._async_evaluate()

    @callback
    def _handle_coordinator_update(self) -> None:
        self.hass.async_create_task(self._async_evaluate())

    def _cooling_active(self) -> bool:
        """Return true if any configured AC entity is actively cooling."""
        for entity_id in self.ac_entities:
            state = self.hass.states.get(entity_id)
            if state is not None and state.attributes.get("hvac_action") == "cooling":
                return True
        return False

    def evaluate_demand(self) -> tuple[bool, bool]:
        """Return (data_valid, demand) across thermostats, sensor rooms, and valves."""
        climate_entities = self.climate_entities
        sensor_rooms = self.sensor_rooms
        if not climate_entities and not sensor_rooms:
            return False, False
        hysteresis = self._hysteresis()
        cooling = self._cooling_active()
        valid = True
        demand = False

        for entity_id in climate_entities:
            state = self.hass.states.get(entity_id)
            if state is None or state.state in ("unknown", "unavailable"):
                valid = False
                continue
            current = state.attributes.get("current_temperature")
            target = state.attributes.get("temperature")
            if not isinstance(current, (int, float)) or not isinstance(
                target, (int, float)
            ):
                valid = False
                continue
            if cooling and state.state == "off":
                continue
            if (
                current <= target - hysteresis
                or state.attributes.get("hvac_action") == "heating"
            ):
                demand = True

        for entity_id, target in sensor_rooms:
            state = self.hass.states.get(entity_id)
            if state is None or state.state in ("unknown", "unavailable"):
                valid = False
                continue
            try:
                current = float(state.state)
            except ValueError:
                valid = False
                continue
            if current <= target - hysteresis:
                demand = True

        # Valve-driven sources (e.g. a ventilation unit's water-coil
        # after-heater) are best-effort: unlike thermostats and sensor
        # rooms, their absence or unavailability never invalidates data for
        # everything else, since an actuator reading tends to be flakier
        # than a thermostat or plain temperature sensor.
        threshold = self._valve_threshold()
        for entity_id in self.valve_entities:
            state = self.hass.states.get(entity_id)
            if state is None:
                continue
            try:
                opening = float(state.state)
            except ValueError:
                continue
            if opening > threshold:
                demand = True

        return valid, demand

    def evaluate_all_warm(self) -> tuple[bool, bool]:
        """Return (data_valid, all_warm): true once every configured source is warm enough.

        The mirror-image, zero-margin counterpart to evaluate_demand(), used
        by the auto-standby feature to decide when it's safe to consider
        putting the whole unit into standby. Kept as a separate method
        (rather than a parametrized version of evaluate_demand()) since the
        per-source comparisons are inverted, not just margin-shifted.
        """
        climate_entities = self.climate_entities
        sensor_rooms = self.sensor_rooms
        if not climate_entities and not sensor_rooms:
            return False, False
        cooling = self._cooling_active()
        valid = True
        warm = True

        for entity_id in climate_entities:
            state = self.hass.states.get(entity_id)
            if state is None or state.state in ("unknown", "unavailable"):
                valid = False
                continue
            current = state.attributes.get("current_temperature")
            target = state.attributes.get("temperature")
            if not isinstance(current, (int, float)) or not isinstance(
                target, (int, float)
            ):
                valid = False
                continue
            if cooling and state.state == "off":
                continue
            if current < target or state.attributes.get("hvac_action") == "heating":
                warm = False

        for entity_id, target in sensor_rooms:
            state = self.hass.states.get(entity_id)
            if state is None or state.state in ("unknown", "unavailable"):
                valid = False
                continue
            try:
                current = float(state.state)
            except ValueError:
                valid = False
                continue
            if current < target:
                warm = False

        # Same best-effort treatment as evaluate_demand(): an unavailable
        # valve sensor never invalidates data for everything else.
        threshold = self._valve_threshold()
        for entity_id in self.valve_entities:
            state = self.hass.states.get(entity_id)
            if state is None:
                continue
            try:
                opening = float(state.state)
            except ValueError:
                continue
            if opening > threshold:
                warm = False

        return valid, warm

    def _summer_stop_currently_blocking(self) -> bool:
        outdoor = self.coordinator.data.get("outdoor_temperature")
        normal = self.options.get(
            CONF_HEAT_CALL_SUMMER_STOP_NORMAL, DEFAULT_HEAT_CALL_SUMMER_STOP_NORMAL
        )
        if not isinstance(outdoor, (int, float)):
            return False
        return outdoor >= float(normal)

    async def _async_evaluate(self) -> None:
        """Recompute state and start/stop the heat call as needed."""
        if not self.active:
            self._demand_since = None
            if self._call_active:
                await self._async_stop("deaktiveret")
            self._set_public_state(False, False, False, False)
            return

        data_valid, demand = self.evaluate_demand()
        summer_stop_blocking = self._summer_stop_currently_blocking()

        if not data_valid:
            self._demand_since = None
            if self._call_active:
                await self._async_stop("ugyldige data")
            self._set_public_state(False, False, summer_stop_blocking, False)
            return

        if not demand:
            self._demand_since = None
            if self._call_active:
                await self._async_stop("intet behov")
            self._set_public_state(True, False, summer_stop_blocking, False)
            return

        # Real, valid demand from here on. A brief dip - a window airing out
        # a sensor-only room, for instance - shouldn't itself trigger a
        # call: demand has to hold for the configured delay first. Once a
        # call is already active, refresh it immediately on every re-check
        # instead, since debouncing there would only risk letting it lapse.
        if not self._call_active:
            if self._demand_since is None:
                self._demand_since = time.time()
            if time.time() - self._demand_since < self.restart_delay_minutes() * 60:
                self._set_public_state(True, False, summer_stop_blocking, False)
                return
            if self.coordinator.data.get("standby") == 1:
                # The whole unit is in standby - most likely the
                # auto-standby feature holding it there. Starting a call
                # now would be pointless; keep waiting and re-check on the
                # next state change or coordinator poll, without resetting
                # the demand timer (the demand itself hasn't gone away).
                self._set_public_state(True, False, summer_stop_blocking, False)
                return
            await self._async_start()
        else:
            if (
                self._call_started_at is not None
                and time.time() - self._call_started_at > self._max_duration_seconds()
            ):
                LOGGER.warning(
                    "Wavin Calefa heat call held active past its safety limit, restarting it"
                )
                await self._async_stop("sikkerhedsgraense")
                await self._async_start()
            else:
                await self._async_refresh()

        fault = self._check_fault()
        self._set_public_state(True, True, summer_stop_blocking, fault)

    def _set_public_state(
        self, data_valid: bool, demand: bool, summer_stop_blocking: bool, fault: bool
    ) -> None:
        changed = (
            data_valid != self.data_valid
            or demand != self.demand
            or summer_stop_blocking != self.summer_stop_blocking
            or fault != self.fault
        )
        self.data_valid = data_valid
        self.demand = demand
        self.summer_stop_blocking = summer_stop_blocking
        self.fault = fault
        if changed:
            self._notify_listeners()

    def _check_fault(self) -> bool:
        """Return true if the call has been active for a while with no response."""
        if not self._call_active or self._call_started_at is None:
            self._fault_since = None
            return False
        pump_status = self.coordinator.data.get("itc_pump_status")
        valve = self.coordinator.data.get("cvv_valve_position")
        responded = pump_status == 1 or (
            isinstance(valve, (int, float)) and valve > 1
        )
        if responded:
            self._fault_since = None
            return False
        elapsed = time.time() - self._call_started_at
        return elapsed > HEAT_CALL_FAULT_GRACE_MINUTES * 60

    async def _async_start(self) -> None:
        """Begin holding the heat-call override, capturing the current baseline."""
        current_summer_stop = self.coordinator.data.get("itc_max_outdoor_temp")
        if isinstance(current_summer_stop, (int, float)) and current_summer_stop < self._summer_stop_override():
            self._baseline_summer_stop = float(current_summer_stop)
        elif self._baseline_summer_stop is None:
            self._baseline_summer_stop = self.options.get(
                CONF_HEAT_CALL_SUMMER_STOP_NORMAL, DEFAULT_HEAT_CALL_SUMMER_STOP_NORMAL
            )
        self._call_active = True
        self._call_started_at = time.time()
        await self._async_refresh()

    async def _async_refresh(self) -> None:
        """Write the override registers again, only touching what's needed."""
        registers: dict[int, int] = {}
        if self.summer_stop_blocking:
            override_raw = round(self._summer_stop_override() * 100) & 0xFFFF
            current = self.coordinator.data.get("itc_max_outdoor_temp")
            if not isinstance(current, (int, float)) or round(current * 100) != override_raw:
                registers[HEAT_CALL_REGISTER_SUMMER_STOP] = override_raw

        target_raw = round(self._room_target() * 100) & 0xFFFF
        expiry = int(time.time()) + HEAT_CALL_REFRESH_MINUTES * 60 * 2
        registers[HEAT_CALL_REGISTER_ROOM_TEMPORARY_TEMPERATURE] = target_raw
        registers[HEAT_CALL_REGISTER_ROOM_TEMPORARY_EXPIRY_HIGH] = (expiry >> 16) & 0xFFFF
        registers[HEAT_CALL_REGISTER_ROOM_TEMPORARY_EXPIRY_LOW] = expiry & 0xFFFF
        registers[HEAT_CALL_REGISTER_ROOM_TEMPORARY_MODE] = 1

        try:
            await self.coordinator.async_write_holding_registers(registers)
        except Exception:  # noqa: BLE001 - surfaced as the fault sensor, not raised
            LOGGER.exception("Wavin Calefa heat call: failed to refresh override registers")

    async def _async_stop(self, reason: str) -> None:
        """Release the heat-call override and restore the baseline summer stop."""
        LOGGER.debug("Wavin Calefa heat call ending (%s)", reason)
        restore = self._baseline_summer_stop
        if restore is None:
            restore = self.options.get(
                CONF_HEAT_CALL_SUMMER_STOP_NORMAL, DEFAULT_HEAT_CALL_SUMMER_STOP_NORMAL
            )
        registers = {
            HEAT_CALL_REGISTER_ROOM_TEMPORARY_MODE: 0,
            HEAT_CALL_REGISTER_SUMMER_STOP: round(float(restore) * 100) & 0xFFFF,
        }
        try:
            await self.coordinator.async_write_holding_registers(registers)
        except Exception:  # noqa: BLE001 - best-effort revert, don't block state reset
            LOGGER.exception("Wavin Calefa heat call: failed to revert override registers")
        self._call_active = False
        self._call_started_at = None
        self._baseline_summer_stop = None
        self._fault_since = None

    def status_text(self, danish: bool) -> str:
        """Return a short, human-readable status string."""
        if not self.configured:
            return "Ikke sat op" if danish else "Not configured"
        if not self.runtime_enabled:
            return "Fra" if danish else "Off"
        if not self.data_valid:
            return "Fejlsikring" if danish else "Failsafe"
        if self.fault:
            return "Intet svar fra Calefa" if danish else "No response from Calefa"
        if self.call_active:
            return "Varmekald aktivt" if danish else "Heat call active"
        if not self.demand:
            return "Intet behov" if danish else "No demand"
        return "Venter" if danish else "Waiting"
