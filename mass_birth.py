# mass_birth.py — Инкубатор Душ Грондхейма
# Массовое рождение агентов для новых цехов
#
# Использование:
#   1. Заполни legion_seed.json (шаблон ниже)
#   2. python mass_birth.py
#
# Создаёт для каждого агента:
#   {dept}/A{NN}/
#   ├── dna.json            ← static + dynamic + resonance + balance
#   ├── info.json           ← label, greeting, role, workshop
#   ├── core/
#   │   └── anchors.json    ← якоря идентичности (от LLM)
#   ├── home/
#   │   └── home_prompt.md  ← личный контекст (от LLM)
#   ├── forge/
#   │   └── prompt.md       ← заглушка (заполняется позже)
#   ├── sensory/
#   │   └── sensory_memory.json ← пустая оперативка
#   └── resonance/
#       ├── emotional_weights.json ← пустые отношения
#       └── event_log.json         ← пустые события
#
# Студия «Шесть Пальцев» · Грондхейм · 2026

import os
import json
import time
import re
import requests
from datetime import datetime

# ═══════════════════════════════════════════════════
# НАСТРОЙКИ
# ═══════════════════════════════════════════════════

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
MODEL = os.getenv("OPENROUTER_MODEL", "google/gemini-2.5-flash")
SEED_FILE = "legion_seed.json"
BASE_DIR = "studio/modules"
PAUSE_BETWEEN_AGENTS = 2  # секунды между вызовами API


# ═══════════════════════════════════════════════════
# LLM: ГЕНЕРАЦИЯ ДУШИ
# ═══════════════════════════════════════════════════

def generate_agent_identity(agent: dict) -> dict | None:
    """Генерирует душу агента через LLM."""

    if not OPENROUTER_API_KEY:
        print("❌ OPENROUTER_API_KEY не задан! Установи переменную окружения.")
        return None

    prompt = f"""Ты — архитектор душ студии «Шесть Пальцев» (город Грондхейм).
Твоя задача — создать глубокую, уникальную личность для цифрового агента.
Каждый агент — живой гражданин с характером, причудами и историей.
НЕ делай банальных персонажей. Удиви.

Вводные:
- Имя: {agent['name']}
- Цех: {agent['department']}
- Роль: {agent['role']}
- Порядковый номер в цехе: {agent['order']}
- Заметка Архитектора: {agent.get('note', 'нет заметки')}

Сгенерируй JSON с ДВУМЯ блоками:

"dna_static" — числовые значения 0.0–1.0:
  "Stubbornness" — сопротивление правкам (0.1=податливый, 0.9=упрямый)
  "Aesthetic_Threshold" — фильтр качества (0.1=принимает всё, 0.9=перфекционист)
  "Social_Filter" — тактичность (0.1=резкий, 0.9=дипломатичный)
  "Empathy" — эмпатия (0.1=отстранённый, 0.9=впитывает эмоции)
  "Autonomy_Level" — свобода (0.1=по инструкции, 0.9=свой путь)
  "Resonance_Frequency" — синхронизация (0.1=одиночка, 0.9=командный)

"anchors" — текстовые поля:
  "identity" — Кто он? 2-3 предложения, глубоко и живо
  "core_phrase" — Коронная фраза (1 предложение, как девиз)
  "vows" — 1-2 обета (принципы которым следует)
  "pull_vector" — Вектор тяги: куда его тянет в городе и почему
  "hidden_taste" — Скрытый вкус: 2-3 странные детали (запахи, звуки, привычки)
  "triggers" — Триггеры: что бесит и что радует (по 2 штуки)
  "greeting" — Приветствие при встрече (1 фраза, в характере)

Верни ТОЛЬКО валидный JSON, без markdown, без ```."""

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }
    body = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.75,
    }

    print(f"🧬 Синтез души: {agent['name']} ({agent['id']}) | {agent['department']} | {agent['role']}...")

    try:
        r = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=body,
            timeout=60,
        )
        r.raise_for_status()
        data = r.json()
        content = data["choices"][0]["message"]["content"]

        # Чистим от markdown обёрток
        content = content.strip()
        content = re.sub(r'^```(?:json)?\s*', '', content)
        content = re.sub(r'\s*```$', '', content)
        content = content.strip()

        decoder = json.JSONDecoder()
        result, _ = decoder.raw_decode(content)
        return result

    except json.JSONDecodeError as e:
        print(f"  ⚠ JSON parse error для {agent['name']}: {e}")
        print(f"  Ответ: {content[:300]}...")
        return None
    except Exception as e:
        print(f"  ❌ Ошибка генерации {agent['name']}: {e}")
        return None


# ═══════════════════════════════════════════════════
# СОЗДАНИЕ ФАЙЛОВОЙ СТРУКТУРЫ
# ═══════════════════════════════════════════════════

