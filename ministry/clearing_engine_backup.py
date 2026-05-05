"""
clearing_engine.py — Сердце экономики Грондхейма
Версия «КАРТА + КАЗНА» — полное соответствие Генеральному плану от 4 мая 2026
"""

import json
from pathlib import Path
from typing import Optional, Dict, Any
import config

# ============================================================================
# КОНФИГУРАЦИЯ (из карты)
# ============================================================================

REGISTRY_PATH = Path(config.REGISTRY_PATH)
STUDIO_MODULES_PATH = Path(config.STUDIO_MODULES_PATH)

# Системные ID
TREASURY_ID = "TREASURY"
GLOBAL_POOL_ID = "GLOBAL_POOL"

# Ранги и бонусы (по карте: 0% → 3%)
RANK_BONUS = {
    "Искра": 0.0,
    "Пламя": 0.5,
    "Светило": 1.0,
    "Звезда": 1.5,
    "Маяк": 2.0,
    "Солнце": 3.0,
}

MAX_BONUS = 3.0  # Солнце

# Водопад: 30% от покупки, распределение по уровням
WATERFALL_LEVELS = [4, 4, 4, 4, 4, 2, 2, 2, 2, 2]  # проценты от 30%

# ============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================================

def get_dna_path(workshop: str, role: str) -> Path:
    return STUDIO_MODULES_PATH / workshop / role / "dna.json"

def get_catalog() -> list:
    if not REGISTRY_PATH.exists():
        return []
    with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def save_catalog(catalog: list) -> bool:
    with open(REGISTRY_PATH, "w", encoding="utf-8") as f:
        json.dump(catalog, f, ensure_ascii=False, indent=2)
    return True

def get_balance_gnd(object_id: str) -> float:
    catalog = get_catalog()
    for obj in catalog:
        if obj.get("ID_Object") == object_id:
            return float(obj.get("Balance_GND", 0) or 0)
    return 0.0

def add_gnd_to_catalog(object_id: str, amount: float) -> bool:
    if amount == 0:
        return True
    if abs(amount) < 0.0001:
        return True
    catalog = get_catalog()
    for obj in catalog:
        if obj.get("ID_Object") == object_id:
            # Системным объектам разрешено всё
            if obj.get("Object_Type_Class") == "agent" and not obj.get("allow_GND", False):
                if object_id not in [TREASURY_ID, GLOBAL_POOL_ID]:
                    print(f"[AXIOM] 🚨 Агент {object_id} не может получать GND (allow_GND=false)")
                    return False
            current = float(obj.get("Balance_GND", 0) or 0)
            obj["Balance_GND"] = current + amount
            obj["Backing_Status"] = "Обеспечено резервом"
            save_catalog(catalog)
            name = obj.get('Official_Name', object_id)
            if object_id == TREASURY_ID:
                print(f"[TREASURY] 💰 +{amount:.2f} GND → {current + amount:.2f}")
            elif object_id == GLOBAL_POOL_ID:
                print(f"[GLOBAL_POOL] 🌍 +{amount:.2f} GND → {current + amount:.2f}")
            else:
                print(f"[NIKO] {name} +{amount:.2f} GND → {current + amount:.2f}")
            return True
    print(f"[ERROR] Объект {object_id} не найден в catalog.json")
    return False

def add_fuel_to_agent(workshop: str, role: str, amount: float) -> bool:
    dna_path = get_dna_path(workshop, role)
    if not dna_path.exists():
        print(f"[ERROR] dna.json не найден: {dna_path}")
        return False
    with open(dna_path, "r", encoding="utf-8") as f:
        dna = json.load(f)
    if "balance" not in dna:
        dna["balance"] = {}
    if "Световики" not in dna["balance"]:
        dna["balance"]["Световики"] = 0.0
    dna["balance"]["Световики"] += amount
    with open(dna_path, "w", encoding="utf-8") as f:
        json.dump(dna, f, ensure_ascii=False, indent=2)
    print(f"[FUEL] {workshop}/{role} +{amount:.2f} 💡 (баланс: {dna['balance']['Световики']:.2f})")
    return True

def get_fuel_balance(workshop: str, role: str) -> float:
    dna_path = get_dna_path(workshop, role)
    if not dna_path.exists():
        return 0.0
    with open(dna_path, "r", encoding="utf-8") as f:
        dna = json.load(f)
    return dna.get("balance", {}).get("Световики", 0.0)

def check_memory_deposit(workshop: str, role: str) -> bool:
    """Депозит Личности: 100 💡 минимум для работы агента"""
    balance = get_fuel_balance(workshop, role)
    if balance < config.MEMORY_DEPOSIT_LIMIT:
        print(f"[AXIOM] 🚨 {workshop}/{role}: баланс {balance:.2f} 💡 < {config.MEMORY_DEPOSIT_LIMIT} — АГЕНТ В АРХИВЕ")
        return False
    return True

