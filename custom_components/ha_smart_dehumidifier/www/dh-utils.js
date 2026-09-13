export const DEFAULT_LAYOUT_BASE_WIDTH = 400;
export const DEFAULT_CONTROLS_MAX_WIDTH = 520;
export const TARGET_SYNC_GRACE_MS = 1800;

export function toFiniteNumber(value, fallback = 0) {
  const num = Number(value);
  return Number.isFinite(num) ? num : fallback;
}

export function toPositiveNumber(value, fallback, min = 1) {
  return Math.max(min, toFiniteNumber(value, fallback));
}

export function clamp(value, min, max) {
  return Math.min(Math.max(toFiniteNumber(value, min), min), max);
}

export function layoutUnit(value, layoutBaseWidth = DEFAULT_LAYOUT_BASE_WIDTH) {
  const base = toPositiveNumber(layoutBaseWidth, DEFAULT_LAYOUT_BASE_WIDTH);
  return `${(toFiniteNumber(value, 0) / base) * 100}cqw`;
}

export function getEntityState(card, entityId) {
  return entityId ? card?._hass?.states?.[entityId] : undefined;
}

export function readNumberState(card, entityId) {
  const stateObj = getEntityState(card, entityId);
  if (!stateObj) return null;
  const raw = Number(stateObj.state);
  return Number.isFinite(raw) ? raw : null;
}

export function isEntityOn(card, entityId) {
  return getEntityState(card, entityId)?.state === 'on';
}

export function isMainEntityOn(card, entityId) {
  const state = getEntityState(card, entityId)?.state;
  return !!state && state !== 'off' && state !== 'unavailable' && state !== 'unknown';
}

export function callHA(card, domain, service, data = {}) {
  if (!card?._hass) return;
  card._hass.callService(domain, service, data);
}

export function readHumidityTarget(card, entityId, fallback = 50) {
  const attrs = getEntityState(card, entityId)?.attributes || {};
  if (attrs.target_humidity !== undefined) return clamp(attrs.target_humidity, 0, 100);
  if (attrs.humidity !== undefined) return clamp(attrs.humidity, 0, 100);
  return clamp(fallback, 0, 100);
}

// Ключі сутностей, які підтягуються автоматично (без ручного вибору):
// частина — обрані користувачем під час налаштування пристрою
// (fan_entity, current_humidity_entity), решта — сутності, які створив
// сам пристрій.
export const AUTO_DERIVED_ENTITY_KEYS = [
  'fan_entity',
  'current_humidity_entity',
  'status_entity',
  'calc_entity',
  'auto_entity',
  'manual_script_entity',
  'delta_entity',
  'min_rh_entity',
  'max_rh_entity',
  'manual_runtime_entity',
  'manual_pause_runtime_entity',
];

export function deriveConfig(config = {}, hass = null) {
  // Для власного бекенду ha_smart_dehumidifier усі супутні сутності мають
  // передбачуваний entity_id (той самий object_id, що й у entity), тож їх
  // не потрібно вказувати вручну — досить обрати лише `entity`. Це запасний
  // варіант на випадок, якщо hass ще недоступний (перший рендер).
  const objectId = typeof config.entity === 'string' ? config.entity.split('.')[1] : null;

  const guessed = objectId
    ? {
        status_entity: `sensor.${objectId}_status`,
        calc_entity: `sensor.${objectId}_recommended_humidity`,
        auto_entity: `switch.${objectId}_auto_mode`,
        manual_script_entity: `button.${objectId}_manual_toggle`,
        delta_entity: `number.${objectId}_delta`,
        min_rh_entity: `number.${objectId}_min_humidity`,
        max_rh_entity: `number.${objectId}_max_humidity`,
        manual_runtime_entity: `number.${objectId}_manual_runtime`,
        manual_pause_runtime_entity: `number.${objectId}_manual_pause`,
      }
    : {};

  // Достовірні значення: сам пристрій публікує їх як атрибути стану
  // головної сутності (entity) — це ті самі сутності, обрані під час
  // налаштування пристрою (fan_entity, current_humidity_entity), і ті, що
  // створив сам пристрій, знайдені через реєстр сутностей (коректно,
  // навіть якщо object_id відрізняється від назви пристрою).
  const stateAttrs = hass?.states?.[config.entity]?.attributes || {};
  const fromDevice = {};
  for (const key of AUTO_DERIVED_ENTITY_KEYS) {
    if (stateAttrs[key]) fromDevice[key] = stateAttrs[key];
  }

  return { ...guessed, ...fromDevice, ...config };
}

export function hasEqualDerivedEntities(a, b) {
  for (const key of AUTO_DERIVED_ENTITY_KEYS) {
    if ((a?.[key] ?? null) !== (b?.[key] ?? null)) return false;
  }
  return true;
}

export function readCurrentHumidity(card, config = {}, fallback = 50) {
  const hass = card?._hass;
  const currentEntity =
    config.current_humidity_entity ||
    config.humidity_entity ||
    config.current_entity;

  if (currentEntity && hass?.states?.[currentEntity]) {
    return clamp(hass.states[currentEntity].state, 0, 100);
  }

  const attrs = getEntityState(card, config.entity)?.attributes || {};
  if (attrs.current_humidity !== undefined) return clamp(attrs.current_humidity, 0, 100);
  if (attrs.humidity !== undefined) return clamp(attrs.humidity, 0, 100);
  return clamp(fallback, 0, 100);
}

export function formatElapsedSince(lastChanged, now = Date.now()) {
  if (!lastChanged) return null;

  const startedAt = new Date(lastChanged).getTime();
  if (!Number.isFinite(startedAt)) return null;

  const diffSecs = Math.max(0, Math.floor((now - startedAt) / 1000));
  const hours = Math.floor(diffSecs / 3600);
  const minutes = Math.floor((diffSecs % 3600) / 60);
  const seconds = diffSecs % 60;

  if (hours > 0) {
    return `${hours}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
  }

  return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
}
