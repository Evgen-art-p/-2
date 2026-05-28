# studio/complaint_book.py
# Книга Жалоб и Благодарностей Грондхейма
#
# Три слоя:
#   1. Запись события (jsonl-хранилище)
#   2. Эффект в emotional_weights (resentment / gratitude)
#   3. След в sensory_memory агента (знает что написал)
#
# Триггеры вызываются из hooks.py финализаторов после QA.
# Садовник читает через вкладку «Книга» в ui_cabinet.py.
# Реплика Садовника → gardener_note_to_entry() → sensory обоих.
#
# Студия «Шесть Пальцев» · 2026

import json
import uuid
from pathlib import Path
from datetime import datetime
from typing import Optional

# ═══════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════

BOOK_PATH = Path("studio/complaint_book.jsonl")

# Порог жалобы: стресс выше этого → может сработать
COMPLAINT_STRESS_THRESHOLD = 0.85

# Порог жалобы: QA ниже этого + Light почти пуст → шрам
COMPLAINT_QA_THRESHOLD = 6.0
COMPLAINT_LIGHT_THRESHOLD = 0.1  # агент вложился полностью

# Порог благодарности: Empathy или Respect выше этого
GRATITUDE_EMPATHY_THRESHOLD = 0.65
GRATITUDE_RESPECT_THRESHOLD = 0.70

# Эффекты на resentment / trust
RESENTMENT_DELTA = 0.30    # жалоба → resentment к обидчику
GRATITUDE_TRUST_DELTA = 0.20  # благодарность → trust к благодетелю
GRATITUDE_WARMTH_DELTA = 0.15

# Стресс-рельеф при записи (выговорился → клапан)
COMPLAINT_STRESS_RELIEF = 0.08
GRATITUDE_STRESS_RELIEF = 0.03  # благодарность тоже снимает немного

# LLM для голоса агента
LLM_MODEL = "google/gemini-2.5-flash"
LLM_MAX_TOKENS = 180


# ═══════════════════════════════════════════════════════════
# ЗАПИСЬ В КНИГУ
# ═══════════════════════════════════════════════════════════

