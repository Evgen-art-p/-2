# studio/city_traces.py
# ════════════════════════════════════════════════════════════════════
# СЛЕДЫ ГОРОДА — Слой 2
# ════════════════════════════════════════════════════════════════════
#
# Читает city_pulse.jsonl → находит паттерны → пишет city_traces.json
#
# Запускается раз в сутки из morning_checkout.py.
# Никакого LLM. Только математика.
#
# Пять паттернов:
#   location_streaks   — кто куда ходит регулярно и в каком состоянии
#   stress_at_location — средний стресс агента по локациям
#   meeting_frequency  — кто с кем встречается и с каким качеством
#   revolt_patterns    — личный порог бунта каждого агента
#   voice_themes       — слова которые агент повторяет (из agent_voice)
#
# Лока НЕ читает city_pulse.jsonl напрямую.
# Лока читает city_traces.json — уже выжатые паттерны.
#
# Студия «Шесть Пальцев» · 2026

import json
import re
from collections import defaultdict, Counter
from datetime import datetime, timedelta
from pathlib import Path

PULSE_FILE  = Path("studio/city_pulse.jsonl")
TRACES_FILE = Path("studio/city_traces.json")


# ════════════════════════════════════════════════════════════════════
# ГЛАВНАЯ ФУНКЦИЯ
# ════════════════════════════════════════════════════════════════════

