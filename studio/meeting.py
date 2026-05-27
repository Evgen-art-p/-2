# studio/meeting.py
"""
🤝 MEETING ENGINE — Живые встречи агентов Грондхейма
Спринт 23 Блок Б · Версия 1.0

ФИЛОСОФИЯ:
─────────────────────────────────────────────────────────
Встреча — НЕ режиссёрский диалог. Не "сгенерируй 5 реплик".
Встреча = два агента, по очереди пробуждающиеся в одной точке города,
с правом замолчать или уйти.

Один LLM-вызов = одна реплика одного агента.
Каждый агент читает только то, что услышал бы реально.
Никакого рассказчика. Никаких внешних судей.

СВЯЗИ ПО ПРАВДЕ:
─────────────────────────────────────────────────────────
• Память:
    sensory_memory ← record_sensory_event(type="meeting", source="meeting", partner=...)
    resonance      ← on_agents_interact(quality, type) → emotional_weights
    DNA            ← НЕ трогаем напрямую. Встреча влияет через emotional_weights
                     → следующий ран → следующая температура.
                     (правило трёх каналов Спринта 21 не ломается)

• Экономика:
    billing_ledger ← пишется автоматически в chat() (slot_id="meeting:{loc}",
                                                      knowledge_source="meeting")
    cost_intuition ← пока не подключаем как блок (TODO Спринт 24),
                     но право молчать у агента есть — выбор LLM, не цены.

• Локация:
    Модулирует ТЕМПЕРАТУРУ (не подменяет характер):
        Таверна  +0.10
        Площадь   0.00
        Маяк    -0.05
        Библиотека/Гавань -0.05
        Храм/Павильон  -0.10
        Замок Сов -0.05

• Архив:
    city_chronicles/YYYY-MM-DD/{loc_slug}_{HH-MM}.json
    Не в city_state (тот чистится). Хроники остаются навсегда.

КОНТРАКТ РЕПЛИКИ (агент возвращает ТОЛЬКО это):
─────────────────────────────────────────────────────────
{
    "text":   "...",                   // что сказал, или ""
    "action": "continue|leave|silent", // что делает
    "felt":   "одна фраза"             // что унёс изнутри
}
"""

import os
import re
import json
import random
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Optional

# ═══════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════

MODULES_DIR     = Path("studio/modules")
CHRONICLES_DIR  = Path("studio/city_chronicles")
MAX_REPLIES     = 6           # потолок реплик в сцене (страховка)
MIN_REPLY_GAP   = 0.5         # секунд между вызовами (мягкая защита от rate limit)
DEBUG           = True


# Модификация температуры по локации (тип → дельта к agent_temp)
LOCATION_TEMP_MOD: dict[str, float] = {
    "tavern":     +0.10,   # расслабленнее, болтливее
    "square":      0.00,   # нейтрально
    "lighthouse": -0.05,   # сосредоточенно
    "library":    -0.05,   # тихо
    "harbor":     -0.05,   # вдумчиво
    "castle":     -0.05,   # стратегически
    "temple":     -0.10,   # шёпотом
    "pavilion":   -0.10,   # рефлексивно
    "workshop":   -0.05,   # рабочая концентрация
    "home":        0.00,
}


# ═══════════════════════════════════════════════════════════
# КЛАССИФИКАЦИЯ ЛОКАЦИИ (зеркало _classify_location из city_walker)
# ═══════════════════════════════════════════════════════════

_LOC_KEYWORDS = {
    "маяк":      "lighthouse",
    "таверна":   "tavern",
    "высотка":   "home",
    "квартал":   "home",
    "гавань":    "harbor",
    "храм":      "temple",
    "замок":     "castle",
    "библиотека":"library",
    "павильон":  "pavilion",
    "площадь":   "square",
    "artifacts": "workshop",
}


def _classify_location(loc_name: str) -> str:
    name_lower = (loc_name or "").lower()
    for kw, ltype in _LOC_KEYWORDS.items():
        if kw in name_lower:
            return ltype
    return "other"


def _slugify_location(loc_name: str) -> str:
    """Безопасное имя файла из названия локации."""
    s = (loc_name or "unknown").lower()
    s = re.sub(r"[«»\"'`\(\)]", "", s)
    s = re.sub(r"[^a-zа-яё0-9]+", "_", s, flags=re.IGNORECASE)
    return s.strip("_")[:60] or "unknown"


