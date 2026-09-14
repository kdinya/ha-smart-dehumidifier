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
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN, STATUS_AUTO, STATUS_MANUAL, STATUS_MANUAL_AUTO, STATUS_OFF
from .device import DehumidifierDevice


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    device: DehumidifierDevice = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([DehumidifierHumidifierEntity(device, entry)])


class DehumidifierHumidifierEntity(HumidifierEntity, RestoreEntity):
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

        # Відновлення стану після рестарту ХА: увімкнено/вимкнено, ціль
        # вологості й авто-режим - все, ЩО НЕ пов'язане з ручним режимом.
        # Ручний режим (і пов'язана з ним пауза) навмисно НЕ відновлюється -
        # _manual_active/_pause_active й так завжди стартують як False
        # (див. DehumidifierDevice.__init__), тож після рестарту статус сам
        # природно розрахується як "очікування" або "авто"/"он" - залежно
        # від поточної вологості, без жодного спеціального коду для цього.
        last_state = await self.async_get_last_state()
        if last_state is not None and last_state.state in ("on", "off"):
            self._device.is_on = last_state.state == "on"

            humidity = last_state.attributes.get("humidity")
            if humidity is not None:
                try:
                    self._device.target_humidity = int(float(humidity))
                except (TypeError, ValueError):
                    pass

            auto_mode = last_state.attributes.get("auto_mode")
            if isinstance(auto_mode, bool):
                self._device.auto_mode = auto_mode

            self._device.recompute()

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
        # Ліміти min/max (Options пристрою) застосовуються лише всередині
        # авто-розрахунку рекомендованої вологості (device.recommended_humidity),
        # а не як обмеження на ручний вибір значення. Ручний вибір завжди
        # доступний у повному діапазоні 0-100%, незалежно від auto_mode.
        return 0

    @property
    def max_humidity(self) -> int:
        return 100

    @property
    def current_humidity(self):
        return self._device.current_humidity()

    @property
    def action(self) -> HumidifierAction:
        status = self._device.status
        if status == STATUS_OFF:
            return HumidifierAction.OFF
        if status in (STATUS_AUTO, STATUS_MANUAL, STATUS_MANUAL_AUTO):
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
