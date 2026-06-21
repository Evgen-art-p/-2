#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ─────────────────────────────────────────────────────────────
# ПАТЧ: СОВЕТ СОБИРАЕТСЯ ПО СПУСКУ (факт), не по суждению Искры-LLM
# Маркер: COUNCIL_BY_DESCENT_V1
# Дата: 2026-06-21 · Брат (Claude) + Шеф
#
# БЕДА (Шеф): работает одна Искра, Совет молчит. А если сигнал
# отработал — должна быть полноценная сделка, весь Совет.
#
# КОРЕНЬ. Ворота тестера к Совету:
#     if t1_status not in ("DETECTED","CONFIRMED"): continue
# t1_status — суждение Искры-LLM. Спуск (механика _descend) находит
# точку (в логе «найдено=ДА»), кладёт факт в промт «ставь DETECTED»,
# но живая Искра судит СТРОЖЕ и часто оставляет NOT_FOUND. Ворота
# закрыты — Совет спит. Искра-часовой глушит круг ДО того, как все сели.
#
# ЗАКОН ШЕФА (его выбор): спуск нашёл точку = ФАКТ на столе = Совет
# собирается и решает САМ. Искра не решает за всех — она кричит «вижу!»,
# а судят все вместе. Код кладёт факты, Совет решает.
#
# РЕШЕНИЕ — ворота по СПУСКУ, не по настроению LLM:
#   1. iskra_live: run_iskra кладёт в return поле "descent"
#      {found, compass, zero_point, timeframe} — факт спуска наружу.
#      (t1_status остаётся — это ГОЛОС Искры, идёт в Совет как мнение,
#       но больше не глушит круг.)
#   2. tester: ворота = descent.found (факт), а не t1_status (суждение).
#      Нашёл спуск → весь Совет садится. Искра среди них, не вместо них.
#
# ДВА КАСАНИЯ. Идемпотентно, бэкап, py_compile. Из корня репы:
#   python patch_council_by_descent.py
# ─────────────────────────────────────────────────────────────

import sys
import shutil
import py_compile
from datetime import datetime
from pathlib import Path

MARKER = "COUNCIL_BY_DESCENT_V1"
ROOT = Path.cwd()
TRADING = ROOT / "studio" / "modules" / "trading"
ISKRA = TRADING / "iskra_live.py"
TESTER = TRADING / "tester_express.py"


def _fail(msg: str):
    print(f"❌ {msg}")
    sys.exit(1)


def _backup(path: Path):
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = path.with_name(f"{path.name}.bak_{stamp}")
    shutil.copy2(path, bak)
    print(f"   💾 бэкап: {bak.name}")


def _check_root():
    if not ISKRA.exists() or not TESTER.exists():
        _fail("Не вижу iskra_live.py / tester_express.py. Запускай из корня репы.")


# ── 1. Искра кладёт descent в return ──
ISKRA_OLD = '''        "raw": response,   # на случай если парсинг частичный — для отладки
    }'''
ISKRA_NEW = '''        "raw": response,   # на случай если парсинг частичный — для отладки
        "descent": md.get("v2_descent", {"found": False}),  # ''' + MARKER + ''' факт спуска
    }'''

# ── 2. Тестер: ворота по descent.found, не по t1_status ──
TESTER_OLD = '''            sig = r_iskra.get("signal", {})
            t1 = sig.get("t1_status", "NOT_FOUND")

            bd = bars_all[i].get("date", "?")
            # Искра живьём может отмести то, что ядро сочло кандидатом —
            # это нормально, она судит строже. Показываем коротко и идём.
            if t1 not in ("DETECTED", "CONFIRMED"):
                print(f"  кандидат {idx+1}/{len(candidates)} ({bd}, {side}): "
                      f"Искра живьём сказала {t1} — пропускаю")
                continue'''

TESTER_NEW = '''            sig = r_iskra.get("signal", {})
            t1 = sig.get("t1_status", "NOT_FOUND")

            bd = bars_all[i].get("date", "?")
            # ВОРОТА ПО СПУСКУ (закон Шефа): спуск нашёл точку = ФАКТ →  # ''' + MARKER + '''
            # Совет собирается и решает САМ. t1_status (суждение Искры-LLM)
            # больше не глушит круг — это её ГОЛОС, идёт в Совет как мнение.
            descent = r_iskra.get("descent", {}) or {}
            found = descent.get("found", False)
            if not found:
                print(f"  кандидат {idx+1}/{len(candidates)} ({bd}, {side}): "
                      f"спуск не нашёл точку (компас={descent.get('compass')}) — пропускаю")
                continue'''


def patch_iskra() -> bool:
    src = ISKRA.read_text(encoding="utf-8")
    if MARKER in src:
        print("✅ iskra_live.py уже пропатчен — пропускаю.")
        return False
    if ISKRA_OLD not in src:
        _fail("iskra: не нашёл финальный return run_iskra — структура изменилась.")
    src = src.replace(ISKRA_OLD, ISKRA_NEW, 1)
    _backup(ISKRA)
    ISKRA.write_text(src, encoding="utf-8")
    print("✅ iskra_live.py пропатчен: descent в return (факт спуска наружу).")
    return True


def patch_tester() -> bool:
    src = TESTER.read_text(encoding="utf-8")
    if MARKER in src:
        print("✅ tester_express.py уже пропатчен — пропускаю.")
        return False
    if TESTER_OLD not in src:
        _fail("tester: не нашёл ворота t1_status — структура изменилась.")
    src = src.replace(TESTER_OLD, TESTER_NEW, 1)
    _backup(TESTER)
    TESTER.write_text(src, encoding="utf-8")
    print("✅ tester_express.py пропатчен: ворота Совета по descent.found.")
    return True


def _verify_compiles():
    for p in (ISKRA, TESTER):
        try:
            py_compile.compile(str(p), doraise=True)
        except py_compile.PyCompileError as e:
            _fail(f"После патча {p.name} НЕ компилируется:\n{e}")
    print("🧪 Песочница: оба файла компилируются.")


def main():
    print("═" * 62)
    print("  СОВЕТ СОБИРАЕТСЯ ПО СПУСКУ  ·", MARKER)
    print("═" * 62)
    _check_root()
    changed = False
    changed |= patch_iskra()
    changed |= patch_tester()
    if changed:
        _verify_compiles()
        print("─" * 62)
        print("✅ ГОТОВО. Спуск нашёл точку → весь Совет садится и решает сам.")
        print("   Искра кричит «вижу!», судят все вместе. Полноценная сделка.")
    else:
        print("─" * 62)
        print("ℹ️  Уже было пропатчено ранее.")


if __name__ == "__main__":
    main()
