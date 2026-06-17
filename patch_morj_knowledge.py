#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_morj_knowledge.py — Морж читает свою книжку MORJ_MATH.md

ЧТО ЧИНИТ (на пальцах):
  У Моржа теперь есть своя книга знаний — MORJ_MATH.md (Аллигатор + резинка,
  сверено с движком). Но код Моржа ищет файл с именем WILLIAMS_MATH.md
  (как у Искры) — и не находит, работает голым промтом.
  Имя книжки Моржа другое (его математика — Аллигатор, не AO Искры),
  поэтому учим код искать правильное имя.

ЧТО ДЕЛАЕТ (одна строка):
  KNOWLEDGE = .../WILLIAMS_MATH.md  →  KNOWLEDGE = .../MORJ_MATH.md
  Чтение уже есть (knowledge = KNOWLEDGE.read_text() if exists),
  механизм передачи в модель уже работает (knowledge=knowledge в chat()).
  Меняется ТОЛЬКО имя файла.

ПЕРЕД ЗАПУСКОМ: положи MORJ_MATH.md в
  studio/modules/trading/A02/forge/knowledge/MORJ_MATH.md
  (папки knowledge у Моржа пока нет — создай её).

БЕЗОПАСНОСТЬ: идемпотентен (маркер), бэкап .bak, якорный replace, CRLF-safe.
"""
import shutil
from datetime import datetime
from pathlib import Path

TARGET = Path("studio/modules/trading/morj_live.py")
MARKER = "MORJ_KNOWLEDGE_FILE"

OLD = 'KNOWLEDGE    = A02_DIR / "forge" / "knowledge" / "WILLIAMS_MATH.md"   # если появится'
NEW = 'KNOWLEDGE    = A02_DIR / "forge" / "knowledge" / "MORJ_MATH.md"   # книга Моржа (Аллигатор+резинка)  # ' + MARKER


def main():
    if not TARGET.exists():
        print(f"❌ Не найден файл: {TARGET}")
        return
    src = TARGET.read_text(encoding="utf-8")
    if MARKER in src:
        print(f"✅ Уже пропатчено (маркер {MARKER}) — ничего не делаю.")
        return

    if OLD in src:
        new_src = src.replace(OLD, NEW, 1)
    else:
        old_cr = OLD.replace("\n", "\r\n")
        if old_cr in src:
            new_src = src.replace(old_cr, NEW, 1)
        else:
            print("❌ Якорь не найден (строка KNOWLEDGE = ... WILLIAMS_MATH.md).")
            print("   Возможно уже менялась. Покажи строку 33 morj_live.py — поправлю.")
            return

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = TARGET.with_suffix(TARGET.suffix + f".bak_{stamp}")
    shutil.copy2(TARGET, bak)
    print(f"💾 Бэкап: {bak.name}")
    TARGET.write_text(new_src, encoding="utf-8")
    print("✅ Морж теперь читает свою книгу: MORJ_MATH.md.")
    print("   ⚠️ Не забудь положить файл в A02/forge/knowledge/MORJ_MATH.md")


if __name__ == "__main__":
    main()
