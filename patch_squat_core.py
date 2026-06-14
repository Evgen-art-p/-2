# -*- coding: utf-8 -*-
# patch_squat_core.py
# ─────────────────────────────────────────────────────────────
# ЗАКОН: вход по приседающему (Squat), не по фракталу.
# Этот патч добавляет в williams_core.py обнаружение приседающих
# баров по всему ряду и отдаёт last_squat в market_data.
#
# Канон (Вильямс, "Торговый Хаос", гл. 6):
#   Приседающий = +Тиковый Объём и −MFI (объём растёт, MFI падает).
#   "Все движения заканчиваются приседающим как самым высоким/низким
#    баром ±1 бар." → разворотный приседающий на экстремуме.
#   "Приседающий в середине 3-й волны = мерный (контрольный)" → НЕ вход.
#   Отсечение мерных: разворотный = приседающий в окне дивергенции AO
#   (Точка Ноль Искры). Без дивергенции приседающий мерный.
#   Вход = ПРОБОЙ приседающего: Buy Stop над high+тик / Sell Stop под low−тик.
#
# williams_core НЕ знает про агентов — только математику. Поэтому
# разворотность считается здесь через detect_ao_divergence (уже в core),
# а не через сигнал Искры (тот же факт, посчитанный кодом).
#
# Запуск: python patch_squat_core.py
# ─────────────────────────────────────────────────────────────

import re
import sys
import shutil
import py_compile
from datetime import datetime
from pathlib import Path

TARGET = Path("studio/modules/trading/williams_core.py")

# ── Новая функция: обнаружение приседающих по всему ряду ──────
SQUAT_FUNC = '''def detect_squat_bars(bars: list[dict], point: float = None) -> dict:
    """
    Приседающие бары (Squat) — окно Profitunity Вильямса (+Vol, −MFI).
    По "Торговому Хаосу", гл. 6: рынок присел перед рывком, готовясь
    прыгнуть в любую сторону. ВХОД — на ПРОБОЕ приседающего, не на нём.

    ЗАКОН ЯДРА: здесь только ФАКТ — где приседающие бары. Никакого
    суждения о том, разворотный приседающий или мерный. Это суждение
    выносят ТРЕЙДЕРЫ (A06/A07/A08), каждый своим порогом — для того
    их и трое. Ядро не имеет мнения. Дивергенция (Точка Ноль) уже
    отдаётся отдельным полем market_data — трейдеры сводят сами.

    Возвращает:
      last_squat — последний приседающий бар ряда (high/low/index/date)
      all        — все приседающие ряда
      count      — сколько всего
    """
    n = len(bars)
    squats = []

    for i in range(1, n):
        b  = bars[i]
        pb = bars[i - 1]
        if b["volume"] == 0 or pb["volume"] == 0:
            continue

        # MFI = (H−L)/_Point/Volume — формула BWMFI
        def _mfi(bar):
            v = (bar["high"] - bar["low"]) / bar["volume"]
            return v / point if point else v

        vol_up   = b["volume"] > pb["volume"]
        mfi_down = _mfi(b) < _mfi(pb)

        # Приседающий: объём вырос, MFI упал
        if vol_up and mfi_down:
            squats.append({
                "bar_index": i,
                "high":      round(b["high"], 6),
                "low":       round(b["low"], 6),
                "date":      b["date"],
            })

    return {
        "last_squat": squats[-1] if squats else None,
        "all":        squats,
        "count":      len(squats),
    }


'''

# ── Точка врезки функции: перед compute_mfi ──────────────────
ANCHOR_FUNC = 'def compute_mfi(bar: dict, prev_bar: dict, point: float = None) -> dict:'

# ── Вызов detect_squat_bars в build_market_data ──────────────
ANCHOR_CALL = '''    fractals   = detect_fractals(bars)
    _point     = get_point(symbol, point)'''
REPLACE_CALL = '''    fractals   = detect_fractals(bars)
    _point     = get_point(symbol, point)
    squat      = detect_squat_bars(bars, point=_point)'''

# ── Поле squat в return market_data: после fractals-блока ────
ANCHOR_FIELD = '''        "fractals": {
            "last_up":    fractals["last_up"],
            "last_down":  fractals["last_down"],
            "count_up":   fractals["count_up"],
            "count_down": fractals["count_down"],
        },
    }'''
REPLACE_FIELD = '''        "fractals": {
            "last_up":    fractals["last_up"],
            "last_down":  fractals["last_down"],
            "count_up":   fractals["count_up"],
            "count_down": fractals["count_down"],
        },

        "squat": {
            "last_squat": squat["last_squat"],
            "count":      squat["count"],
        },
    }'''


def main():
    if not TARGET.exists():
        print(f"[PATCH] ❌ Не найден: {TARGET}")
        print("        Запускай из корня репозитория (где studio/).")
        sys.exit(1)

    src = TARGET.read_text(encoding="utf-8")
    original = src

    # ── Бэкап ────────────────────────────────────────────────
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = TARGET.with_suffix(f".py.bak_{ts}")
    shutil.copy2(TARGET, bak)
    print(f"[PATCH] 💾 Бэкап: {bak.name}")

    # ── Идемпотентность ──────────────────────────────────────
    if "def detect_squat_bars" in src:
        print("[PATCH] ⚠️  detect_squat_bars уже есть — патч уже применён. Выход.")
        sys.exit(0)

    # ── 1. Вставка функции перед compute_mfi ─────────────────
    if ANCHOR_FUNC not in src:
        print("[PATCH] ❌ Якорь compute_mfi не найден. Структура файла изменилась.")
        sys.exit(1)
    src, n1 = re.subn(re.escape(ANCHOR_FUNC),
                      SQUAT_FUNC + ANCHOR_FUNC, src, count=1)
    print(f"[PATCH] ✏️  Функция detect_squat_bars вставлена: {n1}")

    # ── 2. Вызов в build_market_data ─────────────────────────
    if ANCHOR_CALL not in src:
        print("[PATCH] ❌ Якорь вызова (fractals/_point) не найден.")
        sys.exit(1)
    src, n2 = re.subn(re.escape(ANCHOR_CALL), REPLACE_CALL, src, count=1)
    print(f"[PATCH] ✏️  Вызов detect_squat_bars добавлен: {n2}")

    # ── 3. Поле squat в return ───────────────────────────────
    if ANCHOR_FIELD not in src:
        print("[PATCH] ❌ Якорь fractals-блока в return не найден.")
        sys.exit(1)
    src, n3 = re.subn(re.escape(ANCHOR_FIELD), REPLACE_FIELD, src, count=1)
    print(f"[PATCH] ✏️  Поле market_data['squat'] добавлено: {n3}")

    if not (n1 == n2 == n3 == 1):
        print("[PATCH] ❌ Не все замены прошли ровно один раз — откат.")
        sys.exit(1)

    # ── Запись и проверка компиляции ─────────────────────────
    TARGET.write_text(src, encoding="utf-8")
    try:
        py_compile.compile(str(TARGET), doraise=True)
        print("[PATCH] ✅ Компиляция прошла.")
    except py_compile.PyCompileError as e:
        print(f"[PATCH] ❌ Ошибка компиляции — откат:\n{e}")
        TARGET.write_text(original, encoding="utf-8")
        sys.exit(1)

    print("[PATCH] ✅ Готово. williams_core.py теперь отдаёт market_data['squat'].")
    print("        Следующий патч: hooks.py — вход по приседающему + SHORT-зеркало.")


if __name__ == "__main__":
    main()
