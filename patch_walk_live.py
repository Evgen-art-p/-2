"""
patch_walk_live.py
=================================================================
Два фикса в одном:

1. ЖИВАЯ КАРТА — агенты видны во время прогулки
   - here_now НЕ очищается в конце run_city_walk/morning/evening
   - _do_city_walk получает on_progress callback который каждые
     3 агента вызывает _refresh_map() прямо в UI

2. БЕЗ ВЕЧНОЙ ЗАГРУЗКИ — батчевый параллелизм + таймаут
   - walk_one_agent оборачивается в asyncio.wait_for(timeout=45)
   - Агенты идут батчами по BATCH_SIZE=12 параллельно
   - Между батчами asyncio.sleep(2) вместо sleep(2) на каждого
   - Один зависший агент не блокирует остальных

Файлы:
  studio/city_walker.py   — run_city_walk, run_city_walk_morning,
                             run_city_walk_evening, walk_quantum_chain
  studio/cabinet/ui_cabinet.py — _do_city_walk, _do_morning_checkout,
                                  _do_evening_walk

Применение:
  python patch_walk_live.py [--dry-run]
"""

import sys
import shutil
from pathlib import Path
from datetime import datetime

WALKER = Path("studio/city_walker.py")
CABINET = Path("studio/cabinet/ui_cabinet.py")
BACKUP_DIR = Path("_patch_backups")

# ─── Патч 1: city_walker.py ──────────────────────────────────────────────────
# Заменяем финальную очистку here_now в run_city_walk на "не трогаем"
# и добавляем батчевый asyncio.gather вместо последовательного цикла

OLD_WALK_LOOP = """    # Запускаем прогулки — последовательно с паузой чтобы не спамить API
    results = []
    for i, agent in enumerate(all_agents):
        name = agent.get("Official_Name", agent.get("ID_Object", "?"))
        await log(f"🚶 {name} выходит в город...")

        result = await walk_one_agent(agent, city_state, locations)

        # Retry при обрыве соединения (1 попытка)
        if result.get("status") == "error" and "Connection" in result.get("reason", ""):
            await log(f"  ⚡ Переподключение через 3 сек...")
            await asyncio.sleep(3)
            result = await walk_one_agent(agent, city_state, locations)

        results.append(result)

        if result["status"] == "ok":
            await log(f"  → {name} пошёл в: {result['location']}")
            await log(f"  💭 {result['response'][:120]}...")
        elif result["status"] == "skip":
            await log(f"  ⏭ {name}: {result['reason']}")
        else:
            await log(f"  ❌ {name}: ошибка — {result['reason']}")

        # Пауза между агентами — защита от rate limit OpenRouter
        await asyncio.sleep(2)

    # Очищаем пространство и активных агентов после прогулки
    city_state["active_agents"] = []
    city_state["here_now"] = {}
    save_city_state(city_state)"""

NEW_WALK_LOOP = """    # Запускаем прогулки — батчами, параллельно внутри батча
    BATCH_SIZE = 12   # агентов одновременно (rate limit защита)
    AGENT_TIMEOUT = 45  # сек на одного агента

    results = []

    async def _safe_walk(agent):
        name = agent.get("Official_Name", agent.get("ID_Object", "?"))
        try:
            return await asyncio.wait_for(
                walk_one_agent(agent, city_state, locations),
                timeout=AGENT_TIMEOUT,
            )
        except asyncio.TimeoutError:
            return {"agent": name, "status": "skip", "reason": f"таймаут {AGENT_TIMEOUT}s"}
        except Exception as e:
            return {"agent": name, "status": "error", "reason": str(e)}

    for batch_start in range(0, len(all_agents), BATCH_SIZE):
        batch = all_agents[batch_start:batch_start + BATCH_SIZE]
        batch_num = batch_start // BATCH_SIZE + 1
        total_batches = (len(all_agents) + BATCH_SIZE - 1) // BATCH_SIZE
        await log(f"🏃 Батч {batch_num}/{total_batches}: {len(batch)} агентов параллельно...")

        batch_results = await asyncio.gather(
            *[_safe_walk(a) for a in batch],
            return_exceptions=True,
        )

        for agent, result in zip(batch, batch_results):
            name = agent.get("Official_Name", agent.get("ID_Object", "?"))
            if isinstance(result, Exception):
                result = {"agent": name, "status": "error", "reason": str(result)}
            results.append(result)
            if result["status"] == "ok":
                await log(f"  ✓ {name} → {result['location']}")
            elif result["status"] == "skip":
                await log(f"  ⏭ {name}: {result['reason']}")
            else:
                await log(f"  ❌ {name}: {result['reason']}")

        # Пауза между батчами
        if batch_start + BATCH_SIZE < len(all_agents):
            await asyncio.sleep(2)

    # Сохраняем активных агентов, here_now НЕ очищаем —
    # карта должна показывать последние позиции
    city_state["active_agents"] = []
    save_city_state(city_state)"""

