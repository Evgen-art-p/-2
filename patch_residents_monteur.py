#!/usr/bin/env python3
"""
patch_residents_monteur.py
==========================
Добавляет Монтажёра в residents_manager.py:
  - MONTEUR_DIR константа
  - run_monteur_assembly(deliverables, project_id, slot_id) → AssemblyResult

По образцу run_victor_critique().
Запуск из корня репо: python patch_residents_monteur.py
"""

from pathlib import Path

MANAGER_PATH = Path("studio/residents_manager.py")

# ── Что добавляем в константы (после VICTOR_DIR) ──────────────────

OLD_CONSTANTS = 'VICTOR_DIR = RESIDENTS_DIR / "005_VICTOR"   # Резидент-критик Виктор'

NEW_CONSTANTS = '''VICTOR_DIR  = RESIDENTS_DIR / "005_VICTOR"   # Резидент-критик Виктор
MONTEUR_DIR = RESIDENTS_DIR / "006_MONTEUR"  # Монтажёр — сборка финального ролика'''

# ── Что добавляем в конец файла ────────────────────────────────────

MONTEUR_BLOCK = '''

# ============================================================
# 006_MONTEUR — Монтажёр (финальная сборка роликов)
# ============================================================

def run_monteur_assembly(
    deliverables: dict,
    project_id: str = "",
    slot_id: str = "video_long",
):
    """Запускает Монтажёра — собирает финальный ролик из deliverables Боба.

    Вызывается из hooks.py после _bob_finalize когда chain_status APPROVED.
    Один Монтажёр работает со всеми цехами которые производят видео.

    Args:
        deliverables: dict из state["_last_output"]["deliverables"]
        project_id:   ID проекта (для папки output/render/)
        slot_id:      цех-источник (video_long, video_shorts, ...)

    Returns:
        AssemblyResult с полями:
            status      — "DONE" | "PARTIAL" | "FAILED"
            final_path  — путь к final.mp4 или None
            duration_sec, clips_used, clips_total, has_audio, errors
    """
    try:
        from studio.assembly.monteur import assemble
    except ImportError as e:
        print(f"[MONTEUR] ❌ monteur.py не найден: {e}")
        # Возвращаем заглушку с нужными полями
        class _FailResult:
            status = "FAILED"
            final_path = None
            duration_sec = 0.0
            clips_used = 0
            clips_total = 0
            has_audio = False
            has_vo = False
            has_sfx = False
            errors = [str(e)]
            assembled_at = ""
        return _FailResult()

    project_id = project_id or deliverables.get("project_id", "unknown")

    print(f"[MONTEUR] 🎬 Запуск сборки: {project_id} (цех: {slot_id})")

    result = assemble(
        deliverables=deliverables,
        project_id=project_id,
        slot_id=slot_id,
    )

    # Логируем итог
    if result.status == "DONE":
        print(
            f"[MONTEUR] ✅ {project_id} → {result.final_path} "
            f"({result.clips_used}/{result.clips_total} клипов, "
            f"{result.duration_sec:.1f}с)"
        )
    elif result.status == "PARTIAL":
        print(
            f"[MONTEUR] ⚠️  {project_id} — частично. "
            f"Ошибки: {result.errors[:2]}"
        )
    else:
        print(
            f"[MONTEUR] ❌ {project_id} — сборка упала. "
            f"Ошибки: {result.errors[:2]}"
        )

    return result
'''


def apply():
    if not MANAGER_PATH.exists():
        print(f"❌ Не найден: {MANAGER_PATH}")
        print("   Запускай из корня репо.")
        return False

    text = MANAGER_PATH.read_text(encoding="utf-8")

    # Проверяем — уже добавлен?
    if "run_monteur_assembly" in text:
        print("ℹ️  run_monteur_assembly уже есть — ничего не делаю.")
        return True

    original = text

    # ── Патч 1: константа ──────────────────────────────────────
    if OLD_CONSTANTS in text:
        text = text.replace(OLD_CONSTANTS, NEW_CONSTANTS)
        print("✅ Константа MONTEUR_DIR добавлена")
    else:
        print("⚠️  VICTOR_DIR строка не найдена точно — константу пропускаю")

    # ── Патч 2: функция в конец файла ──────────────────────────
    text = text.rstrip() + "\n" + MONTEUR_BLOCK

    print("✅ run_monteur_assembly() добавлена в конец файла")

    if text == original:
        print("⚠️  Файл не изменился")
        return False

    # Бэкап
    backup = MANAGER_PATH.with_suffix(".py.bak_monteur")
    backup.write_text(original, encoding="utf-8")
    print(f"💾 Бэкап: {backup}")

    MANAGER_PATH.write_text(text, encoding="utf-8")
    print(f"✅ Записано: {MANAGER_PATH}")
    print("\n🎉 Готово. Монтажёр зарегистрирован в residents_manager.")
    print("\nКак вызывать из hooks.py:")
    print("  from studio.residents_manager import run_monteur_assembly")
    print("  result = run_monteur_assembly(deliverables, project_id, slot_id)")
    return True


if __name__ == "__main__":
    apply()
