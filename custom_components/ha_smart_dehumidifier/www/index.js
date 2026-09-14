import './dehumidifier-card.js';
import './dehumidifier-editor.js';

export const HA_SMART_DEHUMIDIFIER_VERSION = '1.0.3';

console.info(
  `%c ha-smart-dehumidifier %c v${HA_SMART_DEHUMIDIFIER_VERSION} `,
  'background:#0f1720;color:#7dd3fc;padding:2px 8px;border-radius:8px 0 0 8px;font-weight:700;',
  'background:#111827;color:#e5e7eb;padding:2px 8px;border-radius:0 8px 8px 0;font-weight:700;'
);

window.customCards = window.customCards || [];
window.customCards.push({
  type: 'ha-smart-dehumidifier',
  name: 'HA Smart Dehumidifier',
  description: 'Картка керування розумним осушувачем (ha-smart-dehumidifier)',
});
