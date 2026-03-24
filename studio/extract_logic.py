"""
extract_logic.py — Извлекает логику Web Story из вывода Артура (A12)
Вход:  A12_arthur_output.json / .md  (финальный файл пайплайна)
Выход: logic_map.json                — рядом с manifest.json в папке проекта

Что вытаскивает:
  scenes[]        — порядок сцен, тексты, эмоции         (Маркус + Софи + Рина)
  branches[]      — логика выборов и переходов             (Лана + Люми)
  interactions[]  — что происходит при клике              (Люми)
  achievements[]  — условия бейджей                       (Бруно)
  sound_map[]     — звук и тишина по сценам               (Рэй)
"""

import json
import re
import sys
from pathlib import Path


# ────────────────────────────────────────────────────────────
# ХЕЛПЕРЫ
# ────────────────────────────────────────────────────────────

def _safe_list(obj, key) -> list:
    val = obj.get(key) if isinstance(obj, dict) else None
    return val if isinstance(val, list) else []

def _safe_dict(obj, key) -> dict:
    val = obj.get(key) if isinstance(obj, dict) else None
    return val if isinstance(val, dict) else {}

def _is_stub(val) -> bool:
    """Проверяет, является ли значение заглушкой {{inherit}}."""
    return isinstance(val, str) and "inherit" in val


def _parse_file(path: Path) -> dict:
    """Читает JSON из .json или .md файла (SYSTEM_JSON_START блок)."""
    text = path.read_text(encoding="utf-8")

    if path.suffix.lower() == ".json":
        return json.loads(text)

    # .md — ищем SYSTEM_JSON_START ... SYSTEM_JSON_END
    pattern = r'SYSTEM_JSON_START[^\n]*\n(.*?)\n[^\n]*SYSTEM_JSON_END'
    match = re.search(pattern, text, re.DOTALL)
    if match:
        raw = match.group(1).strip().strip("`").strip()
        if raw.startswith("json"):
            raw = raw[4:].strip()
        return json.loads(raw)

    # Фоллбэк: fenced ```json ... ```
    fence = re.search(r'`{3}json\s*\n(\{.*?\})\s*\n`{3}', text, re.DOTALL)
    if fence:
        return json.loads(fence.group(1))

    raise ValueError(f"JSON не найден в {path.name}")


def _resolve_chain(data: dict) -> dict:
    """
    Извлекает chain_data и «разворачивает» all_agents_output
    в плоскую структуру, которую ожидают extract_* функции.

    A12 Артур хранит агентов по пути:
      chain_data.all_agents_output.<run>.03_markus.my_output → markus
    Нужно развернуть в:
      chain["markus_structure"] = markus.my_output
    """
    chain = data.get("chain_data", {})
    if not chain:
        chain = data.get("my_output", {}).get("chain_data", {})
    if not chain:
        return {}

    # Если прямые ключи уже есть — используем как есть (A05 формат)
    if chain.get("markus_structure") or chain.get("lana_flow"):
        return chain

    # Разворачиваем all_agents_output (A12 формат)
    aao = chain.get("all_agents_output", {})
    if not isinstance(aao, dict):
        return chain

    # Маппинг: ожидаемый ключ → agent_key в all_agents_output
    AGENT_MAP = {
        "markus_structure":    "03_markus",
        "sophie_scenario":     "04_sophie",
        "lana_flow":           "05_lana",
        "oliver_visuals":      "06_oliver",
        "lumi_interactions":   "07_lumi",
        "bruno_gamification":  "08_bruno",
        "nova_prompts":        "09_nova",
        "ray_sound":           "10_ray",
        "rina_gate":           "11_iris",
    }

    for run_key, run_val in aao.items():
        if not isinstance(run_val, dict):
            continue
        for logic_key, agent_key in AGENT_MAP.items():
            if logic_key in chain and not _is_stub(chain[logic_key]):
                continue  # уже есть реальные данные
            agent = run_val.get(agent_key, {})
            if isinstance(agent, dict) and isinstance(agent.get("my_output"), dict):
                chain[logic_key] = agent["my_output"]
                print(f"    🔗 {logic_key} ← {agent_key}.my_output")

    return chain


