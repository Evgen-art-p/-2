"""
🔧 Патч для studio/cabinet/tools.py — обновление city_walk

1. Кнопка «прогулка» → только резиденты (workshops=[])
2. Новый тулз city_walk_workshop — прогулка выбранных цехов
3. Обновление exec_city_walk под новую сигнатуру

Запуск:
  python patch_tools_walk.py
"""

import sys
from pathlib import Path

TOOLS_FILE = Path("studio/cabinet/tools.py")


def patch():
    if not TOOLS_FILE.exists():
        print(f"❌ {TOOLS_FILE} не найден")
        return False

    text = TOOLS_FILE.read_text(encoding="utf-8")

    if "city_walk_workshop" in text:
        print("✅ tools.py уже содержит city_walk_workshop")
        return True

    changes = 0

    # 1. Добавляем новый тулз city_walk_workshop в TOOLS_SCHEMA
    old_city_walk_schema = '''    # ═══ City Walker ═══
    {
        "type": "function",
        "function": {
            "name": "city_walk",
            "description": "Отправить агентов Грондхейма на прогулку по городу. Каждый агент сам решает куда пойти исходя из своего состояния, характера и погоды города. Прогулка снижает стресс и пополняет оперативную память.",
            "parameters": {
                "type": "object",
                "properties": {
                    "agent_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Список ID агентов для прогулки. Если не указан — гуляют все у кого есть dna.json."
                    },
                    "event": {
                        "type": "string",
                        "description": "Событие которое добавить в историю города (например 'завершён TURBO ран' или 'Артур выдал критику')."
                    }
                }
            }
        }
    },'''

    new_city_walk_schema = '''    # ═══ City Walker ═══
    {
        "type": "function",
        "function": {
            "name": "city_walk",
            "description": "Отправить РЕЗИДЕНТОВ Грондхейма на прогулку (Лока, Джем, Сет, Оле). Быстрая прогулка — только постоянные жители.",
            "parameters": {
                "type": "object",
                "properties": {
                    "event": {
                        "type": "string",
                        "description": "Событие которое добавить в историю города."
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "city_walk_workshop",
            "description": "Отправить на прогулку агентов выбранных цехов + резиденты (они гуляют всегда). Используй после завершения пайплайна чтобы дать отдохнуть цеху который отработал.",
            "parameters": {
                "type": "object",
                "properties": {
                    "workshops": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Цехи для прогулки: turbo, video_long, video_shorts, social_mix, web_story, clipmakers, advertising, emo_card, logo_design, market_hit, living_book"
                    },
                    "event": {
                        "type": "string",
                        "description": "Событие для истории города."
                    },
                    "max_agents": {
                        "type": "integer",
                        "description": "Лимит агентов (0 = без лимита). По умолчанию 20."
                    }
                }
            }
        }
    },'''

    if old_city_walk_schema in text:
        text = text.replace(old_city_walk_schema, new_city_walk_schema, 1)
        changes += 1
        print("  ✓ TOOLS_SCHEMA: city_walk обновлён + city_walk_workshop добавлен")
    else:
        print("  ⚠ Не нашёл city_walk в TOOLS_SCHEMA — проверь вручную")

    # 2. Добавляем executor для city_walk_workshop в executors dict
    old_executors_walk = '"city_walk": lambda a: exec_city_walk(a.get("agent_ids"), a.get("event", "")),'
    new_executors_walk = (
        '"city_walk": lambda a: exec_city_walk(None, a.get("event", "")),'
        '\n        "city_walk_workshop": lambda a: exec_city_walk_workshop('
        'a.get("workshops", []), a.get("event", ""), a.get("max_agents", 20)),'
    )

    if old_executors_walk in text:
        text = text.replace(old_executors_walk, new_executors_walk, 1)
        changes += 1
        print("  ✓ executors: city_walk + city_walk_workshop")
    else:
        print("  ⚠ Не нашёл city_walk executor — проверь вручную")

    # 3. Обновляем exec_city_walk — только резиденты
    old_exec = '''async def exec_city_walk(agent_ids: list | None = None, event: str = "") -> str:
    """Запустить прогулку агентов по городу."""
    try:
        from studio.city_walker import run_city_walk'''

    new_exec = '''async def exec_city_walk(agent_ids: list | None = None, event: str = "") -> str:
    """Запустить прогулку РЕЗИДЕНТОВ по городу."""
    try:
        from studio.city_walker import run_city_walk'''

    if old_exec in text:
        text = text.replace(old_exec, new_exec, 1)

    # Меняем вызов run_city_walk в exec_city_walk: workshops=[] → только резиденты
    old_call = '''        results = await run_city_walk(
            agent_ids=agent_ids or None,
            add_event=event or None,
            on_progress=collect,
        )'''

    new_call = '''        results = await run_city_walk(
            agent_ids=agent_ids or None,
            workshops=[],  # только резиденты
            add_event=event or None,
            on_progress=collect,
        )'''

    if old_call in text:
        text = text.replace(old_call, new_call, 1)
        changes += 1
        print("  ✓ exec_city_walk → workshops=[] (только резиденты)")

    # 4. Добавляем exec_city_walk_workshop — новая функция
    new_func = '''

async def exec_city_walk_workshop(workshops: list = None, event: str = "", max_agents: int = 20) -> str:
    """Запустить прогулку выбранных цехов + резиденты."""
    try:
        from studio.city_walker import run_city_walk

        messages = []

        async def collect(msg: str):
            messages.append(msg)

        ws_list = workshops or []
        ws_label = ", ".join(ws_list) if ws_list else "только резиденты"
        ui.notify(f"🚶 Прогулка: {ws_label}...", type="info")

        results = await run_city_walk(
            workshops=ws_list,
            add_event=event or None,
            on_progress=collect,
            max_agents=max_agents,
        )

        if not results:
            return "Нет агентов для прогулки."

        ok = [r for r in results if r["status"] == "ok"]
        lines = [f"🌆 Прогулка завершена · {len(ok)}/{len(results)} агентов"]
        lines.append(f"Цехи: {ws_label} + резиденты\\n")

        for r in results:
            if r["status"] == "ok":
                name = r["agent"]
                loc  = r["location"]
                resp = r["response"][:150]
                lines.append(
                    f"🚶 {name} → {loc}\\n"
                    f"   \\"{resp}...\\"\\n"
                )
            elif r["status"] == "skip":
                lines.append(f"⏭ {r['agent']}: {r['reason']}")
            else:
                lines.append(f"❌ {r['agent']}: {r['reason']}")

        return "\\n".join(lines)

    except ImportError:
        return "⚠️ city_walker.py не найден"
    except Exception as e:
        return f"❌ Ошибка прогулки: {e}"
'''

    # Вставляем перед финальной пустой строкой или в конец файла
    if "exec_city_walk_workshop" not in text:
        text = text.rstrip() + "\n" + new_func
        changes += 1
        print("  ✓ exec_city_walk_workshop() добавлена")

    if changes == 0:
        print("⚠ Изменений не найдено")
        return False

    TOOLS_FILE.write_text(text, encoding="utf-8")
    print(f"\n✅ tools.py патчен! ({changes} изменений)")
    print()
    print("Теперь:")
    print("  - Кнопка «прогулка» → только 4 резидента (~30 сек)")
    print("  - Через чат: «погуляй turbo» → city_walk_workshop(['turbo'])")
    print("  - Через чат: «погуляй всех» → city_walk_workshop(['turbo','web_story',...])")
    return True


if __name__ == "__main__":
    patch()
