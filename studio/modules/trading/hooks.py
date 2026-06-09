# studio/modules/trading/hooks.py
# Торговый Цех — хуки и расчёт индикаторов
# Версия: 1.0 · Спринт 43 · 2026-06-09
#
# Источник данных: CSV из MT5 (ШАГ 1)
# Следующий этап: Pine Script webhook или MT5 polling (после бэктеста)
#
# Формат CSV (MT5 экспорт, utf-16-le):
#   date, open, high, low, close, tick_volume, spread
#
# Все индикаторы — точная математика Вильямса из WILLIAMS_MATH.md.
# SMMA: рекуррентная формула с прогревом (≠ SMA).
# Фракталы: классические 5-барные (±2 от центра).
# Смещения Аллигатора: jaw+8, teeth+5, lips+3 (в будущем — для Pine Script).

import json
import os
from pathlib import Path
from datetime import datetime
from typing import Optional

# ── Путь к Атласу Ошибок ──────────────────────────────────
ATLAS_PATH = Path("economy/data/atlas_trading.jsonl")


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
        print(f"[TRADING] ❌ CSV не найден: {filepath}")
        return []

    with open(path, encoding="utf-16-le") as f:
        for line in f:
            line = line.strip().lstrip("\ufeff")
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

    print(f"[TRADING] 📂 {path.name}: {len(bars)} баров "
          f"({bars[0]['date']} → {bars[-1]['date']})" if bars else "пусто")
    return bars


# ════════════════════════════════════════════════════════════
# МАТЕМАТИКА ВИЛЬЯМСА
# ════════════════════════════════════════════════════════════

def _smma_series(medians: list[float], period: int) -> list[Optional[float]]:
    """
    Smoothed Moving Average — рекуррентная формула.

    smma[i] = (smma[i-1] * (period - 1) + value[i]) / period
    Прогрев: первые (period - 1) значений = None,
             первое рабочее значение = SMA(period).

    ВАЖНО: SMMA ≠ EMA ≠ SMA. Это именно SMMA Вильямса.
    """
    result = [None] * len(medians)
    if len(medians) < period:
        return result

    # Первое значение = SMA
    first = sum(medians[:period]) / period
    result[period - 1] = first

    for i in range(period, len(medians)):
        result[i] = (result[i - 1] * (period - 1) + medians[i]) / period

    return result


def compute_alligator(highs: list[float], lows: list[float]) -> dict:
    """
    Аллигатор Вильямса:
      Jaw(13)   — челюсть, SMMA(13) медианы, смещение +8
      Teeth(8)  — зубы,   SMMA(8)  медианы, смещение +5
      Lips(5)   — губы,   SMMA(5)  медианы, смещение +3

    Смещения (future bars) для Pine Script / MT5 визуализации.
    Для принятия решений здесь используем ТЕКУЩИЕ значения без смещения.

    Аллигатор СПИТ если jaw ≈ teeth ≈ lips (разница < threshold).
    Threshold зависит от актива — передаётся снаружи или по дефолту.
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

    # Считаем сколько баров Аллигатор открыт подряд
    bars_open = 0
    for i in range(len(jaw_s) - 1, -1, -1):
        j = jaw_s[i]
        t = teeth_s[i]
        l = lips_s[i]
        if j is None or t is None or l is None:
            break
        spread = max(abs(j - t), abs(t - l), abs(j - l))
        # Порог "спит" = 10% от средней разницы — грубо
        # Более точно: Шеф задаёт threshold при запуске
        if spread < 0.0005:  # для Forex; для XAUUSD пересчитать
            break
        bars_open += 1

    sleeping = bars_open == 0
    opening  = 0 < bars_open < 8
    mature   = bars_open >= 8  # Консерватор требует MATURE

    return {
        "jaw":       round(jaw, 6),
        "teeth":     round(teeth, 6),
        "lips":      round(lips, 6),
        "sleeping":  sleeping,
        "opening":   opening,
        "mature":    mature,
        "bars_open": bars_open,
    }


def compute_ao_series(highs: list[float], lows: list[float]) -> list[Optional[float]]:
    """
    Awesome Oscillator:
      AO[i] = SMA(median, 5)[i] - SMA(median, 34)[i]
    Возвращает серию значений (len = len(highs)).
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
        # Нужны 5 валидных AO значений подряд
        window = ao_series[max(0, i-4):i+1]
        valid  = [v for v in window if v is not None]
        if len(valid) < 5:
            continue
        sma5_ao = sum(valid[-5:]) / 5
        result[i] = ao_series[i] - sma5_ao

    return result