# ────────────────────────────────────────────────────────────
# ИЗВЛЕЧЕНИЕ СЦЕН
# Источники: markus_structure → sophie_scenario → rina_gate
# ────────────────────────────────────────────────────────────

def extract_scenes(chain: dict) -> list:
    scenes = []
    seen_ids = set()

    # 1. Маркус — структура сцен (скелет)
    markus = chain.get("markus_structure", {})
    if _is_stub(markus):
        markus = {}
    for s in _safe_list(markus, "scenes"):
        # Поддержка обоих форматов: scene_id / scene_number
        sid = s.get("scene_id") or s.get("id") or f"scene_{int(s.get('scene_number', len(scenes)+1)):02d}"
        if not sid or sid in seen_ids:
            continue
        seen_ids.add(sid)
        scenes.append({
            "scene_id":   sid,
            "scene_name": s.get("scene_name") or s.get("name") or s.get("title", ""),
            "order":      s.get("order") or s.get("scene_number") or s.get("index", len(scenes) + 1),
            "type":       s.get("type", "scene"),
            "emotion":    s.get("emotion") or s.get("emotional_bit", ""),
            "text":       "",
            "speaker":    "",
            "key_lines":  s.get("key_lines", []),
            "location":   s.get("location", ""),
        })

    # 2. Рина / Ирис — финальные тексты (приоритет)
    rina = chain.get("rina_gate", {})
    if _is_stub(rina):
        rina = {}
    rina_scenes = (_safe_list(rina, "scenes_final")
                   or _safe_list(rina, "scenes")
                   or _safe_list(rina, "polish_notes"))
    for rs in rina_scenes:
        if not isinstance(rs, dict):
            continue
        sid = rs.get("scene_id") or rs.get("id", "")
        match = next((s for s in scenes if s["scene_id"] == sid), None)
        if match:
            match["text"]    = rs.get("dialogue") or rs.get("text", match["text"])
            match["speaker"] = rs.get("speaker", match["speaker"])
        elif sid and sid not in seen_ids:
            seen_ids.add(sid)
            scenes.append({
                "scene_id":   sid,
                "scene_name": rs.get("name", ""),
                "order":      len(scenes) + 1,
                "type":       "scene",
                "emotion":    rs.get("emotion", ""),
                "text":       rs.get("dialogue") or rs.get("text", ""),
                "speaker":    rs.get("speaker", ""),
            })

    # 3. Софи — добираем текст если Рина не дала
    sophie = chain.get("sophie_scenario", {})
    if _is_stub(sophie):
        sophie = {}
    sophie_scenes = _safe_list(sophie, "scenes_full") or _safe_list(sophie, "content_review")
    for ss in sophie_scenes:
        if not isinstance(ss, dict):
            continue
        sid = ss.get("scene_id") or ss.get("id", "")
        match = next((s for s in scenes if s["scene_id"] == sid), None)
        if match and not match["text"]:
            match["text"]    = ss.get("dialogue") or ss.get("text", "")
            match["speaker"] = ss.get("speaker") or match["speaker"]

    # Заполняем текст из key_lines Маркуса если ничего нет
    for s in scenes:
        if not s["text"] and s.get("key_lines"):
            s["text"] = " | ".join(str(kl) for kl in s["key_lines"] if kl)

    scenes.sort(key=lambda s: s["order"])
    return scenes


# ────────────────────────────────────────────────────────────
# ИЗВЛЕЧЕНИЕ ВЕТОК / ПЕРЕХОДОВ
# Источник: lana_flow
# ────────────────────────────────────────────────────────────

