"""
patch_memory_request.py — Спринт 43 · MEMORY_REQUEST handler

Два изменения в residents_manager.py:

1. Новая функция handle_memory_request(agent_id, agent_response, dept)
   — парсит "MEMORY_REQUEST: <запрос>" из ответа агента
   — вызывает dig_archive() через memory_tools
   — fallback: remind() из city_memory если личный архив пуст
   — возвращает форматированный текст для инжекта в следующий шаг

2. Хук в _run_resident() -> _work():
   после LLM-ответа проверяем MEMORY_REQUEST в тексте.
   Если есть — result["archive_memory"] = найденный контекст.

Применять из корня проекта:
  python patch_memory_request.py
"""

import shutil
from datetime import datetime
from pathlib import Path

# ──────────────────────────────────────────────
RESIDENTS_MANAGER = Path("studio/residents_manager.py")
STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
# ──────────────────────────────────────────────


def backup(path: Path):
    bak = path.with_suffix(f".bak_{STAMP}")
    shutil.copy2(path, bak)
    print(f"  [bak] {bak.name}")


def patch_str(src: str, old: str, new: str, label: str) -> str:
    if old not in src:
        print(f"  [SKIP] {label} — якорь не найден, пропускаю")
        return src
    result = src.replace(old, new, 1)
    print(f"  [OK]   {label}")
    return result


# ══════════════════════════════════════════════
# ПАТЧ 1 — новая функция handle_memory_request
# Вставляем ПЕРЕД get_ole_memory_for_agent()
# ══════════════════════════════════════════════

HANDLE_ANCHOR = "def get_ole_memory_for_agent(query: str, max_chars: int = 1500) -> str:"

HANDLE_NEW = (
    "def handle_memory_request(\n"
    "    agent_id: str,\n"
    "    agent_response: str,\n"
    "    dept: str = \"\",\n"
    "    max_chars: int = 1500,\n"
    ") -> str:\n"
    '    """\n'
    "    СЕМЕЙНЫЙ АЛЬБОМ · Спринт 43 — слух Оле.\n"
    "\n"
    "    Если агент написал в своём ответе:\n"
    "        MEMORY_REQUEST: <запрос>\n"
    "\n"
    "    Оле достаёт воспоминания из архива и возвращает\n"
    "    форматированный текст для инжекта в следующий шаг.\n"
    "\n"
    "    Возвращает пустую строку если сигнал не найден или архив пуст.\n"
    "    Вызывается из _run_resident() после каждого LLM-ответа.\n"
    '    """\n'
    "    import re as _re\n"
    "\n"
    "    match = _re.search(\n"
    r'        r"MEMORY_REQUEST\s*:\s*(.+?)(?:\n|$)",'
    "\n"
    "        agent_response,\n"
    "        _re.IGNORECASE,\n"
    "    )\n"
    "    if not match:\n"
    "        return \"\"\n"
    "\n"
    "    query = match.group(1).strip()\n"
    "    if not query:\n"
    "        return \"\"\n"
    "\n"
    "    print(f\"[ОЛЕ·СЛУХ] \\U0001f442 {agent_id} просит: '{query}'\")\n"
    "\n"
    "    try:\n"
    "        from studio.memory_tools import dig_archive, format_archive_for_agent\n"
    "        hits = dig_archive(agent_id=agent_id, query=query, dept=dept)\n"
    "        if not hits:\n"
    "            from studio.memory_tools import remind, format_for_agent\n"
    "            city_hits = remind(query=query, top_k=3)\n"
    "            if city_hits:\n"
    "                print(f\"[ОЛЕ·СЛУХ] \\U0001f310 Нашла в памяти города: {len(city_hits)}\")\n"
    "                return format_for_agent(city_hits, max_chars=max_chars)\n"
    "            print(f\"[ОЛЕ·СЛУХ] \\U0001f937 Ничего не нашла по '{query}'\")\n"
    "            return \"\"\n"
    "        return format_archive_for_agent(hits, max_chars=max_chars)\n"
    "    except Exception as e:\n"
    "        print(f\"[ОЛЕ·СЛУХ] \\u274c {e}\")\n"
    "        return \"\"\n"
    "\n"
    "\n"
    "def get_ole_memory_for_agent(query: str, max_chars: int = 1500) -> str:"
)


# ══════════════════════════════════════════════
# ПАТЧ 2 — хук в _run_resident() -> _work()
# ══════════════════════════════════════════════

HOOK_OLD = (
    "        return {\"verdict\": \"APPROVED\", \"text\": raw}\n"
    "\n"
    "    return resident_lifecycle("
)

HOOK_NEW = (
    "        # СЕМЕЙНЫЙ АЛЬБОМ · Спринт 43 — слышим MEMORY_REQUEST\n"
    "        result = {\"verdict\": \"APPROVED\", \"text\": raw}\n"
    "        archive_ctx = handle_memory_request(\n"
    "            agent_id=resident_id,\n"
    "            agent_response=raw,\n"
    "            dept=dept,\n"
    "        )\n"
    "        if archive_ctx:\n"
    "            result[\"archive_memory\"] = archive_ctx\n"
    "            print(f\"[ОЛЕ·СЛУХ] \\U0001f4da {resident_id}: архив поднят\")\n"
    "        return result\n"
    "\n"
    "    return resident_lifecycle("
)


# ══════════════════════════════════════════════
# ПРИМЕНЕНИЕ
# ══════════════════════════════════════════════

def apply():
    print("\n╔══════════════════════════════════════════╗")
    print("║  patch_memory_request.py · Спринт 43    ║")
    print("║  MEMORY_REQUEST → handle_memory_request ║")
    print("╚══════════════════════════════════════════╝\n")

    if not RESIDENTS_MANAGER.exists():
        print(f"[ERROR] {RESIDENTS_MANAGER} не найден")
        return

    backup(RESIDENTS_MANAGER)
    src = RESIDENTS_MANAGER.read_text(encoding="utf-8")

    src = patch_str(
        src, HANDLE_ANCHOR, HANDLE_NEW,
        "handle_memory_request() перед get_ole_memory_for_agent()"
    )
    src = patch_str(
        src, HOOK_OLD, HOOK_NEW,
        "хук MEMORY_REQUEST в _run_resident() -> _work()"
    )

    RESIDENTS_MANAGER.write_text(src, encoding="utf-8")

    print()
    print("═══════════════════════════════════════════")
    print("✅ Патч применён.")
    print()
    print("Что изменилось:")
    print("  • handle_memory_request(agent_id, agent_response, dept)")
    print("    — парсит MEMORY_REQUEST: <запрос> из ответа агента")
    print("    — личный архив агента (dig_archive) → fallback город (remind)")
    print("    — возвращает текст для инжекта")
    print()
    print("  • _run_resident(): result['archive_memory'] если сигнал найден")
    print()
    print("Следующий шаг (опционально):")
    print("  pipeline.py → process_agent_result():")
    print("  если result['archive_memory'] — добавить в контекст")
    print("  следующего агента в цепочке.")


if __name__ == "__main__":
    apply()
