# studio/api_trading.py
"""
TRADING API v2
  POST /api/trading/scan   — математика williams_core, без LLM
                             принимает куски истории от MT5
                             возвращает: где были сигналы
  POST /api/trading/signal — полный Совет (LLM)
                             только для текущего бара
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
import json
from pathlib import Path

router = APIRouter(prefix="/api/trading", tags=["trading"])


# ── Общие модели ───────────────────────────────────────────
class MT5Bar(BaseModel):
    date:   str
    open:   float
    high:   float
    low:    float
    close:  float
    volume: int
    spread: float = 0.0

class MT5ScanRequest(BaseModel):
    symbol:    str
    timeframe: str
    bars:      list[MT5Bar]   # любой размер — куски по 500+


class BarSignal(BaseModel):
    date:        str
    bar_index:   int          # индекс в присланном массиве
    divergence:  bool         # бычья дивергенция (Точка Ноль)
    exit_bell:   bool         # медвежья (звонок выхода)
    squat:       bool         # приседающий бар
    alligator_sleeping: bool
    entry_price: Optional[float]   # цена входа если есть setup
    stop_price:  Optional[float]   # стоп


class MT5ScanResponse(BaseModel):
    symbol:    str
    timeframe: str
    bars_total: int
    signals:   list[BarSignal]   # только бары с сигналами
    error:     Optional[str]


class TraderSignal(BaseModel):
    verdict:   str
    reason:    str
    entry:     Optional[float]
    stop:      Optional[float]
    tp:        Optional[float]
    lot:       Optional[float]
    narrative: str

class MT5SignalRequest(BaseModel):
    symbol:    str
    timeframe: str
    bars:      list[MT5Bar]   # последние 150-200 баров для контекста

class MT5SignalResponse(BaseModel):
    symbol:      str
    timeframe:   str
    bar_time:    str
    t1_status:   str
    morj_status: str
    panic_phase: str
    divergence:  bool
    exit_bell:   bool
    alligator:   dict
    brut:        TraderSignal
    avan:        TraderSignal
    cons:        TraderSignal
    council_fired: bool
    error:       Optional[str]


# ══════════════════════════════════════════════════════════════
# SCAN — математика по истории, без LLM
# ══════════════════════════════════════════════════════════════

@router.post("/scan", response_model=MT5ScanResponse)
async def scan_history(req: MT5ScanRequest):
    """
    Принимает кусок истории (500+ баров).
    Считает williams_core на каждом баре.
    Возвращает только бары где есть сигнал.
    Никакого LLM — только математика.
    """
    try:
        from studio.modules.trading.williams_core import (
            build_market_data, get_point
        )

        bars = [b.dict() for b in req.bars]
        n    = len(bars)

        if n < 40:
            return MT5ScanResponse(
                symbol=req.symbol, timeframe=req.timeframe,
                bars_total=n, signals=[], error="мало баров (нужно >= 40)"
            )

        point   = get_point(req.symbol)
        signals = []

        # Скользящее окно: минимум 40 баров контекста
        # Обрабатываем каждый бар начиная с 40-го
        for i in range(40, n):
            window = bars[max(0, i - 199):i + 1]  # до 200 баров контекста
            md = build_market_data(
                window,
                symbol=req.symbol,
                timeframe=req.timeframe,
                point=point,
            )
            if not md:
                continue

            has_divergence = bool(md.get("divergence_ao"))
            has_exit_bell  = bool(md.get("exit_bell"))
            has_squat      = bool(md.get("squat", {}).get("last_squat"))
            al_sleeping    = bool(md.get("alligator", {}).get("sleeping"))

            # Пишем только бары с чем-то интересным
            if not (has_divergence or has_exit_bell or has_squat):
                continue

            # Цены входа (только если есть дивергенция и не спит)
            entry_price = None
            stop_price  = None
            if has_divergence and not al_sleeping:
                sq = md.get("squat", {}).get("last_squat")
                if sq:
                    entry_price = round(sq["high"] + point, 6)
                    # Стоп: лоу предыдущего бара
                    if i >= 1:
                        stop_price = round(bars[i - 1]["low"] - point, 6)

            signals.append(BarSignal(
                date=bars[i]["date"],
                bar_index=i,
                divergence=has_divergence,
                exit_bell=has_exit_bell,
                squat=has_squat,
                alligator_sleeping=al_sleeping,
                entry_price=entry_price,
                stop_price=stop_price,
            ))

        print(f"[SCAN] {req.symbol} {req.timeframe}: "
              f"{n} баров → {len(signals)} сигналов")

        return MT5ScanResponse(
            symbol=req.symbol,
            timeframe=req.timeframe,
            bars_total=n,
            signals=signals,
            error=None,
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        return MT5ScanResponse(
            symbol=req.symbol, timeframe=req.timeframe,
            bars_total=0, signals=[], error=str(e)
        )


# ══════════════════════════════════════════════════════════════
# SIGNAL — полный Совет для живого бара
# ══════════════════════════════════════════════════════════════

@router.post("/signal", response_model=MT5SignalResponse)
async def get_signal(req: MT5SignalRequest):
    """
    Живой бар: запускает полный Совет (LLM).
    Вызывается только на новом баре, не на каждом тике.
    """
    try:
        from studio.modules.trading.williams_core import build_market_data
        bars = [b.dict() for b in req.bars]
        md   = build_market_data(bars, symbol=req.symbol, timeframe=req.timeframe)
        if not md:
            return _error_response(req, "williams_core пуст")

        from studio.cartridge import run_cartridge
        state = {
            "settings":   {"symbol": req.symbol, "timeframe": req.timeframe},
            "chain_data": {"market_data": md},
        }
        result  = await run_cartridge("trading", state)
        cd      = result.get("chain_data", {})
        results = result.get("results", {})

        def _trader(aid, vk, rk, ek, sk, tk, lk):
            out = (results.get(aid, {}).get("meta", {}) or {}).get("my_output", {}) or {}
            return TraderSignal(
                verdict=out.get(vk, "REJECTED"),
                reason=out.get(rk, "NO_RESPONSE"),
                entry=out.get(ek), stop=out.get(sk),
                tp=out.get(tk),    lot=out.get(lk),
                narrative=out.get("narrative", ""),
            )

        return MT5SignalResponse(
            symbol=req.symbol, timeframe=req.timeframe,
            bar_time=md.get("bar_time", ""),
            t1_status=cd.get("t1_status",  "NOT_FOUND"),
            morj_status=cd.get("morj_status", "SLEEPING"),
            panic_phase=cd.get("panic_phase", "NEUTRAL"),
            divergence=bool(md.get("divergence_ao")),
            exit_bell=bool(md.get("exit_bell")),
            alligator=md.get("alligator", {}),
            brut=_trader("A06","brut_verdict","brut_reason","brut_entry","brut_stop","brut_tp","brut_lot"),
            avan=_trader("A07","avan_verdict","avan_reason","avan_entry","avan_stop","avan_tp","avan_lot"),
            cons=_trader("A08","cons_verdict","cons_reason","cons_entry","cons_stop","cons_tp","cons_lot"),
            council_fired=bool(results),
            error=None,
        )

    except Exception as e:
        import traceback; traceback.print_exc()
        return _error_response(req, str(e))


def _error_response(req, msg):
    empty = TraderSignal(verdict="REJECTED", reason="ERROR",
                         entry=None, stop=None, tp=None, lot=None, narrative=msg)
    return MT5SignalResponse(
        symbol=req.symbol, timeframe=req.timeframe, bar_time="",
        t1_status="NOT_FOUND", morj_status="SLEEPING", panic_phase="NEUTRAL",
        divergence=False, exit_bell=False, alligator={},
        brut=empty, avan=empty, cons=empty, council_fired=False, error=msg,
    )