# ═══════════════════════════════════════════════════════════
# ЗАГРУЗКА ЛИЧНОСТИ АГЕНТА
# ═══════════════════════════════════════════════════════════

def _read_anchor_points(dept: str, folder: str) -> str:
    """Голос агента — anchor_points.md (если есть)."""
    path = MODULES_DIR / dept / folder / "core" / "anchor_points.md"
    if path.exists():
        try:
            return path.read_text(encoding="utf-8")
        except Exception:
            return ""
    return ""


def _load_dna(dept: str, folder: str) -> dict:
    path = MODULES_DIR / dept / folder / "dna.json"
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _emotional_weight_to(agent_dept: str, agent_folder: str, partner_id: str) -> dict:
    """Текущее отношение агента к партнёру (warmth/trust/respect/rivalry)."""
    path = MODULES_DIR / agent_dept / agent_folder / "resonance" / "emotional_weights.json"
    if not path.exists():
        return {}
    try:
        weights = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    # Пробуем разные ключи — folder, ID
    for key in (partner_id, partner_id.upper()):
        if key in weights:
            return weights[key]
    return {}


def _describe_relation(rel: dict) -> str:
    """Человекочитаемое описание отношения (для промпта)."""
    if not rel:
        return "Ты ещё толком не знаешь этого собеседника."

    warmth   = float(rel.get("warmth",   0.5))
    trust    = float(rel.get("trust",    0.5))
    respect  = float(rel.get("respect",  0.5))
    rivalry  = float(rel.get("rivalry",  0.0))
    memory   = rel.get("memory", "")

    parts = []
    if warmth > 0.7:
        parts.append("тебе тепло с ним")
    elif warmth < 0.3:
        parts.append("тебе холодно с ним")

    if trust > 0.7:
        parts.append("доверяешь")
    elif trust < 0.3:
        parts.append("не доверяешь")

    if respect > 0.75:
        parts.append("глубоко уважаешь")
    elif respect < 0.3:
        parts.append("не уважаешь")

    if rivalry > 0.4:
        parts.append("есть соперничество")

    if not parts:
        relation = "Отношение нейтральное."
    else:
        relation = "Сейчас: " + ", ".join(parts) + "."

    if memory:
        relation += f"\nПомнишь: {memory[:200]}"

    return relation


# ═══════════════════════════════════════════════════════════
# ПОСТРОЕНИЕ ПРОМПТОВ
# ═══════════════════════════════════════════════════════════

def _build_meeting_system_prompt(
    agent: dict,
    anchor_points: str,
) -> str:
    """
    Системный промпт встречи = голос агента (anchor_points) + ДНК-описание
    + блок о том КАК говорить в живом диалоге.

    ДНК-описание и резонанс подмешиваем через grondheim_memory
    (он уже умеет format_dna_for_prompt, format_resonance_for_prompt).
    """
    from studio.grondheim_memory import format_dna_for_prompt, format_resonance_for_prompt

    name       = agent.get("name", "Агент")
    profession = agent.get("profession", "")
    folder     = agent.get("folder", "")
    dept       = agent.get("dept", "")

    parts = []

    # 1. Голос — anchor_points.md (это и есть КТО ты)
    if anchor_points:
        parts.append(anchor_points)
    else:
        parts.append(f"Ты — {name}. {profession}. Живёшь в Грондхейме.")

    # 2. ДНК (характер + текущее состояние)
    dna_block = format_dna_for_prompt(folder, dept)
    if dna_block:
        parts.append(dna_block)

    # 3. Резонанс (отношения с коллегами в общем) — короткий контекст
    res_block = format_resonance_for_prompt(folder, dept)
    if res_block:
        parts.append(res_block)

    # 4. Контракт живого диалога
    parts.append(
        "=== 🗣 КАК ТЫ ГОВОРИШЬ В ДИАЛОГЕ ===\n"
        "• Ты живой. Не играешь роль. Не пишешь сценарий.\n"
        "• Говоришь одну реплику — то что сказал бы ИМЕННО ТЫ ИМЕННО СЕЙЧАС.\n"
        "• Если тебе нечего сказать — молчи (action=silent).\n"
        "• Если не хочешь продолжать — уйди (action=leave).\n"
        "• Не пересказывай и не комментируй слова собеседника.\n"
        "• Не строй длинных монологов. Реплика — это реплика, не эссе.\n"
        "• Внутри ты чувствуешь что-то — это поле 'felt', одна фраза.\n"
        "=== КОНЕЦ КОНТРАКТА ===\n"
    )

    return "\n\n".join(parts)


