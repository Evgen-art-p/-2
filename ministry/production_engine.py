"""
production_engine.py — Цикл работы агента
Трата топлива (💡) при генерации контента + выплата Роялти автору картриджа.

Структура траты 100 💡:
    75 💡 → API / Compute (сгорают)
     7 💡 → Development (агенту → 🔆 репутация)
    10 💡 → Rent (владельцу локации → GND из казны)
     3 💡 → Insurance (страхфонд → GND из казны)
     5 💡 → Royalty (автору картриджа → GND из казны)

Обновлено: 5 мая 2026
"""

import json
from pathlib import Path
from typing import Optional, Dict, Any
import config

# ============================================================================
# ИМПОРТ ИЗ CLEARING ENGINE
# ============================================================================

from clearing_engine import (
    CATALOG_PATH,
    PARTNERS_PATH,
    SYSTEM_PATH,
    TREASURY_ID,
    GLOBAL_POOL_ID,
    get_catalog,
    save_catalog,
    get_partners,
    get_system,
    get_partner_obj,
    get_system_obj,
    get_agent_obj,
    get_balance_gnd,
    add_gnd_to_catalog,
    get_dna_path,
    get_fuel_balance,
    check_memory_deposit,
)

STUDIO_MODULES_PATH = Path(config.STUDIO_MODULES_PATH)

# ============================================================================
# КОНСТАНТЫ ПРОИЗВОДСТВА
# ============================================================================

# Распределение 100 💡 при работе агента
FUEL_API_SHARE        = 0.75   # 75 💡 → сгорают (API/Compute)
FUEL_DEV_SHARE        = 0.07   # 7 💡  → агенту (репутация 🔆)
FUEL_RENT_SHARE       = 0.10   # 10 💡 → владельцу локации (GND из казны)
FUEL_INSURANCE_SHARE  = 0.03   # 3 💡  → страхфонд (GND из казны)
FUEL_ROYALTY_SHARE    = 0.05   # 5 💡  → автору картриджа (GND из казны)

# Курс перевода 💡 → GND для выплат из казны
# (казна покрывает Rent, Insurance, Royalty по текущему курсу)
FUEL_TO_GND_RATE = 1.0 / config.GND_TO_FUEL_RATE   # 1 💡 = 0.1 GND

# Минимальный остаток 💡 для работы (Депозит Личности)
MEMORY_DEPOSIT = config.MEMORY_DEPOSIT_LIMIT

# Страховой фонд — системный объект
INSURANCE_FUND_ID = "INSURANCE_FUND"

# ============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================================

def get_cartridge_author(workshop: str) -> Optional[str]:
    """
    Возвращает Cartridge_Author_ID для картриджа (Workshop_ID).
    Ищет первого агента из этого цеха и берёт его Author_ID.
    Все агенты одного цеха имеют одного автора.
    """
    for obj in get_catalog():
        if (obj.get("Object_Type_Class") == "agent"
                and obj.get("Workshop_ID") == workshop
                and obj.get("Cartridge_Author_ID")):
            return obj["Cartridge_Author_ID"]
    return None

def get_location_owner(workshop: str) -> Optional[str]:
    """
    Возвращает владельца локации (Owner_ID картриджа).
    Для Rent — платим владельцу цеха.
    """
    for obj in get_catalog():
        if (obj.get("Object_Type_Class") == "agent"
                and obj.get("Workshop_ID") == workshop):
            return obj.get("Owner_ID")
    return None

def add_reputation_to_agent(workshop: str, role: str, amount: float) -> bool:
    """
    Начисляет репутацию (🔆) агенту в dna.json.
    Development: 7% от потраченного топлива.
    """
    dna_path = get_dna_path(workshop, role)
    if not dna_path.exists():
        print(f"[PROD] ⚠️ dna.json не найден: {dna_path}")
        return False

    with open(dna_path, "r", encoding="utf-8") as f:
        dna = json.load(f)

    dna.setdefault("balance", {})
    dna.setdefault("reputation", {})

    # Вычитаем топливо
    current_fuel = dna["balance"].get("Световики", 0.0)
    dna["balance"]["Световики"] = round(current_fuel - amount, 4)

    # Начисляем репутацию
    rep_gain = round(amount * FUEL_DEV_SHARE, 4)
    current_rep = dna["reputation"].get("Звёзды", 0.0)
    dna["reputation"]["Звёзды"] = round(current_rep + rep_gain, 4)

    with open(dna_path, "w", encoding="utf-8") as f:
        json.dump(dna, f, ensure_ascii=False, indent=2)

    return True

def fuel_to_gnd(fuel_amount: float) -> float:
    """Конвертирует 💡 в GND для выплат из казны."""
    return round(fuel_amount * FUEL_TO_GND_RATE, 4)

