#!/usr/bin/env python3
"""
patch_hooks_monteur.py
======================
Добавляет вызов Монтажёра в hooks.py после _bob_finalize:
  - Импорт run_monteur_assembly из residents_manager
  - Вызов в on_after_agent после A12 APPROVED

Запуск из корня репо: python patch_hooks_monteur.py
"""

from pathlib import Path

HOOKS_PATH = Path("studio/modules/video_long/hooks.py")

# ── Патч 1: импорт в шапке ────────────────────────────────────────

OLD_IMPORT = "from studio.fal_client import generate_with_refs, generate_image, add_to_catalog, load_catalog"

NEW_IMPORT = """from studio.fal_client import generate_with_refs, generate_image, add_to_catalog, load_catalog

# Монтажёр — финальная сборка после Боба
try:
    from studio.residents_manager import run_monteur_assembly as _run_monteur
    _MONTEUR_ENABLED = True
    print("[MONTEUR] 🎬 Монтажёр подключён")
except ImportError:
    _MONTEUR_ENABLED = False
    def _run_monteur(deliverables, project_id="", slot_id="video_long"):
        print("[MONTEUR] ⚠️  residents_manager не найден — сборка пропущена")"""

# ── Патч 2: вызов после _bob_finalize ────────────────────────────

OLD_BOB_CALL = """    elif mode == "episode" and worker_id == "A12":
        _bob_finalize(state, human_text)"""

NEW_BOB_CALL = """    elif mode == "episode" and worker_id == "A12":
        _bob_finalize(state, human_text)
        # Монтажёр запускается автоматически если chain_status APPROVED
        if _MONTEUR_ENABLED:
            _monteur_after_bob(state)"""

# ── Патч 3: функция _monteur_after_bob ───────────────────────────

MONTEUR_FUNC = """

# ═══════════════════════════════════════════════════════════════════
# МОНТАЖЁР — автосборка после Боба
# ═══════════════════════════════════════════════════════════════════

def _monteur_after_bob(state: dict):
    \"\"\"
    Вызывается хуком после _bob_finalize.
    Читает deliverables из state, проверяет chain_status APPROVED,
    запускает Монтажёра через residents_manager.

    Монтажёр — резидент на все цеха видео. Один. Работает с любым цехом.
    \"\"\"
    last_output = state.get("_last_output", {})
    deliverables = last_output.get("deliverables", {})

    if not deliverables:
        print("[MONTEUR] ⚠️  deliverables пусты — сборку пропускаю")
        return

    # Проверяем chain_status из bob_marketing
    bob_marketing = (last_output.get("my_output", {})
                                .get("bob_marketing", {}))
    chain_status = bob_marketing.get("chain_status", "")

    if chain_status != "APPROVED":
        print(f"[MONTEUR] ℹ️  chain_status={chain_status} — сборку не запускаю")
        return

    project_id = deliverables.get("project_id", state.get("project_id", ""))
    slot_id    = state.get("_slot_id", "video_long")

    print(f"[MONTEUR] 🎬 Боб дал APPROVED → запускаю сборку: {project_id}")

    try:
        result = _run_monteur(
            deliverables=deliverables,
            project_id=project_id,
            slot_id=slot_id,
        )
        # Сохраняем статус сборки в state
        state["_assembly_result"] = {
            "status":     result.status,
            "final_path": result.final_path,
            "duration":   result.duration_sec,
            "clips":      f"{result.clips_used}/{result.clips_total}",
        }
    except Exception as e:
        print(f"[MONTEUR] ❌ Сборка упала: {e}")
        state["_assembly_result"] = {"status": "FAILED", "error": str(e)}

"""


def apply():
    if not HOOKS_PATH.exists():
        print(f"❌ Не найден: {HOOKS_PATH}")
        print("   Запускай из корня репо.")
        return False

    text = HOOKS_PATH.read_text(encoding="utf-8")

    if "_monteur_after_bob" in text:
        print("ℹ️  Монтажёр уже подключён в hooks.py — ничего не делаю.")
        return True

    original = text

    # ── Патч 1: импорт ────────────────────────────────────────
    if OLD_IMPORT in text:
        text = text.replace(OLD_IMPORT, NEW_IMPORT)
        print("✅ Импорт run_monteur_assembly добавлен")
    else:
        print("⚠️  Строка импорта fal_client не найдена точно — пропускаю")

    # ── Патч 2: вызов в диспетчере ────────────────────────────
    if OLD_BOB_CALL in text:
        text = text.replace(OLD_BOB_CALL, NEW_BOB_CALL)
        print("✅ Вызов _monteur_after_bob добавлен в on_after_agent")
    else:
        print("⚠️  Блок A12 не найден точно — пропускаю")

    # ── Патч 3: функция перед _bob_finalize ───────────────────
    BOB_ANCHOR = "\ndef _bob_finalize"
    if "_monteur_after_bob" not in text and BOB_ANCHOR in text:
        text = text.replace(BOB_ANCHOR, MONTEUR_FUNC + "\ndef _bob_finalize")
        print("✅ _monteur_after_bob() добавлена перед _bob_finalize")

    if text == original:
        print("⚠️  Файл не изменился — проверь вручную")
        return False

    backup = HOOKS_PATH.with_suffix(".py.bak_monteur")
    backup.write_text(original, encoding="utf-8")
    print(f"💾 Бэкап: {backup}")

    HOOKS_PATH.write_text(text, encoding="utf-8")
    print(f"✅ Записано: {HOOKS_PATH}")
    print("\n🎉 Готово. После Боба (APPROVED) → Монтажёр собирает автоматически.")
    return True


if __name__ == "__main__":
    apply()
