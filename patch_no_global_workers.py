"""
patch_no_global_workers.py
==========================
Убирает `global WORKERS, ALL_WORKERS` из page_workshop().

Проблема: NiceGUI при reload=False всё равно создаёт нового клиента
при каждом подключении браузера и вызывает page_workshop() заново.
Изменение глобальных переменных внутри page_workshop() вызывает
побочные эффекты и лишние обновления страницы.

Три замены:
  1. global WORKERS, ALL_WORKERS → локальные _dept_workers, _all_workers
  2. WORKERS.values() → _dept_workers.values() в continue_cartridge_pipeline
  3. ALL_WORKERS → _all_workers в layout аватаров

Применение:
  python patch_no_global_workers.py [--dry-run]
"""

import sys
import shutil
from pathlib import Path
from datetime import datetime

TARGET = Path("studio/workshop/ui.py")
BACKUP = Path("_patch_backups")

# ─── Замена 1: убираем global и переходим на локальные переменные ─────────────

OLD_GLOBAL = """     # ══ DYNAMIC WORKERS: перестраиваем под текущий цех ══
    global WORKERS, ALL_WORKERS
    WORKERS, ALL_WORKERS = _build_workers_for_dept(dept)
    print(f"[WORKSHOP] Цех={dept}: {sum(len(v) for v in WORKERS.values())} агентов, фазы: {list(WORKERS.keys())}")"""

NEW_LOCAL = """    # ══ DYNAMIC WORKERS: локальные переменные — не трогаем глобальные ══
    _dept_workers, _all_workers = _build_workers_for_dept(dept)
    print(f"[WORKSHOP] Цех={dept}: {sum(len(v) for v in _dept_workers.values())} агентов, фазы: {list(_dept_workers.keys())}")"""

# ─── Замена 2: continue_cartridge_pipeline ────────────────────────────────────

OLD_CONTINUE = "        all_agents_flat = [w for workers in WORKERS.values() for w in workers]"
NEW_CONTINUE  = "        all_agents_flat = [w for workers in _dept_workers.values() for w in workers]"

# ─── Замена 3: layout аватаров ────────────────────────────────────────────────

OLD_AVATAR = "                    _avatar_list = ALL_TURBO if is_turbo else ALL_WORKERS"
NEW_AVATAR  = "                    _avatar_list = ALL_TURBO if is_turbo else _all_workers"


def main(dry_run=False):
    if not TARGET.exists():
        print(f"[ERROR] {TARGET} не найден")
        sys.exit(1)

    content = TARGET.read_text(encoding="utf-8")

    fixes = [
        ("global → локальные переменные", OLD_GLOBAL,    NEW_LOCAL),
        ("continue: WORKERS → _dept_workers",  OLD_CONTINUE, NEW_CONTINUE),
        ("аватары: ALL_WORKERS → _all_workers", OLD_AVATAR,   NEW_AVATAR),
    ]

    new_content = content
    for label, old, new in fixes:
        if old in new_content:
            new_content = new_content.replace(old, new, 1)
            print(f"  [OK] {label}")
        else:
            print(f"  [SKIP] {label} — не найдено (уже пропатчено?)")

    if dry_run:
        print("\n[DRY-RUN] Файл не изменён.")
        return

    if new_content == content:
        print("\n[INFO] Нечего менять — все фиксы уже применены.")
        return

    BACKUP.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    shutil.copy2(TARGET, BACKUP / f"ui.py.bak_no_global_{ts}")
    print(f"\n[BACKUP] {BACKUP}")

    TARGET.write_text(new_content, encoding="utf-8")
    print(f"[DONE] {TARGET}")
    print("\nСтраница больше не будет обновляться сама при запуске рана.")


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    main(dry_run=dry)
