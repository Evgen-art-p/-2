# prepare_living_book_new.py — Подготовка двух новых агентов цеха Living Book
# Фабула Фейн (A00) и Вера Душа (A00a) — создаёт правильную структуру папок
# чтобы register_existing.py и resurrect_agents.py их подхватили
#
# Запуск: python prepare_living_book_new.py
# Потом: python register_existing.py living_book
# Потом: python resurrect_agents.py --dept living_book
#
# Студия «Шесть Пальцев» · Грондхейм · 2026

import json
import shutil
from pathlib import Path

MODULES_DIR = Path("studio/modules/living_book")

# Два новых агента
NEW_AGENTS = [
    {
        "folder": "A00",
        "old_folder": "A00",          # уже существует
        "old_prompt": "promt.md",      # опечатка в оригинале
        "name": "Фабула Фейн (Fable Fein)",
        "role": "Сказочник — творец миров",
        "icon": "📖",
        "greeting": "Давай посмотрим, что будет, если...",
        "character": "Тёплый, но не сюсюкающий. Глубокий, но не мрачный. Пишет истории для детей с двойным дном — ребёнок слышит волшебство, родитель слышит смысл.",
    },
    {
        "folder": "A00a",
        "old_folder": "A00 a",         # пробел в имени!
        "old_prompt": "promt.md",
        "name": "Вера Душа (Vera Dusha)",
        "role": "Детский психолог-критик",
        "icon": "🧸",
        "greeting": "Красиво — не значит безопасно. Давайте проверим, что останется в душе ребёнка.",
        "character": "Глубокая, спокойная, защищающая. Проверяет каждую историю на экологичность, возрастную релевантность и терапевтическую ценность.",
    },
]


def prepare_agent(agent_cfg: dict):
    folder = agent_cfg["folder"]
    old_folder = agent_cfg["old_folder"]
    agent_dir = MODULES_DIR / folder
    old_dir = MODULES_DIR / old_folder

    print(f"\n═══ {agent_cfg['name']} ({folder}) ═══")

    # ── 1. Переименовать папку если имя с пробелом ──
    if old_folder != folder and old_dir.exists():
        if agent_dir.exists():
            print(f"  ⚠️  Папка {folder} уже существует, старую {old_folder} не трогаю")
        else:
            old_dir.rename(agent_dir)
            print(f"  ✅ Переименовано: '{old_folder}' → '{folder}'")
    elif not agent_dir.exists():
        agent_dir.mkdir(parents=True)
        print(f"  ✅ Создана папка: {folder}")
    else:
        print(f"  ✅ Папка {folder} существует")

    # ── 2. Создать подпапки ──
    for sub in ["core", "home", "forge", "sensory", "resonance"]:
        (agent_dir / sub).mkdir(parents=True, exist_ok=True)

    # ── 3. Перенести промпт в forge/prompt.md ──
    forge_prompt = agent_dir / "forge" / "prompt.md"
    old_prompt = agent_dir / agent_cfg["old_prompt"]

    if old_prompt.exists() and not forge_prompt.exists():
        shutil.move(str(old_prompt), str(forge_prompt))
        print(f"  ✅ Промпт перенесён: {agent_cfg['old_prompt']} → forge/prompt.md")
    elif old_prompt.exists() and forge_prompt.exists():
        print(f"  ⚠️  forge/prompt.md уже есть, {agent_cfg['old_prompt']} оставлен")
    elif forge_prompt.exists():
        print(f"  ✅ forge/prompt.md уже на месте")
    else:
        # Ищем промпт в других местах
        for alt in ["prompt.md", "prompt.txt"]:
            alt_path = agent_dir / alt
            if alt_path.exists():
                shutil.move(str(alt_path), str(forge_prompt))
                print(f"  ✅ Промпт перенесён: {alt} → forge/prompt.md")
                break
        else:
            print(f"  ⚠️  Промпт не найден — нужно добавить вручную")

    # ── 4. Создать info.json (минимальный — чтобы register_existing подхватил) ──
    info_path = agent_dir / "info.json"
    if not info_path.exists():
        info = {
            "id": folder,
            "label": agent_cfg["name"],
            "role": agent_cfg["role"],
            "icon": agent_cfg["icon"],
            "greeting": agent_cfg["greeting"],
            "avatar": "",
            "workshop": "living_book",
        }
        info_path.write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  ✅ Создан info.json")
    else:
        print(f"  ✅ info.json уже есть")

    # ── 5. Создать пустые файлы памяти (если нет) ──
    sensory_path = agent_dir / "sensory" / "sensory_memory.json"
    if not sensory_path.exists():
        sensory_path.write_text(json.dumps({
            "entries": [], "summary": "", "last_location": "", "location_tags": [],
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  ✅ Создан sensory_memory.json")

    ew_path = agent_dir / "resonance" / "emotional_weights.json"
    if not ew_path.exists():
        ew_path.write_text("{}", encoding="utf-8")

    el_path = agent_dir / "resonance" / "event_log.json"
    if not el_path.exists():
        el_path.write_text("[]", encoding="utf-8")

    print(f"  ✅ Структура готова — register_existing.py подхватит")


def main():
    if not MODULES_DIR.exists():
        print(f"❌ Папка {MODULES_DIR} не найдена!")
        print(f"   Запусти из корня проекта")
        return

    print(f"🧒 Подготовка двух новых агентов Living Book")
    print(f"   Папка: {MODULES_DIR}")

    for agent_cfg in NEW_AGENTS:
        prepare_agent(agent_cfg)

    print(f"""
═══════════════════════════════════════
  ✅ Готово! Следующие шаги:
═══════════════════════════════════════

  1. python register_existing.py living_book
     → добавит A00 и A00a в каталог

  2. python resurrect_agents.py --dept living_book
     → LLM сгенерирует dna.json, anchor_points.md,
       home_prompt.md, заполнит каталог

  Фабула Фейн (A00) — Сказочник
  Вера Душа (A00a) — Психолог-критик
""")


if __name__ == "__main__":
    main()
