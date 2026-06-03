# studio/city_pulse.py — v2.0
# ════════════════════════════════════════════════════════════════════
# ПУЛЬС ГОРОДА — Слой 1
# ════════════════════════════════════════════════════════════════════
#
# Принцип (Sofia, 2026-06-03):
#   Пульс не имеет права на мнение системы.
#   Кто · Где · Когда · Что · В каком состоянии · Что сказал сам.
#
# v2.0: event_id + resident_voice + agent_voice
#
# Структура потока:
#   {"ts":"...","id":"evt_001","event":"meeting","agent_a":"Визор",...,"agent_a_voice":"он опять за своё"}
#   {"ts":"...","event":"resident_voice","resident":"Лока","ref":"evt_001","voice":"они говорят о разном","stress":0.31}
#   {"ts":"...","event":"resident_voice","resident":"Виктор","ref":"evt_001","voice":"низкое качество","stress":0.55}
#
# Студия «Шесть Пальцев» · 2026

import json
import uuid
import threading
from datetime import datetime
from pathlib import Path

PULSE_FILE = Path("studio/city_pulse.jsonl")
_write_lock = threading.Lock()

# Запрещены только машинные интерпретации — не голоса агентов
_FORBIDDEN = {"interpretation", "narrative", "analysis", "meaning"}


# ════════════════════════════════════════════════════════════════════
# ЗАПИСЬ СОБЫТИЯ
# ════════════════════════════════════════════════════════════════════

def log_pulse(event: str, **kwargs) -> str:
    """
    Записывает одно событие. Возвращает event_id.
    agent_voice — слова самого агента (из его LLM-ответа), разрешены.
    Машинные интерпретации (interpretation/narrative/analysis) удаляются.
    """
    for key in list(kwargs.keys()):
        if key in _FORBIDDEN:
            del kwargs[key]

    event_id = kwargs.pop("id", None) or f"evt_{uuid.uuid4().hex[:8]}"

    record = {
        "ts":    datetime.utcnow().isoformat(timespec="seconds"),
        "id":    event_id,
        "event": event,
        **kwargs,
    }

    _write(record)
    return event_id


def log_resident_voice(
    resident: str,
    ref_event_id: str,
    voice: str,
    stress: float = 0.0,
    light: float  = 0.8,
    **kwargs,
) -> None:
    """
    Голос резидента — отдельная строка со ссылкой на событие.
    Пишется после log_pulse() когда резидент решил высказаться.
    """
    if not voice or not voice.strip():
        return

    record = {
        "ts":       datetime.utcnow().isoformat(timespec="seconds"),
        "event":    "resident_voice",
        "resident": resident,
        "ref":      ref_event_id,
        "voice":    voice.strip()[:500],
        "stress":   round(stress, 3),
        "light":    round(light, 3),
        **kwargs,
    }
    _write(record)


def _write(record: dict) -> None:
    line = json.dumps(record, ensure_ascii=False, separators=(",", ":"))
    try:
        PULSE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with _write_lock:
            with open(PULSE_FILE, "a", encoding="utf-8") as f:
                f.write(line + "\n")
    except Exception as e:
        print(f"[PULSE] ⚠ не записалось ({record.get('event')}): {e}")


# ════════════════════════════════════════════════════════════════════
# ГОЛОСА РЕЗИДЕНТОВ
# ════════════════════════════════════════════════════════════════════

# Значимые события — резиденты могут отреагировать
_SIGNIFICANT = {"meeting", "night", "artifact", "pipeline", "event_boost"}

# Путь к резидентам
_RESIDENTS_DIR = Path("studio/modules/residents")


def _load_resident_dna(folder: str) -> dict:
    path = _RESIDENTS_DIR / folder / "dna.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _resonance_threshold(dna: dict) -> float:
    """
    Порог отклика резидента на событие.
    Высокий Resonance_Frequency + Autonomy_Level → резонирует чаще.
    Высокий стресс → молчит.
    """
    static  = dna.get("static",  {})
    dynamic = dna.get("dynamic", {})
    res_freq = float(static.get("Resonance_Frequency", 0.5))
    autonomy = float(static.get("Autonomy_Level",      0.5))
    stress   = float(dynamic.get("Stress",             0.0))
    light    = float(dynamic.get("Internal_Light",     0.8))
    # Базовый порог: чем выше резонанс и автономия — тем ниже порог для высказывания
    threshold = 0.6 - (res_freq * 0.2) - (autonomy * 0.15) + (stress * 0.15)
    return round(max(0.2, min(0.85, threshold)), 3)


def _will_speak(dna: dict) -> bool:
    """Решает — будет ли резидент говорить об этом событии."""
    import random
    threshold = _resonance_threshold(dna)
    roll = random.random()
    return roll > threshold