def extract_branches(chain: dict) -> list:
    lana = chain.get("lana_flow", {})
    if _is_stub(lana):
        return []

    branches = []
    screens = _safe_list(lana, "screens")

    if not screens:
        # user_flows может быть dict или list
        user_flows = lana.get("user_flows", {})
        if isinstance(user_flows, dict):
            for flow_key, flow_val in user_flows.items():
                if isinstance(flow_val, dict):
                    for step in _safe_list(flow_val, "steps") or _safe_list(flow_val, "screens"):
                        screens.append(step)
        elif isinstance(user_flows, list):
            screens = user_flows

    # navigation
    nav = lana.get("navigation", {})
    if isinstance(nav, dict):
        for nav_item in _safe_list(nav, "flow") or _safe_list(nav, "screens"):
            if isinstance(nav_item, dict) and nav_item not in screens:
                screens.append(nav_item)

    for screen in screens:
        if not isinstance(screen, dict):
            continue
        sid = screen.get("scene_id") or screen.get("screen_id") or screen.get("step", "")
        choices = (_safe_list(screen, "choices")
                   or _safe_list(screen, "branches")
                   or _safe_list(screen, "options"))
        if not choices:
            nxt = screen.get("next") or screen.get("next_scene") or screen.get("leads_to")
            if nxt:
                branches.append({
                    "from_scene":   sid,
                    "type":         "linear",
                    "choices":      [],
                    "default_next": nxt,
                })
            continue

        branch_entry = {
            "from_scene":   sid,
            "type":         "choice",
            "choices":      [],
            "default_next": None,
        }
        for ch in choices:
            if not isinstance(ch, dict):
                continue
            branch_entry["choices"].append({
                "label":      ch.get("label") or ch.get("text", ""),
                "element_id": ch.get("element_id") or ch.get("button_id", ""),
                "next_scene": ch.get("next_scene") or ch.get("next") or ch.get("leads_to", ""),
                "condition":  ch.get("condition", ""),
            })
        branches.append(branch_entry)

    return branches


# ────────────────────────────────────────────────────────────
# ИЗВЛЕЧЕНИЕ ИНТЕРАКТИВА
# Источник: lumi_interactions
# ────────────────────────────────────────────────────────────

def extract_interactions(chain: dict) -> list:
    lumi = chain.get("lumi_interactions", {})
    if _is_stub(lumi):
        return []

    interactions = []
    imap = _safe_list(lumi, "interaction_map") or _safe_list(lumi, "interactions")
    for item in imap:
        if not isinstance(item, dict):
            continue
        interactions.append({
            "interaction_id": item.get("interaction_id") or item.get("id", ""),
            "scene_id":       item.get("scene_id", ""),
            "trigger":        item.get("trigger", ""),
            "action":         item.get("action", ""),
            "feedback":       item.get("feedback", ""),
            "states":         _safe_dict(item, "states"),
            "elements":       _safe_list(item, "elements"),
        })

    micro = _safe_dict(lumi, "micro_interactions")
    if micro:
        interactions.append({
            "interaction_id": "micro",
            "scene_id":       "*",
            "trigger":        "various",
            "action":         "micro-feedback",
            "feedback":       micro,
            "states":         {},
        })

    return interactions


# ────────────────────────────────────────────────────────────
# ИЗВЛЕЧЕНИЕ ДОСТИЖЕНИЙ
# Источник: bruno_gamification
# ────────────────────────────────────────────────────────────

def extract_achievements(chain: dict) -> list:
    bruno = chain.get("bruno_gamification", {})
    if _is_stub(bruno):
        return []

    achievements = []
    for ach in _safe_list(bruno, "achievements"):
        if not isinstance(ach, dict):
            continue
        ach_id = ach.get("id") or ach.get("achievement_id", "")
        achievements.append({
            "achievement_id": ach_id,
            "name":           ach.get("name", ""),
            "condition":      ach.get("condition", ""),
            "scene_id":       ach.get("scene_id", ""),
            "icon":           ach.get("icon", ""),
            "reward":         ach.get("reward", ""),
            "badge_file":     f"badges/badge_{ach_id}.png",
            "animation":      "scale 0→1.2→1 / 250ms spring",
            "duration_ms":    2000,
            "sfx":            "sfx_achievement",
        })

    reward = _safe_dict(bruno, "reward_system")
    if reward:
        achievements.append({
            "achievement_id": "_reward_system",
            "name":           "Система наград",
            "condition":      "meta",
            "reward":         reward,
        })

    return achievements


