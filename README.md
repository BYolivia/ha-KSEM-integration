# Kostal KSEM para Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-custom%20integration-blue.svg)](https://github.com/hacs/integration)
![Python](https://img.shields.io/badge/typing-mypy%20strict-brightgreen)

Integración para Home Assistant que lee el **Kostal Smart Energy Meter (KSEM)** por
**Modbus TCP** y expone los datos de electricidad necesarios para el panel de **Energía**
de HA: red, placas solares, consumo de la casa y batería.

![Logo](logo.svg)

## Características

- Instalable directamente desde **HACS** (repositorio personalizado).
- Configuración 100% por interfaz (sin tocar YAML).
- 10 sensores con `device_class` y `state_class` correctos para el panel de Energía.
- Tipado fuerte (type hints + `mypy` en modo estricto, `py.typed`).

## Sensores expuestos

| Sensor | Registro KSEM | Unidad | Clase |
|---|---|---|---|
| `ksem_grid_power` — Potencia de red | 40972 | W | `power` |
| `ksem_pv_power` — Potencia placas | 40974 | W | `power` |
| `ksem_home_consumption` — Consumo de la casa | 40982 | W | `power` |
| `ksem_battery_power` — Potencia batería | 40984 | W | `power` |
| `ksem_grid_import_energy` — Energía red importada | 512 | kWh | `energy` (total_increasing) |
| `ksem_grid_export_energy` — Energía vertida a red | 516 | kWh | `energy` (total_increasing) |
| `ksem_pv_energy` — Energía placas | integrada | kWh | `energy` (total_increasing) |
| `ksem_home_energy` — Energía consumo casa | integrada | kWh | `energy` (total_increasing) |
| `ksem_battery_in_energy` — Energía batería (entrada) | integrada | kWh | `energy` (total_increasing) |
| `ksem_battery_out_energy` — Energía batería (salida) | integrada | kWh | `energy` (total_increasing) |

> La energía de placas, casa y batería se **integra** a partir de la potencia instantánea
> (el KSEM solo expone contadores físicos para la red). El valor se restaura tras reinicio
> para mantener la monotonicidad.

## Requisitos previos

1. En el KSEM: activa **Modbus TCP Slave** (puerto `502` por defecto) desde su web de configuración.
2. Home Assistant con acceso de red al KSEM.
3. Un broker no es necesario: la integración crea las entidades directamente.

## Instalación con HACS

1. En HACS → ![⋮](https://github.com/user-attachments/assets/placeholder) → **Repositorios personalizados**.
2. Añade: `https://github.com/BYolivia/ha-KSEM-integration` (categoría: Integración).
3. Busca **Kostal KSEM** y pulsa **Descargar**.
4. Reinicia Home Assistant.
5. **Ajustes → Dispositivos y servicios → Añadir integración → Kostal KSEM**.
6. Introduce la IP del KSEM, puerto, Slave ID e intervalo.

## Mapeo en el panel de Energía

En **Ajustes → Energía**:

- *Producción solar* → `ksem_pv_energy`
- *Consumo de la red* → `ksem_grid_import_energy`
- *Energía a la red* → `ksem_grid_export_energy`
- *Batería entrante* → `ksem_battery_in_energy`
- *Batería saliente* → `ksem_battery_out_energy`
- *Consumo del hogar* → `ksem_home_energy`

## Ajustes (config_flow)

| Parámetro | Def. | Descripción |
|---|---|---|
| `host` | — | IP del KSEM |
| `port` | `502` | Puerto Modbus TCP |
| `slave` | `1` | Slave ID |
| `scan_interval` | `5` | Segundos entre consultas |
| `power_scale` | `1.0` | Factor de escala de los registros de potencia |

### `power_scale`

Según el manual oficial del KSEM, los registros del bloque *Energiefluss/Dashboard*
son `int32` en **W**. Si observas valores ~1000× demasiado grandes o pequeños,
cambia `power_scale` a `0.001` (algunas fuentes los reportan en kW).

## Desarrollo

```bash
python -m mypy custom_components/ksem
```

El proyecto usa `from __future__ import annotations` y está verificado con `mypy`
en configuración estricta (`disallow_untyped_defs`, `disallow_any_generics`, …).

## Estructura

```
custom_components/ksem/
├── __init__.py        # setup/unload de la integración
├── config_flow.py     # configuración por UI + prueba de conexión
├── const.py           # constantes y registros Modbus
├── coordinator.py     # DataUpdateCoordinator (lectura + integración)
├── sensor.py          # definición de entidades/sensores
├── manifest.json      # metadatos de la integración
├── strings.json       # textos del config flow
└── translations/es.json
```