# ============================================================================
# ПРОВЕРКА NFT-ЛИЦЕНЗИИ
# ============================================================================

def check_license(partner_id: str, workshop: str) -> Dict[str, Any]:
    """
    Проверяет наличие NFT-лицензии на картридж у партнёра.

    Логика App Store:
    1. Базовые картриджи (turbo, social_mix, video_long, video_shorts,
       residents) — у всех партнёров есть по умолчанию.
    2. Платные картриджи — проверяем поле purchased_cartridges в partners.json.

    Возвращает: {"allowed": bool, "reason": str}

    Когда будет Web3:
        Заменить тело на проверку владения NFT-токеном в блокчейне.
        contract.functions.hasLicense(partner_wallet, cartridge_id).call()
    """
    FREE_CARTRIDGES = {
        "residents", "turbo", "social_mix", "video_long", "video_shorts"
    }

    if workshop in FREE_CARTRIDGES:
        return {"allowed": True, "reason": "базовый картридж"}

    obj = get_partner_obj(partner_id)
    if not obj:
        return {"allowed": False, "reason": f"партнёр {partner_id} не найден"}

    purchased = obj.get("purchased_cartridges", [])
    if workshop in purchased:
        return {"allowed": True, "reason": f"лицензия куплена ({workshop})"}

    return {
        "allowed": False,
        "reason": f"нет лицензии на '{workshop}' — купите NFT-картридж"
    }

# ============================================================================
# ГЛАВНАЯ ФУНКЦИЯ: РАБОТА АГЕНТА
# ============================================================================

