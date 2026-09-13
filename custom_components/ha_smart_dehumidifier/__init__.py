"""HA Smart Dehumidifier integration."""
from __future__ import annotations

import logging

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CARD_JS_URL, CARD_URL_BASE, DOMAIN, PLATFORMS
from .device import DehumidifierDevice

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Register the bundled Lovelace card so it loads without a manual resource."""
    www_path = hass.config.path("custom_components", DOMAIN, "www")

    try:
        from homeassistant.components.http import StaticPathConfig

        await hass.http.async_register_static_paths(
            [StaticPathConfig(CARD_URL_BASE, www_path, cache_headers=False)]
        )
    except ImportError:
        # Fallback for older HA cores without async_register_static_paths.
        hass.http.register_static_path(CARD_URL_BASE, www_path, cache_headers=False)

    add_extra_js_url(hass, CARD_JS_URL)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})

    device = DehumidifierDevice(hass, entry)
    await device.async_setup()
    hass.data[DOMAIN][entry.entry_id] = device

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    device: DehumidifierDevice = hass.data[DOMAIN][entry.entry_id]
    device.reload_options()
    device.recompute()


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        device: DehumidifierDevice = hass.data[DOMAIN].pop(entry.entry_id)
        device.async_unload()
    return unload_ok
