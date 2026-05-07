"""
clearing_engine.py — Сердце экономики Грондхейма
Версия «ТРИ РЕЕСТРА» — агенты / партнёры / система раздельно
Обновлено: 5 мая 2026
"""

import json
from pathlib import Path
from typing import Optional, Dict, Any
import config

# ============================================================================
# ПУТИ К РЕЕСТРАМ
# ============================================================================

# Агенты (NFT-персонажи, ДНК, картриджи) — большой файл, трогаем редко
CATALOG_PATH  = Path(config.REGISTRY_PATH)                          # catalog.json

# Партнёры (люди, балансы, ранги, NFT) — основной рабочий файл
PARTNERS_PATH = CATALOG_PATH.parent / "partners.json"

# Системные объекты (TREASURY, GLOBAL_POOL) — отдельно, чтобы не мешались
SYSTEM_PATH   = CATALOG_PATH.parent / "system.json"

STUDIO_MODULES_PATH = Path(config.STUDIO_MODULES_PATH)

# Системные ID
TREASURY_ID    = "TREASURY"
GLOBAL_POOL_ID = "GLOBAL_POOL"

# Ранги и бонусы
RANK_BONUS = {
    "Искра":   0.0,
    "Пламя":   0.5,
    "Светило": 1.0,
    "Звезда":  1.5,
    "Маяк":    2.0,
    "Солнце":  3.0,
}
MAX_BONUS = 3.0

# Водопад: 30% от покупки по уровням
WATERFALL_LEVELS = [4, 4, 4, 4, 4, 2, 2, 2, 2, 2]

# NFT: льготный множитель топлива для ранга «Солнце»
NFT_FUEL_BONUS_RATE = 1.20   # +20%

# Лидерский Exit Bonus
LEADER_EXIT_BONUS_RATE = 0.50  # 50% от накопленной Гравитации

# ============================================================================
# ЧТЕНИЕ / ЗАПИСЬ РЕЕСТРОВ
# ============================================================================

def _load(path: Path) -> list:
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def _save(path: Path, data: list) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_catalog() -> list:
    return _load(CATALOG_PATH)

def save_catalog(catalog: list) -> None:
    _save(CATALOG_PATH, catalog)

def get_partners() -> list:
    return _load(PARTNERS_PATH)

def save_partners(partners: list) -> None:
    _save(PARTNERS_PATH, partners)

def get_system() -> list:
    return _load(SYSTEM_PATH)

def save_system(system: list) -> None:
    _save(SYSTEM_PATH, system)

# ============================================================================
# ПОИСК ОБЪЕКТОВ
# ============================================================================

def _find_in(data: list, object_id: str) -> Optional[dict]:
    for obj in data:
        if obj.get("ID_Object") == object_id:
            return obj
    return None

def get_partner_obj(partner_id: str) -> Optional[dict]:
    return _find_in(get_partners(), partner_id)

def get_system_obj(system_id: str) -> Optional[dict]:
    return _find_in(get_system(), system_id)

def get_agent_obj(workshop: str, role: str) -> Optional[dict]:
    for obj in get_catalog():
        if obj.get("Workshop_ID") == workshop and obj.get("Turbo_Role") == role:
            return obj
    return None

# ============================================================================
# БАЛАНСЫ GND
# ============================================================================

def get_balance_gnd(object_id: str) -> float:
    """Ищет баланс сначала в партнёрах, потом в системе."""
    obj = get_partner_obj(object_id) or get_system_obj(object_id)
    return float(obj.get("Balance_GND", 0) or 0) if obj else 0.0

def _add_gnd_partner(partner_id: str, amount: float) -> bool:
    partners = get_partners()
    for obj in partners:
        if obj.get("ID_Object") == partner_id:
            current = float(obj.get("Balance_GND", 0) or 0)
            obj["Balance_GND"] = round(current + amount, 4)
            obj["Backing_Status"] = "Обеспечено резервом"
            save_partners(partners)
            name = obj.get("Official_Name", partner_id)
            print(f"[NIKO] {name} {'+' if amount >= 0 else ''}{amount:.2f} GND → {obj['Balance_GND']:.2f}")
            return True
    return False