def produce(
    workshop: str,
    role: str,
    fuel_cost: float = 100.0,
    task_description: str = ""
) -> Dict[str, Any]:
    """
    Запускает цикл работы агента — тратит топливо и распределяет выплаты.

    workshop: ID картриджа (например "living_book")
    role:     роль агента внутри картриджа (например "A16")
    fuel_cost: стоимость задачи в 💡 (по умолчанию 100 💡)
    task_description: описание задачи для лога

    Распределение fuel_cost:
        75% → API (сгорают)
         7% → Development (репутация агента)
        10% → Rent (владельцу локации, GND из казны)
         3% → Insurance (страхфонд, GND из казны)
         5% → Royalty (автору картриджа, GND из казны)
    """

    print(f"\n[PROD] ══════════ ПРОИЗВОДСТВО ══════════")
    print(f"[PROD] Агент:   {workshop}/{role}")
    if task_description:
        print(f"[PROD] Задача:  {task_description}")
    print(f"[PROD] Стоимость: {fuel_cost:.2f} 💡")

    # ── 1. ПРОВЕРКА БАЛАНСА ───────────────────────────────────────────────
    current_fuel = get_fuel_balance(workshop, role)
    if current_fuel < fuel_cost + MEMORY_DEPOSIT:
        msg = (f"недостаточно топлива: {current_fuel:.2f} 💡 "
               f"(нужно {fuel_cost:.2f} + {MEMORY_DEPOSIT:.0f} депозит)")
        print(f"[AXIOM] 🚨 {msg}")
        return {"status": "error", "msg": msg}

    # ── 2. ПРОВЕРКА ЛИЦЕНЗИИ ──────────────────────────────────────────────
    owner_id  = (get_agent_obj(workshop, role) or {}).get("Owner_ID")
    if owner_id:
        license_check = check_license(owner_id, workshop)
        if not license_check["allowed"]:
            print(f"[LICENSE] 🚫 {license_check['reason']}")
            return {"status": "error", "msg": license_check["reason"]}
        print(f"[LICENSE] ✅ {license_check['reason']}")

    # ── 3. РАСЧЁТ ДОЛЕЙ ───────────────────────────────────────────────────
    api_fuel        = round(fuel_cost * FUEL_API_SHARE,       4)   # 75 💡
    dev_fuel        = round(fuel_cost * FUEL_DEV_SHARE,       4)   # 7 💡
    rent_fuel       = round(fuel_cost * FUEL_RENT_SHARE,      4)   # 10 💡
    insurance_fuel  = round(fuel_cost * FUEL_INSURANCE_SHARE, 4)   # 3 💡
    royalty_fuel    = round(fuel_cost * FUEL_ROYALTY_SHARE,   4)   # 5 💡

    rent_gnd        = fuel_to_gnd(rent_fuel)
    insurance_gnd   = fuel_to_gnd(insurance_fuel)
    royalty_gnd     = fuel_to_gnd(royalty_fuel)

    print(f"\n[PROD] Распределение {fuel_cost:.0f} 💡:")
    print(f"[PROD]   API/Compute:  {api_fuel:.2f} 💡 (сгорают)")
    print(f"[PROD]   Development:  {dev_fuel:.2f} 💡 → репутация агента")
    print(f"[PROD]   Rent:         {rent_fuel:.2f} 💡 = {rent_gnd:.4f} GND → владелец локации")
    print(f"[PROD]   Insurance:    {insurance_fuel:.2f} 💡 = {insurance_gnd:.4f} GND → страхфонд")
    print(f"[PROD]   Royalty:      {royalty_fuel:.2f} 💡 = {royalty_gnd:.4f} GND → автор картриджа")

    # ── 4. ТРАТА ТОПЛИВА + РЕПУТАЦИЯ ──────────────────────────────────────
    add_reputation_to_agent(workshop, role, fuel_cost)
    print(f"\n[DEV] 🔆 {workshop}/{role}: -{fuel_cost:.2f} 💡, +{dev_fuel:.4f} репутации")

    # ── 5. RENT → ВЛАДЕЛЕЦ ЛОКАЦИИ ────────────────────────────────────────
    location_owner = get_location_owner(workshop) or TREASURY_ID
    # Казна покрывает Rent и переводит владельцу
    add_gnd_to_catalog(TREASURY_ID, -rent_gnd)
    add_gnd_to_catalog(location_owner, rent_gnd)
    print(f"[RENT] 🏠 {location_owner}: +{rent_gnd:.4f} GND (из казны)")

    # ── 6. INSURANCE → СТРАХФОНД ──────────────────────────────────────────
    # Проверяем есть ли страхфонд в system.json, если нет — в казну
    system = get_system()
    insurance_target = TREASURY_ID
    for obj in system:
        if obj.get("ID_Object") == INSURANCE_FUND_ID:
            insurance_target = INSURANCE_FUND_ID
            break

    add_gnd_to_catalog(TREASURY_ID, -insurance_gnd)
    add_gnd_to_catalog(insurance_target, insurance_gnd)
    print(f"[INS]  🛡 {insurance_target}: +{insurance_gnd:.4f} GND (из казны)")

    # ── 7. ROYALTY → АВТОР КАРТРИДЖА ──────────────────────────────────────
    cartridge_author = get_cartridge_author(workshop) or TREASURY_ID
    add_gnd_to_catalog(TREASURY_ID, -royalty_gnd)
    add_gnd_to_catalog(cartridge_author, royalty_gnd)

    if cartridge_author == TREASURY_ID:
        print(f"[ROYALTY] 📦 Автор не найден → казна: +{royalty_gnd:.4f} GND")
    else:
        author_name = (get_partner_obj(cartridge_author) or {}).get(
            "Official_Name", cartridge_author)
        print(f"[ROYALTY] 💎 {author_name} ({cartridge_author}): +{royalty_gnd:.4f} GND")

    # ── 8. ИТОГ ───────────────────────────────────────────────────────────
    new_fuel = get_fuel_balance(workshop, role)
    print(f"\n[PROD] ✅ Задача выполнена")
    print(f"[PROD] Топливо агента: {current_fuel:.2f} → {new_fuel:.2f} 💡")

    return {
        "status":           "success",
        "workshop":         workshop,
        "role":             role,
        "fuel_spent":       fuel_cost,
        "fuel_remaining":   new_fuel,
        "api_burned":       api_fuel,
        "dev_reputation":   dev_fuel,
        "rent_gnd":         rent_gnd,
        "rent_recipient":   location_owner,
        "insurance_gnd":    insurance_gnd,
        "royalty_gnd":      royalty_gnd,
        "royalty_recipient": cartridge_author,
    }

# ============================================================================
# ПОКУПКА NFT-ЛИЦЕНЗИИ НА КАРТРИДЖ
# ============================================================================