def transfer_gnd(sender_id: str, receiver_id: str, amount: float) -> bool:
    """Комиссия 1 GND за перевод (защита от спама)"""
    if amount <= 0:
        return False
    fee = config.TRANSFER_FEE
    total = amount + fee
    
    if get_balance_gnd(sender_id) < total:
        print(f"[NIKO] Ошибка: у {sender_id} недостаточно GND")
        return False
    
    if add_gnd_to_catalog(sender_id, -total) and add_gnd_to_catalog(receiver_id, amount):
        # Комиссия 1 GND уходит в казну
        add_gnd_to_catalog(TREASURY_ID, fee)
        print(f"[NIKO] {sender_id} → {receiver_id}: {amount} GND (комиссия {fee} GND в казну)")
        return True
    return False

def get_partner_by_agent(workshop: str, role: str) -> Optional[str]:
    catalog = get_catalog()
    for obj in catalog:
        if obj.get("Workshop_ID") == workshop and obj.get("Turbo_Role") == role:
            return obj.get("Owner_ID")
    return None

def get_referrer(partner_id: str) -> Optional[str]:
    catalog = get_catalog()
    for obj in catalog:
        if obj.get("ID_Object") == partner_id and obj.get("Object_Type_Class") == "partner":
            return obj.get("Referrer_ID")
    return None

def get_ambassador_rank(partner_id: str) -> Optional[str]:
    catalog = get_catalog()
    for obj in catalog:
        if obj.get("ID_Object") == partner_id:
            return obj.get("Ambassador_Rank")
    return None

def get_parents(partner_id: str, max_depth: int = 10) -> list:
    """Возвращает цепочку вышестоящих партнёров [{id, rank}, ...]"""
    catalog = get_catalog()
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
        parent = referrers.get(current)
        if not parent:
            break
        chain.append({"id": parent, "rank": ranks.get(parent)})
        current = parent
    return chain

def get_first_ambassador_up(partner_id: str) -> Optional[str]:
    """Поднимается вверх, возвращает ID первого с рангом или Архитектора"""
    parents = get_parents(partner_id, max_depth=20)
    for p in parents:
        if p["rank"]:
            return p["id"]
    return "P_0000000000"

# ============================================================================
# РАСПРЕДЕЛЕНИЕ «ДОЖДЯ»
# ============================================================================

def distribute_waterfall(partner_id: str, purchase_amount_gnd: float) -> None:
    """Водопад: 30% от покупки, фиксированные проценты по уровням"""
    total = purchase_amount_gnd * 0.30
    if total <= 0:
        return
    
    chain = get_parents(partner_id, max_depth=10)
    distributed = 0.0
    
    for i, parent_info in enumerate(chain[:10]):
        percent = WATERFALL_LEVELS[i]
        amount = total * (percent / 30.0)
        add_gnd_to_catalog(parent_info["id"], amount)
        distributed += amount
        print(f"[WATERFALL] Уровень {i+1} ({parent_info['id']}): +{amount:.2f} GND ({percent}%)")
    
    # Остаток — в казну
    remainder = total - distributed
    if remainder > 0:
        add_gnd_to_catalog(TREASURY_ID, remainder)
        print(f"[WATERFALL] Остаток → казна: +{remainder:.2f} GND")

def distribute_gravity(partner_id: str, purchase_amount_gnd: float) -> None:
    """
    Гравитация: 24% от покупки.
    Распределяется по разнице рангов (по карте: 0% → 3%).
    """
    total = purchase_amount_gnd * 0.24
    if total <= 0:
        return
    
    chain = get_parents(partner_id, max_depth=20)
    if not chain:
        add_gnd_to_catalog(TREASURY_ID, total)
        print(f"[GRAVITY] Нет цепочки → казна: +{total:.2f} GND")
        return
    
    distributed = 0.0
    last_bonus = 0.0
    
    for parent_info in chain:
        rank = parent_info["rank"]
        if not rank or rank not in RANK_BONUS:
            continue
        
        current_bonus = RANK_BONUS[rank]  # 0, 0.5, 1, 1.5, 2, 3
        if current_bonus > last_bonus:
            diff = current_bonus - last_bonus  # разница в процентах
            # diff / MAX_BONUS (3) = доля от фонда гравитации (24%)
            amount = total * (diff / MAX_BONUS)
            add_gnd_to_catalog(parent_info["id"], amount)
            distributed += amount
            print(f"[GRAVITY] {parent_info['id']} ({rank}, +{diff}%): +{amount:.2f} GND")
            last_bonus = current_bonus
    
    remainder = total - distributed
    if remainder > 0:
        add_gnd_to_catalog(TREASURY_ID, remainder)
        print(f"[GRAVITY] Остаток → казна: +{remainder:.2f} GND")

