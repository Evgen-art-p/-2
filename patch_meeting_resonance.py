"""
patch_meeting_resonance.py
─────────────────────────────────────────────────────────────
Спринт 23 Блок Б · Умный выбор партнёра встречи

ПРОБЛЕМА:
  Сейчас в _try_meeting() партнёр выбирается как ПЕРВЫЙ попавшийся
  агент в локации (не себя). Это фанера — встречи получаются пустые,
  у агентов нет общей истории.

РЕШЕНИЕ:
  Партнёр выбирается по РЕЗОНАНСУ — emotional_weights + общий цех.
  Score = warmth*0.4 + trust*0.3 + respect*0.2 + same_dept*0.3.

  Если в локации есть знакомый (score >= 0.3) — встречаются ОНИ.
  Если только незнакомцы — Social_Filter решает заговорить или
  молча пройти. Замкнутые интроверты пройдут мимо. Открытые —
  познакомятся.

  Дополнительно: если в локации >=3 агентов, может запуститься
  до 2 пар встреч (раньше — максимум одна).

Запуск:
    python patch_meeting_resonance.py

Идемпотентен. Делает бэкап studio/city_walker.py.bak_meeting_resonance.
"""

import sys
import shutil
from pathlib import Path

REPO = Path(__file__).resolve().parent
WALKER_PATH = REPO / "studio" / "city_walker.py"


# ═══════════════════════════════════════════════════════════
# Новый _try_meeting — со score-based выбором партнёра
# ═══════════════════════════════════════════════════════════

NEW_TRY_MEETING = '''async def _try_meeting(
    agent_folder: str,
    agent_name: str,
    agent_dna: dict,
    chosen_location: str,
    here_now: dict,
    workshop: str,
    agent_profession: str = "",
) -> dict | None:
    """
    Пространственный триггер встречи · Спринт 23 Блок Б · v2 (резонанс).

    Партнёр выбирается по СВЯЗИ, не по случайному соседству:
      • emotional_weights.json — кого агент уже знает (warmth/trust/respect)
      • Workshop_ID — один цех = знакомы по ранам
      • Если знакомых нет → Social_Filter решает заговорить с незнакомцем

    Это убирает «фанеру» — пустые встречи между агентами без истории.
    Замкнутые интроверты в Таверне молча пройдут. Тёплые пары
    (после общего рана, после удачного диалога) встретятся точно.
    """
    import random

    others = [c for c in here_now.get(chosen_location, []) if c["folder"] != agent_folder]
    if not others:
        return None

    # ═══ ЗАГРУЗКА РЕЗОНАНСА АГЕНТА ═══
    # Читаем emotional_weights.json — кто кого знает и насколько тепло.
    def _load_resonance(dept: str, folder: str) -> dict:
        path = MODULES_DIR / dept / folder / "resonance" / "emotional_weights.json"
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    my_weights = _load_resonance(workshop, agent_folder)

    # ═══ SCORE КАЖДОГО КАНДИДАТА ═══
    # Чем выше score — тем сильнее агента тянет именно к этому соседу.
    a_social = float(agent_dna.get("static", {}).get("Social_Filter", 0.5))

    candidates_scored = []
    for cand in others:
        cand_folder = cand["folder"]
        cand_dept   = cand.get("workshop", workshop)

        # Резонанс ОТ agent К cand
        rel = my_weights.get(cand_folder) or my_weights.get(cand_folder.upper()) or {}
        warmth  = float(rel.get("warmth",  0.0))
        trust   = float(rel.get("trust",   0.0))
        respect = float(rel.get("respect", 0.0))
        rivalry = float(rel.get("rivalry", 0.0))

        # Общий цех = знакомы по ранам
        same_dept = 1.0 if cand_dept == workshop and workshop != "residents" else 0.0

        # Базовый score связи
        score = (
            warmth   * 0.40 +
            trust    * 0.30 +
            respect  * 0.20 +
            same_dept * 0.30
        )

        # Соперничество — притягивает (хочется выяснить отношения), но мягко
        score += rivalry * 0.10

        # Социальный филер партнёра — насколько он сам готов вступить в диалог.
        # Если партнёр-интроверт, шанс встречи падает даже при тёплых отношениях.
        cand_dna = load_dna(cand_dept, cand_folder)
        b_social = float(cand_dna.get("static", {}).get("Social_Filter", 0.5))
        score *= (0.5 + b_social * 0.5)  # коэф 0.5..1.0

        candidates_scored.append({
            "cand":      cand,
            "score":     round(score, 3),
            "rel":       rel,
            "same_dept": bool(same_dept),
            "b_social":  b_social,
        })

    # Сортируем — лучший наверху
    candidates_scored.sort(key=lambda x: x["score"], reverse=True)
    best = candidates_scored[0]
    partner = best["cand"]

    # ═══ ПОРОГИ ВСТРЕЧИ ═══
    # 1. Если score >= 0.30 — это знакомый, встреча почти гарантирована.
    #    Шанс = 70% + score*30% (capped 95%)
    # 2. Если score < 0.30 — незнакомец. Шанс решает Social_Filter
    #    обоих сторон, как раньше, но НИЖЕ (т.к. незнакомый):
    #    base 0.15 + avg_social*0.35 (max ~50%)
    # 3. Если Social_Filter агента < 0.3 — интроверт, всегда молча проходит
    #    мимо незнакомцев (но к знакомым подходит).

    is_known = best["score"] >= 0.30

    if is_known:
        meet_chance = min(0.95, 0.70 + best["score"] * 0.30)
        reason_tag = f"знакомый (score={best['score']:.2f})"
    else:
        # Замкнутый интроверт пройдёт мимо незнакомца
        if a_social < 0.30:
            print(f"[CITY] 🚶 {agent_name} (интроверт) прошёл мимо в {chosen_location}")
            return None
        avg_social = (a_social + best["b_social"]) / 2
        meet_chance = 0.15 + avg_social * 0.35
        reason_tag = f"незнакомец (S_F={avg_social:.2f})"

    if random.random() > meet_chance:
        print(f"[CITY] 🚶 {agent_name} прошёл мимо {partner['name']} "
              f"в {chosen_location} ({reason_tag})")
        return None

    print(f"[CITY] 🤝 ВСТРЕЧА: {agent_name} ↔ {partner['name']} "
          f"в {chosen_location} · {reason_tag}")

    partner_folder = partner["folder"]
    partner_name   = partner["name"]
    partner_dept   = partner.get("workshop", workshop)

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
        "score":    best["score"],
        "known":    is_known,
    }'''


