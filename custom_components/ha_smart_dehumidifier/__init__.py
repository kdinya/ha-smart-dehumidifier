"""HA Smart Dehumidifier integration."""
from __future__ import annotations

import logging
import os
import time

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CARD_JS_URL, CARD_URL_BASE, DOMAIN, PLATFORMS
from .device import DehumidifierDevice

_LOGGER = logging.getLogger(__name__)

# Обчислюється рівно один раз при імпорті модуля - тобто рівно один раз на
# кожен повний рестарт Home Assistant (весь Python-процес і всі модулі
# переімпортовуються заново при рестарті).
_BOOT_TS = int(time.time())


def _cache_busted_card_js_url(www_path: str) -> str:
    """Append ?v=<mtime>-<boot_ts> so browsers always fetch a fresh card.js.

    ES module imports кешуються браузером ПО ТОЧНОМУ URL. Раніше ?v=
    рахувався ЛИШЕ з mtime файлу index.js на диску - а оскільки файл
    зазвичай не змінюється між рестартами ХА, URL картки лишався
    буквально ІДЕНТИЧНИМ при кожному рестарті.

    Це відкривало вікно для перегонів (race condition) під час старту:
    http-сервер ХА піднімається й починає відповідати на запити раніше,
    ніж встигають завантажитись усі інтеграції (в т.ч. ця - реєстрація
    статичного шляху нижче в async_setup). Якщо браузер встигав
    запросити картку САМЕ в цю паузу, він отримував помилку (шлях ще
    не зареєстрований) - і оскільки URL не змінювався від рестарту до
    рестарту, браузер міг закешувати цю невдалу відповідь під тим самим
    URL і продовжувати роздавати її з кешу навіть після успішного
    довантаження ХА, аж до ручного очищення кешу.

    Додавання _BOOT_TS (унікальний для кожного рестарту, а не лише для
    кожної зміни файлу) гарантує, що URL картки ЗАВЖДИ новий після
    рестарту ХА - навіть якщо один раз перегони й трапляться, наступний
    рестарт піде вже за URL, якого браузер ще ніколи не бачив, і
    самостійно довантажить картку без участі користувача.
    """
    try:
        mtime = int(os.path.getmtime(os.path.join(www_path, "index.js")))
        return f"{CARD_JS_URL}?v={mtime}-{_BOOT_TS}"
    except OSError:
        return f"{CARD_JS_URL}?v={_BOOT_TS}"


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
