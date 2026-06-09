"""
patch_williams_core.py
======================
Спринт 43 · 2026-06-09

ЗАДАЧА:
  Разрезать hooks.py на два слоя:
    williams_core.py — вся математика Вильямса (не знает про Грондхейм)
    hooks.py         — чистый шлюз картриджа (не знает про Вильямса)

ЗАПУСК из корня проекта:
  python patch_williams_core.py

РЕЗУЛЬТАТ:
  studio/modules/trading/williams_core.py  — создан
  studio/modules/trading/hooks.py          — перезаписан (шлюз)
  studio/modules/trading/hooks.py.bak_*   — резервная копия оригинала
"""

import shutil
from datetime import datetime
from pathlib import Path

TRADING_DIR = Path("studio/modules/trading")
HOOKS_PATH  = TRADING_DIR / "hooks.py"
CORE_PATH   = TRADING_DIR / "williams_core.py"

# ── Резервная копия ───────────────────────────────────────
ts  = datetime.now().strftime("%Y%m%d_%H%M%S")
bak = HOOKS_PATH.with_suffix(f".py.bak_{ts}")
shutil.copy2(HOOKS_PATH, bak)
print(f"[PATCH] 💾 Резервная копия: {bak}")


# ════════════════════════════════════════════════════════════
# williams_core.py
# ════════════════════════════════════════════════════════════

