#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ─────────────────────────────────────────────────────────────
# ПАТЧ: КАМЕНЬ 4·ШАГ 2a — РУЛЬ ТЕСТЕРУ (on_progress + should_stop)
# Маркер: TESTER_HANDLES_V1
# Дата: 2026-06-20 · Брат (Claude) + Шеф
#
# ЗАЧЕМ. run_tester уже перебирает историю бар за баром и будит Совет
# (это твой готовый перебор). Но он печатает в консоль/файл и бежит до
# n_signals — его НЕ слышно в UI и НЕ прервать. Чтобы биржа (режим
# «тестер») могла лить его ход в чат и останавливать кнопкой СТОП,
# даём ему два руля — по образцу run_night_cycle:
#   on_progress(msg)  — callback: каждое событие перебора уходит наружу
#   should_stop()     — callback→bool: перед каждым кандидатом тестер
#                       спрашивает «стоп?» и, если да, выходит чисто
#                       (кран снимается в finally — состояние цело).
#
# Оба ОПЦИОНАЛЬНЫ (дефолт None) — консольный запуск
#   python -m studio.modules.trading.tester_express ...
# работает как раньше, ноль изменений в поведении.
#
# ОДНО КАСАНИЕ: tester_express.py
#   1. сигнатура run_tester += on_progress, should_stop
#   2. помощник _emit(msg) — печать + (если есть) on_progress
#   3. в начале цикла сита 2 — проверка should_stop() → чистый выход
#
# ИДЕМПОТЕНТНО: маркер, бэкап, py_compile. Запуск из корня репы:
#   python patch_tester_handles.py
# ─────────────────────────────────────────────────────────────

import sys
import shutil
import py_compile
from datetime import datetime
from pathlib import Path

MARKER = "TESTER_HANDLES_V1"
ROOT = Path.cwd()
TESTER = ROOT / "studio" / "modules" / "trading" / "tester_express.py"


def _fail(msg: str):
    print(f"❌ {msg}")
    sys.exit(1)


def _backup(path: Path):
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = path.with_name(f"{path.name}.bak_{stamp}")
    shutil.copy2(path, bak)
    print(f"   💾 бэкап: {bak.name}")


def _check_root():
    if not TESTER.exists():
        _fail(f"Не вижу {TESTER}. Запускай из КОРНЯ репы (где папка studio/).")


# ── 1. Сигнатура: добавляем on_progress, should_stop ──
SIG_ANCHOR = (
    "def run_tester(csv_path: str, symbol: str, timeframe: str,\n"
    "               n_signals: int = 1, point_override=None,\n"
    "               warmup: int = 60, loose: bool = False):\n"
)
SIG_INSERT = (
    "def run_tester(csv_path: str, symbol: str, timeframe: str,\n"
    "               n_signals: int = 1, point_override=None,\n"
    "               warmup: int = 60, loose: bool = False,\n"
    "               on_progress=None, should_stop=None):  # " + MARKER + "\n"
)

# ── 2. Помощник _emit рядом с out() — печать + наружу ──
# Якорь: первая строка тела после докстринга — импорт из williams_core.
EMIT_ANCHOR = (
    "    from studio.modules.trading.williams_core import read_mt5_csv, build_market_data\n"
    "    from studio.modules.trading import mt5_feed\n"
)
EMIT_INSERT = (
    "    from studio.modules.trading.williams_core import read_mt5_csv, build_market_data\n"
    "    from studio.modules.trading import mt5_feed\n"
    "\n"
    "    # РУЛЬ (биржа слушает ход / прерывает перебор).  # " + MARKER + "\n"
    "    def _emit(msg):\n"
    "        if on_progress:\n"
    "            try:\n"
    "                on_progress(msg)\n"
    "            except Exception:\n"
    "                pass\n"
    "    def _stop_requested():\n"
    "        if should_stop:\n"
    "            try:\n"
    "                return bool(should_stop())\n"
    "            except Exception:\n"
    "                return False\n"
    "        return False\n"
)

# ── 3. Проверка стопа в начале цикла сита 2 ──
LOOP_ANCHOR = (
    "        for idx, (i, side) in enumerate(candidates):\n"
    "            state[\"cursor\"] = i\n"
    "            scanned += 1\n"
)
LOOP_INSERT = (
    "        for idx, (i, side) in enumerate(candidates):\n"
    "            if _stop_requested():   # " + MARKER + ": кнопка СТОП биржи\n"
    "                out(f\"⏸ СТОП по команде Шефа — прошёл {scanned} из {len(candidates)} кандидатов.\")\n"
    "                break\n"
    "            state[\"cursor\"] = i\n"
    "            scanned += 1\n"
    "            _emit(f\"кандидат {idx+1}/{len(candidates)} · бар {i}\")\n"
)


def patch_tester() -> bool:
    src = TESTER.read_text(encoding="utf-8")
    if MARKER in src:
        print("✅ tester_express.py уже пропатчен — пропускаю.")
        return False

    if SIG_ANCHOR not in src:
        _fail("tester: не нашёл сигнатуру run_tester — структура изменилась.")
    src = src.replace(SIG_ANCHOR, SIG_INSERT, 1)

    if EMIT_ANCHOR not in src:
        _fail("tester: не нашёл импорт williams_core в теле — структура изменилась.")
    src = src.replace(EMIT_ANCHOR, EMIT_INSERT, 1)

    if LOOP_ANCHOR not in src:
        _fail("tester: не нашёл начало цикла сита 2 — структура изменилась.")
    src = src.replace(LOOP_ANCHOR, LOOP_INSERT, 1)

    _backup(TESTER)
    TESTER.write_text(src, encoding="utf-8")
    print("✅ tester_express.py пропатчен: on_progress + should_stop + _emit.")
    return True


def _verify_compiles():
    try:
        py_compile.compile(str(TESTER), doraise=True)
    except py_compile.PyCompileError as e:
        _fail(f"После патча tester_express.py НЕ компилируется:\n{e}")
    print("🧪 Песочница: tester_express.py компилируется.")


def main():
    print("═" * 62)
    print("  КАМЕНЬ 4·ШАГ 2a: РУЛЬ ТЕСТЕРУ  ·", MARKER)
    print("═" * 62)
    _check_root()

    if patch_tester():
        _verify_compiles()
        print("─" * 62)
        print("✅ ГОТОВО. У тестера руль: on_progress (ход наружу) + should_stop (СТОП).")
        print("   Консольный запуск не тронут — параметры опциональны.")
        print("   Дальше: тумблер тестер/реал + поле баров + СТОП на бирже (шаг 2b).")
    else:
        print("─" * 62)
        print("ℹ️  Уже было пропатчено ранее — ничего не менял.")


if __name__ == "__main__":
    main()
