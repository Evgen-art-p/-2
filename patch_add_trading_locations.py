#!/usr/bin/env python3
"""
patch_add_trading_locations.py
Добавляет две локации в 00_REGISTRY_NFT/catalog.json:
  - Торговый Квартал (дом трейдеров) X=1179 Y=158 W=310 H=96
  - Биржа (рабочее место трейдеров)  X=2140 Y=172 W=130 H=73
"""

import json
import shutil
from pathlib import Path
from datetime import datetime

CATALOG_PATH = Path("00_REGISTRY_NFT/catalog.json")
BACKUP_EXT   = datetime.now().strftime("%Y%m%d_%H%M%S")

NEW_LOCATIONS = [
    {
        "Rarity": "Rare",
        "Object_Type_Class": "location",
        "Object_Type": "Location",
        "ID_Object": "0013_TRADING_QUARTER",
        "Official_Name": "Торговый Квартал",
        "Author_Signature": "[JAM] 6F-Origin",
        "Creation_Date": datetime.now().strftime("%Y-%m-%d"),
        "Social_Rank": "Хранитель",
        "Profession": "Дом трейдеров Грондхейма.",
        "Area_of_Responsibility": "Жилой район финансистов. Здесь живут те, кто умеет считать риски.",
        "Hidden_History": "Квартал вырос рядом с Биржей. Узкие улицы, закрытые ставни, разговоры вполголоса. Каждый житель знает цену тишины.",
        "Sensory_Response": "Запах кофе и свежей прессы. Утром — спокойно, вечером — оживлённо. Цифры в воздухе.",
        "Style_Tags": "#Финансы, #Тишина, #КофеИЦифры, #ЗакрытыеСтавни, #УзкиеУлицы",
        "Location_Connections": "Биржа, Площадь Резонанса, Таверна «Усталый Пиксель»",
        "Capacity": 9,
        "Scale": "small",
        "Lighting": "day",
        "Map_X": 1179,
        "Map_Y": 158,
        "Map_W": 310,
        "Map_H": 96,
        "_timestamp": datetime.now().isoformat(),
    },
    {
        "Rarity": "Rare",
        "Object_Type_Class": "location",
        "Object_Type": "Location",
        "ID_Object": "0014_EXCHANGE",
        "Official_Name": "Биржа",
        "Author_Signature": "[JAM] 6F-Origin",
        "Creation_Date": datetime.now().strftime("%Y-%m-%d"),
        "Social_Rank": "Хранитель",
        "Profession": "Рабочее место Военного Совета.",
        "Area_of_Responsibility": "Торговый зал. Здесь принимаются решения о входе и выходе.",
        "Hidden_History": "Построена на месте старого маяка. Говорят, первые сделки здесь заключались ещё при свечах. Теперь — только экраны и тишина перед решением.",
        "Sensory_Response": "Напряжение перед открытием. Щелчки клавиш. Тихие голоса. Момент, когда всё замирает — и ты нажимаешь кнопку.",
        "Style_Tags": "#Торговля, #Решение, #Напряжение, #Экраны, #ВоенныйСовет",
        "Location_Connections": "Торговый Квартал, Гавань Смыслов",
        "Capacity": 9,
        "Scale": "small",
        "Lighting": "neon",
        "Map_X": 2140,
        "Map_Y": 172,
        "Map_W": 130,
        "Map_H": 73,
        "_timestamp": datetime.now().isoformat(),
    },
]


def apply():
    print("=" * 55)
    print("patch_add_trading_locations.py")
    print("Торговый Квартал + Биржа → catalog.json")
    print("=" * 55)

    if not CATALOG_PATH.exists():
        raise FileNotFoundError(f"Не найден: {CATALOG_PATH}")

    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))

    existing_ids = {obj.get("ID_Object") for obj in catalog}

    added = []
    for loc in NEW_LOCATIONS:
        if loc["ID_Object"] in existing_ids:
            print(f"⚠️  {loc['ID_Object']} уже существует — пропускаем")
            continue
        catalog.append(loc)
        added.append(loc["Official_Name"])

    if not added:
        print("Всё уже добавлено.")
        return

    bak = CATALOG_PATH.with_suffix(f".json.bak_{BACKUP_EXT}")
    shutil.copy2(CATALOG_PATH, bak)
    print(f"[BACKUP] {bak.name}")

    CATALOG_PATH.write_text(
        json.dumps(catalog, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    for name in added:
        print(f"✅ Добавлено: {name}")

    print(f"\nВсего объектов в каталоге: {len(catalog)}")
    print("Локации появятся на карте после перезапуска студии.")


if __name__ == "__main__":
    apply()
