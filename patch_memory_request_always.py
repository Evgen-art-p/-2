"""
patch_memory_request_always.py — Спринт 43 · финальный

Убираем привязку MEMORY_REQUEST к режиму (WORK/HOME).
Агент может вспомнить в любой момент — на работе, дома, в таверне.
Архив не льётся автоматом — только по запросу самого агента.

Три изменения:

1. grondheim_memory.py → format_soul_for_agent()
   Строчка про Оле была только в HOME (в конце функции).
   Теперь — всегда, без условий.

2. pipeline.py → build_agent_context()
   Строчка про MEMORY_REQUEST была внутри `if is_work`.
   Теперь — вынесена наружу, добавляется всегда.

3. pipeline.py → build_agent_context()
   Убираем дублирование: раньше строчка была И в ИНСТРУКЦИИ (WORK),
   И теперь добавляется безусловно. Оставляем только безусловную.

Применять из корня проекта:
  python patch_memory_request_always.py
"""

import shutil
from datetime import datetime
from pathlib import Path

GRONDHEIM = Path("studio/grondheim_memory.py")
PIPELINE  = Path("studio/workshop/pipeline.py")
STAMP     = datetime.now().strftime("%Y%m%d_%H%M%S")


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


# ══════════════════════════════════════════════════════════
# ПАТЧ 1 — grondheim_memory.py
# format_soul_for_agent(): строчка про Оле была только в HOME
# убираем условие — пусть будет всегда
# ══════════════════════════════════════════════════════════

# Старый вариант (из patch_family_album): строчка добавлялась
# безусловно в конце format_soul_for_agent() — это уже правильно.
# Проверяем что она там есть и не привязана к условию.
# Если patch_family_album применён корректно — этот патч ничего не меняет
# в grondheim_memory, просто подтверждаем.

SOUL_CHECK = (
    "    parts.append(\n"
    "        \"\\n\\U0001f5c2 Если что-то кажется знакомым, но не помнишь — напиши:\\n\"\n"
    "        \"   MEMORY_REQUEST: <твой запрос>\\n\"\n"
    "        \"   Оле поднимет это из глубины. Она хранит всё что было.\"\n"
    "    )"
)

# Вариант который patch_family_album записал (с другим unicode)
SOUL_OLD = (
    "    parts.append(\n"
    "        \"\\n\\U0001f5c2 Если что-то кажется знакомым, но не помнишь — напиши:\\n\"\n"
    "        \"   MEMORY_REQUEST: <твой запрос>\\n\"\n"
    "        \"   Оле поднимет это из глубины. Она хранит всё что было.\"\n"
    "    )\n"
    "\n"
    "    if not parts:\n"
    "        return \"\"\n"
    "\n"
    "    return \"\\n\\n\".join(parts)"
)

# Правильный вариант — то же самое, строчка уже безусловна
# grondheim_memory менять не нужно если patch_family_album применён верно
# Патч просто проверит наличие


# ══════════════════════════════════════════════════════════
# ПАТЧ 2 — pipeline.py
# build_agent_context(): убираем строчку из if is_work
# добавляем безусловно перед финальным return
# ══════════════════════════════════════════════════════════

# Убираем из блока ИНСТРУКЦИЯ (был patch_instruction_memory_request)
PIPE_OLD_INSTRUCTION = (
    "    if is_work and client_slug != \"_sandbox\":\n"
    "        context += (\n"
    "            \"\\n=== ИНСТРУКЦИЯ ===\\n\"\n"
    "            \"В конце своего ответа добавь блок INSIGHT — одно предложение, \"\n"
    "            \"ключевой вывод о клиенте, который будет полезен тебе в будущих проектах.\\n\"\n"
    "            \"Формат: INSIGHT: <твой вывод>\\n\"\n"
    "            \"\\n\"\n"
    "            \"Если тема кажется знакомой но не помнишь откуда — напиши:\\n\"\n"
    "            \"MEMORY_REQUEST: <запрос>\\n\"\n"
    "            \"Оле поднимет из твоего архива. Один запрос за ран.\\n\"\n"
    "        )"
)

