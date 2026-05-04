"""
Тест Клиринга · Версия 2.0 (Автономная)
"""
import json
from pathlib import Path
from ministry.clearing_engine import process_deliver

# Пути задаём локально, чтобы не зависеть от импортов
REGISTRY_PATH = Path("00_REGISTRY_NFT/catalog.json")
MODULES_DIR = Path("studio/modules")

TEST_WORKSHOP = "living_book"
TEST_ROLE = "A99"

TEST_AGENT = {
    "Rarity": "Common",
    "Object_Type_Class": "agent",
    "ID_Object": "TEST_CLEARING_AGENT",
    "Official_Name": "Тестовый Марка",
    "Workshop_ID": TEST_WORKSHOP,
    "Turbo_Role": TEST_ROLE,
    "Balance_GND": 0.0,
    "Backing_Status": "Ожидает ликвидности"
}

print("⚙️ Готовим чистое окружение...")

# 1. Инжект тестового агента в каталог
if REGISTRY_PATH.exists():
    catalog = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
else:
    catalog = []

catalog = [a for a in catalog if a.get("ID_Object") != "TEST_CLEARING_AGENT"]
catalog.append(TEST_AGENT.copy())
REGISTRY_PATH.write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")
print("✅ Агент внедрён в catalog.json")

# 2. Создаём/сбрасываем dna.json
dna_path = MODULES_DIR / TEST_WORKSHOP / TEST_ROLE / "dna.json"
dna_path.parent.mkdir(parents=True, exist_ok=True)
dna_path.write_text(json.dumps({
    "id": TEST_AGENT["ID_Object"],
    "workshop": TEST_WORKSHOP,
    "role": TEST_ROLE,
    "balance": {"GND": 0.0, "Теплики": 0, "Световики": 0}
}, ensure_ascii=False, indent=2), encoding="utf-8")
print("✅ Агент внедрён в dna.json")

# 3. Запускаем deliver
print("\n📦 Запуск симуляции deliver...")
result = process_deliver(
    workshop=TEST_WORKSHOP,
    agent_role=TEST_ROLE,
    payload={"valid": True, "complexity": 2.0, "quality_score": 0.9}
)
print(f"🔹 Ответ: {result}\n")

# 4. Прямая проверка файлов
catalog_check = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
agent_ui = next((a for a in catalog_check if a.get("ID_Object") == "TEST_CLEARING_AGENT"), None)

dna_check = json.loads(dna_path.read_text(encoding="utf-8"))
balance_runtime = dna_check.get("balance", {}).get("GND", 0)

print("📊 ПРОВЕРКА СИНХРОНИЗАЦИИ:")
print(f"  🖥️ UI (catalog.json) → Balance_GND: {agent_ui.get('Balance_GND', 'ERR') if agent_ui else 'NOT FOUND'}")
print(f"  🧬 Runtime (dna.json) → balance.GND: {balance_runtime}")

print("\n" + "="*40)
if agent_ui and float(agent_ui.get("Balance_GND", 0)) > 0:
    print("🔥 ТЕСТ ПРОЙДЕН УСПЕШНО! Кровь течёт по венам.")
else:
    print("❌ БАЛАНС НЕ ОБНОВИЛСЯ. Проверь пути к файлам.")