def buy_cartridge_license(
    partner_id: str,
    workshop: str,
    price_gnd: float
) -> Dict[str, Any]:
    """
    Партнёр покупает NFT-лицензию на платный картридж.

    1. Проверяем что лицензии ещё нет
    2. Списываем GND с баланса партнёра
    3. Запускаем Дождь (64% по сети)
    4. 35% → казна
    5. 1% → Global Pool
    6. Записываем лицензию в partners.json → purchased_cartridges

    Когда будет Web3:
        После шага 6 вызвать mint_license_nft(partner_id, workshop)
        и записать tx_hash в purchased_cartridges как объект.
    """
    FREE_CARTRIDGES = {
        "residents", "turbo", "social_mix", "video_long", "video_shorts"
    }

    if workshop in FREE_CARTRIDGES:
        return {"status": "error", "msg": f"'{workshop}' — базовый картридж, он бесплатный"}

    # Проверяем нет ли уже лицензии
    license_check = check_license(partner_id, workshop)
    if license_check["allowed"]:
        return {"status": "error", "msg": f"лицензия на '{workshop}' уже есть"}

    # Проверяем баланс
    balance = get_balance_gnd(partner_id)
    if balance < price_gnd:
        return {
            "status": "error",
            "msg": f"недостаточно GND: {balance:.2f} < {price_gnd:.2f}"
        }

    # Списываем с партнёра
    add_gnd_to_catalog(partner_id, -price_gnd)

    # Дождь от покупки лицензии (64% в сеть, 35% казна, 1% пул)
    from clearing_engine import (
        distribute_waterfall, distribute_gravity, distribute_matching
    )
    print(f"\n[LICENSE] 🔑 Покупка лицензии '{workshop}' за {price_gnd:.2f} GND")
    print(f"[RAIN] Дождь 64% = {price_gnd * 0.64:.2f} GND:")
    distribute_waterfall(partner_id, price_gnd)
    distribute_gravity(partner_id, price_gnd)
    distribute_matching(partner_id, price_gnd)

    add_gnd_to_catalog(TREASURY_ID,    price_gnd * 0.35)
    add_gnd_to_catalog(GLOBAL_POOL_ID, price_gnd * 0.01)
    print(f"[TREASURY]   35% → +{price_gnd * 0.35:.2f} GND")
    print(f"[GLOBAL_POOL] 1% → +{price_gnd * 0.01:.2f} GND")

    # Записываем лицензию
    partners = get_partners()
    for obj in partners:
        if obj.get("ID_Object") == partner_id:
            obj.setdefault("purchased_cartridges", [])
            if workshop not in obj["purchased_cartridges"]:
                obj["purchased_cartridges"].append(workshop)

            # Место для NFT-адреса (заполнит mint_license_nft когда будет Web3)
            obj.setdefault("cartridge_nft_addresses", {})
            obj["cartridge_nft_addresses"][workshop] = f"mock_license_{partner_id}_{workshop}"
            break

    from clearing_engine import save_partners
    save_partners(partners)

    partner_name = (get_partner_obj(partner_id) or {}).get("Official_Name", partner_id)
    print(f"\n[LICENSE] ✅ {partner_name} получил лицензию на '{workshop}'")
    print(f"[LICENSE] NFT-адрес: mock_license_{partner_id}_{workshop}")
    print(f"[LICENSE] (Web3: здесь будет вызов mint_license_nft)")

    return {
        "status":    "success",
        "partner":   partner_id,
        "workshop":  workshop,
        "price_gnd": price_gnd,
        "nft_mock":  f"mock_license_{partner_id}_{workshop}",
    }

# ============================================================================
# ТЕСТЫ
# ============================================================================

if __name__ == "__main__":

    print("\n" + "="*60)
    print("ТЕСТ 1: Работа агента — трата 100 💡 с роялти")
    print("="*60)
    result = produce(
        workshop="living_book",
        role="A16",
        fuel_cost=100.0,
        task_description="Создание детской сказки"
    )
    print(f"\nРезультат: {result['status']}")
    if result["status"] == "success":
        print(f"Роялти получил: {result['royalty_recipient']} "
              f"(+{result['royalty_gnd']:.4f} GND)")

    print("\n" + "="*60)
    print("ТЕСТ 2: Проверка лицензии — базовый картридж")
    print("="*60)
    check = check_license("P_0000000001", "turbo")
    print(f"turbo для P_0000000001: {check}")

    print("\n" + "="*60)
    print("ТЕСТ 3: Проверка лицензии — платный картридж (нет лицензии)")
    print("="*60)
    check = check_license("P_0000000001", "living_book")
    print(f"living_book для P_0000000001: {check}")

    print("\n" + "="*60)
    print("ТЕСТ 4: Покупка лицензии на living_book")
    print("="*60)
    result = buy_cartridge_license("P_0000000001", "living_book", 5000.0)
    print(f"\nРезультат: {result}")

    print("\n" + "="*60)
    print("ТЕСТ 5: Проверка лицензии после покупки")
    print("="*60)
    check = check_license("P_0000000001", "living_book")
    print(f"living_book для P_0000000001: {check}")

    print("\n" + "="*60)
    print("ТЕСТ 6: Повторная покупка (должна отклонить)")
    print("="*60)
    result = buy_cartridge_license("P_0000000001", "living_book", 5000.0)
    print(f"Результат: {result}")

    print("\n" + "="*60)
    print("ТЕСТ 7: Работа агента без лицензии (должна отклонить)")
    print("="*60)
    result = produce("advertising", "A01", 100.0, "Реклама без лицензии")
    print(f"Результат: {result['status']} — {result.get('msg', '')}")
