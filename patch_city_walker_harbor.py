"""
patch_city_walker_harbor.py — Добавляет визит в Гавань Смыслов в city_walker.py
═══════════════════════════════════════════════════════════════════════════════

Ищет блок после Маяка (lighthouse_result) и добавляет аналогичный для Гавани.
Бэкап: city_walker.py.bak_harbor

Использование:
  python patch_city_walker_harbor.py
  python patch_city_walker_harbor.py studio/city_walker.py
"""

import sys
import shutil
from pathlib import Path


def patch_file(filepath: str = None):
    if filepath:
        walker_path = Path(filepath)
    else:
        candidates = [
            Path("studio/city_walker.py"),
            Path("city_walker.py"),
        ]
        walker_path = None
        for c in candidates:
            if c.exists():
                walker_path = c
                break
        if not walker_path:
            print("❌ Не найден city_walker.py!")
            sys.exit(1)

    print(f"📁 Файл: {walker_path}")
    source = walker_path.read_text(encoding="utf-8")
    original_len = len(source)

    # ═══════════════════════════════════════════════════════
    # ПАТЧ 1: Добавить тип "harbor" в _LOCATION_TYPES
    # ═══════════════════════════════════════════════════════

    OLD_TYPES = '''    "гавань": "library",       # Гавань Смыслов → внутренняя библиотека (RAG)'''
    NEW_TYPES = '''    "гавань": "harbor",        # Гавань Смыслов → RAG (ChromaDB)'''

    if OLD_TYPES in source:
        source = source.replace(OLD_TYPES, NEW_TYPES, 1)
        print("✅ Патч 1: _LOCATION_TYPES гавань → harbor")
    elif '"harbor"' in source and '"гавань"' in source:
        print("⏭  Патч 1: уже применён")
    else:
        print("⚠️  Патч 1: блок не найден")

    # ═══════════════════════════════════════════════════════
    # ПАТЧ 2: Обновить compute_location_weights для harbor
    # ═══════════════════════════════════════════════════════

    OLD_LIBRARY = '''        elif loc_type == "library":
            # ═══ ГАВАНЬ СМЫСЛОВ (внутренняя библиотека) ═══
            w = 0.15
            if aesthetic > 0.6:
                w += 0.1
            # Если стресс средний — идёт осмыслять, а не за трендами
            if 0.3 < stress < 0.6:
                w += 0.1'''

    NEW_HARBOR = '''        elif loc_type == "harbor":
            # ═══ ГАВАНЬ СМЫСЛОВ (RAG — внутренняя мудрость) ═══
            days_since_harbor = _days_since_last_visit(memory, "harbor", locations)
            harbor_hunger = min(1.0, days_since_harbor / 5.0)  # голод быстрее чем Маяк
            w = harbor_hunger * 0.4
            if aesthetic > 0.6:
                w += 0.15
            # Средний стресс — осмысление, не поиск снаружи
            if 0.3 < stress < 0.6:
                w += 0.15
            # Высокий Light — хочет углубиться
            if light > 0.7:
                w += 0.1
            w = max(0.05, min(0.75, w))'''

    if OLD_LIBRARY in source:
        source = source.replace(OLD_LIBRARY, NEW_HARBOR, 1)
        print("✅ Патч 2: compute_location_weights harbor с голодом")
    elif 'loc_type == "harbor"' in source:
        print("⏭  Патч 2: уже применён")
    else:
        print("⚠️  Патч 2: блок library не найден")

    # ═══════════════════════════════════════════════════════
    # ПАТЧ 3: Добавить harbor_visit после блока Маяка в walk_one_agent
    # ═══════════════════════════════════════════════════════

    # Ищем конец блока Маяка — после него вставляем блок Гавани
    AFTER_LIGHTHOUSE = '''    # Сохраняем в sensory_memory
    entry = {
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "location": chosen_location,
        "feeling": response[:300],
        "weather": city_state.get("weather", ""),
    }'''

    HARBOR_BLOCK = '''    # ═══ ГАВАНЬ СМЫСЛОВ: RAG если агент пришёл в Гавань ═══
    harbor_result = ""
    if chosen_type == "harbor":
        try:
            from studio.harbor_of_meanings import harbor_visit as _harbor_visit, index_new_files

            # Инкрементальная индексация перед поиском
            index_new_files()

            print(f"[ГАВАНЬ] ⚓ {name} пришёл в Гавань Смыслов — активирую search_harbor")

            harbor_result = await _harbor_visit(
                agent_name=name,
                agent_profession=agent.get("Profession", ""),
                agent_dna=dna,
                system_prompt=system_prompt,
                temperature=agent_temp,
            )

        except ImportError:
            print(f"[ГАВАНЬ] ⚠️ harbor_of_meanings.py не найден — pip install chromadb")
            harbor_result = "Гавань была закрыта сегодня."
        except Exception as e:
            print(f"[ГАВАНЬ] ❌ {name}: ошибка в Гавани — {e}")
            harbor_result = "Что-то помешало сосредоточиться в Гавани."

    # Сохраняем в sensory_memory
    entry = {
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "location": chosen_location,
        "feeling": response[:300],
        "weather": city_state.get("weather", ""),
    }'''

    if AFTER_LIGHTHOUSE in source and "harbor_result" not in source:
        source = source.replace(AFTER_LIGHTHOUSE, HARBOR_BLOCK, 1)
        print("✅ Патч 3: harbor_visit блок в walk_one_agent")
    elif "harbor_result" in source:
        print("⏭  Патч 3: уже применён")
    else:
        print("⚠️  Патч 3: точка вставки не найдена")

    # ═══════════════════════════════════════════════════════
    # ПАТЧ 4: Сохранение harbor_result в sensory_memory
    # (после блока сохранения lighthouse_entry)
    # ═══════════════════════════════════════════════════════

    AFTER_LIGHTHOUSE_ENTRY = '''        memory.setdefault("entries", []).append(lighthouse_entry)

    memory.setdefault("entries", []).append(entry)'''

    WITH_HARBOR_ENTRY = '''        memory.setdefault("entries", []).append(lighthouse_entry)

    # Запись Гавани в память (Найденный Смысл)
    if harbor_result:
        entry["tags"] = entry.get("tags", []) + ["гавань", "найденный_смысл"]
        harbor_entry = {
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "location": "Гавань Смыслов",
            "feeling": f"[НАЙДЕННЫЙ СМЫСЛ] {harbor_result}",
            "weather": city_state.get("weather", ""),
            "tags": ["гавань", "найденный_смысл", "rag"],
        }
        memory.setdefault("entries", []).append(harbor_entry)

    memory.setdefault("entries", []).append(entry)'''

    if AFTER_LIGHTHOUSE_ENTRY in source and "harbor_entry" not in source:
        source = source.replace(AFTER_LIGHTHOUSE_ENTRY, WITH_HARBOR_ENTRY, 1)
        print("✅ Патч 4: harbor_entry в sensory_memory")
    elif "harbor_entry" in source:
        print("⏭  Патч 4: уже применён")
    else:
        print("⚠️  Патч 4: точка вставки не найдена")

    # ═══════════════════════════════════════════════════════
    # ПАТЧ 5: Добавить harbor в result dict
    # ═══════════════════════════════════════════════════════

    OLD_RESULT = '''    if lighthouse_result:
        result["lighthouse"] = lighthouse_result

    return result'''

    NEW_RESULT = '''    if lighthouse_result:
        result["lighthouse"] = lighthouse_result
    if harbor_result:
        result["harbor"] = harbor_result

    return result'''

    if OLD_RESULT in source and 'result["harbor"]' not in source:
        source = source.replace(OLD_RESULT, NEW_RESULT, 1)
        print("✅ Патч 5: harbor в result dict")
    elif 'result["harbor"]' in source:
        print("⏭  Патч 5: уже применён")
    else:
        print("⚠️  Патч 5: точка вставки не найдена")

    # ═══════════════════════════════════════════════════════
    # СОХРАНЕНИЕ
    # ═══════════════════════════════════════════════════════

    if len(source) == original_len:
        print("\n⚠️ Ни один патч не применён. Файл не изменён.")
        sys.exit(1)

    backup_path = walker_path.with_suffix(".py.bak_harbor")
    if not backup_path.exists():
        shutil.copy2(walker_path, backup_path)
        print(f"\n💾 Бэкап: {backup_path}")

    walker_path.write_text(source, encoding="utf-8")
    delta = len(source) - original_len
    print(f"\n📝 Записано: {walker_path}")
    print(f"📏 Было: {original_len:,} → Стало: {len(source):,} (+{delta:,})")
    print(f"\n{'='*50}")
    print(f"✅ Гавань Смыслов подключена к city_walker!")
    print(f"{'='*50}")


if __name__ == "__main__":
    path_arg = sys.argv[1] if len(sys.argv) > 1 else None
    patch_file(path_arg)