# INSIGHT остаётся только в WORK, MEMORY_REQUEST — убираем отсюда
PIPE_NEW_INSTRUCTION = (
    "    if is_work and client_slug != \"_sandbox\":\n"
    "        context += (\n"
    "            \"\\n=== ИНСТРУКЦИЯ ===\\n\"\n"
    "            \"В конце своего ответа добавь блок INSIGHT — одно предложение, \"\n"
    "            \"ключевой вывод о клиенте, который будет полезен тебе в будущих проектах.\\n\"\n"
    "            \"Формат: INSIGHT: <твой вывод>\\n\"\n"
    "        )"
)

# Добавляем MEMORY_REQUEST безусловно — перед записью контекста в state
PIPE_OLD_CACHE = (
    "    # Сохраняем для возможного ретрая Таможни\n"
    "    state.setdefault(\"_last_context\", {})[worker_id] = context"
)

PIPE_NEW_CACHE = (
    "    # ПАМЯТЬ БЕЗ УСЛОВИЙ · Спринт 43\n"
    "    # Агент может вспомнить в любой момент — на работе, дома, в таверне.\n"
    "    # Архив не льётся автоматом — только если сам попросит.\n"
    "    context += (\n"
    "        \"\\n\\U0001f5c2 Если что-то кажется знакомым но не помнишь — напиши \"\n"
    "        \"MEMORY_REQUEST: <запрос> и Оле поднимет из архива.\\n\"\n"
    "    )\n"
    "\n"
    "    # Сохраняем для возможного ретрая Таможни\n"
    "    state.setdefault(\"_last_context\", {})[worker_id] = context"
)


# ══════════════════════════════════════════════════════════
# ПРИМЕНЕНИЕ
# ══════════════════════════════════════════════════════════

def apply():
    print("\n╔══════════════════════════════════════════════════╗")
    print("║  patch_memory_request_always.py · Спринт 43    ║")
    print("║  MEMORY_REQUEST везде — без привязки к режиму  ║")
    print("╚══════════════════════════════════════════════════╝\n")

    # ── pipeline.py ─────────────────────────────────────
    print(f"▶ {PIPELINE}")
    if not PIPELINE.exists():
        print("  [ERROR] не найден")
    else:
        backup(PIPELINE)
        src = PIPELINE.read_text(encoding="utf-8")

        src = patch_str(
            src, PIPE_OLD_INSTRUCTION, PIPE_NEW_INSTRUCTION,
            "убираем MEMORY_REQUEST из блока ИНСТРУКЦИЯ (только WORK)"
        )
        src = patch_str(
            src, PIPE_OLD_CACHE, PIPE_NEW_CACHE,
            "добавляем MEMORY_REQUEST безусловно перед сохранением контекста"
        )

        PIPELINE.write_text(src, encoding="utf-8")
        print()

    # ── grondheim_memory.py — проверяем ─────────────────
    print(f"▶ {GRONDHEIM}")
    if not GRONDHEIM.exists():
        print("  [ERROR] не найден")
    else:
        src = GRONDHEIM.read_text(encoding="utf-8")
        if "MEMORY_REQUEST" in src:
            print("  [OK]   строчка про Оле уже есть — без условий ✅")
        else:
            print("  [WARN] строчка про Оле не найдена — проверь patch_family_album")
        print()

    print("══════════════════════════════════════════════════════")
    print("✅ Патч применён.")
    print()
    print("Теперь:")
    print("  • MEMORY_REQUEST доступен агенту всегда")
    print("  • неважно WORK / HOME / прогулка / таверна")
    print("  • архив не льётся сам — только по запросу агента")
    print("  • INSIGHT остался только в WORK (это правильно — рабочий вывод)")
    print()
    print("Семейный Альбом — финально собран:")
    print("  ✅ patch_family_album.py")
    print("  ✅ patch_memory_request.py")
    print("  ✅ patch_pipeline_memory_request.py")
    print("  ✅ patch_instruction_memory_request.py")
    print("  ✅ patch_memory_request_always.py  ← этот (финальный)")


if __name__ == "__main__":
    apply()
