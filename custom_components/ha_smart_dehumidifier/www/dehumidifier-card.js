import { html, css, LitElement, unsafeCSS } from './files/lit-proxy.js';

import { renderArcSlider } from './components/arc-slider.js';
import { renderCurrentHumidity } from './components/current-humidity.js';
import { renderHumidityPanel } from './components/humidity-panel.js';
import { renderBottomControls } from './components/bottom-controls.js';
import { renderVisualEffects } from './components/visual-effects.js';
import { renderSettingsPanel } from './components/settings-panel.js';

import {
  toFiniteNumber,
  toPositiveNumber,
  formatElapsedSince, // Додано для прямого оновлення часу
  deriveConfig,
  hasEqualDerivedEntities,
} from './dh-utils.js';

const DEFAULT_BORDER_RADIUS = 28;
const DEFAULT_HEIGHT_PERCENT = 105;
const TICK_MS = 1000;
// Той самий "внутрішній" масштаб, що й у _renderSceneContent() (device_design_width
// для дуги/панелей/кнопок) - потрібен тут для компенсації зсуву нижньої панелі (див. _getLayoutData).
const SCENE_REFERENCE_WIDTH = 400;
const NOISE_DATA_URI = `url("data:image/svg+xml,%3Csvg viewBox='0 0 400 400' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.8' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)'/%3E%3C/svg%3E")`;

function normalizeAlign(value) {
  return value === 'center' || value === 'right' ? value : 'left';
}


function extractTrackedEntities(config = {}) {
  const ids = new Set();

  for (const [key, value] of Object.entries(config)) {
    if (!value) continue;

    if (key === 'entity' || key.endsWith('_entity')) {
      if (typeof value === 'string' && value.trim()) ids.add(value);
      continue;
    }

    if (key.endsWith('_entities') && Array.isArray(value)) {
      for (const item of value) {
        if (typeof item === 'string' && item.trim()) ids.add(item);
      }
    }
  }

  return [...ids];
}

function hasTrackedEntityChange(prevHass, nextHass, entityIds) {
  if (!prevHass || !nextHass) return true;
  if (!entityIds?.length) return true;

  const prevStates = prevHass.states || {};
  const nextStates = nextHass.states || {};

  for (const entityId of entityIds) {
    if ((prevStates[entityId] || null) !== (nextStates[entityId] || null)) {
      return true;
    }
  }

  return false;
}

class MyDehumidifierCard extends LitElement {
  static properties = {
    _config: { state: true },
    _hass: { state: true },
    // _tick ВИДАЛЕНО: таймер більше не провокує щосекундний повний рендер
    _targetHumidity: { state: true },
    _isSettingsOpen: { state: true },
    _humPanelAutoPopupOpen: { state: true },
    _openSections: { state: true },
  };

