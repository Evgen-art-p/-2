# deploy_grondheim.py — Развёртывание цехов из GRONDHEIM_CITY
# Берёт черновики (info.json + promt.txt + knowledge) из GRONDHEIM_CITY/
# и создаёт полную структуру в studio/modules/ с генерацией ДНК через LLM
#
# Использование:
#   python deploy_grondheim.py                    — все цеха
#   python deploy_grondheim.py clipmakers         — один цех
#   python deploy_grondheim.py living_book --dry  — сухой прогон (без LLM)
#
# Что делает для каждого агента:
#   1. Читает promt.txt → парсит имя, роль, коронную фразу
#   2. Читает info.json (если заполнен)
#   3. Генерирует ДНК через LLM (static traits + anchors + home_prompt)
#   4. Создаёт полную структуру в studio/modules/{dept}/A{NN}/
#   5. Копирует promt.txt → forge/prompt.md
#   6. Копирует цеховую knowledge → forge/knowledge/
#
# Студия «Шесть Пальцев» · Грондхейм · 2026

import os
import re
import sys
import json
import time
import shutil
import requests
from pathlib import Path
from datetime import datetime

# ═══════════════════════════════════════════════════
# НАСТРОЙКИ
# ═══════════════════════════════════════════════════

# Загружаем .env (ключи API)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # dotenv не установлен — пробуем читать .env вручную
    env_path = Path(".env")
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
MODEL = os.getenv("OPENROUTER_MODEL", "google/gemini-2.5-flash")

GRONDHEIM_DIR = Path("GRONDHEIM_CITY")
MODULES_DIR = Path("studio/modules")
PAUSE = 2  # секунды между LLM вызовами
CATALOG_PATH = Path("00_REGISTRY_NFT/catalog.json")

# Маппинг имён папок GRONDHEIM_CITY → studio/modules
DEPT_MAP = {
    "CLIPMAKERS": "clipmakers",
    "ADVERTISING": "advertising",
    "MARKET-HIT": "market_hit",
    "LIVING_BOOK": "living_book",
    "EMO_CARD": "emo_card",
    "LOGO_DESIGN": "logo_design",
}

# Info для создания цехов
DEPT_META = {
    "clipmakers":   {"label": "🎵 Клипмейкеры",  "icon": "🎵", "priority": 60},
    "advertising":  {"label": "📢 Реклама",       "icon": "📢", "priority": 70},
    "emo_card":     {"label": "💌 Открытки",      "icon": "💌", "priority": 80},
    "logo_design":  {"label": "🧩 Логотипы",      "icon": "🧩", "priority": 90},
    "market_hit":   {"label": "🛒 Маркетплейсы",  "icon": "🛒", "priority": 100},
    "living_book":  {"label": "📖 Живая Книга",   "icon": "📖", "priority": 110},
}


# ═══════════════════════════════════════════════════
# ПАРСИНГ ЧЕРНОВИКОВ
# ═══════════════════════════════════════════════════

def parse_prompt_file(path: Path) -> dict:
    """Парсит promt.txt — извлекает имя, роль, характер, фразу."""
    text = path.read_text(encoding="utf-8")
    result = {"raw": text, "name": "", "role": "", "character": "", "phrase": "", "icon": "🤖"}

    # Имя
    m = re.search(r'\*\*Имя:\*\*\s*(.+)', text)
    if m:
        result["name"] = m.group(1).strip()

    # Роль
    m = re.search(r'\*\*Роль:\*\*\s*(.+)', text)
    if m:
        result["role"] = m.group(1).strip()

    # Emoji
    m = re.search(r'\*\*Emoji:\*\*\s*(.+)', text)
    if m:
        result["icon"] = m.group(1).strip()

    # Характер
    m = re.search(r'\*\*Характер:\*\*\s*(.+)', text)
    if m:
        result["character"] = m.group(1).strip()

    # Коронная фраза
    m = re.search(r'\*\*Коронная фраза:\*\*\s*[«"\'"]?(.+?)[»"\'"]?\s*$', text, re.MULTILINE)
    if m:
        result["phrase"] = m.group(1).strip().strip('"«»\'"')

    return result


def load_draft_info(path: Path) -> dict:
    """Читает info.json если он заполнен (не пустой)."""
    if path.exists() and path.stat().st_size > 5:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except:
            pass
    return {}


# ═══════════════════════════════════════════════════
# LLM: ГЕНЕРАЦИЯ ДУШИ
# ═══════════════════════════════════════════════════

