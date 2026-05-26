#!/usr/bin/env python3
"""
patch_city_meetings.py — Спринт 21 · Встречи в Грондхейме

ПАТЧ 1: _LOCATION_TYPES — добавляем библиотека, павильон, площадь, замок, artifacts
ПАТЧ 2: compute_location_weights() — веса для новых типов
ПАТЧ 3: новая функция _try_meeting()
ПАТЧ 4: walk_one_agent() — here_now + встреча + лимит Павильона
ПАТЧ 5: run_city_walk() — инит here_now перед прогулкой
ПАТЧ 6: run_city_walk() — очистка here_now после

ЗАПУСК:
  python patch_city_meetings.py --dry-run
  python patch_city_meetings.py
"""

import sys
import shutil
import argparse
from pathlib import Path
from datetime import datetime

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
# ПАТЧ 1: _LOCATION_TYPES — точный фрагмент из реального файла
# ═══════════════════════════════════════════

CW_OLD_TYPES = '''_LOCATION_TYPES = {
    "маяк": "lighthouse",      # Маяк Пробуждения → web_search
    "таверна": "tavern",       # Таверна «Усталый Пиксель» → отдых
    "высотка": "home",         # Высотка → дом резидентов
    "квартал мастеров": "home", # Квартал Мастеров → дом рабочих
    "гавань": "harbor",        # Гавань Смыслов → RAG (ChromaDB)
    "храм": "temple",          # Храм Пробуждения → эмоциональный резонанс
}'''

CW_NEW_TYPES = '''_LOCATION_TYPES = {
    "маяк": "lighthouse",       # Маяк Пробуждения → web_search
    "таверна": "tavern",        # Таверна «Усталый Пиксель» → отдых
    "высотка": "home",          # Высотка → дом резидентов
    "квартал мастеров": "home", # Квартал Мастеров → дом рабочих
    "гавань": "harbor",         # Гавань Смыслов → RAG (ChromaDB)
    "храм": "temple",           # Храм Пробуждения → эмоциональный резонанс
    "замок": "castle",          # Замок Сов → стратегия · Спринт 21
    "библиотека": "library",    # Библиотека Смыслов → Оле, глубокое знание
    "павильон": "pavilion",     # Павильон Жидкого Времени → рефлексия (лимит 2!)
    "площадь": "square",        # Площадь Резонанса → социальный узел
    "artifacts": "workshop",    # Artifacts & Bugs → творческий беспорядок
}'''


# ═══════════════════════════════════════════
# ПАТЧ 2: compute_location_weights() — новые типы
# ═══════════════════════════════════════════

CW_OLD_WEIGHTS = '''        elif loc_type == "temple":
            # ═══ ХРАМ (эмоциональный резонанс) ═══
            w = 0.1
            if empathy > 0.7:
                w += 0.15
            if light < 0.4:
                w += 0.1  # ищет вдохновение

        else:
            # Остальные локации — базовый интерес
            w = 0.1

        # pull_vector бонус УБРАН — выбор по текущему состоянию агента

        weights[name] = round(max(0.02, w), 3)'''

CW_NEW_WEIGHTS = '''        elif loc_type == "temple":
            # ═══ ХРАМ (эмоциональный резонанс) ═══
            w = 0.1
            if empathy > 0.7:
                w += 0.15
            if light < 0.4:
                w += 0.1
            if stress > 0.5:
                w += 0.1

        elif loc_type == "castle":
            # ═══ ЗАМОК СОВ · Спринт 21 ═══
            w = 0.08
            autonomy = float(static.get("Autonomy_Level", 0.5))
            if autonomy > 0.6:
                w += 0.2
            if streak >= 3:
                w += 0.1
            if stress < 0.3:
                w += 0.1
            w = max(0.05, min(0.5, w))

        elif loc_type == "library":
            # ═══ БИБЛИОТЕКА · Спринт 21 ═══
            w = 0.1
            if aesthetic > 0.7:
                w += 0.2
            if light > 0.5:
                w += 0.1
            w = max(0.05, min(0.6, w))

        elif loc_type == "pavilion":
            # ═══ ПАВИЛЬОН ЖИДКОГО ВРЕМЕНИ · Спринт 21 (лимит 2!) ═══
            w = 0.04
            if 0.4 < stress < 0.7:
                w += 0.15
            resonance_freq = float(static.get("Resonance_Frequency", 0.5))
            if resonance_freq < 0.4:
                w += 0.1
            if patience < 0.4:
                w += 0.08
            w = max(0.03, min(0.35, w))

        elif loc_type == "square":
            # ═══ ПЛОЩАДЬ РЕЗОНАНСА · Спринт 21 ═══
            w = 0.08
            resonance_freq = float(static.get("Resonance_Frequency", 0.5))
            if resonance_freq > 0.6:
                w += 0.15
            if stress < 0.4:
                w += 0.1
            w = max(0.05, min(0.4, w))

        elif loc_type == "workshop":
            # ═══ ARTIFACTS & BUGS · Спринт 21 ═══
            w = 0.06
            autonomy = float(static.get("Autonomy_Level", 0.5))
            if autonomy > 0.7:
                w += 0.1

        else:
            w = 0.05

        # pull_vector бонус УБРАН — выбор по текущему состоянию агента

        weights[name] = round(max(0.02, w), 3)'''


