"""Shared heat-demand detection for Wavin Calefa.

Watches a set of existing Home Assistant thermostats, plain sensor-only
rooms, and valve/actuator entities, and answers two questions purely from
current state: does *anything* currently need heat, and is *everything*
currently warm enough. auto_standby.py is the only consumer: it uses these
to decide when it's safe to put the whole Calefa unit into standby, and
when to release it again.

This used to also drive a Sentio-emulation "heat call" that forced Calefa's
RUM temporary-room override open whenever demand was detected. That has
been removed: Calefa has no live per-room reading to modulate the CVV valve
against, so engaging the override always drove it fully open regardless of
how small the real deficit was - blunt, and hard on afkoling for no
proportionate benefit. See CHANGELOG for the removal.
"""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import (
    CONF_DEMAND_AC_ENTITIES,
    CONF_DEMAND_CLIMATE_ENTITIES,
    CONF_DEMAND_HYSTERESIS,
    CONF_DEMAND_RESTART_DELAY_MINUTES,
    CONF_DEMAND_SENSOR_ROOMS,
    CONF_DEMAND_VALVE_ENTITIES,
    CONF_DEMAND_VALVE_THRESHOLD,
    DEFAULT_DEMAND_HYSTERESIS,
    DEFAULT_DEMAND_RESTART_DELAY_MINUTES,
    DEFAULT_DEMAND_VALVE_THRESHOLD,
)


class WavinCalefaDemandTracker:
    """Answer whether configured rooms currently need heat, from live state."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the tracker."""
        self.hass = hass
        self.entry = entry

    @property
    def options(self) -> dict[str, Any]:
        """Return the entry's options."""
        return self.entry.options

    @property
    def climate_entities(self) -> list[str]:
        """Return the configured thermostat entities."""
        return list(self.options.get(CONF_DEMAND_CLIMATE_ENTITIES, []))

    @property
    def ac_entities(self) -> list[str]:
        """Return the configured AC/cooling entities that suppress demand."""
        return list(self.options.get(CONF_DEMAND_AC_ENTITIES, []))

    @property
    def valve_entities(self) -> list[str]:
        """Return actuator entities (e.g. an after-heater valve) that signal demand by opening."""
        return list(self.options.get(CONF_DEMAND_VALVE_ENTITIES, []))

    @property
    def sensor_rooms(self) -> list[tuple[str, float | str]]:
        """Parse sensor rooms with a numeric or entity-backed target."""
        raw = self.options.get(CONF_DEMAND_SENSOR_ROOMS, "")
        rooms: list[tuple[str, float | str]] = []
        for line in str(raw).splitlines():
            line = line.strip()
            if not line or ":" not in line:
                continue
            entity_id, _, target_text = line.partition(":")
            try:
                target: float | str = float(target_text.strip())
            except ValueError:
                target = target_text.strip()
                if "." not in target:
                    continue
            rooms.append((entity_id.strip(), target))
        return rooms

    def _sensor_room_target(self, target: float | str) -> float | None:
        """Resolve a sensor-room target, including an input_number entity."""
        if isinstance(target, (int, float)):
            return float(target)
        state = self.hass.states.get(target)
        if state is None or state.state in ("unknown", "unavailable"):
            return None
        try:
            return float(state.state)
        except ValueError:
            return None

    @property
    def has_demand_sources(self) -> bool:
        """Return whether any thermostat or sensor-only room is configured.

        Used by the auto-standby feature to decide whether it has a demand
        signal to work from at all.
        """
        return bool(self.climate_entities or self.sensor_rooms or self.valve_entities)

    def _valve_threshold(self) -> float:
        return float(
            self.options.get(CONF_DEMAND_VALVE_THRESHOLD, DEFAULT_DEMAND_VALVE_THRESHOLD)
        )

    def _hysteresis(self) -> float:
        return float(self.options.get(CONF_DEMAND_HYSTERESIS, DEFAULT_DEMAND_HYSTERESIS))

    def restart_delay_minutes(self) -> float:
        """Return the retained legacy restart-delay option.

        Automatic standby deliberately does not use this value: a valid heat
        request must release standby immediately.
        """
        return float(
            self.options.get(
                CONF_DEMAND_RESTART_DELAY_MINUTES,
                DEFAULT_DEMAND_RESTART_DELAY_MINUTES,
            )
        )

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
        valve_entities = self.valve_entities
        if not climate_entities and not sensor_rooms and not valve_entities:
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

        for entity_id, target_source in sensor_rooms:
            state = self.hass.states.get(entity_id)
            target = self._sensor_room_target(target_source)
            if state is None or state.state in ("unknown", "unavailable"):
                valid = False
                continue
            if target is None:
                valid = False
                continue
            try:
                current = float(state.state)
            except ValueError:
                valid = False
                continue
            if current <= target - hysteresis:
                demand = True

        # A configured actuator is a safety-critical demand source. If it
        # cannot be read, automatic standby must fail open rather than risk
        # blocking heat while the physical valve is open.
        threshold = self._valve_threshold()
        for entity_id in valve_entities:
            state = self.hass.states.get(entity_id)
            if state is None or state.state in ("unknown", "unavailable"):
                valid = False
                continue
            if state.state == "on":
                demand = True
                continue
            if state.state == "off":
                continue
            try:
                opening = float(state.state)
            except ValueError:
                valid = False
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
        valve_entities = self.valve_entities
        if not climate_entities and not sensor_rooms and not valve_entities:
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

        for entity_id, target_source in sensor_rooms:
            state = self.hass.states.get(entity_id)
            target = self._sensor_room_target(target_source)
            if state is None or state.state in ("unknown", "unavailable"):
                valid = False
                continue
            if target is None:
                valid = False
                continue
            try:
                current = float(state.state)
            except ValueError:
                valid = False
                continue
            if current < target:
                warm = False

        # Same fail-open treatment as evaluate_demand(): an unreadable
        # configured valve makes the complete standby decision invalid.
        threshold = self._valve_threshold()
        for entity_id in valve_entities:
            state = self.hass.states.get(entity_id)
            if state is None or state.state in ("unknown", "unavailable"):
                valid = False
                continue
            if state.state == "on":
                warm = False
                continue
            if state.state == "off":
                continue
            try:
                opening = float(state.state)
            except ValueError:
                valid = False
                continue
            if opening > threshold:
                warm = False

        return valid, warm
