#!/usr/bin/env python3
"""
patch_quantum_walk.py — Спринт 24: Квантовые прогулки + Автотриггер

Что делает этот патч:
  1. Добавляет walk_quantum_chain() в studio/city_walker.py
     — утренняя прогулка: 1 квант (быстрый разогрев перед раном)
     — вечерняя прогулка: цепочка квантов пока хватает Light
  2. Добавляет автотриггер в studio/workshop/pipeline.py
     — после QA-агента вечерняя прогулка запускается сама
     — только для цеха у которого был ран (workshops=[dept])
     — не блокирует pipeline — fire-and-forget через asyncio.create_task

Архитектура: Вариант Б — обёртка поверх walk_one_agent(), сам файл не трогаем.

Запуск: python patch_quantum_walk.py
"""

import re
from pathlib import Path

CITY_WALKER_PATH = Path("studio/city_walker.py")
PIPELINE_PATH    = Path("studio/workshop/pipeline.py")

# ═══════════════════════════════════════════════════════
# 1. ВСТАВКА В city_walker.py
# ═══════════════════════════════════════════════════════

QUANTUM_WALK_CODE = '''

# ═══════════════════════════════════════════════════════
# КВАНТОВЫЕ ПРОГУЛКИ · Спринт 24
# ═══════════════════════════════════════════════════════

def _compute_attention_budget(dna: dict, mode: str = "evening") -> float:
    """
    Бюджет внимания агента — сколько кварталов он может пройти.

    Утро (mode="morning"):  фиксировано 1 квант — агент торопится на работу.
    Вечер (mode="evening"): зависит от Light после рана.
      Light > 0.7  → 3 кванта (полный вечер)
      Light 0.5–0.7 → 2 кванта
      Light < 0.5  → 1 квант (домой побыстрее)

    Stubbornness слегка корректирует: упрямый задержится ещё на 0.5 кванта.
    """
    if mode == "morning":
        return 1.0  # всегда 1 квант утром — без вариантов

    dynamic = dna.get("dynamic", {})
    static  = dna.get("static", {})
    light   = float(dynamic.get("Internal_Light", 0.75))
    stub    = float(static.get("Stubbornness", 0.5))

    if light > 0.70:
        base = 3.0
    elif light > 0.50:
        base = 2.0
    else:
        base = 1.0

    # Упрямый задерживается чуть дольше
    bonus = stub * 0.5
    return round(base + bonus, 2)


def _attention_cost(loc_type: str) -> float:
    """
    Стоимость кванта зависит от локации.
    Маяк тяжелее — там думаешь. Таверна средне. Площадь легко.
    """
    costs = {
        "lighthouse": 0.30,
        "harbor":     0.28,
        "temple":     0.25,
        "library":    0.25,
        "pavilion":   0.22,
        "tavern":     0.22,
        "castle":     0.20,
        "workshop":   0.20,
        "square":     0.15,
        "home":       0.0,   # дом не тратит — он финиш
        "other":      0.18,
    }
    return costs.get(loc_type, 0.18)


async def walk_quantum_chain(
    agent: dict,
    city_state: dict,
    locations: list,
    mode: str = "evening",
    on_progress=None,
) -> list[dict]:
    """
    Квантовая прогулка агента — цепочка локаций пока есть внимание.

    mode="morning" → 1 квант, быстро, разогрев перед раном
    mode="evening" → N квантов, бюджет из Light+Stubbornness

    Каждый квант:
      1. Считаем веса локаций (с учётом намерений утра)
      2. Запускаем walk_one_agent() — LLM выбирает куда
      3. Вычитаем стоимость кванта из бюджета
      4. Если домой пришёл или бюджет кончился — стоп

    sync_to_dna("walk_rest") вызывается внутри walk_one_agent() за каждый квант.
    Habit_strength обновляется за каждый визит.

    Возвращает список результатов по каждому кванту.
    """
    async def log(msg: str):
        print(f"[QUANTUM] {msg}")
        if on_progress:
            result = on_progress(msg)
            if asyncio.iscoroutine(result):
                await result

    workshop = agent.get("Workshop_ID", "")
    folder   = agent.get("_folder", "") or _resolve_folder(agent)
    name     = agent.get("Official_Name", folder)

    dna = load_dna(workshop, folder)
    if not dna:
        return [{"agent": name, "status": "skip", "reason": "нет dna.json"}]

    budget = _compute_attention_budget(dna, mode=mode)
    attention = budget

    mode_label = "🌅 утро" if mode == "morning" else "🏠 вечер"
    await log(f"{mode_label} | {name} | бюджет внимания: {budget:.1f}")

    results = []
    quantum_n = 0

    while attention > 0.12:  # порог "домой" — меньше этого уже не хватит на квант
        quantum_n += 1
        await log(f"  Квант {quantum_n}: внимание {attention:.2f}")

        result = await walk_one_agent(agent, city_state, locations)
        results.append(result)

        if result.get("status") != "ok":
            break

        chosen_loc  = result.get("location", "")
        chosen_type = _classify_location(chosen_loc)

        # Домой — прогулка завершена
        if chosen_type == "home":
            await log(f"  🏠 {name} пришёл домой — прогулка закончена")
            break

        # Утром — всегда только 1 квант
        if mode == "morning":
            await log(f"  ⚡ Утро: один квант сделан, {name} идёт на работу")
            break

        # Вычитаем стоимость кванта
        cost = _attention_cost(chosen_type)
        attention = round(attention - cost, 3)
        await log(f"  → {chosen_loc} (cost={cost:.2f}, осталось={attention:.2f})")

        # Небольшая пауза между квантами
        await asyncio.sleep(1)

    if attention <= 0.12 and results and results[-1].get("location", "") != "home":
        await log(f"  💤 {name}: внимание иссякло — идёт домой")

    return results


async def run_city_walk_morning(
    workshops: list[str] | None = None,
    on_progress=None,
    max_agents: int = 0,
) -> list[dict]:
    """
    Утренняя прогулка — 1 квант на агента, быстро.
    Вызывается кнопкой 🌅 ПОСЛЕ morning_checkout (агент уже знает свой режим дня).

    workshops: список цехов которые идут на работу. None = все.
    Резиденты всегда участвуют.
    """
    city_state = update_city_weather()
    all_agents = get_all_agents()

    if workshops:
        allowed = set(workshops)
        allowed.add("residents")
        all_agents = [a for a in all_agents if a.get("Workshop_ID", "") in allowed]

    if max_agents > 0 and len(all_agents) > max_agents:
        all_agents = all_agents[:max_agents]

    locations = get_all_locations()
    if not locations:
        return []

    city_state["here_now"] = {}
    save_city_state(city_state)

    results = []
    for agent in all_agents:
        chain = await walk_quantum_chain(
            agent, city_state, locations,
            mode="morning",
            on_progress=on_progress,
        )
        results.extend(chain)
        await asyncio.sleep(1)

    city_state["here_now"] = {}
    save_city_state(city_state)
    return results


async def run_city_walk_evening(
    workshops: list[str] | None = None,
    on_progress=None,
    max_agents: int = 0,
) -> list[dict]:
    """
    Вечерняя прогулка — цепочка квантов, бюджет из Light после рана.
    Вызывается автоматически после QA, или кнопкой вручную.

    workshops: цех который только что отработал. Резиденты всегда участвуют.
    """
    city_state = update_city_weather()
    all_agents = get_all_agents()

    if workshops:
        allowed = set(workshops)
        allowed.add("residents")
        all_agents = [a for a in all_agents if a.get("Workshop_ID", "") in allowed]

    if max_agents > 0 and len(all_agents) > max_agents:
        all_agents = all_agents[:max_agents]

    locations = get_all_locations()
    if not locations:
        return []

    city_state["here_now"] = {}
    save_city_state(city_state)

    results = []
    for agent in all_agents:
        chain = await walk_quantum_chain(
            agent, city_state, locations,
            mode="evening",
            on_progress=on_progress,
        )
        results.extend(chain)
        await asyncio.sleep(2)

    city_state["here_now"] = {}
    save_city_state(city_state)

    # Добавляем событие в историю города
    dept_label = workshops[0] if workshops and len(workshops) == 1 else "цех"
    add_city_event(f"Агенты {dept_label} вернулись с вечерней прогулки")

    return results

# ═══════════════════════════════════════════════════════
# END КВАНТОВЫЕ ПРОГУЛКИ
# ═══════════════════════════════════════════════════════
'''

