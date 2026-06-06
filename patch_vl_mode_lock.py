#!/usr/bin/env python3
"""
patch_vl_mode_lock.py — фикс video_long: BIBLE/EPISODE не перебивается SET'ом

Та же проблема что с ПЛАН/ПОСТ в social_mix.
Кнопки BIBLE и EPISODE не ставили run_type_locked = True.
SET при сборке брифа переключал на дефолтный 'episode'.
"""

import sys, shutil, py_compile, tempfile
from pathlib import Path
from datetime import datetime

DRY_RUN = "--dry-run" in sys.argv
BACKUP_DIR = Path("_patch_backups") / f"vl_mode_lock_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

def backup(path):
    if DRY_RUN: return
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, BACKUP_DIR / path.name)
    print(f"  ✓ backup → {BACKUP_DIR / path.name}")

def apply(path, old, new, desc):
    content = path.read_text(encoding="utf-8")
    if old not in content:
        print(f"  ⚠ Не найдено: {desc}")
        return False
    if DRY_RUN:
        print(f"  [DRY] {path.name}: {desc}")
        return True
    backup(path)
    nc = content.replace(old, new, 1)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".py", delete=False) as tmp:
        tmp.write(nc); tmp_path = Path(tmp.name)
    try:
        py_compile.compile(str(tmp_path), doraise=True)
    except py_compile.PyCompileError as e:
        tmp_path.unlink(); print(f"  ❌ {e}"); return False
    shutil.move(str(tmp_path), str(path))
    print(f"  ✓ {path.name}: {desc}")
    return True


# ── Патч 1: кнопки BIBLE/EPISODE ──────────────────────────────────

BTN_OLD = """                                def _set_bible():
                                    state['run_type'] = 'bible'
                                    _vl_refs['bible'].style('background:rgba(139,92,246,0.3); color:#a78bfa;')
                                    _vl_refs['episode'].style('background:transparent; color:rgba(255,255,255,0.35);')
                                    ui.notify('📖 Библия — создание вселенной (A01–A04)', type='info', timeout=2000)

                                def _set_episode():
                                    state['run_type'] = 'episode'
                                    _vl_refs['episode'].style('background:rgba(52,211,153,0.3); color:#34d399;')
                                    _vl_refs['bible'].style('background:transparent; color:rgba(255,255,255,0.35);')
                                    ui.notify('🎬 Эпизод — экранизация по Библии', type='info', timeout=2000)"""

BTN_NEW = """                                def _set_bible():
                                    state['run_type'] = 'bible'
                                    state['run_type_locked'] = True  # ПАТЧ: не перебивать SET'ом
                                    _vl_refs['bible'].style('background:rgba(139,92,246,0.3); color:#a78bfa;')
                                    _vl_refs['episode'].style('background:transparent; color:rgba(255,255,255,0.35);')
                                    ui.notify('📖 Библия — создание вселенной (A01–A04)', type='info', timeout=2000)

                                def _set_episode():
                                    state['run_type'] = 'episode'
                                    state['run_type_locked'] = True  # ПАТЧ: не перебивать SET'ом
                                    _vl_refs['episode'].style('background:rgba(52,211,153,0.3); color:#34d399;')
                                    _vl_refs['bible'].style('background:transparent; color:rgba(255,255,255,0.35);')
                                    ui.notify('🎬 Эпизод — экранизация по Библии', type='info', timeout=2000)"""


# ── Патч 2: build_brief() — уже пропатчен для social_mix,
#    но проверяем что патч run_type_lock уже применён ──────────────
# (если нет — применяем снова, теперь покрывает оба цеха)

BUILD_OLD = """            # ═══ SET AUTO-MODE: контент-план или производство ═══
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

BUILD_NEW = """            # ═══ SET AUTO-MODE: контент-план или производство ═══
            # ПАТЧ: не меняем режим если пользователь выбрал вручную
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
    print("ПАТЧ: video_long BIBLE/EPISODE lock")
    print("=" * 55)
    if DRY_RUN: print("DRY-RUN\n")

    ui_path = Path("studio/workshop/ui.py")

    print("\n[1/2] ui.py — BIBLE/EPISODE ставят run_type_locked")
    apply(ui_path, BTN_OLD, BTN_NEW, "locked=True для bible и episode")

    print("\n[2/2] ui.py — build_brief() уважает locked (если не пропатчено)")
    ok2 = apply(ui_path, BUILD_OLD, BUILD_NEW, "guard в build_brief")
    if not ok2:
        print("  → уже пропатчено ранее, пропускаем")

    print("\n" + "=" * 55)
    if not DRY_RUN:
        print("✅ Готово! Перезапусти: python main.py")
        print()
        print("Теперь: нажал BIBLE → SET не переключит на episode")

if __name__ == "__main__":
    main()
