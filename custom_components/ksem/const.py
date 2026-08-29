from __future__ import annotations

from datetime import timedelta

DOMAIN: str = "ksem"

CONF_HOST: str = "host"
CONF_PORT: str = "port"
CONF_SLAVE: str = "slave"
CONF_SCAN_INTERVAL: str = "scan_interval"
CONF_POWER_SCALE: str = "power_scale"

DEFAULT_PORT: int = 502
DEFAULT_SLAVE: int = 1
DEFAULT_SCAN_INTERVAL: int = 5
DEFAULT_POWER_SCALE: float = 1.0

REG_GRID_POWER: int = 40972
REG_PV_POWER: int = 40974
REG_HOME_POWER: int = 40982
REG_BATTERY_POWER: int = 40984
REG_GRID_IMPORT_ENERGY: int = 512
REG_GRID_EXPORT_ENERGY: int = 516