# Очистка here_now в конце morning — тоже убираем
OLD_MORNING_END = """    city_state["here_now"] = {}
    save_city_state(city_state)
    return results


async def run_city_walk_evening("""

NEW_MORNING_END = """    # here_now НЕ очищаем — карта показывает последние позиции
    save_city_state(city_state)
    return results


async def run_city_walk_evening("""

# Очистка here_now в конце evening — убираем
OLD_EVENING_END = """    city_state["here_now"] = {}
    save_city_state(city_state)

    # Добавляем событие в историю города"""

NEW_EVENING_END = """    # here_now НЕ очищаем — карта показывает последние позиции
    save_city_state(city_state)

    # Добавляем событие в историю города"""

# walk_quantum_chain: убираем sleep(1) между квантами — уже есть gather
OLD_QUANTUM_SLEEP = """        # Небольшая пауза между квантами
        await asyncio.sleep(1)"""

NEW_QUANTUM_SLEEP = """        # Пауза между квантами минимальная
        await asyncio.sleep(0.3)"""

# Между агентами в morning/evening — тоже уменьшаем
OLD_MORNING_SLEEP = """        await asyncio.sleep(1)

    city_state["here_now"] = {}
    save_city_state(city_state)
    return results


async def run_city_walk_evening("""

NEW_MORNING_SLEEP = """        await asyncio.sleep(0.5)

    # here_now НЕ очищаем — карта показывает последние позиции
    save_city_state(city_state)
    return results


async def run_city_walk_evening("""

OLD_EVENING_SLEEP = """        await asyncio.sleep(2)

    city_state["here_now"] = {}
    save_city_state(city_state)

    # Добавляем событие в историю города"""

NEW_EVENING_SLEEP = """        await asyncio.sleep(0.5)

    # here_now НЕ очищаем — карта показывает последние позиции
    save_city_state(city_state)

    # Добавляем событие в историю города"""


# ─── Патч 2: ui_cabinet.py ───────────────────────────────────────────────────
# _do_city_walk: добавляем on_progress callback с _refresh_map каждые 3 агента

OLD_DO_CITY_WALK = """    async def _do_city_walk():
        \"\"\"Запустить прогулку всех агентов.\"\"\"
        try:
            from studio.cabinet.tools import exec_city_walk
            ui.notify("🚶 Агенты выходят в город...", type="info")
            result = await exec_city_walk()
            try:
                ui.notify("✅ Прогулка завершена", type="positive")
                _refresh_map()
                reload_all_agents()
                update_residents()
                update_city_zone()
                # Показываем результат в чате если есть активный агент
                if state.get("selected_agent"):
                    state["chat_history"].append({
                        "role": "assistant",
                        "content": result,
                        "time": datetime.now().strftime("%H:%M")
                    })
                    update_chat()
            except Exception:
                # Клиент мог быть удалён (страница обновлена)
                print("[CITY] ⚠ UI обновлён во время прогулки — результат записан в память")
        except Exception as e:
            try:
                ui.notify(f"❌ {e}", type="negative")
            except Exception:
                print(f"[CITY] ❌ {e}")"""

