#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ─────────────────────────────────────────────────────────────
# ПАТЧ: ТЕСТЕР ШЛЁТ ОТЧЁТЫ АГЕНТОВ (структурно, не в консоль)
# Маркер: TESTER_REPORTS_V1
# Дата: 2026-06-21 · Брат (Claude) + Шеф
#
# БЕДА (Шеф): «агенты запускаются с кабинета, но пишут в консоль».
# В РЕАЛЕ run_market кладёт голос каждого агента в state["reports"][id]
# → отчёт под его аватаром. В ТЕСТЕРЕ те же голоса идут в print/консоль
# и в reports НЕ попадают. Тестер — консольный, биржевого state не видит.
#
# РЕШЕНИЕ (путь Шефа А): тестер шлёт СТРУКТУРНЫЙ отчёт через уже
# существующий on_progress (TESTER_HANDLES_V1). После каждого агента —
# словарь {"type":"report","agent":"A0X","narrative":...,"status":...}.
# Биржа (отдельный патч) разложит его в reports[id] как run_market.
# Тестер остаётся независимым — лишь репортит факт наружу.
#
# ОДНО КАСАНИЕ: tester_express.py
#   1. помощник _emit_report(agent, narrative, status) рядом с _emit
#   2. после narrative КАЖДОГО из 9 агентов — вызов _emit_report
#      A01 Искра · A02 Морж · A03 Паникёр · A04 Ганс · A05 Архивариус
#      A06 Брут · A07 Авантюрист · A08 Консерватор · A09 Исполнитель
#
# print/out НЕ убираем — консоль остаётся как было (для отладки).
# Просто ДОБАВЛЯЕМ ветку наружу. Идемпотентно, бэкап, py_compile.
# Запуск из корня репы:  python patch_tester_reports.py
# ─────────────────────────────────────────────────────────────

import sys
import shutil
import py_compile
from datetime import datetime
from pathlib import Path

MARKER = "TESTER_REPORTS_V1"
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
        _fail(f"Не вижу {TESTER}. Запускай из КОРНЯ репы.")
    src = TESTER.read_text(encoding="utf-8")
    if "TESTER_HANDLES_V1" not in src:
        _fail("Нужен руль TESTER_HANDLES_V1 (on_progress) — его в файле нет.")


# ── помощник _emit_report рядом с _emit ──
# Якорь — конец блока _stop_requested (он идёт сразу за _emit).
HELPER_ANCHOR = (
    "    def _stop_requested():\n"
    "        if should_stop:\n"
    "            try:\n"
    "                return bool(should_stop())\n"
    "            except Exception:\n"
    "                return False\n"
    "        return False\n"
)
HELPER_INSERT = HELPER_ANCHOR + (
    "\n"
    "    def _emit_report(agent, narrative, status=\"\"):  # " + MARKER + "\n"
    "        \"\"\"Структурный отчёт агента наружу — биржа разложит по аватарам.\"\"\"\n"
    "        if on_progress and narrative:\n"
    "            try:\n"
    "                on_progress({\"type\": \"report\", \"agent\": agent,\n"
    "                             \"narrative\": str(narrative).strip(),\n"
    "                             \"status\": status})\n"
    "            except Exception:\n"
    "                pass\n"
)