def detect_fractals(bars: list[dict], lookback: int = 2) -> dict:
    """
    Фракталы Вильямса — классические 5-барные (±2 от центра).

    Фрактал вверх: bars[i].high > всех 2 баров до и 2 после.
    Фрактал вниз:  bars[i].low  < всех 2 баров до и 2 после.

    Возвращает последние confirmed фракталы (подтверждены 2 барами справа).
    Текущий и предыдущий бар — ещё не подтверждены.
    """
    n = len(bars)
    up_fractals   = []
    down_fractals = []

    for i in range(lookback, n - lookback):
        b = bars[i]

        # Фрактал вверх — точно по исходнику MT5 Fractals.mq5:
        # правые бары (будущие): строгое >
        # левые  бары (прошлые): нестрогое >=
        if all(b["high"] >  bars[i + j]["high"] for j in range(1, lookback + 1)) and \
           all(b["high"] >= bars[i - j]["high"] for j in range(1, lookback + 1)):
            up_fractals.append({
                "bar_index": i,
                "price":     round(b["high"], 6),
                "date":      b["date"],
            })

        # Фрактал вниз — та же логика:
        # правые бары: строгое <
        # левые  бары: нестрогое <=
        if all(b["low"] <  bars[i + j]["low"] for j in range(1, lookback + 1)) and \
           all(b["low"] <= bars[i - j]["low"] for j in range(1, lookback + 1)):
            down_fractals.append({
                "bar_index": i,
                "price":     round(b["low"], 6),
                "date":      b["date"],
            })

    last_up   = up_fractals[-1]   if up_fractals   else None
    last_down = down_fractals[-1] if down_fractals  else None

    return {
        "last_up":         last_up,
        "last_down":       last_down,
        "all_up":          up_fractals,
        "all_down":        down_fractals,
        "count_up":        len(up_fractals),
        "count_down":      len(down_fractals),
    }


