# studio/workshop/cabinet_prompts.py — Загрузка промптов Кабинета
# Вынесено из ui_cabinet.py

from pathlib import Path

PROMPTS_DIR = Path("prompts/cabinet")
KNOWLEDGE_DIR_CAB = Path("prompts/cabinet/knowledge")

DIRECTOR_FALLBACK = (
    "Ты — креативный режиссёр студии «Шесть пальцев». "
    "Помогаешь с идеями, концепциями, сценариями. Отвечай на русском."
)


def load_cabinet_prompts() -> dict:
    """Сканирует prompts/cabinet/*.txt и строит каталог промптов.

    Свободный чат — всегда есть, без файла.
    Режиссёр — фоллбэк-промпт если файл не найден.
    """
    prompts = {
        "free": {"name": "💬 Свободный чат", "system": "", "knowledge": ""},
    }

    # Режиссёр — всегда есть
    director_file = PROMPTS_DIR / "director.txt"
    director_system = DIRECTOR_FALLBACK
    if director_file.exists():
        try:
            director_system = director_file.read_text(encoding="utf-8").strip()
        except Exception:
            pass

    director_knowledge = ""
    director_kb = KNOWLEDGE_DIR_CAB / "director.md"
    if director_kb.exists():
        try:
            director_knowledge = director_kb.read_text(encoding="utf-8").strip()
        except Exception:
            pass

    prompts["director"] = {
        "name": "🎬 Режиссёр",
        "system": director_system,
        "knowledge": director_knowledge,
    }

    # Сканируем остальные .txt файлы
    if PROMPTS_DIR.exists():
        for txt_file in sorted(PROMPTS_DIR.glob("*.txt")):
            pid = txt_file.stem
            if pid == "director":
                continue
            try:
                system = txt_file.read_text(encoding="utf-8").strip()
            except Exception:
                continue
            if not system:
                continue

            # Knowledge — .md с тем же именем
            knowledge = ""
            kb_file = KNOWLEDGE_DIR_CAB / f"{pid}.md"
            if kb_file.exists():
                try:
                    knowledge = kb_file.read_text(encoding="utf-8").strip()
                except Exception:
                    pass

            # Имя из первой строки или filename
            name = pid.replace("_", " ").replace("-", " ").title()
            first_line = system.split("\n")[0].strip()
            if first_line.startswith("#"):
                name = first_line.lstrip("# ").strip()

            prompts[pid] = {
                "name": f"📄 {name}",
                "system": system,
                "knowledge": knowledge,
            }

    return prompts
