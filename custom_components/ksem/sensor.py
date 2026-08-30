from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import KSEMCoordinator


@dataclass(frozen=True)
class SensorDesc:
    key: str
    name: str
    unit: str
    device_class: str
    state_class: str
    kind: str  # "power" | "direct" | "accum"
    attr: str = ""
    acc_key: str = ""


_SENSORS: tuple[SensorDesc, ...] = (
    SensorDesc("grid_import_power", "Consumo de red", "W", SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT, "power", attr="grid_import_power"),
    SensorDesc("grid_export_power", "Inyeccion a la red", "W", SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT, "power", attr="grid_export_power"),
    SensorDesc("pv_power", "Produccion solar", "W", SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT, "power", attr="pv_power"),
    SensorDesc("home_consumption", "Consumo del hogar", "W", SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT, "power", attr="home_power"),
    SensorDesc("battery_power", "Potencia de la bateria", "W", SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT, "power", attr="battery_power"),
    SensorDesc("grid_import_energy", "Energia consumida de la red", "kWh", SensorDeviceClass.ENERGY, SensorStateClass.TOTAL_INCREASING, "direct", attr="grid_import_energy"),
    SensorDesc("grid_export_energy", "Energia inyectada a la red", "kWh", SensorDeviceClass.ENERGY, SensorStateClass.TOTAL_INCREASING, "direct", attr="grid_export_energy"),
    SensorDesc("pv_energy", "Energia solar producida", "kWh", SensorDeviceClass.ENERGY, SensorStateClass.TOTAL_INCREASING, "accum", acc_key="pv"),
    SensorDesc("home_energy", "Energia consumida del hogar", "kWh", SensorDeviceClass.ENERGY, SensorStateClass.TOTAL_INCREASING, "accum", acc_key="home"),
    SensorDesc("battery_in_energy", "Energia de la bateria (carga)", "kWh", SensorDeviceClass.ENERGY, SensorStateClass.TOTAL_INCREASING, "accum", acc_key="bat_in"),
    SensorDesc("battery_out_energy", "Energia de la bateria (descarga)", "kWh", SensorDeviceClass.ENERGY, SensorStateClass.TOTAL_INCREASING, "accum", acc_key="bat_out"),
)


def _device_info() -> DeviceInfo:
    return DeviceInfo(
        identifiers={(DOMAIN, "ksem")},
        name="Kostal KSEM",
        manufacturer="Kostal",
        model="Smart Energy Meter",
    )


class KSEMSensor(CoordinatorEntity[KSEMCoordinator], SensorEntity):
    """Sensor whose value comes directly from the latest KSEM reading."""

    def __init__(self, coordinator: KSEMCoordinator, desc: SensorDesc) -> None:
        super().__init__(coordinator)
        self._desc = desc
        self._attr_unique_id = f"{DOMAIN}_{desc.key}"
        self._attr_name = desc.name
        self._attr_native_unit_of_measurement = desc.unit
        self._attr_device_class = desc.device_class
        self._attr_state_class = desc.state_class
        self._attr_should_poll = False

    @property
    def device_info(self) -> DeviceInfo:
        return _device_info()

    @property
    def native_value(self) -> float | None:
        reading = self.coordinator.data
        if reading is None:
            return None
        value = getattr(reading, self._desc.attr)
        return round(float(value), 3)


class KSEMEnergySensor(CoordinatorEntity[KSEMCoordinator], SensorEntity, RestoreEntity):
    """Energy sensor integrated from power; restores last value across restarts."""

    def __init__(self, coordinator: KSEMCoordinator, desc: SensorDesc) -> None:
        super().__init__(coordinator)
        self._desc = desc
        self._attr_unique_id = f"{DOMAIN}_{desc.key}"
        self._attr_name = desc.name
        self._attr_native_unit_of_measurement = desc.unit
        self._attr_device_class = desc.device_class
        self._attr_state_class = desc.state_class
        self._attr_should_poll = False

    @property
    def device_info(self) -> DeviceInfo:
        return _device_info()

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        state = await self.async_get_last_state()
        if state is not None and state.state is not None:
            try:
                self.coordinator.set_base(self._desc.acc_key, float(state.state))
            except ValueError:
                pass

    @property
    def native_value(self) -> float | None:
        return round(self.coordinator.energy_value(self._desc.acc_key), 3)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: Any,
) -> None:
    coordinator: KSEMCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[SensorEntity] = []
    for desc in _SENSORS:
        if desc.kind == "accum":
            entities.append(KSEMEnergySensor(coordinator, desc))
        else:
            entities.append(KSEMSensor(coordinator, desc))
    async_add_entities(entities)