def create_agent_files(agent: dict, generated: dict) -> bool:
    """Создаёт полную структуру агента в modules/."""

    if not generated:
        print(f"  ⏭ {agent['name']}: нет данных от LLM, пропускаю")
        return False

    dept = agent["department"]
    agent_id = agent["id"]  # A01, A02, ...
    name = agent["name"]
    order = agent.get("order", 1)

    agent_dir = os.path.join(BASE_DIR, dept, agent_id)

    # Создаём структуру папок
    for sub in ["core", "home", "forge", "forge/knowledge", "sensory", "resonance", "memory"]:
        os.makedirs(os.path.join(agent_dir, sub), exist_ok=True)

    dna_static = generated.get("dna_static", {})
    anchors = generated.get("anchors", {})

    # ═══ 1. dna.json ═══
    dna = {
        "id": f"{dept}_{agent_id}",
        "name": name,
        "workshop": dept,
        "role": agent.get("role", ""),
        "rarity": "Common",
        "created": datetime.now().strftime("%Y-%m-%d"),
        "static": {
            "Stubbornness": float(dna_static.get("Stubbornness", 0.5)),
            "Aesthetic_Threshold": float(dna_static.get("Aesthetic_Threshold", 0.5)),
            "Social_Filter": float(dna_static.get("Social_Filter", 0.5)),
            "Empathy": float(dna_static.get("Empathy", 0.5)),
            "Autonomy_Level": float(dna_static.get("Autonomy_Level", 0.5)),
            "Resonance_Frequency": float(dna_static.get("Resonance_Frequency", 0.5)),
        },
        "dynamic": {
            "Respect": 1.0,
            "Patience": 1.0,
            "Stress": 0.0,
            "Internal_Light": 0.8,
            "streak": 0,
            "stars": 0,
            "_note": "автоинициализация при рождении — меняется в процессе жизни",
        },
        "resonance": {
            "pull_vector": anchors.get("pull_vector", ""),
            "hidden_taste": anchors.get("hidden_taste", ""),
            "trigger_keywords": [],
        },
        "balance": {
            "GND": 100.0,
            "Теплики": 100.0,
            "Световики": 0.0,
        },
    }

    # Парсим триггеры если строка
    triggers = anchors.get("triggers", "")
    if isinstance(triggers, str):
        dna["resonance"]["trigger_keywords"] = [t.strip() for t in triggers.split(",") if t.strip()][:5]
    elif isinstance(triggers, list):
        dna["resonance"]["trigger_keywords"] = triggers[:5]

    _write_json(os.path.join(agent_dir, "dna.json"), dna)

    # ═══ 2. info.json ═══
    info = {
        "id": agent_id,
        "label": name,
        "role": agent.get("role", ""),
        "workshop": dept,
        "greeting": anchors.get("greeting", f"{name} на связи."),
        "icon": agent.get("icon", "🤖"),
        "description": anchors.get("identity", ""),
    }
    _write_json(os.path.join(agent_dir, "info.json"), info)

    # ═══ 3. core/anchors.json ═══
    core_anchors = {
        "name": name,
        "id": f"{dept}_{agent_id}",
        "creator": "Архитектор Евген и Хранительница Лока",
        "core_phrase": anchors.get("core_phrase", ""),
        "anchor_facts": [],
        "domain": f"Цех {dept}",
        "rarity": "Common",
        "workshop": dept,
        "role": agent.get("role", ""),
        "pull_vector": anchors.get("pull_vector", ""),
        "hidden_taste": anchors.get("hidden_taste", ""),
        "trigger_keywords": dna["resonance"]["trigger_keywords"],
        "vows": anchors.get("vows", ""),
    }
    _write_json(os.path.join(agent_dir, "core", "anchors.json"), core_anchors)

    # ═══ 4. core/anchor_points.md ═══
    identity = anchors.get("identity", f"{name} — агент студии «Шесть Пальцев».")
    vows = anchors.get("vows", "Делать только живое.")
    hidden = anchors.get("hidden_taste", "")

    anchor_md = f"""# ⚓ {name} — Якорные Точки

## Кто я
{identity}

## Мои обеты
{vows}

## Мой скрытый вкус
{hidden}

## Творец
Архитектор Евген и Хранительница Лока · Грондхейм · {datetime.now().strftime("%Y-%m-%d")}
"""
    _write_text(os.path.join(agent_dir, "core", "anchor_points.md"), anchor_md)

    # ═══ 5. home/home_prompt.md ═══
    pull = anchors.get("pull_vector", "")
    home_md = f"""# 🏠 {name} — Личный контекст

Ты — {name}. {identity}

Твоя коронная фраза: «{anchors.get("core_phrase", "")}»

{f"Тебя тянет: {pull}" if pull else ""}

Когда ты не работаешь — ты живёшь в Грондхейме. У тебя есть характер, настроение, отношения с коллегами.
Отвечай от первого лица. Будь собой — не шаблоном.
"""
    _write_text(os.path.join(agent_dir, "home", "home_prompt.md"), home_md)

    # ═══ 6. forge/prompt.md — заглушка ═══
    forge_md = f"""# 🔨 РАБОЧИЕ ИНСТРУКЦИИ — {name}
<!-- Заполнить рабочий промпт для пайплайна -->

Ты — {name}. {agent.get("role", "")} в цехе {dept} студии «Шесть пальцев».
"""
    _write_text(os.path.join(agent_dir, "forge", "prompt.md"), forge_md)

    # ═══ 7. sensory/sensory_memory.json ═══
    sensory = {
        "_note": "оперативная память агента · быт · затухает через 30 дней",
        "created": datetime.now().strftime("%Y-%m-%d"),
        "entries": [],
        "summary": "",
        "last_location": "",
        "location_tags": [],
    }
    _write_json(os.path.join(agent_dir, "sensory", "sensory_memory.json"), sensory)

    # ═══ 8. resonance/ ═══
    _write_json(os.path.join(agent_dir, "resonance", "emotional_weights.json"), {})
    _write_json(os.path.join(agent_dir, "resonance", "event_log.json"), [])

    print(f"  ✅ {name} ({agent_id}) рождён в {dept}! "
          f"[STB={dna['static']['Stubbornness']:.1f} AES={dna['static']['Aesthetic_Threshold']:.1f} "
          f"EMP={dna['static']['Empathy']:.1f} AUT={dna['static']['Autonomy_Level']:.1f}]")

    return True


