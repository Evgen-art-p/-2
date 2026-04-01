"""
🔧 Комплексный патч для studio/city_walker.py v2

1. Фикс coroutine-never-awaited (log → async log)
2. Фильтр по цехам: run_city_walk(workshops=["turbo", "web_story"])
3. Резиденты ВСЕГДА гуляют (даже если workshops указан)
4. Лимит агентов за один запуск (max_agents)

Запуск:
  python patch_city_walker_v2.py          — применить
  python patch_city_walker_v2.py --check  — проверить
"""

import sys
from pathlib import Path

WALKER_FILE = Path("studio/city_walker.py")


def patch():
    check_only = "--check" in sys.argv

    if not WALKER_FILE.exists():
        print(f"❌ Файл не найден: {WALKER_FILE}")
        return False

    text = WALKER_FILE.read_text(encoding="utf-8")

    # Проверяем: уже патчено v2?
    if "workshops:" in text and "max_agents:" in text and "async def log" in text:
        print("✅ city_walker.py уже патчен v2.")
        return True

    if check_only:
        print("⚠ city_walker.py НЕ патчен v2. Запусти без --check.")
        return False

    # ═══════════════════════════════════════════
    # 1. ФИКС КОРУТИНЫ: log → async log
    # ═══════════════════════════════════════════

    old_log = '''    def log(msg: str):
        print(f"[CITY] {msg}")
        if on_progress:
            on_progress(msg)'''

    new_log = '''    async def log(msg: str):
        print(f"[CITY] {msg}")
        if on_progress:
            result = on_progress(msg)
            if asyncio.iscoroutine(result):
                await result'''

    if old_log in text:
        text = text.replace(old_log, new_log, 1)
        print("  ✓ log() → async def log()")
    elif "async def log" not in text:
        print("  ⚠ Не нашёл синхронную log() — пропускаю")

    # Все вызовы log() → await log() внутри run_city_walk
    import re
    pattern = re.compile(r'^(\s+)(?<!await )(?<!def )(?<!async def )log\(', re.MULTILINE)
    count_before = len(pattern.findall(text))
    text = pattern.sub(lambda m: f"{m.group(1)}await log(", text)
    if count_before:
        print(f"  ✓ {count_before} вызовов log() → await log()")

    # ═══════════════════════════════════════════
    # 2. НОВАЯ СИГНАТУРА run_city_walk
    # ═══════════════════════════════════════════

    old_sig = '''async def run_city_walk(
    agent_ids: list[str] | None = None,
    add_event: str | None = None,
    on_progress=None,
) -> list[dict]:
    """
    Запускает прогулку по городу.

    agent_ids: список ID агентов для прогулки.
               Если None — гуляют все у кого есть dna.json.
    add_event: событие которое добавляется в city_state
               (например "завершён TURBO ран" или "Артур выдал критику")
    on_progress: callback(message: str) для UI прогресса

    Возвращает список результатов по каждому агенту.
    """'''

    new_sig = '''async def run_city_walk(
    agent_ids: list[str] | None = None,
    workshops: list[str] | None = None,
    add_event: str | None = None,
    on_progress=None,
    max_agents: int = 0,
) -> list[dict]:
    """
    Запускает прогулку по городу.

    agent_ids:   список ID агентов для прогулки (точечный выбор).
    workshops:   список цехов для прогулки (напр. ["turbo", "web_story"]).
                 Резиденты (residents) гуляют ВСЕГДА, даже если не указаны.
                 Если None и agent_ids=None — гуляют ВСЕ.
    add_event:   событие которое добавляется в city_state
    on_progress: callback(message: str) для UI прогресса
    max_agents:  лимит агентов за один запуск (0 = без лимита).
                 Полезно для тестов: max_agents=5

    Возвращает список результатов по каждому агенту.
    """'''

    if old_sig in text:
        text = text.replace(old_sig, new_sig, 1)
        print("  ✓ Новая сигнатура run_city_walk (workshops, max_agents)")
    else:
        print("  ⚠ Не нашёл точную сигнатуру run_city_walk — РУЧНАЯ ПРОВЕРКА")

    # ═══════════════════════════════════════════
    # 3. ФИЛЬТР ПО ЦЕХАМ + РЕЗИДЕНТЫ ВСЕГДА
    # ═══════════════════════════════════════════

    old_filter = '''    # Загружаем агентов
    all_agents = get_all_agents()
    if agent_ids:
        all_agents = [a for a in all_agents if a.get("ID_Object") in agent_ids]

    if not all_agents:
        log("Нет агентов для прогулки.")
        return []'''

    new_filter = '''    # Загружаем агентов
    all_agents = get_all_agents()

    if agent_ids:
        # Точечный выбор по ID
        all_agents = [a for a in all_agents if a.get("ID_Object") in agent_ids]
    elif workshops:
        # Фильтр по цехам + резиденты ВСЕГДА
        allowed = set(workshops)
        allowed.add("residents")  # резиденты гуляют всегда
        all_agents = [a for a in all_agents if a.get("Workshop_ID", "") in allowed]

    # Лимит агентов (для тестов и безопасности)
    if max_agents > 0 and len(all_agents) > max_agents:
        await log(f"⚠ Лимит: {max_agents} из {len(all_agents)} агентов")
        all_agents = all_agents[:max_agents]

    if not all_agents:
        await log("Нет агентов для прогулки.")
        return []'''

    if old_filter in text:
        text = text.replace(old_filter, new_filter, 1)
        print("  ✓ Фильтр по цехам + резиденты всегда + max_agents")
    else:
        # Попробуем с await log (если корутина уже пофикшена)
        old_filter_await = old_filter.replace('        log(', '        await log(')
        if old_filter_await in text:
            text = text.replace(old_filter_await, new_filter, 1)
            print("  ✓ Фильтр по цехам (после await-фикса)")
        else:
            print("  ⚠ Не нашёл блок фильтрации агентов — РУЧНАЯ ПРОВЕРКА")

    # ═══════════════════════════════════════════
    # СОХРАНЯЕМ
    # ═══════════════════════════════════════════

    backup = WALKER_FILE.with_suffix(".py.bak_v2")
    if not backup.exists():
        import shutil
        shutil.copy2(str(WALKER_FILE), str(backup))
        print(f"  💾 Бэкап: {backup}")

    WALKER_FILE.write_text(text, encoding="utf-8")

    print(f"\n✅ city_walker.py патчен v2!")
    print()
    print("Использование:")
    print()
    print("  # Резиденты только:")
    print("  await run_city_walk(workshops=[])")
    print()
    print("  # Резиденты + turbo после рана:")
    print("  await run_city_walk(workshops=['turbo'])")
    print()
    print("  # Резиденты + несколько цехов:")
    print("  await run_city_walk(workshops=['turbo', 'web_story'])")
    print()
    print("  # Все (как было):")
    print("  await run_city_walk()")
    print()
    print("  # Тест — только 5 агентов:")
    print("  await run_city_walk(max_agents=5)")
    print()
    print("  # Кнопка 'прогулка' в UI — пока только резиденты:")
    print("  await run_city_walk(workshops=[])")
    return True


if __name__ == "__main__":
    patch()
