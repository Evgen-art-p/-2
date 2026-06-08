#!/usr/bin/env python3
"""
patch_clipmakers_victor_ui.py
Студия «Шесть пальцев» | Спринт 40

Одна правка в studio/workshop/ui.py:
  _victor_depts = ["video_long", "video_shorts"]
  →
  _victor_depts = ["video_long", "video_shorts", "clipmakers"]

Без этого пузырёк Виктора не появится в хедере clipmakers.
Весь ANCHOR механизм уже работает — менять больше ничего не нужно.

Запуск:
  python patch_clipmakers_victor_ui.py            # dry-run
  python patch_clipmakers_victor_ui.py --apply
"""
import sys, shutil, ast
from pathlib import Path

DRY_RUN      = "--apply" not in sys.argv
UI_PATH      = Path(__file__).parent / "studio" / "workshop" / "ui.py"
BACKUP_SUFFIX = ".bak_sprint40_victor_ui"

OLD = '_victor_depts = ["video_long", "video_shorts"]'
NEW = '_victor_depts = ["video_long", "video_shorts", "clipmakers"]'

def main():
    mode = "DRY-RUN" if DRY_RUN else "APPLY"
    print(f"\n{'='*55}")
    print(f"  patch_clipmakers_victor_ui.py  [{mode}]")
    print(f"{'='*55}\n")

    if not UI_PATH.exists():
        print(f"  ❌ не найден: {UI_PATH}")
        return

    content = UI_PATH.read_text(encoding="utf-8")

    if NEW in content:
        print("  ✓ clipmakers уже есть в _victor_depts — ничего делать не нужно")
        return

    if OLD not in content:
        print(f"  ❌ Не нашёл строку: {OLD!r}")
        print("  Возможно ui.py изменился — проверь вручную")
        return

    print(f"  [{'DRY' if DRY_RUN else 'APP'}] _victor_depts: добавить 'clipmakers'")
    print(f"       было: {OLD}")
    print(f"       стало: {NEW}")

    if not DRY_RUN:
        # Бэкап
        dst = UI_PATH.with_suffix(UI_PATH.suffix + BACKUP_SUFFIX)
        shutil.copy2(UI_PATH, dst)
        print(f"  бэкап → {dst.name}")

        new_content = content.replace(OLD, NEW, 1)
        UI_PATH.write_text(new_content, encoding="utf-8")

        # Проверка синтаксиса
        try:
            ast.parse(new_content)
            print("  ✅ ui.py обновлён, синтаксис OK")
        except SyntaxError as e:
            print(f"  ❌ SyntaxError: {e} — восстанавливаю бэкап")
            shutil.copy2(dst, UI_PATH)

    print(f"\n{'='*55}")
    if DRY_RUN:
        print("  Dry-run. Применить: python patch_clipmakers_victor_ui.py --apply")
    else:
        print("  ✅ Готово.")
        print("  Пузырёк Виктора теперь появится в хедере clipmakers.")
        print()
        print("  Как работает ANCHOR при хард-стопе (уже в ui.py):")
        print("  1. Виктор → пузырёк ⚡V пульсирует")
        print("  2. Клик на аватар A01/A03 → active_worker")
        print("  3. Пишешь правки в чат → chat_history_A0N")
        print("  4. ⚓ ANCHOR → run_cartridge_pipeline(from_worker, with_chat_context=True)")
        print("  5. ▶ CONTINUE → continue_cartridge_pipeline() → от следующего агента")
    print(f"{'='*55}\n")

if __name__ == "__main__":
    main()
