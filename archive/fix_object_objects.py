# fix_object_objects.py — Фикс [object Object] в каталоге
# Некоторые поля содержат dict вместо строки (Gemini Flash вернул JSON объект)
# В NiceGUI отображается как [object Object]
#
# Запуск: python fix_object_objects.py
# Студия «Шесть Пальцев» · Грондхейм · 2026

import json
from pathlib import Path

CATALOG_PATH = Path("00_REGISTRY_NFT/catalog.json")

# Поля которые ДОЛЖНЫ быть строкой (не dict, не list-of-dict)
TEXT_FIELDS = [
    "Object_Behavior", "Interaction_Scripts",
    "Visual_Base", "Unique_Mark", "Material_Texture",
    "Domain_Connection", "Relationships",
    "Hidden_History", "Sensory_Response",
    "Core_Phrase", "Anchor_Points",
]

def dict_to_text(val) -> str:
    """Превращает dict/list-of-dict в читаемый текст."""
    if val is None:
        return ""
    if isinstance(val, str):
        return val
    if isinstance(val, dict):
        # {"work": "делает X", "home": "делает Y"} → "work: делает X; home: делает Y"
        parts = []
        for k, v in val.items():
            parts.append(f"{k}: {v}")
        return "; ".join(parts)
    if isinstance(val, list):
        texts = []
        for item in val:
            if isinstance(item, dict):
                texts.append(dict_to_text(item))
            else:
                texts.append(str(item))
        return ", ".join(texts)
    return str(val)


def main():
    if not CATALOG_PATH.exists():
        print("❌ Каталог не найден!")
        return

    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    fixed = 0

    for obj in catalog:
        name = obj.get("Official_Name", "?")
        for field in TEXT_FIELDS:
            val = obj.get(field)
            if isinstance(val, dict):
                new_val = dict_to_text(val)
                obj[field] = new_val
                print(f"  🔧 {name}.{field}: dict → \"{new_val[:80]}...\"")
                fixed += 1
            elif isinstance(val, list):
                # Проверяем есть ли dict внутри списка
                has_dict = any(isinstance(x, dict) for x in val)
                if has_dict:
                    new_val = dict_to_text(val)
                    obj[field] = new_val
                    print(f"  🔧 {name}.{field}: list-of-dict → \"{new_val[:80]}...\"")
                    fixed += 1

    if fixed > 0:
        CATALOG_PATH.write_text(
            json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"\n💾 Исправлено {fixed} полей в {CATALOG_PATH}")
    else:
        print("✅ Все поля чистые, dict не найдено")


if __name__ == "__main__":
    main()