# ── 9 врезок: после out(narrative) каждого агента ──
REPORTS = [
    # (якорь out-строки, что вставить после неё)
    (
        '            out(f"  ✴️ ИСКРА:\\n     {r_iskra.get(\'narrative\',\'\').strip()}")\n',
        '            _emit_report("A01", r_iskra.get("narrative", ""), t1)  # ' + MARKER + '\n',
    ),
    (
        '                out(f"  🦭 МОРЖ:\\n     {rm.get(\'narrative\',\'\').strip()}")\n',
        '                _emit_report("A02", rm.get("narrative", ""))  # ' + MARKER + '\n',
    ),
    (
        '                out(f"  😱 ПАНИКЁР:\\n     {rp.get(\'narrative\',\'\').strip()}")\n',
        '                _emit_report("A03", rp.get("narrative", ""))  # ' + MARKER + '\n',
    ),
    (
        '                out(f"  🎯 ГАНС:\\n     {rh.get(\'narrative\',\'\').strip()}")\n',
        '                _emit_report("A04", rh.get("narrative", ""))  # ' + MARKER + '\n',
    ),
    (
        '                out(f"  📚 АРХИВАРИУС:\\n     {ra.get(\'narrative\',\'\').strip()}")\n',
        '                _emit_report("A05", ra.get("narrative", ""))  # ' + MARKER + '\n',
    ),
    (
        '                out(f"  🪨 БРУТ:\\n     {rb.get(\'narrative\',\'\').strip()}")\n',
        '                _emit_report("A06", rb.get("narrative", ""))  # ' + MARKER + '\n',
    ),
    (
        '                out(f"  ⚡ АВАНТЮРИСТ:\\n     {rav.get(\'narrative\',\'\').strip()}")\n',
        '                _emit_report("A07", rav.get("narrative", ""))  # ' + MARKER + '\n',
    ),
    (
        '                out(f"  🛡 КОНСЕРВАТОР:\\n     {rco.get(\'narrative\',\'\').strip()}")\n',
        '                _emit_report("A08", rco.get("narrative", ""))  # ' + MARKER + '\n',
    ),
]

# Исполнитель — особый: у него narrative в signal.history_dna, а не в .narrative.
EXEC_ANCHOR = (
    '                out(f"  📋 ИСПОЛНИТЕЛЬ: ордеров "\n'
    '                    f"{fdna.get(\'orders_sent\',\'—\')} из 3 · "\n'
    '                    f"task_score {fdna.get(\'task_score\',\'—\')}")\n'
)
EXEC_INSERT = EXEC_ANCHOR + (
    '                _emit_report("A09",  # ' + MARKER + '\n'
    '                    esig.get("history_dna", "") or\n'
    '                    f"ордеров {fdna.get(\'orders_sent\',\'—\')} из 3")\n'
)


def patch_tester() -> bool:
    src = TESTER.read_text(encoding="utf-8")
    if MARKER in src:
        print("✅ tester_express.py уже пропатчен (reports) — пропускаю.")
        return False

    # helper
    if HELPER_ANCHOR not in src:
        _fail("tester: не нашёл _stop_requested — структура изменилась.")
    src = src.replace(HELPER_ANCHOR, HELPER_INSERT, 1)

    # 8 агентов
    for anchor, insert in REPORTS:
        if anchor not in src:
            _fail(f"tester: не нашёл якорь отчёта — структура изменилась:\n{anchor[:60]}")
        src = src.replace(anchor, anchor + insert, 1)

    # Исполнитель
    if EXEC_ANCHOR not in src:
        _fail("tester: не нашёл вывод Исполнителя — структура изменилась.")
    src = src.replace(EXEC_ANCHOR, EXEC_INSERT, 1)

    _backup(TESTER)
    TESTER.write_text(src, encoding="utf-8")
    print("✅ tester_express.py пропатчен: 9 структурных отчётов наружу.")
    return True


def _verify_compiles():
    try:
        py_compile.compile(str(TESTER), doraise=True)
    except py_compile.PyCompileError as e:
        _fail(f"После патча НЕ компилируется:\n{e}")
    print("🧪 Песочница: tester_express.py компилируется.")


def main():
    print("═" * 62)
    print("  ТЕСТЕР ШЛЁТ ОТЧЁТЫ АГЕНТОВ  ·", MARKER)
    print("═" * 62)
    _check_root()
    if patch_tester():
        _verify_compiles()
        print("─" * 62)
        print("✅ ГОТОВО. Тестер шлёт отчёты A01-A09 через on_progress.")
        print("   Консоль не тронута. Биржа разложит по аватарам (отд. патч).")
    else:
        print("─" * 62)
        print("ℹ️  Уже было пропатчено ранее.")


if __name__ == "__main__":
    main()
