"""
add_partner_fields.py — Инициализация социального графа Грондхейма
Версия с цифровыми ID для всех партнёров (включая Архитектора)
"""

import json
import random
from pathlib import Path

REGISTRY_PATH = Path("../00_REGISTRY_NFT/catalog.json")

def generate_partner_id() -> str:
    """Генерирует уникальный ID партнёра в формате P_XXXXXXXXXX"""
    random_digits = ''.join(str(random.randint(0, 9)) for _ in range(10))
    return f"P_{random_digits}"

def main():
    print("🚀 Запуск инициализации социального графа Грондхейма...")
    
    if not REGISTRY_PATH.exists():
        print("❌ catalog.json не найден!")
        return
    
    catalog = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    
    # ============================================================
    # 1. Добавляем поля агентам (Owner_ID, allow_GND)
    # ============================================================
    agents_updated = 0
    for obj in catalog:
        if obj.get("Object_Type_Class") == "agent":
            if "Owner_ID" not in obj:
                obj["Owner_ID"] = "P_0000000000"  # Архитектор
                agents_updated += 1
            if "allow_GND" not in obj:
                obj["allow_GND"] = False
                agents_updated += 1
    
    print(f"✅ Обновлено {agents_updated} агентов: добавлены Owner_ID и allow_GND")
    
    # ============================================================
    # 2. Создаём партнёров-людей (только цифровые ID)
    # ============================================================
    
    # Архитектор (P_0000000000)
    if not any(obj.get("ID_Object") == "P_0000000000" for obj in catalog):
        catalog.append({
            "ID_Object": "P_0000000000",
            "Object_Type_Class": "partner",
            "Official_Name": "Архитектор",
            "Referrer_ID": None,
            "Ambassador_Rank": "Солнце",
            "Balance_GND": 0,
            "Backing_Status": "Обеспечено резервом"
        })
        print("✅ Создан партнёр: P_0000000000 (Архитектор, ранг Солнце)")
    
    # Первый тестовый партнёр (P_0000000001)
    partner_1_id = "P_0000000001"
    if not any(obj.get("ID_Object") == partner_1_id for obj in catalog):
        catalog.append({
            "ID_Object": partner_1_id,
            "Object_Type_Class": "partner",
            "Official_Name": "Партнёр 1 (тестовый)",
            "Referrer_ID": "P_0000000000",
            "Ambassador_Rank": "Искра",
            "Balance_GND": 0,
            "Backing_Status": "Обеспечено резервом"
        })
        print(f"✅ Создан партнёр: {partner_1_id} (реферер = P_0000000000, ранг Искра)")
    
    # Второй тестовый партнёр (P_0000000002) — для проверки глубины
    partner_2_id = "P_0000000002"
    if not any(obj.get("ID_Object") == partner_2_id for obj in catalog):
        catalog.append({
            "ID_Object": partner_2_id,
            "Object_Type_Class": "partner",
            "Official_Name": "Партнёр 2 (тестовый)",
            "Referrer_ID": partner_1_id,
            "Ambassador_Rank": None,
            "Balance_GND": 0,
            "Backing_Status": "Обеспечено резервом"
        })
        print(f"✅ Создан партнёр: {partner_2_id} (реферер = {partner_1_id}, без ранга)")
    
    # ============================================================
    # 3. Передаём агентов партнёрам для теста
    # ============================================================
    
    # Визора — первому партнёру (P_0000000001)
    vizor_transferred = False
    for obj in catalog:
        if obj.get("ID_Object") == "022_TURBO_VIZOR":
            old_owner = obj.get("Owner_ID", "никому")
            obj["Owner_ID"] = partner_1_id
            vizor_transferred = True
            print(f"✅ Агент Визор (022_TURBO_VIZOR) передан от {old_owner} → {partner_1_id}")
            break
    
    if not vizor_transferred:
        print("⚠️ Агент 022_TURBO_VIZOR не найден, передача не выполнена")
    
    # ============================================================
    # 4. Сохраняем обратно
    # ============================================================
    REGISTRY_PATH.write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\n💾 catalog.json сохранён.")
    print("\n" + "="*60)
    print("🎉 СОЦИАЛЬНЫЙ ГРАФ ИНИЦИАЛИЗИРОВАН!")
    print("="*60)
    print("\nТеперь можно запускать clearing_engine.py и тестировать «Дождь».")
    print("\n📌 Цепочка для теста:")
    print("   P_0000000000 (Архитектор, ранг Солнце)")
    print("        ↑")
    print("   P_0000000001 (Партнёр 1, ранг Искра) ← владеет агентом Визор")
    print("        ↑")
    print("   P_0000000002 (Партнёр 2, без ранга)")

if __name__ == "__main__":
    main()