# Якорь — вставляем перед последним блоком "ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ДЛЯ UI"
CITY_WALKER_ANCHOR = "# ═══════════════════════════════════════════════════════\n# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ДЛЯ UI"

# ═══════════════════════════════════════════════════════
# 2. АВТОТРИГГЕР В pipeline.py
# ═══════════════════════════════════════════════════════

# Вставляем импорт вверху (после существующих импортов Грондхейма)
PIPELINE_IMPORT_ANCHOR = "# ══ END NEW ══"

PIPELINE_IMPORT_ADD = """
# ══ NEW: Квантовые прогулки — автотриггер после рана ══
_QUANTUM_WALK_ENABLED = False
try:
    from studio.city_walker import run_city_walk_evening as _run_evening_walk
    _QUANTUM_WALK_ENABLED = True
    print("[CITY] 🌆 Квантовые прогулки подключены (автотриггер)")
except ImportError:
    async def _run_evening_walk(**kwargs): return []
# ══ END ══"""

# Вставляем автотриггер в конец QA-блока — сразу после maybe_rebuild()
PIPELINE_TRIGGER_ANCHOR = "        # ══ END Memory Embedding ══"

PIPELINE_TRIGGER_ADD = """
        # ══ АВТОТРИГГЕР: вечерняя прогулка после рана · Спринт 24 ══
        # Fire-and-forget — не блокирует пайплайн.
        # Агенты цеха идут домой своим путём пока UI уже показывает результат.
        if _QUANTUM_WALK_ENABLED:
            _dept_for_walk = state.get("active_dept", "")
            if _dept_for_walk:
                try:
                    asyncio.create_task(
                        _run_evening_walk(
                            workshops=[_dept_for_walk],
                            max_agents=0,  # все агенты цеха
                        )
                    )
                    print(f"[CITY] 🌆 Вечерняя прогулка запущена для цеха: {_dept_for_walk}")
                except Exception as _walk_err:
                    print(f"[CITY] ⚠ Автотриггер прогулки: {_walk_err}")
        # ══ END АВТОТРИГГЕР ══"""


