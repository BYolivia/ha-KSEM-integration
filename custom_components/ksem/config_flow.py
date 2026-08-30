from __future__ import annotations

import asyncio
import contextlib
import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigEntry, OptionsFlow
from homeassistant.data_entry_flow import FlowResult

from .const import (
    CONF_HOST,
    CONF_PORT,
    CONF_SCAN_INTERVAL,
    CONF_SLAVE,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_SLAVE,
    DOMAIN,
)
from .coordinator import create_tcp_client, read_registers

_LOGGER = logging.getLogger(__name__)

_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): int,
        vol.Optional(CONF_SLAVE, default=DEFAULT_SLAVE): int,
        vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): int,
    }
)


class KSEMConfigFlow(ConfigFlow, domain=DOMAIN):  # type: ignore[call-arg]
    VERSION = 1

    _connection_error: str = ""

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            self._connection_error = ""
            await self.async_set_unique_id(user_input[CONF_HOST])
            self._abort_if_unique_id_configured()
            if not await self._test_connection(user_input):
                errors["base"] = self._connection_error or "cannot_connect"
            else:
                return self.async_create_entry(
                    title=user_input[CONF_HOST], data=user_input
                )
        return self.async_show_form(
            step_id="user", data_schema=_SCHEMA, errors=errors
        )

    @staticmethod
    def _close_client(client: Any) -> None:
        try:
            result = client.close()
            if hasattr(result, "__await__"):
                asyncio.ensure_future(result)
        except Exception:  # noqa: BLE001 - best effort cleanup
            pass

    async def _tcp_reachable(self, host: str, port: int) -> bool:
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port), timeout=5
            )
            writer.close()
            with contextlib.suppress(Exception):
                await writer.wait_closed()
            return True
        except Exception as err:  # noqa: BLE001 - network probe
            self._connection_error = (
                f"No se alcanza {host}:{port} por TCP. "
                f"Comprueba la IP y que HA tenga acceso de red al KSEM: {err}"
            )
            _LOGGER.warning("KSEM: %s", self._connection_error)
            return False

    async def _test_connection(self, user_input: dict[str, Any]) -> bool:
        host = str(user_input[CONF_HOST])
        port = int(user_input[CONF_PORT])
        slave = int(user_input[CONF_SLAVE])

        if not await self._tcp_reachable(host, port):
            return False

        try:
            client = create_tcp_client(host, port, 5)
            if not await client.connect():
                self._connection_error = (
                    f"Conectado a {host}:{port} pero Modbus no abre la conexion. "
                    f"Verifica que el esclavo TCP este activado en el KSEM "
                    f"(sin cifrado TLS, puerto 502)."
                )
                _LOGGER.warning("KSEM: %s", self._connection_error)
                return False
            response = await read_registers(client, 0, 2, slave)
            self._close_client(client)
            if response is None or response.isError():
                self._connection_error = (
                    f"El KSEM respondio con error de Modbus (slave {slave}). "
                    f"Prueba otro Slave ID en la integracion."
                )
                _LOGGER.warning("KSEM: %s", self._connection_error)
                return False
            return True
        except Exception as err:  # noqa: BLE001 - connection probe
            self._connection_error = f"Error de Modbus: {err}"
            _LOGGER.warning("KSEM: %s", self._connection_error)
            return False

    @staticmethod
    async def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return KSEMOptionsFlow()


class KSEMOptionsFlow(OptionsFlow):
    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)
        return self.async_show_form(step_id="init", data_schema=_SCHEMA)
