"""Constants for HA Smart Dehumidifier."""

DOMAIN = "ha_smart_dehumidifier"

CONF_FAN_ENTITY = "fan_entity"
CONF_CURRENT_HUMIDITY_ENTITY = "current_humidity_entity"
CONF_ABS_HUMIDITY_ENTITY = "abs_humidity_entity"

# Датчики температури, потрібні для коректного перерахунку відносної
# вологості в абсолютну (г/м3) і назад - порівняння між кімнатами
# ведеться в абсолютній вологості, користувачу завжди показується відносна.
CONF_ROOM_TEMP_ENTITY = "room_temp_entity"
CONF_NEIGHBOR_TEMP_ENTITY = "neighbor_temp_entity"

CONF_DELTA = "delta"
CONF_MIN_HUMIDITY = "min_humidity"
CONF_MAX_HUMIDITY = "max_humidity"
CONF_DRY_TOLERANCE = "dry_tolerance"
CONF_MANUAL_RUNTIME = "manual_runtime"
CONF_MANUAL_PAUSE = "manual_pause"

DEFAULT_DELTA = 3.75  # % (відносний режим) або г/м3 (абсолютний режим, обидва датчики температури) - обирається автоматично
DEFAULT_MIN_HUMIDITY = 65
DEFAULT_MAX_HUMIDITY = 85
DEFAULT_DRY_TOLERANCE = 5
DEFAULT_MANUAL_RUNTIME = 20
DEFAULT_MANUAL_PAUSE = 20
DEFAULT_TARGET_HUMIDITY = 70

ENTITY_ID_PREFIX = "smart"

STATUS_OFF = "off"
STATUS_AUTO = "auto"  # вентилятор працює через спрацювання вологості (гістерезис)
STATUS_IDLE = "idle"  # "очікування": увімкнено, вентилятор не працює (незалежно від авто-режиму)
STATUS_MANUAL = "manual"  # ручний режим (права кнопка), вологість ще НЕ спрацювала
STATUS_MANUAL_AUTO = "manual_auto"  # ручний режим одночасно з вологістю, що вже спрацювала
STATUS_PAUSE = "pause"  # ручний режим щойно вимкнено вручну - коротка пауза перед повторним автовизначенням

PLATFORMS = ["humidifier", "sensor", "switch", "button", "number"]

CARD_URL_BASE = "/ha_smart_dehumidifier_files"
CARD_JS_URL = f"{CARD_URL_BASE}/index.js"
