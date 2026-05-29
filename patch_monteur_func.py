#!/usr/bin/env python3
"""
patch_monteur_func.py
=====================
Добавляет тело функции _monteur_after_bob в hooks.py.
Предыдущий патч добавил вызов но не добавил саму функцию.
Запуск из корня репо: python patch_monteur_func.py
"""
from pathlib import Path

HOOKS_PATH = Path("studio/modules/video_long/hooks.py")

FUNC = '''

# ═══════════════════════════════════════════════════════════════════
# МОНТАЖЁР — автосборка после Боба
# ═══════════════════════════════════════════════════════════════════

def _monteur_after_bob(state: dict):
    """
    Вызывается хуком после _bob_finalize.
    Проверяет chain_status APPROVED → запускает Монтажёра.
    Монтажёр — резидент на все цеха видео.
    """
    last_output  = state.get("_last_output", {})
    deliverables = last_output.get("deliverables", {})

    if not deliverables:
        print("[MONTEUR] ⚠️  deliverables пусты — сборку пропускаю")
        return

    chain_status = (last_output.get("my_output", {})
                               .get("bob_marketing", {})
                               .get("chain_status", ""))

    if chain_status != "APPROVED":
        print(f"[MONTEUR] ℹ️  chain_status={chain_status} — сборку не запускаю")
        return

    project_id = deliverables.get("project_id", state.get("project_id", ""))
    slot_id    = state.get("_slot_id", "video_long")

    print(f"[MONTEUR] 🎬 APPROVED → сборка: {project_id}")

    try:
        result = _run_monteur(
            deliverables=deliverables,
            project_id=project_id,
            slot_id=slot_id,
        )
        state["_assembly_result"] = {
            "status":     result.status,
            "final_path": result.final_path,
            "duration":   result.duration_sec,
            "clips":      f"{result.clips_used}/{result.clips_total}",
        }
    except Exception as e:
        print(f"[MONTEUR] ❌ Сборка упала: {e}")
        state["_assembly_result"] = {"status": "FAILED", "error": str(e)}

'''

def apply():
    if not HOOKS_PATH.exists():
        print(f"❌ Не найден: {HOOKS_PATH}")
        return False

    text = HOOKS_PATH.read_text(encoding="utf-8")

    if "def _monteur_after_bob" in text:
        print("ℹ️  _monteur_after_bob уже есть — ничего не делаю.")
        return True

    # Вставляем перед _bob_finalize
    ANCHOR = "\ndef _bob_finalize"
    if ANCHOR not in text:
        print("❌ Якорь _bob_finalize не найден")
        return False

    original = text
    text = text.replace(ANCHOR, FUNC + "\ndef _bob_finalize")

    backup = HOOKS_PATH.with_suffix(".py.bak_monteur_func")
    backup.write_text(original, encoding="utf-8")
    print(f"💾 Бэкап: {backup}")

    HOOKS_PATH.write_text(text, encoding="utf-8")
    print(f"✅ _monteur_after_bob добавлена в {HOOKS_PATH}")
    print("🎉 Готово.")
    return True

if __name__ == "__main__":
    apply()