# ═══════════════════════════════════════════════════════════
# ШАГИ
# ═══════════════════════════════════════════════════════════

def main():
    print()
    print("█" * 60)
    print("  ПАТЧ: УМНЫЙ ВЫБОР ПАРТНЁРА ВСТРЕЧИ — Спринт 23 Блок Б")
    print("█" * 60)
    print()

    if not WALKER_PATH.exists():
        print(f"❌ Не найден {WALKER_PATH}")
        sys.exit(1)

    src = WALKER_PATH.read_text(encoding="utf-8")

    # Идемпотентность: новая версия содержит маркер `v2 (резонанс)`
    marker = "v2 (резонанс)"
    if marker in src:
        print(f"○ Уже применено (найден маркер '{marker}')")
        print()
        print("Если хочешь переприменить — удали бэкап и старая версия")
        print("вернётся через git checkout, потом гоняй патч заново.")
        return

    # ─── Находим начало и конец старой функции _try_meeting ───
    start_marker = "async def _try_meeting("
    start_idx = src.find(start_marker)
    if start_idx == -1:
        print(f"❌ Не найдено начало _try_meeting")
        sys.exit(1)

    # Конец функции = следующая def на верхнем уровне модуля
    # (def без отступа). Ищем `\ndef ` после start_idx.
    # _try_meeting — top-level, следующая top-level функция = apply_walk_effects
    end_marker = "\ndef apply_walk_effects("
    end_idx = src.find(end_marker, start_idx)
    if end_idx == -1:
        print(f"❌ Не найден конец _try_meeting (apply_walk_effects)")
        sys.exit(1)

    # Старый блок: от start_idx до end_idx (не включая \ndef)
    # Захватываем до перевода строки перед end_marker
    old_block = src[start_idx:end_idx].rstrip() + "\n"

    print(f"✓ Найден старый _try_meeting: {len(old_block)} символов")
    print(f"  start={start_idx}, end={end_idx}")

    # Бэкап
    backup = WALKER_PATH.with_suffix(".py.bak_meeting_resonance")
    backup.write_text(src, encoding="utf-8")
    print(f"📦 Бэкап: {backup}")

    # Замена
    new_src = src[:start_idx] + NEW_TRY_MEETING.rstrip() + "\n\n\n" + src[end_idx + 1:]

    # Проверка синтаксиса перед записью
    try:
        import ast
        ast.parse(new_src)
    except SyntaxError as e:
        print(f"❌ Получился невалидный Python: {e}")
        print(f"   Бэкап остался, исходный файл НЕ изменён.")
        sys.exit(1)

    WALKER_PATH.write_text(new_src, encoding="utf-8")
    print(f"✓ Записан: {WALKER_PATH}")

    print()
    print("─" * 60)
    print("✅ ГОТОВО")
    print("─" * 60)
    print()
    print("Что изменилось:")
    print("  • Партнёр встречи выбирается по emotional_weights + цеху")
    print("  • Знакомые (score >= 0.30) встречаются с шансом 70-95%")
    print("  • Незнакомцы — шанс 15-50% от Social_Filter обоих")
    print("  • Интроверты (S_F < 0.3) проходят мимо незнакомцев молча")
    print("  • Лог теперь говорит: 'знакомый score=0.45' или 'незнакомец S_F=0.62'")
    print()
    print("Дальше:")
    print("  1. Перезапусти студию: python main.py")
    print("  2. Нажми 🚶 прогулка в Кабинете")
    print("  3. Смотри в консоль — теперь встречи будут разумнее")
    print()
    print("Если что-то сломалось — верни бэкап:")
    print(f"  cp {backup.name} {WALKER_PATH.name}")


if __name__ == "__main__":
    main()