# ────────────────────────────────────────────────────────────
# ИЗВЛЕЧЕНИЕ ЗВУКОВОЙ КАРТЫ
# Источник: ray_sound
# ────────────────────────────────────────────────────────────

def extract_sound_map(chain: dict) -> list:
    ray = chain.get("ray_sound", {})
    if _is_stub(ray):
        return []

    sound_map = []
    silence_zones = [
        s.get("scene_id", "") for s in _safe_list(
            _safe_dict(ray, "sound_concept"), "silence_zones"
        )
    ]

    for entry in _safe_list(ray, "emotion_sound_map"):
        if not isinstance(entry, dict):
            continue
        sid = entry.get("scene_id", "")
        sound_map.append({
            "scene_id":  sid,
            "emotion":   entry.get("emotion", ""),
            "intensity": entry.get("intensity", ""),
            "music":     entry.get("music", ""),
            "ambient":   entry.get("ambient", ""),
            "voice":     entry.get("voice", ""),
            "sfx":       entry.get("sfx", ""),
            "silence":   sid in silence_zones,
        })

    return sound_map


# ────────────────────────────────────────────────────────────
# ГЛАВНАЯ ФУНКЦИЯ
# ────────────────────────────────────────────────────────────

def extract_logic(arthur_path: str, output_path: str = None) -> dict:
    """Читает файл Артура (.json или .md), собирает logic_map.json."""
    src = Path(arthur_path)
    if not src.exists():
        raise FileNotFoundError(f"Файл не найден: {src}")

    print(f"📖 Читаю: {src.name}")
    data = _parse_file(src)

    chain = _resolve_chain(data)

    project_id = (
        data.get("project_id")
        or data.get("my_output", {}).get("deliverables", {}).get("project_id")
        or data.get("my_output", {}).get("final_dna", {}).get("id")
        or src.stem
    )

    print(f"  🎯 project_id: {project_id}")

    scenes       = extract_scenes(chain)
    branches     = extract_branches(chain)
    interactions = extract_interactions(chain)
    achievements = extract_achievements(chain)
    sound_map    = extract_sound_map(chain)

    print(f"  📋 Сцен:        {len(scenes)}")
    print(f"  🔀 Веток:       {len(branches)}")
    print(f"  🖱️  Интерактив:  {len(interactions)}")
    print(f"  🏆 Достижений:  {len(achievements)}")
    print(f"  🎵 Звук-карта:  {len(sound_map)}")

    logic_map = {
        "project_id":   project_id,
        "source_file":  src.name,
        "_note": (
            "Открывай рядом с manifest.json. "
            "manifest = ЧТО генерировать (картинки). "
            "logic_map = КАК это работает (логика, тексты, переходы)."
        ),
        "scenes": scenes,
        "branches": branches,
        "interactions": interactions,
        "achievements": achievements,
        "sound_map": sound_map,
        "assembly_hints": {
            "scene_order":   "scenes[].order — сортируй по нему",
            "scene_text":    "scenes[].text + scenes[].speaker",
            "next_scene":    "branches[from_scene=X].default_next (линейно) ИЛИ branches[].choices[].next_scene (выбор)",
            "on_click":      "interactions[scene_id=X].action",
            "badge_trigger": "achievements[].condition — проверяй после каждого выбора",
            "sound_on_scene":"sound_map[scene_id=X] — music/sfx/silence для этой сцены",
        }
    }

    if output_path is None:
        output_path = src.parent / f"{project_id}_logic_map.json"

    out = Path(output_path)
    out.write_text(json.dumps(logic_map, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n✅ Готово: {out}")

    return logic_map


# ────────────────────────────────────────────────────────────
# ЗАПУСК
# ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Использование: python extract_logic.py <путь_к_A12.json/.md> [выходной_файл.json]")
        sys.exit(1)

    arthur_path = sys.argv[1]
    out_path    = sys.argv[2] if len(sys.argv) > 2 else None

    extract_logic(arthur_path, out_path)
