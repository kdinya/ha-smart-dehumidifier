import { html } from '../files/lit-proxy.js';

import {
  toFiniteNumber,
  layoutUnit,
  isMainEntityOn,
  readCurrentHumidity,
  getLayoutBaseWidth,
} from '../dh-utils.js';

// Глобальне завантаження локального шрифту (обхід ізоляції Shadow DOM).
// Шрифт вбудовано напряму як base64 (не через мережевий url()) — файл
// зовсім маленький (~2КБ), і саме мережевий запит за .woff був причиною
// короткочасного "блимання" запасним шрифтом (monospace) на першому
// завантаженні картки, доки .woff ще не встиг завантажитись: браузер
// одразу малював текст запасним шрифтом, а потім, коли .woff нарешті
// приходив, перемальовував семисегментним. Вбудований base64 доступний
// синхронно разом із самим CSS-правилом — жодного окремого запиту й
// жодної паузи для "блимання" немає.
if (!document.getElementById('dh-local-7seg-font')) {
  const fontStyle = document.createElement('style');
  fontStyle.id = 'dh-local-7seg-font';
  fontStyle.innerHTML = `
    @font-face {
      font-family: '7segment';
      src: url('data:font/woff;base64,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') format('woff');
      font-weight: normal;
      font-style: normal;
      font-display: block;
    }
  `;
  document.head.appendChild(fontStyle);
}

const DEFAULT_HUMIDITY = 50;

function splitHumidity(value) {
  const rounded = Math.round(toFiniteNumber(value, DEFAULT_HUMIDITY) * 10);
  const intPart = Math.trunc(rounded / 10);
  const decPart = Math.abs(rounded % 10);

  return {
    intText: String(intPart),
    decText: String(decPart),
    hasDecimal: decPart !== 0,
  };
}

function getHumidityInfoEntity(config = {}) {
  return (
    config.current_humidity_entity ||
    config.current_entity ||
    config.humidity_entity ||
    null
  );
}

function openMoreInfo(card, entityId) {
  if (!entityId) return;

  card.dispatchEvent(
    new CustomEvent('hass-more-info', {
      bubbles: true,
      composed: true,
      detail: { entityId },
    })
  );
}

