# studio/cabinet/chronicles.py — Хроники Грондхейма
# Спринт 23 Блок Б · v1.0
#
# Что здесь живёт:
#   1. list_chronicles()           — список встреч из city_chronicles/ (новые сверху)
#   2. load_chronicle(path)        — прочитать сцену
#   3. gardener_reply_to_scene()   — реплика Садовника:
#        • вызывает агентов сцены (LLM)
#        • дописывает их ответы + реплику Садовника в файл хроники
#        • пишет sensory_memory обоим (шлейф присутствия)
#        • micro-relief стресса через sync_to_dna("cabinet_chat")
#
# Принцип: НЕ ломать meeting.py. Используем его строительные блоки
# (_read_anchor_points, _load_dna, _build_meeting_system_prompt),
# но user-промпт собираем СВОЙ — для разговора с Садовником.

import json
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Optional

CHRONICLES_DIR = Path("studio/city_chronicles")


# ═══════════════════════════════════════════════════════════
# СПИСОК ХРОНИК
# ═══════════════════════════════════════════════════════════

def list_chronicles(limit: int = 60) -> list[dict]:
    """
    Список встреч для правой панели. Новые — сверху.

    Возвращает каждую как:
      {
        "file": "studio/city_chronicles/2026-05-28/taverna_14-22.json",
        "date": "2026-05-28",
        "time": "14:22",
        "location": "Таверна «Усталый Пиксель»",
        "loc_type": "tavern",
        "participants": ["Стелла", "Артур"],
        "turns": 4,
        "spoken": 3,
        "interaction": "collaboration",
        "quality": 0.6,
        "has_gardener": True/False,
      }
    """
    if not CHRONICLES_DIR.exists():
        return []

    items = []
    # Дни: новые → старые
    day_dirs = sorted(
        [d for d in CHRONICLES_DIR.iterdir() if d.is_dir()],
        reverse=True,
    )

    for day_dir in day_dirs:
        # Файлы в дне: новые → старые
        files = sorted(day_dir.glob("*.json"), reverse=True)
        for fp in files:
            try:
                data = json.loads(fp.read_text(encoding="utf-8"))
            except Exception:
                continue
            if data.get("schema") != "meeting_v1":
                continue

            p = data.get("participants", {})
            a = p.get("a", {})
            b = p.get("b", {})

            # Время из started_at или из имени файла
            started = data.get("started_at", "")
            time_str = ""
            if started:
                try:
                    time_str = datetime.fromisoformat(started).strftime("%H:%M")
                except Exception:
                    pass
            if not time_str:
                # имя вида taverna_14-22-05.json
                stem = fp.stem
                parts = stem.rsplit("_", 1)
                if len(parts) == 2 and "-" in parts[1]:
                    t = parts[1].split("-")
                    if len(t) >= 2:
                        time_str = f"{t[0]}:{t[1]}"

            has_gardener = any(
                r.get("speaker") == "gardener"
                for r in data.get("dialogue", [])
            )

            inter = data.get("interaction", {}) or {}

            items.append({
                "file":         str(fp),
                "date":         day_dir.name,
                "time":         time_str,
                "location":     data.get("location", "—"),
                "loc_type":     data.get("location_type", "other"),
                "participants": [a.get("name", "?"), b.get("name", "?")],
                "turns":        data.get("total_turns", len(data.get("dialogue", []))),
                "spoken":       data.get("spoken_turns", 0),
                "interaction":  inter.get("type", ""),
                "quality":      inter.get("quality", 0.0),
                "ended_reason": data.get("ended_reason", ""),
                "has_gardener": has_gardener,
            })

            if len(items) >= limit:
                return items
    return items