def _build_meeting_user_prompt(
    partner: dict,
    location: str,
    location_type: str,
    weather: str,
    last_reply: str,
    relation_desc: str,
    turn_number: int,
) -> str:
    """
    User-промпт встречи. Короткий и конкретный.
    Содержит ТОЛЬКО то, что агент реально воспринимает.
    """
    partner_name = partner.get("name", "?")
    partner_role = partner.get("profession", "")

    location_mood = {
        "tavern":     "Тёплый свет, гул, запах хмеля. Расслабленно.",
        "square":     "Открытое пространство. Шум города вокруг.",
        "lighthouse": "Ветер с океана. Звуки чаек. Простор.",
        "library":    "Тишина. Запах бумаги и пыли веков.",
        "harbor":     "Туман на воде. Слышно как скрипят канаты.",
        "castle":     "Прохлада камня. Полумрак. Эхо шагов.",
        "temple":     "Полутемно. Запах воска. Шёпот свечей.",
        "pavilion":   "Стеклянные стены. Время будто замедляется.",
        "workshop":   "Запах смазки и пайки. Гул станков вдалеке.",
        "home":       "Знакомые стены. Можно расслабиться.",
    }.get(location_type, "Обычное место.")

    if turn_number == 0:
        framing = (
            f"Ты только что зашёл в локацию: {location}.\n"
            f"{location_mood}\n"
            f"Погода в городе: {weather}.\n\n"
            f"Здесь {partner_name} ({partner_role}).\n"
            f"{relation_desc}\n\n"
            "Партнёр тебя ещё не заметил — или только что заметил.\n"
            "Ты можешь сказать что-то первым. Или молча сесть рядом. Или уйти.\n"
            "Что ты делаешь?"
        )
    else:
        framing = (
            f"Вы в локации: {location}.\n"
            f"Погода: {weather}.\n\n"
            f"Перед тобой {partner_name} ({partner_role}).\n"
            f"{relation_desc}\n\n"
            f"{partner_name} только что сказал:\n"
            f'  «{last_reply}»\n\n'
            "Что ты ему отвечаешь?\n"
            "Или замолкаешь (silent). Или уходишь (leave)."
        )

    contract = (
        "\n\nОТВЕТ — СТРОГО JSON, ничего больше:\n"
        '{\n'
        '  "text":   "твоя реплика или пустая строка",\n'
        '  "action": "continue|leave|silent",\n'
        '  "felt":   "одна фраза о том что ты унёс из этого момента"\n'
        '}\n'
        "Без префиксов, без ```json, без комментариев. Только объект."
    )

    return framing + contract


# ═══════════════════════════════════════════════════════════
# ПАРСИНГ ОТВЕТА АГЕНТА
# ═══════════════════════════════════════════════════════════

_VALID_ACTIONS = {"continue", "leave", "silent"}


def _parse_reply(raw: str) -> dict:
    """
    Достаёт JSON из ответа модели.
    Гарантирует ключи text / action / felt.
    Если модель промахнулась — возвращает silent + felt="не нашёл слов".
    """
    if not raw:
        return {"text": "", "action": "silent", "felt": "не нашёл слов"}

    # 1. Пробуем найти JSON-объект в любой части ответа
    candidate = None
    # 1a. Срезаем кодовые блоки
    cleaned = re.sub(r"```(?:json)?", "", raw).strip("` \n")

    # 1b. Пробуем парсить целиком
    try:
        candidate = json.loads(cleaned)
    except Exception:
        # 1c. Регексом — самый большой `{...}` в строке
        m = re.search(r"\{[\s\S]*\}", cleaned)
        if m:
            try:
                candidate = json.loads(m.group(0))
            except Exception:
                candidate = None

    if not isinstance(candidate, dict):
        # Не JSON — берём всё как text, действие continue
        return {
            "text":   raw.strip()[:600],
            "action": "continue",
            "felt":   "что-то почувствовал, но не понял что",
        }

    text   = str(candidate.get("text", "")).strip()
    action = str(candidate.get("action", "continue")).strip().lower()
    felt   = str(candidate.get("felt", "")).strip()

    if action not in _VALID_ACTIONS:
        action = "continue" if text else "silent"

    # Пустой text + continue → silent (нечего сказать = молчание)
    if not text and action == "continue":
        action = "silent"

    return {
        "text":   text[:600],
        "action": action,
        "felt":   felt[:300],
    }