# ═══════════════════════════════════════════════════════
# ПРИМЕНЕНИЕ ПАТЧА
# ═══════════════════════════════════════════════════════

def patch_city_walker():
    if not CITY_WALKER_PATH.exists():
        print(f"[ПАТЧ] ❌ Не найден: {CITY_WALKER_PATH}")
        return False

    text = CITY_WALKER_PATH.read_text(encoding="utf-8")

    if "walk_quantum_chain" in text:
        print("[ПАТЧ] ⚠ city_walker.py: walk_quantum_chain уже есть — пропускаем")
        return True

    if CITY_WALKER_ANCHOR not in text:
        print(f"[ПАТЧ] ❌ Якорь не найден в city_walker.py:\n  {CITY_WALKER_ANCHOR[:60]}")
        return False

    new_text = text.replace(
        CITY_WALKER_ANCHOR,
        QUANTUM_WALK_CODE + "\n\n" + CITY_WALKER_ANCHOR
    )

    CITY_WALKER_PATH.write_text(new_text, encoding="utf-8")
    print("[ПАТЧ] ✅ city_walker.py: walk_quantum_chain добавлен")
    return True


def patch_pipeline():
    if not PIPELINE_PATH.exists():
        print(f"[ПАТЧ] ❌ Не найден: {PIPELINE_PATH}")
        return False

    text = PIPELINE_PATH.read_text(encoding="utf-8")

    changed = False

    # 1. Импорт
    if "_QUANTUM_WALK_ENABLED" in text:
        print("[ПАТЧ] ⚠ pipeline.py: импорт уже есть — пропускаем")
    elif PIPELINE_IMPORT_ANCHOR in text:
        text = text.replace(
            PIPELINE_IMPORT_ANCHOR,
            PIPELINE_IMPORT_ANCHOR + PIPELINE_IMPORT_ADD
        )
        changed = True
        print("[ПАТЧ] ✅ pipeline.py: импорт квантовых прогулок добавлен")
    else:
        print(f"[ПАТЧ] ❌ Якорь импорта не найден:\n  {PIPELINE_IMPORT_ANCHOR}")

    # 2. Автотриггер
    if "АВТОТРИГГЕР: вечерняя прогулка" in text:
        print("[ПАТЧ] ⚠ pipeline.py: автотриггер уже есть — пропускаем")
    elif PIPELINE_TRIGGER_ANCHOR in text:
        text = text.replace(
            PIPELINE_TRIGGER_ANCHOR,
            PIPELINE_TRIGGER_ANCHOR + PIPELINE_TRIGGER_ADD
        )
        changed = True
        print("[ПАТЧ] ✅ pipeline.py: автотриггер вечерней прогулки добавлен")
    else:
        print(f"[ПАТЧ] ❌ Якорь триггера не найден:\n  {PIPELINE_TRIGGER_ANCHOR}")

    if changed:
        PIPELINE_PATH.write_text(text, encoding="utf-8")

    return True


if __name__ == "__main__":
    print("=" * 55)
    print("Спринт 24 — Квантовые прогулки + Автотриггер")
    print("=" * 55)

    ok1 = patch_city_walker()
    ok2 = patch_pipeline()

    print()
    if ok1 and ok2:
        print("✅ Патч применён.")
        print()
        print("Что появилось:")
        print("  city_walker.py:")
        print("    • walk_quantum_chain(agent, city_state, locations, mode)")
        print("    • run_city_walk_morning(workshops, max_agents)")
        print("    • run_city_walk_evening(workshops, max_agents)")
        print()
        print("  pipeline.py:")
        print("    • автотриггер вечерней прогулки после QA")
        print("      (fire-and-forget, не блокирует UI)")
        print()
        print("Следующий шаг — подключить кнопки в ui_cabinet.py:")
        print("  🌅 (утро) → morning_checkout() + run_city_walk_morning()")
        print("  🌆 (вечер) → run_city_walk_evening()  — уже автоматически")
    else:
        print("⚠ Часть патча не применена — проверь пути выше.")
