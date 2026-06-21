#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ─────────────────────────────────────────────────────────────
# ПАТЧ: СБРОС СТОЛА на новый круг + смена аватара
# Маркер: EXCHANGE_ROUND_RESET_V1
# Дата: 2026-06-21 · Брат (Claude) + Шеф
#
# БЕДА (Шеф): первый круг прошёл (пузырьки переключались, отчёты легли,
# все позеленели). Второй круг — Искра засигналила снова, а стол ЗАНЯТ:
# пузырьки зелёные с прошлого, Исполнитель торчит активным, старые
# отчёты висят. Сброса между кругами нет — новое наслаивается.
#
# ЗАМЫСЕЛ (Шеф): «значимость прошлого сигнала снижается» — прошлый круг
# не убиваем, он уступает живому. Новый круг = чистый стол.
#
# ПРАВИЛО: приход отчёта A01 (Искра — ГОЛОВА круга, всегда первая) =
# начался НОВЫЙ круг → сбрасываем стол ПЕРЕД тем как положить её отчёт:
#   reports = {}        — старые отчёты гаснут
#   active_agent = None — сброс, потом встанет на Искру
#   update_avatar_states() — зелень пузырьков тухнет
# Остальные в круге (Морж…Исполнитель) ложатся на чистый стол.
#
# + ДОВОДКА: при КАЖДОМ отчёте зовём update_avatar() — большое лицо
# справа меняется вместе с пузырьком (раньше менялся только пузырёк).
#
# ОДНО КАСАНИЕ: ui_exchange.py — тело _on_progress (поверх
# EXCHANGE_TESTER_REPORTS_V1). Идемпотентно, бэкап, py_compile.
# Запуск из корня репы:  python patch_exchange_round_reset.py
# ─────────────────────────────────────────────────────────────

import sys
import shutil
import py_compile
from datetime import datetime
from pathlib import Path

MARKER = "EXCHANGE_ROUND_RESET_V1"
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
    if "EXCHANGE_TESTER_REPORTS_V1" not in src:
        _fail("Нужен приём отчётов EXCHANGE_TESTER_REPORTS_V1 — его нет.")


OLD = '''                if aid and narrative:
                    state["reports"][aid] = narrative
                    state["active_agent"] = aid
                    label = _agent_label(aid)
                    try:
                        update_viewer(f"# {label} ({aid})\\n\\n{narrative}")
                        update_avatar_states()
                    except Exception:
                        pass'''

NEW = '''                if aid and narrative:
                    # НОВЫЙ КРУГ: Искра (A01) — голова цепочки. Её приход =  # ''' + MARKER + '''
                    # начался новый круг → стол чистим, прошлый сигнал
                    # теряет значимость (не убит — уступил живому).
                    if aid == "A01":
                        state["reports"] = {}
                        state["active_agent"] = None
                        try:
                            update_avatar_states()
                        except Exception:
                            pass
                    state["reports"][aid] = narrative
                    state["active_agent"] = aid
                    label = _agent_label(aid)
                    try:
                        update_viewer(f"# {label} ({aid})\\n\\n{narrative}")
                        update_avatar()          # ''' + MARKER + ''': большое лицо ↔ пузырёк
                        update_avatar_states()
                    except Exception:
                        pass'''


def patch_exchange() -> bool:
    src = EXCHANGE.read_text(encoding="utf-8")
    if MARKER in src:
        print("✅ ui_exchange.py уже пропатчен (round-reset) — пропускаю.")
        return False
    if OLD not in src:
        _fail("exchange: не нашёл тело _on_progress (reports) — структура изменилась.")
    src = src.replace(OLD, NEW, 1)
    _backup(EXCHANGE)
    EXCHANGE.write_text(src, encoding="utf-8")
    print("✅ ui_exchange.py пропатчен: сброс на A01 + смена аватара.")
    return True


def _verify_compiles():
    try:
        py_compile.compile(str(EXCHANGE), doraise=True)
    except py_compile.PyCompileError as e:
        _fail(f"После патча НЕ компилируется:\n{e}")
    print("🧪 Песочница: ui_exchange.py компилируется.")


def main():
    print("═" * 62)
    print("  СБРОС СТОЛА на новый круг + смена аватара  ·", MARKER)
    print("═" * 62)
    _check_root()
    if patch_exchange():
        _verify_compiles()
        print("─" * 62)
        print("✅ ГОТОВО. Искра (A01) сигналит заново → стол чистится:")
        print("   старые отчёты гаснут, пузырьки тухнут, аватар на текущем.")
        print("   Большое лицо меняется вместе с пузырьком каждый отчёт.")
    else:
        print("─" * 62)
        print("ℹ️  Уже было пропатчено ранее.")


if __name__ == "__main__":
    main()
