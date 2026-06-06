"""
patch_map_timer.py
=================================================================
Два фикса:

1. ЖИВАЯ КАРТА через ui.timer — обновляется каждые 5 секунд
   автоматически, независимо от прогулки. Не нужен on_progress.
   Таймер запускается при инициализации кабинета и работает всегда.

2. ПРОГУЛКА БЕЗ ЗАВИСАНИЯ — max_agents=15 по умолчанию для кнопки
   🚶, ограничение квантов до 3 для вечерней прогулки.

Файл: studio/cabinet/ui_cabinet.py

Применение:
  python patch_map_timer.py [--dry-run]
"""

import sys
import shutil
from pathlib import Path
from datetime import datetime

TARGET = Path("studio/cabinet/ui_cabinet.py")
BACKUP_DIR = Path("_patch_backups")

# ─── Фикс 1: добавляем таймер после _refresh_map() в конце файла ─────────────

OLD_INIT_MAP = """        # Инициализация карты
        _refresh_map()

        # JS bridge: клик по агенту на карте → select_agent
        ui.on("cab-agent-select", lambda e: select_agent(
            e.args.get("id", ""), e.args.get("dept", "")
        ))"""

NEW_INIT_MAP = """        # Инициализация карты
        _refresh_map()

        # Автообновление карты каждые 5 секунд — живые перемещения
        ui.timer(5.0, _refresh_map)

        # JS bridge: клик по агенту на карте → select_agent
        ui.on("cab-agent-select", lambda e: select_agent(
            e.args.get("id", ""), e.args.get("dept", "")
        ))"""

# ─── Фикс 2: _do_city_walk — добавляем max_agents=15 ────────────────────────

OLD_CITY_WALK = """    async def _do_city_walk():
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

NEW_CITY_WALK = """    async def _do_city_walk():
        \"\"\"Запустить прогулку агентов (до 15 за раз — карта обновляется автоматом).\"\"\"
        try:
            from studio.city_walker import run_city_walk
            ui.notify("🚶 Агенты выходят в город...", type="info")
            results = await run_city_walk(max_agents=15)
            try:
                ok = len([r for r in results if r.get("status") == "ok"])
                ui.notify(f"✅ Прогулка: {ok}/{len(results)} агентов", type="positive")
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

# ─── Фикс 3: вечерняя прогулка — max_quanta=3 ───────────────────────────────

OLD_EVENING = """    async def _do_evening_walk():
        \"\"\"Вечерняя прогулка — цепочка квантов пока есть силы. · Спринт 24\"\"\"
        try:
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

NEW_EVENING = """    async def _do_evening_walk():
        \"\"\"Вечерняя прогулка — до 3 квантов на агента, карта живая.\"\"\"
        try:
            from studio.city_walker import run_city_walk_evening as _evening_walk
            ui.notify("🌆 Агенты идут домой...", type="info")
            await _evening_walk(max_agents=0, max_quanta=3)
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


def main(dry_run=False):
    if not TARGET.exists():
        print(f"[ERROR] {TARGET} не найден")
        sys.exit(1)

    content = TARGET.read_text(encoding="utf-8")

    fixes = [
        ("таймер карты",        OLD_INIT_MAP,    NEW_INIT_MAP),
        ("city_walk max_agents", OLD_CITY_WALK,   NEW_CITY_WALK),
        ("evening max_quanta",  OLD_EVENING,      NEW_EVENING),
    ]

    new_content = content
    for label, old, new in fixes:
        if old in new_content:
            new_content = new_content.replace(old, new, 1)
            print(f"  [OK] {label}")
        else:
            print(f"  [SKIP] {label} — уже применено или не найдено")

    if dry_run:
        print("\n[DRY-RUN] Файл не изменён.")
        return

    if new_content == content:
        print("\n[INFO] Нечего менять — все фиксы уже применены.")
        return

    BACKUP_DIR.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    shutil.copy2(TARGET, BACKUP_DIR / f"ui_cabinet.py.bak_map_timer_{ts}")
    print(f"\n[BACKUP] сохранён в {BACKUP_DIR}")

    TARGET.write_text(new_content, encoding="utf-8")
    print(f"[DONE] {TARGET} обновлён")
    print("\nЧто изменилось:")
    print("  · Карта обновляется каждые 5 сек автоматически (ui.timer)")
    print("  · Кнопка 🚶 прогулка: max_agents=15 (не все 145 сразу)")
    print("  · Кнопка 🌆 вечер: max_quanta=3 (не 17 кругов по Грондхейму)")
    print("\nДополнительно нужно в city_walker.py добавить max_quanta параметр")
    print("в run_city_walk_evening и walk_quantum_chain — см. patch_walk_quanta.py")


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    main(dry_run=dry)