  static styles = css`
    :host {
      display: flex;
      justify-content: center;
      width: 100%;
      height: 100%;
      position: relative;
      container-type: inline-size;
    }

    ha-card {
      position: relative;
      overflow: hidden;
      background: transparent;
      border: none;
      box-shadow: none;
      padding: 0;
      margin: 0;
      width: 100%;
      /* Ширину картки повністю визначає розкладка HA (Masonry-колонка чи
         ширина комірки в Sections) - жодного власного максимуму тут
         більше немає ("Макс. ширина СКЛА" прибрано з редактора).
         aspect-ratio задає "бажану" висоту = ширина / glass_aspect_ratio
         (поки її вистачає) - САМЕ ЦЕ і є "Пропорція скла на ПК". Це
         ОДНОСПРЯМОВАНЕ обчислення (висота завжди виводиться з уже
         визначеної ширини) - на відміну від попередньої версії з
         ResizeObserver, тут немає циклу "вимірюємо власний розмір →
         підставляємо його ж назад у свій max-width", який раніше й
         гасив ефект (картка "переставала розтягуватись").
         min-height - непорушна нижня межа: природна висота приладу за
         його ВЛАСНИМ максимальним розміром (layout_base_width). Коли
         аспектна висота падає нижче цієї межі (вузький екран), min-height
         перемагає - картка більше не "тягне" власну форму і просто
         повторює висоту приладу; звідти й ширина далі рухається разом
         із шириною самого приладу (див. .dh-frame/.dh-device нижче).
         container-type тут НЕ застосовується (на відміну від .dh-frame-aspect
         нижче) - саме це раніше спричиняло повне зникнення картки:
         contain:size ігнорує вміст при визначенні власного розміру, а
         тут його все одно не потрібно - min-height рахується через
         100cqi відносно :host (він і так вже container-type:inline-size),
         а не відносно самої ha-card. Ніяких @container-брейкпоінтів -
         обидва правила діють завжди, перехід між станами суцільний
         (min()/calc() - неперервні функції ширини). */
      aspect-ratio: var(--dh-glass-ar-wide, 1.7);
      min-height: calc(
        min(100cqi, var(--dh-frame-max-width, 400px)) * var(--dh-frame-ar-num, 1)
        + var(--dh-pad-top, 0px) + var(--dh-pad-bottom, 16px)
      );
      box-sizing: border-box;
      border-radius: var(--dh-card-radius, 28px);
      display: flex;
      align-items: center;
      justify-content: var(--dh-justify, center);
    }

    .dh-card-bg,
    .dh-card-bg__base,
    .dh-card-bg__vignette,
    .dh-card-bg__glass-curve,
    .dh-card-bg__specular,
    .dh-card-bg__noise,
    .dh-card-bg__top-line,
    .dh-card-bg__edge {
      position: absolute;
    }

    .dh-card-bg {
      inset: 0;
      z-index: 0;
      overflow: hidden;
      pointer-events: none;
      border-radius: var(--dh-card-radius, 28px);
      background-color: #05070a;
      box-shadow: 0 20px 40px rgba(0, 0, 0, 0.7);
    }

    .dh-card-bg__base,
    .dh-card-bg__vignette,
    .dh-card-bg__noise,
    .dh-card-bg__edge { inset: 0; }

    .dh-card-bg__base {
      background: linear-gradient(180deg, #242a33 0%, #0b0e14 40%, #030406 100%);
    }

    .dh-card-bg__glass-curve {
      top: 0;
      left: 0;
      right: 0;
      height: clamp(120px, 45%, 300px);
      background: linear-gradient(180deg, rgba(255, 255, 255, 0.08) 0%, rgba(255, 255, 255, 0.01) 85%, transparent 100%);
      border-radius: 0 0 50% 50% / 0 0 25px 25px;
      border-bottom: 1px solid rgba(255, 255, 255, 0.03);
    }

    .dh-card-bg__specular {
      top: -20%;
      left: 50%;
      transform: translateX(-50%);
      width: min(150%, 800px);
      aspect-ratio: 2 / 1;
      border-radius: 50%;
      background: radial-gradient(ellipse at center, rgba(255, 255, 255, 0.18) 0%, rgba(255, 255, 255, 0.03) 40%, transparent 70%);
      mix-blend-mode: screen;
      filter: blur(8px);
    }

    .dh-card-bg__vignette {
      background: radial-gradient(ellipse at 50% 50%, transparent 30%, rgba(0, 0, 0, 0.8) 140%);
    }

    .dh-card-bg__noise {
      opacity: 0.03;
      background-image: ${unsafeCSS(NOISE_DATA_URI)};
      mix-blend-mode: overlay;
    }

    .dh-card-bg__edge {
      border-radius: inherit;
      box-shadow:
        inset 0 0 0 2px rgba(255, 255, 255, 0.15),
        inset 0 0 20px 2px rgba(255, 255, 255, 0.08),
        inset 0 2px 8px rgba(255, 255, 255, 0.35),
        inset 0 -2px 8px rgba(255, 255, 255, 0.15);
    }

    .dh-card-bg__top-line {
      top: 0;
      left: 5%;
      right: 5%;
      height: 2px;
      opacity: 0.9;
      background: linear-gradient(90deg, rgba(255,255,255,0) 0%, rgba(255,255,255,0.3) 20%, rgba(255,255,255,0.7) 50%, rgba(255,255,255,0.3) 80%, rgba(255,255,255,0) 100%);
      box-shadow: 0 1px 8px rgba(255,255,255,0.6);
    }

    .dh-frame {
      /* Ширина - чистий CSS min(), без JS-вимірювання: скільки дозволяє
         сама ha-card (100%), але не більше layout_base_width (природний
         максимум приладу). Висота: 100% від ha-card. ha-card тепер сама
         рахує свою висоту через aspect-ratio + min-height (glass_aspect_ratio,
         див. вище) - .dh-frame просто успадковує який би розмір вона не
         мала: і коли ha-card ВИЩА за природну висоту приладу (glassRatio-фаза),
         і коли вона РІВНО дорівнює їй (min-height переміг, фаза "разом").
         Той самий рядок коректно працює для обох випадків, без @container. */
      width: min(100%, var(--dh-frame-max-width, 400px));
      height: 100%;
      display: flex;
      flex-direction: column;
      justify-content: center;
      position: relative;
      z-index: 1;
    }

    .dh-frame-aspect {
      /* Ширина завжди точно дорівнює .dh-frame (100%). aspect-ratio
         однозначно виводить з неї висоту приладу. flex-grow:0 -
         принципово: коли ha-card, завдяки glass_aspect_ratio, стає
         ВИЩОЮ за природну висоту приладу, зайвий простір у .dh-frame НЕ
         повинен розтягувати прилад (це зламало б його форму) - він
         просто лишається порожнім і центрується навколо приладу через
         justify-content:center вище. flex-shrink:1 + min-height:0
         дозволяють ЦЬОМУ Ж правилу коректно СТИСНУТИСЯ, коли доступної
         висоти замало. container-type:size тут безпечний (на відміну
         від ha-card вище) - ширина й похідна від aspect-ratio висота тут
         ЗАВЖДИ визначені (ніколи не auto), тож contain:size нічого не
         колапсує - і .dh-scene/.dh-device нижче можуть надійно виміряти
         цю коробку через cqb, як і раніше. */
      width: 100%;
      aspect-ratio: var(--dh-frame-ar, 1);
      flex: 0 1 auto;
      min-height: 0;
      container-type: size;
      position: relative;
    }

    .dh-frame-top-spacer {
      flex: 0 0 auto;
      width: 100%;
      height: var(--dh-pad-top, 0px);
    }

    .dh-frame-bottom-spacer {
      flex: 0 0 auto;
      width: 100%;
      height: var(--dh-pad-bottom, 16px);
    }

    .dh-scene {
      position: absolute;
      inset: 0;
      box-sizing: border-box;
      padding: 0 var(--dh-pad-right, 14px) 0 var(--dh-pad-left, 14px);
      overflow: visible;
      display: flex;
      align-items: center;
      justify-content: var(--dh-device-justify, center);
      /* Найближчий контейнер розмірного запиту для .dh-device: cqi/cqb тут
         рахуються від ВЖЕ звуженого горизонтальними відступами і РЕАЛЬНО
         доступного (можливо стиснутого по висоті вище) простору - не від
         зовнішньої ha-card і не від "бажаної" aspect-ratio-висоти. */
      container-type: size;
    }

    .dh-device {
      position: relative;
      /* Єдина, безбрейкпоінтна формула "вписати найбільший прямокутник
         заданої форми (--dh-frame-ar) в доступну область": ширина, яку
         дозволяє ширина контейнера (95cqi), ширина, еквівалентна тому,
         що дозволяє ВИСОТА контейнера з урахуванням форми пристрою
         (95cqb * --dh-frame-ar-num), і налаштований максимум. Яке з трьох
         менше - те й перемагає, тож пристрій завжди повністю поміщається
         і по ширині, і по висоті, ніколи не обрізається і ніколи не
         зростає понад свій налаштований максимум. aspect-ratio виводить
         висоту з цієї ширини - форма пристрою завжди відповідає
         card_height_percent, а не примусово квадратна. */
      width: min(95cqi, calc(95cqb * var(--dh-frame-ar-num, 1)), var(--dh-frame-max-width, 400px));
      aspect-ratio: var(--dh-frame-ar, 1);
      /* Компенсація зсуву нижньої панелі кнопок (btns_bottom): якщо вона
         виштовхнута нижче за межі самого приладу, резервуємо стільки ж
         місця знизу через margin - тоді flex-центрування в .dh-scene
         рахує центр уже "приладу разом із панеллю", а не лише квадрата
         дуги, і зсув панелі більше не тягне весь прилад угору. */
      margin-bottom: calc(var(--dh-bottom-overhang, 0) * 100cqi);
      transform: translate(var(--dh-offset-x, 0px), var(--dh-offset-y, 0px));
      container-type: inline-size;
    }

    .dh-limit-layer {
      position: absolute;
      top: 0;
      bottom: 0;
      left: 50%;
      transform: translateX(-50%);
      width: 100%;
      pointer-events: none;
    }

    .dh-limit-layer > * {
      pointer-events: auto;
      max-width: 100% !important;
    }

    .dh-limit-arc { max-width: var(--dh-frame-max-width, 1000px); z-index: 10; }
    .dh-limit-target { z-index: 20; max-width: var(--dh-hum-panel-max, 240px); }
    .dh-limit-bottom { z-index: 25; max-width: var(--dh-controls-max, 520px); }
    .dh-limit-current { z-index: 5; max-width: var(--dh-cur-max, 400px); }

    .dh-cog-btn {
      position: absolute;
      top: 16px;
      right: 16px;
      width: 40px;
      height: 40px;
      border-radius: 50%;
      background: rgba(0,0,0,0.25);
      border: 1px solid rgba(255,255,255,0.05);
      color: rgba(255,255,255,0.4);
      z-index: 50;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: all 0.2s ease;
      box-shadow: 0 4px 10px rgba(0,0,0,0.2);
      cursor: pointer;
    }

    .dh-cog-btn:hover {
      background: rgba(0,0,0,0.5);
      color: rgba(255,255,255,0.9);
      transform: scale(1.05);
    }

    .dh-cog-btn ha-icon {
      --mdc-icon-size: 20px;
    }

    .dh-not-configured {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      gap: 10px;
      padding: 32px 16px;
      text-align: center;
      color: var(--secondary-text-color, rgba(255,255,255,0.6));
    }

    .dh-not-configured ha-icon {
      --mdc-icon-size: 32px;
      opacity: 0.6;
    }
  `;

