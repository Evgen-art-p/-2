# studio/modules/trading/hooks.py
# ─────────────────────────────────────────────────────────────
# ШЛЮЗ КАРТРИДЖА — Торговый Цех
# Версия: 2.0 · Спринт 43 · 2026-06-09
#
# ЗАКОН: этот файл не знает про математику Вильямса.
# Вся математика — в williams_core.py.
# Здесь только: gate-логика, хуки картриджа, запись в Атлас.
#
# Если в будущем появится order_flow_core.py —
# новый hooks.py будет импортировать оттуда. cartridge.py не заметит.
# ─────────────────────────────────────────────────────────────

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from .williams_core import build_market_data, read_mt5_csv

# ── Путь к Атласу Ошибок ──────────────────────────────────
ATLAS_PATH = Path("economy/data/atlas_trading.jsonl")


# ════════════════════════════════════════════════════════════
# GATE — логика цеха (знает про агентов, не знает про Вильямса)
# ════════════════════════════════════════════════════════════

def gate_hans(chain_data: dict) -> bool:
    """
    GATE 1 — A04 Ганс запускается только если:
      t1_status == "CONFIRMED"
      wave_1_validated == true

    Возвращает True если Ганс проходит.
    """
    t1    = chain_data.get("t1_status", "NOT_FOUND")
    wave1 = chain_data.get("wave_1_validated", False)
    result = (t1 == "CONFIRMED" and wave1 is True)
    if not result:
        print(f"[GATE] 🚫 Ганс заблокирован: t1={t1}, wave_1={wave1}")
    else:
        print(f"[GATE] ✅ Ганс проходит: t1={t1}, wave_1={wave1}")
    return result


# ════════════════════════════════════════════════════════════
# ХУКИ КАРТРИДЖА
# ════════════════════════════════════════════════════════════

def on_before_run(state: dict) -> dict:
    """
    Вызывается перед стартом цепочки.
    Идёт в williams_core → забирает market_data → кладёт в chain_data.

    Параметры из state["settings"]:
      csv_path:   путь к CSV файлу (ШАГ 1 — бэктест)
      symbol:     тикер ("EURUSD", "XAUUSD", ...)
      timeframe:  таймфрейм ("D1", "H4", "H1", ...)
      bars_limit: сколько последних баров брать (0 = все)
      point:      _Point override (опционально)
    """
    settings   = state.get("settings", {})
    csv_path   = settings.get("csv_path", "")
    symbol     = settings.get("symbol",    "UNKNOWN")
    timeframe  = settings.get("timeframe", "D1")
    bars_limit = int(settings.get("bars_limit", 0))
    point      = float(settings["point"]) if settings.get("point") else None

    print(f"\n[TRADING] ⚔️  Военный Совет запускается")
    print(f"[TRADING]    Символ: {symbol} | ТФ: {timeframe}")

    if csv_path:
        bars = read_mt5_csv(csv_path)
        if bars_limit > 0:
            bars = bars[-bars_limit:]
    else:
        # market_data уже передан напрямую (webhook / MT5 polling)
        if state.get("chain_data", {}).get("market_data"):
            print("[TRADING] 📡 market_data получен напрямую (webhook режим)")
            return state
        print("[TRADING] ⚠️  csv_path не задан и market_data отсутствует")
        return state

    if not bars:
        print("[TRADING] ❌ Нет данных — Совет не стартует")
        return state

    market_data = build_market_data(bars, symbol=symbol,
                                    timeframe=timeframe, point=point)
    if not market_data:
        print("[TRADING] ❌ williams_core вернул пустой результат")
        return state

    state.setdefault("chain_data", {})["market_data"] = market_data
    state.setdefault("chain_data", {})["history_dna"] = \
        state["chain_data"].get("history_dna", {})

    _print_market_summary(market_data)
    return state


