// Мова картки/редактора. За замовчуванням - українська (весь наявний
// текст у коді вже українською), тож переклад працює як "словник
// заміни": ключ - оригінальний український рядок, значення - його
// англійський відповідник. Це дозволяє додати мову БЕЗ переписування
// самих компонентів (settings-panel.js, visual-editor-config.js) під
// систему i18n-ключів - рядки лишаються як є, змінюється лише те, що
// показується.
export const DEFAULT_LANGUAGE = 'uk';

export const LANGUAGES = [
  { value: 'uk', label: 'Українська' },
  { value: 'en', label: 'English' },
];

export function getLanguage(config = {}) {
  return config?.language === 'en' ? 'en' : DEFAULT_LANGUAGE;
}

const EN = {
  // --- Спливаюче вікно (шестерня на картці) ---
  'Налаштування': 'Settings',
  'Авто-режим': 'Auto mode',
  'Рекомендація': 'Recommendation',
  'розраховано автоматично': 'calculated automatically',
  'Дельта': 'Delta',
  ' (абс. вологість)': ' (abs. humidity)',
  'Min ліміт': 'Min limit',
  'Max ліміт': 'Max limit',
  'Таймери': 'Timers',
  'Ручний режим': 'Manual mode',
  ' хв': ' min',
  'Пауза': 'Pause',
  'Мова': 'Language',

  // --- Візуальний редактор: заголовки вкладок ---
  'Сутності': 'Entities',
  'Розкладка': 'Layout',
  'Дуга та повзунок': 'Arc & handle',
  'Автовологість': 'Auto humidity',
  'Поточна вологість': 'Current humidity',
  'Панель цільової вологості': 'Target humidity panel',
  'Нижні кнопки': 'Bottom buttons',
  'Візуальні ефекти': 'Visual effects',

  // --- Візуальний редактор: службовий текст ---
  'Скинути до стандартного': 'Reset to default',
  'Автоматична вологість недоступна: у налаштуваннях пристрою (Settings → Devices & services → HA Smart Dehumidifier) не вказано датчик вологості сусідньої кімнати. Без нього осушувач працює лише за вручну заданою цільовою вологістю та гістерезисом.':
    'Auto humidity is unavailable: the device settings (Settings → Devices & services → HA Smart Dehumidifier) don\u2019t have a neighboring-room humidity sensor configured. Without it, the dehumidifier only works off a manually set target humidity and hysteresis.',

  // --- Сутності ---
  'Пристрій (HA Smart Dehumidifier)': 'Device (HA Smart Dehumidifier)',

  // --- Розкладка ---
  'Заокруглення картки': 'Card corner radius',
  'Висота картки на телефоні (%)': 'Card height on phone (%)',
  'Пропорція скла на ПК (Шир/Вис)': 'Glass ratio on PC (W/H)',
  'Макс. ширина ПРИЛАДУ': 'Max. DEVICE width',
  'Вирівнювання осушувача': 'Dehumidifier alignment',
  'Відступ зверху': 'Top padding',
  'Відступ знизу': 'Bottom padding',
  'Відступ ліворуч': 'Left padding',
  'Відступ праворуч': 'Right padding',
  'Зсув приладу по X': 'Device shift X',
  'Зсув приладу по Y': 'Device shift Y',
  'Макс. ширина нижніх блоків': 'Max. width of bottom blocks',
  'Ліворуч': 'Left',
  'По центру': 'Center',
  'Праворуч': 'Right',

  // --- Дуга та повзунок ---
  'Показати дугу': 'Show arc',
  'Початок дуги': 'Arc start',
  'Довжина дуги': 'Arc length',
  'Радіус дуги': 'Arc radius',
  'Товщина фону': 'Background thickness',
  'Товщина поточної': 'Current thickness',
  'Товщина цілі': 'Target thickness',
  'Світіння дуги': 'Arc glow',
  'Радіус повзунка': 'Handle radius',
  'Зона дотику повзунка': 'Handle touch area',
  'Світіння повзунка': 'Handle glow',

  // --- Автовологість ---
  'Показати Auto UI': 'Show Auto UI',
  'Іконка панелі Auto': 'Auto panel icon',
  'Текст панелі Auto': 'Auto panel text',
  'Auto панель — зміщення X': 'Auto panel — X offset',
  'Auto панель — позиція Y': 'Auto panel — Y position',
  'Auto панель — ширина': 'Auto panel — width',
  'Auto панель — висота': 'Auto panel — height',
  'Auto панель — заокруглення': 'Auto panel — corner radius',
  'Auto панель — внутрішній відступ X': 'Auto panel — inner padding X',
  'Auto панель — відстань між елементами': 'Auto panel — gap between items',
  'Auto панель — розмір іконки': 'Auto panel — icon size',
  'Auto панель — розмір тексту': 'Auto panel — text size',
  'Auto панель — розмір вологості': 'Auto panel — humidity size',
  'Язичок — зміщення X': 'Tab — X offset',
  'Язичок — позиція Y': 'Tab — Y position',
  'Язичок — ширина': 'Tab — width',
  'Язичок — висота': 'Tab — height',
  'Язичок — розмір іконки': 'Tab — icon size',
  'Язичок — заокруглення': 'Tab — corner radius',

  // --- Поточна вологість ---
  'Показати вологість': 'Show humidity',
  'Макс. ширина тексту': 'Max. text width',
  'Жирність цифр': 'Digit weight',
  'Відстань між числами': 'Gap between numbers',
  'Положення по вертикалі Y': 'Vertical position Y',
  'Розмір цілої': 'Integer part size',
  'Інтервал цифр': 'Digit spacing',
  'Показувати десяткову': 'Show decimal',
  'Розмір десяткової': 'Decimal size',
  'Показувати %': 'Show %',
  'Розмір %': '% size',
  'Жирність %': '% weight',
  'Відступ %': '% margin',

  // --- Панель цільової вологості ---
  'Показати панель': 'Show panel',
  'Ширина панелі (%)': 'Panel width (%)',
  'Макс. ширина панелі (px)': 'Max. panel width (px)',
  'Висота панелі': 'Panel height',
  'Заокруглення панелі': 'Panel corner radius',
  'Внутрішній відступ X': 'Inner padding X',
  'Ширина дисплея': 'Display width',
  'Висота дисплея': 'Display height',
  'Заокруглення дисплея': 'Display corner radius',
  'Діаметр кнопок ±': '± button diameter',
  'Розмір іконок ±': '± icon size',

  // --- Нижні кнопки ---
  'Показати кнопки': 'Show buttons',
  'Висота кнопок': 'Button height',
  'Розмір іконок': 'Icon size',
  'Розмір підписів': 'Label size',
  'Розмір таймера вентилятора': 'Fan timer size',
  'Показати бейдж статусу': 'Show status badge',
  'Ширина бейджа (%)': 'Badge width (%)',
  'Висота бейджа': 'Badge height',
  'Заокруглення бейджа': 'Badge corner radius',
  'Розмір тексту бейджа': 'Badge text size',
  'Жирність тексту бейджа': 'Badge text weight',
  'Положення бейджа по вертикалі Y': 'Badge vertical position Y',
  'Положення блоку по вертикалі Y': 'Block vertical position Y',
  'Підпис OFF': 'OFF label',
  'Іконка OFF': 'OFF icon',
  'Підпис ON': 'ON label',
  'Іконка ON': 'ON icon',
  'Підпис MANUAL': 'MANUAL label',
  'Іконка MANUAL': 'MANUAL icon',

  // --- Візуальні ефекти ---
  'Увімкнути фоновий вентилятор': 'Enable background fan',
  'Розмір вентилятора': 'Fan size',
  'Прозорість вентилятора (%)': 'Fan opacity (%)',
  'Швидкість вентилятора (1-100)': 'Fan speed (1-100)',
  'Увімкнути комету (орбіту)': 'Enable comet (orbit)',
  'Розмір орбіти': 'Orbit size',
  'Швидкість комети (1-100)': 'Comet speed (1-100)',
  'Увімкнути частинки': 'Enable particles',
  'Кількість частинок': 'Particle count',
  'Радіус розлітання частинок': 'Particle spread radius',
  'Швидкість частинок (1-100)': 'Particle speed (1-100)',
};

// t(config, 'Український текст') -> переклад, якщо мова картки - 'en',
// інакше повертає той самий рядок без змін (українська - за замовчуванням).
export function t(config, ukText) {
  if (getLanguage(config) !== 'en') return ukText;
  return EN[ukText] ?? ukText;
}
