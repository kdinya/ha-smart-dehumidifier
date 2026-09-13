"""Number platform.

Recreates the five input_number helpers (dh_delta, dh_auto_min, dh_auto_max,
dh_manual_runtime, dh_manual_pause_runtime) that used to back the card's
in-card gear-icon settings panel. Values persist across restarts via
RestoreEntity and initialise from the config-entry Options.
"""
from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN
from .device import DehumidifierDevice


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    device: DehumidifierDevice = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            DeltaNumber(device, entry),
            MinHumidityNumber(device, entry),
            MaxHumidityNumber(device, entry),
            ManualRuntimeNumber(device, entry),
            ManualPauseNumber(device, entry),
        ]
    )


class _BaseNumber(NumberEntity, RestoreEntity):
    _attr_has_entity_name = True
    _attr_mode = NumberMode.SLIDER
    _attr_should_poll = False
    _device_attribute: str = ""

    def __init__(self, device: DehumidifierDevice, entry: ConfigEntry, suffix: str) -> None:
        self._device = device
        self._attr_unique_id = f"{entry.entry_id}_{suffix}"
        self._attr_suggested_object_id = f"{device.slug}_{suffix}"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, entry.entry_id)})

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state is not None and last_state.state not in (None, "unknown", "unavailable"):
            try:
                setattr(self._device, self._device_attribute, float(last_state.state))
            except (TypeError, ValueError):
                pass
        self.async_on_remove(
            async_dispatcher_connect(self.hass, self._device.signal, self._handle_update)
        )

    @callback
    def _handle_update(self) -> None:
        self.async_write_ha_state()

    @property
    def native_value(self) -> float:
        return getattr(self._device, self._device_attribute)

    async def async_set_native_value(self, value: float) -> None:
        setattr(self._device, self._device_attribute, value)
        self._device.recompute()


class DeltaNumber(_BaseNumber):
    _attr_translation_key = "delta"
    _attr_icon = "mdi:water-plus-outline"
    _attr_native_min_value = 0
    _attr_native_max_value = 10
    _attr_native_step = 0.1
    _attr_native_unit_of_measurement = "%"
    _device_attribute = "delta"

    def __init__(self, device: DehumidifierDevice, entry: ConfigEntry) -> None:
        super().__init__(device, entry, "delta")


class MinHumidityNumber(_BaseNumber):
    _attr_translation_key = "min_humidity"
    _attr_icon = "mdi:water-minus"
    _attr_native_min_value = 0
    _attr_native_max_value = 100
    _attr_native_step = 1
    _attr_native_unit_of_measurement = "%"
    _device_attribute = "min_humidity"

    def __init__(self, device: DehumidifierDevice, entry: ConfigEntry) -> None:
        super().__init__(device, entry, "min_humidity")


class MaxHumidityNumber(_BaseNumber):
    _attr_translation_key = "max_humidity"
    _attr_icon = "mdi:water-plus"
    _attr_native_min_value = 0
    _attr_native_max_value = 100
    _attr_native_step = 1
    _attr_native_unit_of_measurement = "%"
    _device_attribute = "max_humidity"

    def __init__(self, device: DehumidifierDevice, entry: ConfigEntry) -> None:
        super().__init__(device, entry, "max_humidity")


class ManualRuntimeNumber(_BaseNumber):
    _attr_translation_key = "manual_runtime"
    _attr_icon = "mdi:timer-outline"
    _attr_native_min_value = 1
    _attr_native_max_value = 180
    _attr_native_step = 1
    _attr_native_unit_of_measurement = "min"
    _device_attribute = "manual_runtime"

    def __init__(self, device: DehumidifierDevice, entry: ConfigEntry) -> None:
        super().__init__(device, entry, "manual_runtime")


class ManualPauseNumber(_BaseNumber):
    _attr_translation_key = "manual_pause"
    _attr_icon = "mdi:timer-pause-outline"
    _attr_native_min_value = 1
    _attr_native_max_value = 180
    _attr_native_step = 1
    _attr_native_unit_of_measurement = "min"
    _device_attribute = "manual_pause"

    def __init__(self, device: DehumidifierDevice, entry: ConfigEntry) -> None:
        super().__init__(device, entry, "manual_pause")