def _add_gnd_system(system_id: str, amount: float) -> bool:
    system = get_system()
    for obj in system:
        if obj.get("ID_Object") == system_id:
            current = float(obj.get("Balance_GND", 0) or 0)
            obj["Balance_GND"] = round(current + amount, 4)
            save_system(system)
            label = "[TREASURY]" if system_id == TREASURY_ID else "[GLOBAL_POOL]"
            icon  = "💰" if system_id == TREASURY_ID else "🌍"
            print(f"{label} {icon} {'+' if amount >= 0 else ''}{amount:.2f} GND → {obj['Balance_GND']:.2f}")
            return True
    return False

def add_gnd_to_catalog(object_id: str, amount: float) -> bool:
    """
    Универсальное начисление GND.
    Маршрутизирует в нужный реестр автоматически.
    """
    if abs(amount) < 0.0001:
        return True

    if object_id in [TREASURY_ID, GLOBAL_POOL_ID]:
        return _add_gnd_system(object_id, amount)

    if _add_gnd_partner(object_id, amount):
        return True

    # Агенты — GND запрещён
    for obj in get_catalog():
        if obj.get("ID_Object") == object_id:
            if not obj.get("allow_GND", False):
                print(f"[AXIOM] 🚨 Агент {object_id} не может получать GND (allow_GND=false)")
                return False

    print(f"[ERROR] Объект {object_id} не найден ни в одном реестре")
    return False

# ============================================================================
# ТОПЛИВО (💡 Световики)
# ============================================================================

def get_dna_path(workshop: str, role: str) -> Path:
    return STUDIO_MODULES_PATH / workshop / role / "dna.json"

def add_fuel_to_agent(workshop: str, role: str, amount: float) -> bool:
    dna_path = get_dna_path(workshop, role)
    if not dna_path.exists():
        print(f"[ERROR] dna.json не найден: {dna_path}")
        return False
    with open(dna_path, "r", encoding="utf-8") as f:
        dna = json.load(f)
    dna.setdefault("balance", {})
    dna["balance"]["Световики"] = round(dna["balance"].get("Световики", 0.0) + amount, 4)
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
        print(f"[AXIOM] 🚨 {workshop}/{role}: {balance:.2f} 💡 < {config.MEMORY_DEPOSIT_LIMIT} — АГЕНТ В АРХИВЕ")
        return False
    return True

# ============================================================================
# ИЕРАРХИЯ ПАРТНЁРОВ
# ============================================================================

def get_partner_by_agent(workshop: str, role: str) -> Optional[str]:
    """Возвращает Owner_ID агента из catalog.json"""
    obj = get_agent_obj(workshop, role)
    return obj.get("Owner_ID") if obj else None

def get_referrer(partner_id: str) -> Optional[str]:
    obj = get_partner_obj(partner_id)
    return obj.get("Referrer_ID") if obj else None

def get_ambassador_rank(partner_id: str) -> Optional[str]:
    obj = get_partner_obj(partner_id)
    return obj.get("Ambassador_Rank") if obj else None

def get_parents(partner_id: str, max_depth: int = 10) -> list:
    """Цепочка вышестоящих партнёров [{id, rank}, ...]"""
    partners  = get_partners()
    referrers = {o["ID_Object"]: o.get("Referrer_ID") for o in partners}
    ranks     = {o["ID_Object"]: o.get("Ambassador_Rank") for o in partners}

    chain, current = [], partner_id
    for _ in range(max_depth):
        parent = referrers.get(current)
        if not parent:
            break
        chain.append({"id": parent, "rank": ranks.get(parent)})
        current = parent
    return chain