def on_before_agent(state: dict, agent_id: str) -> dict:
    """
    Вызывается перед каждым агентом.
    Реализует GATE 1 — блокировку Ганса.
    """
    if agent_id == "A04":
        chain = state.get("chain_data", {})
        if not gate_hans(chain):
            state.setdefault("chain_data", {}).update({
                "entry_trigger":     False,
                "fractal_detected":  False,
                "fractal_outside_jaw": False,
                "absorption_ratio":  None,
            })
            state["_skip_agent"] = True
            print("[GATE] ⏭  A04 Ганс пропущен")
    return state


def on_after_agent(state: dict, agent_id: str, result: dict) -> dict:
    """
    Вызывается после каждого агента.
    Реализует GATE 2 — хард-стоп если все трое отказали.
    """
    if agent_id == "A09":
        results = state.get("results", {})
        brut_v  = _extract_verdict(results.get("A06", {}), "brut_verdict")
        avan_v  = _extract_verdict(results.get("A07", {}), "avan_verdict")
        cons_v  = _extract_verdict(results.get("A08", {}), "cons_verdict")

        all_rejected = all(
            v == "REJECTED" for v in [brut_v, avan_v, cons_v] if v is not None
        )

        if all_rejected:
            print("[TRADING] 🛑 ХАРД-СТОП: все трое отказали")
            _write_atlas({
                "event":  "HARD_STOP",
                "reason": "all_traders_rejected",
                "brut":   brut_v,
                "avan":   avan_v,
                "cons":   cons_v,
                "market": state.get("chain_data", {}).get("market_data", {}),
            })
            return {"action": "stop"}

    return {}


# ════════════════════════════════════════════════════════════
# УТИЛИТЫ
# ════════════════════════════════════════════════════════════

def _extract_verdict(agent_result: dict, key: str) -> Optional[str]:
    """Извлекает вердикт из результата агента."""
    if not agent_result:
        return None
    meta   = agent_result.get("meta", {}) or {}
    my_out = meta.get("my_output", {}) or {}
    return my_out.get(key) or agent_result.get("text", "")[:10] or None


def _write_atlas(entry: dict):
    """Записывает событие в Атлас Ошибок."""
    ATLAS_PATH.parent.mkdir(parents=True, exist_ok=True)
    record = {"ts": datetime.now().isoformat(), "entry": entry}
    with open(ATLAS_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(f"[ATLAS] 📝 Записано: {entry.get('event', '?')}")


def _print_market_summary(md: dict):
    """Печатает краткую сводку market_data в консоль."""
    print(f"\n[TRADING] 📊 РЫНОЧНАЯ СВОДКА {md['symbol']} {md['timeframe']}")
    print(f"  Бар:      {md['bar_time']}")
    p = md["price"]
    print(f"  Цена:     O={p['open']} H={p['high']} L={p['low']} C={p['close']}")
    al = md["alligator"]
    state_str = ("СПИТ" if al["sleeping"] else
                 "MATURE" if al["mature"] else f"открыт {al['bars_open']} баров")
    print(f"  Аллигатор: Jaw={al['jaw']} Teeth={al['teeth']} "
          f"Lips={al['lips']} [{state_str}]")
    ao = md["ao"]
    print(f"  AO:       {ao['value']} (prev={ao['prev_value']}) "
          f"dir={ao['direction']} zero={ao['crossed_zero']}")
    ac = md["ac"]
    print(f"  AC:       {ac['value']} dir={ac['direction']}")
    print(f"  MFI:      {md['mfi']['type']} vol={md['mfi']['volume']}")
    print(f"  Фракталы: ▲{md['fractals']['count_up']} ▼{md['fractals']['count_down']}")
    if md["divergence_ao"]: print("  ⚡ ДИВЕРГЕНЦИЯ AO (бычья) — Точка Ноль!")
    if md["exit_bell"]:     print("  🔔 EXIT BELL — импульс выдохся")
    print()
