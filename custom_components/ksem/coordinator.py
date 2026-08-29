from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from pymodbus.exceptions import ModbusException

from .const import (
    CONF_POWER_SCALE,
    REG_BATTERY_POWER,
    REG_GRID_EXPORT_ENERGY,
    REG_GRID_IMPORT_ENERGY,
    REG_GRID_POWER,
    REG_HOME_POWER,
    REG_PV_POWER,
)

_LOGGER = logging.getLogger(__name__)

_ACC_KEYS: tuple[str, ...] = ("pv", "home", "bat_in", "bat_out")


class KSEMReading:
    """Instantaneous and cumulative (direct) values read from the KSEM."""

    def __init__(
        self,
        grid_power: float,
        pv_power: float,
        home_power: float,
        battery_power: float,
        grid_import_energy: float,
        grid_export_energy: float,
    ) -> None:
        self.grid_power: float = grid_power
        self.pv_power: float = pv_power
        self.home_power: float = home_power
        self.battery_power: float = battery_power
        self.grid_import_energy: float = grid_import_energy
        self.grid_export_energy: float = grid_export_energy


class KSEMCoordinator(DataUpdateCoordinator[KSEMReading]):
    """Polls the Kostal KSEM over Modbus TCP and integrates power into energy."""

    def __init__(
        self,
        hass: Any,
        client: Any,
        slave: int,
        power_scale: float,
        update_interval: timedelta,
    ) -> None:
        super().__init__(hass, _LOGGER, name="Kostal KSEM", update_interval=update_interval)
        self._client: Any = client
        self._slave: int = slave
        self._power_scale: float = power_scale
        self._base: dict[str, float] = {key: 0.0 for key in _ACC_KEYS}
        self._session: dict[str, float] = {key: 0.0 for key in _ACC_KEYS}
        self._last: datetime | None = None

    async def close(self) -> None:
        try:
            self._client.close()
        except Exception:  # noqa: BLE001 - best effort on shutdown
            pass

    def set_base(self, key: str, value: float) -> None:
        if key in self._base:
            self._base[key] = value

    def energy_value(self, key: str) -> float:
        return self._base.get(key, 0.0) + self._session.get(key, 0.0)

    async def _read(self, address: int, count: int) -> list[int]:
        if not self._client.connected:
            await self._client.connect()
        response = await self._client.read_holding_registers(
            address, count, slave=self._slave
        )
        if response is None or response.isError() or not hasattr(response, "registers"):
            raise UpdateFailed(f"Error Modbus al leer el registro {address}")
        return [int(r) for r in response.registers]

    @staticmethod
    def _decode_int32(registers: list[int]) -> int:
        value = (registers[0] << 16) | registers[1]
        if value >= 0x80000000:
            value -= 0x100000000
        return int(value)

    @staticmethod
    def _decode_uint64(registers: list[int]) -> int:
        value = 0
        for register in registers:
            value = (value << 16) | register
        return int(value)

    async def _async_update_data(self) -> KSEMReading:
        try:
            grid_regs = await self._read(REG_GRID_POWER, 2)
            pv_regs = await self._read(REG_PV_POWER, 2)
            home_regs = await self._read(REG_HOME_POWER, 2)
            battery_regs = await self._read(REG_BATTERY_POWER, 2)
            import_regs = await self._read(REG_GRID_IMPORT_ENERGY, 4)
            export_regs = await self._read(REG_GRID_EXPORT_ENERGY, 4)
        except ModbusException as err:
            raise UpdateFailed(f"Modbus: {err}") from err
        except UpdateFailed:
            raise
        except Exception as err:  # noqa: BLE001 - surface any failure as UpdateFailed
            raise UpdateFailed(f"Lectura KSEM: {err}") from err

        grid_power = self._decode_int32(grid_regs) * self._power_scale
        pv_power = self._decode_int32(pv_regs) * self._power_scale
        home_power = self._decode_int32(home_regs) * self._power_scale
        battery_power = self._decode_int32(battery_regs) * self._power_scale
        grid_import = self._decode_uint64(import_regs) * 0.1 / 1000.0
        grid_export = self._decode_uint64(export_regs) * 0.1 / 1000.0

        now = datetime.now()
        if self._last is not None:
            hours = (now - self._last).total_seconds() / 3600.0
            if hours > 0:
                self._session["pv"] += max(0.0, pv_power) * hours / 1000.0
                self._session["home"] += max(0.0, home_power) * hours / 1000.0
                if battery_power >= 0:
                    self._session["bat_in"] += battery_power * hours / 1000.0
                else:
                    self._session["bat_out"] += (-battery_power) * hours / 1000.0
        self._last = now

        return KSEMReading(
            grid_power=grid_power,
            pv_power=pv_power,
            home_power=home_power,
            battery_power=battery_power,
            grid_import_energy=grid_import,
            grid_export_energy=grid_export,
        )