def run_traces(last_n_days: int = 30) -> dict:
    """
    Читает пульс за последние N дней, считает паттерны,
    пишет city_traces.json.

    Вызывается из morning_checkout.run_morning_checkout()
    раз в сутки (только если пульс изменился).

    Возвращает traces dict.
    """
    events = _read_pulse(last_n_days=last_n_days)

    if not events:
        print(f"[TRACES] ℹ️  city_pulse.jsonl пуст или не найден — traces не обновляем")
        return {}

    print(f"[TRACES] 📊 Читаю {len(events)} событий за {last_n_days} дней...")

    traces = {
        "computed_at":       datetime.utcnow().isoformat(timespec="seconds"),
        "events_analyzed":   len(events),
        "period_days":       last_n_days,
        "location_streaks":  _compute_location_streaks(events),
        "stress_at_location": _compute_stress_at_location(events),
        "meeting_frequency": _compute_meeting_frequency(events),
        "revolt_patterns":   _compute_revolt_patterns(events),
        "voice_themes":      _compute_voice_themes(events),
    }

    # Пишем
    TRACES_FILE.parent.mkdir(parents=True, exist_ok=True)
    TRACES_FILE.write_text(
        json.dumps(traces, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    # Краткий отчёт
    n_streaks  = sum(len(v) for v in traces["location_streaks"].values())
    n_pairs    = len(traces["meeting_frequency"])
    n_revolts  = len(traces["revolt_patterns"])
    n_themes   = sum(len(v) for v in traces["voice_themes"].values())
    print(
        f"[TRACES] ✅ city_traces.json обновлён: "
        f"streaks={n_streaks} pairs={n_pairs} "
        f"revolts={n_revolts} themes={n_themes}"
    )

    return traces


# ════════════════════════════════════════════════════════════════════
# ЧТЕНИЕ ПУЛЬСА
# ════════════════════════════════════════════════════════════════════

def _read_pulse(last_n_days: int = 30) -> list[dict]:
    """Читает city_pulse.jsonl, фильтрует по дате."""
    if not PULSE_FILE.exists():
        return []

    cutoff = (datetime.utcnow() - timedelta(days=last_n_days)).isoformat()
    events = []

    try:
        with open(PULSE_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except Exception:
                    continue
                if rec.get("ts", "") >= cutoff:
                    events.append(rec)
    except Exception as e:
        print(f"[TRACES] ⚠️  Ошибка чтения пульса: {e}")

    return events


# ════════════════════════════════════════════════════════════════════
# ПАТТЕРН 1: LOCATION STREAKS
# Кто куда ходит регулярно и в каком состоянии
# ════════════════════════════════════════════════════════════════════

def _compute_location_streaks(events: list[dict]) -> dict:
    """
    Для каждого агента: топ-3 локации по количеству визитов
    с указанием среднего стресса в момент визита.

    Структура:
    {
      "Визор": [
        {"location": "Галерея", "visits": 11, "avg_stress": 0.63, "last_visit": "2026-06-03"},
        ...
      ]
    }
    """
    # agent → location → [stress values]
    data: dict[str, dict[str, list]] = defaultdict(lambda: defaultdict(list))

    for e in events:
        if e.get("event") != "walk":
            continue
        agent    = e.get("agent", "")
        location = e.get("location", "")
        stress   = e.get("stress")
        ts       = e.get("ts", "")

        if not agent or not location or location == "неизвестно":
            continue

        stress_val = float(stress) if stress is not None else None
        data[agent][location].append({
            "stress": stress_val,
            "ts":     ts,
        })

    result = {}
    for agent, locs in data.items():
        agent_locs = []
        for loc, visits in locs.items():
            stresses = [v["stress"] for v in visits if v["stress"] is not None]
            last_ts  = max((v["ts"] for v in visits), default="")
            agent_locs.append({
                "location":   loc,
                "visits":     len(visits),
                "avg_stress": round(sum(stresses) / len(stresses), 3) if stresses else None,
                "last_visit": last_ts[:10],
            })
        # Топ-3 по количеству визитов
        agent_locs.sort(key=lambda x: x["visits"], reverse=True)
        result[agent] = agent_locs[:3]

    return result


# ════════════════════════════════════════════════════════════════════
# ПАТТЕРН 2: STRESS AT LOCATION
# Средний стресс агента по локациям — где он расслабляется, где напрягается
# ════════════════════════════════════════════════════════════════════

def _compute_stress_at_location(events: list[dict]) -> dict:
    """
    Для каждой локации: средний стресс всех агентов которые туда ходили.
    Плюс — какие агенты ходят туда со стрессом выше среднего.

    Структура:
    {
      "Таверна «Усталый Пиксель»": {
        "avg_stress": 0.61,
        "visit_count": 45,
        "high_stress_agents": ["Джем", "Виктор"]
      }
    }
    """
    # location → list of (agent, stress)
    loc_data: dict[str, list] = defaultdict(list)

    for e in events:
        if e.get("event") != "walk":
            continue
        location = e.get("location", "")
        agent    = e.get("agent", "")
        stress   = e.get("stress")

        if not location or location == "неизвестно" or stress is None:
            continue

        loc_data[location].append({
            "agent":  agent,
            "stress": float(stress),
        })

    result = {}
    for loc, visits in loc_data.items():
        if len(visits) < 2:
            continue  # мало данных

        stresses  = [v["stress"] for v in visits]
        avg       = sum(stresses) / len(stresses)
        threshold = avg + 0.1  # высокий стресс = выше среднего + 0.1

        # Агенты которые приходят сюда со стрессом выше порога
        high_stress = Counter(
            v["agent"] for v in visits
            if v["stress"] >= threshold and v["agent"]
        )
        top_stressed = [agent for agent, _ in high_stress.most_common(3)]

        result[loc] = {
            "avg_stress":         round(avg, 3),
            "visit_count":        len(visits),
            "high_stress_agents": top_stressed,
        }

    return result


# ════════════════════════════════════════════════════════════════════
# ПАТТЕРН 3: MEETING FREQUENCY
# Кто с кем встречается и с каким качеством
# ════════════════════════════════════════════════════════════════════

def _compute_meeting_frequency(events: list[dict]) -> dict:
    """
    Топ пар агентов по количеству встреч с средним качеством.

    Структура:
    {
      "Визор|Джем": {
        "agent_a": "Визор",
        "agent_b": "Джем",
        "meetings": 7,
        "avg_quality": 0.68,
        "locations": ["Таверна", "Площадь Резонанса"]
      }
    }
    """
    # pair_key → list of meetings
    pairs: dict[str, list] = defaultdict(list)

    for e in events:
        if e.get("event") != "meeting":
            continue
        a       = e.get("agent_a", "")
        b       = e.get("agent_b", "")
        quality = e.get("quality")
        loc     = e.get("location", "")

        if not a or not b:
            continue

        # Нормализуем пару (алфавитный порядок)
        key = "|".join(sorted([a, b]))
        pairs[key].append({
            "quality":  float(quality) if quality is not None else None,
            "location": loc,
        })

    result = {}
    for key, meetings in pairs.items():
        if len(meetings) < 2:
            continue  # разовая встреча — не паттерн

        a, b = key.split("|", 1)
        qualities = [m["quality"] for m in meetings if m["quality"] is not None]
        locs      = list(dict.fromkeys(m["location"] for m in meetings if m["location"]))

        result[key] = {
            "agent_a":     a,
            "agent_b":     b,
            "meetings":    len(meetings),
            "avg_quality": round(sum(qualities) / len(qualities), 3) if qualities else None,
            "locations":   locs[:3],
        }

    # Сортируем по количеству встреч
    result = dict(
        sorted(result.items(), key=lambda x: x[1]["meetings"], reverse=True)
    )

    return result


# ════════════════════════════════════════════════════════════════════
# ПАТТЕРН 4: REVOLT PATTERNS
# Личный порог бунта каждого агента
# ════════════════════════════════════════════════════════════════════

def _compute_revolt_patterns(events: list[dict]) -> dict:
    """
    Для каждого агента у которого были REVOLT/RESTLESS:
    средний стресс и resentment в момент решения.

    Структура:
    {
      "Виктор": {
        "revolts": 3,
        "restless": 1,
        "avg_stress_at_revolt": 0.82,
        "avg_resentment_at_revolt": 0.45,
        "last_revolt": "2026-06-03"
      }
    }
    """
    # agent → list of night events
    agent_nights: dict[str, list] = defaultdict(list)

    for e in events:
        if e.get("event") != "night":
            continue
        agent    = e.get("agent", "")
        decision = e.get("decision", "")
        if not agent or decision == "SLEEP":
            continue

        agent_nights[agent].append({
            "decision":   decision,
            "stress":     e.get("stress"),
            "resentment": e.get("resentment"),
            "ts":         e.get("ts", ""),
        })

    result = {}
    for agent, nights in agent_nights.items():
        revolts   = [n for n in nights if n["decision"] == "REVOLT"]
        restless  = [n for n in nights if n["decision"] == "RESTLESS"]

        r_stresses    = [n["stress"]     for n in revolts if n["stress"]     is not None]
        r_resentments = [n["resentment"] for n in revolts if n["resentment"] is not None]
        last_ts = max((n["ts"] for n in nights), default="")

        result[agent] = {
            "revolts":                len(revolts),
            "restless":               len(restless),
            "avg_stress_at_revolt":   round(sum(r_stresses)    / len(r_stresses),    3) if r_stresses    else None,
            "avg_resentment_at_revolt": round(sum(r_resentments) / len(r_resentments), 3) if r_resentments else None,
            "last_revolt":            last_ts[:10],
        }

    # Сортируем по количеству бунтов
    result = dict(
        sorted(result.items(), key=lambda x: x[1]["revolts"], reverse=True)
    )

    return result


# ════════════════════════════════════════════════════════════════════
# ПАТТЕРН 5: VOICE THEMES
# Слова которые агент повторяет в agent_voice
# ════════════════════════════════════════════════════════════════════

# Стоп-слова — не несут смысла
_STOP_WORDS = {
    "и", "в", "на", "с", "по", "к", "у", "о", "из", "за", "не", "но",
    "а", "я", "он", "она", "мы", "вы", "они", "это", "то", "что", "как",
    "так", "там", "тут", "здесь", "уже", "ещё", "даже", "просто", "очень",
    "всё", "всегда", "когда", "если", "чтобы", "потому", "хочу", "могу",
    "буду", "был", "была", "было", "есть", "нет", "да", "нет", "ну",
    "the", "a", "an", "in", "on", "at", "to", "of", "and", "or", "but",
    "is", "are", "was", "were", "it", "i", "me", "my", "we", "you",
}


def _compute_voice_themes(events: list[dict]) -> dict:
    """
    Для каждого агента: топ-10 слов из его agent_voice за период.
    Слова короче 4 букв и стоп-слова отфильтрованы.

    Структура:
    {
      "Визор": [
        {"word": "ученики", "count": 7},
        {"word": "обучение", "count": 5},
        ...
      ]
    }
    """
    # agent → Counter слов
    agent_words: dict[str, Counter] = defaultdict(Counter)

    for e in events:
        if e.get("event") != "walk":
            continue
        agent = e.get("agent", "")
        voice = e.get("agent_voice", "")

        if not agent or not voice:
            continue

        # Токенизируем: только буквы, нижний регистр
        words = re.findall(r"[а-яёa-z]{4,}", voice.lower())
        for w in words:
            if w not in _STOP_WORDS:
                agent_words[agent][w] += 1

    result = {}
    for agent, counter in agent_words.items():
        # Только слова которые встречаются 2+ раз — иначе не паттерн
        themes = [
            {"word": word, "count": count}
            for word, count in counter.most_common(10)
            if count >= 2
        ]
        if themes:
            result[agent] = themes

    return result


# ════════════════════════════════════════════════════════════════════
# УТИЛИТА: НУЖНО ЛИ ПЕРЕСЧИТЫВАТЬ?
# ════════════════════════════════════════════════════════════════════

def traces_need_update() -> bool:
    """
    Проверяет нужно ли пересчитывать traces.
    Пересчёт нужен если:
      - city_traces.json не существует
      - он старше 20 часов
      - city_pulse.jsonl новее чем city_traces.json
    """
    if not TRACES_FILE.exists():
        return True

    try:
        traces_mtime = TRACES_FILE.stat().st_mtime
        import time
        age_hours = (time.time() - traces_mtime) / 3600
        if age_hours > 20:
            return True

        if PULSE_FILE.exists():
            pulse_mtime = PULSE_FILE.stat().st_mtime
            if pulse_mtime > traces_mtime:
                return True

    except Exception:
        return True

    return False


# ════════════════════════════════════════════════════════════════════
# ТОЧКА ВХОДА ДЛЯ MORNING_CHECKOUT
# ════════════════════════════════════════════════════════════════════

def maybe_run_traces(last_n_days: int = 30) -> None:
    """
    Вызывается из morning_checkout.run_morning_checkout().
    Пересчитывает traces только если нужно.
    Молча падает при ошибке — не ломает чекаут.
    """
    try:
        if traces_need_update():
            run_traces(last_n_days=last_n_days)
        else:
            print("[TRACES] ℹ️  city_traces.json актуален — пропускаю")
    except Exception as e:
        print(f"[TRACES] ⚠️  Ошибка: {e}")