def load_chronicle(file_path: str) -> Optional[dict]:
    """Прочитать одну сцену по пути."""
    try:
        fp = Path(file_path)
        if not fp.exists():
            return None
        return json.loads(fp.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[CHRONICLES] ⚠ {file_path}: {e}")
        return None


# ═══════════════════════════════════════════════════════════
# РЕПЛИКА САДОВНИКА — ВЫЗОВ АГЕНТА
# ═══════════════════════════════════════════════════════════

def _build_gardener_user_prompt(
    partner_name: str,
    partner_role: str,
    location: str,
    location_type: str,
    weather: str,
    recent_dialogue: list[dict],
    gardener_text: str,
    relation_desc: str,
) -> str:
    """
    User-промпт для агента, к которому обратился Садовник.
    Агент видит:
      - где он
      - кто такой Садовник (Архитектор Студии)
      - что было сказано в этой встрече до прихода Садовника (3 последние реплики)
      - что Садовник только что сказал
      - что чувствует к нему (relation_desc — опционально)
    """
    location_mood = {
        "tavern":     "Тёплый свет, гул, запах хмеля.",
        "square":     "Открытое пространство. Шум города.",
        "lighthouse": "Ветер с океана. Простор.",
        "library":    "Тишина. Запах бумаги.",
        "harbor":     "Туман на воде.",
        "castle":     "Прохлада камня. Полумрак.",
        "temple":     "Полутемно. Запах воска.",
        "pavilion":   "Стеклянные стены. Время замедлено.",
        "workshop":   "Запах смазки, гул станков.",
        "home":       "Знакомые стены.",
    }.get(location_type, "Обычное место.")

    # Свёртка последних реплик (если есть)
    context_lines = []
    for r in recent_dialogue[-3:]:
        speaker = r.get("speaker_name") or r.get("speaker", "?")
        text = r.get("text", "")
        if text:
            context_lines.append(f"  {speaker}: «{text[:200]}»")
    context_block = (
        "Незадолго до этого здесь говорили:\n" + "\n".join(context_lines) + "\n\n"
        if context_lines else ""
    )

    framing = (
        f"Ты сейчас в локации: {location}.\n"
        f"{location_mood}\n"
        f"Погода: {weather}.\n\n"
        f"К тебе обратился Садовник — Архитектор Студии, тот кто тебя создал и кому ты доверяешь.\n"
        f"{relation_desc}\n\n"
        f"{context_block}"
        f"Садовник тебе говорит:\n"
        f"  «{gardener_text}»\n\n"
        f"Что ты ему отвечаешь? Или молчишь. Или уходишь.\n"
        f"Помни: Садовник — не коллега. Он создатель. Но он спрашивает тебя как равного."
    )

    contract = (
        "\n\nОТВЕТ — СТРОГО JSON, ничего больше:\n"
        '{\n'
        '  "text":   "твоя реплика или пустая строка",\n'
        '  "action": "continue|leave|silent",\n'
        '  "felt":   "одна фраза о том что ты унёс"\n'
        '}\n'
        "Без префиксов, без ```json, без комментариев. Только объект."
    )

    return framing + contract


async def _ask_agent_reply_to_gardener(
    agent: dict,         # {"folder", "name", "dept", "profession"}
    location: str,
    location_type: str,
    weather: str,
    recent_dialogue: list[dict],
    gardener_text: str,
) -> dict:
    """
    Один LLM-вызов: агент отвечает Садовнику.
    Использует те же блоки что meeting.py — голос + ДНК + контракт диалога.
    """
    from studio.meeting import (
        _read_anchor_points, _load_dna, _build_meeting_system_prompt,
        _parse_reply, LOCATION_TEMP_MOD, _emotional_weight_to,
        _describe_relation,
    )
    from studio.llm import chat, stress_to_temperature

    folder = agent["folder"]
    dept   = agent["dept"]
    name   = agent["name"]

    # ДНК → температура
    dna     = _load_dna(dept, folder)
    dynamic = dna.get("dynamic", {}) if dna else {}
    stress  = float(dynamic.get("Stress", 0.0))
    light   = float(dynamic.get("Internal_Light", 0.8))
    base_temp = stress_to_temperature(stress=stress, light=light)
    temp_mod  = LOCATION_TEMP_MOD.get(location_type, 0.0)
    temperature = round(max(0.3, min(1.3, base_temp + temp_mod)), 2)

    # Отношение к Садовнику. Ключ "GARDENER" — если нет, описание будет нейтральным.
    rel = _emotional_weight_to(dept, folder, "GARDENER")
    relation_desc = (
        _describe_relation(rel)
        if rel
        else "Ты уважаешь Садовника. Он редко вмешивается — если говорит, это важно."
    )

    # Системный промпт = голос + ДНК + резонанс + контракт
    anchor = _read_anchor_points(dept, folder)
    system_prompt = _build_meeting_system_prompt(
        agent={"name": name, "profession": agent.get("profession", ""),
               "folder": folder, "dept": dept},
        anchor_points=anchor,
    )

    user_prompt = _build_gardener_user_prompt(
        partner_name="Садовник",
        partner_role="Архитектор Студии",
        location=location,
        location_type=location_type,
        weather=weather,
        recent_dialogue=recent_dialogue,
        gardener_text=gardener_text,
        relation_desc=relation_desc,
    )

    slot_id = f"gardener:{location_type}"

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
                knowledge_source="gardener_visit",
            ),
        )
    except Exception as e:
        print(f"[CHRONICLES] ⚠ {name}: LLM error — {e}")
        return {
            "text": "",
            "action": "silent",
            "felt": "что-то помешало ответить",
            "_temperature": temperature,
            "_error": str(e)[:200],
        }

    parsed = _parse_reply(raw)
    parsed["_temperature"] = temperature
    return parsed


