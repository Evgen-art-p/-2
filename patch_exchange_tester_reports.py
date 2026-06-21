#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ─────────────────────────────────────────────────────────────
# ПАТЧ: БИРЖА ПРИНИМАЕТ ОТЧЁТЫ ТЕСТЕРА (раскладка по аватарам)
# Маркер: EXCHANGE_TESTER_REPORTS_V1
# Дата: 2026-06-21 · Брат (Claude) + Шеф
#
# Пара к TESTER_REPORTS_V1. Тестер шлёт структурные отчёты агентов
# {"type":"report","agent":"A0X","narrative":...} через on_progress.
# Биржевой _on_progress сейчас просто print — учим его РАСКЛАДЫВАТЬ:
#   · отчёт (dict) → state["reports"][agent] = narrative,
#       active_agent = agent, метка в чат, обновить аватары+вид.
#       Точно как run_market в РЕАЛЕ — отчёт под аватаром агента.
#   · прогресс (str) → print (как было).
#
# Так в ТЕСТЕРЕ агенты пишут в СВОИ отчёты (клик по аватару A06 →
# отчёт Брута из прогона), а не в консоль. Реал и тестер выглядят
# одинаково — единая раскладка.
#
# ОДНО КАСАНИЕ: ui_exchange.py — тело _on_progress в run_tester_session.
# Идемпотентно, бэкап, py_compile. Запуск из корня репы:
#   python patch_exchange_tester_reports.py
# ─────────────────────────────────────────────────────────────

import sys
import shutil
import py_compile
from datetime import datetime
from pathlib import Path

MARKER = "EXCHANGE_TESTER_REPORTS_V1"
ROOT = Path.cwd()
EXCHANGE = ROOT / "studio" / "economy" / "ui_exchange.py"


def _fail(msg: str):
    print(f"❌ {msg}")
    sys.exit(1)


def _backup(path: Path):
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = path.with_name(f"{path.name}.bak_{stamp}")
    shutil.copy2(path, bak)
    print(f"   💾 бэкап: {bak.name}")


def _check_root():
    if not EXCHANGE.exists():
        _fail(f"Не вижу {EXCHANGE}. Запускай из КОРНЯ репы.")
    src = EXCHANGE.read_text(encoding="utf-8")
    if "EXCHANGE_TESTER_TOGGLE_V1" not in src:
        _fail("Нужен тумблер EXCHANGE_TESTER_TOGGLE_V1 — его нет.")


OLD = '''        def _on_progress(msg):
            # лёгкий репорт — не плодим тяжёлый UI на каждый бар
            print(f"[EXCHANGE·TESTER] {msg}")'''

NEW = '''        def _on_progress(msg):
            # СТРУКТУРНЫЙ отчёт агента (dict) → раскладываем по аватарам,  # ''' + MARKER + '''
            # как run_market в реале. Строка → лёгкий прогресс в консоль.
            if isinstance(msg, dict) and msg.get("type") == "report":
                aid = msg.get("agent")
                narrative = msg.get("narrative", "")
                if aid and narrative:
                    state["reports"][aid] = narrative
                    state["active_agent"] = aid
                    label = _agent_label(aid)
                    try:
                        update_viewer(f"# {label} ({aid})\\n\\n{narrative}")
                        update_avatar_states()
                    except Exception:
                        pass
                    # короткая метка в чат — голос в отчёте, не дубль
                    status = msg.get("status", "")
                    tail = f" · {status}" if status else ""
                    state["chat_history"].append({
                        "role": "assistant", "agent": aid,
                        "content": f"отработал{tail}. Отчёт справа."})
                    try:
                        update_chat_display()
                    except Exception:
                        pass
                return
            print(f"[EXCHANGE·TESTER] {msg}")'''


def patch_exchange() -> bool:
    src = EXCHANGE.read_text(encoding="utf-8")
    if MARKER in src:
        print("✅ ui_exchange.py уже пропатчен (tester-reports) — пропускаю.")
        return False
    if OLD not in src:
        _fail("exchange: не нашёл _on_progress тестера — структура изменилась.")
    src = src.replace(OLD, NEW, 1)
    _backup(EXCHANGE)
    EXCHANGE.write_text(src, encoding="utf-8")
    print("✅ ui_exchange.py пропатчен: _on_progress раскладывает отчёты по аватарам.")
    return True


def _verify_compiles():
    try:
        py_compile.compile(str(EXCHANGE), doraise=True)
    except py_compile.PyCompileError as e:
        _fail(f"После патча НЕ компилируется:\n{e}")
    print("🧪 Песочница: ui_exchange.py компилируется.")


def main():
    print("═" * 62)
    print("  БИРЖА ПРИНИМАЕТ ОТЧЁТЫ ТЕСТЕРА  ·", MARKER)
    print("═" * 62)
    _check_root()
    if patch_exchange():
        _verify_compiles()
        print("─" * 62)
        print("✅ ГОТОВО. В тестере агенты пишут в СВОИ отчёты под аватарами,")
        print("   не в консоль. Клик по A06 → отчёт Брута из прогона.")
        print("   Реал и тестер — единая раскладка.")
    else:
        print("─" * 62)
        print("ℹ️  Уже было пропатчено ранее.")


if __name__ == "__main__":
    main()
