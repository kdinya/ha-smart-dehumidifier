"""HA Smart Dehumidifier integration."""
from __future__ import annotations

import logging
import os

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CARD_JS_URL, CARD_URL_BASE, DOMAIN, PLATFORMS
from .device import DehumidifierDevice

_LOGGER = logging.getLogger(__name__)


def _cache_busted_card_js_url(www_path: str) -> str:
    """Append ?v=<mtime> so browsers fetch a fresh card.js after every update.

    ES module imports are cached by the browser per exact URL — without a
    changing query string, an update to index.js on disk can keep being
    served from a stale (possibly broken, mid-edit) cached copy, which looks
    to the user exactly like "Custom element not found".
    """
    try:
        mtime = os.path.getmtime(os.path.join(www_path, "index.js"))
        return f"{CARD_JS_URL}?v={int(mtime)}"
    except OSError:
        return CARD_JS_URL


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Register the bundled Lovelace card so it loads without a manual resource."""
    www_path = hass.config.path("custom_components", DOMAIN, "www")
    card_js_url = _cache_busted_card_js_url(www_path)

    registered = False
    try:
        from homeassistant.components.http import StaticPathConfig

        await hass.http.async_register_static_paths(
            [StaticPathConfig(CARD_URL_BASE, www_path, cache_headers=False)]
        )
        registered = True
    except ImportError:
        # Older HA cores without async_register_static_paths / StaticPathConfig.
        try:
            hass.http.register_static_path(CARD_URL_BASE, www_path, cache_headers=False)
            registered = True
        except Exception:  # noqa: BLE001
            _LOGGER.exception(
                "HA Smart Dehumidifier: failed to register static path %s -> %s",
                CARD_URL_BASE,
                www_path,
            )
    except Exception:  # noqa: BLE001
        _LOGGER.exception(
            "HA Smart Dehumidifier: failed to register static path %s -> %s",
            CARD_URL_BASE,
            www_path,
        )

    if registered:
        add_extra_js_url(hass, card_js_url)
        _LOGGER.debug("HA Smart Dehumidifier: card registered at %s", card_js_url)
    else:
        _LOGGER.error(
            "HA Smart Dehumidifier: card resource was NOT registered - "
            "add it manually in Settings -> Dashboards -> Resources as %s (JavaScript Module)",
            card_js_url,
        )

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
