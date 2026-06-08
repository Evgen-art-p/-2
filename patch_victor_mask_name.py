#!/usr/bin/env python3
"""
patch_victor_mask_name.py
Студия «Шесть пальцев» | Спринт 40

Проблема: run_victor_critique передаёт mask_name=dept → ищет "clipmakers.md"
          но мы создали файл "clipmakers_hardstop.md"

Решение: переименовать clipmakers_hardstop.md → clipmakers.md
         чтобы совпало с паттерном mask_name=dept в _run_resident

Применять ПОСЛЕ patch_clipmakers_launch.py --apply

Запуск:
  python patch_victor_mask_name.py            # dry-run
  python patch_victor_mask_name.py --apply
"""
import sys, shutil
from pathlib import Path

DRY_RUN       = "--apply" not in sys.argv
STUDIO_ROOT   = Path(__file__).parent / "studio"
VICTOR_MASKS  = STUDIO_ROOT / "modules" / "residents" / "005_VICTOR" / "forge" / "masks"
OLD_MASK      = VICTOR_MASKS / "clipmakers_hardstop.md"
NEW_MASK      = VICTOR_MASKS / "clipmakers.md"

def log(msg): print(f"  {msg}")

def main():
    mode = "DRY-RUN" if DRY_RUN else "APPLY"
    print(f"\n{'='*60}")
    print(f"  patch_victor_mask_name.py  [{mode}]")
    print(f"{'='*60}\n")

    # Проверяем состояние
    print("[1/1] Маска Виктора для clipmakers")

    if NEW_MASK.exists():
        log("✓ clipmakers.md уже существует — всё правильно")
        print(f"\n{'='*60}")
        print("  Ничего делать не нужно.")
        print(f"{'='*60}\n")
        return

    if not OLD_MASK.exists():
        log(f"❌ {OLD_MASK.name} не найден")
        log(f"   Сначала примени patch_clipmakers_launch.py --apply")
        print(f"\n{'='*60}")
        print("  Патч не применён — файл-источник не найден.")
        print(f"{'='*60}\n")
        return

    print(f"  [{'DRY' if DRY_RUN else 'APP'}] "
          f"clipmakers_hardstop.md → clipmakers.md")
    log(f"Причина: run_victor_critique передаёт mask_name=dept → "
        f"_run_resident ищет 'clipmakers.md'")

    if not DRY_RUN:
        shutil.copy2(OLD_MASK, NEW_MASK)
        # Оставляем hardstop тоже — не удаляем, вдруг пригодится
        log(f"✅ скопирован: {NEW_MASK}")
        log(f"   оригинал {OLD_MASK.name} сохранён")

    # Финальная проверка
    print("\n[Проверка]")
    checks = {
        "005_VICTOR/masks/clipmakers.md":          NEW_MASK,
        "005_VICTOR/masks/clipmakers_hardstop.md": OLD_MASK,
    }
    for label, path in checks.items():
        exists = path.exists() if not DRY_RUN else (path == OLD_MASK)
        print(f"  {'✅' if exists else '○'} {label}")

    print(f"\n{'='*60}")
    if DRY_RUN:
        print("  Dry-run. Применить: python patch_victor_mask_name.py --apply")
    else:
        print("  ✅ Виктор теперь найдёт маску clipmakers.md")
        print("  run_victor_critique(dept='clipmakers') → mask_name='clipmakers'")
        print(f"  → {NEW_MASK}")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    main()
