"""Runtime state machine for one HA Smart Dehumidifier instance.

This class reproduces, inside the integration, everything that used to be
spread across helpers (input_boolean, timer, input_number) and four
automations plus one script in the original Lovelace-card-only setup:

- Vanna - Full Stop Handler
- Vanna - Physical Fan ON Starts/Resumes Manual
- Vanna - Physical Fan OFF Pauses Manual
- Vanna - Auto Target Humidity Sync
- Vanna - Master Fan Controller
- script.vanna_manual_toggle
"""
from __future__ import annotations

import logging
import time

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_call_later, async_track_state_change_event
from homeassistant.util import slugify

from .const import (
    CONF_ABS_HUMIDITY_ENTITY,
    CONF_CURRENT_HUMIDITY_ENTITY,
    CONF_DELTA,
    CONF_DRY_TOLERANCE,
    CONF_FAN_ENTITY,
    CONF_MANUAL_PAUSE,
    CONF_MANUAL_RUNTIME,
    CONF_MAX_HUMIDITY,
    CONF_MIN_HUMIDITY,
    DEFAULT_DELTA,
    DEFAULT_DRY_TOLERANCE,
    DEFAULT_MANUAL_PAUSE,
    DEFAULT_MANUAL_RUNTIME,
    DEFAULT_MAX_HUMIDITY,
    DEFAULT_MIN_HUMIDITY,
    DEFAULT_TARGET_HUMIDITY,
    DOMAIN,
    ENTITY_ID_PREFIX,
    STATUS_DRYING,
    STATUS_DRYING_MANUAL,
    STATUS_IDLE,
    STATUS_MANUAL,
    STATUS_OFF,
    STATUS_PAUSE,
)

_LOGGER = logging.getLogger(__name__)

SIGNAL_UPDATE = f"{DOMAIN}_update_{{}}"

# Мінімальний інтервал між авто-перемиканнями auto_request (гістерезису
# самого по собі не завжди досить: якщо показник вологості чи ціль (у
# авто-режимі ціль постійно синхронізується з рекомендованою вологістю)
# коливаються біля межі +-dry_tolerance, реле може клацати щосекунди).
MIN_AUTO_CYCLE_SECONDS = 90


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


