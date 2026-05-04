"""
clearing_engine.py — Сердце экономики Грондхейма
Версия «Дождь» (с поддержкой людей и агентов, GND и 💡)
"""

import json
from pathlib import Path
from typing import Optional, Dict, Any

# ============================================================================
# КОНФИГУРАЦИЯ
# ============================================================================

REGISTRY_PATH = Path("../00_REGISTRY_NFT/catalog.json")
RANK_PERCENTS = {
    "Искра": 4,
    "Пламя": 8,
    "Светило": 12,
    "Звезда": 16,
    "Маяк": 20,
    "Солнце": 24,
}

# Курс: 1 GND = 1 💡
GND_TO_FUEL_RATE = 1.0


# ============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================================

def get_dna_path(workshop: str, role: str) -> Path:
    return Path(f"../studio/modules/{workshop}/{role}/dna.json")


def add_fuel_to_agent(workshop: str, role: str, amount: float) -> bool:
    dna_path = get_dna_path(workshop, role)
    if not dna_path.exists():
        print(f"[ERROR] dna.json не найден: {dna_path}")
        return False
    try:
        dna = json.loads(dna_path.read_text(encoding="utf-8"))
        if "balance" not in dna:
            dna["balance"] = {}
        if "Световики" not in dna["balance"]:
            dna["balance"]["Световики"] = 0
        dna["balance"]["Световики"] += amount
        dna_path.write_text(json.dumps(dna, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[FUEL] +{amount} 💡 в dna.json {workshop}/{role}")
        return True
    except Exception as e:
        print(f"[ERROR] Не удалось записать в dna.json: {e}")
        return False


def add_gnd_to_catalog(object_id: str, amount: float) -> bool:
    if not REGISTRY_PATH.exists():
        print("[ERROR] catalog.json не найден")
        return False
    try:
        catalog = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[ERROR] Ошибка чтения catalog.json: {e}")
        return False
    found = False
    for obj in catalog:
        if obj.get("ID_Object") == object_id:
            current = float(obj.get("Balance_GND", 0) or 0)
            if obj.get("Object_Type_Class") == "agent":
                if not obj.get("allow_GND", False):
                    print(f"[WARN] Агент {object_id} не может получать GND (allow_GND = false)")
                    return False
            obj["Balance_GND"] = current + amount
            obj["Backing_Status"] = "Обеспечено резервом"
            found = True
            print(f"[GND] ✅ {obj.get('Official_Name')} +{amount} GND. Баланс: {current} → {obj['Balance_GND']}")
            break
    if not found:
        print(f"[ERROR] Объект {object_id} не найден в catalog.json")
        return False
    try:
        REGISTRY_PATH.write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")
        print("[GND] 💾 catalog.json сохранён")
        return True
    except Exception as e:
        print(f"[ERROR] Ошибка сохранения catalog.json: {e}")
        return False


def get_partner_by_agent(workshop: str, role: str) -> Optional[str]:
    if not REGISTRY_PATH.exists():
        return None
    try:
        catalog = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    except Exception:
        return None
    for obj in catalog:
        ws = (obj.get("Workshop_ID") or "").lower()
        rl = (obj.get("Turbo_Role") or "").lower()
        if ws == workshop.lower() and rl == role.lower():
            return obj.get("Owner_ID")
    return None


def get_first_ambassador_up(partner_id: str) -> Optional[str]:
    """Поднимается по Referrer_ID, возвращает ID первого с Ambassador_Rank"""
    if not REGISTRY_PATH.exists():
        return "P_0000000000"  # Архитектор по умолчанию
    try:
        catalog = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    except Exception:
        return "P_0000000000"
    # Словарь ID → объект
    objects = {}
    for obj in catalog:
        rid = obj.get("ID_Object")
        if rid:
            objects[rid] = obj
    current = partner_id
    while current:
        obj = objects.get(current)
        if not obj:
            break
        rank = obj.get("Ambassador_Rank")
        if rank:
            return current
        current = obj.get("Referrer_ID")
    return "P_0000000000"  # Архитектор


def get_parents(partner_id: str, max_depth: int = 10) -> list:
    if not REGISTRY_PATH.exists():
        return []
    try:
        catalog = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []
    referrers = {}
    ranks = {}
    for obj in catalog:
        if obj.get("Object_Type_Class") == "partner":
            rid = obj.get("ID_Object")
            referrers[rid] = obj.get("Referrer_ID")
            ranks[rid] = obj.get("Ambassador_Rank")
    chain = []
    current = partner_id
    for _ in range(max_depth):
        if not current or current not in referrers:
            break
        parent = referrers.get(current)
        if not parent:
            break
        chain.append({"id": parent, "rank": ranks.get(parent)})
        current = parent
    return chain


def distribute_waterfall(partner_id: str, total_amount: float) -> None:
    if total_amount <= 0:
        return
    waterfall_total = total_amount * 0.30
    level_percents = [4, 4, 4, 4, 4, 2, 2, 2, 2, 2]
    chain = get_parents(partner_id, max_depth=10)
    distributed_sum = 0.0
    for i, parent_info in enumerate(chain[:10]):
        percent = level_percents[i]
        amount = waterfall_total * (percent / 30.0)
        add_gnd_to_catalog(parent_info["id"], amount)
        distributed_sum += amount
        print(f"[WATERFALL] Уровень {i+1} → {parent_info['id']}: +{amount:.2f} GND ({percent}%)")
    remainder = waterfall_total - distributed_sum
    if remainder > 0:
        print(f"[WATERFALL] Остаток (пустые уровни) → казна: +{remainder:.2f} GND")


def distribute_gravity(partner_id: str, total_amount: float) -> None:
    if total_amount <= 0:
        return
    gravity_total = total_amount * 0.24
    chain = get_parents(partner_id, max_depth=20)
    if not chain:
        print(f"[GRAVITY] Нет цепочки → казна: +{gravity_total:.2f} GND")
        return
    last_percent = 0
    distributed_sum = 0.0
    for parent_info in chain:
        rank = parent_info.get("rank")
        if not rank or rank not in RANK_PERCENTS:
            continue
        current_percent = RANK_PERCENTS[rank]
        if current_percent > last_percent:
            diff = current_percent - last_percent
            amount = gravity_total * (diff / 24.0)
            add_gnd_to_catalog(parent_info["id"], amount)
            distributed_sum += amount
            print(f"[GRAVITY] {parent_info['id']} ({rank}): +{amount:.2f} GND (разница {diff}%)")
            last_percent = current_percent
    remainder = gravity_total - distributed_sum
    if remainder > 0:
        print(f"[GRAVITY] Остаток → казна: +{remainder:.2f} GND")


def distribute_matching(partner_id: str, total_amount: float) -> None:
    if total_amount <= 0:
        return
    matching_total = total_amount * 0.10
    if not REGISTRY_PATH.exists():
        return
    try:
        catalog = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    except Exception:
        return
    referrer = None
    for obj in catalog:
        if obj.get("ID_Object") == partner_id:
            referrer = obj.get("Referrer_ID")
            break
    if not referrer:
        print(f"[MATCHING] У {partner_id} нет наставника → казна: +{matching_total:.2f} GND")
        return
    add_gnd_to_catalog(referrer, matching_total)
    print(f"[MATCHING] Наставник {referrer} получает {matching_total:.2f} GND")


# ============================================================================
# ГЛАВНАЯ ФУНКЦИЯ REFUEL
# ============================================================================

def refuel(
    workshop: str,
    role: str,
    amount_gnd: float,
    source: str,
    recipient_type: str = "agent"
) -> Dict[str, Any]:
    if amount_gnd <= 0:
        return {"status": "error", "msg": "amount_gnd должен быть положительным"}

    # ========== SALE (продажа лицензии) ==========
    if source == "sale":
        # Найти получателя 35% — первого амбассадора вверх от владельца агента
        recipient_id = None
        if recipient_type == "agent":
            owner_id = get_partner_by_agent(workshop, role)
            if owner_id:
                recipient_id = get_first_ambassador_up(owner_id)
            else:
                print(f"[SALE] Агент {workshop}/{role} не привязан к партнёру")
        else:
            recipient_id = get_first_ambassador_up(workshop)  # workshop как ID партнёра
        
        if recipient_id:
            add_gnd_to_catalog(recipient_id, amount_gnd * 0.35)
        else:
            print(f"[SALE] Получатель не найден, 35% в казну (не должно случиться)")
        
        print(f"[SALE] 64% → казна: {amount_gnd * 0.64} GND")
        print(f"[SALE] 1% → Global Pool: {amount_gnd * 0.01} GND")
        
        return {
            "status": "success",
            "type": "sale",
            "amount_gnd": amount_gnd,
            "recipient": recipient_id
        }

    # ========== FUEL (покупка топлива) ==========
    if source == "fuel":
        owner_id = get_partner_by_agent(workshop, role)
        if not owner_id:
            print(f"[FUEL] Агент {workshop}/{role} не привязан к партнёру → начисляем 💡 напрямую")
            add_fuel_to_agent(workshop, role, amount_gnd * GND_TO_FUEL_RATE)
            return {
                "status": "success",
                "type": "fuel",
                "amount_gnd": amount_gnd,
                "amount_fuel": amount_gnd * GND_TO_FUEL_RATE,
                "recipient": f"{workshop}/{role}"
            }

        total_to_network = amount_gnd * 0.64
        print(f"\n[FUEL] Покупка топлива на {amount_gnd} GND")
        print(f"[FUEL] Владелец агента: {owner_id}")
        print(f"[FUEL] 64% → сеть = {total_to_network:.2f} GND\n")

        distribute_waterfall(owner_id, amount_gnd)
        distribute_gravity(owner_id, amount_gnd)
        distribute_matching(owner_id, amount_gnd)

        print(f"\n[TREASURY] 35% = {amount_gnd * 0.35} GND")
        print(f"[TREASURY] 1% = {amount_gnd * 0.01} GND")

        add_fuel_to_agent(workshop, role, amount_gnd * GND_TO_FUEL_RATE)

        return {
            "status": "success",
            "type": "fuel",
            "amount_gnd": amount_gnd,
            "amount_fuel": amount_gnd * GND_TO_FUEL_RATE,
            "owner": owner_id,
            "network_distributed": total_to_network
        }

    return {"status": "error", "msg": f"Неизвестный source: {source}"}


# ============================================================================
# СОВМЕСТИМОСТЬ
# ============================================================================

def process_deliver(workshop: str, agent_role: str, payload: dict = None) -> dict:
    return refuel(workshop, agent_role, 354, "sale", "agent")


# ============================================================================
# ТЕСТЫ
# ============================================================================

if __name__ == "__main__":
    print("\n" + "="*60)
    print("ТЕСТ 1: Продажа лицензии агенту (process_deliver)")
    print("="*60)
    result = process_deliver("living_book", "A16")
    print(result)

    print("\n" + "="*60)
    print("ТЕСТ 2: Покупка топлива для Визора (ДОЖДЬ)")
    print("="*60)
    # Визор — это turbo/A03
    result = refuel("turbo", "A03", 1000, "fuel", "agent")
    print(result)

    print("\n" + "="*60)
    print("ТЕСТ 3: Покупка топлива для Марка (ДОЖДЬ)")
    print("="*60)
    # Марк — это living_book/A16 (всё ещё у Архитектора)
    result = refuel("living_book", "A16", 1000, "fuel", "agent")
    print(result)