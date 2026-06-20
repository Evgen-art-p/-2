#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ─────────────────────────────────────────────────────────────
# ПАТЧ: КОМПАС ИЗ СИНЕЙ ЛИНИИ (global_bias)
# Маркер: GLOBAL_BIAS_COMPASS_V1
# Дата: 2026-06-20 · Автор: Брат (Claude) + Шеф
#
# ЗАЧЕМ. Брут пасует «нет якоря», когда нет дивера-компаса Искры.
# На тестере (один CSV) дивер-компас редок, спуск по лесенке слеп —
# Брут почти всегда без направления глобального тренда.
#
# РЕШЕНИЕ (канон, не костыль). Три линии Аллигатора — три баланса
# (справедливые цены) на трёх горизонтах памяти. Синяя (Jaw, SMMA-13) —
# самый медленный, инертный баланс = дыхание старшего ТФ внутри рабочего
# окна. Цена относительно синей + наклон синей = глобальный фон.
# Это ВСЕГДА на столе, считается из той же математики, без терминала.
#
# ТРИ КАСАНИЯ (ни одно не рушит линзы агентов):
#  1. ЯДРО (williams_core.build_market_data) — рожает факт global_bias.
#     Ядро мерит, агенты читают (как divergence_ao, rubber_band).
#  2. ИСКРА (iskra_live._save_iskra_memory) — фоллбэк: если дивер-компас
#     дал trend_direction=None, берём global_bias. Дивер приоритетен.
#  3. БРУТ (brut_live.run_brut) — страховка: если global_trend из памяти
#     Искры пуст, читает global_bias прямо из market_data.
#
# Искра НЕ начинает «читать Аллигатор» — она получает готовый факт ядра,
# как получает дивергенцию. Линза не нарушена.
#
# ИДЕМПОТЕНТНО: маркер-проверка, авто-бэкап, проверка в песочнице (py_compile).
# Запуск из корня репы:  python patch_global_bias_compass.py
# ─────────────────────────────────────────────────────────────

import re
import sys
import shutil
import py_compile
from datetime import datetime
from pathlib import Path

MARKER = "GLOBAL_BIAS_COMPASS_V1"
ROOT = Path.cwd()
TRADING = ROOT / "studio" / "modules" / "trading"

CORE  = TRADING / "williams_core.py"
ISKRA = TRADING / "iskra_live.py"
BRUT  = TRADING / "brut_live.py"


def _fail(msg: str):
    print(f"❌ {msg}")
    sys.exit(1)


def _backup(path: Path) -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = path.with_name(f"{path.name}.bak_{stamp}")
    shutil.copy2(path, bak)
    print(f"   💾 бэкап: {bak.name}")
    return bak


def _check_root():
    if not TRADING.exists():
        _fail(f"Не вижу {TRADING}. Запускай из КОРНЯ репы (где папка studio/).")
    for p in (CORE, ISKRA, BRUT):
        if not p.exists():
            _fail(f"Не найден файл: {p}")


# ════════════════════════════════════════════════════════════
# КАСАНИЕ 1 — ЯДРО: рождаем global_bias
# ════════════════════════════════════════════════════════════

# Функция-вычислитель компаса. Вставляется ПЕРЕД build_market_data.
CORE_FUNC = '''
def compute_global_bias(bars: list, alligator: dict, point: float,
                        slope_lookback: int = 5) -> str:
    """
    КОМПАС ГЛОБАЛЬНОГО ФОНА из синей линии Аллигатора (Jaw, SMMA-13).  # GLOBAL_BIAS_COMPASS_V1

    Три линии Аллигатора — три баланса (справедливые цены) на трёх
    горизонтах памяти. Синяя самая медленная и инертная: дыхание
    старшего ТФ внутри рабочего окна. Берём ЦЕНУ относительно синей
    плюс НАКЛОН синей — грубый, но всегда живой компас, переживающий
    развороты (в отличие от строгого веера, схлопывающегося в NONE
    ровно на развороте, когда компас нужнее всего).

    ЗАКОН ЯДРА: только ФАКТ направления фона. Не суждение, не команда.
    Трейдеры читают и сводят сами.

      BULL: close выше Jaw И Jaw не падает (наклон >= 0)
      BEAR: close ниже Jaw И Jaw не растёт (наклон <= 0)
      NONE: цена и наклон спорят (переходная зона) ИЛИ синей нет

    Возвращает "BULL" / "BEAR" / "NONE".
    """
    jaw = alligator.get("jaw")
    if jaw is None or not bars:
        return "NONE"

    close = bars[-1]["close"]

    # Наклон синей: сравниваем текущую Jaw с Jaw slope_lookback баров назад.
    # Пересчёт лёгкий — SMMA(13) по медианам всего окна, берём срез.
    medians = [(b["high"] + b["low"]) / 2 for b in bars]
    jaw_series = _smma_series(medians, 13)
    jaw_prev = None
    if len(jaw_series) > slope_lookback:
        cand = jaw_series[-1 - slope_lookback]
        if cand is not None:
            jaw_prev = cand

    slope = 0.0
    if jaw_prev is not None:
        slope = jaw - jaw_prev

    # Безразмерный порог наклона: шум в пределах ~5 пунктов считаем плоским.
    flat = (5 * point) if point else 0.0

    price_above = close > jaw
    price_below = close < jaw
    rising  = slope >  flat
    falling = slope < -flat

    if price_above and not falling:
        return "BULL"
    if price_below and not rising:
        return "BEAR"
    return "NONE"


'''