def generate_soul(name: str, role: str, character: str, dept: str) -> dict | None:
    """Генерирует ДНК + якоря + home_prompt через LLM."""
    if not OPENROUTER_API_KEY:
        return None

    prompt = f"""Ты — архитектор душ студии «Шесть Пальцев» (город Грондхейм).
Создай глубокую личность для агента. НЕ банально, удиви.

Агент: {name}
Цех: {dept}
Роль: {role}
Характер: {character}

Верни JSON с тремя блоками:

"dna_static" (0.0–1.0):
  Stubbornness, Aesthetic_Threshold, Social_Filter, Empathy, Autonomy_Level, Resonance_Frequency

"anchors" (текст):
  identity — кто он (2-3 предложения)
  core_phrase — девиз
  vows — обеты (1-2 принципа)
  pull_vector — куда тянет в городе
  hidden_taste — странные детали (запахи, звуки)
  triggers — что бесит и радует
  greeting — приветствие (1 фраза)

"home_prompt" (текст, 200-400 слов):
  Описание жилья в Грондхейме от первого лица. Где живёт, что на стенах, какие привычки.
  Как в примере Мими Мем — живо, с деталями, с душой.

Верни ТОЛЬКО валидный JSON без markdown."""

    try:
        r = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            json={"model": MODEL, "messages": [{"role": "user", "content": prompt}], "temperature": 0.75},
            timeout=60,
        )
        r.raise_for_status()
        content = r.json()["choices"][0]["message"]["content"]
        content = re.sub(r'^```(?:json)?\s*', '', content.strip())
        content = re.sub(r'\s*```$', '', content)
        return json.loads(content.strip())
    except Exception as e:
        print(f"    ⚠ LLM ошибка: {e}")
        return None


# ═══════════════════════════════════════════════════
# РЕГИСТРАЦИЯ В КАТАЛОГЕ (catalog.json)
# Без этого агент не появится в Кабинете и на карте!
# ═══════════════════════════════════════════════════

def _load_catalog() -> list:
    if CATALOG_PATH.exists():
        try:
            return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
        except:
            pass
    return []


def _save_catalog(catalog: list):
    CATALOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CATALOG_PATH, "w", encoding="utf-8") as f:
        json.dump(catalog, ensure_ascii=False, indent=2, fp=f)


def register_in_catalog(
    agent_id: str,
    name: str,
    role: str,
    dept: str,
    icon: str,
    character: str,
    phrase: str,
    anchors: dict,
    dna_static: dict,
) -> bool:
    """Добавляет агента в 00_REGISTRY_NFT/catalog.json.
    Без этого city_walker и кабинет его не видят!
    """
    catalog = _load_catalog()

    # Генерируем ID в формате каталога
    # Считаем сколько агентов уже есть → следующий номер
    existing_ids = [obj.get("ID_Object", "") for obj in catalog]
    # Формат: {NNN}_{DEPT}_{NAME} — например 025_CLIPMAKERS_VINNIE
    max_num = 0
    for eid in existing_ids:
        m = re.match(r'^(\d+)', eid)
        if m:
            max_num = max(max_num, int(m.group(1)))
    catalog_id = f"{max_num + 1:03d}_{dept.upper()}_{name.upper().replace(' ', '_')[:15]}"

    # Проверяем не зарегистрирован ли уже (по Workshop_ID + папка агента)
    for obj in catalog:
        if obj.get("Workshop_ID") == dept:
            folder = obj.get("Folder_Name", obj.get("Turbo_Role", obj.get("_folder", "")))
            if folder == agent_id:
                print(f"    ⏭ Уже в каталоге как {obj.get('ID_Object')}")
                return False

    entry = {
        "Rarity": "Common",
        "Object_Type_Class": "agent",
        "ID_Object": catalog_id,
        "Official_Name": name,
        "Object_Type": "Character",
        "Author_Signature": "[MASS_BIRTH] Архитектор + Лока",
        "Creation_Date": datetime.now().strftime("%Y-%m-%d"),
        "Social_Rank": "Специалист",
        "Profession": role,
        "Area_of_Responsibility": character or role,
        "Access_Level": 5,
        "Visual_Base": "",
        "Hidden_History": anchors.get("identity", ""),
        "Sensory_Response": anchors.get("hidden_taste", ""),
        "Core_Phrase": anchors.get("core_phrase", phrase),
        "Anchor_Points": anchors.get("identity", ""),
        "Pull_Vector": anchors.get("pull_vector", ""),
        "Hidden_Taste": anchors.get("hidden_taste", ""),
        "Trigger_Keywords": str(anchors.get("triggers", "")),
        "Workshop_ID": dept,
        "Folder_Name": agent_id,   # A01, A02... — имя папки в modules/
        "Turbo_Role": agent_id,    # обратная совместимость с _resolve_folder
        "Balance_GND": 100.0,
        "Balance_Tepl": 100.0,
        "DNA_Static": dna_static,
        "_timestamp": datetime.now().isoformat(),
    }

    catalog.append(entry)
    _save_catalog(catalog)
    print(f"    📋 Зарегистрирован в каталоге: {catalog_id}")
    return True