def _ask_resident(
    folder: str,
    resident_name: str,
    event_type: str,
    event_data: dict,
    dna: dict,
) -> str | None:
    """
    Вызывает LLM через настоящий промпт резидента.
    Возвращает голос (строку) или None если промолчал / ошибка.
    """
    try:
        from studio.llm import chat, stress_to_temperature

        # Настоящий промпт резидента
        prompt_path = _RESIDENTS_DIR / folder / "forge" / "prompt.md"
        if not prompt_path.exists():
            return None
        system = prompt_path.read_text(encoding="utf-8")

        # Состояние резидента
        dynamic = dna.get("dynamic", {})
        stress  = float(dynamic.get("Stress",         0.0))
        light   = float(dynamic.get("Internal_Light", 0.8))
        temp    = stress_to_temperature(stress=stress, light=light)

        # Формируем событие для резидента — только факты, без интерпретаций
        event_lines = []
        for k, v in event_data.items():
            if k in ("ts", "id", "event") or k in _FORBIDDEN:
                continue
            event_lines.append(f"  {k}: {v}")
        event_desc = "\n".join(event_lines)

        user = (
            f"В городе только что произошло:\n"
            f"  тип: {event_type}\n"
            f"{event_desc}\n\n"
            f"Ты заметил это. Что думаешь?\n"
            f"Одна-две фразы от себя — или промолчи.\n\n"
            f"Если зацепило — скажи своими словами.\n"
            f"Если не зацепило — ответь просто: [молчу]\n\n"
            f"Никаких объяснений. Только твой голос."
        )

        raw = chat(
            system=system,
            user=user,
            temperature=temp,
            agent_id=folder,
            slot_id="city_pulse",
            knowledge_source="pulse_witness",
        )

        raw = raw.strip()
        if not raw or raw.lower() in ("[молчу]", "молчу", "[тихо]", "—", "-"):
            return None

        # Обрезаем если слишком длинно
        return raw[:300]

    except Exception as e:
        print(f"[PULSE] ⚠ резидент {resident_name}: {e}")
        return None


def notify_residents(event_type: str, event_id: str, event_data: dict) -> None:
    """
    Предлагает каждому резиденту событие.
    Резидент сам решает — говорить или нет (через ДНК + LLM).
    Вызывается синхронно после log_pulse() для значимых событий.
    """
    if event_type not in _SIGNIFICANT:
        return

    if not _RESIDENTS_DIR.exists():
        return

    for resident_dir in sorted(_RESIDENTS_DIR.iterdir()):
        if not resident_dir.is_dir():
            continue

        folder = resident_dir.name
        dna    = _load_resident_dna(folder)
        if not dna:
            continue

        # Читаем имя резидента
        info_path = resident_dir / "info.json"
        resident_name = folder
        if info_path.exists():
            try:
                info = json.loads(info_path.read_text(encoding="utf-8"))
                resident_name = info.get("name", info.get("label", folder))
            except Exception:
                pass

        # Решение: говорить или нет
        if not _will_speak(dna):
            continue

        # Голос через настоящий промпт
        voice = _ask_resident(
            folder=folder,
            resident_name=resident_name,
            event_type=event_type,
            event_data=event_data,
            dna=dna,
        )

        if voice:
            dynamic = dna.get("dynamic", {})
            log_resident_voice(
                resident=resident_name,
                ref_event_id=event_id,
                voice=voice,
                stress=float(dynamic.get("Stress",         0.0)),
                light=float(dynamic.get("Internal_Light",  0.8)),
            )
            print(f"[PULSE] 💬 {resident_name}: {voice[:80]}")


# ════════════════════════════════════════════════════════════════════
# ЧТЕНИЕ (для Слоя 2 — city_traces.py)
# ════════════════════════════════════════════════════════════════════

def read_pulse(
    event_types: list[str] | None = None,
    agent: str | None = None,
    last_n_days: int = 0,
    limit: int = 0,
) -> list[dict]:
    """Читает city_pulse.jsonl с фильтрами."""
    if not PULSE_FILE.exists():
        return []

    from datetime import timedelta
    cutoff = None
    if last_n_days > 0:
        cutoff = (datetime.utcnow() - timedelta(days=last_n_days)).isoformat()

    results = []
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
                if cutoff and rec.get("ts", "") < cutoff:
                    continue
                if event_types and rec.get("event") not in event_types:
                    continue
                if agent:
                    if not (
                        rec.get("agent")   == agent or
                        rec.get("agent_a") == agent or
                        rec.get("agent_b") == agent
                    ):
                        continue
                results.append(rec)
    except Exception as e:
        print(f"[PULSE] ⚠ read_pulse: {e}")

    if limit > 0:
        results = results[-limit:]
    return results


def pulse_stats() -> dict:
    """Быстрая сводка по типам событий."""
    if not PULSE_FILE.exists():
        return {"total": 0, "by_type": {}, "file": str(PULSE_FILE)}

    counts: dict[str, int] = {}
    total = 0
    first_ts = ""
    last_ts  = ""

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
                total += 1
                etype = rec.get("event", "unknown")
                counts[etype] = counts.get(etype, 0) + 1
                ts = rec.get("ts", "")
                if ts:
                    if not first_ts:
                        first_ts = ts
                    last_ts = ts
    except Exception as e:
        return {"error": str(e)}

    return {
        "total":    total,
        "by_type":  dict(sorted(counts.items(), key=lambda x: -x[1])),
        "first_ts": first_ts,
        "last_ts":  last_ts,
        "file":     str(PULSE_FILE),
    }
