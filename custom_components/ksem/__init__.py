from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

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
from .coordinator import KSEMCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[str] = ["sensor"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    options = dict(entry.data)
    options.update(entry.options)

    host = str(options[CONF_HOST])
    port = int(options[CONF_PORT])
    slave = int(options[CONF_SLAVE])
    scan_interval = int(options[CONF_SCAN_INTERVAL])

    from .coordinator import create_tcp_client

    client = create_tcp_client(host, port, 10)
    coordinator = KSEMCoordinator(
        hass,
        client,
        slave,
        timedelta(seconds=scan_interval),
    )

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await coordinator.async_config_entry_first_refresh()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        coordinator: KSEMCoordinator = hass.data[DOMAIN].pop(entry.entry_id)
        await coordinator.close()
    return unloaded
