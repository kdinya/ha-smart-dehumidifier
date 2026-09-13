"""Humidifier platform - the main entity the card points `entity:` at."""
from __future__ import annotations

from homeassistant.components.humidifier import (
    HumidifierAction,
    HumidifierDeviceClass,
    HumidifierEntity,
    HumidifierEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, STATUS_DRYING, STATUS_DRYING_MANUAL, STATUS_MANUAL, STATUS_OFF
from .device import DehumidifierDevice


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    device: DehumidifierDevice = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([DehumidifierHumidifierEntity(device, entry)])


class DehumidifierHumidifierEntity(HumidifierEntity):
    _attr_has_entity_name = True
    _attr_name = None
    _attr_device_class = HumidifierDeviceClass.DEHUMIDIFIER
    _attr_supported_features = HumidifierEntityFeature(0)
    _attr_should_poll = False

    def __init__(self, device: DehumidifierDevice, entry: ConfigEntry) -> None:
        self._device = device
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_humidifier"
        self._attr_suggested_object_id = device.slug
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="kdinya",
            model="HA Smart Dehumidifier",
        )

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            async_dispatcher_connect(self.hass, self._device.signal, self._handle_update)
        )

    @callback
    def _handle_update(self) -> None:
        self.async_write_ha_state()

    @property
    def is_on(self) -> bool:
        return self._device.is_on

    @property
    def target_humidity(self) -> int:
        return self._device.target_humidity

    @property
    def min_humidity(self) -> int:
        # Ліміти min/max діють лише в авто-режимі. Коли авто вимкнено,
        # користувач повинен мати змогу обрати будь-яке значення 0-100%.
        return self._device.min_humidity if self._device.auto_mode else 0

    @property
    def max_humidity(self) -> int:
        return self._device.max_humidity if self._device.auto_mode else 100

    @property
    def current_humidity(self):
        return self._device.current_humidity()

    @property
    def action(self) -> HumidifierAction:
        status = self._device.status
        if status == STATUS_OFF:
            return HumidifierAction.OFF
        if status in (STATUS_DRYING, STATUS_DRYING_MANUAL, STATUS_MANUAL):
            return HumidifierAction.DRYING
        return HumidifierAction.IDLE

    def _sibling_entity_id(self, domain: str, suffix: str) -> str | None:
        """Знайти реальний entity_id сутності нашого пристрою через реєстр.

        Використовує unique_id (стабільний, не залежить від того, як
        користувач перейменував entity_id), тож картка завжди отримає
        правильне посилання, навіть якщо object_id відрізняється від
        `device.slug` (перейменування, конфлікт імен тощо).
        """
        registry = er.async_get(self.hass)
        return registry.async_get_entity_id(domain, DOMAIN, f"{self._entry.entry_id}_{suffix}")

    @property
    def extra_state_attributes(self) -> dict:
        return {
            "status": self._device.status,
            "auto_mode": self._device.auto_mode,
            # Сутності, обрані користувачем під час налаштування пристрою:
            "fan_entity": self._device.fan_entity,
            "current_humidity_entity": self._device.current_humidity_entity,
            "abs_humidity_entity": self._device.abs_humidity_entity,
            # Сутності, які створив сам пристрій (їх entity_id визначається
            # через реєстр сутностей, а не вгадується за object_id):
            "status_entity": self._sibling_entity_id("sensor", "status"),
            "calc_entity": self._sibling_entity_id("sensor", "recommended_humidity"),
            "auto_entity": self._sibling_entity_id("switch", "auto_mode"),
            "manual_script_entity": self._sibling_entity_id("button", "manual_toggle"),
            "delta_entity": self._sibling_entity_id("number", "delta"),
            "min_rh_entity": self._sibling_entity_id("number", "min_humidity"),
            "max_rh_entity": self._sibling_entity_id("number", "max_humidity"),
            "manual_runtime_entity": self._sibling_entity_id("number", "manual_runtime"),
            "manual_pause_runtime_entity": self._sibling_entity_id("number", "manual_pause"),
        }

    async def async_turn_on(self, **kwargs) -> None:
        self._device.async_turn_on()

    async def async_turn_off(self, **kwargs) -> None:
        self._device.async_turn_off()

    async def async_set_humidity(self, humidity: int) -> None:
        self._device.async_set_humidity(humidity)
