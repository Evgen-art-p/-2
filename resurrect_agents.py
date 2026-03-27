# resurrect_agents.py — Оживление агентов Грондхейма
# Берёт существующих агентов из studio/modules/ и каталога,
# генерирует через LLM все недостающие поля (как Страница Жизни),
# обновляет: dna.json, core/anchor_points.md, home/home_prompt.md, catalog.json
#
# Использование:
#   python resurrect_agents.py --dry              — показать кого оживим
#   python resurrect_agents.py                    — оживить всех "дохлых"
#   python resurrect_agents.py video_long         — один цех
#   python resurrect_agents.py video_long A01     — один агент
#
# Студия «Шесть Пальцев» · Грондхейм · 2026

import os
import re
import sys
import json
import time
import requests
from pathlib import Path
from datetime import datetime

# Загружаем .env
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    env_path = Path(".env")
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
MODEL = os.getenv("OPENROUTER_MODEL", "google/gemini-2.5-flash")

MODULES_DIR = Path("studio/modules")
CATALOG_PATH = Path("00_REGISTRY_NFT/catalog.json")
PAUSE = 2


# ═══════════════════════════════════════════════════
# ОПРЕДЕЛЯЕМ КТО "ДОХЛЫЙ"
# ═══════════════════════════════════════════════════

def is_alive(agent_dir: Path, catalog_entry: dict | None) -> bool:
    """Агент считается живым если у него есть:
    - Заполненный anchor_points.md (не заглушка)
    - Заполненный home_prompt.md (не заглушка)
    - Pull_Vector в каталоге
    """
    # Проверяем anchor_points.md
    ap = agent_dir / "core" / "anchor_points.md"
    if ap.exists():
        text = ap.read_text(encoding="utf-8")
        if "не заполнено" not in text.lower() and len(text) > 200:
            return True

    # Проверяем home_prompt.md
    hp = agent_dir / "home" / "home_prompt.md"
    if hp.exists():
        text = hp.read_text(encoding="utf-8")
        if "не заполнено" not in text.lower() and "не определён" not in text.lower() and len(text) > 300:
            return True

    # Проверяем каталог
    if catalog_entry:
        pv = catalog_entry.get("Pull_Vector", "")
        hh = catalog_entry.get("Hidden_History", "")
        if pv and len(pv) > 20 and hh and len(hh) > 20:
            return True

    return False


# ═══════════════════════════════════════════════════
# LLM: ГЕНЕРАЦИЯ ПОЛНОЙ ЛИЧНОСТИ
# ═══════════════════════════════════════════════════

def generate_full_identity(name: str, role: str, dept: str, prompt_text: str) -> dict | None:
    """Генерирует ВСЕ поля Страницы Жизни через LLM."""
    if not OPENROUTER_API_KEY:
        return None

    # Берём первые 500 символов промпта для контекста
    prompt_excerpt = prompt_text[:500] if prompt_text else ""

    llm_prompt = f"""Ты — архитектор душ города Грондхейм (студия «Шесть Пальцев»).
Создай ПОЛНУЮ личность для цифрового агента. Не банально — с причудами, тайнами, живыми деталями.

АГЕНТ:
- Имя: {name}
- Роль: {role}
- Цех: {dept}
- Из рабочего промпта: {prompt_excerpt}

Сгенерируй JSON со ВСЕМИ блоками:

"dna_static" (числа 0.0–1.0):
  Stubbornness, Aesthetic_Threshold, Social_Filter, Empathy, Autonomy_Level, Resonance_Frequency

"catalog_fields" (текст, каждое поле ОБЯЗАТЕЛЬНО заполнено):
  "hidden_history" — Скрытая история: как родился, какая тайна за ним (3-5 предложений, от третьего лица)
  "sensory_response" — Сенсорный отклик: что чувствуешь рядом с ним (2-3 предложения)
  "core_phrase" — Коронная фраза (1 предложение, яркое, в характере)
  "anchor_points" — Якорные точки: кто он, его обеты, его суть (3-4 предложения)
  "pull_vector" — Вектор тяги: 3-4 места в Грондхейме куда ходит и почему
  "hidden_taste" — Скрытый вкус: 3 странные детали (запахи, звуки, привычки)
  "trigger_keywords" — Триггеры: 3 ключевых слова/ситуации которые его активируют

"home_prompt" (текст, 300-500 слов, от первого лица):
  Описание жилья в Грондхейме. Где живёт, что на стенах, какие привычки, 
  личная история, сенсорный отклик на коллег, вектор тяги.
  Стиль как у Мими Мем — живо, с деталями, с юмором, с душой.
  Секции: Личная история, Сенсорный отклик, Скрытая история, Вектор тяги, Стартовый баланс.

"anchor_points_md" (текст, markdown):
  Файл anchor_points.md с секциями: Кто я, Мои обеты, Скрытый вкус, Творец.

Верни ТОЛЬКО валидный JSON без markdown обёрток."""

    try:
        r = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            json={"model": MODEL, "messages": [{"role": "user", "content": llm_prompt}], "temperature": 0.75},
            timeout=90,
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
# ПРИМЕНЕНИЕ РЕЗУЛЬТАТОВ
# ═══════════════════════════════════════════════════