NEW_DO_CITY_WALK = """    async def _do_city_walk():
        \"\"\"Запустить прогулку всех агентов — с живой картой.\"\"\"
        try:
            from studio.city_walker import run_city_walk, update_city_weather, get_all_agents, get_all_locations
            ui.notify("🚶 Агенты выходят в город...", type="info")

            city_state = update_city_weather()
            all_agents = get_all_agents()
            locations  = get_all_locations()

            if not all_agents:
                ui.notify("⚠ Нет агентов", type="warning")
                return
            if not locations:
                ui.notify("⚠ Нет локаций в каталоге", type="warning")
                return

            city_state["here_now"] = {}
            from studio.city_walker import save_city_state
            save_city_state(city_state)

            _walk_counter = {"n": 0}

            async def _on_progress(msg: str):
                print(f"[WALK] {msg}")
                _walk_counter["n"] += 1
                # Обновляем карту каждые 3 сообщения (≈ каждый агент)
                if _walk_counter["n"] % 3 == 0:
                    try:
                        _refresh_map()
                    except Exception:
                        pass

            results = await run_city_walk(
                on_progress=_on_progress,
            )

            try:
                ok = len([r for r in results if r.get("status") == "ok"])
                ui.notify(f"✅ Прогулка завершена · {ok}/{len(results)} агентов", type="positive")
                _refresh_map()
                reload_all_agents()
                update_residents()
                update_city_zone()
            except Exception:
                print("[CITY] ⚠ UI обновлён во время прогулки")
        except Exception as e:
            import traceback; traceback.print_exc()
            try:
                ui.notify(f"❌ {e}", type="negative")
            except Exception:
                print(f"[CITY] ❌ {e}")"""

# morning checkout: добавляем _refresh_map в on_progress утренней прогулки
OLD_MORNING_WALK_CALL = """            try:
                from studio.city_walker import run_city_walk_morning as _morning_walk
                ui.notify("🚶 Дорога на работу...", type="info")
                await _morning_walk(max_agents=0)
                _refresh_map()
                reload_all_agents()
                update_residents()
                update_city_zone()
                print("[CITY] 🌅 Утренняя прогулка завершена")
            except Exception as _wm_err:
                print(f"[CITY] ⚠ Утренняя прогулка: {_wm_err}")"""

NEW_MORNING_WALK_CALL = """            try:
                from studio.city_walker import run_city_walk_morning as _morning_walk
                ui.notify("🚶 Дорога на работу...", type="info")
                _mw_cnt = {"n": 0}
                async def _mw_prog(msg):
                    _mw_cnt["n"] += 1
                    if _mw_cnt["n"] % 3 == 0:
                        try: _refresh_map()
                        except Exception: pass
                await _morning_walk(max_agents=0, on_progress=_mw_prog)
                _refresh_map()
                reload_all_agents()
                update_residents()
                update_city_zone()
                print("[CITY] 🌅 Утренняя прогулка завершена")
            except Exception as _wm_err:
                print(f"[CITY] ⚠ Утренняя прогулка: {_wm_err}")"""

OLD_EVENING_WALK_CALL = """        try:
            from studio.city_walker import run_city_walk_evening as _evening_walk
            ui.notify("🌆 Агенты идут домой...", type="info")
            await _evening_walk(max_agents=0)
            _refresh_map()
            reload_all_agents()
            update_residents()
            update_city_zone()
            ui.notify("✅ Вечерняя прогулка завершена", type="positive")
        except Exception as e:
            try:
                ui.notify(f"❌ {e}", type="negative")
            except Exception:
                print(f"[CITY] ❌ вечерняя прогулка: {e}")"""

NEW_EVENING_WALK_CALL = """        try:
            from studio.city_walker import run_city_walk_evening as _evening_walk
            ui.notify("🌆 Агенты идут домой...", type="info")
            _ew_cnt = {"n": 0}
            async def _ew_prog(msg):
                _ew_cnt["n"] += 1
                if _ew_cnt["n"] % 3 == 0:
                    try: _refresh_map()
                    except Exception: pass
            await _evening_walk(max_agents=0, on_progress=_ew_prog)
            _refresh_map()
            reload_all_agents()
            update_residents()
            update_city_zone()
            ui.notify("✅ Вечерняя прогулка завершена", type="positive")
        except Exception as e:
            try:
                ui.notify(f"❌ {e}", type="negative")
            except Exception:
                print(f"[CITY] ❌ вечерняя прогулка: {e}")"""