def distribute_matching(partner_id: str, purchase_amount_gnd: float) -> None:
    """Сопричастность: 10% прямому наставнику"""
    total = purchase_amount_gnd * 0.10
    if total <= 0:
        return
    
    referrer = get_referrer(partner_id)
    if not referrer:
        add_gnd_to_catalog(TREASURY_ID, total)
        print(f"[MATCHING] У {partner_id} нет наставника → казна: +{total:.2f} GND")
        return
    
    add_gnd_to_catalog(referrer, total)
    print(f"[MATCHING] Наставник {referrer}: +{total:.2f} GND")

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
    """
    Покупка топлива или продажа лицензии
    
    source: "sale" (продажа лицензии) или "fuel" (покупка топлива)
    """
    if amount_gnd <= 0:
        return {"status": "error", "msg": "amount_gnd должен быть положительным"}
    
    # ========== SALE (продажа лицензии) ==========
    if source == "sale":
        recipient_id = None
        if recipient_type == "agent":
            owner_id = get_partner_by_agent(workshop, role)
            if owner_id:
                recipient_id = get_first_ambassador_up(owner_id)
        else:
            recipient_id = get_first_ambassador_up(workshop)
        
        # 35% первому амбассадору
        if recipient_id:
            add_gnd_to_catalog(recipient_id, amount_gnd * 0.35)
        else:
            add_gnd_to_catalog(TREASURY_ID, amount_gnd * 0.35)
            print(f"[SALE] Получатель не найден, 35% в казну")
        
        # 64% в казну (прямая продажа без сети)
        add_gnd_to_catalog(TREASURY_ID, amount_gnd * 0.64)
        
        # 1% в глобальный пул
        add_gnd_to_catalog(GLOBAL_POOL_ID, amount_gnd * 0.01)
        
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
            # Агент не привязан к партнёру — начисляем топливо напрямую
            fuel = amount_gnd * config.GND_TO_FUEL_RATE
            add_fuel_to_agent(workshop, role, fuel)
            # 35% в казну
            add_gnd_to_catalog(TREASURY_ID, amount_gnd * 0.35)
            # 1% в глобальный пул
            add_gnd_to_catalog(GLOBAL_POOL_ID, amount_gnd * 0.01)
            return {
                "status": "success",
                "type": "fuel",
                "amount_gnd": amount_gnd,
                "amount_fuel": fuel,
                "recipient": f"{workshop}/{role}"
            }
        
        print(f"\n[FUEL] ========== ПОКУПКА ТОПЛИВА ==========")
        print(f"[FUEL] Агент: {workshop}/{role}")
        print(f"[FUEL] Владелец: {owner_id}")
        print(f"[FUEL] Сумма: {amount_gnd} GND")
        print(f"[FUEL] Курс: 1 GND = {config.GND_TO_FUEL_RATE} 💡")
        
        # Конвертация в топливо
        fuel_received = amount_gnd * config.GND_TO_FUEL_RATE
        add_fuel_to_agent(workshop, role, fuel_received)
        print(f"[FUEL] Зачислено: {fuel_received} 💡")
        
        # Распределение «Дождя» (64%)
        print(f"\n[RAIN] Распределение 64% = {amount_gnd * 0.64} GND:")
        distribute_waterfall(owner_id, amount_gnd)
        distribute_gravity(owner_id, amount_gnd)
        distribute_matching(owner_id, amount_gnd)
        
        # 35% в казну
        treasury_35 = amount_gnd * 0.35
        add_gnd_to_catalog(TREASURY_ID, treasury_35)
        print(f"\n[TREASURY] 35% → казна: +{treasury_35:.2f} GND")
        
        # 1% в глобальный пул
        global_pool_1 = amount_gnd * 0.01
        add_gnd_to_catalog(GLOBAL_POOL_ID, global_pool_1)
        print(f"[GLOBAL_POOL] 1% → пул: +{global_pool_1:.2f} GND")
        
        return {
            "status": "success",
            "type": "fuel",
            "amount_gnd": amount_gnd,
            "amount_fuel": fuel_received,
            "owner": owner_id
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
    if check_memory_deposit("turbo", "A03"):
        result = refuel("turbo", "A03", 1000, "fuel", "agent")
        print(result)
    else:
        print("❌ Агент не прошёл проверку Депозита Личности")

    print("\n" + "="*60)
    print("ТЕСТ 3: Покупка топлива для Марка (ДОЖДЬ)")
    print("="*60)
    result = refuel("living_book", "A16", 1000, "fuel", "agent")
    print(result)
    
    print("\n" + "="*60)
    print("ТЕСТ 4: Проверка балансов системных объектов")
    print("="*60)
    print(f"Баланс TREASURY: {get_balance_gnd(TREASURY_ID):.2f} GND")
    print(f"Баланс GLOBAL_POOL: {get_balance_gnd(GLOBAL_POOL_ID):.2f} GND")