export function renderCurrentHumidity(card, config = {}) {
  if (!(config.show_current ?? true)) return html``;

  const layoutBaseWidth = getLayoutBaseWidth(config);

  const isOn = isMainEntityOn(card, config.entity);
  const currentHumidity = readCurrentHumidity(card, config);
  // Крапки завантаження показуємо ЗАВЖДИ, коли датчика поточної вологості
  // ще немає (currentHumidity === null) - незалежно від того, який зараз
  // режим/статус (manual/pause теж можуть бути активні одночасно з тим,
  // що сам датчик вологості ще не віддав перше значення). Ніяких "--"
  // більше немає в коді зовсім.
  const isConnecting = currentHumidity === null;
  const value = isConnecting ? null : splitHumidity(currentHumidity);
  const infoEntityId = getHumidityInfoEntity(config);

  // Семисегментний шрифт — єдиний і незмінний для поточної вологості
  // (вибір шрифту прибрано з візуального редактора).
  const curFontFamily = "'7segment', monospace";

  const curSize = toFiniteNumber(config.cur_size, 140);
  const curDecSize = toFiniteNumber(config.cur_dec_size, 100);
  const curUnitSize = toFiniteNumber(config.cur_unit_size, 70);

  const curColorOn = config.cur_color_on ?? 'white';
  const curColorOff = config.cur_color_off ?? 'rgba(255,255,255,0.38)';
  const curDecColorOn = config.cur_dec_color_on ?? curColorOn;
  const curDecColorOff = config.cur_dec_color_off ?? curColorOff;
  const curUnitColorOn = config.cur_unit_color_on ?? 'rgba(255,255,255,0.60)';
  const curUnitColorOff = config.cur_unit_color_off ?? 'rgba(255,255,255,0.26)';

  // Складна тінь для імітації фізичного індикатора (тільки фаски та легке біле світіння)
  const curGlowOn = config.cur_glow_on ?? 
    '-1px -1px 1px rgba(255,255,255,0.4), ' +
    '1px 1px 1px rgba(0,0,0,0.6), ' +          
    '0 0 10px rgba(255,255,255,0.4)';           

  const curFontWeight = toFiniteNumber(config.cur_font_weight, 500);
  const curUnitWeight = toFiniteNumber(config.cur_unit_weight, 300);

  const curLetterSpacing = toFiniteNumber(config.cur_letter_spacing, -2);
  const curGap = toFiniteNumber(config.cur_gap, 3);
  const curUnitMarginLeft = toFiniteNumber(config.cur_unit_margin_left, 2);
  const curOffsetY = toFiniteNumber(config.cur_offset_y, 22);

  const curShowDecimal = config.cur_show_decimal ?? true;
  const curShowUnit = config.cur_show_unit ?? true;

  const mainColor = isOn ? curColorOn : curColorOff;
  const decColor = isOn ? curDecColorOn : curDecColorOff;
  const unitColor = isOn ? curUnitColorOn : curUnitColorOff;
  const mainShadow = isOn ? curGlowOn : 'none';
  const unitShadow = isOn ? '0 0 10px rgba(255,255,255,0.15)' : 'none';

  return html`
    <style>
      .dh-cur-layer {
        position: absolute;
        inset: 0;
        z-index: 18;
        pointer-events: none;
        display: flex;
        align-items: center;
        justify-content: center;
      }

      .dh-cur-wrap {
        position: relative;
        display: flex;
        align-items: center;
        justify-content: center;
        transform: translateY(${layoutUnit(curOffsetY, layoutBaseWidth)});
        pointer-events: auto;
      }

      .dh-cur-button {
        position: relative;
        z-index: 2;
        display: flex;
        align-items: baseline;
        gap: ${layoutUnit(curGap, layoutBaseWidth)};
        line-height: 1;
        border: none;
        background: transparent;
        padding: 0;
        margin: 0;
        cursor: ${infoEntityId ? 'pointer' : 'default'};
        pointer-events: auto;
        -webkit-tap-highlight-color: transparent;
      }

      .dh-cur-button:focus-visible {
        outline: none;
        filter: drop-shadow(0 0 8px rgba(255,255,255,0.35));
      }

      .dh-cur-int,
      .dh-cur-dec {
        font-family: ${curFontFamily};
        font-weight: ${curFontWeight};
      }

      .dh-cur-int {
        font-size: ${layoutUnit(curSize, layoutBaseWidth)};
        letter-spacing: ${layoutUnit(curLetterSpacing, layoutBaseWidth)};
        color: ${mainColor};
        text-shadow: ${mainShadow};
        filter: drop-shadow(0 2px 10px rgba(0,0,0,0.35));
      }

      .dh-cur-dec {
        font-size: ${layoutUnit(curDecSize, layoutBaseWidth)};
        color: ${decColor};
        text-shadow: ${mainShadow};
      }

      .dh-cur-unit {
        font-size: ${layoutUnit(curUnitSize, layoutBaseWidth)};
        font-weight: ${curUnitWeight};
        color: ${unitColor};
        margin-left: ${layoutUnit(curUnitMarginLeft, layoutBaseWidth)};
        text-shadow: ${unitShadow};
      }

      @keyframes dh-cur-connecting-pulse {
        0%, 100% { opacity: 0.25; transform: scale(0.85); }
        50% { opacity: 1; transform: scale(1); }
      }

      .dh-cur-connecting {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        height: ${layoutUnit(curSize, layoutBaseWidth)};
        gap: ${layoutUnit(curSize * 0.16, layoutBaseWidth)};
      }

      .dh-cur-connecting-dot {
        display: inline-block;
        width: ${layoutUnit(curSize * 0.15, layoutBaseWidth)};
        height: ${layoutUnit(curSize * 0.15, layoutBaseWidth)};
        border-radius: 50%;
        background: ${mainColor};
        box-shadow: ${mainShadow};
        animation: dh-cur-connecting-pulse 1.2s ease-in-out infinite;
      }

      .dh-suspended .dh-cur-connecting-dot {
        animation-play-state: paused !important;
      }

      .dh-cur-connecting-dot:nth-child(2) {
        animation-delay: 0.2s;
      }

      .dh-cur-connecting-dot:nth-child(3) {
        animation-delay: 0.4s;
      }
    </style>

    <div class="dh-cur-layer">
      <div class="dh-cur-wrap">
        <button
          class="dh-cur-button"
          type="button"
          title="${infoEntityId ? 'Показати властивості датчика' : ''}"
          @pointerdown=${(e) => e.stopPropagation()}
          @click=${(e) => {
            e.stopPropagation();
            openMoreInfo(card, infoEntityId);
          }}
        >
          ${isConnecting
            ? html`
              <span class="dh-cur-connecting" aria-hidden="true">
                <span class="dh-cur-connecting-dot"></span>
                <span class="dh-cur-connecting-dot"></span>
                <span class="dh-cur-connecting-dot"></span>
              </span>
            `
            : html`<span class="dh-cur-int">${value.intText}</span>`}

          ${!isConnecting && curShowDecimal && value.hasDecimal
            ? html`<span class="dh-cur-dec">.${value.decText}</span>`
            : html``}

          ${!isConnecting && curShowUnit
            ? html`<span class="dh-cur-unit">%</span>`
            : html``}
        </button>
      </div>
    </div>
  `;
}