#!/usr/bin/env python3
"""
patch_run_type_lock.py — фикс переопределения run_type

ПРОБЛЕМА:
  Пользователь нажимает ПЛАН в UI → state['run_type'] = 'content_plan'
  Затем нажимает BRIEF → build_brief() вызывает detect_run_type_from_brief()
  SET не находит маркеры 'content_plan' в тексте брифа → возвращает 'social'
  state['run_type'] меняется на 'social'
  Запускается FULL PIPELINE вместо остановки после A04

ФИКС:
  ui.py — build_brief() не перезаписывает run_type если пользователь
  уже выбрал режим вручную (content_plan). Только если run_type был
  автоматическим (social/episode/etc).
  
  Добавляем флаг state['run_type_locked'] который ставится при ручном
  выборе режима через кнопки ПЛАН/ПОСТ.
"""

import sys
import shutil
import py_compile
import tempfile
from pathlib import Path
from datetime import datetime

DRY_RUN = "--dry-run" in sys.argv
BACKUP_DIR = Path("_patch_backups") / f"run_type_lock_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

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
# ПАТЧ 1: ui.py — кнопки ПЛАН/ПОСТ ставят флаг locked
# ══════════════════════════════════════════════════════════════════

PLAN_BTN_OLD = """                                def _set_plan():
                                    state['run_type'] = 'content_plan'
                                    _sm_refs['plan'].style('background:rgba(99,179,237,0.3); color:#63b3ed;')
                                    _sm_refs['post'].style('background:transparent; color:rgba(255,255,255,0.35);')
                                    ui.notify('📝 Контент-план (A01–A04)', type='info', timeout=2000)

                                def _set_post():
                                    state['run_type'] = 'social'
                                    _sm_refs['post'].style('background:rgba(72,187,120,0.3); color:#68d391;')
                                    _sm_refs['plan'].style('background:transparent; color:rgba(255,255,255,0.35);')
                                    ui.notify('📱 Производство поста (все агенты)', type='info', timeout=2000)"""

PLAN_BTN_NEW = """                                def _set_plan():
                                    state['run_type'] = 'content_plan'
                                    state['run_type_locked'] = True  # ПАТЧ: не перезаписывать при BRIEF
                                    _sm_refs['plan'].style('background:rgba(99,179,237,0.3); color:#63b3ed;')
                                    _sm_refs['post'].style('background:transparent; color:rgba(255,255,255,0.35);')
                                    ui.notify('📝 Контент-план (A01–A04)', type='info', timeout=2000)

                                def _set_post():
                                    state['run_type'] = 'social'
                                    state['run_type_locked'] = True  # ПАТЧ: не перезаписывать при BRIEF
                                    _sm_refs['post'].style('background:rgba(72,187,120,0.3); color:#68d391;')
                                    _sm_refs['plan'].style('background:transparent; color:rgba(255,255,255,0.35);')
                                    ui.notify('📱 Производство поста (все агенты)', type='info', timeout=2000)"""


# ══════════════════════════════════════════════════════════════════
# ПАТЧ 2: ui.py — build_brief() не меняет run_type если locked
# ══════════════════════════════════════════════════════════════════

BUILD_BRIEF_OLD = """            # ═══ SET AUTO-MODE: контент-план или производство ═══
            dept = state.get("active_dept", "social_mix")
            default_type = DEPT_TO_RUNTYPE.get(dept, "social")
            new_run_type = detect_run_type_from_brief(
                brief=brief,
                dept=dept,
                default_run_type=default_type,
            )
            if state["run_type"] != new_run_type:
                state["run_type"] = new_run_type
                mode_label = "КОНТЕНТ-ПЛАН (A01-A04)" if new_run_type == "content_plan" else new_run_type
                print(f"[SET] Режим → {new_run_type}")
                ui.notify(f"📝 SET: режим {mode_label}", type="info", timeout=5000)
            # ═════════════════════════════════════════════════════"""

BUILD_BRIEF_NEW = """            # ═══ SET AUTO-MODE: контент-план или производство ═══
            # ПАТЧ run_type_lock: не меняем режим если пользователь
            # выбрал его вручную через кнопки ПЛАН/ПОСТ
            if not state.get("run_type_locked", False):
                dept = state.get("active_dept", "social_mix")
                default_type = DEPT_TO_RUNTYPE.get(dept, "social")
                new_run_type = detect_run_type_from_brief(
                    brief=brief,
                    dept=dept,
                    default_run_type=default_type,
                )
                if state["run_type"] != new_run_type:
                    state["run_type"] = new_run_type
                    mode_label = "КОНТЕНТ-ПЛАН (A01-A04)" if new_run_type == "content_plan" else new_run_type
                    print(f"[SET] Режим → {new_run_type}")
                    ui.notify(f"📝 SET: режим {mode_label}", type="info", timeout=5000)
            else:
                print(f"[SET] Режим зафиксирован пользователем: {state['run_type']}")
            # ═════════════════════════════════════════════════════"""


def main():
    print("=" * 55)
    print("ПАТЧ: run_type lock — ПЛАН/ПОСТ не перебивается SET'ом")
    print("=" * 55)
    if DRY_RUN:
        print("РЕЖИМ: DRY-RUN\n")

    ui_path = Path("studio/workshop/ui.py")

    print("\n[1/2] ui.py — кнопки ПЛАН/ПОСТ ставят флаг locked")
    ok1 = apply(ui_path, PLAN_BTN_OLD, PLAN_BTN_NEW,
                "run_type_locked = True при ручном выборе")

    print("\n[2/2] ui.py — build_brief() уважает locked флаг")
    ok2 = apply(ui_path, BUILD_BRIEF_OLD, BUILD_BRIEF_NEW,
                "detect_run_type_from_brief пропускается если locked")

    print("\n" + "=" * 55)
    if DRY_RUN:
        print("DRY-RUN завершён.")
        return

    if ok1 or ok2:
        print("✅ Патч применён!")
        print(f"   Бекапы: {BACKUP_DIR}")
        print()
        print("Что изменилось:")
        print("  • Нажал ПЛАН → run_type зафиксирован как content_plan")
        print("  • SET при сборке брифа НЕ переключает на 'social'")
        print("  • Пайплайн остановится после A04 как положено")
        print()
        print("Перезапусти: python main.py")
    else:
        print("⚠ Ничего не применено — проверь структуру файлов")


if __name__ == "__main__":
    main()