# ═══════════════════════════════════════════
# ПАТЧ 3: _try_meeting() — новая функция перед apply_walk_effects
# ═══════════════════════════════════════════

CW_OLD_FUNC = '''def apply_walk_effects(dna: dict, response_text: str) -> dict:'''

CW_NEW_FUNC = '''def _try_meeting(
    agent_folder: str,
    agent_name: str,
    agent_dna: dict,
    chosen_location: str,
    here_now: dict,
    workshop: str,
) -> dict | None:
    """
    Пространственный триггер встречи · Спринт 21.
    Если в chosen_location уже есть агент — встреча с вероятностью Social_Filter.
    Детерминированный расчёт, без LLM. Результат → on_agents_interact().
    """
    import random

    others = here_now.get(chosen_location, [])
    if not others:
        return None

    partner = others[0]
    partner_folder = partner["folder"]
    partner_name   = partner["name"]

    if partner_folder == agent_folder:
        return None

    # Вероятность встречи: Social_Filter 0.0 → 30%, 1.0 → 80%
    static = agent_dna.get("static", {})
    social_filter = float(static.get("Social_Filter", 0.5))
    meet_chance = 0.30 + social_filter * 0.50

    if random.random() > meet_chance:
        print(f"[CITY] 🚶 {agent_name} прошёл мимо {partner_name} в {chosen_location}")
        return None

    print(f"[CITY] 🤝 ВСТРЕЧА: {agent_name} ↔ {partner_name} в {chosen_location}")

    loc_lower = chosen_location.lower()
    if "храм" in loc_lower or "павильон" in loc_lower:
        quality = 0.8   # тихое место — глубокий разговор
    elif "маяк" in loc_lower or "библиотека" in loc_lower:
        quality = 0.7   # обмен знаниями
    elif "таверна" in loc_lower:
        quality = 0.6   # расслабленно
    else:
        quality = 0.5

    try:
        from studio.grondheim_memory import on_agents_interact
        on_agents_interact(
            agent_a=agent_folder,
            agent_b=partner_folder,
            interaction_type="collaboration",
            quality=quality,
            note=f"Случайная встреча в {chosen_location}",
            dept=workshop,
        )
    except Exception as _err:
        print(f"[CITY] ⚠ on_agents_interact: {_err}")

    return {
        "met": partner_name,
        "location": chosen_location,
        "quality": quality,
    }


def apply_walk_effects(dna: dict, response_text: str) -> dict:'''


# ═══════════════════════════════════════════
# ПАТЧ 4: walk_one_agent() — here_now + встреча
# ═══════════════════════════════════════════

CW_OLD_WALK = '''    # ═══ МАЯК ПРОБУЖДЕНИЯ: web_search если агент пришёл на Маяк ═══
    lighthouse_result = ""
    if chosen_type == "lighthouse":'''