def get_first_ambassador_up(partner_id: str) -> str:
    parents = get_parents(partner_id, max_depth=20)
    for p in parents:
        if p["rank"]:
            return p["id"]
    return "P_0000000000"

def transfer_gnd(sender_id: str, receiver_id: str, amount: float) -> bool:
    if amount <= 0:
        return False
    fee = config.TRANSFER_FEE
    if get_balance_gnd(sender_id) < amount + fee:
        print(f"[NIKO] Ошибка: у {sender_id} недостаточно GND")
        return False
    if add_gnd_to_catalog(sender_id, -(amount + fee)) and add_gnd_to_catalog(receiver_id, amount):
        add_gnd_to_catalog(TREASURY_ID, fee)
        print(f"[NIKO] {sender_id} → {receiver_id}: {amount} GND (комиссия {fee} GND)")
        return True
    return False

# ============================================================================
# NFT: РАНГ И ЛЬГОТЫ
# ============================================================================

def get_nft_rank_status(partner_id: str) -> Optional[str]:
    """
    Возвращает NFT-подтверждённый ранг из partners.json.
    Когда будет Web3 — заменить тело на вызов смарт-контракта.
    """
    obj = get_partner_obj(partner_id)
    if not obj:
        return None
    return obj.get("NFT_Rank_Status") or obj.get("Ambassador_Rank")

def mint_rank_nft(partner_id: str, rank: str) -> bool:
    """
    Минтинг NFT при повышении ранга. Сейчас — заглушка.

    Когда будет готов смарт-контракт:
        from web3 import Web3
        w3 = Web3(Web3.HTTPProvider(RPC_URL))
        contract = w3.eth.contract(address=CONTRACT_ADDRESS, abi=ABI)
        tx = contract.functions.mint(partner_wallet, rank_id).transact()
        → записать tx.hex() в NFT_Address
    """
    partners = get_partners()
    for obj in partners:
        if obj.get("ID_Object") == partner_id:
            old = obj.get("NFT_Rank_Status", "—")
            obj["NFT_Rank_Status"] = rank
            obj["NFT_Address"] = f"mock_nft_{partner_id}_{rank}"
            save_partners(partners)
            print(f"[NFT] 🏅 {partner_id}: {old} → {rank} (адрес: {obj['NFT_Address']})")
            return True
    print(f"[NFT] ❌ Партнёр {partner_id} не найден")
    return False

def update_ambassador_rank(partner_id: str, new_rank: str) -> bool:
    """
    Повышает ранг партнёра, минтит NFT, проверяет Exit Bonus.
    Вызывается вручную Архитектором или автоматически.
    """
    if new_rank not in RANK_BONUS:
        print(f"[ERROR] Неизвестный ранг: {new_rank}")
        return False

    partners = get_partners()
    for obj in partners:
        if obj.get("ID_Object") == partner_id:
            old_rank  = obj.get("Ambassador_Rank") or "Искра"
            new_bonus = RANK_BONUS[new_rank]
            old_bonus = RANK_BONUS.get(old_rank, 0.0)

            obj["Ambassador_Rank"] = new_rank
            save_partners(partners)
            print(f"[RANK] {partner_id}: {old_rank} → {new_rank}")

            if new_bonus > old_bonus:
                mint_rank_nft(partner_id, new_rank)

            if new_rank == "Солнце":
                _check_leader_exit_trigger(partner_id)

            return True

    print(f"[ERROR] Партнёр {partner_id} не найден")
    return False

def get_nft_fuel_multiplier(partner_id: str) -> float:
    """Солнце → x1.20, остальные → x1.0"""
    if get_nft_rank_status(partner_id) == "Солнце":
        print(f"[NFT] ☀️ {partner_id} — NFT «Солнце», льготный курс x{NFT_FUEL_BONUS_RATE}")
        return NFT_FUEL_BONUS_RATE
    return 1.0

# ============================================================================
# ЛИДЕРСКИЙ EXIT BONUS
# ============================================================================