# ═══════════════════════════════════════════════════════════
# ВЫЗОВ ОДНОЙ РЕПЛИКИ
# ═══════════════════════════════════════════════════════════

async def _ask_one_reply(
    speaker: dict,
    partner: dict,
    location: str,
    location_type: str,
    weather: str,
    last_reply: str,
    relation_desc: str,
    turn_number: int,
) -> dict:
    """
    Один LLM-вызов = одна реплика. Использует chat() из llm.py,
    биллинг попадает в ledger автоматически.
    """
    from studio.llm import chat, stress_to_temperature

    folder = speaker["folder"]
    dept   = speaker["dept"]
    name   = speaker["name"]

    # ДНК → температура агента
    dna     = _load_dna(dept, folder)
    dynamic = dna.get("dynamic", {}) if dna else {}
    stress  = float(dynamic.get("Stress", 0.0))
    light   = float(dynamic.get("Internal_Light", 0.8))
    base_temp = stress_to_temperature(stress=stress, light=light)

    # Модификация по локации
    temp_mod = LOCATION_TEMP_MOD.get(location_type, 0.0)
    temperature = round(max(0.3, min(1.3, base_temp + temp_mod)), 2)

    # Системный промпт = голос + ДНК + резонанс + контракт диалога
    anchor = _read_anchor_points(dept, folder)
    system_prompt = _build_meeting_system_prompt(
        agent={"name": name, "profession": speaker.get("profession", ""),
               "folder": folder, "dept": dept},
        anchor_points=anchor,
    )

    # User-промпт = ситуация встречи + контракт JSON
    user_prompt = _build_meeting_user_prompt(
        partner=partner,
        location=location,
        location_type=location_type,
        weather=weather,
        last_reply=last_reply,
        relation_desc=relation_desc,
        turn_number=turn_number,
    )

    # slot_id специальный — чтобы в ledger было видно отдельной строкой
    slot_id = f"meeting:{location_type}"

    loop = asyncio.get_event_loop()
    try:
        raw = await loop.run_in_executor(
            None,
            lambda: chat(
                system=system_prompt,
                user=user_prompt,
                temperature=temperature,
                agent_id=folder,
                slot_id=slot_id,
                knowledge_source="meeting",
            )
        )
    except Exception as e:
        if DEBUG:
            print(f"[MEETING] ⚠ {name}: ошибка LLM — {e}")
        return {
            "text": "",
            "action": "silent",
            "felt": "что-то помешало",
            "_temperature": temperature,
            "_error": str(e)[:200],
        }

    parsed = _parse_reply(raw)
    parsed["_temperature"] = temperature
    return parsed


# ═══════════════════════════════════════════════════════════
# КАЧЕСТВО ВСТРЕЧИ (для on_agents_interact)
# ═══════════════════════════════════════════════════════════

