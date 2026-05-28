#!/usr/bin/env python3
"""
patch_fix_reports2.py
Убирает _hide_map() из кнопок день/ночь.
Добавляет restless в save_report ночного цикла.
"""
from pathlib import Path
from datetime import datetime

UI = Path("studio/cabinet/ui_cabinet.py")
code = UI.read_text(encoding="utf-8")
backup = UI.with_suffix(".py.bak_fix2")
backup.write_text(code, encoding="utf-8")
print(f"Бэкап: {backup.name}")

fixes = 0

# 1. Убираем _hide_map() из morning checkout
OLD1 = """            _hide_map()
            # Сохраняем отчёт
            try:
                from studio.daily_reports import save_report
                by_mode_save"""
NEW1 = """            # Сохраняем отчёт
            try:
                from studio.daily_reports import save_report
                by_mode_save"""
if OLD1 in code:
    code = code.replace(OLD1, NEW1, 1)
    print("✅ _hide_map убран из morning checkout")
    fixes += 1
else:
    print("ℹ morning _hide_map не найден")

# 2. Убираем _hide_map() из night cycle
OLD2 = """            _hide_map()
            reload_all_agents()
            update_residents()
            update_city_zone()

            # Сохраняем отчёт"""
NEW2 = """            reload_all_agents()
            update_residents()
            update_city_zone()

            # Сохраняем отчёт"""
if OLD2 in code:
    code = code.replace(OLD2, NEW2, 1)
    print("✅ _hide_map убран из night cycle")
    fixes += 1
else:
    print("ℹ night _hide_map не найден")

# 3. Добавляем restless в save_report ночного цикла
OLD3 = """                save_report("night", summary, {
                    "revolts":   revolts,
                    "resentful": resentful_save,
                })"""
NEW3 = """                restless_save = [
                    d.get("agent_name", k.split("_")[0])
                    for k, d in night_results.items()
                    if d.get("decision") == "RESTLESS"
                ]
                save_report("night", summary, {
                    "revolts":   revolts,
                    "resentful": resentful_save,
                    "restless":  restless_save,
                })"""
if OLD3 in code:
    code = code.replace(OLD3, NEW3, 1)
    print("✅ restless добавлен в save_report")
    fixes += 1
else:
    print("ℹ restless уже есть или якорь не найден")

UI.write_text(code, encoding="utf-8")
print(f"\n{'✅ Готово' if fixes else '⚠ Ничего не изменилось'} ({fixes} фикса). Перезапусти студию.")