def compute_mfi(bar: dict, prev_bar: dict, point: float = None) -> dict:
    """
    Bill Williams Market Facilitation Index.
    Точная реализация по исходнику MT5 MarketFacilitationIndex.mq5 (BWMFI).

    Формула: MFI = (high - low) / _Point / volume
    _Point — минимальный шаг цены актива.
    На тип (SQUAT/GREEN/FADE/FAKE) не влияет (сокращается при сравнении),
    но для абсолютного значения важен.

    Если point не передан — используем (high-low)/volume (упрощённо).
    Для точного совпадения с MT5 передавать point:
      EURUSD:  0.00001
      XAUUSD:  0.01
      SP500:   0.01
      AAPL:    0.001

    Типы (цвета в MT5 — порядок важен):
      GREEN  — MFI up  vol up    настоящее движение
      FADE   — MFI dn  vol dn    рынок остывает
      FAKE   — MFI up  vol dn    движение без объёма
      SQUAT  — MFI dn  vol up    рынок борется, скоро взрыв

    При volume=0 берём предыдущее MFI значение (как в MT5).
    """
    # volume=0 — берём предыдущее MFI (поведение MT5)
    if bar["volume"] == 0:
        mfi_cur = (prev_bar["high"] - prev_bar["low"]) / max(prev_bar["volume"], 1)
        if point:
            mfi_cur /= point
    else:
        mfi_cur = (bar["high"] - bar["low"]) / bar["volume"]
        if point:
            mfi_cur /= point

    if prev_bar["volume"] == 0:
        mfi_prev = 0.0
    else:
        mfi_prev = (prev_bar["high"] - prev_bar["low"]) / prev_bar["volume"]
        if point:
            mfi_prev /= point

    mfi_up = mfi_cur > mfi_prev
    vol_up = bar["volume"] > prev_bar["volume"]

    # Порядок как в исходнике MT5
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
    Дивергенция AO (Вильямс):

    БЫЧЬЯ  (Точка Ноль): цена делает новый минимум,
                         AO делает минимум ВЫШЕ предыдущего
                         И оба минимума ниже нуля.
                         → сигнал разворота вверх (DETECTED для Искры)

    МЕДВЕЖЬЯ (exit_bell): цена делает новый максимум,
                          AO делает максимум НИЖЕ предыдущего
                          И оба максимума выше нуля.
                          → сигнал конца импульса (ВЫХОД)

    Ищем на последних 50 барах.
    """
    lookback = min(50, len(bars) - 1)
    window_bars = bars[-lookback:]
    window_ao   = ao_series[-lookback:]

    bullish  = False
    bearish  = False

    # Ищем два локальных минимума по цене и AO
    lows_price = []
    lows_ao    = []
    highs_price = []
    highs_ao    = []

    for i in range(2, len(window_bars) - 2):
        b   = window_bars[i]
        ao  = window_ao[i]
        if ao is None:
            continue

        # Локальный минимум
        if (b["low"] < window_bars[i-1]["low"] and
            b["low"] < window_bars[i+1]["low"]):
            lows_price.append(b["low"])
            lows_ao.append(ao)

        # Локальный максимум
        if (b["high"] > window_bars[i-1]["high"] and
            b["high"] > window_bars[i+1]["high"]):
            highs_price.append(b["high"])
            highs_ao.append(ao)

    # Бычья дивергенция: последние два минимума
    if len(lows_price) >= 2 and len(lows_ao) >= 2:
        p1, p2 = lows_price[-2], lows_price[-1]
        a1, a2 = lows_ao[-2],    lows_ao[-1]
        if p2 < p1 and a2 > a1 and a1 < 0 and a2 < 0:
            bullish = True

    # Медвежья дивергенция: последние два максимума
    if len(highs_price) >= 2 and len(highs_ao) >= 2:
        p1, p2 = highs_price[-2], highs_price[-1]
        a1, a2 = highs_ao[-2],   highs_ao[-1]
        if p2 > p1 and a2 < a1 and a1 > 0 and a2 > 0:
            bearish = True

    return {
        "bullish":  bullish,   # Точка Ноль — DETECTED
        "bearish":  bearish,   # exit_bell — ВЫХОД
    }


# ════════════════════════════════════════════════════════════
# GATE ДЛЯ ГАНСА
# ════════════════════════════════════════════════════════════

def gate_hans(chain_data: dict) -> bool:
    """
    GATE 1 — A04 Ганс запускается только если:
      t1_status == "CONFIRMED"
      wave_1_validated == true

    Возвращает True если Ганс проходит.
    """
    t1     = chain_data.get("t1_status", "NOT_FOUND")
    wave1  = chain_data.get("wave_1_validated", False)
    result = (t1 == "CONFIRMED" and wave1 is True)
    if not result:
        print(f"[GATE] 🚫 Ганс заблокирован: t1={t1}, wave_1={wave1}")
    else:
        print(f"[GATE] ✅ Ганс проходит: t1={t1}, wave_1={wave1}")
    return result


def fractal_outside_jaw(fractal_price: float, jaw: float,
                         direction: str) -> bool:
    """
    Фрактал ВНЕ пасти (вне Jaw Аллигатора):
      Для входа LONG:  фрактал вверх выше Jaw
      Для входа SHORT: фрактал вниз ниже Jaw
    """
    if direction == "LONG":
        return fractal_price > jaw
    elif direction == "SHORT":
        return fractal_price < jaw
    return False


# ════════════════════════════════════════════════════════════
# СБОРКА market_data
# ════════════════════════════════════════════════════════════

# Справочник _Point по тикерам (стандарт MT5)
# Можно переопределить через settings["point"]
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


def build_market_data(
    bars:      list[dict],
    symbol:    str = "UNKNOWN",
    timeframe: str = "D1",
    point:     float = None,
) -> dict:
    """
    Главная функция hooks.py.
    Из сырых баров собирает market_data для Искры и всего Совета.

    point — минимальный шаг цены (_Point в MT5).
    Если не передан — берётся из POINT_MAP по символу.
    Для точного MFI всегда передавай point или задавай symbol.

    Возвращает структуру согласно CHAIN_CONTRACT.md:
    {
        symbol, timeframe, bar_time,
        alligator: {jaw, teeth, lips, sleeping, mature, bars_open},
        ao: {value, prev_value, crossed_zero, direction},
        ac: {value, prev_value, direction},
        mfi: {type, volume, spread},
        price: {open, high, low, close},
        divergence_ao: bool,
        exit_bell: bool,
        fractals: {last_up, last_down, count_up, count_down},
        bars_total: int,
    }
    """
    if len(bars) < 40:
        print(f"[TRADING] ❌ Недостаточно баров: {len(bars)} (нужно ≥ 40)")
        return {}

    highs  = [b["high"]  for b in bars]
    lows   = [b["low"]   for b in bars]
    closes = [b["close"] for b in bars]

    # Индикаторы
    alligator = compute_alligator(highs, lows)
    ao_series = compute_ao_series(highs, lows)
    ac_series = compute_ac_series(ao_series)
    fractals  = detect_fractals(bars)
    _point    = get_point(symbol, point)
    mfi       = compute_mfi(bars[-1], bars[-2], point=_point)
    print(f"[TRADING]    _Point={_point} ({symbol})")
    divergence = detect_ao_divergence(bars, ao_series)

    # Текущие и предыдущие значения AO/AC
    ao_cur  = ao_series[-1]
    ao_prev = next((v for v in reversed(ao_series[:-1]) if v is not None), None)
    ac_cur  = ac_series[-1]
    ac_prev = next((v for v in reversed(ac_series[:-1]) if v is not None), None)

    # Пересечение нуля AO (снизу вверх или сверху вниз)
    ao_crossed_zero = False
    ao_zero_dir     = None
    if ao_cur is not None and ao_prev is not None:
        if ao_prev < 0 < ao_cur:
            ao_crossed_zero = True
            ao_zero_dir     = "UP"
        elif ao_prev > 0 > ao_cur:
            ao_crossed_zero = True
            ao_zero_dir     = "DOWN"

    ao_direction = None
    if ao_cur is not None and ao_prev is not None:
        ao_direction = "UP" if ao_cur > ao_prev else "DOWN"

    ac_direction = None
    if ac_cur is not None and ac_prev is not None:
        ac_direction = "UP" if ac_cur > ac_prev else "DOWN"

    last_bar = bars[-1]

    market_data = {
        "symbol":    symbol,
        "timeframe": timeframe,
        "bar_time":  last_bar["date"],
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
            "type":    mfi["type"],
            "volume":  mfi["volume"],
            "spread":  mfi["spread"],
        },

        "price": {
            "open":  round(last_bar["open"],  6),
            "high":  round(last_bar["high"],  6),
            "low":   round(last_bar["low"],   6),
            "close": round(last_bar["close"], 6),
        },

        "divergence_ao": divergence["bullish"],   # Точка Ноль
        "exit_bell":     divergence["bearish"],   # Конец импульса

        "fractals": {
            "last_up":    fractals["last_up"],
            "last_down":  fractals["last_down"],
            "count_up":   fractals["count_up"],
            "count_down": fractals["count_down"],
        },
    }

    return market_data


# ════════════════════════════════════════════════════════════
# ХУКИ КАРТРИДЖА
# ════════════════════════════════════════════════════════════

def on_before_run(state: dict) -> dict:
    """
    Вызывается перед стартом цепочки.
    Читает CSV или market_data из state, считает индикаторы,
    кладёт market_data в state["chain_data"].

    Параметры из state["settings"]:
      csv_path:  путь к CSV файлу
      symbol:    тикер ("EURUSD", "XAUUSD", ...)
      timeframe: таймфрейм ("D1", "H4", "H1", ...)
      bars_limit: сколько последних баров брать (0 = все)
    """
    settings   = state.get("settings", {})
    csv_path   = settings.get("csv_path", "")
    symbol     = settings.get("symbol",     "UNKNOWN")
    timeframe  = settings.get("timeframe",  "D1")
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
        market_data = state.get("chain_data", {}).get("market_data")
        if market_data:
            print("[TRADING] 📡 market_data получен напрямую (webhook режим)")
            return state
        print("[TRADING] ⚠️  csv_path не задан и market_data отсутствует")
        return state

    if not bars:
        print("[TRADING] ❌ Нет данных — Совет не стартует")
        return state

    market_data = build_market_data(bars, symbol=symbol, timeframe=timeframe, point=point)

    if not market_data:
        print("[TRADING] ❌ build_market_data вернул пустой результат")
        return state

    # Кладём в chain_data — Искра и все агенты прочитают
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
            # Пропускаем Ганса — entry_trigger = false
            state.setdefault("chain_data", {})["entry_trigger"] = False
            state.setdefault("chain_data", {})["fractal_detected"] = False
            state.setdefault("chain_data", {})["fractal_outside_jaw"] = False
            state.setdefault("chain_data", {})["absorption_ratio"] = None
            # Сигнал пайплайну — пропустить агента
            state["_skip_agent"] = True
            print(f"[GATE] ⏭  A04 Ганс пропущен")
    return state


def on_after_agent(state: dict, agent_id: str, result: dict) -> dict:
    """
    Вызывается после каждого агента.
    Реализует GATE 2 — хард-стоп если все трое отказали.
    """
    if agent_id == "A09":
        results  = state.get("results", {})
        brut     = results.get("A06", {})
        avan     = results.get("A07", {})
        cons     = results.get("A08", {})

        brut_v = _extract_verdict(brut, "brut_verdict")
        avan_v = _extract_verdict(avan, "avan_verdict")
        cons_v = _extract_verdict(cons, "cons_verdict")

        all_rejected = all(v == "REJECTED" for v in [brut_v, avan_v, cons_v]
                           if v is not None)

        if all_rejected:
            print("[TRADING] 🛑 ХАРД-СТОП: все трое отказали")
            _write_atlas({
                "event":     "HARD_STOP",
                "reason":    "all_traders_rejected",
                "brut":      brut_v,
                "avan":      avan_v,
                "cons":      cons_v,
                "market":    state.get("chain_data", {}).get("market_data", {}),
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
    meta = agent_result.get("meta", {}) or {}
    my_out = meta.get("my_output", {}) or {}
    return my_out.get(key) or agent_result.get("text", "")[:10] or None


def _write_atlas(entry: dict):
    """Записывает событие в Атлас Ошибок."""
    ATLAS_PATH.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "ts":    datetime.now().isoformat(),
        "entry": entry,
    }
    with open(ATLAS_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(f"[ATLAS] 📝 Записано: {entry.get('event', '?')}")


def _print_market_summary(md: dict):
    """Печатает краткую сводку market_data в консоль."""
    print(f"\n[TRADING] 📊 РЫНОЧНАЯ СВОДКА {md['symbol']} {md['timeframe']}")
    print(f"  Бар:      {md['bar_time']}")
    print(f"  Цена:     O={md['price']['open']} H={md['price']['high']} "
          f"L={md['price']['low']} C={md['price']['close']}")

    al = md["alligator"]
    state_str = "СПИТ" if al["sleeping"] else (
        "MATURE" if al["mature"] else f"открыт {al['bars_open']} баров")
    print(f"  Аллигатор: Jaw={al['jaw']} Teeth={al['teeth']} Lips={al['lips']} [{state_str}]")

    ao = md["ao"]
    print(f"  AO:       {ao['value']} (prev={ao['prev_value']}) "
          f"dir={ao['direction']} zero_cross={ao['crossed_zero']}")

    ac = md["ac"]
    print(f"  AC:       {ac['value']} dir={ac['direction']}")
    print(f"  MFI:      {md['mfi']['type']} vol={md['mfi']['volume']}")
    print(f"  Фракталы: ▲{md['fractals']['count_up']} ▼{md['fractals']['count_down']}")

    if md["divergence_ao"]:
        print(f"  ⚡ ДИВЕРГЕНЦИЯ AO (бычья) — Точка Ноль обнаружена!")
    if md["exit_bell"]:
        print(f"  🔔 EXIT BELL — медвежья дивергенция, импульс выдохся")
    print()


# ════════════════════════════════════════════════════════════
# CLI — быстрая проверка на CSV
# ════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Использование: python hooks.py <path_to_csv> [SYMBOL] [TIMEFRAME]")
        print("Пример: python hooks.py data/EURUSDDaily.csv EURUSD D1")
        sys.exit(0)

    csv_path  = sys.argv[1]
    symbol    = sys.argv[2] if len(sys.argv) > 2 else "UNKNOWN"
    timeframe = sys.argv[3] if len(sys.argv) > 3 else "D1"

    bars = read_mt5_csv(csv_path)
    if bars:
        md = build_market_data(bars, symbol=symbol, timeframe=timeframe)
        if md:
            print("\n=== JSON market_data ===")
            print(json.dumps(md, ensure_ascii=False, indent=2))