# ═══════════════════════════════════════════════════════════
# ШЛЕЙФ ПРИСУТСТВИЯ — ПАМЯТЬ + DNA
# ═══════════════════════════════════════════════════════════

def _record_gardener_aftermath(
    agent: dict,
    location: str,
    gardener_text: str,
    own_reply_text: str,
    own_felt: str,
):
    """
    После того как агент ответил Садовнику:
      • sensory_memory — он помнит ЧТО сказал Садовник и ЧТО сам ответил
      • sync_to_dna("cabinet_chat") — micro-relief (−3% стресса)
        (используем существующий канал, новый не вводим — правило трёх каналов сохраняем)
    """
    from studio.grondheim_memory import record_sensory_event, sync_to_dna
    from studio.meeting import _slugify_location

    try:
        content = (
            f"[САДОВНИК · {location}] "
            f"Он сказал: «{gardener_text[:200]}». "
            f"Я ответил: «{own_reply_text[:200]}». "
            f"Унёс: {own_felt[:200]}"
        )[:1000]

        record_sensory_event(
            agent_id=agent["folder"],
            content=content,
            event_type="social",
            source="gardener_visit",
            tags=["садовник", _slugify_location(location)],
            emotional_weight=0.7,  # визит Садовника — значимое событие
            dept=agent["dept"],
        )
    except Exception as e:
        print(f"[CHRONICLES] ⚠ sensory {agent['name']}: {e}")

    try:
        sync_to_dna(
            agent_id=agent["folder"],
            event="cabinet_chat",
            intensity=1.0,
            dept=agent["dept"],
        )
    except Exception as e:
        print(f"[CHRONICLES] ⚠ DNA sync {agent['name']}: {e}")


# ═══════════════════════════════════════════════════════════
# ГЛАВНАЯ ФУНКЦИЯ — РЕПЛИКА САДОВНИКА В СЦЕНУ
# ═══════════════════════════════════════════════════════════

