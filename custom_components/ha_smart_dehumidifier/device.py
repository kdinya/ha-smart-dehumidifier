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

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_call_later, async_track_state_change_event
from homeassistant.util import slugify

from . import humidity_math
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
    CONF_NEIGHBOR_TEMP_ENTITY,
    CONF_ROOM_TEMP_ENTITY,
    DEFAULT_DELTA,
    DEFAULT_DRY_TOLERANCE,
    DEFAULT_MANUAL_PAUSE,
    DEFAULT_MANUAL_RUNTIME,
    DEFAULT_MAX_HUMIDITY,
    DEFAULT_MIN_HUMIDITY,
    DEFAULT_TARGET_HUMIDITY,
    DOMAIN,
    ENTITY_ID_PREFIX,
    STATUS_AUTO,
    STATUS_IDLE,
    STATUS_MANUAL,
    STATUS_OFF,
    STATUS_ON,
    STATUS_PAUSE,
)

_LOGGER = logging.getLogger(__name__)

SIGNAL_UPDATE = f"{DOMAIN}_update_{{}}"


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

        self.reload_options()

    # ---------------------------------------------------------------- config

    def reload_options(self) -> None:
        data = self.entry.data
        options = self.entry.options

        self.fan_entity = data.get(CONF_FAN_ENTITY)
        self.current_humidity_entity = data.get(CONF_CURRENT_HUMIDITY_ENTITY)
        self.abs_humidity_entity = data.get(CONF_ABS_HUMIDITY_ENTITY)
        self.room_temp_entity = data.get(CONF_ROOM_TEMP_ENTITY)
        self.neighbor_temp_entity = data.get(CONF_NEIGHBOR_TEMP_ENTITY)

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

        watched_entities = (
            self.abs_humidity_entity,
            self.current_humidity_entity,
            self.room_temp_entity,
            self.neighbor_temp_entity,
        )
        for entity_id in watched_entities:
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

    @property
    def uses_absolute_humidity(self) -> bool:
        """True, якщо в обох кімнатах налаштовано датчики температури.

        В цьому режимі дельта - в абсолютних одиницях (г/м3) і додається
        ДО перерахунку у відсотки. Без обох датчиків температури дельта -
        у відсоткових пунктах (стара поведінка, пряме порівняння %).
        """
        return bool(self.room_temp_entity and self.neighbor_temp_entity)

    def _read_float(self, entity_id: str | None) -> float | None:
        if not entity_id:
            return None
        state = self.hass.states.get(entity_id)
        if state is None:
            return None
        try:
            return float(state.state)
        except (TypeError, ValueError):
            return None

    def neighbor_humidity(self) -> float | None:
        """Відносна вологість сусідньої (референтної) кімнати, як є з датчика, %."""
        return self._read_float(self.abs_humidity_entity)

    def neighbor_temp(self) -> float | None:
        return self._read_float(self.neighbor_temp_entity)

    def room_temp(self) -> float | None:
        return self._read_float(self.room_temp_entity)

    def absolute_humidity_neighbor(self) -> float | None:
        """Абсолютна вологість сусідньої кімнати, г/м3 (потребує датчик температури)."""
        return humidity_math.absolute_humidity(self.neighbor_humidity(), self.neighbor_temp())

    def absolute_humidity_room(self) -> float | None:
        """Абсолютна вологість кімнати з осушувачем, г/м3 (потребує датчик температури)."""
        return humidity_math.absolute_humidity(self.current_humidity(), self.room_temp())

    def recommended_humidity(self) -> int | None:
        """Рекомендована (цільова) відносна вологість для кімнати з осушувачем.

        Автоматичний вибір режиму порівняння - залежно від того, чи
        налаштовано ОБИДВА датчики температури (своєї і сусідньої кімнати):

        - Є обидва датчики температури (uses_absolute_humidity=True):
          порівняння і дельта - в абсолютній вологості (г/м3), яка не
          залежить від температури і коректно відображає реальну кількість
          вологи в повітрі. Беремо абсолютну вологість сусідньої кімнати,
          додаємо дельту (г/м3) - і вже цю суму перераховуємо в еквівалентні
          відсотки відносної вологості для температури кімнати з осушувачем.
        - Немає хоча б одного датчика температури: стара поведінка - пряме
          порівняння відсотків, дельта у відсоткових пунктах (вологість
          сусідньої кімнати + дельта).

        Ліміти min/max застосовуються лише коли увімкнено авто-режим.
        Коли авто-режим вимкнено - ліміти ігноруються (результат лише
        затиснутий у фізично можливих межах 0-100%).
        """
        neighbor_humidity = self.neighbor_humidity()
        if neighbor_humidity is None:
            return None

        if self.uses_absolute_humidity:
            neighbor_abs = humidity_math.absolute_humidity(neighbor_humidity, self.neighbor_temp())
            equivalent_rh = None
            if neighbor_abs is not None:
                target_abs = max(0.0, neighbor_abs + self.delta)
                equivalent_rh = humidity_math.relative_humidity_from_absolute(target_abs, self.room_temp())
            result = equivalent_rh if equivalent_rh is not None else (neighbor_humidity + self.delta)
        else:
            result = neighbor_humidity + self.delta

        if self.auto_mode:
            result = _clamp(result, self.min_humidity, self.max_humidity)
        else:
            result = _clamp(result, 0, 100)

        return int(round(result))

    def current_humidity(self) -> float | None:
        return self._read_float(self.current_humidity_entity)

    # -------------------------------------------------------- state machine

    @property
    def status(self) -> str:
        """Видимий статус пристрою.

        - off: вимкнено (кнопка OFF)
        - manual: ручний режим (права кнопка), поки що працює таймер
        - pause: ручний режим щойно вимкнено вручну - коротка пауза перед
          тим, як знову запрацює автовизначення фізичного перемикача
        - auto: авто-режим увімкнений і вентилятор фактично працює
        - on: авто-режим вимкнений, пристрій увімкнено (середня кнопка),
          вентилятор фактично працює
        - idle ("очікування"): увімкнено, вентилятор не працює - вологість
          ще не досягла цілі. Стосується як авто-, так і не-авто режиму.
        """
        if not self.is_on:
            return STATUS_OFF
        if self._pause_active:
            return STATUS_PAUSE
        if self._manual_active:
            return STATUS_MANUAL
        if self.auto_request:
            return STATUS_AUTO if self.auto_mode else STATUS_ON
        return STATUS_IDLE

    @property
    def fan_should_run(self) -> bool:
        return self.is_on and not self._pause_active and (self._manual_active or self.auto_request)

    def _update_auto_request(self) -> None:
        """Керування вентилятором за поточною вологістю.

        Асиметричний гістерезис, як просив користувач:
        - УВІМКНУТИ, щойно вологість досягає цільової (>=) - без додаткового
          запасу зверху, реагуємо одразу.
        - ВИМКНУТИ лише коли вологість опуститься нижче цільової на
          dry_tolerance ("гістерезис" в Options) - запас знизу потрібен,
          щоб не клацати реле щоразу, як вологість на мить торкнеться цілі.
        """
        if not self.is_on:
            self.auto_request = False
            return
        current = self.current_humidity()
        if current is None:
            return

        desired = self.auto_request
        if current >= self.target_humidity:
            desired = True
        elif current <= self.target_humidity - self.dry_tolerance:
            desired = False

        if desired == self.auto_request:
            return

        self.auto_request = desired

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
        # Будь-яка ручна зміна цільової вологості (кнопки +/-, повзунок,
        # клік по панелі авто- чи цільової вологості) одразу вимикає
        # авто-режим, щоб наступна ж синхронізація з сенсорів
        # (_async_source_changed) не перезаписала вибір користувача.
        self.auto_mode = False
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
