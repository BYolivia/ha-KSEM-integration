from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigEntry, OptionsFlow
from homeassistant.data_entry_flow import FlowResult

from .const import (
    CONF_HOST,
    CONF_PORT,
    CONF_POWER_SCALE,
    CONF_SCAN_INTERVAL,
    CONF_SLAVE,
    DEFAULT_PORT,
    DEFAULT_POWER_SCALE,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_SLAVE,
    DOMAIN,
)

_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): int,
        vol.Optional(CONF_SLAVE, default=DEFAULT_SLAVE): int,
        vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): int,
        vol.Optional(CONF_POWER_SCALE, default=DEFAULT_POWER_SCALE): float,
    }
)


class KSEMConfigFlow(ConfigFlow, domain=DOMAIN):  # type: ignore[call-arg]
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            if not await self._test_connection(user_input):
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(
                    title=user_input[CONF_HOST], data=user_input
                )
        return self.async_show_form(
            step_id="user", data_schema=_SCHEMA, errors=errors
        )

    async def _test_connection(self, user_input: dict[str, Any]) -> bool:
        from pymodbus.client import AsyncModbusTcpClient

        try:
            client = AsyncModbusTcpClient(
                host=user_input[CONF_HOST],
                port=int(user_input[CONF_PORT]),
                timeout=5,
            )
            await client.connect()
            response = await client.read_holding_registers(
                40972, 2, slave=int(user_input[CONF_SLAVE])
            )
            client.close()
            return response is not None and not response.isError()
        except Exception:  # noqa: BLE001 - connection probe
            return False

    @staticmethod
    async def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return KSEMOptionsFlow()


class KSEMOptionsFlow(OptionsFlow):
    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)
        return self.async_show_form(step_id="init", data_schema=_SCHEMA)
