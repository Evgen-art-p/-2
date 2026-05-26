#!/usr/bin/env python3
"""
patch_city_walker_memory.py — Спринт 21 · City Walker · Память и ДНК

ПРОБЛЕМЫ (аудит Брата + замечания Локи):

П1 · apply_walk_effects() пишет в dna.json напрямую через save_dna()
  - В обход sync_to_dna() → без логирования [SOUL]
  - Без учёта Empathy/Stubbornness из static ДНК
  - Эвристика по ключевым словам ("тихо", "красиво") — тот же пластик
    что мы выжгли в _apply_qa_feedback()

П1.Лока · Хард-лимит на walk_rest
  - Прогулка не должна быть чит-кодом для сброса стресса
  - Лимит: Stress -0.02 (мягче кабинета -0.03, нет живого разговора)
  - Фиксировано в EVENT_MAP sync_to_dna — intensity игнорируется

П2 · Два формата sensory_memory
  - city_walker: {date, location, feeling, weather}
  - grondheim_memory: {ts, type, content, emotional_weight, source, tags}
  - Унифицируем: city_walker → record_sensory_event()
  - Обратная совместимость: format_sensory_for_prompt() уже читает оба формата

ПАТЧИ:
  1. grondheim_memory.py → sync_to_dna(): добавляем "walk_rest" в elif
  2. city_walker.py → apply_walk_effects(): убираем, заменяем на sync_to_dna()
  3. city_walker.py → walk_one_agent(): сохраняем через record_sensory_event()

ЗАПУСК:
  python patch_city_walker_memory.py --dry-run
  python patch_city_walker_memory.py
"""

import sys
import shutil
import argparse
from pathlib import Path
from datetime import datetime

GRONDHEIM_PATH  = Path("studio/grondheim_memory.py")
CITY_WALKER_PATH = Path("studio/city_walker.py")
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")


def backup(path):
    bak = path.with_suffix(f".bak_{TIMESTAMP}")
    shutil.copy2(path, bak)
    print(f"  [BAK] {path} → {bak.name}")


def apply_patch(path, old, new, label, dry):
    text = path.read_text(encoding="utf-8")
    if old not in text:
        print(f"  [SKIP] {label} — не найден")
        return False
    if dry:
        print(f"  [DRY]  {label} — найден ✓")
        return True
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    print(f"  [OK]   {label}")
    return True


# ═══════════════════════════════════════════
# ПАТЧ 1: grondheim_memory.py
# Добавляем "walk_rest" в sync_to_dna()
# Хард-лимит Локи: Stress -0.02, Light +0.01
# Мягче кабинета (-0.03) — прогулка без живого разговора
# ═══════════════════════════════════════════

G_OLD = '''    elif event == "cabinet_chat":
        # Пластырь Кабинета · Спринт 21 · правила Локи
        # Фиксировано — intensity не влияет. Защита от водопада дофамина.
        # Полное восстановление только через streak ≥ 3 успешных ранов.
        stress   = max(0, stress   - 0.03)
        light    = min(1, light    + 0.02)
        patience = min(1, patience + 0.01)

    # ── Записываем обратно ──'''

G_NEW = '''    elif event == "cabinet_chat":
        # Пластырь Кабинета · Спринт 21 · правила Локи
        # Фиксировано — intensity не влияет. Защита от водопада дофамина.
        # Полное восстановление только через streak ≥ 3 успешных ранов.
        stress   = max(0, stress   - 0.03)
        light    = min(1, light    + 0.02)
        patience = min(1, patience + 0.01)

    elif event == "walk_rest":
        # Прогулка по городу · Спринт 21 · хард-лимит Локи
        # Мягче кабинета: нет живого разговора с Архитектором.
        # Фиксировано — intensity игнорируется. Прогулка не чит-код.
        # Полный сброс стресса только через streak ≥ 3 ранов — железное правило.
        stress   = max(0, stress   - 0.02)
        light    = min(1, light    + 0.01)
        patience = min(1, patience + 0.01)

    # ── Записываем обратно ──'''


# ═══════════════════════════════════════════
# ПАТЧ 2: city_walker.py
# apply_walk_effects() → заглушка + комментарий
# Эвристика по ключевым словам удалена
# ═══════════════════════════════════════════

