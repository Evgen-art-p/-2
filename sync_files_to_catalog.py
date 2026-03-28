# sync_files_to_catalog.py — Синхронизация файлов агента → каталог
# Перечитывает dna.json, core/anchors.json, home/home_prompt.md
# и заполняет пустые поля в catalog.json
#
# Запуск: python sync_files_to_catalog.py                    — все
#         python sync_files_to_catalog.py --dept living_book  — один цех
#         python sync_files_to_catalog.py --dry               — сухой прогон
#
# Студия «Шесть Пальцев» · Грондхейм · 2026

import json
import sys
from pathlib import Path

CATALOG_PATH = Path("00_REGISTRY_NFT/catalog.json")
MODULES_DIR = Path("studio/modules")


def load_catalog():
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


def save_catalog(catalog):
    CATALOG_PATH.write_text(
        json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def resolve_folder(obj):
    folder = (obj.get("Folder_Name") or obj.get("Turbo_Role") or "").strip()
    if folder and folder not in ("administrator", "keeper", "mentor", "guardian"):
        return folder
    return obj.get("ID_Object", "").strip()


def read_agent_files(workshop, folder):
    """Читает данные из файлов агента."""
    agent_dir = MODULES_DIR / workshop / folder
    result = {}

    # dna.json → resonance (pull_vector, hidden_taste, trigger_keywords)
    dna_path = agent_dir / "dna.json"
    if dna_path.exists():
        try:
            dna = json.loads(dna_path.read_text(encoding="utf-8"))
            res = dna.get("resonance", {})
            result["pull_vector"] = res.get("pull_vector", "")
            result["hidden_taste"] = res.get("hidden_taste", "")
            triggers = res.get("trigger_keywords", [])
            if isinstance(triggers, list):
                result["trigger_keywords"] = ", ".join(str(t) for t in triggers)
            else:
                result["trigger_keywords"] = str(triggers)
        except Exception:
            pass

    # core/anchors.json → anchor facts, core_phrase
    anchors_path = agent_dir / "core" / "anchors.json"
    if anchors_path.exists():
        try:
            anchors = json.loads(anchors_path.read_text(encoding="utf-8"))
            facts = anchors.get("anchor_facts", [])
            if isinstance(facts, list) and facts:
                result["anchor_points"] = "\n".join(f for f in facts if f.strip())
            core = anchors.get("core_phrase", "")
            if core:
                result["core_phrase"] = core
        except Exception:
            pass

    # core/anchor_points.md → anchor_points (если anchors.json пустой)
    if not result.get("anchor_points"):
        anchor_md = agent_dir / "core" / "anchor_points.md"
        if anchor_md.exists():
            try:
                text = anchor_md.read_text(encoding="utf-8")
                # Извлекаем секцию "Мои обеты" или весь текст
                if "## Мои обеты" in text:
                    start = text.index("## Мои обеты")
                    end = text.index("##", start + 5) if "##" in text[start+5:] else len(text)
                    result["anchor_points"] = text[start:end].strip()
                elif "## Личные якоря" in text:
                    start = text.index("## Личные якоря")
                    end = text.index("##", start + 5) if "##" in text[start+5:] else len(text)
                    result["anchor_points"] = text[start:end].strip()
            except Exception:
                pass

    # home/home_prompt.md → hidden_history (берём секцию "Личная история" или весь текст)
    home_path = agent_dir / "home" / "home_prompt.md"
    if home_path.exists():
        try:
            text = home_path.read_text(encoding="utf-8")
            # Убираем заголовок и берём основной текст как Hidden_History
            lines = [l for l in text.split("\n") if not l.startswith("#") and l.strip()]
            if lines:
                result["hidden_history"] = "\n".join(lines).strip()[:500]
        except Exception:
            pass

    # info.json → sensory_response из visual_description
    info_path = agent_dir / "info.json"
    if info_path.exists():
        try:
            info = json.loads(info_path.read_text(encoding="utf-8"))
            vis = info.get("visual_description", "")
            if vis:
                result["visual_description"] = vis
        except Exception:
            pass

    return result


def main():
    args = sys.argv[1:]
    dry_run = "--dry" in args
    args = [a for a in args if a != "--dry"]
    target_dept = args[0].replace("--dept=", "").replace("--dept", "").strip() if args else ""
    if not target_dept and args:
        target_dept = args[0]

    catalog = load_catalog()

    print(f"🔄 Синхронизация файлов агента → каталог")
    print(f"   Каталог: {len(catalog)} объектов")
    print(f"   Режим: {'DRY RUN' if dry_run else 'БОЕВОЙ'}")
    if target_dept:
        print(f"   Цех: {target_dept}")
    print()

    updated = 0
    skipped = 0

    for obj in catalog:
        if obj.get("Object_Type_Class") != "agent":
            continue
        workshop = obj.get("Workshop_ID", "")
        if target_dept and workshop != target_dept:
            continue

        folder = resolve_folder(obj)
        name = obj.get("Official_Name", "?")

        # Читаем файлы агента
        file_data = read_agent_files(workshop, folder)
        if not file_data:
            continue

        # Маппинг: файл → поле каталога
        field_map = {
            "pull_vector":      "Pull_Vector",
            "hidden_taste":     "Hidden_Taste",
            "trigger_keywords": "Trigger_Keywords",
            "anchor_points":    "Anchor_Points",
            "core_phrase":      "Core_Phrase",
            "hidden_history":   "Hidden_History",
        }

        changes = []
        for file_key, cat_field in field_map.items():
            file_val = file_data.get(file_key, "")
            cat_val = obj.get(cat_field, "")

            # Заполняем только если в каталоге пусто, а в файле есть данные
            if (not cat_val or not str(cat_val).strip()) and file_val and str(file_val).strip():
                obj[cat_field] = str(file_val).strip()
                changes.append(cat_field)

        # Sensory_Response — из home_prompt если пусто
        if not obj.get("Sensory_Response", "").strip():
            vis = file_data.get("visual_description", "")
            if vis:
                obj["Sensory_Response"] = vis
                changes.append("Sensory_Response")

        if changes:
            print(f"  📝 {name} ({folder}): +{len(changes)} полей → {', '.join(changes)}")
            updated += 1
        else:
            skipped += 1

    print(f"\n═══════════════════════════════════════")
    print(f"  📝 Обновлено: {updated}")
    print(f"  ⏭️  Без изменений: {skipped}")
    print(f"═══════════════════════════════════════")

    if updated > 0 and not dry_run:
        save_catalog(catalog)
        print(f"💾 Каталог сохранён: {CATALOG_PATH}")
    elif updated > 0 and dry_run:
        print(f"   (запусти без --dry чтобы сохранить)")


if __name__ == "__main__":
    main()
