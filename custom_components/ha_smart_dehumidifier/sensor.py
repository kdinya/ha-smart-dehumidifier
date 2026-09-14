"""Sensor platform: status text sensor + recommended/absolute humidity sensors."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity, SensorStateClass
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
            DehumidifierAbsoluteHumidityRoomSensor(device, entry),
            DehumidifierAbsoluteHumidityNeighborSensor(device, entry),
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
    """Raw state: off / on / auto / idle / manual / pause."""

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


class _AbsoluteHumiditySensor(_BaseSensor):
    """Абсолютна вологість, г/м3 - для порівняння кімнат незалежно від температури.

    Показується як діагностика: користувачу в картці/панелях завжди
    відображається відносна вологість (%), ця сутність - лише для звірки
    (наприклад, у графіках чи автоматизаціях, де потрібна абсолютна
    вологість замість відносної).
    """

    _attr_native_unit_of_measurement = "g/m³"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:water"
    _attr_entity_category = None
    _attr_suggested_display_precision = 1


class DehumidifierAbsoluteHumidityRoomSensor(_AbsoluteHumiditySensor):
    _attr_translation_key = "absolute_humidity_room"

    def __init__(self, device: DehumidifierDevice, entry: ConfigEntry) -> None:
        super().__init__(device, entry)
        self._attr_unique_id = f"{entry.entry_id}_absolute_humidity_room"
        self._attr_suggested_object_id = f"{device.slug}_absolute_humidity_room"

    @property
    def native_value(self) -> float | None:
        return self._device.absolute_humidity_room()


class DehumidifierAbsoluteHumidityNeighborSensor(_AbsoluteHumiditySensor):
    _attr_translation_key = "absolute_humidity_neighbor"

    def __init__(self, device: DehumidifierDevice, entry: ConfigEntry) -> None:
        super().__init__(device, entry)
        self._attr_unique_id = f"{entry.entry_id}_absolute_humidity_neighbor"
        self._attr_suggested_object_id = f"{device.slug}_absolute_humidity_neighbor"

    @property
    def native_value(self) -> float | None:
        return self._device.absolute_humidity_neighbor()
