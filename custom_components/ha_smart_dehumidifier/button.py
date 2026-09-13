"""Button platform: MANUAL button (replaces script.vanna_manual_toggle)."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .device import DehumidifierDevice


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    device: DehumidifierDevice = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([DehumidifierManualToggleButton(device, entry)])


class DehumidifierManualToggleButton(ButtonEntity):
    _attr_has_entity_name = True
    _attr_translation_key = "manual_toggle"
    _attr_icon = "mdi:gesture-tap"

    def __init__(self, device: DehumidifierDevice, entry: ConfigEntry) -> None:
        self._device = device
        self._attr_unique_id = f"{entry.entry_id}_manual_toggle"
        self._attr_suggested_object_id = f"{device.slug}_manual_toggle"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, entry.entry_id)})

    async def async_press(self) -> None:
        self._device.async_manual_toggle()
