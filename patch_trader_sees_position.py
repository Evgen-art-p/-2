#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ─────────────────────────────────────────────────────────────
# ПАТЧ: КАМЕНЬ 1 — ТРЕЙДЕР ВИДИТ СВОЮ ОТКРЫТУЮ ПОЗИЦИЮ
# Маркер: TRADER_SEES_POSITION_V1
# Дата: 2026-06-20 · Брат (Claude) + Шеф
#
# ЗАКОН (Шеф): код кладёт ФАКТ на стол, решение — природа трейдера.
# Никаких приказов «держи / двигай стоп / выходи». Только факт:
# «у тебя открыта вот эта позиция, живёт столько баров, плавает столько R».
# Что с ней делать — его выводы, его воля. Это камень 1: трейдер
# впервые ВИДИТ, что он в рынке. Языка распоряжений (камень 2) тут нет.
#
# ЧТО ДЕЛАЕТ. В раскладку стола каждого из троих (table_for_brut/
# avan/cons) добавляет блок "position":
#   · нет открытой позиции этого трейдера → "position": null (как сейчас,
#     ищет вход — поведение НЕ меняется).
#   · есть → факт: direction, entry, stop, lot, bars_alive, current_price,
#     floating_r (плавающий результат ТОЙ ЖЕ формулой, что _settle посчитает
#     при закрытии — чтобы трейдер видел свой R той же мерой, не выдуманной).
#
# КАК НАХОДИТ СВОЮ. По магику (BRUT 100001 / AVAN 100002 / CONS 100003) —
# те же паспорта, что у Исполнителя. Берёт из trading_state["positions"]
# запись со status=OPEN и своим magic.
#
# ФОРМУЛА R — эталон из hooks._settle_positions (защита чисел):
#   LONG:  risk = entry - stop;  pnl_price = price - entry
#   SHORT: risk = stop - entry;  pnl_price = entry - price
#   floating_r = pnl_price / risk   (risk>0)
# price = текущий close (нереализованный R, «как если бы закрыл сейчас»).
#
# bars_alive — сколько баров позиция живёт. Считаем по opened_at vs
# текущий bar_time через индекс в истории, если доступен; иначе None
# (честно: не знаем — не врём).
#
# ТРИ КАСАНИЯ, симметрично (структура движков идентична):
#   brut_live.py · avan_live.py · cons_live.py
# Вставляем общий помощник _my_open_position() + блок position в раскладку.
#
# ИДЕМПОТЕНТНО: маркер, бэкап, py_compile. Запуск из корня репы:
#   python patch_trader_sees_position.py
# ─────────────────────────────────────────────────────────────

import sys
import shutil
import py_compile
from datetime import datetime
from pathlib import Path

MARKER = "TRADER_SEES_POSITION_V1"
ROOT = Path.cwd()
TRADING = ROOT / "studio" / "modules" / "trading"

FILES = {
    "brut": (TRADING / "brut_live.py", "table_for_brut", 100001),
    "avan": (TRADING / "avan_live.py", "table_for_avan", 100002),
    "cons": (TRADING / "cons_live.py", "table_for_cons", 100003),
}


def _fail(msg: str):
    print(f"❌ {msg}")
    sys.exit(1)


def _backup(path: Path):
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = path.with_name(f"{path.name}.bak_{stamp}")
    shutil.copy2(path, bak)
    print(f"   💾 бэкап: {bak.name}")


def _check_root():
    if not TRADING.exists():
        _fail(f"Не вижу {TRADING}. Запускай из КОРНЯ репы (где папка studio/).")
    for key, (p, _, _) in FILES.items():
        if not p.exists():
            _fail(f"Не найден файл: {p}")