# Точка вставки функции — прямо перед определением build_market_data.
CORE_ANCHOR_FUNC = "def build_market_data("

# Вычисление внутри build_market_data — после wave_form, перед print _Point.
CORE_ANCHOR_CALL = (
    "    wave_form = read_ao_wave_form(bars, ao_series, teeth_series)\n"
)
CORE_INSERT_CALL = (
    "    wave_form = read_ao_wave_form(bars, ao_series, teeth_series)\n"
    "\n"
    "    # Компас глобального фона из синей линии (Jaw).  # GLOBAL_BIAS_COMPASS_V1\n"
    "    # Факт направления, всегда на столе (не зависит от дивера/терминала).\n"
    "    global_bias = compute_global_bias(bars, alligator, _point)\n"
)

# Добавление поля в возвращаемый словарь — рядом с wave_form.
CORE_ANCHOR_RET = (
    '        "wave_form":     wave_form,            # факты формы AO (глаз Искры v2)\n'
)
CORE_INSERT_RET = (
    '        "wave_form":     wave_form,            # факты формы AO (глаз Искры v2)\n'
    '        "global_bias":   global_bias,          # компас фона из синей (GLOBAL_BIAS_COMPASS_V1)\n'
)


def patch_core() -> bool:
    src = CORE.read_text(encoding="utf-8")
    if MARKER in src:
        print("✅ ЯДРО уже пропатчено — пропускаю.")
        return False

    # 1) вставить функцию перед build_market_data
    if CORE_ANCHOR_FUNC not in src:
        _fail("ЯДРО: не нашёл якорь 'def build_market_data(' — структура изменилась.")
    src = src.replace(CORE_ANCHOR_FUNC, CORE_FUNC.lstrip("\n") + "\n" + CORE_ANCHOR_FUNC, 1)

    # 2) вставить вычисление после wave_form
    if CORE_ANCHOR_CALL not in src:
        _fail("ЯДРО: не нашёл якорь вызова wave_form — структура изменилась.")
    src = src.replace(CORE_ANCHOR_CALL, CORE_INSERT_CALL, 1)

    # 3) добавить поле в словарь
    if CORE_ANCHOR_RET not in src:
        _fail("ЯДРО: не нашёл якорь поля wave_form в return — структура изменилась.")
    src = src.replace(CORE_ANCHOR_RET, CORE_INSERT_RET, 1)

    _backup(CORE)
    CORE.write_text(src, encoding="utf-8")
    print("✅ ЯДРО пропатчено: compute_global_bias + поле global_bias.")
    return True


# ════════════════════════════════════════════════════════════
# КАСАНИЕ 2 — ИСКРА: фоллбэк trend_direction на global_bias
# ════════════════════════════════════════════════════════════

# Меняем сигнатуру _save_iskra_memory, чтобы принять md.
ISKRA_ANCHOR_SIG = "def _save_iskra_memory(signal: dict):"
ISKRA_INSERT_SIG = "def _save_iskra_memory(signal: dict, md: dict = None):  # GLOBAL_BIAS_COMPASS_V1"

# Меняем запись trend_direction: добавляем фоллбэк на global_bias.
ISKRA_ANCHOR_TREND = (
    '    tstate["iskra"]["trend_direction"] = (\n'
    '        signal.get("trend_direction") or signal.get("compass")\n'
    '    )\n'
)
ISKRA_INSERT_TREND = (
    '    # КОМПАС: приоритет — дивер-компас Искры (trend_direction/compass).  # GLOBAL_BIAS_COMPASS_V1\n'
    '    # Фоллбэк — global_bias из синей линии (всегда на столе), если дивер молчит.\n'
    '    _td = signal.get("trend_direction") or signal.get("compass")\n'
    '    if not _td and md:\n'
    '        _gb = md.get("global_bias")\n'
    '        if _gb in ("BULL", "BEAR"):\n'
    '            _td = _gb\n'
    '    tstate["iskra"]["trend_direction"] = _td\n'
)

