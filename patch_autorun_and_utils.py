#!/usr/bin/env python3
"""
patch_autorun_and_utils.py — два точечных фикса

1. utils.py — AttributeError: 'list' object has no attribute 'get'
2. ui.py — _check_auto_run не перезапускает если пайплайн на паузе (paused_at)
"""

import sys
import shutil
import py_compile
import tempfile
from pathlib import Path
from datetime import datetime

DRY_RUN = "--dry-run" in sys.argv
BACKUP_DIR = Path("_patch_backups") / f"autorun_utils_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

def backup(path: Path):
    if DRY_RUN:
        print(f"  [DRY] backup {path}")
        return
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    dest = BACKUP_DIR / path.name
    shutil.copy2(path, dest)
    print(f"  ✓ backup → {dest}")

def apply(path: Path, old: str, new: str, desc: str) -> bool:
    if not path.exists():
        print(f"  ❌ Файл не найден: {path}")
        return False
    content = path.read_text(encoding="utf-8")
    if old not in content:
        print(f"  ⚠ Не найдено: {desc}")
        return False
    new_content = content.replace(old, new, 1)
    if DRY_RUN:
        print(f"  [DRY] {path.name}: {desc}")
        return True
    backup(path)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8",
                                     suffix=".py", delete=False) as tmp:
        tmp.write(new_content)
        tmp_path = Path(tmp.name)
    try:
        py_compile.compile(str(tmp_path), doraise=True)
    except py_compile.PyCompileError as e:
        tmp_path.unlink()
        print(f"  ❌ Синтакс-ошибка: {e}")
        return False
    shutil.move(str(tmp_path), str(path))
    print(f"  ✓ {path.name}: {desc}")
    return True


# ══════════════════════════════════════════════════════════════════
# ПАТЧ 1: utils.py — защита от list в _validate_asset_ids
# ══════════════════════════════════════════════════════════════════

UTILS_OLD = """    for item in selected.get(cat, []):"""

UTILS_NEW = """    if not isinstance(selected, dict):
        selected = {}
    for item in selected.get(cat, []):"""


# ══════════════════════════════════════════════════════════════════
# ПАТЧ 2: ui.py — _check_auto_run не стартует если paused_at
# Ищем несколько вариантов — патч мог уже частично применяться
# ══════════════════════════════════════════════════════════════════

# Вариант А — оригинальный (до наших патчей)
AUTORUN_OLD_A = """                async def _check_auto_run():
                    global _auto_run_requested
                    if _auto_run_requested and not state["pipeline_running"]:
                        _auto_run_requested = False
                        try:
                            with _page_client:
                                await run_cartridge_pipeline()
                        except Exception:
                            pass  # клиент мог умереть"""

AUTORUN_NEW_A = """                async def _check_auto_run():
                    global _auto_run_requested
                    if not _auto_run_requested:
                        return
                    if state.get("pipeline_running"):
                        return
                    if state.get("paused_at"):
                        return
                    _auto_run_requested = False
                    try:
                        with _page_client:
                            await run_cartridge_pipeline()
                    except Exception:
                        pass"""

# Вариант Б — после патча timer_and_contract
AUTORUN_OLD_B = """                async def _check_auto_run():
                    global _auto_run_requested
                    # ПАТЧ timer: guard — не запускаем если pipeline уже работает
                    if not _auto_run_requested:
                        return
                    if state.get("pipeline_running"):
                        return
                    _auto_run_requested = False
                    try:
                        with _page_client:
                            await run_cartridge_pipeline()
                    except Exception:
                        pass  # клиент мог умереть"""

AUTORUN_NEW_B = """                async def _check_auto_run():
                    global _auto_run_requested
                    # ПАТЧ: не стартуем если pipeline на паузе (Виктор, checkpoint)
                    if not _auto_run_requested:
                        return
                    if state.get("pipeline_running"):
                        return
                    if state.get("paused_at"):
                        return
                    _auto_run_requested = False
                    try:
                        with _page_client:
                            await run_cartridge_pipeline()
                    except Exception:
                        pass"""

# Вариант В — оригинал из репо (без наших патчей)
AUTORUN_OLD_C = """                async def _check_auto_run():
                    global _auto_run_requested
                    if _auto_run_requested and not state["pipeline_running"]:
                        _auto_run_requested = False
                        with _page_client:
                            await run_cartridge_pipeline()  # <- добавить отступ (4 пробела)

                ui.timer(1.0, _check_auto_run)"""

AUTORUN_NEW_C = """                async def _check_auto_run():
                    global _auto_run_requested
                    if not _auto_run_requested:
                        return
                    if state.get("pipeline_running"):
                        return
                    if state.get("paused_at"):
                        return
                    _auto_run_requested = False
                    try:
                        with _page_client:
                            await run_cartridge_pipeline()
                    except Exception:
                        pass

                ui.timer(1.0, _check_auto_run)"""


def main():
    print("=" * 55)
    print("ПАТЧ: utils fix + autorun paused_at guard")
    print("=" * 55)
    if DRY_RUN:
        print("DRY-RUN\n")

    utils_path = Path("studio/workshop/utils.py")
    ui_path    = Path("studio/workshop/ui.py")

    print("\n[1/2] utils.py — защита от list в _validate_asset_ids")
    ok1 = apply(utils_path, UTILS_OLD, UTILS_NEW,
                "isinstance(selected, dict) перед .get()")
    if not ok1:
        print("  → возможно уже пропатчено")

    print("\n[2/2] ui.py — _check_auto_run не стартует при paused_at")
    # Пробуем все варианты
    ok2 = apply(ui_path, AUTORUN_OLD_C, AUTORUN_NEW_C, "вариант C (оригинал репо)")
    if not ok2:
        ok2 = apply(ui_path, AUTORUN_OLD_A, AUTORUN_NEW_A, "вариант A")
    if not ok2:
        ok2 = apply(ui_path, AUTORUN_OLD_B, AUTORUN_NEW_B, "вариант B (после timer патча)")
    if not ok2:
        print("  ❌ Ни один вариант не найден — структура файла изменилась")

    print("\n" + "=" * 55)
    if not DRY_RUN:
        print("✅ Готово! Перезапусти: python main.py")
        print()
        print("Что изменилось:")
        print("  • utils.py: нет краша при list вместо dict")
        print("  • ui.py: после хард-стопа Виктора страница")
        print("    НЕ перезапускает пайплайн автоматически")
        print("    Нажми CONTINUE чтобы продолжить")
    else:
        print("DRY-RUN завершён.")

if __name__ == "__main__":
    main()