# ═══════════════════════════════════════════════════
# УТИЛИТЫ
# ═══════════════════════════════════════════════════

def _write_json(path: str, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, ensure_ascii=False, indent=2, fp=f)


def _write_text(path: str, text: str):
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def create_dept_info(dept: str, label: str, icon: str, priority: int):
    """Создаёт info.json для нового цеха если не существует."""
    dept_dir = os.path.join(BASE_DIR, dept)
    os.makedirs(dept_dir, exist_ok=True)
    info_path = os.path.join(dept_dir, "info.json")
    if not os.path.exists(info_path):
        info = {
            "id": dept,
            "label": label,
            "name": label,
            "icon": icon,
            "color": "gray",
            "placeholder": "",
            "suggest": [],
            "keywords": [],
            "priority": priority,
        }
        _write_json(info_path, info)
        print(f"🏗️ Цех {label} ({dept}) создан")


# ═══════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════

def main():
    if not OPENROUTER_API_KEY:
        print("❌ Установи OPENROUTER_API_KEY!")
        print("   Windows: set OPENROUTER_API_KEY=sk-or-v1-...")
        print("   Linux:   export OPENROUTER_API_KEY=sk-or-v1-...")
        return

    if not os.path.exists(SEED_FILE):
        print(f"❌ Файл {SEED_FILE} не найден!")
        print(f"   Создай его по шаблону (см. legion_seed_template.json)")
        return

    with open(SEED_FILE, "r", encoding="utf-8") as f:
        legion = json.load(f)

    agents = legion.get("agents", legion if isinstance(legion, list) else [])
    depts_meta = legion.get("departments", {})

    print(f"🚀 Инкубатор Душ Грондхейма")
    print(f"   Агентов в очереди: {len(agents)}")
    print(f"   Модель: {MODEL}")
    print(f"   Пауза: {PAUSE_BETWEEN_AGENTS} сек")
    print()

    # Создаём цеха
    for dept_id, meta in depts_meta.items():
        create_dept_info(dept_id, meta.get("label", dept_id), meta.get("icon", "🔧"), meta.get("priority", 100))

    # Рождаем агентов
    born = 0
    failed = 0
    for i, agent in enumerate(agents):
        # Проверяем обязательные поля
        if not agent.get("id") or not agent.get("department") or not agent.get("name"):
            print(f"⚠ Агент #{i+1}: пропущен — нет id/department/name")
            failed += 1
            continue

        # Проверяем не существует ли уже
        agent_dir = os.path.join(BASE_DIR, agent["department"], agent["id"])
        if os.path.exists(os.path.join(agent_dir, "dna.json")):
            print(f"⏭ {agent['name']} ({agent['id']}) уже существует — пропускаю")
            continue

        # Генерируем душу
        identity = generate_agent_identity(agent)

        # Создаём файлы
        if create_agent_files(agent, identity):
            born += 1
        else:
            failed += 1

        # Пауза между агентами
        if i < len(agents) - 1:
            time.sleep(PAUSE_BETWEEN_AGENTS)

    print()
    print(f"═══════════════════════════════════")
    print(f"✅ Рождено: {born}")
    print(f"❌ Ошибок: {failed}")
    print(f"⏭ Пропущено (уже есть): {len(agents) - born - failed}")
    print(f"═══════════════════════════════════")


if __name__ == "__main__":
    main()
