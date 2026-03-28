# check_catalog.py — Показывает что лежит в каталоге для конкретных агентов
# Запуск: python check_catalog.py

import json
from pathlib import Path

catalog = json.loads(Path("00_REGISTRY_NFT/catalog.json").read_text(encoding="utf-8"))

for o in catalog:
    name = o.get("Official_Name", "")
    if "Фабула" in name or "Вера Душа" in name or "Fable" in name or "Vera" in name:
        print(f"\n{'='*60}")
        print(f"ID: {o.get('ID_Object')}")
        print(f"Name: {name}")
        print(f"Workshop: {o.get('Workshop_ID')} / Folder: {o.get('Folder_Name')}")
        print(f"{'='*60}")
        
        fields = [
            "Hidden_History", "Sensory_Response", "Domain_Connection",
            "Relationships", "Object_Behavior", "Interaction_Scripts",
            "Visual_Base", "Unique_Mark", "Material_Texture",
            "Core_Phrase", "Anchor_Points", "Pull_Vector",
            "Hidden_Taste", "Trigger_Keywords", "Rarity",
        ]
        for f in fields:
            val = o.get(f, "<<MISSING>>")
            typ = type(val).__name__
            if isinstance(val, str):
                preview = val[:80] if val.strip() else "<<EMPTY STRING>>"
            elif isinstance(val, list):
                preview = f"[list len={len(val)}] {str(val)[:80]}"
            elif isinstance(val, dict):
                preview = f"[DICT!] {str(val)[:80]}"
            elif val is None:
                preview = "<<None>>"
            else:
                preview = str(val)[:80]
            
            status = "✅" if (isinstance(val, str) and val.strip()) or (isinstance(val, list) and val) else "❌"
            print(f"  {status} {f:25s} ({typ:5s}) {preview}")