class DehumidifierDevice:
    """Holds all runtime state for one dehumidifier config entry."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry

        self.is_on: bool = False
        self.auto_mode: bool = True
        self.target_humidity: int = DEFAULT_TARGET_HUMIDITY
        self.auto_request: bool = False
        self._manual_active: bool = False
        self._pause_active: bool = False

        self._unsub_manual = None
        self._unsub_pause = None
        self._unsub_listeners: list = []
        self._last_auto_request_change = 0.0

        self.reload_options()

    # ---------------------------------------------------------------- config

    def reload_options(self) -> None:
        data = self.entry.data
        options = self.entry.options

        self.fan_entity = data.get(CONF_FAN_ENTITY)
        self.current_humidity_entity = data.get(CONF_CURRENT_HUMIDITY_ENTITY)
        self.abs_humidity_entity = data.get(CONF_ABS_HUMIDITY_ENTITY)

        self.delta = float(options.get(CONF_DELTA, DEFAULT_DELTA))
        self.min_humidity = int(options.get(CONF_MIN_HUMIDITY, DEFAULT_MIN_HUMIDITY))
        self.max_humidity = int(options.get(CONF_MAX_HUMIDITY, DEFAULT_MAX_HUMIDITY))
        self.dry_tolerance = float(options.get(CONF_DRY_TOLERANCE, DEFAULT_DRY_TOLERANCE))
        self.manual_runtime = int(options.get(CONF_MANUAL_RUNTIME, DEFAULT_MANUAL_RUNTIME))
        self.manual_pause = int(options.get(CONF_MANUAL_PAUSE, DEFAULT_MANUAL_PAUSE))

    @property
    def signal(self) -> str:
        return SIGNAL_UPDATE.format(self.entry.entry_id)

    @property
    def slug(self) -> str:
        """Базовий entity_id зі своїм префіксом - щоб ніколи не перетнутись зі старими vanna_* об'єктами."""
        base = slugify(self.entry.title) or "dehumidifier"
        return f"{ENTITY_ID_PREFIX}_{base}"

    # ------------------------------------------------------------ lifecycle

    async def async_setup(self) -> None:
        rec = self.recommended_humidity()
        if rec is not None:
            self.target_humidity = rec

        for entity_id in (self.abs_humidity_entity, self.current_humidity_entity):
            if entity_id:
                self._unsub_listeners.append(
                    async_track_state_change_event(self.hass, entity_id, self._async_source_changed)
                )

        if self.fan_entity:
            self._unsub_listeners.append(
                async_track_state_change_event(self.hass, self.fan_entity, self._async_fan_changed)
            )

    def async_unload(self) -> None:
        for unsub in self._unsub_listeners:
            unsub()
        self._unsub_listeners = []
        self._cancel_manual_timer()
        self._cancel_pause_timer()

    # ------------------------------------------------------- recommendation

    def recommended_humidity(self) -> int | None:
        """Рекомендована вологість = вологість сусідньої кімнати + дельта.

        Ліміти min/max застосовуються лише коли увімкнено авто-режим.
        Коли авто-режим вимкнено - ліміти ігноруються (результат лише
        затиснутий у фізично можливих межах 0-100%).
        """
        neighbor_state = self.hass.states.get(self.abs_humidity_entity) if self.abs_humidity_entity else None
        if neighbor_state is None:
            return None

        try:
            neighbor_humidity = float(neighbor_state.state)
        except (TypeError, ValueError):
            return None

        result = neighbor_humidity + self.delta

        if self.auto_mode:
            result = _clamp(result, self.min_humidity, self.max_humidity)
        else:
            result = _clamp(result, 0, 100)

        return int(round(result))

    def current_humidity(self) -> float | None:
        state = self.hass.states.get(self.current_humidity_entity) if self.current_humidity_entity else None
        if state is None:
            return None
        try:
            return float(state.state)
        except (TypeError, ValueError):
            return None

    # -------------------------------------------------------- state machine

    @property
    def status(self) -> str:
        if not self.is_on:
            return STATUS_OFF
        if self._pause_active:
            return STATUS_PAUSE
        if self._manual_active and self.auto_request:
            return STATUS_DRYING_MANUAL
        if self._manual_active:
            return STATUS_MANUAL
        if self.auto_request:
            return STATUS_DRYING
        return STATUS_IDLE

    @property
    def fan_should_run(self) -> bool:
        return self.is_on and not self._pause_active and (self._manual_active or self.auto_request)

    def _update_auto_request(self) -> None:
        if not self.is_on:
            self.auto_request = False
            return
        current = self.current_humidity()
        if current is None:
            return

        desired = self.auto_request
        if current > self.target_humidity + self.dry_tolerance:
            desired = True
        elif current <= self.target_humidity - self.dry_tolerance:
            desired = False

        if desired == self.auto_request:
            return

        # Anti short-cycle: не даємо реле клацати частіше, ніж раз на
        # MIN_AUTO_CYCLE_SECONDS, навіть якщо вологість/ціль смикаються
        # прямо на межі гістерезису.
        now = time.monotonic()
        if now - self._last_auto_request_change < MIN_AUTO_CYCLE_SECONDS:
            return

        self.auto_request = desired
        self._last_auto_request_change = now

    def recompute(self) -> None:
        self._update_auto_request()
        should_run = self.fan_should_run

        if self.fan_entity:
            state = self.hass.states.get(self.fan_entity)
            currently_on = bool(state and state.state == "on")
            if should_run != currently_on:
                self.hass.async_create_task(
                    self.hass.services.async_call(
                        "switch",
                        "turn_on" if should_run else "turn_off",
                        {"entity_id": self.fan_entity},
                        blocking=False,
                    )
                )

        async_dispatcher_send(self.hass, self.signal)

    # ------------------------------------------------------------ actions

    def async_turn_on(self) -> None:
        self.is_on = True
        if self.auto_mode:
            rec = self.recommended_humidity()
            if rec is not None:
                self.target_humidity = rec
        self.recompute()

    def async_turn_off(self) -> None:
        """Vanna - Full Stop Handler."""
        self.is_on = False
        self._cancel_manual_timer()
        self._cancel_pause_timer()
        self.auto_request = False
        self.recompute()

    def async_set_humidity(self, humidity: float) -> None:
        self.target_humidity = int(_clamp(humidity, 0, 100))
        self.recompute()

    def async_set_auto_mode(self, enabled: bool) -> None:
        self.auto_mode = enabled
        if enabled:
            rec = self.recommended_humidity()
            if rec is not None:
                self.target_humidity = rec
        self.recompute()

    def async_manual_toggle(self) -> None:
        """script.vanna_manual_toggle."""
        if self._manual_active:
            self._cancel_manual_timer()
            self._start_pause_timer()
        else:
            self._cancel_pause_timer()
            if not self.is_on:
                self.is_on = True
            self._start_manual_timer()
        self.recompute()

    # ------------------------------------------------------------- timers

    def _start_manual_timer(self) -> None:
        self._cancel_manual_timer()
        self._manual_active = True

        @callback
        def _expire(_now):
            self._unsub_manual = None
            self._manual_active = False
            self.recompute()

        self._unsub_manual = async_call_later(self.hass, self.manual_runtime * 60, _expire)

    def _cancel_manual_timer(self) -> None:
        if self._unsub_manual:
            self._unsub_manual()
            self._unsub_manual = None
        self._manual_active = False

    def _start_pause_timer(self) -> None:
        self._cancel_pause_timer()
        self._pause_active = True

        @callback
        def _expire(_now):
            self._unsub_pause = None
            self._pause_active = False
            self.recompute()

        self._unsub_pause = async_call_later(self.hass, self.manual_pause * 60, _expire)

    def _cancel_pause_timer(self) -> None:
        if self._unsub_pause:
            self._unsub_pause()
            self._unsub_pause = None
        self._pause_active = False

    # ----------------------------------------------------------- listeners

    @callback
    def _async_source_changed(self, _event: Event) -> None:
        """Vanna - Auto Target Humidity Sync."""
        if self.auto_mode and self.is_on:
            rec = self.recommended_humidity()
            if rec is not None:
                self.target_humidity = rec
        self.recompute()

    @callback
    def _async_fan_changed(self, event: Event) -> None:
        """Physical Fan ON/OFF Starts/Pauses Manual."""
        new_state = event.data.get("new_state")
        if new_state is None:
            return

        if new_state.state == "on":
            if self._pause_active:
                self.async_manual_toggle()
            elif not self.auto_request and not self._manual_active and not self._pause_active:
                self.async_manual_toggle()
        elif new_state.state == "off":
            if self._manual_active:
                self.async_manual_toggle()
        else:
            self.recompute()
