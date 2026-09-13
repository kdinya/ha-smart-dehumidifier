"""Перерахунок відносної вологості (%) <-> абсолютної вологості (г/м3).

Формула Magnus-Tetens для тиску насиченої водяної пари, застосовна в
звичайному побутовому діапазоні температур (-40..+50 C):

    Ps(T) = 6.112 * exp((17.62 * T) / (243.12 + T))   [гПа]
    Pv     = RH / 100 * Ps(T)                          [гПа]
    AH     = 216.7 * Pv / (T + 273.15)                 [г/м3]

Порівнювати вологість різних кімнат напряму у відсотках некоректно -
однакова відносна вологість при різній температурі відповідає різній
кількості води в повітрі. Тому для порівняння між кімнатами
використовується абсолютна вологість (г/м3): вона не залежить від
температури і відображає реальний вміст вологи в повітрі. Користувачу
при цьому завжди показується відносна вологість (%) - або взята
напряму з датчика, або перерахована за цією ж формулою.
"""
from __future__ import annotations

import math

MIN_TEMP_C = -40.0
MAX_TEMP_C = 60.0


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def saturation_vapor_pressure(temp_c: float) -> float:
    """Тиск насиченої водяної пари при заданій температурі, гПа."""
    t = _clamp(temp_c, MIN_TEMP_C, MAX_TEMP_C)
    return 6.112 * math.exp((17.62 * t) / (243.12 + t))


def absolute_humidity(rh_percent: float, temp_c: float) -> float | None:
    """Відносна вологість (%) + температура (C) -> абсолютна вологість, г/м3."""
    if rh_percent is None or temp_c is None:
        return None
    rh = _clamp(rh_percent, 0.0, 100.0)
    t = _clamp(temp_c, MIN_TEMP_C, MAX_TEMP_C)

    ps = saturation_vapor_pressure(t)
    pv = (rh / 100.0) * ps
    return 216.7 * pv / (t + 273.15)


def relative_humidity_from_absolute(abs_humidity_g_m3: float, temp_c: float) -> float | None:
    """Абсолютна вологість (г/м3) + температура (C) -> відносна вологість, %.

    Обернена до absolute_humidity(): скільки відсотків відносної вологості
    відповідає заданій кількості води в повітрі (г/м3) при заданій
    температурі. Результат затиснутий у фізичних межах 0-100%.
    """
    if abs_humidity_g_m3 is None or temp_c is None:
        return None
    t = _clamp(temp_c, MIN_TEMP_C, MAX_TEMP_C)

    ps = saturation_vapor_pressure(t)
    if ps <= 0:
        return None

    pv = abs_humidity_g_m3 * (t + 273.15) / 216.7
    rh = (pv / ps) * 100.0
    return _clamp(rh, 0.0, 100.0)