WILLIAMS_CORE = '''# studio/modules/trading/williams_core.py
# ─────────────────────────────────────────────────────────────
# МАТЕМАТИКА ВИЛЬЯМСА — изолированное ядро
# Версия: 1.0 · Спринт 43 · 2026-06-09
#
# ЗАКОН: этот файл не знает про Грондхейм, агентов, cartridge.
# Принимает CSV или список баров → возвращает market_data.
# Любая другая торговая система пишет свой *_core.py рядом.
#
# Все формулы по исходникам MT5:
#   AO:       Awesome_Oscillator.mq5
#   AC:       Accelerator.mq5
#   Аллигатор: Alligator.mq5 (SMMA рекуррентно)
#   Фракталы: Fractals.mq5 (левые >=, правые >)
#   BWMFI:    MarketFacilitationIndex.mq5
# ─────────────────────────────────────────────────────────────

from pathlib import Path
from typing import Optional


# ════════════════════════════════════════════════════════════
# _Point по тикерам (стандарт MT5)
# ════════════════════════════════════════════════════════════

POINT_MAP = {
    "EURUSD": 0.00001,
    "GBPUSD": 0.00001,
    "USDJPY": 0.001,
    "AUDUSD": 0.00001,
    "USDCHF": 0.00001,
    "USDCAD": 0.00001,
    "XAUUSD": 0.01,
    "XAGUSD": 0.001,
    "SP500":  0.01,
    "US500":  0.01,
    "NAS100": 0.01,
    "AAPL":   0.001,
    "TSLA":   0.001,
    "MSFT":   0.001,
}


def get_point(symbol: str, override: float = None) -> float:
    """Возвращает _Point для символа. override имеет приоритет."""
    if override:
        return override
    return POINT_MAP.get(symbol.upper(), 0.00001)


# ════════════════════════════════════════════════════════════
# ЧТЕНИЕ CSV
# ════════════════════════════════════════════════════════════

def read_mt5_csv(filepath: str) -> list[dict]:
    """
    Читает CSV-файл экспорта MT5.
    Формат: date,open,high,low,close,tick_volume,spread
    Кодировка: utf-16-le (стандарт MT5).
    Возвращает список баров от старых к новым.
    """
    bars = []
    path = Path(filepath)
    if not path.exists():
        print(f"[CORE] ❌ CSV не найден: {filepath}")
        return []

    with open(path, encoding="utf-16-le") as f:
        for line in f:
            line = line.strip().lstrip("\\ufeff")
            if not line:
                continue
            parts = line.split(",")
            if len(parts) < 6:
                continue
            try:
                bars.append({
                    "date":   parts[0].strip(),
                    "open":   float(parts[1]),
                    "high":   float(parts[2]),
                    "low":    float(parts[3]),
                    "close":  float(parts[4]),
                    "volume": int(parts[5]),
                    "spread": float(parts[6]) if len(parts) > 6 else 0.0,
                })
            except (ValueError, IndexError):
                continue

    if bars:
        print(f"[CORE] 📂 {path.name}: {len(bars)} баров "
              f"({bars[0][\'date\']} → {bars[-1][\'date\']})")
    else:
        print(f"[CORE] ⚠️  {path.name}: пусто")
    return bars


# ════════════════════════════════════════════════════════════
# МАТЕМАТИКА
# ════════════════════════════════════════════════════════════

def _smma_series(medians: list[float], period: int) -> list[Optional[float]]:
    """
    Smoothed Moving Average — рекуррентная формула.
    smma[i] = (smma[i-1] * (period-1) + value[i]) / period
    Первое рабочее значение = SMA(period).
    SMMA ≠ EMA ≠ SMA.
    """
    result = [None] * len(medians)
    if len(medians) < period:
        return result
    result[period - 1] = sum(medians[:period]) / period
    for i in range(period, len(medians)):
        result[i] = (result[i - 1] * (period - 1) + medians[i]) / period
    return result


def compute_alligator(highs: list[float], lows: list[float]) -> dict:
    """
    Аллигатор Вильямса:
      Jaw(13)  — SMMA(13) медианы
      Teeth(8) — SMMA(8)  медианы
      Lips(5)  — SMMA(5)  медианы

    Смещения (+8/+5/+3) — для Pine Script / MT5 визуализации.
    Здесь используем текущие значения без смещения.

    bars_open — сколько баров подряд Аллигатор открыт.
    mature    — True если bars_open >= 8 (требует Консерватор).
    """
    medians = [(h + l) / 2 for h, l in zip(highs, lows)]

    jaw_s   = _smma_series(medians, 13)
    teeth_s = _smma_series(medians, 8)
    lips_s  = _smma_series(medians, 5)

    jaw   = jaw_s[-1]
    teeth = teeth_s[-1]
    lips  = lips_s[-1]

    if jaw is None or teeth is None or lips is None:
        return {
            "jaw": None, "teeth": None, "lips": None,
            "sleeping": True, "opening": False, "mature": False,
            "bars_open": 0,
        }

    # Считаем bars_open (сколько баров подряд открыт)
    bars_open = 0
    for i in range(len(jaw_s) - 1, -1, -1):
        j = jaw_s[i]; t = teeth_s[i]; l = lips_s[i]
        if j is None or t is None or l is None:
            break
        spread = max(abs(j - t), abs(t - l), abs(j - l))
        if spread < 0.0005:  # Forex-порог; для XAUUSD/SP500 пересчитать
            break
        bars_open += 1

    sleeping = bars_open == 0
    opening  = 0 < bars_open < 8
    mature   = bars_open >= 8

    return {
        "jaw":       round(jaw,   6),
        "teeth":     round(teeth, 6),
        "lips":      round(lips,  6),
        "sleeping":  sleeping,
        "opening":   opening,
        "mature":    mature,
        "bars_open": bars_open,
    }


def compute_ao_series(highs: list[float], lows: list[float]) -> list[Optional[float]]:
    """
    Awesome Oscillator:
      AO[i] = SMA(median, 5)[i] - SMA(median, 34)[i]
    """
    medians = [(h + l) / 2 for h, l in zip(highs, lows)]
    result  = [None] * len(medians)
    for i in range(33, len(medians)):
        sma5  = sum(medians[i-4:i+1])  / 5
        sma34 = sum(medians[i-33:i+1]) / 34
        result[i] = sma5 - sma34
    return result


def compute_ac_series(ao_series: list[Optional[float]]) -> list[Optional[float]]:
    """
    Accelerator Oscillator:
      AC[i] = AO[i] - SMA(AO, 5)[i]
    """
    result = [None] * len(ao_series)
    for i in range(len(ao_series)):
        window = ao_series[max(0, i-4):i+1]
        valid  = [v for v in window if v is not None]
        if len(valid) < 5:
            continue
        result[i] = ao_series[i] - sum(valid[-5:]) / 5
    return result


def detect_fractals(bars: list[dict], lookback: int = 2) -> dict:
    """
    Фракталы Вильямса — классические 5-барные (±2 от центра).
    По исходнику MT5 Fractals.mq5:
      правые бары: строгое > / <
      левые  бары: нестрогое >= / <=
    """
    n = len(bars)
    up_fractals   = []
    down_fractals = []

    for i in range(lookback, n - lookback):
        b = bars[i]

        if all(b["high"] >  bars[i + j]["high"] for j in range(1, lookback + 1)) and \\
           all(b["high"] >= bars[i - j]["high"] for j in range(1, lookback + 1)):
            up_fractals.append({
                "bar_index": i,
                "price":     round(b["high"], 6),
                "date":      b["date"],
            })

        if all(b["low"] <  bars[i + j]["low"] for j in range(1, lookback + 1)) and \\
           all(b["low"] <= bars[i - j]["low"] for j in range(1, lookback + 1)):
            down_fractals.append({
                "bar_index": i,
                "price":     round(b["low"], 6),
                "date":      b["date"],
            })

    return {
        "last_up":    up_fractals[-1]   if up_fractals   else None,
        "last_down":  down_fractals[-1] if down_fractals else None,
        "all_up":     up_fractals,
        "all_down":   down_fractals,
        "count_up":   len(up_fractals),
        "count_down": len(down_fractals),
    }


def compute_mfi(bar: dict, prev_bar: dict, point: float = None) -> dict:
    """
    Bill Williams Market Facilitation Index (BWMFI).
    По исходнику MT5 MarketFacilitationIndex.mq5.

    MFI = (high - low) / _Point / volume

    Типы (порядок как в MT5):
      GREEN  — MFI↑ vol↑  — настоящее движение
      FADE   — MFI↓ vol↓  — рынок остывает
      FAKE   — MFI↑ vol↓  — движение без объёма
      SQUAT  — MFI↓ vol↑  — рынок борется, скоро взрыв
    """
    def _calc(b, pt):
        if b["volume"] == 0:
            return 0.0
        v = (b["high"] - b["low"]) / b["volume"]
        return v / pt if pt else v

    mfi_cur  = _calc(bar,      point)
    mfi_prev = _calc(prev_bar, point)

    mfi_up = mfi_cur  > mfi_prev
    vol_up = bar["volume"] > prev_bar["volume"]

    if   mfi_up     and vol_up:     mtype = "GREEN"
    elif not mfi_up and not vol_up: mtype = "FADE"
    elif mfi_up     and not vol_up: mtype = "FAKE"
    else:                           mtype = "SQUAT"

    return {
        "type":     mtype,
        "volume":   bar["volume"],
        "spread":   bar["spread"],
        "mfi":      round(mfi_cur,  10),
        "mfi_prev": round(mfi_prev, 10),
    }


def detect_ao_divergence(bars: list[dict], ao_series: list[Optional[float]]) -> dict:
    """
    Дивергенция AO:
      БЫЧЬЯ  — цена ↓ новый минимум, AO↑ минимум выше (оба ниже нуля)
               → Точка Ноль (DETECTED для Искры)
      МЕДВЕЖЬЯ — цена↑ новый максимум, AO↓ максимум ниже (оба выше нуля)
               → exit_bell (конец импульса)
    """
    lookback    = min(50, len(bars) - 1)
    window_bars = bars[-lookback:]
    window_ao   = ao_series[-lookback:]

    lows_price  = []; lows_ao   = []
    highs_price = []; highs_ao  = []

    for i in range(2, len(window_bars) - 2):
        b  = window_bars[i]
        ao = window_ao[i]
        if ao is None:
            continue
        if b["low"]  < window_bars[i-1]["low"]  and b["low"]  < window_bars[i+1]["low"]:
            lows_price.append(b["low"]);  lows_ao.append(ao)
        if b["high"] > window_bars[i-1]["high"] and b["high"] > window_bars[i+1]["high"]:
            highs_price.append(b["high"]); highs_ao.append(ao)

    bullish = False
    if len(lows_price) >= 2:
        p1, p2 = lows_price[-2], lows_price[-1]
        a1, a2 = lows_ao[-2],    lows_ao[-1]
        if p2 < p1 and a2 > a1 and a1 < 0 and a2 < 0:
            bullish = True

    bearish = False
    if len(highs_price) >= 2:
        p1, p2 = highs_price[-2], highs_price[-1]
        a1, a2 = highs_ao[-2],    highs_ao[-1]
        if p2 > p1 and a2 < a1 and a1 > 0 and a2 > 0:
            bearish = True

    return {"bullish": bullish, "bearish": bearish}


def fractal_outside_jaw(fractal_price: float, jaw: float,
                        direction: str) -> bool:
    """
    Фрактал ВНЕ пасти (вне Jaw Аллигатора).
    LONG:  фрактал вверх выше Jaw
    SHORT: фрактал вниз ниже Jaw
    """
    if direction == "LONG":
        return fractal_price > jaw
    elif direction == "SHORT":
        return fractal_price < jaw
    return False


# ════════════════════════════════════════════════════════════
# ГЛАВНАЯ ФУНКЦИЯ — СБОРКА market_data
# ════════════════════════════════════════════════════════════

def build_market_data(
    bars:      list[dict],
    symbol:    str   = "UNKNOWN",
    timeframe: str   = "D1",
    point:     float = None,
) -> dict:
    """
    Из сырых баров собирает market_data для всего Совета.
    Структура согласно CHAIN_CONTRACT.md.

    point — минимальный шаг цены (_Point в MT5).
    Если не передан — берётся из POINT_MAP по символу.
    """
    if len(bars) < 40:
        print(f"[CORE] ❌ Недостаточно баров: {len(bars)} (нужно ≥ 40)")
        return {}

    highs = [b["high"]  for b in bars]
    lows  = [b["low"]   for b in bars]

    alligator  = compute_alligator(highs, lows)
    ao_series  = compute_ao_series(highs, lows)
    ac_series  = compute_ac_series(ao_series)
    fractals   = detect_fractals(bars)
    _point     = get_point(symbol, point)
    mfi        = compute_mfi(bars[-1], bars[-2], point=_point)
    divergence = detect_ao_divergence(bars, ao_series)

    print(f"[CORE]    _Point={_point} ({symbol})")

    # Текущие и предыдущие AO / AC
    ao_cur  = ao_series[-1]
    ao_prev = next((v for v in reversed(ao_series[:-1]) if v is not None), None)
    ac_cur  = ac_series[-1]
    ac_prev = next((v for v in reversed(ac_series[:-1]) if v is not None), None)

    # Пересечение нуля AO
    ao_crossed_zero = False
    ao_zero_dir     = None
    if ao_cur is not None and ao_prev is not None:
        if ao_prev < 0 < ao_cur:
            ao_crossed_zero = True; ao_zero_dir = "UP"
        elif ao_prev > 0 > ao_cur:
            ao_crossed_zero = True; ao_zero_dir = "DOWN"

    ao_direction = None
    if ao_cur is not None and ao_prev is not None:
        ao_direction = "UP" if ao_cur > ao_prev else "DOWN"

    ac_direction = None
    if ac_cur is not None and ac_prev is not None:
        ac_direction = "UP" if ac_cur > ac_prev else "DOWN"

    last_bar = bars[-1]

    return {
        "symbol":     symbol,
        "timeframe":  timeframe,
        "bar_time":   last_bar["date"],
        "bars_total": len(bars),

        "alligator": {
            "jaw":       alligator["jaw"],
            "teeth":     alligator["teeth"],
            "lips":      alligator["lips"],
            "sleeping":  alligator["sleeping"],
            "opening":   alligator["opening"],
            "mature":    alligator["mature"],
            "bars_open": alligator["bars_open"],
        },

        "ao": {
            "value":        round(ao_cur,  8) if ao_cur  is not None else None,
            "prev_value":   round(ao_prev, 8) if ao_prev is not None else None,
            "crossed_zero": ao_crossed_zero,
            "zero_dir":     ao_zero_dir,
            "direction":    ao_direction,
        },

        "ac": {
            "value":      round(ac_cur,  8) if ac_cur  is not None else None,
            "prev_value": round(ac_prev, 8) if ac_prev is not None else None,
            "direction":  ac_direction,
        },

        "mfi": {
            "type":   mfi["type"],
            "volume": mfi["volume"],
            "spread": mfi["spread"],
        },

        "price": {
            "open":  round(last_bar["open"],  6),
            "high":  round(last_bar["high"],  6),
            "low":   round(last_bar["low"],   6),
            "close": round(last_bar["close"], 6),
        },

        "divergence_ao": divergence["bullish"],  # Точка Ноль
        "exit_bell":     divergence["bearish"],  # Конец импульса

        "fractals": {
            "last_up":    fractals["last_up"],
            "last_down":  fractals["last_down"],
            "count_up":   fractals["count_up"],
            "count_down": fractals["count_down"],
        },
    }


# ════════════════════════════════════════════════════════════
# CLI — быстрая проверка на CSV
# ════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys, json

    if len(sys.argv) < 2:
        print("Использование: python williams_core.py <path_to_csv> [SYMBOL] [TIMEFRAME]")
        print("Пример: python williams_core.py data/EURUSDDaily.csv EURUSD D1")
        sys.exit(0)

    csv_path  = sys.argv[1]
    symbol    = sys.argv[2] if len(sys.argv) > 2 else "UNKNOWN"
    timeframe = sys.argv[3] if len(sys.argv) > 3 else "D1"

    bars = read_mt5_csv(csv_path)
    if bars:
        md = build_market_data(bars, symbol=symbol, timeframe=timeframe)
        if md:
            print("\\n=== JSON market_data ===")
            print(json.dumps(md, ensure_ascii=False, indent=2))
'''


