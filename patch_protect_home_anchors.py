#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════╗
║  ПАТЧ · ЗАЩИТА ДОМАШНЕГО И ЯКОРНОГО ПРОМПТОВ                ║
║  Студия «Шесть Пальцев» · Грондхейм                        ║
╚══════════════════════════════════════════════════════════════╝

ПРОБЛЕМА:
  generate_agent_files() в studio/ui_registry.py при КАЖДОМ сохранении
  агента через Страницу Жизни безусловно перезаписывал два файла:
    - home/home_prompt.md   ← домашняя жизнь, история, тайны
    - core/anchor_points.md ← вечные константы личности (текстовый слой)

  Если эти файлы правились РУКАМИ (а не через форму), то при редактировании
  агента ради рабочих настроек форма открывалась с пустыми домашними полями
  (их нет в catalog.json) и записывала файл заново с «— не заполнено —»,
  затирая ручной текст.

  Рабочий промпт forge/prompt.md НЕ страдал — он защищён `if not exists`.

РЕШЕНИЕ (умная логика, как у dna.json):
  Перезаписывать home_prompt.md и anchor_points.md ТОЛЬКО ЕСЛИ:
    - файла ещё нет (первое рождение), ЛИБО
    - в форме реально заполнены соответствующие поля.
  Пусто в форме + файл существует → НЕ трогаем. Ручной текст в безопасности.

  Сами тексты внутри функции (home_content, anchor_content) НЕ меняются —
  меняется только УСЛОВИЕ их записи на диск.

ПРИМЕНЕНИЕ:
  Положи скрипт в корень репозитория (рядом с папкой studio/) и запусти:
    python patch_protect_home_anchors.py
  Скрипт сам найдёт studio/ui_registry.py, сделает резервную копию
  ui_registry.py.bak и применит правку. Идемпотентен — повторный запуск
  ничего не сломает (увидит, что патч уже наложен).
"""

import sys
from pathlib import Path
from datetime import datetime

TARGET = Path("studio/ui_registry.py")


# ── Что ищем и на что меняем ─────────────────────────────────────────

# Блок 2: anchor_points.md — было (безусловная запись)
ANCHOR_OLD = '''    anchor_path = agent_dir / "core" / "anchor_points.md"
    anchor_path.write_text(anchor_content, encoding="utf-8")
    created.append(str(anchor_path))'''

# Блок 2: anchor_points.md — стало (умная защита)
ANCHOR_NEW = '''    anchor_path = agent_dir / "core" / "anchor_points.md"
    # ЗАЩИТА (патч): перезаписываем только если файла нет ИЛИ в форме
    # реально заполнены якорные поля. Иначе бережём ручную правку.
    _anchor_has_input = bool(
        (anchor_points or "").strip()
        or (core_phrase or "").strip()
    )
    if (not anchor_path.exists()) or _anchor_has_input:
        anchor_path.write_text(anchor_content, encoding="utf-8")
        created.append(str(anchor_path))'''


# Блок 3: home_prompt.md — было (безусловная запись)
HOME_OLD = '''    home_path = agent_dir / "home" / "home_prompt.md"
    home_path.write_text(home_content, encoding="utf-8")
    created.append(str(home_path))'''

# Блок 3: home_prompt.md — стало (умная защита)
HOME_NEW = '''    home_path = agent_dir / "home" / "home_prompt.md"
    # ЗАЩИТА (патч): перезаписываем только если файла нет ИЛИ в форме
    # реально заполнены домашние поля. Иначе бережём ручную правку.
    _home_has_input = bool(
        (home_story or "").strip()
        or (pull_vector or "").strip()
        or (obj.get("Sensory_Response") or "").strip()
        or (obj.get("Hidden_History") or "").strip()
    )
    if (not home_path.exists()) or _home_has_input:
        home_path.write_text(home_content, encoding="utf-8")
        created.append(str(home_path))'''


# Маркер, по которому понимаем, что патч уже наложен
ALREADY = "ЗАЩИТА (патч): перезаписываем только если файла нет"


def main() -> int:
    if not TARGET.exists():
        print(f"✗ Не найден {TARGET}")
        print("  Запусти скрипт из КОРНЯ репозитория (там где папка studio/).")
        return 1

    src = TARGET.read_text(encoding="utf-8")

    if ALREADY in src:
        print("ℹ Патч уже наложен ранее — ничего не делаю.")
        return 0

    problems = []
    if ANCHOR_OLD not in src:
        problems.append("не найден блок записи anchor_points.md")
    if HOME_OLD not in src:
        problems.append("не найден блок записи home_prompt.md")

    if problems:
        print("✗ Не могу применить патч — структура файла отличается:")
        for p in problems:
            print(f"   • {p}")
        print("  Файл не изменён. Напиши Брату — соберём патч под текущую версию.")
        return 1

    # Резервная копия
    backup = TARGET.with_suffix(".py.bak")
    backup.write_text(src, encoding="utf-8")

    patched = src.replace(ANCHOR_OLD, ANCHOR_NEW).replace(HOME_OLD, HOME_NEW)
    TARGET.write_text(patched, encoding="utf-8")

    print("✓ Патч наложен успешно.")
    print(f"  Резервная копия: {backup}")
    print()
    print("  Теперь форма НЕ затирает home_prompt.md и anchor_points.md,")
    print("  если соответствующие поля в ней пустые. Ручной текст в безопасности.")
    print()
    print("  Чтобы ОБНОВИТЬ домашку через форму — просто заполни домашние поля.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