  static getConfigElement() {
    return document.createElement('ha-smart-dehumidifier-editor');
  }

  constructor() {
    super();
    this._config = null;
    this._rawConfig = null;
    this._hass = null;

    this._timerInterval = null;
    this._trackedEntityIds = [];

    this._targetHumidity = null;
    this._ignoreStateUntil = 0;

    this._dragging = false;
    this._isSettingsOpen = false;
    this._humPanelAutoPopupOpen = false;
    this._openSections = { auto: true, manual: false };
  }

  connectedCallback() {
    super.connectedCallback();
    this._syncTicker();
  }

  disconnectedCallback() {
    this._stopTicker();
    super.disconnectedCallback();
  }

  setConfig(config) {
    // Порожній/початковий конфіг (щойно додана картка, пристрій ще не
    // обраний) не повинен кидати виняток — інакше падає рендер усього
    // діалогу редагування картки, а не лише прев'ю.
    this._rawConfig = {
      type: 'custom:ha-smart-dehumidifier',
      ...config,
    };
    this._config = deriveConfig(this._rawConfig, this._hass);

    this._trackedEntityIds = extractTrackedEntities(this._config);
    this._syncTicker();
  }

  _isFanRunning(hass = this._hass) {
    const fanEntity = this._config?.fan_entity;
    if (!fanEntity || !hass?.states) return false;
    return hass.states[fanEntity]?.state === 'on';
  }