CW_OLD_FUNC = '''def apply_walk_effects(dna: dict, response_text: str) -> dict:
    """
    Прогулка влияет на dynamic веса.
    Анализируем ответ LLM — нашёл ли агент что-то хорошее?
    Простая эвристика по ключевым словам.
    """
    dynamic = dna.get("dynamic", {})

    stress  = float(dynamic.get("Stress", 0.0))
    light   = float(dynamic.get("Internal_Light", 0.8))
    patience = float(dynamic.get("Patience", 1.0))

    text_lower = response_text.lower()

    # Позитивные сигналы → снижаем стресс, повышаем свет
    positive_words = ["тихо", "спокойно", "хорошо", "красиво", "отдохнул",
                      "нашёл", "понял", "улыбнулся", "тепло", "свет",
                      "радость", "покой", "вдохновение", "идея"]
    # Негативные сигналы → стресс растёт
    negative_words = ["тревога", "одиноко", "пусто", "холодно", "тяжело",
                      "устал", "беспокойство", "раздражение", "скучно"]

    pos_count = sum(1 for w in positive_words if w in text_lower)
    neg_count = sum(1 for w in negative_words if w in text_lower)

    # Базовый эффект прогулки — небольшое снижение стресса
    stress = max(0.0, stress - 0.05)
    light  = min(1.0, light + 0.03)

    # Корректировка по тону ответа
    if pos_count > neg_count:
        stress  = max(0.0, stress - 0.05)
        light   = min(1.0, light + 0.05)
        patience = min(1.0, patience + 0.03)
    elif neg_count > pos_count:
        stress = min(1.0, stress + 0.03)
        light  = max(0.0, light - 0.03)

    dynamic["Stress"]         = round(stress, 3)
    dynamic["Internal_Light"] = round(light, 3)
    dynamic["Patience"]       = round(patience, 3)
    dna["dynamic"] = dynamic
    return dna'''

CW_NEW_FUNC = '''def apply_walk_effects(dna: dict, response_text: str) -> dict:
    """
    УДАЛЕНО · Спринт 21.
    Эвристика по ключевым словам ("тихо", "красиво") — тот же пластик
    что _apply_qa_feedback(). ДНК меняется через sync_to_dna("walk_rest").
    Функция-заглушка для совместимости — не удалять (вызывается из walk_one_agent).
    """
    return dna  # DNA изменяется через sync_to_dna() ниже по коду'''


# ═══════════════════════════════════════════
# ПАТЧ 3: city_walker.py → walk_one_agent()
# Заменяем apply_walk_effects + save_dna
# на sync_to_dna("walk_rest") + record_sensory_event()
# ═══════════════════════════════════════════

CW_OLD_CALL = '''    # Обновляем dna.json dynamic
    dna = apply_walk_effects(dna, response)
    save_dna(workshop, folder, dna)'''

CW_NEW_CALL = '''    # ── ДНК: прогулка через единый канал · Спринт 21 ──
    # Хард-лимит Локи: walk_rest = Stress-0.02, Light+0.01 (фиксировано в EVENT_MAP).
    # Не чит-код — мягче кабинета, без живого разговора с Архитектором.
    try:
        from studio.grondheim_memory import sync_to_dna as _sync_dna
        _sync_dna(folder, "walk_rest", intensity=1.0, dept=workshop)
        print(f"[CITY] 🧬 {name}: walk_rest → DNA (Stress-0.02)")
    except Exception as _dna_err:
        print(f"[CITY] ⚠ DNA не обновлена: {_dna_err}")'''


# ═══════════════════════════════════════════
# ПАТЧ 4: city_walker.py → walk_one_agent()
# sensory entry: унифицируем через record_sensory_event()
# Убираем старый формат {date, location, feeling, weather}
# ═══════════════════════════════════════════

CW_OLD_SENSORY = '''    # Сохраняем в sensory_memory
    entry = {
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "location": chosen_location,
        "feeling": response[:300],
        "weather": city_state.get("weather", ""),
    }

    # Если был на Маяке — добавляем отдельную запись с тегом
    if lighthouse_result:
        entry["tags"] = ["маяк", "web_search", "тренды"]
        # Дополнительная запись — Рюкзак Знаний
        lighthouse_entry = {
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "location": "Маяк Пробуждения",
            "feeling": f"[ЧИСТЫЙ СМЫСЛ] {lighthouse_result}",
            "weather": city_state.get("weather", ""),
            "tags": ["маяк", "чистый_смысл", "web_search"],
        }
        memory.setdefault("entries", []).append(lighthouse_entry)

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

    memory.setdefault("entries", []).append(entry)

    # Оставляем только последние 30 записей
    memory["entries"] = memory["entries"][-30:]
    memory["last_location"] = chosen_location
    save_sensory_memory(workshop, folder, memory)'''

