"""
patch_pipeline_harbor.py — Добавляет Рюкзак Знаний v2 (Гавань) в pipeline.py
═══════════════════════════════════════════════════════════════════════════════

Добавляет в build_agent_context() вызов get_harbor_knowledge() —
агент получает релевантные данные из ChromaDB при работе в пайплайне.

Бэкап: pipeline.py.bak_harbor

Использование:
  python patch_pipeline_harbor.py
  python patch_pipeline_harbor.py studio/workshop/pipeline.py
"""

import sys
import shutil
from pathlib import Path


def patch_file(filepath: str = None):
    if filepath:
        pipe_path = Path(filepath)
    else:
        candidates = [
            Path("studio/workshop/pipeline.py"),
            Path("workshop/pipeline.py"),
            Path("pipeline.py"),
        ]
        pipe_path = None
        for c in candidates:
            if c.exists():
                pipe_path = c
                break
        if not pipe_path:
            print("❌ Не найден pipeline.py!")
            sys.exit(1)

    print(f"📁 Файл: {pipe_path}")
    source = pipe_path.read_text(encoding="utf-8")
    original_len = len(source)

    # ═══════════════════════════════════════════════════════
    # ПАТЧ 1: Импорт harbor_of_meanings
    # ═══════════════════════════════════════════════════════

    IMPORT_ANCHOR = '''# ══ NEW: Грондхейм — личная память агента ══'''

    HARBOR_IMPORT = '''# ══ NEW: Гавань Смыслов — RAG внутренних знаний ══
try:
    from studio.harbor_of_meanings import get_harbor_knowledge
    _HARBOR_ENABLED = True
    print("[ГАВАНЬ] ⚓ Рюкзак Знаний v2 (RAG) подключён")
except ImportError:
    _HARBOR_ENABLED = False
    print("[ГАВАНЬ] ⚠ harbor_of_meanings.py не найден — работаем без Гавани")
    def get_harbor_knowledge(worker_id, dept, task_context=""): return ""
# ══ END ГАВАНЬ ══

# ══ NEW: Грондхейм — личная память агента ══'''

    if IMPORT_ANCHOR in source and "_HARBOR_ENABLED" not in source:
        source = source.replace(IMPORT_ANCHOR, HARBOR_IMPORT, 1)
        print("✅ Патч 1: Импорт harbor_of_meanings")
    elif "_HARBOR_ENABLED" in source:
        print("⏭  Патч 1: уже применён")
    else:
        print("⚠️  Патч 1: точка вставки не найдена")

    # ═══════════════════════════════════════════════════════
    # ПАТЧ 2: Добавить Гавань в build_agent_context()
    # (после Рюкзака Знаний с Маяка)
    # ═══════════════════════════════════════════════════════

    AFTER_BACKPACK = '''        print(f"[РЮКЗАК] 🔦 {worker_id} несёт знания с Маяка ({len(backpack)} симв.)")
    # ══ END ══'''

    WITH_HARBOR = '''        print(f"[РЮКЗАК] 🔦 {worker_id} несёт знания с Маяка ({len(backpack)} симв.)")

    # ══ Гавань Смыслов — RAG по внутренним знаниям ══
    if _HARBOR_ENABLED:
        harbor_ctx = get_harbor_knowledge(
            worker_id,
            state.get("active_dept", ""),
            task_context=state.get("master_brief", "")[:300],
        )
        if harbor_ctx:
            context += harbor_ctx + "\\n\\n"
            print(f"[РЮКЗАК] ⚓ {worker_id} получил знания из Гавани ({len(harbor_ctx)} симв.)")
    # ══ END ══'''

    if AFTER_BACKPACK in source and "harbor_ctx" not in source:
        source = source.replace(AFTER_BACKPACK, WITH_HARBOR, 1)
        print("✅ Патч 2: Гавань в build_agent_context()")
    elif "harbor_ctx" in source:
        print("⏭  Патч 2: уже применён")
    else:
        print("⚠️  Патч 2: точка вставки не найдена")

    # ═══════════════════════════════════════════════════════
    # СОХРАНЕНИЕ
    # ═══════════════════════════════════════════════════════

    if len(source) == original_len:
        print("\n⚠️ Ни один патч не применён. Файл не изменён.")
        sys.exit(1)

    backup_path = pipe_path.with_suffix(".py.bak_harbor")
    if not backup_path.exists():
        shutil.copy2(pipe_path, backup_path)
        print(f"\n💾 Бэкап: {backup_path}")

    pipe_path.write_text(source, encoding="utf-8")
    delta = len(source) - original_len
    print(f"\n📝 Записано: {pipe_path}")
    print(f"📏 +{delta:,} символов")
    print(f"\n{'='*50}")
    print(f"✅ Гавань подключена к пайплайну!")
    print(f"{'='*50}")


if __name__ == "__main__":
    path_arg = sys.argv[1] if len(sys.argv) > 1 else None
    patch_file(path_arg)