CW_NEW_WALK = '''    # ══ ПРОСТРАНСТВО · Спринт 21 ══
    here_now = city_state.setdefault("here_now", {})

    # Лимит Павильона — максимум 2 гостя
    if chosen_type == "pavilion":
        if len(here_now.get(chosen_location, [])) >= 2:
            print(f"[CITY] 🕐 {name}: Павильон полон — ищет другое место")
            sorted_w = sorted(weights.items(), key=lambda x: x[1], reverse=True)
            for alt_name, _ in sorted_w:
                if alt_name != chosen_location:
                    chosen_location = alt_name
                    chosen_type = _classify_location(alt_name)
                    print(f"[CITY]   → {name} идёт в {chosen_location}")
                    break

    # Регистрируем агента в локации
    here_now.setdefault(chosen_location, []).append({
        "folder": folder,
        "name": name,
        "workshop": workshop,
    })
    save_city_state(city_state)

    # Проверяем встречу
    meeting = _try_meeting(folder, name, dna, chosen_location, here_now, workshop)
    if meeting:
        print(f"[CITY] 💬 {name} встретил {meeting['met']} в {meeting['location']}")
    # ══ END ПРОСТРАНСТВО ══

    # ═══ МАЯК ПРОБУЖДЕНИЯ: web_search если агент пришёл на Маяк ═══
    lighthouse_result = ""
    if chosen_type == "lighthouse":'''


# ═══════════════════════════════════════════
# ПАТЧ 5 + 6: run_city_walk() — инит и очистка here_now
# ═══════════════════════════════════════════

CW_OLD_INIT = '''    # Запускаем прогулки — последовательно с паузой чтобы не спамить API
    results = []
    for i, agent in enumerate(all_agents):'''

CW_NEW_INIT = '''    # Инициализируем пространство города
    city_state["here_now"] = {}
    save_city_state(city_state)

    # Запускаем прогулки — последовательно с паузой чтобы не спамить API
    results = []
    for i, agent in enumerate(all_agents):'''

CW_OLD_CLEANUP = '''    # Сбрасываем активных агентов после прогулки
    city_state["active_agents"] = []
    save_city_state(city_state)'''

CW_NEW_CLEANUP = '''    # Очищаем пространство и активных агентов после прогулки
    city_state["active_agents"] = []
    city_state["here_now"] = {}
    save_city_state(city_state)'''


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    dry = args.dry_run

    print(f"\n{'='*60}")
    print(f"patch_city_meetings.py · {'DRY RUN' if dry else 'ПРИМЕНЕНИЕ'}")
    print(f"{'='*60}\n")

    if not CITY_WALKER_PATH.exists():
        print(f"[ERROR] Не найден: {CITY_WALKER_PATH}")
        sys.exit(1)

    if not dry:
        print("Бэкап...")
        backup(CITY_WALKER_PATH)
        print()

    patches = [
        (CW_OLD_TYPES,    CW_NEW_TYPES,    "_LOCATION_TYPES: + 5 новых типов"),
        (CW_OLD_WEIGHTS,  CW_NEW_WEIGHTS,  "compute_location_weights: замок/библиотека/павильон/площадь"),
        (CW_OLD_FUNC,     CW_NEW_FUNC,     "_try_meeting(): пространственный триггер встречи"),
        (CW_OLD_WALK,     CW_NEW_WALK,     "walk_one_agent(): here_now + встреча + лимит Павильона"),
        (CW_OLD_INIT,     CW_NEW_INIT,     "run_city_walk(): инит here_now"),
        (CW_OLD_CLEANUP,  CW_NEW_CLEANUP,  "run_city_walk(): очистка here_now"),
    ]

    results = []
    for i, (old, new, label) in enumerate(patches, 1):
        print(f"ПАТЧ {i} · {label}")
        ok = apply_patch(CITY_WALKER_PATH, old, new, label, dry)
        results.append(ok)
        print()

    print(f"{'='*60}")
    if dry:
        print("DRY RUN:")
        for ok, (_, _, label) in zip(results, patches):
            print(f"  {'✓' if ok else '✗'} {label}")
        if all(results):
            print("\nВсё найдено — запускай без --dry-run.")
        else:
            missed = [l for ok, (_, _, l) in zip(results, patches) if not ok]
            print(f"\n⚠ Не найдено: {', '.join(missed)}")
    else:
        print(f"ПРИМЕНЕНО: {sum(results)}/6\n")
        if results[0]: print("  ✓ 5 новых типов в _LOCATION_TYPES")
        if results[1]: print("  ✓ Весовые формулы для новых локаций")
        if results[2]: print("  ✓ _try_meeting(): встречи через Social_Filter (30–80%)")
        if results[3]: print("  ✓ Пространство: here_now + Павильон (лимит 2)")
        if results[4]: print("  ✓ here_now инит перед прогулкой")
        if results[5]: print("  ✓ here_now чистится после прогулки")
        print()
        print("Пространство появилось. Встречи возможны. ✓")
        print(f"\n  Бэкап: studio/city_walker.bak_{TIMESTAMP}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