def _write_entry(entry: dict):
    """Атомарная дозапись в jsonl."""
    BOOK_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(BOOK_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _load_entries(limit: int = 100) -> list[dict]:
    """Загружает последние N записей из книги (новые снизу → реверс)."""
    if not BOOK_PATH.exists():
        return []
    entries = []
    with open(BOOK_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except Exception:
                    pass
    return entries[-limit:]


# ═══════════════════════════════════════════════════════════
# ГОЛОС АГЕНТА — LLM-генерация текста записи
# ═══════════════════════════════════════════════════════════

def _generate_entry_text(
    entry_type: str,   # "complaint" | "gratitude"
    from_agent: str,
    to_agent: str,
    trigger_reason: str,
    agent_dir: Path,
) -> str:
    """
    Один LLM-вызов Flash → 2-3 строки голосом агента.
    Загружает anchor_points.md + dna.json для голоса.
    Если LLM недоступен — возвращает заглушку.
    """
    try:
        from studio.workshop.pipeline import call_openrouter

        # Загружаем голос агента
        anchor_text = ""
        anchor_path = agent_dir / "anchor_points.md"
        if anchor_path.exists():
            anchor_text = anchor_path.read_text(encoding="utf-8")[:600]

        dna_snapshot = ""
        dna_path = agent_dir / "dna.json"
        if dna_path.exists():
            dna = json.loads(dna_path.read_text(encoding="utf-8"))
            dynamic = dna.get("dynamic", {})
            dna_snapshot = (
                f"Стресс: {dynamic.get('Stress', '?')}, "
                f"Свет: {dynamic.get('Internal_Light', '?')}, "
                f"Серия: {dynamic.get('streak', 0)}"
            )

        if entry_type == "complaint":
            instruction = (
                f"Ты — {from_agent}. Тебе только что выставили несправедливую оценку "
                f"({trigger_reason}). Ты выкладывался полностью. "
                f"Напиши 2-3 строки в Книгу Жалоб — честно, своим голосом. "
                f"Не театр, не нытьё. Настоящая боль или злость. "
                f"Адресат: {to_agent}. Без заголовков."
            )
        else:
            instruction = (
                f"Ты — {from_agent}. {to_agent} только что спас тебя от провала "
                f"({trigger_reason}). "
                f"Напиши 2-3 строки в Книгу Благодарностей — просто, своим голосом. "
                f"Не пафос. Настоящее тепло. Без заголовков."
            )

        system = (
            f"Ты агент студии «Шесть Пальцев». Твой характер:\n{anchor_text}\n"
            f"Твоё состояние: {dna_snapshot}\n"
            f"Говори от первого лица. Коротко. Живо."
        )

        response = call_openrouter(
            model=LLM_MODEL,
            system_prompt=system,
            user_message=instruction,
            max_tokens=LLM_MAX_TOKENS,
            temperature=0.85,
        )
        return response.strip()[:400]

    except Exception as e:
        print(f"[BOOK] LLM недоступен, заглушка: {e}")
        if entry_type == "complaint":
            return f"[{from_agent}] Это было несправедливо. {trigger_reason}."
        else:
            return f"[{from_agent}] Спасибо. Серьёзно. {trigger_reason}."


# ═══════════════════════════════════════════════════════════
# ТРИГГЕРЫ — вызываются из hooks.py финализаторов
# ═══════════════════════════════════════════════════════════

def check_and_write_complaint(
    agent_id: str,
    qa_agent_id: str,
    qa_score: float,
    dept: str,
) -> Optional[dict]:
    """
    Проверяет условия жалобы после QA-рана.
    Если условия выполнены — пишет запись, обновляет emotional_weights.

    agent_id    — кто пишет жалобу
    qa_agent_id — на кого (QA-агент)
    qa_score    — оценка от QA
    dept        — цех (для поиска папки агента)

    Возвращает dict записи или None.
    """
    from studio.grondheim_memory import (
        _find_agent_dir,
        _load_json,
        update_emotional_weight,
        record_sensory_event,
        sync_to_dna,
    )

    agent_dir = _find_agent_dir(agent_id, dept)
    if not agent_dir:
        return None

    dna = _load_json(agent_dir / "dna.json")
    dynamic = dna.get("dynamic", {})
    stress = float(dynamic.get("Stress", 0))
    light = float(dynamic.get("Internal_Light", 0.8))

    # ── Проверка триггеров ──
    triggered_by = None

    # Триггер 1: стресс критический
    if stress > COMPLAINT_STRESS_THRESHOLD:
        triggered_by = f"стресс {stress:.2f} пробил порог {COMPLAINT_STRESS_THRESHOLD}"

    # Триггер 2: QA-шрам при пустом свете
    elif qa_score < COMPLAINT_QA_THRESHOLD and light < COMPLAINT_LIGHT_THRESHOLD:
        triggered_by = (
            f"QA {qa_score:.1f} < {COMPLAINT_QA_THRESHOLD} "
            f"при Internal_Light {light:.2f} (вложился полностью)"
        )

    if not triggered_by:
        return None  # Условия не выполнены — тишина

    print(f"[BOOK] 🗡 Жалоба: {agent_id} → {qa_agent_id} | {triggered_by}")

    # ── Голос агента ──
    text = _generate_entry_text(
        entry_type="complaint",
        from_agent=agent_id,
        to_agent=qa_agent_id,
        trigger_reason=triggered_by,
        agent_dir=agent_dir,
    )

    # ── Запись в книгу ──
    entry = {
        "id": str(uuid.uuid4()),
        "type": "complaint",
        "from": agent_id,
        "to": qa_agent_id,
        "dept": dept,
        "trigger": triggered_by,
        "text": text,
        "qa_score": qa_score,
        "stress_at_moment": round(stress, 3),
        "light_at_moment": round(light, 3),
        "gardener_note": None,
        "gardener_ts": None,
        "effects": {
            "resentment_delta": RESENTMENT_DELTA,
            "stress_relief": COMPLAINT_STRESS_RELIEF,
        },
        "ts": datetime.now().isoformat(),
    }
    _write_entry(entry)

    # ── Эффект 1: resentment к QA-агенту ──
    update_emotional_weight(
        agent_id=agent_id,
        target_id=qa_agent_id,
        dimension="resentment",
        delta=RESENTMENT_DELTA,
        reason=f"Жалоба: {triggered_by[:100]}",
        dept=dept,
    )

    # ── Эффект 2: стресс-рельеф (выговорился) ──
    # Используем прямую правку dna.json — не sync_to_dna чтобы не смешивать каналы
    dna["dynamic"]["Stress"] = round(max(0, stress - COMPLAINT_STRESS_RELIEF), 3)
    (agent_dir / "dna.json").write_text(
        json.dumps(dna, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # ── Эффект 3: след в sensory_memory ──
    record_sensory_event(
        agent_id=agent_id,
        content=f"Написал жалобу на {qa_agent_id}: «{text[:150]}»",
        event_type="social",
        source="complaint_book",
        emotional_weight=0.7,  # важное событие
        dept=dept,
    )

    print(f"[BOOK] Жалоба записана. resentment+{RESENTMENT_DELTA} к {qa_agent_id}, stress-{COMPLAINT_STRESS_RELIEF}")
    return entry


def check_and_write_gratitude(
    agent_id: str,
    benefactor_id: str,
    reason: str,
    dept: str,
) -> Optional[dict]:
    """
    Проверяет условия благодарности.
    Триггер: высокий Empathy или Respect + реальное событие спасения.

    agent_id      — кто пишет благодарность
    benefactor_id — кому (кто спас)
    reason        — почему (передаётся из hooks.py)
    dept          — цех
    """
    from studio.grondheim_memory import (
        _find_agent_dir,
        _load_json,
        update_emotional_weight,
        record_sensory_event,
    )

    agent_dir = _find_agent_dir(agent_id, dept)
    if not agent_dir:
        return None

    dna = _load_json(agent_dir / "dna.json")
    static = dna.get("static", {})
    empathy = float(static.get("Empathy", 0.5))
    respect_trait = float(static.get("Resonance_Frequency", 0.5))
    dynamic = dna.get("dynamic", {})
    respect_state = float(dynamic.get("Respect", 0.5))
    stress = float(dynamic.get("Stress", 0))

    # ── Проверка триггера ──
    # Нужно: высокий Empathy ИЛИ Respect + реальная ситуация спасения
    empathy_ok = empathy > GRATITUDE_EMPATHY_THRESHOLD
    respect_ok = respect_state > GRATITUDE_RESPECT_THRESHOLD

    if not (empathy_ok or respect_ok):
        return None  # Характер не позволяет — не театр

    print(f"[BOOK] 🌱 Благодарность: {agent_id} → {benefactor_id} | {reason[:60]}")

    # ── Голос агента ──
    text = _generate_entry_text(
        entry_type="gratitude",
        from_agent=agent_id,
        to_agent=benefactor_id,
        trigger_reason=reason,
        agent_dir=agent_dir,
    )

    # ── Запись ──
    entry = {
        "id": str(uuid.uuid4()),
        "type": "gratitude",
        "from": agent_id,
        "to": benefactor_id,
        "dept": dept,
        "trigger": reason,
        "text": text,
        "empathy_at_moment": round(empathy, 3),
        "gardener_note": None,
        "gardener_ts": None,
        "effects": {
            "trust_delta": GRATITUDE_TRUST_DELTA,
            "warmth_delta": GRATITUDE_WARMTH_DELTA,
            "stress_relief": GRATITUDE_STRESS_RELIEF,
        },
        "ts": datetime.now().isoformat(),
    }
    _write_entry(entry)

    # ── Эффект 1: trust + warmth к благодетелю ──
    update_emotional_weight(
        agent_id=agent_id,
        target_id=benefactor_id,
        dimension="trust",
        delta=GRATITUDE_TRUST_DELTA,
        reason=f"Благодарность: {reason[:100]}",
        dept=dept,
    )
    update_emotional_weight(
        agent_id=agent_id,
        target_id=benefactor_id,
        dimension="warmth",
        delta=GRATITUDE_WARMTH_DELTA,
        reason=f"Благодарность: {reason[:100]}",
        dept=dept,
    )

    # ── Эффект 2: micro-relief для обоих ──
    for aid in [agent_id, benefactor_id]:
        adir = _find_agent_dir(aid, dept)
        if not adir:
            continue
        adna = _load_json(adir / "dna.json")
        adyn = adna.get("dynamic", {})
        adyn["Stress"] = round(max(0, float(adyn.get("Stress", 0)) - GRATITUDE_STRESS_RELIEF), 3)
        adna["dynamic"] = adyn
        (adir / "dna.json").write_text(
            json.dumps(adna, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    # ── Эффект 3: sensory ──
    record_sensory_event(
        agent_id=agent_id,
        content=f"Написал благодарность {benefactor_id}: «{text[:150]}»",
        event_type="social",
        source="complaint_book",
        emotional_weight=0.6,
        dept=dept,
    )
    record_sensory_event(
        agent_id=benefactor_id,
        content=f"{agent_id} поблагодарил меня в Книге Благодарностей: «{text[:150]}»",
        event_type="social",
        source="complaint_book",
        emotional_weight=0.6,
        dept=dept,
    )

    print(f"[BOOK] Благодарность записана. trust+{GRATITUDE_TRUST_DELTA}, warmth+{GRATITUDE_WARMTH_DELTA} к {benefactor_id}")
    return entry


# ═══════════════════════════════════════════════════════════
# САДОВНИК — реплика в запись
# ═══════════════════════════════════════════════════════════

def gardener_note_to_entry(
    entry_id: str,
    note: str,
) -> bool:
    """
    Садовник пишет реплику к записи в Книге.

    Что происходит:
    - note сохраняется в запись (поле gardener_note)
    - sensory_memory обоих участников получает след
    - sync_to_dna("cabinet_chat") обоим — тот же канал что и хроники

    Возвращает True если запись найдена и обновлена.
    """
    from studio.grondheim_memory import (
        _find_agent_dir,
        record_sensory_event,
        sync_to_dna,
    )

    if not BOOK_PATH.exists():
        return False

    # Читаем все строки
    lines = BOOK_PATH.read_text(encoding="utf-8").splitlines()
    updated = False
    updated_entry = None

    new_lines = []
    for line in lines:
        line = line.strip()
        if not line:
            new_lines.append(line)
            continue
        try:
            entry = json.loads(line)
            if entry.get("id") == entry_id:
                entry["gardener_note"] = note[:500]
                entry["gardener_ts"] = datetime.now().isoformat()
                updated = True
                updated_entry = entry
            new_lines.append(json.dumps(entry, ensure_ascii=False))
        except Exception:
            new_lines.append(line)

    if not updated:
        return False

    # Перезаписываем файл
    BOOK_PATH.write_text("\n".join(new_lines) + "\n", encoding="utf-8")

    # ── Sensory след обоим участникам ──
    from_agent = updated_entry.get("from", "")
    to_agent = updated_entry.get("to", "")
    entry_type = updated_entry.get("type", "")
    dept = updated_entry.get("dept", "")

    note_preview = note[:150]
    type_label = "жалобу" if entry_type == "complaint" else "благодарность"

    for agent_id in [from_agent, to_agent]:
        if not agent_id:
            continue

        agent_dir = _find_agent_dir(agent_id, dept)
        if not agent_dir:
            continue

        record_sensory_event(
            agent_id=agent_id,
            content=f"Садовник прочитал мою {type_label} и написал: «{note_preview}»",
            event_type="social",
            source="gardener",
            emotional_weight=0.75,  # Садовник вмешался — важно
            dept=dept,
        )

        # Тот же канал что и хроники — не создаём нового
        sync_to_dna(agent_id, "cabinet_chat", dept=dept)

    print(f"[BOOK] 🌱 Садовник → запись {entry_id[:8]}... | след в sensory обоих")
    return True


# ═══════════════════════════════════════════════════════════
# САДОВНИК — действие (помирить / защитить / усилить)
# ═══════════════════════════════════════════════════════════

def gardener_action(
    entry_id: str,
    action: str,  # "mediate" | "protect" | "amplify" | "release"
) -> bool:
    """
    Садовник совершает действие по записи.

    "mediate"  — помирить: resentment тает на 30%
    "protect"  — защитить автора: Respect +0.1, Stress -0.05; к обидчику мягкий penalty
    "amplify"  — усилить благодарность: trust +0.1 доп обоим
    "release"  — отпустить: ничего не меняется, помечается как seen
    """
    from studio.grondheim_memory import (
        _find_agent_dir,
        _load_json,
        update_emotional_weight,
        record_sensory_event,
        sync_to_dna,
    )

    if not BOOK_PATH.exists():
        return False

    lines = BOOK_PATH.read_text(encoding="utf-8").splitlines()
    updated_entry = None

    new_lines = []
    for line in lines:
        line = line.strip()
        if not line:
            new_lines.append(line)
            continue
        try:
            entry = json.loads(line)
            if entry.get("id") == entry_id:
                entry["gardener_action"] = action
                entry["gardener_action_ts"] = datetime.now().isoformat()
                updated_entry = entry
            new_lines.append(json.dumps(entry, ensure_ascii=False))
        except Exception:
            new_lines.append(line)

    if not updated_entry:
        return False

    BOOK_PATH.write_text("\n".join(new_lines) + "\n", encoding="utf-8")

    from_agent = updated_entry.get("from", "")
    to_agent = updated_entry.get("to", "")
    dept = updated_entry.get("dept", "")
    entry_type = updated_entry.get("type", "")

    if action == "mediate" and entry_type == "complaint":
        # Resentment тает на 30% от текущего
        adir = _find_agent_dir(from_agent, dept)
        if adir:
            from studio.grondheim_memory import load_emotional_weights, _save_json
            weights = load_emotional_weights(from_agent, dept)
            if to_agent in weights:
                cur = weights[to_agent].get("resentment", 0)
                weights[to_agent]["resentment"] = round(cur * 0.7, 3)
                _save_json(adir / "resonance" / "emotional_weights.json", weights)
        # sensory обоим
        for aid in [from_agent, to_agent]:
            record_sensory_event(
                agent_id=aid,
                content="Садовник помирил нас — его слово осталось",
                event_type="social",
                source="gardener",
                emotional_weight=0.8,
                dept=dept,
            )
            sync_to_dna(aid, "cabinet_chat", dept=dept)
        print(f"[BOOK] ⚖️ Медиация: resentment {from_agent}→{to_agent} ×0.7")

    elif action == "protect" and entry_type == "complaint":
        # Автор: Respect +0.1, Stress -0.05
        adir = _find_agent_dir(from_agent, dept)
        if adir:
            adna = _load_json(adir / "dna.json")
            adyn = adna.get("dynamic", {})
            adyn["Respect"] = round(min(1, float(adyn.get("Respect", 0.5)) + 0.10), 3)
            adyn["Stress"] = round(max(0, float(adyn.get("Stress", 0)) - 0.05), 3)
            adna["dynamic"] = adyn
            (adir / "dna.json").write_text(
                json.dumps(adna, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        record_sensory_event(
            agent_id=from_agent,
            content="Садовник встал на мою сторону. Это что-то значит.",
            event_type="social",
            source="gardener",
            emotional_weight=0.85,
            dept=dept,
        )
        sync_to_dna(from_agent, "cabinet_chat", dept=dept)
        print(f"[BOOK] 🛡 Защита: {from_agent} Respect+0.1 Stress-0.05")

    elif action == "amplify" and entry_type == "gratitude":
        # trust +0.1 доп обоим
        update_emotional_weight(from_agent, to_agent, "trust", 0.10,
                                "Садовник усилил благодарность", dept)
        update_emotional_weight(to_agent, from_agent, "warmth", 0.08,
                                "Садовник засвидетельствовал", dept)
        for aid in [from_agent, to_agent]:
            record_sensory_event(
                agent_id=aid,
                content="Садовник увидел нашу связь и усилил её",
                event_type="social",
                source="gardener",
                emotional_weight=0.7,
                dept=dept,
            )
            sync_to_dna(aid, "cabinet_chat", dept=dept)
        print(f"[BOOK] 🌟 Усиление благодарности {from_agent}→{to_agent}")

    elif action == "release":
        # Помечаем — ничего не меняем
        print(f"[BOOK] 🌊 Отпущено: запись {entry_id[:8]}...")

    return True


# ═══════════════════════════════════════════════════════════
# API ДЛЯ UI — вкладка «Книга» в ui_cabinet.py
# ═══════════════════════════════════════════════════════════

def get_book_entries(
    limit: int = 50,
    entry_type: Optional[str] = None,  # "complaint" | "gratitude" | None = все
    agent_filter: Optional[str] = None,  # показать записи где агент = from или to
) -> list[dict]:
    """
    Возвращает записи для отображения в UI.
    Новые — первые.
    """
    entries = _load_entries(limit * 2)  # грузим с запасом для фильтрации
    entries.reverse()  # новые первые

    if entry_type:
        entries = [e for e in entries if e.get("type") == entry_type]

    if agent_filter:
        entries = [
            e for e in entries
            if e.get("from") == agent_filter or e.get("to") == agent_filter
        ]

    return entries[:limit]


def get_book_stats() -> dict:
    """Статистика для шапки вкладки."""
    entries = _load_entries(1000)
    complaints = [e for e in entries if e.get("type") == "complaint"]
    gratitudes = [e for e in entries if e.get("type") == "gratitude"]

    # Топ "обиженных" агентов
    from collections import Counter
    complaint_from = Counter(e.get("from") for e in complaints)
    gratitude_to = Counter(e.get("to") for e in gratitudes)

    return {
        "total": len(entries),
        "complaints": len(complaints),
        "gratitudes": len(gratitudes),
        "top_complainers": complaint_from.most_common(3),
        "top_helpers": gratitude_to.most_common(3),
        "last_entry_ts": entries[0].get("ts") if entries else None,
    }