def _classify_interaction(scene: dict) -> tuple[str, float]:
    """
    Из тональности 'felt' и количества реплик определяем
    interaction_type и quality для on_agents_interact().

    Признаки:
      • есть слова-конфликта в felt → conflict
      • похвальные слова → praise
      • уход на 1 ходу → нейтрально / тихо
      • длинный обмен с тёплым felt → collaboration
    """
    dialogue = scene.get("dialogue", [])
    if not dialogue:
        return ("collaboration", 0.3)

    felt_all = " ".join(r.get("felt", "") for r in dialogue).lower()

    conflict_markers = ["раздраж", "злюсь", "обиж", "холодно", "разочарован",
                        "не понял", "стена", "тяжело", "не хочется",
                        "пустота", "напряж", "одиноч"]
    praise_markers   = ["благодар", "восхищ", "уважен", "тепло", "поддерж",
                        "вдохнов", "светл", "согрел", "понимани"]
    rescue_markers   = ["спас", "вытащ", "помог в трудный", "подобрал"]
    critique_markers = ["не согласен", "спор", "возраж", "критич"]

    score_conflict = sum(1 for m in conflict_markers if m in felt_all)
    score_praise   = sum(1 for m in praise_markers if m in felt_all)
    score_rescue   = sum(1 for m in rescue_markers if m in felt_all)
    score_critique = sum(1 for m in critique_markers if m in felt_all)

    n_replies = sum(1 for r in dialogue if r.get("text"))

    if score_rescue > 0:
        return ("rescue", min(1.0, 0.6 + score_rescue * 0.2))

    if score_conflict > score_praise:
        return ("conflict", min(1.0, 0.4 + score_conflict * 0.15))

    if score_critique > 0 and score_conflict == 0:
        return ("critique", min(1.0, 0.5 + score_critique * 0.1))

    if score_praise > 0:
        return ("praise", min(1.0, 0.5 + score_praise * 0.15))

    # По умолчанию — обычная коллаборация. Качество = плотность диалога.
    quality = 0.3 + min(0.5, n_replies * 0.08)
    return ("collaboration", round(quality, 2))


# ═══════════════════════════════════════════════════════════
# АРХИВ СЦЕНЫ
# ═══════════════════════════════════════════════════════════