# Точка вызова _save_iskra_memory(signal) в run_iskra — прокидываем md.
ISKRA_ANCHOR_CALL = "    _save_iskra_memory(signal)\n"
ISKRA_INSERT_CALL = "    _save_iskra_memory(signal, md)   # GLOBAL_BIAS_COMPASS_V1: фоллбэк компаса\n"


def patch_iskra() -> bool:
    src = ISKRA.read_text(encoding="utf-8")
    if MARKER in src:
        print("✅ ИСКРА уже пропатчена — пропускаю.")
        return False

    if ISKRA_ANCHOR_SIG not in src:
        _fail("ИСКРА: не нашёл сигнатуру _save_iskra_memory — структура изменилась.")
    src = src.replace(ISKRA_ANCHOR_SIG, ISKRA_INSERT_SIG, 1)

    if ISKRA_ANCHOR_TREND not in src:
        _fail("ИСКРА: не нашёл блок записи trend_direction — структура изменилась.")
    src = src.replace(ISKRA_ANCHOR_TREND, ISKRA_INSERT_TREND, 1)

    if ISKRA_ANCHOR_CALL not in src:
        _fail("ИСКРА: не нашёл вызов _save_iskra_memory(signal) — структура изменилась.")
    src = src.replace(ISKRA_ANCHOR_CALL, ISKRA_INSERT_CALL, 1)

    _backup(ISKRA)
    ISKRA.write_text(src, encoding="utf-8")
    print("✅ ИСКРА пропатчена: фоллбэк trend_direction → global_bias.")
    return True


# ════════════════════════════════════════════════════════════
# КАСАНИЕ 3 — БРУТ: страховка global_trend из market_data
# ════════════════════════════════════════════════════════════

BRUT_ANCHOR = (
    '            "global_trend": table.get("iskra", {}).get("trend_direction"),\n'
)
BRUT_INSERT = (
    '            # КОМПАС: память Искры приоритетна; если пуста —  # GLOBAL_BIAS_COMPASS_V1\n'
    '            # страховка прямо из market_data (синяя линия всегда на столе).\n'
    '            "global_trend": (table.get("iskra", {}).get("trend_direction")\n'
    '                             or (md.get("global_bias")\n'
    '                                 if md.get("global_bias") in ("BULL", "BEAR")\n'
    '                                 else None)),\n'
)


def patch_brut() -> bool:
    src = BRUT.read_text(encoding="utf-8")
    if MARKER in src:
        print("✅ БРУТ уже пропатчен — пропускаю.")
        return False

    if BRUT_ANCHOR not in src:
        _fail("БРУТ: не нашёл строку global_trend в table_for_brut — структура изменилась.")
    src = src.replace(BRUT_ANCHOR, BRUT_INSERT, 1)

    _backup(BRUT)
    BRUT.write_text(src, encoding="utf-8")
    print("✅ БРУТ пропатчен: страховка global_trend → md.global_bias.")
    return True


# ════════════════════════════════════════════════════════════
# ПЕСОЧНИЦА — компиляция перед тем как считать патч успешным
# ════════════════════════════════════════════════════════════

def _verify_compiles():
    for p in (CORE, ISKRA, BRUT):
        try:
            py_compile.compile(str(p), doraise=True)
        except py_compile.PyCompileError as e:
            _fail(f"После патча {p.name} НЕ компилируется:\n{e}")
    print("🧪 Песочница: все три файла компилируются.")


def main():
    print("═" * 60)
    print("  ПАТЧ: КОМПАС ИЗ СИНЕЙ ЛИНИИ (global_bias)  ·", MARKER)
    print("═" * 60)
    _check_root()

    changed = False
    changed |= patch_core()
    changed |= patch_iskra()
    changed |= patch_brut()

    if changed:
        _verify_compiles()
        print("─" * 60)
        print("✅ ГОТОВО. Компас из синей линии на столе у всех.")
        print("   Проверка: python -m studio.modules.trading.tester_express \\")
        print("             test_data/XAUUSD_H4.csv XAUUSD H4 --signals 1")
        print("   Брут больше не пасует «нет якоря» — фон всегда есть.")
    else:
        print("─" * 60)
        print("ℹ️  Всё уже было пропатчено ранее — ничего не менял.")


if __name__ == "__main__":
    main()