def _get_gravity_pool(partner_id: str) -> float:
    obj = get_partner_obj(partner_id)
    return float(obj.get("Accumulated_Gravity_Pool", 0) or 0) if obj else 0.0

def _set_gravity_pool(partner_id: str, value: float) -> bool:
    partners = get_partners()
    for obj in partners:
        if obj.get("ID_Object") == partner_id:
            obj["Accumulated_Gravity_Pool"] = round(value, 4)
            save_partners(partners)
            return True
    return False

def accumulate_gravity_for_branch(partner_id: str, amount: float) -> None:
    """Накапливает Гравитацию в пуле партнёра для будущего Exit Bonus."""
    _set_gravity_pool(partner_id, _get_gravity_pool(partner_id) + amount)

def process_leader_exit_bonus(upline_id: str) -> Dict[str, Any]:
    """
    Разовый куш при отсечке.
    50% накопленной Гравитации → вышестоящему из казны.
    50% остаётся в казне.
    """
    pool = _get_gravity_pool(upline_id)
    if pool <= 0:
        print(f"[EXIT_BONUS] У {upline_id} нет накопленной Гравитации — пропускаем")
        return {"status": "skip", "reason": "pool_empty", "partner": upline_id}

    bonus         = round(pool * LEADER_EXIT_BONUS_RATE, 4)
    treasury_keep = round(pool - bonus, 4)

    treasury_bal = get_balance_gnd(TREASURY_ID)
    if treasury_bal < bonus:
        print(f"[EXIT_BONUS] ⚠️ Казна не покрывает бонус полностью")
        bonus         = treasury_bal
        treasury_keep = 0.0

    add_gnd_to_catalog(TREASURY_ID, -bonus)
    add_gnd_to_catalog(upline_id, bonus)
    _set_gravity_pool(upline_id, 0.0)

    name = (get_partner_obj(upline_id) or {}).get("Official_Name", upline_id)
    print(f"\n[EXIT_BONUS] ☀️☀️ РАЗОВЫЙ КУШ")
    print(f"[EXIT_BONUS] Получатель: {name} ({upline_id})")
    print(f"[EXIT_BONUS] Пул:        {pool:.2f} GND")
    print(f"[EXIT_BONUS] Выплачено:  {bonus:.2f} GND (50%)")
    print(f"[EXIT_BONUS] В казне:    {treasury_keep:.2f} GND (50%)")

    return {"status": "success", "upline_id": upline_id,
            "gravity_pool": pool, "bonus_paid": bonus, "treasury_kept": treasury_keep}

def _check_leader_exit_trigger(new_sun_id: str) -> None:
    """Ищет первого вышестоящего «Солнца» и выплачивает Exit Bonus."""
    for parent in get_parents(new_sun_id, max_depth=20):
        if parent["rank"] == "Солнце":
            print(f"\n[TRIGGER] 🌅 {new_sun_id} достиг «Солнца» → Exit Bonus для {parent['id']}")
            process_leader_exit_bonus(parent["id"])
            return
    print(f"[TRIGGER] Нет вышестоящего «Солнца» для {new_sun_id}")

# ============================================================================
# ДОЖДЬ
# ============================================================================

def distribute_waterfall(partner_id: str, purchase_amount_gnd: float) -> None:
    """Водопад: 30% от покупки по 10 уровням"""
    total = purchase_amount_gnd * 0.30
    if total <= 0:
        return

    chain = get_parents(partner_id, max_depth=10)
    distributed = 0.0

    for i, p in enumerate(chain[:10]):
        percent = WATERFALL_LEVELS[i]
        amount  = total * (percent / 30.0)
        add_gnd_to_catalog(p["id"], amount)
        distributed += amount
        print(f"[WATERFALL] Уровень {i+1} ({p['id']}): +{amount:.2f} GND ({percent}%)")

    remainder = total - distributed
    if remainder > 0.0001:
        add_gnd_to_catalog(TREASURY_ID, remainder)
        print(f"[WATERFALL] Остаток → казна: +{remainder:.2f} GND")

