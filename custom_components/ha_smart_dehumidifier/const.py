"""Constants for HA Smart Dehumidifier."""

DOMAIN = "ha_smart_dehumidifier"

CONF_FAN_ENTITY = "fan_entity"
CONF_CURRENT_HUMIDITY_ENTITY = "current_humidity_entity"
CONF_ABS_HUMIDITY_ENTITY = "abs_humidity_entity"
CONF_REF_TEMP_ENTITY = "ref_temp_entity"

CONF_DELTA = "delta"
CONF_MIN_HUMIDITY = "min_humidity"
CONF_MAX_HUMIDITY = "max_humidity"
CONF_DRY_TOLERANCE = "dry_tolerance"
CONF_MANUAL_RUNTIME = "manual_runtime"
CONF_MANUAL_PAUSE = "manual_pause"

DEFAULT_DELTA = 0.5
DEFAULT_MIN_HUMIDITY = 30
DEFAULT_MAX_HUMIDITY = 80
DEFAULT_DRY_TOLERANCE = 3
DEFAULT_MANUAL_RUNTIME = 20
DEFAULT_MANUAL_PAUSE = 20
DEFAULT_TARGET_HUMIDITY = 50

STATUS_OFF = "off"
STATUS_IDLE = "idle"
STATUS_MANUAL = "manual"
STATUS_DRYING = "drying"
STATUS_DRYING_MANUAL = "drying_manual"
STATUS_PAUSE = "pause"

PLATFORMS = ["humidifier", "sensor", "switch", "button"]

CARD_URL_BASE = "/ha_smart_dehumidifier_files"
CARD_JS_URL = f"{CARD_URL_BASE}/index.js"
