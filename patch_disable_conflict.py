#!/usr/bin/env python3
"""
patch_disable_conflict.py — ОТКЛЮЧАЕМ conflict_mode в манифестах

ПРОБЛЕМА:
  conflict_mode: divergent запускает asyncio.gather с 4 параллельными
  LLM-вызовами через run_in_executor. На Windows ProactorEventLoop это
  создаёт состояние гонки при приёме новых TCP-соединений NiceGUI.
  Результат: "Exception in callback BaseProactorEventLoop._start_serving"
  → страница перезагружается.

РЕШЕНИЕ:
  Выключаем conflict_mode в manifest.json для social_mix и video_long.
  Агенты работают последовательно — стабильно, без гонок.
  Conflict system можно включить обратно когда перейдёшь на Linux/VPS.

ПРАВКИ:
  studio/modules/social_mix/manifest.json — conflict_mode: none
  studio/modules/video_long/manifest.json — conflict_mode: none
"""

import sys
import json
import shutil
from pathlib import Path
from datetime import datetime

DRY_RUN = "--dry-run" in sys.argv
BACKUP_DIR = Path("_patch_backups") / f"disable_conflict_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

def backup(path: Path):
    if DRY_RUN:
        print(f"  [DRY] backup {path}")
        return
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    dest = BACKUP_DIR / path.name
    shutil.copy2(path, dest)
    print(f"  ✓ backup → {dest}")

def patch_manifest(path: Path) -> bool:
    if not path.exists():
        print(f"  ❌ Не найден: {path}")
        return False

    data = json.loads(path.read_text(encoding="utf-8"))
    current = data.get("conflict_mode", "none")

    if current == "none":
        print(f"  ✓ {path.parent.name}/manifest.json — уже none, пропуск")
        return True

    if DRY_RUN:
        print(f"  [DRY] {path.parent.name}/manifest.json: {current} → none")
        return True

    backup(path)
    data["conflict_mode"] = "none"
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print(f"  ✓ {path.parent.name}/manifest.json: {current} → none")
    return True

def main():
    print("=" * 55)
    print("ПАТЧ: Отключаем conflict_mode (Windows asyncio fix)")
    print("=" * 55)
    if DRY_RUN:
        print("РЕЖИМ: DRY-RUN\n")

    manifests = [
        Path("studio/modules/social_mix/manifest.json"),
        Path("studio/modules/video_long/manifest.json"),
        Path("studio/modules/video_shorts/manifest.json"),
        Path("studio/modules/clipmakers/manifest.json"),
        Path("studio/modules/market_hit/manifest.json"),
        Path("studio/modules/advertising/manifest.json"),
        Path("studio/modules/logo_design/manifest.json"),
        Path("studio/modules/emo_card/manifest.json"),
        Path("studio/modules/web_story/manifest.json"),
    ]

    errors = 0
    for m in manifests:
        if not patch_manifest(m):
            errors += 1

    print()
    if DRY_RUN:
        print("DRY-RUN завершён. Запусти без --dry-run.")
    elif errors:
        print(f"❌ Ошибок: {errors}")
    else:
        print("✅ Готово!")
        print(f"   Бекапы: {BACKUP_DIR}")
        print()
        print("Что изменилось:")
        print("  • Все цеха: conflict_mode = none")
        print("  • Агенты работают последовательно (A01→A02→...→A12)")
        print("  • Никаких asyncio.gather → нет гонок на Windows")
        print("  • Страница перестанет перезагружаться")
        print()
        print("Перезапусти: python main.py")

if __name__ == "__main__":
    main()