def distribute_gravity(partner_id: str, purchase_amount_gnd: float) -> None:
    """
    Гравитация: 24% от покупки по разнице рангов.
    Параллельно накапливает пул для Exit Bonus.
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
    last_bonus  = 0.0

    for p in chain:
        rank = p["rank"]
        if not rank or rank not in RANK_BONUS:
            continue
        current_bonus = RANK_BONUS[rank]
        if current_bonus > last_bonus:
            diff   = current_bonus - last_bonus
            amount = total * (diff / MAX_BONUS)
            add_gnd_to_catalog(p["id"], amount)
            accumulate_gravity_for_branch(p["id"], amount)
            distributed += amount
            print(f"[GRAVITY] {p['id']} ({rank}, +{diff}%): +{amount:.2f} GND")
            last_bonus = current_bonus

    remainder = total - distributed
    if remainder > 0.0001:
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
        print(f"[MATCHING] Нет наставника → казна: +{total:.2f} GND")
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
    source: "sale" — продажа лицензии | "fuel" — покупка топлива
    NFT-льгота применяется автоматически если владелец — «Солнце».
    """
    if amount_gnd <= 0:
        return {"status": "error", "msg": "amount_gnd должен быть положительным"}

    # ── SALE ──────────────────────────────────────────────────────────────────
    if source == "sale":
        if recipient_type == "agent":
            owner_id     = get_partner_by_agent(workshop, role)
            recipient_id = get_first_ambassador_up(owner_id) if owner_id else None
        else:
            recipient_id = get_first_ambassador_up(workshop)

        target = recipient_id or TREASURY_ID
        add_gnd_to_catalog(target, amount_gnd * 0.35)
        if not recipient_id:
            print(f"[SALE] Получатель не найден, 35% в казну")

        add_gnd_to_catalog(TREASURY_ID,    amount_gnd * 0.64)
        add_gnd_to_catalog(GLOBAL_POOL_ID, amount_gnd * 0.01)
        print(f"[SALE] 64% → казна: {amount_gnd * 0.64:.2f} GND")
        print(f"[SALE] 1%  → Global Pool: {amount_gnd * 0.01:.2f} GND")

        return {"status": "success", "type": "sale",
                "amount_gnd": amount_gnd, "recipient": recipient_id}

    # ── FUEL ──────────────────────────────────────────────────────────────────
    if source == "fuel":
        owner_id       = get_partner_by_agent(workshop, role)
        nft_multiplier = get_nft_fuel_multiplier(owner_id) if owner_id else 1.0
        fuel_received  = round(amount_gnd * config.GND_TO_FUEL_RATE * nft_multiplier, 4)

        print(f"\n[FUEL] ══════════ ПОКУПКА ТОПЛИВА ══════════")
        print(f"[FUEL] Агент:    {workshop}/{role}")
        print(f"[FUEL] Владелец: {owner_id or '(нет)'}")
        print(f"[FUEL] Сумма:    {amount_gnd} GND")
        print(f"[FUEL] Курс:     1 GND = {config.GND_TO_FUEL_RATE} 💡"
              + (f" × {nft_multiplier} (NFT)" if nft_multiplier > 1.0 else ""))
        print(f"[FUEL] Итого:    {fuel_received:.2f} 💡")

        add_fuel_to_agent(workshop, role, fuel_received)

        if owner_id:
            print(f"\n[RAIN] Дождь 64% = {amount_gnd * 0.64:.2f} GND:")
            distribute_waterfall(owner_id, amount_gnd)
            distribute_gravity(owner_id, amount_gnd)
            distribute_matching(owner_id, amount_gnd)

        add_gnd_to_catalog(TREASURY_ID,    amount_gnd * 0.35)
        add_gnd_to_catalog(GLOBAL_POOL_ID, amount_gnd * 0.01)
        print(f"\n[TREASURY]    35% → +{amount_gnd * 0.35:.2f} GND")
        print(f"[GLOBAL_POOL]  1% → +{amount_gnd * 0.01:.2f} GND")

        return {"status": "success", "type": "fuel",
                "amount_gnd": amount_gnd, "amount_fuel": fuel_received,
                "nft_multiplier": nft_multiplier, "owner": owner_id}

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
    print("ТЕСТ 1: Продажа лицензии (process_deliver)")
    print("="*60)
    print(process_deliver("living_book", "A16"))

    print("\n" + "="*60)
    print("ТЕСТ 2: Покупка топлива — стандартный партнёр")
    print("="*60)
    if check_memory_deposit("turbo", "A03"):
        print(refuel("turbo", "A03", 1000, "fuel", "agent"))
    else:
        print("❌ Агент не прошёл проверку Депозита Личности")

    print("\n" + "="*60)
    print("ТЕСТ 3: NFT-льгота — покупка топлива, владелец Солнце")
    print("="*60)
    result   = refuel("living_book", "A16", 1000, "fuel", "agent")
    expected = round(1000 * config.GND_TO_FUEL_RATE * NFT_FUEL_BONUS_RATE, 4)
    actual   = result.get("amount_fuel", 0)
    print(f"Ожидали: {expected} 💡 | Получили: {actual} 💡 | {'✅ OK' if abs(actual - expected) < 0.01 else '❌ ОШИБКА'}")

    print("\n" + "="*60)
    print("ТЕСТ 4: Повышение ранга + NFT-минтинг")
    print("="*60)
    ok  = update_ambassador_rank("P_0000000001", "Солнце")
    obj = get_partner_obj("P_0000000001")
    print(f"Ранг обновлён:   {ok}")
    print(f"NFT_Rank_Status: {obj.get('NFT_Rank_Status')}")
    print(f"NFT_Address:     {obj.get('NFT_Address')}")

    print("\n" + "="*60)
    print("ТЕСТ 5: Exit Bonus — Архитектор получает разовый куш")
    print("="*60)
    # Пополняем казну до нужного уровня (предыдущие тесты её потратили)
    needed = 24000.0 * LEADER_EXIT_BONUS_RATE
    current_treas = get_balance_gnd(TREASURY_ID)
    if current_treas < needed:
        _add_gnd_system(TREASURY_ID, needed - current_treas)
        print(f"[ТЕСТ] Казна пополнена до {get_balance_gnd(TREASURY_ID):.2f} GND для чистоты теста")
    _set_gravity_pool("P_0000000000", 24000.0)
    before_arch  = get_balance_gnd("P_0000000000")
    before_treas = get_balance_gnd(TREASURY_ID)

    result    = process_leader_exit_bonus("P_0000000000")
    bonus_got = get_balance_gnd("P_0000000000") - before_arch
    expected_b = 24000.0 * LEADER_EXIT_BONUS_RATE
    print(f"\nАрхитектор: +{bonus_got:.2f} GND | Ожидали: {expected_b:.2f} | {'✅ OK' if abs(bonus_got - expected_b) < 0.01 else '❌ ОШИБКА'}")
    print(f"Казна:  {before_treas:.2f} → {get_balance_gnd(TREASURY_ID):.2f} GND")
    print(f"Gravity Pool: {_get_gravity_pool('P_0000000000'):.2f} GND (должен быть 0)")

    print("\n" + "="*60)
    print("ТЕСТ 6: Итоговые балансы")
    print("="*60)
    print(f"TREASURY:    {get_balance_gnd(TREASURY_ID):.2f} GND")
    print(f"GLOBAL_POOL: {get_balance_gnd(GLOBAL_POOL_ID):.2f} GND")
    for pid in ["P_0000000000", "P_0000000001", "P_0000000002"]:
        obj = get_partner_obj(pid)
        if obj:
            print(f"{pid} ({obj['Official_Name']}): {get_balance_gnd(pid):.2f} GND")
