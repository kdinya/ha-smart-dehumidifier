"""Sensor platform: status text sensor + recommended humidity sensor."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .device import DehumidifierDevice


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    device: DehumidifierDevice = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            DehumidifierStatusSensor(device, entry),
            DehumidifierRecommendedHumiditySensor(device, entry),
        ]
    )


class _BaseSensor(SensorEntity):
    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, device: DehumidifierDevice, entry: ConfigEntry) -> None:
        self._device = device
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, entry.entry_id)})

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            async_dispatcher_connect(self.hass, self._device.signal, self._handle_update)
        )

    @callback
    def _handle_update(self) -> None:
        self.async_write_ha_state()


class DehumidifierStatusSensor(_BaseSensor):
    """Raw state: off / idle / manual / drying / drying_manual / pause."""

    _attr_translation_key = "status"
    _attr_icon = "mdi:air-filter"

    def __init__(self, device: DehumidifierDevice, entry: ConfigEntry) -> None:
        super().__init__(device, entry)
        self._attr_unique_id = f"{entry.entry_id}_status"
        self._attr_suggested_object_id = f"{device.slug}_status"

    @property
    def native_value(self) -> str:
        return self._device.status


class DehumidifierRecommendedHumiditySensor(_BaseSensor):
    _attr_translation_key = "recommended_humidity"
    _attr_native_unit_of_measurement = "%"
    _attr_icon = "mdi:water-percent"

    def __init__(self, device: DehumidifierDevice, entry: ConfigEntry) -> None:
        super().__init__(device, entry)
        self._attr_unique_id = f"{entry.entry_id}_recommended_humidity"
        self._attr_suggested_object_id = f"{device.slug}_recommended_humidity"

    @property
    def native_value(self) -> int | None:
        return self._device.recommended_humidity()