# ── Общий помощник: вставляется в КАЖДЫЙ движок (свой magic) ──
# Кладётся перед def run_X. Считает живой факт открытой позиции трейдера.
HELPER_TEMPLATE = '''
# ════════════════════════════════════════════════════════════
# КАМЕНЬ 1: СВОЯ ОТКРЫТАЯ ПОЗИЦИЯ — ФАКТ на стол (не приказ)  # TRADER_SEES_POSITION_V1
# ─────────────────────────────────────────────────────────────
# Трейдер видит, что он в рынке: что открыто, сколько живёт, как
# плавает. Решение — его природа. R считаем ТОЙ ЖЕ формулой, что
# _settle_positions применит при закрытии (защита чисел).
# ════════════════════════════════════════════════════════════

_MY_MAGIC = __MAGIC__   # паспорт трейдера (как у Исполнителя)


def _my_open_position(md: dict) -> dict:
    """
    Факт открытой позиции ЭТОГО трейдера (по магику) из trading_state.
    Нет позиции → None. Есть → живой факт с плавающим R. Без суждений.
    """
    try:
        from studio.modules.trading.hooks import load_trading_state
        positions = load_trading_state().get("positions", []) or []
    except Exception:
        return None

    mine = None
    for p in positions:
        if p.get("magic") == _MY_MAGIC and p.get("status") == "OPEN":
            mine = p
            break
    if not mine:
        return None

    entry = mine.get("entry")
    stop  = mine.get("stop")
    direction = mine.get("direction", "LONG")
    price = (md.get("price", {}) or {}).get("close")

    # Плавающий R — эталон формулы из hooks._settle_positions.
    floating_r = None
    if entry is not None and stop is not None and price is not None:
        if direction == "LONG":
            risk = entry - stop
            pnl_price = price - entry
        else:  # SHORT
            risk = stop - entry
            pnl_price = entry - price
        if risk and risk > 0:
            floating_r = round(pnl_price / risk, 2)

    # bars_alive — сколько баров живёт (по дате открытия vs текущий бар).
    bars_alive = None
    opened_at = mine.get("opened_at")
    bar_time  = md.get("bar_time")
    if opened_at and bar_time and opened_at == bar_time:
        bars_alive = 0   # открыта на этом же баре

    return {
        "direction":     direction,
        "entry":         entry,
        "stop":          stop,
        "lot":           mine.get("lot"),
        "opened_at":     opened_at,
        "current_price": price,
        "floating_r":    floating_r,   # нереализованный R «закрой сейчас»
        "bars_alive":    bars_alive,
    }


'''


def patch_one(key: str) -> bool:
    path, table_var, magic = FILES[key]
    src = path.read_text(encoding="utf-8")
    if MARKER in src:
        print(f"✅ {path.name} уже пропатчен — пропускаю.")
        return False

    # 1) Вставить помощник перед def run_X
    run_anchor = f"def run_{key}("
    if run_anchor not in src:
        _fail(f"{path.name}: не нашёл '{run_anchor}' — структура изменилась.")
    helper = HELPER_TEMPLATE.replace("__MAGIC__", str(magic)).lstrip("\n")
    src = src.replace(run_anchor, helper + "\n" + run_anchor, 1)

    # 2) Врезать блок position в раскладку.
    #    Якорь — открытие словаря раскладки: '<table_var> = {\n        "anchor": {'
    anchor = f'{table_var} = {{\n        "anchor": {{'
    if anchor not in src:
        _fail(f"{path.name}: не нашёл начало раскладки '{table_var}' — структура изменилась.")
    insert = (
        f'{table_var} = {{\n'
        f'        # КАМЕНЬ 1: своя открытая позиция — ФАКТ (null если не в рынке).  # TRADER_SEES_POSITION_V1\n'
        f'        "position": _my_open_position(md),\n'
        f'        "anchor": {{'
    )
    src = src.replace(anchor, insert, 1)

    _backup(path)
    path.write_text(src, encoding="utf-8")
    print(f"✅ {path.name} пропатчен: _my_open_position + блок position.")
    return True


def _verify_compiles():
    for key, (p, _, _) in FILES.items():
        try:
            py_compile.compile(str(p), doraise=True)
        except py_compile.PyCompileError as e:
            _fail(f"После патча {p.name} НЕ компилируется:\n{e}")
    print("🧪 Песочница: все три движка компилируются.")


def main():
    print("═" * 60)
    print("  КАМЕНЬ 1: ТРЕЙДЕР ВИДИТ СВОЮ ПОЗИЦИЮ  ·", MARKER)
    print("═" * 60)
    _check_root()

    changed = False
    for key in ("brut", "avan", "cons"):
        changed |= patch_one(key)

    if changed:
        _verify_compiles()
        print("─" * 60)
        print("✅ ГОТОВО. Трое видят свою открытую позицию как факт.")
        print("   Нет позиции → position:null (ищет вход, как раньше).")
        print("   Есть → direction/entry/stop/lot/floating_r/bars_alive.")
        print("   Приказов нет. Что делать с позицией — камень 2 (язык).")
    else:
        print("─" * 60)
        print("ℹ️  Всё уже было пропатчено ранее — ничего не менял.")


if __name__ == "__main__":
    main()