# ════════════════════════════════════════════════════════════
# hooks.py — чистый шлюз
# ════════════════════════════════════════════════════════════

HOOKS_NEW = '''# studio/modules/trading/hooks.py
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

    print(f"\\n[TRADING] ⚔️  Военный Совет запускается")
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
    state.setdefault("chain_data", {})["history_dna"] = \\
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
        f.write(json.dumps(record, ensure_ascii=False) + "\\n")
    print(f"[ATLAS] 📝 Записано: {entry.get(\'event\', \'?\')}")


def _print_market_summary(md: dict):
    """Печатает краткую сводку market_data в консоль."""
    print(f"\\n[TRADING] 📊 РЫНОЧНАЯ СВОДКА {md[\'symbol\']} {md[\'timeframe\']}")
    print(f"  Бар:      {md[\'bar_time\']}")
    p = md["price"]
    print(f"  Цена:     O={p[\'open\']} H={p[\'high\']} L={p[\'low\']} C={p[\'close\']}")
    al = md["alligator"]
    state_str = ("СПИТ" if al["sleeping"] else
                 "MATURE" if al["mature"] else f"открыт {al[\'bars_open\']} баров")
    print(f"  Аллигатор: Jaw={al[\'jaw\']} Teeth={al[\'teeth\']} "
          f"Lips={al[\'lips\']} [{state_str}]")
    ao = md["ao"]
    print(f"  AO:       {ao[\'value\']} (prev={ao[\'prev_value\']}) "
          f"dir={ao[\'direction\']} zero={ao[\'crossed_zero\']}")
    ac = md["ac"]
    print(f"  AC:       {ac[\'value\']} dir={ac[\'direction\']}")
    print(f"  MFI:      {md[\'mfi\'][\'type\']} vol={md[\'mfi\'][\'volume\']}")
    print(f"  Фракталы: ▲{md[\'fractals\'][\'count_up\']} ▼{md[\'fractals\'][\'count_down\']}")
    if md["divergence_ao"]: print("  ⚡ ДИВЕРГЕНЦИЯ AO (бычья) — Точка Ноль!")
    if md["exit_bell"]:     print("  🔔 EXIT BELL — импульс выдохся")
    print()
'''


# ── Запись файлов ─────────────────────────────────────────

# williams_core.py
CORE_PATH.write_text(WILLIAMS_CORE, encoding="utf-8")
print(f"[PATCH] ✅ Создан: {CORE_PATH}")

# hooks.py
HOOKS_PATH.write_text(HOOKS_NEW, encoding="utf-8")
print(f"[PATCH] ✅ Перезаписан: {HOOKS_PATH}")

print("\n[PATCH] 🏁 Готово.")
print("  Проверь импорт: cd <корень проекта> && python -c \"from studio.modules.trading.williams_core import build_market_data; print('OK')\"")
print("  Затем: python studio/modules/trading/williams_core.py <path_to_csv> EURUSD D1")
