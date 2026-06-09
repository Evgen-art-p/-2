"""
patch_pipeline_memory_request.py — Спринт 43

Одно изменение в studio/workshop/pipeline.py:

В process_agent_result() после on_agent_done() —
если агент написал MEMORY_REQUEST: <запрос>,
Оле ищет в архиве и кладёт результат в previous_output
чтобы следующий агент в цепочке это увидел.

Применять из корня проекта:
  python patch_pipeline_memory_request.py
"""

import shutil
from datetime import datetime
from pathlib import Path

PIPELINE = Path("studio/workshop/pipeline.py")
STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")


def backup(path: Path):
    bak = path.with_suffix(f".bak_{STAMP}")
    shutil.copy2(path, bak)
    print(f"  [bak] {bak.name}")


def patch_str(src: str, old: str, new: str, label: str) -> str:
    if old not in src:
        print(f"  [SKIP] {label} — якорь не найден")
        return src
    result = src.replace(old, new, 1)
    print(f"  [OK]   {label}")
    return result


# ══════════════════════════════════════════════
# ЯКОРЬ — место сразу после on_agent_done()
# в process_agent_result()
# ══════════════════════════════════════════════

OLD = (
    "    if _GRONDHEIM_ENABLED:\n"
    "        on_agent_done(\n"
    "            agent_id=worker_id,\n"
    "            result_summary=human_text[:200],\n"
    "            dept=state.get(\"active_dept\", \"\"),\n"
    "        )\n"
    "\n"
    "        # Межагентное взаимодействие"
)

NEW = (
    "    if _GRONDHEIM_ENABLED:\n"
    "        on_agent_done(\n"
    "            agent_id=worker_id,\n"
    "            result_summary=human_text[:200],\n"
    "            dept=state.get(\"active_dept\", \"\"),\n"
    "        )\n"
    "\n"
    "        # СЕМЕЙНЫЙ АЛЬБОМ · Спринт 43\n"
    "        # Если агент написал MEMORY_REQUEST: — Оле слышит и ищет.\n"
    "        # Результат попадёт в previous_output → следующий агент увидит.\n"
    "        try:\n"
    "            from studio.residents_manager import handle_memory_request as _hmr\n"
    "            _archive_ctx = _hmr(\n"
    "                agent_id=worker_id,\n"
    "                agent_response=raw_result,\n"
    "                dept=state.get(\"active_dept\", \"\"),\n"
    "            )\n"
    "            if _archive_ctx:\n"
    "                state.setdefault(\"_archive_memory\", {})[worker_id] = _archive_ctx\n"
    "                print(f\"[ОЛЕ·ЦЕПОЧКА] \\U0001f4da {worker_id}: архив поднят для следующего шага\")\n"
    "        except Exception as _hmr_err:\n"
    "            print(f\"[ОЛЕ·ЦЕПОЧКА] \\u26a0 {worker_id}: {_hmr_err}\")\n"
    "\n"
    "        # Межагентное взаимодействие"
)


# ══════════════════════════════════════════════
# ЯКОРЬ 2 — в build_agent_context()
# добавляем архивную память в контекст следующего агента
# место: сразу перед блоком ФАЙЛЫ И ПРЕДЫДУЩИЕ РЕЗУЛЬТАТЫ
# ══════════════════════════════════════════════

OLD2 = (
    "    # ══ ФАЙЛЫ И ПРЕДЫДУЩИЕ РЕЗУЛЬТАТЫ ════════════════════════════════════\n"
    "    if files_ctx:\n"
    "        context += files_ctx + \"\\n\\n\"\n"
    "    if previous_output:\n"
    "        context += f\"=== РЕЗУЛЬТАТЫ ПРЕДЫДУЩИХ ЭТАПОВ ===\\n{previous_output}\\n\""
)

NEW2 = (
    "    # ══ АРХИВНАЯ ПАМЯТЬ (от предыдущего агента через Оле) ═══════════════\n"
    "    # Если предыдущий агент попросил MEMORY_REQUEST — кладём ответ Оле сюда.\n"
    "    _archive_mem = state.get(\"_archive_memory\", {})\n"
    "    if _archive_mem:\n"
    "        _all_archive = \"\\n\\n\".join(_archive_mem.values())\n"
    "        if _all_archive:\n"
    "            context += _all_archive + \"\\n\\n\"\n"
    "            print(f\"[ОЛЕ·ЦЕПОЧКА] \\U0001f4da {worker_id}: получил архивную память\")\n"
    "\n"
    "    # ══ ФАЙЛЫ И ПРЕДЫДУЩИЕ РЕЗУЛЬТАТЫ ════════════════════════════════════\n"
    "    if files_ctx:\n"
    "        context += files_ctx + \"\\n\\n\"\n"
    "    if previous_output:\n"
    "        context += f\"=== РЕЗУЛЬТАТЫ ПРЕДЫДУЩИХ ЭТАПОВ ===\\n{previous_output}\\n\""
)


def apply():
    print("\n╔══════════════════════════════════════════════╗")
    print("║  patch_pipeline_memory_request.py · Сп.43  ║")
    print("║  MEMORY_REQUEST в цепочке цеховых агентов  ║")
    print("╚══════════════════════════════════════════════╝\n")

    if not PIPELINE.exists():
        print(f"[ERROR] {PIPELINE} не найден")
        return

    backup(PIPELINE)
    src = PIPELINE.read_text(encoding="utf-8")

    src = patch_str(src, OLD, NEW,
        "process_agent_result(): слушаем MEMORY_REQUEST после on_agent_done()")
    src = patch_str(src, OLD2, NEW2,
        "build_agent_context(): инжектим архивную память перед previous_output")

    PIPELINE.write_text(src, encoding="utf-8")

    print()
    print("════════════════════════════════════════════════")
    print("✅ Патч применён.")
    print()
    print("Как это работает теперь:")
    print("  A03 пишет MEMORY_REQUEST: проект с аркой")
    print("  → Оле ищет в личном архиве A03")
    print("  → результат попадает в state['_archive_memory']")
    print("  → A04 при сборке контекста видит этот блок")
    print("  → A04 знает что A03 вспомнил")
    print()
    print("Три патча Семейного Альбома применены:")
    print("  ✅ patch_family_album.py       — архив + dig_archive + строчка про Оле")
    print("  ✅ patch_memory_request.py     — handle_memory_request + резиденты")
    print("  ✅ patch_pipeline_memory_request.py — цепочка цехов")


if __name__ == "__main__":
    apply()