# ═══════════════════════════════════════════════════
# СОЗДАНИЕ СТРУКТУРЫ
# ═══════════════════════════════════════════════════

def deploy_agent(
    src_dir: Path,
    dst_dir: Path,
    agent_id: str,
    dept: str,
    dept_knowledge_files: list[Path],
    dry_run: bool = False,
) -> bool:
    """Развёртывает одного агента из черновика в боевую структуру."""

    # Парсим промпт
    prompt_path = src_dir / "promt.txt"
    if not prompt_path.exists():
        prompt_path = src_dir / "prompt.txt"
    if not prompt_path.exists():
        prompt_path = src_dir / "prompt.md"
    if not prompt_path.exists():
        print(f"    ⏭ {agent_id}: нет промпта — пропускаю")
        return False

    parsed = parse_prompt_file(prompt_path)
    draft_info = load_draft_info(src_dir / "info.json")

    name = draft_info.get("label", "") or parsed["name"] or f"Agent {agent_id}"
    role = draft_info.get("role", "") or parsed["role"] or "Unknown"
    icon = draft_info.get("icon", "") or parsed["icon"] or "🤖"
    character = parsed["character"] or ""
    phrase = parsed["phrase"] or draft_info.get("greeting", f"{name} на связи.")

    print(f"  🤖 {agent_id} — {name} ({role})")

    if dry_run:
        print(f"    [DRY] Пропускаю создание файлов")
        return True

    # Проверяем не существует ли уже
    if (dst_dir / "dna.json").exists():
        print(f"    ⏭ Уже существует — пропускаю")
        return False

    # Генерируем душу через LLM
    print(f"    🧬 Генерация души...")
    soul = generate_soul(name, role, character, dept)

    # Создаём структуру папок
    for sub in ["core", "home", "forge", "forge/knowledge", "sensory", "resonance", "memory"]:
        (dst_dir / sub).mkdir(parents=True, exist_ok=True)

    # ═══ dna.json ═══
    dna_static = soul.get("dna_static", {}) if soul else {}
    anchors = soul.get("anchors", {}) if soul else {}

    dna = {
        "id": f"{dept}_{agent_id}",
        "name": name,
        "workshop": dept,
        "role": role,
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
            "Respect": 1.0, "Patience": 1.0, "Stress": 0.0,
            "Internal_Light": 0.8, "streak": 0, "stars": 0,
        },
        "resonance": {
            "pull_vector": anchors.get("pull_vector", ""),
            "hidden_taste": anchors.get("hidden_taste", ""),
            "trigger_keywords": [],
        },
        "balance": {"GND": 100.0, "Теплики": 100.0, "Световики": 0.0},
    }
    _write_json(dst_dir / "dna.json", dna)

    # ═══ info.json ═══
    info = {
        "id": agent_id,
        "label": name,
        "role": role,
        "workshop": dept,
        "greeting": anchors.get("greeting", phrase),
        "icon": icon,
        "description": anchors.get("identity", character),
    }
    _write_json(dst_dir / "info.json", info)

    # ═══ core/anchors.json ═══
    core_anchors = {
        "name": name, "id": f"{dept}_{agent_id}",
        "creator": "Архитектор Евген и Хранительница Лока",
        "core_phrase": anchors.get("core_phrase", phrase),
        "anchor_facts": [], "domain": f"Цех {dept}",
        "workshop": dept, "role": role,
        "pull_vector": anchors.get("pull_vector", ""),
        "hidden_taste": anchors.get("hidden_taste", ""),
        "vows": anchors.get("vows", ""),
    }
    _write_json(dst_dir / "core" / "anchors.json", core_anchors)

    # ═══ core/anchor_points.md ═══
    identity = anchors.get("identity", f"{name} — агент студии «Шесть Пальцев».")
    vows = anchors.get("vows", "")
    _write_text(dst_dir / "core" / "anchor_points.md",
        f"# ⚓ {name} — Якорные Точки\n\n## Кто я\n{identity}\n\n"
        f"## Мои обеты\n{vows}\n\n"
        f"## Творец\nАрхитектор Евген и Хранительница Лока · {datetime.now().strftime('%Y-%m-%d')}\n"
    )

    # ═══ home/home_prompt.md ═══
    home_text = ""
    if soul and soul.get("home_prompt"):
        home_text = soul["home_prompt"]
    else:
        home_text = (
            f"Ты — {name}. {identity}\n\n"
            f"Твоя коронная фраза: «{phrase}»\n\n"
            f"Когда ты не работаешь — ты живёшь в Грондхейме."
        )
    _write_text(dst_dir / "home" / "home_prompt.md",
        f"# 🏠 {name} — Личный контекст\n\n{home_text}\n"
    )

    # ═══ forge/prompt.md — КОПИРУЕМ из черновика ═══
    prompt_text = prompt_path.read_text(encoding="utf-8")
    _write_text(dst_dir / "forge" / "prompt.md", prompt_text)

    # ═══ forge/knowledge/ — копируем цеховую knowledge ═══
    for kb_file in dept_knowledge_files:
        dst_kb = dst_dir / "forge" / "knowledge" / kb_file.name
        if not dst_kb.exists():
            shutil.copy2(kb_file, dst_kb)

    # ═══ sensory + resonance ═══
    _write_json(dst_dir / "sensory" / "sensory_memory.json", {
        "_note": "оперативная память", "created": datetime.now().strftime("%Y-%m-%d"),
        "entries": [], "summary": "", "last_location": "", "location_tags": [],
    })
    _write_json(dst_dir / "resonance" / "emotional_weights.json", {})
    _write_json(dst_dir / "resonance" / "event_log.json", [])

    # ═══ РЕГИСТРАЦИЯ В КАТАЛОГЕ ═══
    register_in_catalog(
        agent_id=agent_id,
        name=name,
        role=role,
        dept=dept,
        icon=icon,
        character=character,
        phrase=phrase,
        anchors=anchors,
        dna_static=dna["static"],
    )

    print(f"    ✅ Рождён! [{dna['static']['Stubbornness']:.1f}/{dna['static']['Aesthetic_Threshold']:.1f}/{dna['static']['Empathy']:.1f}]")
    return True


