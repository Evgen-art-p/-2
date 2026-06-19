#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ─────────────────────────────────────────────────────────────
# ПАТЧ: patch_fix_direction.py
# Тихий баг в деньгах: рука открывающая теряла direction позиции
# Версия: 1.0 · 2026-06-19 · Брат (Claude) + Шеф
#
# БАГ. В hooks._persist_trading_state рука открывающая собирает позицию
# из execution_log, но НЕ переносит поле `direction`. А _settle_positions
# читает `pos.get("direction", "LONG")` — значит ЛЮБАЯ позиция без
# direction считается LONG. Результат: SHORT открывается, но закрывается
# по правилам LONG — стоп проверяется не с той стороны, а PnL считается
# зеркально НЕВЕРНО. Тихо, без ошибки, прямо в деньгах.
#
# ФИКС. Одна строка: переносим `direction` из ордера в позицию.
# Legacy-позиции (без direction) по-прежнему трактуются как LONG —
# их фоллбэк в _settle не трогаем.
#
# Идемпотентно, маркер + авто-бэкап. Запуск из КОРНЯ репы:
#   python patch_fix_direction.py
# ─────────────────────────────────────────────────────────────
import shutil, sys, py_compile
from datetime import datetime
from pathlib import Path

ROOT = Path.cwd()
HOOKS = ROOT / "studio" / "modules" / "trading" / "hooks.py"

OLD = ('        tstate["positions"].append({\n'
       '            "trader":    order.get("trader"),\n'
       '            "magic":     order.get("magic"),\n'
       '            "entry":     order.get("entry"),\n')

NEW = ('        tstate["positions"].append({\n'
       '            "trader":    order.get("trader"),\n'
       '            "magic":     order.get("magic"),\n'
       '            "direction": order.get("direction"),   # FIX: было потеряно — шорт закрывался как лонг\n'
       '            "entry":     order.get("entry"),\n')

MARKER = '"direction": order.get("direction")'

def main():
    print("─" * 60)
    print("ПАТЧ: фикс потери direction при открытии позиции")
    print("─" * 60)
    if not HOOKS.exists():
        print("✗ Не вижу studio/modules/trading/hooks.py — запусти из КОРНЯ репы.")
        sys.exit(1)
    src = HOOKS.read_text(encoding="utf-8")

    if MARKER in src:
        print("  ✓ direction уже переносится — фикс применён ранее.")
        return
    if OLD not in src:
        print("  ⚠️  не нашёл якорь руки открывающей (append позиции).")
        print("      Возможно, hooks.py изменился. Проверь _persist_trading_state вручную:")
        print("      в tstate['positions'].append добавь \"direction\": order.get(\"direction\").")
        sys.exit(1)
    if src.count(OLD) != 1:
        print(f"  ⚠️  якорь найден {src.count(OLD)} раз — ожидался 1. Останавливаюсь, проверь вручную.")
        sys.exit(1)

    b = HOOKS.with_suffix(".py.bak_" + datetime.now().strftime("%Y%m%d_%H%M%S"))
    shutil.copy2(HOOKS, b)
    print("  📦 бэкап:", b.relative_to(ROOT))

    HOOKS.write_text(src.replace(OLD, NEW, 1), encoding="utf-8")
    print("  ✍️  direction теперь переносится в позицию.")

    try:
        py_compile.compile(str(HOOKS), doraise=True)
        print("  ✓ hooks.py компилируется")
        print("\n✅ ГОТОВО. Шорты больше не считаются как лонги.")
        print("Заметь: позиции, открытые ДО фикса (если есть в trading_state.json),")
        print("останутся без direction → закроются как LONG. Новые — корректно.")
    except py_compile.PyCompileError as e:
        print("  ✗ ОШИБКА компиляции:", e)
        print("  ⚠️  откати из .bak и позови меня.")

if __name__ == "__main__":
    main()