  set hass(hass) {
    const oldHass = this._hass;
    const oldFanOn = this._isFanRunning(oldHass);

    this._hass = hass;

    // Підтягти сутності, які обрані під час налаштування пристрою та створені ним самим (fan_entity, status_entity тощо), коли стани вже доступні. Оновлюємо лише при реальній зміні, щоб не ломати оптимізацію ререндерів нижче.
    if (this._rawConfig) {
      const nextConfig = deriveConfig(this._rawConfig, hass);
      if (!hasEqualDerivedEntities(nextConfig, this._config)) {
        this._config = nextConfig;
      }
    }

    const newFanOn = this._isFanRunning(hass);
    if (oldFanOn !== newFanOn) {
      this._syncTicker();
    }

    this.requestUpdate('_hass', oldHass);
  }

  get hass() {
    return this._hass;
  }

  updated(changedProps) {
    if (changedProps.has('_config')) {
      this._trackedEntityIds = extractTrackedEntities(this._config || {});
      this._syncTicker();
    }
  }

  shouldUpdate(changedProps) {
    if (
      changedProps.has('_config') ||
      changedProps.has('_targetHumidity') ||
      changedProps.has('_isSettingsOpen') ||
      changedProps.has('_humPanelAutoPopupOpen') ||
      changedProps.has('_openSections')
    ) {
      return true;
    }

    if (changedProps.has('_hass')) {
      const prevHass = changedProps.get('_hass');
      return hasTrackedEntityChange(prevHass, this._hass, this._trackedEntityIds);
    }

    return true;
  }