CW_NEW_SENSORY = '''    # ── Память прогулки: единый формат · Спринт 21 ──
    # Переводим на record_sensory_event() — унификация двух форматов.
    # Обратная совместимость: format_sensory_for_prompt() читает оба формата.
    try:
        from studio.grondheim_memory import record_sensory_event as _rse
        weather_note = city_state.get("weather", "")

        # Основная запись прогулки
        _rse(
            agent_id=folder,
            content=f"[{chosen_location}] {response[:250]}",
            event_type="location",
            source="city_walker",
            tags=["прогулка", chosen_location.lower()[:20]],
            emotional_weight=0.4,
            dept=workshop,
        )

        # Маяк — отдельная запись с тегом чистый_смысл
        if lighthouse_result:
            _rse(
                agent_id=folder,
                content=f"[ЧИСТЫЙ СМЫСЛ] {lighthouse_result}",
                event_type="location",
                source="city_walker",
                tags=["маяк", "чистый_смысл", "web_search"],
                emotional_weight=0.7,
                dept=workshop,
            )

        # Гавань — отдельная запись
        if harbor_result:
            _rse(
                agent_id=folder,
                content=f"[НАЙДЕННЫЙ СМЫСЛ] {harbor_result}",
                event_type="location",
                source="city_walker",
                tags=["гавань", "найденный_смысл", "rag"],
                emotional_weight=0.6,
                dept=workshop,
            )

        # last_location обновляем вручную (record_sensory_event не делает это)
        _mem = load_sensory_memory(workshop, folder)
        _mem["last_location"] = chosen_location
        save_sensory_memory(workshop, folder, _mem)

    except Exception as _mem_err:
        # Фоллбэк: старый формат если grondheim_memory недоступен
        print(f"[CITY] ⚠ record_sensory_event недоступен: {_mem_err}")
        entry = {
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "location": chosen_location,
            "feeling": response[:300],
            "weather": city_state.get("weather", ""),
        }
        if lighthouse_result:
            memory.setdefault("entries", []).append({
                "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "location": "Маяк Пробуждения",
                "feeling": f"[ЧИСТЫЙ СМЫСЛ] {lighthouse_result}",
                "tags": ["маяк", "чистый_смысл", "web_search"],
            })
        if harbor_result:
            memory.setdefault("entries", []).append({
                "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "location": "Гавань Смыслов",
                "feeling": f"[НАЙДЕННЫЙ СМЫСЛ] {harbor_result}",
                "tags": ["гавань", "найденный_смысл", "rag"],
            })
        memory.setdefault("entries", []).append(entry)
        memory["entries"] = memory["entries"][-30:]
        memory["last_location"] = chosen_location
        save_sensory_memory(workshop, folder, memory)'''


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    dry = args.dry_run

    print(f"\n{'='*60}")
    print(f"patch_city_walker_memory.py · {'DRY RUN' if dry else 'ПРИМЕНЕНИЕ'}")
    print(f"{'='*60}\n")

    for p in [GRONDHEIM_PATH, CITY_WALKER_PATH]:
        if not p.exists():
            print(f"[ERROR] Не найден: {p}")
            sys.exit(1)

    if not dry:
        print("Бэкапы...")
        backup(GRONDHEIM_PATH)
        backup(CITY_WALKER_PATH)
        print()

    print("ПАТЧ 1 · grondheim_memory.py: walk_rest в sync_to_dna()")
    ok1 = apply_patch(GRONDHEIM_PATH, G_OLD, G_NEW,
                      "sync_to_dna: elif walk_rest (Stress-0.02, хард-лимит)", dry)
    print()

    print("ПАТЧ 2 · city_walker.py: apply_walk_effects() → заглушка")
    ok2 = apply_patch(CITY_WALKER_PATH, CW_OLD_FUNC, CW_NEW_FUNC,
                      "apply_walk_effects(): эвристика ключевых слов → pass", dry)
    print()

    print("ПАТЧ 3 · city_walker.py: вызов → sync_to_dna(walk_rest)")
    ok3 = apply_patch(CITY_WALKER_PATH, CW_OLD_CALL, CW_NEW_CALL,
                      "walk_one_agent(): apply_walk_effects → sync_to_dna", dry)
    print()

    print("ПАТЧ 4 · city_walker.py: sensory → record_sensory_event()")
    ok4 = apply_patch(CITY_WALKER_PATH, CW_OLD_SENSORY, CW_NEW_SENSORY,
                      "walk_one_agent(): старый формат → единый record_sensory_event", dry)
    print()

    applied = [ok1, ok2, ok3, ok4]
    labels  = ["walk_rest в sync_to_dna", "apply_walk_effects заглушка",
               "вызов sync_to_dna", "унификация sensory"]

    print(f"{'='*60}")
    if dry:
        print("DRY RUN:")
        for ok, label in zip(applied, labels):
            print(f"  {'✓' if ok else '✗'} {label}")
        all_ok = all(applied)
        if all_ok:
            print("\nВсё найдено — запускай без --dry-run.")
        else:
            missed = [l for ok, l in zip(applied, labels) if not ok]
            print(f"\n⚠ Не найдено: {', '.join(missed)}")
    else:
        print(f"ПРИМЕНЕНО: {sum(applied)}/4\n")
        if ok1:
            print("  ✓ walk_rest: Stress-0.02 / Light+0.01 (хард-лимит, intensity игнор.)")
        if ok2:
            print("  ✓ apply_walk_effects(): эвристика слов удалена → заглушка")
        if ok3:
            print("  ✓ walk_one_agent(): ДНК через sync_to_dna() с логом [SOUL]")
        if ok4:
            print("  ✓ sensory: единый формат через record_sensory_event()")
        print()
        print("Математика прогулки:")
        print("  walk_rest:    Stress -0.02 / Light +0.01 / Patience +0.01")
        print("  cabinet_chat: Stress -0.03 / Light +0.02 / Patience +0.01")
        print("  streak≥3:     Stress → 0.0  (в 15x мощнее прогулки)")
        print()
        print("Прогулка — свежий воздух. Кабинет — разговор с Архитектором.")
        print("Recovery — только через работу. Иерархия соблюдена. ✓")
        print()
        print(f"  Бэкапы: *.bak_{TIMESTAMP}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
