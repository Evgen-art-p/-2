#!/usr/bin/env python3
"""
migrate_turbo_agent_folders.py — Спринт 18 финал
Студия «Шесть Пальцев»

Мигрирует уже созданных агентов TURBO:
  Переименовывает папки и обновляет dna.json + info.json внутри.

Маппинг:
  T1_stella → T1
  A01       → T1  (если T1_stella не существует)
  A02       → T2
  A03       → T3
  A04       → T4
  A05       → T5

Запуск из корня студии:
  python migrate_turbo_agent_folders.py

Флаги:
  --dry-run   показать что будет сделано, без изменений
"""

import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.resolve()
TURBO_DIR = ROOT / "studio" / "modules" / "turbo"
BACKUP_SUFFIX = f".bak_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

DRY_RUN = "--dry-run" in sys.argv

# Предпочтительный порядок переименования (T1_stella приоритетнее A01)
RENAME_MAP = {
    "T1_stella": "T1",
    "A01":       "T1",
    "A02":       "T2",
    "A03":       "T3",
    "A04":       "T4",
    "A05":       "T5",
}

# ─── Утилиты ──────────────────────────────────────────────────────────────────

def load_json(path: Path) -> dict | list:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_json(path: Path, data):
    if not DRY_RUN:
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def backup_dir(src: Path) -> Path:
    bak = src.parent / (src.name + BACKUP_SUFFIX)
    if not DRY_RUN:
        shutil.copytree(str(src), str(bak))
    print(f"    📦 Бэкап: {bak.name}")
    return bak


# ─── Сканирование ─────────────────────────────────────────────────────────────

def scan_turbo_dir() -> dict[str, Path]:
    """
    Возвращает словарь {folder_name: path} для папок в turbo/
    которые требуют миграции.
    """
    if not TURBO_DIR.exists():
        return {}

    found = {}
    for d in TURBO_DIR.iterdir():
        if d.is_dir() and d.name in RENAME_MAP:
            found[d.name] = d
    return found


def detect_conflicts(found: dict[str, Path]) -> list[tuple]:
    """
    Ищет конфликты: два старых имени → одно новое.
    Например: T1_stella и A01 оба хотят стать T1.
    """
    conflicts = []
    new_names: dict[str, list[str]] = {}
    for old_name in found:
        new = RENAME_MAP[old_name]
        new_names.setdefault(new, []).append(old_name)

    for new_name, old_list in new_names.items():
        if len(old_list) > 1:
            conflicts.append((new_name, old_list))

    return conflicts


# ─── Миграция одной папки ─────────────────────────────────────────────────────

def migrate_folder(old_path: Path, new_name: str) -> bool:
    """
    1. Делает бэкап
    2. Переименовывает папку
    3. Обновляет dna.json (поле role + id если нужно)
    4. Обновляет info.json (поле id)
    """
    new_path = old_path.parent / new_name

    if new_path.exists():
        print(f"    ⚠️  Папка {new_name}/ уже существует — пропускаем {old_path.name}/")
        print(f"       Удали или проверь вручную: {new_path}")
        return False

    print(f"  📁 {old_path.name}/ → {new_name}/")
    backup_dir(old_path)

    # Переименовываем
    if not DRY_RUN:
        old_path.rename(new_path)

    # Обновляем dna.json
    dna_path = new_path / "dna.json"
    if dna_path.exists():
        dna = load_json(dna_path)
        old_role = dna.get("role", "")
        dna["role"] = new_name
        # Если id совпадал с именем папки — тоже обновляем
        if dna.get("id") == old_path.name:
            dna["id"] = new_name
        save_json(dna_path, dna)
        print(f"    ✏️  dna.json: role {old_role!r} → {new_name!r}")

    # Обновляем info.json
    info_path = new_path / "info.json"
    if info_path.exists():
        info = load_json(info_path)
        old_id = info.get("id", "")
        if old_id == old_path.name:
            info["id"] = new_name
            save_json(info_path, info)
            print(f"    ✏️  info.json: id {old_id!r} → {new_name!r}")

    # Обновляем core/anchors.json
    anchors_path = new_path / "core" / "anchors.json"
    if anchors_path.exists():
        anchors = load_json(anchors_path)
        if anchors.get("role") == old_path.name:
            anchors["role"] = new_name
            save_json(anchors_path, anchors)
            print(f"    ✏️  anchors.json: role → {new_name!r}")

    return True


# ─── main ──────────────────────────────────────────────────────────────────────

def main():
    mode = "DRY-RUN" if DRY_RUN else "БОЕВОЙ"
    print("=" * 60)
    print(f"Миграция TURBO агентов — режим {mode}")
    print(f"Директория: {TURBO_DIR}")
    print("=" * 60)

    if not TURBO_DIR.exists():
        print(f"\n❌ Директория не найдена: {TURBO_DIR}")
        print("   Проверь путь или запусти из корня студии.")
        return

    found = scan_turbo_dir()

    if not found:
        print("\n✅ Папок для миграции не найдено.")
        print("   Агенты уже используют правильные имена (T1–T5),")
        print("   или цех turbo/ пока пуст.")
        return

    print(f"\nНайдено папок для миграции: {len(found)}")
    for old_name, path in found.items():
        print(f"  {old_name}/ → {RENAME_MAP[old_name]}/")

    # Проверка конфликтов
    conflicts = detect_conflicts(found)
    if conflicts:
        print("\n⚠️  КОНФЛИКТЫ — два агента претендуют на одно имя:")
        for new_name, old_list in conflicts:
            print(f"  {new_name}/: {old_list}")
        print()
        print("  Что делать:")
        print("  1. Реши какой агент настоящий (загляни в dna.json каждого)")
        print("  2. Удали или переименуй лишний вручную")
        print("  3. Запусти скрипт снова")
        print()
        print("  Миграция НЕ запущена — сначала разреши конфликты.")
        return

    if DRY_RUN:
        print("\n[DRY-RUN] Изменений не вносилось. Убери --dry-run для реального запуска.")
        return

    # Сортируем: T1_stella раньше A01, чтобы T1_stella получил T1
    priority = {"T1_stella": 0, "A01": 1, "A02": 2, "A03": 3, "A04": 4, "A05": 5}
    sorted_found = sorted(found.items(), key=lambda x: priority.get(x[0], 99))

    print("\nЗапускаю миграцию...")
    migrated = 0
    skipped = 0

    for old_name, old_path in sorted_found:
        new_name = RENAME_MAP[old_name]
        ok = migrate_folder(old_path, new_name)
        if ok:
            migrated += 1
        else:
            skipped += 1

    print()
    print("=" * 60)
    print(f"✅ Мигрировано: {migrated}  |  ⚠️ Пропущено: {skipped}")
    print()
    print("Что дальше:")
    print("  1. Перезапусти сервер студии (сбросит _AGENT_DIR_CACHE)")
    print("  2. Открой Страницу Жизни — проверь что агенты видны")
    print("  3. Запусти тестовый ран turbo — агенты должны находиться")
    print("=" * 60)


if __name__ == "__main__":
    main()