  _shouldRunTicker() {
    return this.isConnected && this._isFanRunning();
  }// --- ВОТ ЭТА ФУНКЦИЯ БЫЛА ПРОПУЩЕНА ---
  _syncTicker() {
    if (this._shouldRunTicker()) this._startTicker();
    else this._stopTicker();
  }

  _startTicker() {
    if (this._timerInterval !== null) return;
    this._timerInterval = window.setInterval(() => {
      this._updateTimerDOM();
    }, TICK_MS);
  }

  _stopTicker() {
    if (this._timerInterval === null) return;
    clearInterval(this._timerInterval);
    this._timerInterval = null;
  }

  // Оновлення таймера безпосередньо в DOM (БЕЗ крашу LitElement)
  _updateTimerDOM() {
    if (!this.shadowRoot) return;
    
    const timerEl = this.shadowRoot.querySelector('.dh-timer-text');
    if (!timerEl) return;

    const fanEntity = this._config?.fan_entity;
    if (!fanEntity || !this._hass?.states?.[fanEntity]) return;

    const stateObj = this._hass.states[fanEntity];
    if (stateObj.state !== 'on') return;

    const newText = formatElapsedSince(stateObj.last_changed);
    if (!newText) return;
    
    // LitElement залишає коментарі-маркери всередині елемента.
    // Властивість .textContent знищує їх і ламає картку при наступному рендері.
    // Змінюємо ЛИШЕ текстовий вузол (nodeType === 3):
    for (const node of timerEl.childNodes) {
      if (node.nodeType === 3) {
        if (node.nodeValue !== newText) {
          node.nodeValue = newText;
        }
        return; // Оновили — виходимо
      }
    }
  }

  _getLayoutData() {
    const config = this._config || {};

    const borderRadius = Math.max(0, toFiniteNumber(config.card_border_radius, DEFAULT_BORDER_RADIUS));
    const glassAspectRatio = toPositiveNumber(config.glass_aspect_ratio, 1.7);
    const layoutBaseWidth = toPositiveNumber(config.layout_base_width, 510);
    const humPanelMax = toPositiveNumber(
      config.hum_panel_max_width,
      toPositiveNumber(config.hum_panel_width, 250)
    );
    const controlsMax = toPositiveNumber(config.controls_max_width, 500);
    const curMax = toPositiveNumber(config.cur_max_width, 400);
    const heightPercent = toPositiveNumber(config.card_height_percent, DEFAULT_HEIGHT_PERCENT);
    const frameRatioNum = 100 / heightPercent;
    const frameRatio = `100 / ${heightPercent}`;

    const align = normalizeAlign(config.alignment);

    let justifyContent = 'center';
    if (align === 'left') justifyContent = 'flex-start';
    if (align === 'right') justifyContent = 'flex-end';

    const padTopPx = toFiniteNumber(config.content_padding_top, 0);
    const padBottomPx = toFiniteNumber(config.content_padding_bottom, 0);

    // Нижня панель кнопок (btns_bottom) позиціюється відносно самого
    // приладу в тих самих "внутрішніх" одиницях, що й решта сцени
    // (масштаб відносно SCENE_REFERENCE_WIDTH - див. _renderSceneContent).
    // Від'ємне значення виштовхує панель НИЖЧЕ за межі приладу - тоді
    // геометричний центр .dh-device більше не збігається з візуальним
    // центром "приладу разом з панеллю". Компенсуємо це нижнім
    // margin на .dh-device (тієї ж пропорції) - flex-центрування в
    // .dh-scene тоді рахує центр уже з урахуванням цього запасу знизу,
    // і зсув панелі більше не тягне весь прилад угору.
    const btnsBottomPx = toFiniteNumber(config.btns_bottom, -30);
    const bottomOverhangRatio = Math.max(0, -btnsBottomPx) / SCENE_REFERENCE_WIDTH;

    return {
      borderRadius,
      glassAspectRatio,
      layoutBaseWidth,
      humPanelMax,
      controlsMax,
      curMax,
      frameRatioNum,
      frameRatio,
      justifyContent,
      padTop: `${padTopPx}px`,
      padBottom: `${padBottomPx}px`,
      padLeft: `${toFiniteNumber(config.content_padding_left, 10)}px`,
      padRight: `${toFiniteNumber(config.content_padding_right, 10)}px`,
      offsetX: `${toFiniteNumber(config.device_offset_x, 0)}px`,
      offsetY: `${toFiniteNumber(config.device_offset_y, 0)}px`,
      bottomOverhangRatio,
    };
  }