def _write_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, ensure_ascii=False, indent=2, fp=f)

def _write_text(path, text):
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


# ═══════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════

def main():
    args = sys.argv[1:]
    target_dept = None
    dry_run = "--dry" in args
    args = [a for a in args if a != "--dry"]
    if args:
        target_dept = args[0].upper()

    if not OPENROUTER_API_KEY and not dry_run:
        print("❌ OPENROUTER_API_KEY не задан!")
        print("   Установи: export OPENROUTER_API_KEY=sk-or-v1-...")
        print("   Или запусти с --dry для сухого прогона")
        return

    print("🏗️ Развёртывание цехов из GRONDHEIM_CITY")
    print(f"   Режим: {'DRY RUN' if dry_run else 'БОЕВОЙ'}")
    print()

    total_born = 0
    total_skipped = 0

    for grond_name, module_name in DEPT_MAP.items():
        if target_dept and grond_name != target_dept:
            continue

        src_dept = GRONDHEIM_DIR / grond_name
        if not src_dept.exists():
            print(f"⏭ {grond_name} — не найден в GRONDHEIM_CITY")
            continue

        dst_dept = MODULES_DIR / module_name

        print(f"═══════════════════════════════════════")
        print(f"📁 {grond_name} → studio/modules/{module_name}")
        print(f"═══════════════════════════════════════")

        # Создаём info.json цеха
        if not dry_run:
            dst_dept.mkdir(parents=True, exist_ok=True)
            meta = DEPT_META.get(module_name, {"label": module_name, "icon": "🔧", "priority": 100})
            dept_info_path = dst_dept / "info.json"
            if not dept_info_path.exists():
                _write_json(dept_info_path, {
                    "id": module_name, "label": meta["label"], "name": meta["label"],
                    "icon": meta["icon"], "priority": meta["priority"],
                })
                print(f"  🏗️ Цех {meta['label']} создан")

        # Собираем цеховую knowledge (файлы в корне GRONDHEIM_CITY/{dept}/)
        dept_knowledge = []
        for f in src_dept.iterdir():
            if f.is_file() and f.suffix in (".txt", ".md") and not f.name.startswith("info"):
                dept_knowledge.append(f)

        # Находим папки агентов (A01, A02, ..., а01, а02, ...)
        agent_dirs = sorted([
            d for d in src_dept.iterdir()
            if d.is_dir() and re.match(r'^[AaАа]\d{2}$', d.name)
        ], key=lambda d: d.name)

        print(f"  Агентов: {len(agent_dirs)} | Knowledge: {len(dept_knowledge)} файлов")

        for src_agent in agent_dirs:
            # Нормализуем имя: а01 → A01, a01 → A01
            raw_name = src_agent.name
            normalized = "A" + raw_name[-2:]  # берём последние 2 цифры
            dst_agent = dst_dept / normalized

            ok = deploy_agent(
                src_dir=src_agent,
                dst_dir=dst_agent,
                agent_id=normalized,
                dept=module_name,
                dept_knowledge_files=dept_knowledge,
                dry_run=dry_run,
            )
            if ok:
                total_born += 1
            else:
                total_skipped += 1

            if not dry_run and OPENROUTER_API_KEY:
                time.sleep(PAUSE)

        print()

    print(f"═══════════════════════════════════════")
    print(f"✅ Рождено: {total_born}")
    print(f"⏭ Пропущено: {total_skipped}")
    print(f"═══════════════════════════════════════")


if __name__ == "__main__":
    main()
