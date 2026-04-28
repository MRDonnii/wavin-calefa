"""Config flow for Wavin Calefa."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.core import callback

from .const import (
    CONF_HOST,
    CONF_PORT,
    CONF_SCAN_INTERVAL,
    CONF_UNIT_ID,
    DEFAULT_NAME,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_UNIT_ID,
    DOMAIN,
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

    VERSION = 1

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
                return self.async_create_entry(
                    title=user_input[CONF_NAME],
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=_schema(user_input, include_port=False),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> "WavinCalefaOptionsFlow":
        """Create the options flow."""
        return WavinCalefaOptionsFlow(config_entry)


class WavinCalefaOptionsFlow(config_entries.OptionsFlow):
    """Options flow for Wavin Calefa."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Manage options."""
        if user_input is not None:
            data = {**self._config_entry.data, **user_input}
            self.hass.config_entries.async_update_entry(
                self._config_entry,
                title=data[CONF_NAME],
                data=data,
            )
            await self.hass.config_entries.async_reload(self._config_entry.entry_id)
            return self.async_create_entry(title="", data={})

        return self.async_show_form(
            step_id="init",
            data_schema=_schema(self._config_entry.data, include_port=True),
        )
