#!/usr/bin/env python3
# patch_city_walker_meetings.py
"""
Патч-хирург для studio/city_walker.py
Спринт 23 Блок Б · Подключение живых встреч.

ЧТО ДЕЛАЕТ:
  1. Создаёт бэкап city_walker.py.bak_meetings (если ещё нет)
  2. Заменяет тело функции _try_meeting() на новую версию,
     которая по Social_Filter решает встречаться или нет,
     и при встрече вызывает meeting.run_meeting().
  3. Старая логика (детерминированный update_emotional_weight)
     полностью заменена — теперь сам диалог даёт эмоциональный вес
     через _apply_meeting_aftermath() внутри meeting.py.

ЗАПУСК:
  python patch_city_walker_meetings.py

ОТКАТ:
  copy /Y studio\\city_walker.py.bak_meetings studio\\city_walker.py
"""

import sys
import shutil
from pathlib import Path

TARGET = Path("studio/city_walker.py")
BACKUP = Path("studio/city_walker.py.bak_meetings")

OLD_FUNCTION = '''def _try_meeting(
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
    }'''


NEW_FUNCTION = '''async def _try_meeting(
    agent_folder: str,
    agent_name: str,
    agent_dna: dict,
    chosen_location: str,
    here_now: dict,
    workshop: str,
    agent_profession: str = "",
) -> dict | None:
    """
    Пространственный триггер встречи · Спринт 23 Блок Б.
    Если в chosen_location уже есть агент — жребий по Social_Filter,
    и при выпадении — ЖИВОЙ диалог через meeting.run_meeting().

    Возвращает dict с описанием встречи (или None если не состоялась).
    """
    import random

    others = here_now.get(chosen_location, [])
    if not others:
        return None

    # Берём первого подходящего партнёра (не себя)
    partner = None
    for candidate in others:
        if candidate["folder"] != agent_folder:
            partner = candidate
            break
    if partner is None:
        return None

    partner_folder = partner["folder"]
    partner_name   = partner["name"]
    partner_dept   = partner.get("workshop", workshop)

    # Вероятность встречи: усреднённый Social_Filter обоих
    a_social = float(agent_dna.get("static", {}).get("Social_Filter", 0.5))
    partner_dna = load_dna(partner_dept, partner_folder)
    b_social = float(partner_dna.get("static", {}).get("Social_Filter", 0.5))
    avg_social = (a_social + b_social) / 2
    meet_chance = 0.30 + avg_social * 0.50

    if random.random() > meet_chance:
        print(f"[CITY] 🚶 {agent_name} прошёл мимо {partner_name} в {chosen_location}")
        return None

    # Резидент Павильона — лимит 2 уже соблюдён в walk_one_agent
    print(f"[CITY] 🤝 ВСТРЕЧА: {agent_name} ↔ {partner_name} в {chosen_location}")

    # Подгружаем профессии — нужны для голоса в meeting.py
    def _read_profession(dept: str, folder: str) -> str:
        info_path = MODULES_DIR / dept / folder / "info.json"
        if info_path.exists():
            try:
                info = json.loads(info_path.read_text(encoding="utf-8"))
                return info.get("profession") or info.get("role") or ""
            except Exception:
                return ""
        return ""

    agent_a_dict = {
        "folder":     agent_folder,
        "name":       agent_name,
        "dept":       workshop,
        "profession": agent_profession or _read_profession(workshop, agent_folder),
    }
    agent_b_dict = {
        "folder":     partner_folder,
        "name":       partner_name,
        "dept":       partner_dept,
        "profession": _read_profession(partner_dept, partner_folder),
    }

    # Загружаем city_state свежим — там лежит weather
    city_state = load_city_state()

    # Живой диалог
    try:
        from studio.meeting import run_meeting
        scene = await run_meeting(
            agent_a=agent_a_dict,
            agent_b=agent_b_dict,
            location=chosen_location,
            city_state=city_state,
        )
    except Exception as _err:
        print(f"[CITY] ⚠ run_meeting упал: {_err}")
        import traceback; traceback.print_exc()
        # Фоллбэк — детерминированный режим как было
        try:
            from studio.grondheim_memory import on_agents_interact
            on_agents_interact(
                agent_a=agent_folder, agent_b=partner_folder,
                interaction_type="collaboration", quality=0.4,
                note=f"Случайная встреча в {chosen_location} (фоллбэк)",
                dept=workshop,
            )
        except Exception:
            pass
        return {"met": partner_name, "location": chosen_location, "quality": 0.4}

    if scene is None:
        # Молча разошлись — это нормально, on_agents_interact уже отработал внутри
        return {"met": partner_name, "location": chosen_location,
                "quality": 0.15, "silent": True}

    inter = scene.get("interaction", {})
    return {
        "met":      partner_name,
        "location": chosen_location,
        "quality":  inter.get("quality", 0.5),
        "type":     inter.get("type", "collaboration"),
        "turns":    scene.get("total_turns", 0),
        "spoken":   scene.get("spoken_turns", 0),
    }'''


# Старая строка вызова в walk_one_agent — синхронный _try_meeting
OLD_CALL = '    meeting = _try_meeting(folder, name, dna, chosen_location, here_now, workshop)'
NEW_CALL = '    meeting = await _try_meeting(\n' \
           '        folder, name, dna, chosen_location, here_now, workshop,\n' \
           '        agent_profession=agent.get("Profession", ""),\n' \
           '    )'


def main() -> int:
    if not TARGET.exists():
        print(f"❌ Не найден {TARGET}")
        return 1

    src = TARGET.read_text(encoding="utf-8")

    # Идемпотентность — не патчим повторно
    if "Спринт 23 Блок Б" in src and "from studio.meeting import run_meeting" in src:
        print("✅ Уже пропатчен (Спринт 23 Блок Б). Выхожу.")
        return 0

    # Бэкап (только если ещё нет)
    if not BACKUP.exists():
        shutil.copy2(TARGET, BACKUP)
        print(f"📦 Бэкап создан: {BACKUP}")
    else:
        print(f"📦 Бэкап уже есть: {BACKUP} — не перезаписываю")

    # 1. Замена тела функции
    if OLD_FUNCTION not in src:
        print("❌ Не нашёл старую _try_meeting() — возможно файл уже изменён вручную.")
        print("   Проверь содержимое и при необходимости откати из бэкапа.")
        return 2

    src = src.replace(OLD_FUNCTION, NEW_FUNCTION)
    print("✅ Тело _try_meeting() заменено (теперь async + run_meeting)")

    # 2. Замена места вызова в walk_one_agent
    if OLD_CALL not in src:
        print("⚠ Не нашёл строку вызова _try_meeting(...) — возможно она уже async.")
        print("   Проверь walk_one_agent вручную.")
    else:
        src = src.replace(OLD_CALL, NEW_CALL)
        print("✅ Вызов _try_meeting заменён на await-форму")

    TARGET.write_text(src, encoding="utf-8")
    print(f"✅ {TARGET} обновлён")
    print()
    print("ДАЛЬШЕ:")
    print("  1. Убедись что studio/meeting.py лежит в studio/")
    print("  2. Запусти прогулку с 2-3 агентами в одном цехе:")
    print("     python -c \"import asyncio; from studio.city_walker import run_city_walk; "
          "asyncio.run(run_city_walk(workshops=['video_shorts'], max_agents=3))\"")
    print("  3. Смотри логи: должны появиться [MEETING] 🤝 и 💬")
    print("  4. Проверь studio/city_chronicles/ — там должны лечь .json файлы сцен")
    return 0


if __name__ == "__main__":
    sys.exit(main())