  _renderSceneContent() {
    const config = this._config;
    // device_design_width - НЕ те саме, що config.layout_base_width
    // ("Макс. ширина ПРИЛАДУ", піксельний cap для --dh-frame-max-width,
    // рахується в _getLayoutData). Це окрема, суто внутрішня геометрична
    // база координат ("прилад намальований як 400px завширшки"), у якій
    // задані всі px-подібні параметри дуги/панелей/кнопок/ефектів
    // (arc_radius, cur_size, btn_height і т.д.) - layoutUnit() переводить
    // їх у cqw ВІДНОСНО САМЕ ЦІЄЇ бази, а не відносно налаштованого
    // користувачем максимуму ширини приладу. Той самий SCENE_REFERENCE_WIDTH,
    // що й у _getLayoutData() (компенсація нижньої панелі) - єдине джерело.
    const renderConfig = { ...config, device_design_width: SCENE_REFERENCE_WIDTH };

    return html`
      ${renderVisualEffects(this, renderConfig)}

      <div class="dh-limit-layer dh-limit-arc">
        ${(config.show_arc ?? true) ? renderArcSlider(this, renderConfig) : null}
      </div>

      <div class="dh-limit-layer dh-limit-current">
        ${renderCurrentHumidity(this, renderConfig)}
      </div>

      <div class="dh-limit-layer dh-limit-target">
        ${renderHumidityPanel(this, renderConfig)}
      </div>

      <div class="dh-limit-layer dh-limit-bottom">
        ${renderBottomControls(this, renderConfig)}
      </div>
    `;
  }

  render() {
    if (!this._config || !this._hass) return html``;

    if (!this._config.entity) {
      return html`
        <ha-card>
          <div class="dh-not-configured">
            <ha-icon icon="mdi:air-humidifier-off"></ha-icon>
            <span>Оберіть пристрій «HA Smart Dehumidifier» у налаштуваннях картки</span>
          </div>
        </ha-card>
      `;
    }

    const layout = this._getLayoutData();

    const cardStyle = `
      --dh-card-radius: ${layout.borderRadius}px;
      --dh-glass-ar-wide: ${layout.glassAspectRatio};
      --dh-justify: ${layout.justifyContent};
      --dh-frame-max-width: ${layout.layoutBaseWidth}px;
      --dh-frame-ar-num: ${layout.frameRatioNum};
      --dh-pad-top: ${layout.padTop};
      --dh-pad-bottom: ${layout.padBottom};
    `;

    const frameStyle = `
      --dh-frame-ar: ${layout.frameRatio};
      --dh-hum-panel-max: ${layout.humPanelMax}px;
      --dh-controls-max: ${layout.controlsMax}px;
      --dh-cur-max: ${layout.curMax}px;
      --dh-pad-left: ${layout.padLeft};
      --dh-pad-right: ${layout.padRight};
      --dh-offset-x: ${layout.offsetX};
      --dh-offset-y: ${layout.offsetY};
      --dh-device-justify: ${layout.justifyContent};
      --dh-bottom-overhang: ${layout.bottomOverhangRatio};
    `;

    return html`
      <ha-card style="${cardStyle}">
        <div class="dh-card-bg" aria-hidden="true">
          <div class="dh-card-bg__base"></div>
          <div class="dh-card-bg__vignette"></div>
          <div class="dh-card-bg__glass-curve"></div>
          <div class="dh-card-bg__specular"></div>
          <div class="dh-card-bg__noise"></div>
          <div class="dh-card-bg__top-line"></div>
          <div class="dh-card-bg__edge"></div>
        </div>

        <button class="dh-cog-btn" @click=${() => { this._isSettingsOpen = true; }}>
          <ha-icon icon="mdi:cog"></ha-icon>
        </button>

        <div class="dh-frame" style="${frameStyle}">
          <div class="dh-frame-top-spacer"></div>
          <div class="dh-frame-aspect">
            <div class="dh-scene">
              <div class="dh-device">
                ${this._renderSceneContent()}
              </div>
            </div>
          </div>
          <div class="dh-frame-bottom-spacer"></div>
        </div>
      </ha-card>

      ${renderSettingsPanel(this, this._config)}
    `;
  }
}

if (!customElements.get('ha-smart-dehumidifier')) {
  customElements.define('ha-smart-dehumidifier', MyDehumidifierCard);
}

export { MyDehumidifierCard };