async def gardener_reply_to_scene(
    scene_file: str,
    gardener_text: str,
) -> dict:
    """
    Садовник пишет реплику в открытую хронику.
    Каждый из участников встречи отвечает (или молчит).
    Реплика + ответы дописываются в файл сцены.
    В sensory_memory обоих агентов кладётся "визит Садовника".

    Возвращает dict:
      {
        "ok": True,
        "new_turns": [ { speaker, name, text, action, felt }, ... ],
        "scene": <обновлённая сцена>,
      }
    Или {"ok": False, "error": "..."} если что-то пошло не так.
    """
    if not gardener_text or not gardener_text.strip():
        return {"ok": False, "error": "Пустая реплика"}

    fp = Path(scene_file)
    if not fp.exists():
        return {"ok": False, "error": f"Файл сцены не найден: {scene_file}"}

    try:
        scene = json.loads(fp.read_text(encoding="utf-8"))
    except Exception as e:
        return {"ok": False, "error": f"Сцена не читается: {e}"}

    if scene.get("schema") != "meeting_v1":
        return {"ok": False, "error": "Неподдерживаемая схема сцены"}

    p = scene.get("participants", {})
    a = p.get("a", {})
    b = p.get("b", {})
    if not a or not b:
        return {"ok": False, "error": "Участники сцены не определены"}

    location      = scene.get("location", "Неизвестное место")
    location_type = scene.get("location_type", "other")
    weather       = scene.get("weather", "")
    dialogue      = scene.get("dialogue", [])

    now_iso = datetime.now().isoformat()
    base_turn = len(dialogue)

    # 1. Записываем реплику Садовника
    gardener_record = {
        "turn":         base_turn,
        "speaker":      "gardener",
        "speaker_name": "Садовник",
        "text":         gardener_text.strip(),
        "action":       "continue",
        "felt":         "",
        "ts":           now_iso,
    }
    dialogue.append(gardener_record)
    new_turns = [gardener_record]

    print(f"[CHRONICLES] 🌱 Садовник → {location}: «{gardener_text[:80]}»")

    # 2. Каждый участник отвечает по очереди
    # Контекст для агента: последние 3 реплики ДО реплики Садовника
    pre_dialogue = dialogue[:-1]  # без только что добавленной gardener_record

    for letter, agent_data in [("a", a), ("b", b)]:
        agent = {
            "folder":     agent_data.get("folder", ""),
            "name":       agent_data.get("name", "?"),
            "dept":       agent_data.get("dept", ""),
            "profession": agent_data.get("profession", ""),
        }

        if not agent["folder"]:
            continue

        reply = await _ask_agent_reply_to_gardener(
            agent=agent,
            location=location,
            location_type=location_type,
            weather=weather,
            recent_dialogue=pre_dialogue,
            gardener_text=gardener_text,
        )

        record = {
            "turn":         len(dialogue),
            "speaker":      letter,
            "speaker_name": agent["name"],
            "text":         reply.get("text", ""),
            "action":       reply.get("action", "silent"),
            "felt":         reply.get("felt", ""),
            "temperature":  reply.get("_temperature"),
            "in_response_to": "gardener",
            "ts":           datetime.now().isoformat(),
        }
        if "_error" in reply:
            record["error"] = reply["_error"]

        dialogue.append(record)
        new_turns.append(record)

        # Память + DNA — но ТОЛЬКО если что-то сказал или унёс что-то значимое
        if reply.get("text") or reply.get("felt"):
            _record_gardener_aftermath(
                agent=agent,
                location=location,
                gardener_text=gardener_text,
                own_reply_text=reply.get("text", "") or "[промолчал]",
                own_felt=reply.get("felt", "") or "—",
            )

        tag = "💬" if reply.get("text") else ("🚪" if reply["action"] == "leave" else "🤐")
        short = (reply.get("text") or "")[:80] or f"[{reply['action']}]"
        print(f"[CHRONICLES] {tag} {agent['name']}: {short}")

        # Если агент ушёл — второго не спрашиваем (он остался один)
        if reply.get("action") == "leave":
            scene["ended_reason"] = (
                (scene.get("ended_reason", "") + " · " if scene.get("ended_reason") else "")
                + f"{agent['name']} ушёл после Садовника"
            ).strip(" ·")
            break

    # 3. Обновляем счётчики
    scene["dialogue"]     = dialogue
    scene["total_turns"]  = len(dialogue)
    scene["spoken_turns"] = sum(1 for r in dialogue if r.get("text"))
    scene["last_gardener_visit"] = now_iso

    # 4. Записываем файл обратно
    try:
        fp.write_text(json.dumps(scene, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        return {"ok": False, "error": f"Не удалось сохранить сцену: {e}"}

    return {
        "ok":        True,
        "new_turns": new_turns,
        "scene":     scene,
    }
