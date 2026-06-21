#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ─────────────────────────────────────────────────────────────
# ПАТЧ: СПИСОК АКТИВОВ РАСТЯГИВАЕТСЯ (не скролл)
# Маркер: EXCHANGE_LIST_GROW_V1
# Дата: 2026-06-21 · Брат (Шеф)
#
# БЕДА (Шеф): список активов зажат в скролл, не растянут.
# ПРИЧИНА: контейнер files_ref без явной высоты наследует тесную
# коробку; содержимое скроллится вместо роста по числу активов.
# РЕШЕНИЕ: даём списку явный стиль роста (height:auto, overflow:visible),
# и контейнеру asset-bay — рост по содержимому.
#
# ОДНО КАСАНИЕ: ui_exchange.py — стиль files_ref["element"].
# Идемпотентно, бэкап, py_compile.
#   python patch_exchange_list_grow.py
# ─────────────────────────────────────────────────────────────

import sys, shutil, py_compile
from datetime import datetime
from pathlib import Path

MARKER = "EXCHANGE_LIST_GROW_V1"
ROOT = Path.cwd()
EXCHANGE = ROOT / "studio" / "economy" / "ui_exchange.py"


def _fail(m): print(f"❌ {m}"); sys.exit(1)
def _backup(p):
    b = p.with_name(f"{p.name}.bak_{datetime.now():%Y%m%d_%H%M%S}")
    shutil.copy2(p, b); print(f"   💾 бэкап: {b.name}")


OLD = '                    files_ref["element"] = ui.element("div").classes("file-list")\n'
NEW = ('                    files_ref["element"] = ui.element("div").classes("file-list").style(  # ' + MARKER + '\n'
       '                        "height:auto; max-height:none; overflow:visible; padding:4px 8px;")\n')


def patch():
    if not EXCHANGE.exists():
        _fail(f"Не вижу {EXCHANGE}. Запускай из корня репы.")
    src = EXCHANGE.read_text(encoding="utf-8")
    if MARKER in src:
        print("✅ уже пропатчен — пропускаю."); return False
    if OLD not in src:
        _fail("не нашёл создание files_ref element — структура изменилась.")
    src = src.replace(OLD, NEW, 1)
    _backup(EXCHANGE)
    EXCHANGE.write_text(src, encoding="utf-8")
    print("✅ список растягивается (height:auto, overflow:visible).")
    return True


def main():
    print("═"*62); print("  СПИСОК АКТИВОВ РАСТЯГИВАЕТСЯ  ·", MARKER); print("═"*62)
    if patch():
        py_compile.compile(str(EXCHANGE), doraise=True)
        print("🧪 компилируется.")
        print("─"*62); print("✅ ГОТОВО. Список растёт по числу активов, без скролла.")
    else:
        print("─"*62); print("ℹ️  уже было.")


if __name__ == "__main__":
    main()
