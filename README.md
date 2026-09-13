# HA Smart Dehumidifier

Повноцінна Home Assistant інтеграція для керування осушувачем ванної кімнати
(звичайний вентилятор через розумний вимикач) з візуальною карткою для Lovelace.

Раніше це була лише картка + 5 допоміжних об'єктів + 4 автоматизації + 1 скрипт.
Тепер уся ця логіка живе всередині інтеграції — жодних ручних helper'ів чи
автоматизацій створювати не потрібно.

## Встановлення через HACS

1. HACS → Custom repositories → додати цей репозиторій (тип: Integration).
2. Встановити "HA Smart Dehumidifier", перезапустити Home Assistant.
3. Settings → Devices & services → Add integration → **HA Smart Dehumidifier**.
4. Вказати:
   - **Вимикач вентилятора** — реальний `switch`, який фізично вмикає вентилятор.
   - **Датчик вологості** у кімнаті з осушувачем.
   - **Датчик абсолютної вологості** сусідньої кімнати (наприклад, сенсор
     інтеграції Thermal Comfort).
   - **Датчик температури** тієї ж сусідньої кімнати.
5. Після додавання інтеграція створить: `humidifier.*`, `switch.*_auto_mode`,
   `button.*_manual_toggle`, `sensor.*_status`, `sensor.*_recommended_humidity`.

Картка `ha-smart-dehumidifier` реєструється автоматично — додавати ресурс
Lovelace вручну не потрібно.

## Налаштування розрахунку (Settings → Options)

| Параметр | Значення за замовчуванням | Було |
|---|---|---|
| Дельта абс. вологості | 0.5 | `input_number.dh_delta` |
| Мін. рекомендована вологість | 30% | `input_number.dh_auto_min` |
| Макс. рекомендована вологість | 80% | `input_number.dh_auto_max` |
| Гістерезис | 3% | — (новий параметр, замінює логіку Generic Hygrostat) |
| Тривалість ручного режиму | 20 хв | `input_number.dh_manual_runtime` |
| Пауза після ручного режиму | 20 хв | `input_number.dh_manual_pause_runtime` |

> ⚠️ Значення дельти, гістерезису та обох таймаутів виставлені як розумні
> дефолти — я не мав доступу до твоїх реальних збережених значень
> `input_number`. Перевір і підправ їх у Options одразу після встановлення.

## Приклад картки

```yaml
type: custom:ha-smart-dehumidifier
entity: humidifier.vanna
fan_entity: switch.unknown_right
auto_entity: switch.vanna_auto_mode
status_entity: sensor.vanna_status
calc_entity: sensor.vanna_recommended_humidity
manual_script_entity: button.vanna_manual_toggle
current_humidity_entity: sensor.temperatura_vologist_aaa_humidity
```

Заміни `vanna` на entity_id, які реально створила твоя інтеграція
(Developer tools → States). Усі візуальні налаштування (розкладка, дуга,
кольори, ефекти, шрифт 7-segment тощо) — редагуються через візуальний
редактор картки так само, як і раніше.
