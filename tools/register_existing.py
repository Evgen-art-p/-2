# register_existing.py — Регистрация существующих агентов в каталоге
# Для агентов которые уже есть в studio/modules/ но отсутствуют в catalog.json
#
# Использование:
#   python register_existing.py              — все цеха
#   python register_existing.py clipmakers   — один цех
#   python register_existing.py --dry        — сухой прогон
#
# Студия «Шесть Пальцев» · Грондхейм · 2026

import os
import re
import sys
import json
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

MODULES_DIR = Path("studio/modules")
CATALOG_PATH = Path("00_REGISTRY_NFT/catalog.json")


def load_catalog() -> list:
    if CATALOG_PATH.exists():
        try:
            return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
        except:
            pass
    return []


def save_catalog(catalog: list):
    CATALOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CATALOG_PATH.write_text(
        json.dumps(catalog, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


def get_next_id(catalog: list) -> int:
    """Следующий свободный номер в каталоге."""
    max_num = 0
    for obj in catalog:
        m = re.match(r'^(\d+)', obj.get("ID_Object", ""))
        if m:
            max_num = max(max_num, int(m.group(1)))
    return max_num + 1


def is_registered(catalog: list, dept: str, folder_name: str) -> bool:
    """Проверяет есть ли агент уже в каталоге."""
    for obj in catalog:
        if obj.get("Workshop_ID") != dept:
            continue
        # Проверяем по всем возможным полям
        cat_folder = (
            obj.get("Folder_Name", "")
            or obj.get("Turbo_Role", "")
            or ""
        ).strip()
        if cat_folder == folder_name:
            return True
        # Также проверяем по ID_Object (для резидентов)
        if obj.get("ID_Object", "") == folder_name:
            return True
    return False


def read_agent_data(agent_dir: Path) -> dict:
    """Читает данные агента из его файлов."""
    result = {"name": "", "role": "", "icon": "🤖", "character": "", "phrase": ""}

    # info.json
    info_path = agent_dir / "info.json"
    if info_path.exists() and info_path.stat().st_size > 5:
        try:
            info = json.loads(info_path.read_text(encoding="utf-8"))
            result["name"] = info.get("label", "")
            result["role"] = info.get("role", "")
            result["icon"] = info.get("icon", "🤖")
            result["phrase"] = info.get("greeting", "")
            result["character"] = info.get("description", "")
        except:
            pass

    # dna.json
    dna_path = agent_dir / "dna.json"
    dna = {}
    if dna_path.exists():
        try:
            dna = json.loads(dna_path.read_text(encoding="utf-8"))
            if not result["name"]:
                result["name"] = dna.get("name", "")
            if not result["role"]:
                result["role"] = dna.get("role", "")
        except:
            pass
    result["dna"] = dna

    # core/anchors.json
    anchors_path = agent_dir / "core" / "anchors.json"
    anchors = {}
    if anchors_path.exists():
        try:
            anchors = json.loads(anchors_path.read_text(encoding="utf-8"))
        except:
            pass
    result["anchors"] = anchors

    # Парсим prompt если имя ещё пустое
    if not result["name"]:
        for pf in ["forge/prompt.md", "prompt.md", "prompt.txt"]:
            pp = agent_dir / pf
            if pp.exists():
                text = pp.read_text(encoding="utf-8")
                m = re.search(r'\*\*Имя:\*\*\s*(.+)', text)
                if m:
                    result["name"] = m.group(1).strip()
                m = re.search(r'\*\*Роль:\*\*\s*(.+)', text)
                if m and not result["role"]:
                    result["role"] = m.group(1).strip()
                break

    return result


def main():
    args = sys.argv[1:]
    dry_run = "--dry" in args
    args = [a for a in args if a != "--dry"]
    target_dept = args[0] if args else None

    catalog = load_catalog()
    next_id = get_next_id(catalog)

    print(f"📋 Регистрация агентов в каталоге")
    print(f"   Каталог: {CATALOG_PATH} ({len(catalog)} объектов)")
    print(f"   Следующий ID: {next_id:03d}")
    print(f"   Режим: {'DRY RUN' if dry_run else 'БОЕВОЙ'}")
    print()

    registered = 0
    skipped = 0
    already = 0

    for dept_dir in sorted(MODULES_DIR.iterdir()):
        if not dept_dir.is_dir():
            continue
        dept = dept_dir.name

        if target_dept and dept != target_dept:
            continue

        # Пропускаем не-цеха
        if not (dept_dir / "info.json").exists() and dept != "residents":
            continue

        agents = sorted([
            d for d in dept_dir.iterdir()
            if d.is_dir() and not d.name.startswith(".")
            and d.name != "__pycache__"
        ])

        if not agents:
            continue

        print(f"═══ {dept.upper()} ({len(agents)} агентов) ═══")

        for agent_dir in agents:
            folder = agent_dir.name  # A01, 001_GENESIS_LOKA, etc.

            # Проверяем есть ли уже в каталоге
            if is_registered(catalog, dept, folder):
                print(f"  ✅ {folder} — уже в каталоге")
                already += 1
                continue

            # Проверяем есть ли хоть что-то (dna.json или info.json)
            has_dna = (agent_dir / "dna.json").exists()
            has_info = (agent_dir / "info.json").exists()
            if not has_dna and not has_info:
                print(f"  ⏭ {folder} — нет dna.json и info.json, пропускаю")
                skipped += 1
                continue

            # Читаем данные
            data = read_agent_data(agent_dir)
            name = data["name"] or folder
            role = data["role"] or "Agent"
            dna = data["dna"]
            anchors = data["anchors"]

            # Формируем ID
            safe_name = re.sub(r'[^A-Za-zА-Яа-я0-9]', '_', name)[:15].upper()
            catalog_id = f"{next_id:03d}_{dept.upper()}_{safe_name}"

            print(f"  📋 {folder} → {catalog_id} ({name}, {role})")

            if not dry_run:
                entry = {
                    "Rarity": dna.get("rarity", "Common"),
                    "Object_Type_Class": "agent",
                    "ID_Object": catalog_id,
                    "Official_Name": name,
                    "Object_Type": "Character",
                    "Author_Signature": "[REGISTER] Архитектор + Брат",
                    "Creation_Date": dna.get("created", datetime.now().strftime("%Y-%m-%d")),
                    "Social_Rank": "Специалист",
                    "Profession": role,
                    "Area_of_Responsibility": data["character"] or role,
                    "Access_Level": 5,
                    "Visual_Base": "",
                    "Hidden_History": anchors.get("identity", ""),
                    "Sensory_Response": anchors.get("hidden_taste", dna.get("resonance", {}).get("hidden_taste", "")),
                    "Core_Phrase": anchors.get("core_phrase", data["phrase"]),
                    "Anchor_Points": anchors.get("identity", ""),
                    "Pull_Vector": anchors.get("pull_vector", dna.get("resonance", {}).get("pull_vector", "")),
                    "Hidden_Taste": anchors.get("hidden_taste", dna.get("resonance", {}).get("hidden_taste", "")),
                    "Trigger_Keywords": str(anchors.get("trigger_keywords", dna.get("resonance", {}).get("trigger_keywords", ""))),
                    "Workshop_ID": dept,
                    "Folder_Name": folder,
                    "Turbo_Role": folder,  # обратная совместимость
                    "Balance_GND": dna.get("balance", {}).get("GND", 100.0),
                    "Balance_Tepl": dna.get("balance", {}).get("Теплики", 100.0),
                    "DNA_Static": dna.get("static", {}),
                    "_timestamp": datetime.now().isoformat(),
                }
                catalog.append(entry)

            next_id += 1  # инкрементируем всегда (и в dry тоже для правильного показа)
            registered += 1

        print()

    # Сохраняем каталог
    if not dry_run and registered > 0:
        save_catalog(catalog)
        print(f"💾 Каталог сохранён: {CATALOG_PATH}")
        print(f"   Было: {len(catalog) - registered} объектов → Стало: {len(catalog)} объектов")

    print(f"═══════════════════════════════════════")
    if dry_run:
        print(f"📋 Будет зарегистрировано: {registered}")
        print(f"   (запусти без --dry чтобы сохранить!)")
    else:
        print(f"📋 Зарегистрировано: {registered}")
    print(f"✅ Уже были: {already}")
    print(f"⏭ Пропущено: {skipped}")
    print(f"═══════════════════════════════════════")


if __name__ == "__main__":
    main()
