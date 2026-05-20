#!/usr/bin/env python3
"""
fix_turbo_role_options.py — Исправление ошибки Спринт 18
Студия «Шесть Пальцев»

КОНТЕКСТ:
  Предыдущий патч (patch_ui_registry_turbo_roles.py) ошибочно
  заменил A01-A05 на T1-T5. T1-T5 — это кодовые имена персонажей
  в TURBO_RULES, но папки и worker_id везде используют A-нотацию.
  Единый стандарт по всей студии: A01-A12 (или A01-A05 для turbo).

ЧТО ИСПРАВЛЯЕТ:
  TURBO_ROLE_OPTIONS: ["", "T1","T2","T3","T4","T5"]
                    → ["", "A01","A02","A03","A04","A05"]

ЧТО НЕ ТРОГАЕТ:
  Существующие папки агентов (A01-A05) — они правильные, не трогать.

ВАЖНО:
  Скрипт migrate_turbo_agent_folders.py — НЕ ЗАПУСКАТЬ.
  Он переименовывал бы A→T, что неправильно.

Запуск из корня студии:
  python fix_turbo_role_options.py
"""

import os
import shutil
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.resolve()
TARGET = ROOT / "studio" / "ui_registry.py"
BACKUP_SUFFIX = f".bak_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

# После предыдущего патча стало так:
OLD_WRONG = 'TURBO_ROLE_OPTIONS = [\n    "", "T1", "T2", "T3", "T4", "T5"\n]'

# Правильный вариант:
NEW_CORRECT = 'TURBO_ROLE_OPTIONS = [\n    "", "A01", "A02", "A03", "A04", "A05"\n]'


def main():
    print("=" * 60)
    print("Исправление TURBO_ROLE_OPTIONS → A-нотация")
    print("=" * 60)

    if not TARGET.exists():
        print(f"❌ Файл не найден: {TARGET}")
        return

    content = TARGET.read_text(encoding="utf-8")

    # Случай 1: предыдущий патч уже применён (T1-T5)
    if OLD_WRONG in content:
        bak = str(TARGET) + BACKUP_SUFFIX
        shutil.copy2(str(TARGET), bak)
        print(f"📦 Бэкап: {bak}")
        content = content.replace(OLD_WRONG, NEW_CORRECT)
        TARGET.write_text(content, encoding="utf-8")
        print("✅ Исправлено: T1-T5 → A01-A05")

    # Случай 2: оригинал с T1_stella (патч не применялся)
    elif '"T1_stella"' in content:
        bak = str(TARGET) + BACKUP_SUFFIX
        shutil.copy2(str(TARGET), bak)
        print(f"📦 Бэкап: {bak}")
        # Убираем T1_stella, оставляем A01-A05
        content = content.replace(
            '"", "A01", "A02", "A03", "A04", "A05", "T1_stella"',
            '"", "A01", "A02", "A03", "A04", "A05"'
        )
        TARGET.write_text(content, encoding="utf-8")
        print("✅ Убран T1_stella, A01-A05 сохранены")

    # Случай 3: уже правильно
    elif '"", "A01", "A02", "A03", "A04", "A05"' in content and '"T1_stella"' not in content:
        print("✅ Уже правильно — A01-A05, без T1_stella. Ничего не меняем.")

    else:
        print("⚠️  Не удалось определить состояние файла.")
        print("   Проверь TURBO_ROLE_OPTIONS вручную:")
        print('   Должно быть: ["", "A01", "A02", "A03", "A04", "A05"]')
        return

    print()
    print("Итоговый стандарт папок по студии:")
    print("  turbo/      → A01, A02, A03, A04, A05")
    print("  video_long/ → A01 ... A12")
    print("  video_shorts→ A01 ... A12")
    print("  все цеха    → A01 ... A12")
    print()
    print("T1-T5 в TURBO_RULES — только кодовые имена персонажей,")
    print("не имена папок и не worker_id системы.")
    print()
    print("⛔  migrate_turbo_agent_folders.py — НЕ ЗАПУСКАТЬ.")
    print("    Существующие папки A01-A05 правильные.")
    print("=" * 60)


if __name__ == "__main__":
    main()