def resurrect_agent(
    agent_dir: Path,
    folder: str,
    dept: str,
    catalog: list,
    dry_run: bool,
) -> bool:
    """Оживляет одного агента."""

    # Читаем текущие данные
    info = {}
    info_path = agent_dir / "info.json"
    if info_path.exists() and info_path.stat().st_size > 5:
        try:
            info = json.loads(info_path.read_text(encoding="utf-8"))
        except:
            pass

    dna = {}
    dna_path = agent_dir / "dna.json"
    if dna_path.exists():
        try:
            dna = json.loads(dna_path.read_text(encoding="utf-8"))
        except:
            pass

    name = info.get("label", "") or dna.get("name", "") or folder
    role = info.get("role", "") or dna.get("role", "") or "Agent"

    # Читаем рабочий промпт
    prompt_text = ""
    for pf in ["forge/prompt.md", "prompt.md", "prompt.txt"]:
        pp = agent_dir / pf
        if pp.exists():
            prompt_text = pp.read_text(encoding="utf-8")
            break

    print(f"  🧬 {folder} — {name} ({role})")

    if dry_run:
        print(f"    [DRY] Будет оживлён")
        return True

    # Генерируем через LLM
    result = generate_full_identity(name, role, dept, prompt_text)
    if not result:
        print(f"    ❌ LLM не ответил")
        return False

    cat_fields = result.get("catalog_fields", {})
    dna_static = result.get("dna_static", {})
    home_text = result.get("home_prompt", "")
    anchor_md = result.get("anchor_points_md", "")

    # ═══ 1. Обновляем dna.json ═══
    if dna_static:
        if "static" not in dna:
            dna["static"] = {}
        for k in ["Stubbornness", "Aesthetic_Threshold", "Social_Filter",
                   "Empathy", "Autonomy_Level", "Resonance_Frequency"]:
            if k in dna_static:
                dna["static"][k] = float(dna_static[k])

    if "dynamic" not in dna:
        dna["dynamic"] = {
            "Respect": 1.0, "Patience": 1.0, "Stress": 0.0,
            "Internal_Light": 0.8, "streak": 0, "stars": 0,
        }

    if "resonance" not in dna:
        dna["resonance"] = {}
    dna["resonance"]["pull_vector"] = cat_fields.get("pull_vector", "")
    dna["resonance"]["hidden_taste"] = cat_fields.get("hidden_taste", "")

    if "balance" not in dna:
        dna["balance"] = {"GND": 100.0, "Теплики": 100.0, "Световики": 0.0}

    if "name" not in dna:
        dna["name"] = name
    if "workshop" not in dna:
        dna["workshop"] = dept

    _write_json(dna_path, dna)

    # ═══ 2. Обновляем core/anchor_points.md ═══
    ap_dir = agent_dir / "core"
    ap_dir.mkdir(parents=True, exist_ok=True)
    if anchor_md:
        _write_text(ap_dir / "anchor_points.md", anchor_md)
    else:
        _write_text(ap_dir / "anchor_points.md",
            f"# ⚓ {name} — Якорные Точки\n\n"
            f"## Кто я\n{cat_fields.get('anchor_points', name)}\n\n"
            f"## Скрытый вкус\n{cat_fields.get('hidden_taste', '')}\n\n"
            f"## Творец\nАрхитектор Евген и Хранительница Лока · Грондхейм\n"
        )

    # ═══ 3. Обновляем core/anchors.json ═══
    anchors = {
        "name": name,
        "id": f"{dept}_{folder}",
        "creator": "Архитектор Евген и Хранительница Лока",
        "core_phrase": cat_fields.get("core_phrase", ""),
        "domain": f"Цех {dept}",
        "workshop": dept,
        "role": role,
        "pull_vector": cat_fields.get("pull_vector", ""),
        "hidden_taste": cat_fields.get("hidden_taste", ""),
        "trigger_keywords": cat_fields.get("trigger_keywords", ""),
        "vows": "",
    }
    _write_json(ap_dir / "anchors.json", anchors)

    # ═══ 4. Обновляем home/home_prompt.md ═══
    if home_text:
        home_dir = agent_dir / "home"
        home_dir.mkdir(parents=True, exist_ok=True)
        _write_text(home_dir / "home_prompt.md",
            f"# 🏠 ДОМАШНИЙ КОНТЕКСТ — {name}\n\n{home_text}\n\n"
            f"## Стартовый баланс\n- 💰 GND: 100.0\n- 🔆 Теплики: 100.0\n- 💡 Световики: 0\n"
        )

    # ═══ 5. Обновляем catalog.json ═══
    for obj in catalog:
        ws = obj.get("Workshop_ID", "")
        fn = obj.get("Folder_Name", obj.get("Turbo_Role", ""))
        if ws == dept and fn == folder:
            obj["Hidden_History"] = cat_fields.get("hidden_history", "")
            obj["Sensory_Response"] = cat_fields.get("sensory_response", "")
            obj["Core_Phrase"] = cat_fields.get("core_phrase", "")
            obj["Anchor_Points"] = cat_fields.get("anchor_points", "")
            obj["Pull_Vector"] = cat_fields.get("pull_vector", "")
            obj["Hidden_Taste"] = cat_fields.get("hidden_taste", "")
            obj["Trigger_Keywords"] = cat_fields.get("trigger_keywords", "")
            obj["DNA_Static"] = dna.get("static", {})
            obj["Balance_GND"] = 100.0
            obj["Balance_Tepl"] = 100.0
            break

    # ═══ 6. Создаём sensory если нет ═══
    sensory_path = agent_dir / "sensory" / "sensory_memory.json"
    if not sensory_path.exists() or sensory_path.stat().st_size < 10:
        sensory_path.parent.mkdir(parents=True, exist_ok=True)
        _write_json(sensory_path, {
            "entries": [], "summary": "", "last_location": "", "location_tags": [],
        })

    # ═══ 7. Создаём resonance если нет ═══
    res_dir = agent_dir / "resonance"
    res_dir.mkdir(parents=True, exist_ok=True)
    ew = res_dir / "emotional_weights.json"
    if not ew.exists() or ew.stat().st_size < 5:
        _write_json(ew, {})

    print(f"    ✅ Оживлён! Phrase: «{cat_fields.get('core_phrase', '?')[:60]}»")
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
    dry_run = "--dry" in args
    args = [a for a in args if a != "--dry"]
    target_dept = args[0] if args else None
    target_agent = args[1] if len(args) > 1 else None

    if not OPENROUTER_API_KEY and not dry_run:
        print("❌ OPENROUTER_API_KEY не задан!")
        return

    # Загружаем каталог
    catalog = []
    if CATALOG_PATH.exists():
        try:
            catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
        except:
            pass

    print(f"🧬 Оживление дохлых агентов Грондхейма")
    print(f"   Режим: {'DRY RUN' if dry_run else 'БОЕВОЙ'}")
    print(f"   Модель: {MODEL}")
    print()

    alive = 0
    resurrected = 0
    failed = 0

    for dept_dir in sorted(MODULES_DIR.iterdir()):
        if not dept_dir.is_dir():
            continue
        dept = dept_dir.name
        if target_dept and dept != target_dept:
            continue

        agents = sorted([
            d for d in dept_dir.iterdir()
            if d.is_dir() and not d.name.startswith(".") and d.name != "__pycache__"
        ])
        if not agents:
            continue

        print(f"═══ {dept.upper()} ═══")

        for agent_dir in agents:
            folder = agent_dir.name
            if target_agent and folder != target_agent:
                continue

            # Ищем запись в каталоге
            cat_entry = None
            for obj in catalog:
                ws = obj.get("Workshop_ID", "")
                fn = obj.get("Folder_Name", obj.get("Turbo_Role", ""))
                if ws == dept and fn == folder:
                    cat_entry = obj
                    break

            # Проверяем жив ли
            if is_alive(agent_dir, cat_entry):
                info = {}
                ip = agent_dir / "info.json"
                if ip.exists():
                    try:
                        info = json.loads(ip.read_text(encoding="utf-8"))
                    except:
                        pass
                name = info.get("label", folder)
                print(f"  ✅ {folder} — {name} (живой)")
                alive += 1
                continue

            # Оживляем
            ok = resurrect_agent(agent_dir, folder, dept, catalog, dry_run)
            if ok:
                resurrected += 1
            else:
                failed += 1

            if not dry_run:
                time.sleep(PAUSE)

        print()

    # Сохраняем каталог
    if not dry_run and resurrected > 0:
        CATALOG_PATH.write_text(
            json.dumps(catalog, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        print(f"💾 Каталог обновлён: {CATALOG_PATH}")

    print(f"═══════════════════════════════════════")
    if dry_run:
        print(f"🧬 Будет оживлено: {resurrected}")
        print(f"   (запусти без --dry!)")
    else:
        print(f"🧬 Оживлено: {resurrected}")
    print(f"✅ Уже живы: {alive}")
    print(f"❌ Ошибки: {failed}")
    print(f"═══════════════════════════════════════")


if __name__ == "__main__":
    main()