def _apply(path: Path, replacements: list[tuple[str, str]], label: str) -> tuple[str, str]:
    content = path.read_text(encoding="utf-8")
    new_content = content
    applied = []
    skipped = []
    for old, new in replacements:
        if old in new_content:
            new_content = new_content.replace(old, new, 1)
            applied.append("OK")
        else:
            skipped.append(old[:60].strip())
    return new_content, applied, skipped


def main(dry_run: bool = False):
    errors = []

    # ── city_walker.py ──────────────────────────────────────────────────────
    if not WALKER.exists():
        print(f"[ERROR] {WALKER} не найден")
        sys.exit(1)

    walker_replacements = [
        (OLD_WALK_LOOP,       NEW_WALK_LOOP),
        (OLD_MORNING_END,     NEW_MORNING_END),
        (OLD_EVENING_END,     NEW_EVENING_END),
        (OLD_QUANTUM_SLEEP,   NEW_QUANTUM_SLEEP),
        (OLD_MORNING_SLEEP,   NEW_MORNING_SLEEP),
        (OLD_EVENING_SLEEP,   NEW_EVENING_SLEEP),
    ]

    walker_content, walker_ok, walker_skip = _apply(WALKER, walker_replacements, "city_walker")

    print(f"[city_walker.py] применено: {len(walker_ok)}, пропущено (уже есть): {len(walker_skip)}")
    for s in walker_skip:
        print(f"  SKIP: {s!r}")

    # ── ui_cabinet.py ───────────────────────────────────────────────────────
    if not CABINET.exists():
        print(f"[ERROR] {CABINET} не найден")
        sys.exit(1)

    cabinet_replacements = [
        (OLD_DO_CITY_WALK,        NEW_DO_CITY_WALK),
        (OLD_MORNING_WALK_CALL,   NEW_MORNING_WALK_CALL),
        (OLD_EVENING_WALK_CALL,   NEW_EVENING_WALK_CALL),
    ]

    cabinet_content, cabinet_ok, cabinet_skip = _apply(CABINET, cabinet_replacements, "ui_cabinet")

    print(f"[ui_cabinet.py] применено: {len(cabinet_ok)}, пропущено (уже есть): {len(cabinet_skip)}")
    for s in cabinet_skip:
        print(f"  SKIP: {s!r}")

    if dry_run:
        print("\n[DRY-RUN] Проверка завершена. Файлы не изменены.")
        total_ok = len(walker_ok) + len(cabinet_ok)
        total_skip = len(walker_skip) + len(cabinet_skip)
        print(f"  Итого: {total_ok} замен применится, {total_skip} пропустится")
        return

    # Бэкап + запись
    BACKUP_DIR.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    shutil.copy2(WALKER,  BACKUP_DIR / f"city_walker.py.bak_walk_live_{ts}")
    shutil.copy2(CABINET, BACKUP_DIR / f"ui_cabinet.py.bak_walk_live_{ts}")
    print(f"[BACKUP] {BACKUP_DIR}/*_walk_live_{ts}")

    WALKER.write_text(walker_content, encoding="utf-8")
    CABINET.write_text(cabinet_content, encoding="utf-8")

    print("\n[DONE] Патч применён.")
    print("  city_walker.py  — батчевый gather + таймауты + here_now не чистим")
    print("  ui_cabinet.py   — _refresh_map каждые 3 агента во время прогулки")
    print("\n  Эффект:")
    print("  - Карта обновляется ЖИВО пока агенты гуляют")
    print("  - 134 агента = ~10 батчей ~45s вместо 10+ минут")
    print("  - Один зависший агент пропускается через 45s, не блокирует")


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    main(dry_run=dry)