def write_chronicle(scene: dict) -> Optional[Path]:
    """Пишет сцену в city_chronicles/YYYY-MM-DD/{loc}_{HH-MM}.json."""
    try:
        now = datetime.now()
        day_dir = CHRONICLES_DIR / now.strftime("%Y-%m-%d")
        day_dir.mkdir(parents=True, exist_ok=True)

        loc_slug = _slugify_location(scene.get("location", "unknown"))
        time_str = now.strftime("%H-%M-%S")
        path = day_dir / f"{loc_slug}_{time_str}.json"

        path.write_text(
            json.dumps(scene, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        if DEBUG:
            print(f"[MEETING] 📜 Хроника: {path}")
        return path
    except Exception as e:
        print(f"[MEETING] ⚠ Хроника не записана: {e}")
        return None


# ═══════════════════════════════════════════════════════════
# ПАМЯТЬ ПОСЛЕ ВСТРЕЧИ
# ═══════════════════════════════════════════════════════════

def _apply_meeting_aftermath(scene: dict):
    """
    Закрывает встречу:
      • sensory обоих агентов (асимметричная запись — каждый сохраняет своё felt)
      • on_agents_interact (emotional_weights обновятся, interaction_log тоже)
      • DNA НЕ трогаем напрямую — это путь через emotional_weights → следующий ран
    """
    from studio.grondheim_memory import record_sensory_event, on_agents_interact

    a = scene["participants"]["a"]
    b = scene["participants"]["b"]
    location = scene["location"]
    dialogue = scene["dialogue"]

    # Собираем индивидуальный итог каждого
    a_felts, b_felts = [], []
    a_text_partner, b_text_partner = [], []

    for r in dialogue:
        if r["speaker"] == "a":
            if r.get("felt"):
                a_felts.append(r["felt"])
            if r.get("text"):
                b_text_partner.append(r["text"])
        else:
            if r.get("felt"):
                b_felts.append(r["felt"])
            if r.get("text"):
                a_text_partner.append(r["text"])

    a_summary = " · ".join(a_felts)[:300] or "что-то почувствовал"
    b_summary = " · ".join(b_felts)[:300] or "что-то почувствовал"
    a_heard = " | ".join(a_text_partner)[:300]
    b_heard = " | ".join(b_text_partner)[:300]

    # === Sensory: каждый помнит ПО-СВОЕМУ ===
    try:
        record_sensory_event(
            agent_id=a["folder"],
            content=(
                f"[ВСТРЕЧА] {location} · с {b['name']}. "
                f"Услышал: «{a_heard}». Унёс: {a_summary}"
            )[:1000],
            event_type="social",
            source="meeting",
            tags=["встреча", _slugify_location(location), b["folder"].lower()[:30]],
            emotional_weight=0.6,
            dept=a["dept"],
        )
    except Exception as e:
        print(f"[MEETING] ⚠ sensory A не записан: {e}")

    try:
        record_sensory_event(
            agent_id=b["folder"],
            content=(
                f"[ВСТРЕЧА] {location} · с {a['name']}. "
                f"Услышал: «{b_heard}». Унёс: {b_summary}"
            )[:1000],
            event_type="social",
            source="meeting",
            tags=["встреча", _slugify_location(location), a["folder"].lower()[:30]],
            emotional_weight=0.6,
            dept=b["dept"],
        )
    except Exception as e:
        print(f"[MEETING] ⚠ sensory B не записан: {e}")

    # === Резонанс: emotional_weights через on_agents_interact ===
    interaction_type, quality = _classify_interaction(scene)
    scene["interaction"] = {"type": interaction_type, "quality": quality}

    try:
        on_agents_interact(
            agent_a=a["folder"],
            agent_b=b["folder"],
            interaction_type=interaction_type,
            quality=quality,
            note=f"Встреча в {location}: {a_summary[:100]}",
            dept=a["dept"],  # interaction_log пишется в этот слот
        )
        if DEBUG:
            print(f"[MEETING] 💎 {a['name']} ↔ {b['name']}: "
                  f"{interaction_type} (q={quality})")
    except Exception as e:
        print(f"[MEETING] ⚠ on_agents_interact не отработал: {e}")


# ═══════════════════════════════════════════════════════════
# ГЛАВНАЯ ФУНКЦИЯ — run_meeting
# ═══════════════════════════════════════════════════════════

async def run_meeting(
    agent_a: dict,
    agent_b: dict,
    location: str,
    city_state: dict,
) -> Optional[dict]:
    """
    Проводит встречу двух агентов в локации.

    Параметры:
      agent_a, agent_b — dict с обязательными полями:
          folder      (имя папки агента, напр. "A05_stella")
          name        (Official_Name)
          profession  (роль)
          dept        (Workshop_ID)
      location  — строка, Official_Name локации
      city_state — текущее состояние города (для weather)

    Возвращает dict сцены, или None если встреча не состоялась.
    """
    if agent_a["folder"] == agent_b["folder"]:
        return None  # не разговаривает сам с собой

    loc_type   = _classify_location(location)
    weather    = (city_state or {}).get("weather", "")
    started_at = datetime.now()

    # Отношения (читаем один раз перед встречей)
    rel_a_to_b = _emotional_weight_to(agent_a["dept"], agent_a["folder"], agent_b["folder"])
    rel_b_to_a = _emotional_weight_to(agent_b["dept"], agent_b["folder"], agent_a["folder"])
    desc_a = _describe_relation(rel_a_to_b)
    desc_b = _describe_relation(rel_b_to_a)

    scene = {
        "schema":    "meeting_v1",
        "location":  location,
        "location_type": loc_type,
        "started_at": started_at.isoformat(),
        "weather":   weather,
        "participants": {
            "a": {
                "folder": agent_a["folder"], "name": agent_a["name"],
                "dept":   agent_a["dept"],   "profession": agent_a.get("profession", ""),
                "relation_to_partner_before": rel_a_to_b,
            },
            "b": {
                "folder": agent_b["folder"], "name": agent_b["name"],
                "dept":   agent_b["dept"],   "profession": agent_b.get("profession", ""),
                "relation_to_partner_before": rel_b_to_a,
            },
        },
        "dialogue": [],
        "ended_reason": "",
    }

    if DEBUG:
        print(f"[MEETING] 🤝 СТАРТ: {agent_a['name']} ↔ {agent_b['name']} в {location}")

    # Жребий: кто говорит первым
    # Дефолт — у кого выше Social_Filter, при равенстве — случайно
    a_social = float(_load_dna(agent_a["dept"], agent_a["folder"])
                     .get("static", {}).get("Social_Filter", 0.5))
    b_social = float(_load_dna(agent_b["dept"], agent_b["folder"])
                     .get("static", {}).get("Social_Filter", 0.5))

    if abs(a_social - b_social) < 0.05:
        first_is_a = bool(random.getrandbits(1))
    else:
        first_is_a = a_social > b_social

    # Очередь говорящих: [(speaker, partner, desc, last_reply, turn_n), ...]
    last_reply = ""
    turn = 0
    consecutive_silent = 0

    while turn < MAX_REPLIES:
        if (turn == 0 and first_is_a) or (turn > 0 and turn % 2 == 0 and first_is_a) \
           or (turn > 0 and turn % 2 == 1 and not first_is_a):
            speaker_letter = "a"
            speaker = agent_a
            partner = agent_b
            relation_desc = desc_a
        else:
            speaker_letter = "b"
            speaker = agent_b
            partner = agent_a
            relation_desc = desc_b

        reply = await _ask_one_reply(
            speaker=speaker,
            partner=partner,
            location=location,
            location_type=loc_type,
            weather=weather,
            last_reply=last_reply,
            relation_desc=relation_desc,
            turn_number=turn,
        )

        reply_record = {
            "turn":        turn,
            "speaker":     speaker_letter,
            "speaker_name": speaker["name"],
            "text":        reply["text"],
            "action":      reply["action"],
            "felt":        reply["felt"],
            "temperature": reply.get("_temperature"),
            "ts":          datetime.now().isoformat(),
        }
        if "_error" in reply:
            reply_record["error"] = reply["_error"]

        scene["dialogue"].append(reply_record)

        if DEBUG:
            tag = "💬" if reply["text"] else ("🚪" if reply["action"] == "leave" else "🤐")
            short_text = reply["text"][:80] if reply["text"] else f"[{reply['action']}]"
            print(f"[MEETING] {tag} {speaker['name']}: {short_text}")

        # Условия выхода
        if reply["action"] == "leave":
            scene["ended_reason"] = f"{speaker['name']} ушёл"
            break

        if reply["action"] == "silent":
            consecutive_silent += 1
            # Два подряд silent — сцена не клеится, расходятся молча
            if consecutive_silent >= 2:
                scene["ended_reason"] = "оба замолчали"
                break
            # Передаём ход партнёру — last_reply остаётся прежним
            # (это значит партнёр слышал ту же реплику, но к нему пришла тишина)
            last_reply = last_reply  # явно: молчание не меняет состояние диалога
        else:
            consecutive_silent = 0
            last_reply = reply["text"]

        turn += 1
        await asyncio.sleep(MIN_REPLY_GAP)

    else:
        # while дошёл до MAX_REPLIES без break
        scene["ended_reason"] = "достигнут потолок реплик"

    scene["ended_at"]     = datetime.now().isoformat()
    scene["total_turns"]  = len(scene["dialogue"])
    scene["spoken_turns"] = sum(1 for r in scene["dialogue"] if r.get("text"))

    # Если оба молчали с самого начала — это не встреча
    if scene["spoken_turns"] == 0:
        if DEBUG:
            print(f"[MEETING] 🤐 {agent_a['name']} и {agent_b['name']}: "
                  f"молчали и разошлись")
        # Лёгкое касание в emotional_weights — всё-таки видели друг друга
        try:
            from studio.grondheim_memory import on_agents_interact
            on_agents_interact(
                agent_a=agent_a["folder"], agent_b=agent_b["folder"],
                interaction_type="collaboration", quality=0.15,
                note=f"Молчаливая встреча в {location}",
                dept=agent_a["dept"],
            )
        except Exception:
            pass
        return None  # хронику не пишем — нечего записывать

    # Применяем последствия и пишем архив
    _apply_meeting_aftermath(scene)
    write_chronicle(scene)

    if DEBUG:
        print(f"[MEETING] ✅ Финал: {scene['total_turns']} ход(ов), "
              f"{scene['spoken_turns']} реплик · {scene['ended_reason']}")

    return scene


# ═══════════════════════════════════════════════════════════
# ВСПОМОГАТЕЛЬНАЯ: запустить встречу из city_walker (sync wrapper)
# ═══════════════════════════════════════════════════════════

def run_meeting_sync(
    agent_a: dict,
    agent_b: dict,
    location: str,
    city_state: dict,
) -> Optional[dict]:
    """
    Синхронная обёртка для вызова из обычного кода.
    Если уже внутри asyncio.run — использует существующий event loop.
    """
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Внутри уже работающего loop — создаём задачу
            return asyncio.run_coroutine_threadsafe(
                run_meeting(agent_a, agent_b, location, city_state),
                loop,
            ).result()
        else:
            return loop.run_until_complete(
                run_meeting(agent_a, agent_b, location, city_state)
            )
    except RuntimeError:
        # Loop не существует — создаём
        return asyncio.run(
            run_meeting(agent_a, agent_b, location, city_state)
        )
