"""
╔══════════════════════════════════════════════════════════════╗
║  МИГРАЦИЯ: Добавить душу старым агентам                      ║
║  Запускать ОДИН РАЗ из корня студии:                         ║
║    python migrate_agents.py                                  ║
║                                                              ║
║  ЧТО ДЕЛАЕТ:                                                 ║
║    - Сканирует studio/modules/{dept}/{agent}/                ║
║    - Если НЕТ dna.json — создаёт с дефолтными весами        ║
║    - Если НЕТ core/ — создаёт + anchors.json                ║
║    - Если НЕТ home/ — создаёт + home_prompt.md              ║
║    - Если НЕТ resonance/ — создаёт + пустые файлы           ║
║    - Если НЕТ sensory/ — создаёт + пустой sensory_memory    ║
║                                                              ║
║  ЧТО НЕ ТРОГАЕТ:                                            ║
║    - prompt.md (рабочий промпт)                              ║
║    - Базы знаний (.txt файлы)                                ║
║    - info.json (только читает для имени)                     ║
║    - Любые существующие файлы                                ║
║                                                              ║
║  Студия «Шесть Пальцев» · 2026                              ║
╚══════════════════════════════════════════════════════════════╝
"""

import json
from pathlib import Path
from datetime import datetime

MODULES_DIR = Path("studio/modules")
TODAY = datetime.now().strftime("%Y-%m-%d")

# Дефолтные веса — нейтральные, потом подкрутишь руками
DEFAULT_STATIC = {
    "Stubbornness": 0.5,
    "Aesthetic_Threshold": 0.5,
    "Social_Filter": 0.5,
    "Empathy": 0.5,
    "Autonomy_Level": 0.5,
    "Resonance_Frequency": 0.5,
}

DEFAULT_DYNAMIC = {
    "Respect": 1.0,
    "Patience": 1.0,
    "Stress": 0.0,
    "Internal_Light": 0.8,
    "streak": 0,
    "stars": 0,
    "_note": "автоинициализация миграцией — подкрути характер через реестр или кабинет"
}


def read_json(path: Path) -> dict:
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def write_text(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def migrate_agent(agent_dir: Path, dept: str):
    """Добавляет недостающую структуру одному агенту."""
    agent_id = agent_dir.name
    created = []

    # Читаем info.json для имени
    info = read_json(agent_dir / "info.json")
    label = info.get("label", agent_id)
    role = info.get("role", "")

    # ═══ 1. dna.json ═══
    dna_path = agent_dir / "dna.json"
    if not dna_path.exists():
        dna = {
            "id": info.get("registry_id", agent_id),
            "name": label,
            "workshop": dept,
            "role": agent_id,
            "rarity": "",
            "created": TODAY,
            "static": dict(DEFAULT_STATIC),
            "resonance": {
                "pull_vector": "",
                "hidden_taste": "",
                "trigger_keywords": [],
            },
            "dynamic": dict(DEFAULT_DYNAMIC),
            "balance": {
                "GND": 0.0,
                "Теплики": 0.0,
                "Световики": 0.0,
            },
            "_migrated": True,
        }
        write_json(dna_path, dna)
        created.append("dna.json")

    # ═══ 2. core/anchors.json ═══
    core_dir = agent_dir / "core"
    anchors_path = core_dir / "anchors.json"
    if not anchors_path.exists():
        anchors = {
            "name": label,
            "id": agent_id,
            "creator": "[JAM] 6F-Origin",
            "core_phrase": info.get("greeting", ""),
            "anchor_facts": [],
            "domain": "Студия SIX FINGERS",
            "rarity": "",
            "workshop": dept,
            "role": agent_id,
            "pull_vector": "",
            "hidden_taste": "",
            "trigger_keywords": [],
            "_migrated": True,
        }
        write_json(anchors_path, anchors)
        created.append("core/anchors.json")

    # ═══ 3. home/home_prompt.md ═══
    home_dir = agent_dir / "home"
    home_path = home_dir / "home_prompt.md"
    if not home_path.exists():
        home_text = f"""# 🏠 ДОМАШНИЙ КОНТЕКСТ — {label}
<!-- Личная жизнь, история, тайны · Для Храма и личных сессий -->
<!-- Создан миграцией — заполни через реестр или руками -->

## Личная история
— не заполнено —

## Сенсорный отклик
— не заполнено —

## Скрытая история
— не заполнено —

## Вектор тяги (куда идёт в свободное время)
— не определён —

## Стартовый баланс
- 💰 GND: 0
- 🔆 Теплики: 0
- 💡 Световики: 0
"""
        write_text(home_path, home_text)
        created.append("home/home_prompt.md")

    # ═══ 4. resonance/ ═══
    res_dir = agent_dir / "resonance"
    ew_path = res_dir / "emotional_weights.json"
    if not ew_path.exists():
        write_json(ew_path, {})
        created.append("resonance/emotional_weights.json")

    el_path = res_dir / "event_log.json"
    if not el_path.exists():
        write_json(el_path, [])
        created.append("resonance/event_log.json")

    # ═══ 5. sensory/ ═══
    sensory_dir = agent_dir / "sensory"
    sensory_path = sensory_dir / "sensory_memory.json"
    if not sensory_path.exists():
        sensory = {
            "entries": [],
            "summary": "",
            "last_location": "",
            "location_tags": [],
        }
        write_json(sensory_path, sensory)
        created.append("sensory/sensory_memory.json")

    return created


def main():
    if not MODULES_DIR.exists():
        print(f"❌ Папка {MODULES_DIR} не найдена. Запусти из корня студии.")
        return

    total_agents = 0
    total_created = 0
    skipped = 0

    print("═══ МИГРАЦИЯ АГЕНТОВ В ГРОНДХЕЙМ ═══\n")

    for dept_dir in sorted(MODULES_DIR.iterdir()):
        if not dept_dir.is_dir():
            continue

        dept = dept_dir.name
        agents_in_dept = []

        for agent_dir in sorted(dept_dir.iterdir()):
            if not agent_dir.is_dir():
                continue

            # Пропускаем если уже полная структура
            has_dna = (agent_dir / "dna.json").exists()
            has_core = (agent_dir / "core" / "anchors.json").exists()
            has_resonance = (agent_dir / "resonance" / "emotional_weights.json").exists()

            if has_dna and has_core and has_resonance:
                skipped += 1
                agents_in_dept.append(f"  ✓ {agent_dir.name} — уже полный, пропущен")
                total_agents += 1
                continue

            created = migrate_agent(agent_dir, dept)
            total_agents += 1

            if created:
                total_created += len(created)
                agents_in_dept.append(f"  + {agent_dir.name} — добавлено: {', '.join(created)}")
            else:
                skipped += 1
                agents_in_dept.append(f"  ✓ {agent_dir.name} — без изменений")

        if agents_in_dept:
            print(f"📂 {dept}/")
            for line in agents_in_dept:
                print(line)
            print()

    print(f"═══ ГОТОВО ═══")
    print(f"Агентов: {total_agents}")
    print(f"Файлов создано: {total_created}")
    print(f"Пропущено (уже полные): {skipped}")
    print(f"\nТеперь подкрути характеры через Страницу Жизни или руками в dna.json")
    print(f"Файлы с пометкой '_migrated: true' — дефолтные, ждут твоей руки.")


if __name__ == "__main__":
    main()
