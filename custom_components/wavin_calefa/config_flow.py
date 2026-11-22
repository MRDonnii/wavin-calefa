"""Config flow for Wavin Calefa."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_AUTO_STANDBY_DELAY_MINUTES,
    CONF_AUTO_STANDBY_ENABLED,
    CONF_DEMAND_AC_ENTITIES,
    CONF_DEMAND_CLIMATE_ENTITIES,
    CONF_DEMAND_HYSTERESIS,
    CONF_DEMAND_RESTART_DELAY_MINUTES,
    CONF_DEMAND_SENSOR_ROOMS,
    CONF_DEMAND_VALVE_ENTITIES,
    CONF_DEMAND_VALVE_THRESHOLD,
    CONF_HOST,
    CONF_LANGUAGE,
    CONF_PORT,
    CONF_SCAN_INTERVAL,
    CONF_UNIT_ID,
    DEFAULT_AUTO_STANDBY_DELAY_MINUTES,
    DEFAULT_DEMAND_HYSTERESIS,
    DEFAULT_DEMAND_RESTART_DELAY_MINUTES,
    DEFAULT_DEMAND_VALVE_THRESHOLD,
    DEFAULT_LANGUAGE,
    DEFAULT_NAME,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_UNIT_ID,
    DOMAIN,
    LANGUAGE_CHOICES,
    LANGUAGE_LABELS,
    MIN_SCAN_INTERVAL,
    PORT_SCAN_CANDIDATES,
    PORT_SCAN_TIMEOUT,
)
from .modbus import (
    WavinCalefaClient,
    WavinCalefaConnectionError,
    WavinCalefaModbusError,
)


def _schema(
    defaults: dict[str, Any] | None = None, *, include_port: bool = True
) -> vol.Schema:
    """Build the config flow schema."""
    defaults = defaults or {}
    fields: dict[Any, Any] = {
        vol.Required(CONF_NAME, default=defaults.get(CONF_NAME, DEFAULT_NAME)): str,
        vol.Required(CONF_HOST, default=defaults.get(CONF_HOST, "")): str,
        vol.Optional(
            CONF_LANGUAGE,
            default=defaults.get(CONF_LANGUAGE, DEFAULT_LANGUAGE),
        ): vol.In(LANGUAGE_LABELS),
        vol.Optional(
            CONF_UNIT_ID, default=defaults.get(CONF_UNIT_ID, DEFAULT_UNIT_ID)
        ): vol.All(vol.Coerce(int), vol.Range(min=1, max=247)),
        vol.Optional(
            CONF_SCAN_INTERVAL,
            default=defaults.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
        ): vol.All(vol.Coerce(int), vol.Range(min=MIN_SCAN_INTERVAL, max=3600)),
    }
    if include_port:
        fields[
            vol.Optional(CONF_PORT, default=defaults.get(CONF_PORT, DEFAULT_PORT))
        ] = vol.All(vol.Coerce(int), vol.Range(min=0, max=65535))
    return vol.Schema(fields)


def _demand_schema(defaults: dict[str, Any] | None = None) -> vol.Schema:
    """Build the schema for the shared heat-demand sources.

    These feed automatic standby (see _auto_standby_schema): a thermostat,
    sensor-only room, or valve/actuator configured here is what standby
    watches to decide when everything is warm enough to power the unit
    down, and when real demand means it should come back.
    """
    defaults = defaults or {}
    return vol.Schema(
        {
            vol.Optional(
                CONF_DEMAND_CLIMATE_ENTITIES,
                default=defaults.get(CONF_DEMAND_CLIMATE_ENTITIES, []),
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="climate", multiple=True)
            ),
            vol.Optional(
                CONF_DEMAND_AC_ENTITIES,
                default=defaults.get(CONF_DEMAND_AC_ENTITIES, []),
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="climate", multiple=True)
            ),
            vol.Optional(
                CONF_DEMAND_SENSOR_ROOMS,
                default=defaults.get(CONF_DEMAND_SENSOR_ROOMS, ""),
            ): selector.TextSelector(
                selector.TextSelectorConfig(multiline=True)
            ),
            vol.Optional(
                CONF_DEMAND_VALVE_ENTITIES,
                default=defaults.get(CONF_DEMAND_VALVE_ENTITIES, []),
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(
                    domain=["sensor", "binary_sensor"], multiple=True
                )
            ),
            vol.Optional(
                CONF_DEMAND_VALVE_THRESHOLD,
                default=defaults.get(
                    CONF_DEMAND_VALVE_THRESHOLD, DEFAULT_DEMAND_VALVE_THRESHOLD
                ),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0, max=100, step=1, mode=selector.NumberSelectorMode.BOX
                )
            ),
            vol.Optional(
                CONF_DEMAND_HYSTERESIS,
                default=defaults.get(
                    CONF_DEMAND_HYSTERESIS, DEFAULT_DEMAND_HYSTERESIS
                ),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0.1, max=5, step=0.1, mode=selector.NumberSelectorMode.BOX
                )
            ),
            vol.Optional(
                CONF_DEMAND_RESTART_DELAY_MINUTES,
                default=defaults.get(
                    CONF_DEMAND_RESTART_DELAY_MINUTES,
                    DEFAULT_DEMAND_RESTART_DELAY_MINUTES,
                ),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0, max=30, step=1, mode=selector.NumberSelectorMode.BOX
                )
            ),
        }
    )


def _auto_standby_schema(defaults: dict[str, Any] | None = None) -> vol.Schema:
    """Build the schema for the optional automatic-standby setup.

    Shares the demand schema's thermostats/sensor-rooms/valve entities and
    hysteresis as its demand signal instead of asking for the same rooms
    twice, so this schema only adds what's genuinely new: whether the
    feature is on, and how long everything has to stay warm before it
    actually engages standby.
    """
    defaults = defaults or {}
    return vol.Schema(
        {
            vol.Required(
                CONF_AUTO_STANDBY_ENABLED,
                default=defaults.get(CONF_AUTO_STANDBY_ENABLED, False),
            ): selector.BooleanSelector(),
            vol.Optional(
                CONF_AUTO_STANDBY_DELAY_MINUTES,
                default=defaults.get(
                    CONF_AUTO_STANDBY_DELAY_MINUTES,
                    DEFAULT_AUTO_STANDBY_DELAY_MINUTES,
                ),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=5, max=60, step=1, mode=selector.NumberSelectorMode.BOX
                )
            ),
        }
    )


def _candidate_ports(requested_port: int) -> tuple[int, ...]:
    """Return ordered candidate ports to probe."""
    ports: list[int] = []
    if requested_port:
        ports.append(requested_port)
    ports.extend(PORT_SCAN_CANDIDATES)
    return tuple(dict.fromkeys(port for port in ports if 1 <= port <= 65535))


def _probe_port(host: str, port: int, unit_id: int) -> bool:
    """Return true if a port responds like a Modbus TCP endpoint."""
    client = WavinCalefaClient(
        host=host,
        port=port,
        unit_id=unit_id,
        timeout=PORT_SCAN_TIMEOUT,
    )
    try:
        client.read_register(10)
    except WavinCalefaConnectionError:
        return False
    except WavinCalefaModbusError:
        return True
    return True


def _find_port(host: str, requested_port: int, unit_id: int) -> int | None:
    """Find the first reachable Modbus TCP port."""
    for port in _candidate_ports(requested_port):
        if _probe_port(host, port, unit_id):
            return port
    return None


class WavinCalefaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Wavin Calefa."""

    VERSION = 2

    def __init__(self) -> None:
        """Initialize the flow."""
        self._connection_data: dict[str, Any] | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            user_input[CONF_HOST] = host
            resolved_port = await self.hass.async_add_executor_job(
                _find_port,
                host,
                user_input.get(CONF_PORT, DEFAULT_PORT),
                user_input[CONF_UNIT_ID],
            )
            if resolved_port is None:
                errors["base"] = "cannot_connect"
            else:
                user_input[CONF_PORT] = resolved_port
                await self.async_set_unique_id(
                    f"{host}:{resolved_port}:{user_input[CONF_UNIT_ID]}"
                )
                self._abort_if_unique_id_configured()

            if not errors:
                self._connection_data = user_input
                return await self.async_step_auto_standby()

        return self.async_show_form(
            step_id="user",
            data_schema=_schema(user_input, include_port=False),
            errors=errors,
        )

    async def async_step_auto_standby(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Configure radiator demand sources during first-time setup."""
        if self._connection_data is None:
            return await self.async_step_user()

        errors: dict[str, str] = {}
        if user_input is not None:
            if _auto_standby_missing_sources(user_input):
                errors["base"] = "auto_standby_needs_demand_sources"
            else:
                return self.async_create_entry(
                    title=self._connection_data[CONF_NAME],
                    data=self._connection_data,
                    options=user_input,
                )

        defaults = user_input or {}
        schema_dict = {
            **_demand_schema(defaults).schema,
            **_auto_standby_schema(defaults).schema,
        }
        return self.async_show_form(
            step_id="auto_standby",
            data_schema=vol.Schema(schema_dict),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> "WavinCalefaOptionsFlow":
        """Create the options flow."""
        return WavinCalefaOptionsFlow(config_entry)


_DEMAND_OPTION_KEYS = (
    CONF_DEMAND_CLIMATE_ENTITIES,
    CONF_DEMAND_AC_ENTITIES,
    CONF_DEMAND_SENSOR_ROOMS,
    CONF_DEMAND_VALVE_ENTITIES,
    CONF_DEMAND_VALVE_THRESHOLD,
    CONF_DEMAND_HYSTERESIS,
    CONF_DEMAND_RESTART_DELAY_MINUTES,
)

_AUTO_STANDBY_OPTION_KEYS = (
    CONF_AUTO_STANDBY_ENABLED,
    CONF_AUTO_STANDBY_DELAY_MINUTES,
)

_OPTION_KEYS = _DEMAND_OPTION_KEYS + _AUTO_STANDBY_OPTION_KEYS


def _auto_standby_missing_sources(values: dict[str, Any]) -> bool:
    """Return whether enabled automatic standby lacks a demand source."""
    return bool(values.get(CONF_AUTO_STANDBY_ENABLED, False)) and not bool(
        values.get(CONF_DEMAND_CLIMATE_ENTITIES)
        or values.get(CONF_DEMAND_SENSOR_ROOMS)
        or values.get(CONF_DEMAND_VALVE_ENTITIES)
    )


class WavinCalefaOptionsFlow(config_entries.OptionsFlow):
    """Options flow for Wavin Calefa.

    A single combined form rather than a menu with separate steps: some
    automation/scripting clients only reliably drive a plain single-step
    options flow, and a menu here bought polish at the cost of that
    reliability. One longer form is a fine trade for that.
    """

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Manage connection settings and the optional demand/auto-standby setup.

        The demand sources below (thermostats, sensor-only rooms, valve
        entities) are only ever read, never written to - they're purely how
        the integration knows whether something currently needs heat.

        Automatic standby uses those same thermostats/sensor-rooms/valve
        entities as its demand signal and puts the whole unit into standby
        once every one of them is warm enough for long enough, releasing it
        again the moment real demand returns. It needs at least one
        thermostat or sensor-room configured above to have a signal to work
        from at all.
        """
        errors: dict[str, str] = {}

        if user_input is not None:
            if _auto_standby_missing_sources(user_input):
                errors["base"] = "auto_standby_needs_demand_sources"

            if not errors:
                data = {**self._config_entry.data}
                options = {**self._config_entry.options}
                for key, value in user_input.items():
                    if key in _OPTION_KEYS:
                        options[key] = value
                    else:
                        data[key] = value
                # entry.data (connection settings) has to be applied by hand,
                # but entry.options must NOT also be set here: the options
                # flow manager applies whatever async_create_entry(data=...)
                # returns as the new options right after this step returns.
                # Setting both would have that automatic apply immediately
                # clobber this call with a stale value. The actual reload
                # happens via the update-listener registered in __init__.py,
                # triggered once the manager has applied these options - not
                # here, which would run too early and reload with the old
                # options still in effect.
                self.hass.config_entries.async_update_entry(
                    self._config_entry,
                    title=data[CONF_NAME],
                    data=data,
                )
                return self.async_create_entry(title="", data=options)

        defaults = {**self._config_entry.data, **self._config_entry.options}
        if user_input is not None:
            defaults = {**defaults, **user_input}
        schema_dict = {
            **_schema(defaults, include_port=True).schema,
            **_demand_schema(defaults).schema,
            **_auto_standby_schema(defaults).schema,
        }
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(schema_dict),
            errors=errors,
        )
