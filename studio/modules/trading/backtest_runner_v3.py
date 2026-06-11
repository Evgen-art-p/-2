# backtest_runner_v3.py
# ─────────────────────────────────────────────────────────────
# ШАГ 9 v3 — Двухтаймфреймовый раннер, три стратега
#
# Архитектура:
#   СТАРШИЙ ТФ (D1 или H4) — контекст: аллигатор открыт + AO зональность
#   МЛАДШИЙ ТФ (H4 или H1) — сигнал:   дивергентный бар + SQUAT
#
# Три стратега — три кривые PnL:
#   Авантюрист  → вход сразу на следующем баре после сигнала
#   Брут        → вход после подтверждения: цена прошла 0.5R вперёд
#   Консерватор → вход только на ретесте к уровню дивергентного бара
#
# Стоп системы один для всех — за хай/лоу дивергентного бара.
# PnL считается отдельно по каждому стратегу.
# ─────────────────────────────────────────────────────────────

import sys, csv, argparse
from pathlib import Path
from datetime import datetime
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent))
from studio.modules.trading.williams_core import (
    read_mt5_csv, _smma_series, compute_ao_series,
    compute_mfi, detect_fractals, get_point,
)

WARMUP       = 50
COOLDOWN     = 3
EXIT_MODES   = ["exit_bell", "fixed_1r", "fixed_2r"]
TRADERS      = ["AVANTURIST", "BRUT", "KONSERVATOR"]


# ════════════════════════════════════════════════════════════
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ (из v2, без изменений)
# ════════════════════════════════════════════════════════════

def alligator_series(highs, lows):
    med = [(h+l)/2 for h,l in zip(highs,lows)]
    return _smma_series(med,13), _smma_series(med,8), _smma_series(med,5)

def alligator_open(jaw_s, teeth_s, lips_s, i, direction):
    """Аллигатор открыт в нужную сторону на баре i."""
    j=jaw_s[i]; t=teeth_s[i]; l=lips_s[i]
    if None in (j,t,l): return False
    return (l>t>j) if direction=="LONG" else (l<t<j)

def ao_zone(ao_series, i, direction):
    ao=ao_series[i]
    if ao is None: return False
    return ao<=0 if direction=="LONG" else ao>=0

def divergent_bar(bars, i, direction):
    if i<1: return False
    b=bars[i]; pb=bars[i-1]; mid=(b["high"]+b["low"])/2
    if direction=="LONG":
        return b["low"]<pb["low"] and b["close"]>mid
    else:
        return b["high"]>pb["high"] and b["close"]<mid

def squat_near(bars, i, point):
    for j in [i-1, i]:
        if j<1 or j>=len(bars): continue
        mfi=compute_mfi(bars[j],bars[j-1],point)
        if mfi["type"]=="SQUAT": return True
    return False

def exit_bell_long(bars, ao_s, i):
    lookback=min(30,i)
    wb=bars[i-lookback:i+1]; wa=ao_s[i-lookback:i+1]
    hp=[]; ha=[]
    for k in range(2,len(wb)-2):
        ao=wa[k]
        if ao is None: continue
        if wb[k]["high"]>wb[k-1]["high"] and wb[k]["high"]>wb[k+1]["high"]:
            hp.append(wb[k]["high"]); ha.append(ao)
    if len(hp)>=2:
        p1,p2=hp[-2],hp[-1]; a1,a2=ha[-2],ha[-1]
        if p2>p1 and a2<a1 and a1>0 and a2>0: return True
    return False

def exit_bell_short(bars, ao_s, i):
    lookback=min(30,i)
    wb=bars[i-lookback:i+1]; wa=ao_s[i-lookback:i+1]
    lp=[]; la=[]
    for k in range(2,len(wb)-2):
        ao=wa[k]
        if ao is None: continue
        if wb[k]["low"]<wb[k-1]["low"] and wb[k]["low"]<wb[k+1]["low"]:
            lp.append(wb[k]["low"]); la.append(ao)
    if len(lp)>=2:
        p1,p2=lp[-2],lp[-1]; a1,a2=la[-2],la[-1]
        if p2<p1 and a2>a1 and a1<0 and a2<0: return True
    return False


# ════════════════════════════════════════════════════════════
# СИНХРОНИЗАЦИЯ ТАЙМФРЕЙМОВ
# ════════════════════════════════════════════════════════════

def build_htf_index(htf_bars):
    """
    Строит индекс: дата→бар для старшего ТФ.
    Для D1 ключ = дата без времени.
    Для H4 ключ = дата+час (начало 4-часовки).
    """
    idx = {}
    for i, b in enumerate(htf_bars):
        key = b["date"].split(" ")[0]  # берём дату
        idx[key] = i  # последний бар этой даты
    return idx

def get_htf_bar_for(ltf_bar, htf_bars, htf_idx):
    """
    Возвращает индекс бара старшего ТФ актуального для младшего.
    Ищем ближайший завершённый бар D1 для текущего H4/H1 бара.
    """
    date_key = ltf_bar["date"].split(" ")[0]
    # Если точная дата есть — берём
    if date_key in htf_idx:
        return htf_idx[date_key]
    # Иначе ищем предыдущий
    from datetime import datetime as dt
    d = dt.strptime(date_key, "%Y.%m.%d")
    for days_back in range(1, 10):
        from datetime import timedelta
        prev = (d - timedelta(days=days_back)).strftime("%Y.%m.%d")
        if prev in htf_idx:
            return htf_idx[prev]
    return None


# ════════════════════════════════════════════════════════════
# ЛОГИКА ТРЁХ СТРАТЕГОВ
# ════════════════════════════════════════════════════════════

def avanturist_entry(signal_bar_idx, ltf_bars):
    """Авантюрист: вход на открытии следующего бара после сигнала."""
    ni = signal_bar_idx + 1
    if ni >= len(ltf_bars): return None
    return {"entry_bar": ni, "entry": ltf_bars[ni]["open"]}

def brut_entry(signal_bar_idx, ltf_bars, stop, direction, risk):
    """
    Брут: вход после подтверждения — цена прошла 0.5R в нужную сторону.
    Ищем в следующих 5 барах.
    """
    db = ltf_bars[signal_bar_idx]
    if direction == "LONG":
        confirm_price = db["high"] + 0.5 * risk  # 0.5R выше дивергентного бара
        for ni in range(signal_bar_idx+1, min(signal_bar_idx+6, len(ltf_bars))):
            if ltf_bars[ni]["high"] >= confirm_price:
                return {"entry_bar": ni, "entry": round(confirm_price, 6)}
    else:
        confirm_price = db["low"] - 0.5 * risk
        for ni in range(signal_bar_idx+1, min(signal_bar_idx+6, len(ltf_bars))):
            if ltf_bars[ni]["low"] <= confirm_price:
                return {"entry_bar": ni, "entry": round(confirm_price, 6)}
    return None  # подтверждение не пришло

def konservator_entry(signal_bar_idx, ltf_bars, direction):
    """
    Консерватор: вход на ретесте — цена возвращается к уровню
    дивергентного бара (его экстремуму) в следующие 10 баров.
    """
    db = ltf_bars[signal_bar_idx]
    if direction == "LONG":
        retest_price = db["low"]   # возврат к минимуму дивергентного бара
        for ni in range(signal_bar_idx+1, min(signal_bar_idx+11, len(ltf_bars))):
            b = ltf_bars[ni]
            if b["low"] <= retest_price and b["close"] > retest_price:
                # Коснулся и отскочил — это ретест
                return {"entry_bar": ni, "entry": round(retest_price, 6)}
    else:
        retest_price = db["high"]
        for ni in range(signal_bar_idx+1, min(signal_bar_idx+11, len(ltf_bars))):
            b = ltf_bars[ni]
            if b["high"] >= retest_price and b["close"] < retest_price:
                return {"entry_bar": ni, "entry": round(retest_price, 6)}
    return None


# ════════════════════════════════════════════════════════════
# ВЫХОД (тот же для всех, но entry разный → pnl_r разный)
# ════════════════════════════════════════════════════════════

def check_exit(bar, pos, ltf_bars, ao_s, bar_idx, exit_mode):
    entry=pos["entry"]; stop=pos["stop"]
    direction=pos["direction"]
    risk=abs(entry-stop)
    if risk<=0: return None
    low=bar["low"]; high=bar["high"]; close=bar["close"]

    # Стоп
    if direction=="LONG" and low<=stop:
        return {"exit":stop,"reason":"STOP_LOSS",
                "pnl_r":round((stop-entry)/risk,4)}
    if direction=="SHORT" and high>=stop:
        return {"exit":stop,"reason":"STOP_LOSS",
                "pnl_r":round((entry-stop)/risk,4)}

    if exit_mode=="exit_bell":
        if direction=="LONG" and exit_bell_long(ltf_bars,ao_s,bar_idx):
            return {"exit":close,"reason":"EXIT_BELL",
                    "pnl_r":round((close-entry)/risk,4)}
        if direction=="SHORT" and exit_bell_short(ltf_bars,ao_s,bar_idx):
            return {"exit":close,"reason":"EXIT_BELL",
                    "pnl_r":round((entry-close)/risk,4)}
    elif exit_mode=="fixed_1r":
        tp=entry+risk if direction=="LONG" else entry-risk
        if (direction=="LONG" and high>=tp) or (direction=="SHORT" and low<=tp):
            return {"exit":round(tp,6),"reason":"TP_1R","pnl_r":1.0}
    elif exit_mode=="fixed_2r":
        tp=entry+2*risk if direction=="LONG" else entry-2*risk
        if (direction=="LONG" and high>=tp) or (direction=="SHORT" and low<=tp):
            return {"exit":round(tp,6),"reason":"TP_2R","pnl_r":2.0}
    return None


# ════════════════════════════════════════════════════════════
# ОСНОВНОЙ ПРОГОН
# ════════════════════════════════════════════════════════════

def run_backtest(htf_bars, ltf_bars, symbol, htf_name, ltf_name, exit_mode):
    print(f"\n[BT] ▶ {symbol} | контекст={htf_name} сигнал={ltf_name} "
          f"exit={exit_mode} | HTF={len(htf_bars)} LTF={len(ltf_bars)}")

    # Считаем индикаторы на HTF (контекст)
    htf_h=[b["high"] for b in htf_bars]; htf_l=[b["low"] for b in htf_bars]
    htf_ao   = compute_ao_series(htf_h, htf_l)
    htf_jaw, htf_teeth, htf_lips = alligator_series(htf_h, htf_l)
    htf_idx  = build_htf_index(htf_bars)

    # Считаем индикаторы на LTF (сигнал)
    ltf_h=[b["high"] for b in ltf_bars]; ltf_l=[b["low"] for b in ltf_bars]
    ltf_ao = compute_ao_series(ltf_h, ltf_l)
    pt     = get_point(symbol)

    # Состояние трёх стратегов
    trader_state = {t: {
        "position": None,
        "equity":   0.0,
        "trades":   [],
        "cooldown": 0,
    } for t in TRADERS}

    # Сигналы ожидающие входа стратегов (после нахождения дивергентного бара)
    pending = []  # list of {signal, entries_needed}

    total_signals = 0

    for ltf_i in range(WARMUP, len(ltf_bars)-1):
        ltf_bar = ltf_bars[ltf_i]

        # Уменьшаем кулдаун у всех
        for t in TRADERS:
            if trader_state[t]["cooldown"] > 0:
                trader_state[t]["cooldown"] -= 1

        # ── 1. Ведём открытые позиции всех стратегов ──
        for trader in TRADERS:
            ts = trader_state[trader]
            if ts["position"] is None: continue
            ts["position"]["bars_held"] += 1
            result = check_exit(ltf_bar, ts["position"],
                                 ltf_bars, ltf_ao, ltf_i, exit_mode)
            if result:
                pos = ts["position"]
                trade = {
                    "trader":     trader,
                    "open_date":  pos["open_date"],
                    "close_date": ltf_bar["date"],
                    "direction":  pos["direction"],
                    "entry":      pos["entry"],
                    "stop":       pos["stop"],
                    "exit":       result["exit"],
                    "pnl_r":      result["pnl_r"],
                    "reason":     result["reason"],
                    "bars_held":  ts["position"]["bars_held"],
                    "equity_r":   round(ts["equity"] + result["pnl_r"], 4),
                }
                ts["equity"]  = trade["equity_r"]
                ts["trades"].append(trade)
                ts["position"] = None
                if result["reason"] == "STOP_LOSS":
                    ts["cooldown"] = COOLDOWN
                s = "✅" if result["pnl_r"]>0 else "🛑"
                print(f"[BT]   {s} {ltf_bar['date']} {trader[:4]} "
                      f"[{trade['direction']}] {result['reason']} "
                      f"pnl={result['pnl_r']}R eq={ts['equity']}R")

        # ── 2. Ищем сигнал (только если хотя бы один стратег свободен) ──
        any_free = any(
            trader_state[t]["position"] is None and
            trader_state[t]["cooldown"] == 0
            for t in TRADERS
        )
        if not any_free:
            continue

        # Контекст HTF
        htf_i = get_htf_bar_for(ltf_bar, htf_bars, htf_idx)
        if htf_i is None or htf_i < WARMUP: continue

        for direction in ["LONG", "SHORT"]:
            # Фильтр контекста (HTF)
            if not alligator_open(htf_jaw, htf_teeth, htf_lips, htf_i, direction):
                continue
            if not ao_zone(htf_ao, htf_i, direction):
                continue

            # Сигнал (LTF)
            if not divergent_bar(ltf_bars, ltf_i, direction):
                continue
            if not squat_near(ltf_bars, ltf_i, pt):
                continue

            # Есть сигнал
            total_signals += 1
            db = ltf_bars[ltf_i]
            stop_price = db["low"] if direction=="LONG" else db["high"]
            entry_av   = ltf_bars[ltf_i+1]["open"]
            risk_av    = abs(entry_av - stop_price)
            if risk_av <= 0: continue

            # Вычисляем точки входа для каждого стратега
            entries = {
                "AVANTURIST":  avanturist_entry(ltf_i, ltf_bars),
                "BRUT":        brut_entry(ltf_i, ltf_bars, stop_price,
                                          direction, risk_av),
                "KONSERVATOR": konservator_entry(ltf_i, ltf_bars, direction),
            }

            print(f"[BT]   🎯 {ltf_bar['date']} "
                  f"{'🟢' if direction=='LONG' else '🔴'}{direction} "
                  f"stop={stop_price:.4f} risk={risk_av:.4f}")

            # Каждый стратег входит если свободен
            for trader in TRADERS:
                ts = trader_state[trader]
                if ts["position"] is not None or ts["cooldown"] > 0:
                    continue
                e = entries[trader]
                if e is None:
                    print(f"[BT]      {trader[:4]}: нет входа (условие не выполнено)")
                    continue
                entry_price = e["entry"]
                real_risk   = abs(entry_price - stop_price)
                if real_risk <= 0: continue
                ts["position"] = {
                    "open_date": ltf_bars[e["entry_bar"]]["date"],
                    "entry":     entry_price,
                    "stop":      stop_price,
                    "risk":      real_risk,
                    "direction": direction,
                    "bars_held": 0,
                }
                print(f"[BT]      {trader[:4]}: вход @ {entry_price:.4f} "
                      f"risk={real_risk:.4f}")
            break  # один сигнал на бар (первый подошедший)

    # Незакрытые позиции
    last = ltf_bars[-1]
    for trader in TRADERS:
        ts = trader_state[trader]
        if ts["position"]:
            pos = ts["position"]
            entry=pos["entry"]; stop=pos["stop"]
            risk=abs(entry-stop)
            close=last["close"]
            if pos["direction"]=="LONG":
                pnl_r=round((close-entry)/risk,4)
            else:
                pnl_r=round((entry-close)/risk,4)
            ts["equity"]=round(ts["equity"]+pnl_r,4)
            ts["trades"].append({
                "trader":trader,"open_date":pos["open_date"],
                "close_date":last["date"],"direction":pos["direction"],
                "entry":entry,"stop":stop,"exit":close,
                "pnl_r":pnl_r,"reason":"OPEN_AT_END",
                "bars_held":pos["bars_held"],"equity_r":ts["equity"],
            })

    # Собираем статистику
    stats = {}
    for trader in TRADERS:
        ts = trader_state[trader]
        stats[trader] = compute_stats(ts["trades"], symbol, htf_name,
                                       ltf_name, exit_mode, trader)

    print(f"\n[BT] ■ Сигналов: {total_signals}")
    for t in TRADERS:
        s = stats[t]
        print(f"     {t[:4]:12} сд={s['total_trades']:>3} "
              f"WR={s['win_rate']:>5.1f}% PF={s['profit_factor']:>6.3f} "
              f"R={s['total_r']:>8.4f}")

    return {"trader_states": trader_state, "stats": stats,
            "total_signals": total_signals}


# ════════════════════════════════════════════════════════════
# СТАТИСТИКА
# ════════════════════════════════════════════════════════════

def compute_stats(trades, symbol, htf, ltf, exit_mode, trader):
    closed=[t for t in trades if t["reason"]!="OPEN_AT_END"]
    if not closed:
        return {k:0 for k in ["total_trades","wins","losses","win_rate",
                "profit_factor","avg_r","max_r","min_r","total_r",
                "max_drawdown_r","long_trades","short_trades",
                "symbol","htf","ltf","exit_mode","trader"]}
    wins=[t for t in closed if t["pnl_r"]>0]
    losses=[t for t in closed if t["pnl_r"]<=0]
    gross_p=sum(t["pnl_r"] for t in wins)
    gross_l=abs(sum(t["pnl_r"] for t in losses))
    pf=round(gross_p/gross_l,3) if gross_l>0 else 999.0
    pnl=[t["pnl_r"] for t in closed]
    peak=eq=max_dd=0.0
    for t in closed:
        eq+=t["pnl_r"]; peak=max(peak,eq)
        max_dd=max(max_dd,peak-eq)
    return {
        "symbol":symbol,"htf":htf,"ltf":ltf,
        "exit_mode":exit_mode,"trader":trader,
        "total_trades":len(closed),"wins":len(wins),"losses":len(losses),
        "win_rate":round(len(wins)/len(closed)*100,1),
        "profit_factor":pf,
        "avg_r":round(sum(pnl)/len(pnl),4),
        "max_r":round(max(pnl),4),"min_r":round(min(pnl),4),
        "total_r":round(sum(pnl),4),
        "max_drawdown_r":round(max_dd,4),
        "long_trades":len([t for t in closed if t["direction"]=="LONG"]),
        "short_trades":len([t for t in closed if t["direction"]=="SHORT"]),
    }


# ════════════════════════════════════════════════════════════
# СОХРАНЕНИЕ
# ════════════════════════════════════════════════════════════

def save_results(result, out_dir, symbol, htf_name, ltf_name, exit_mode):
    ts_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    base   = f"bt3_{symbol}_{htf_name}_{ltf_name}_{exit_mode}_{ts_str}"
    out    = Path(out_dir)

    # CSV всех сделок
    all_trades = []
    for t in TRADERS:
        all_trades.extend(result["trader_states"][t]["trades"])
    all_trades.sort(key=lambda x: x["open_date"])

    if all_trades:
        p = out / f"{base}_trades.csv"
        with open(p,"w",newline="",encoding="utf-8") as f:
            w=csv.DictWriter(f,fieldnames=list(all_trades[0].keys()))
            w.writeheader(); w.writerows(all_trades)
        print(f"[OUT] 📄 {p.name}")

    # Текстовый отчёт
    p = out / f"{base}_report.txt"
    with open(p,"w",encoding="utf-8") as f:
        f.write("═"*70+"\n")
        f.write(f"  v3 ТРИ СТРАТЕГА — {symbol} | {htf_name}→{ltf_name} "
                f"| EXIT: {exit_mode}\n")
        f.write(f"  {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        f.write(f"  Сигналов найдено: {result['total_signals']}\n")
        f.write("═"*70+"\n\n")
        f.write(f"  {'Стратег':<14} {'Сд':>4} {'L/S':>7} "
                f"{'WR%':>7} {'PF':>8} {'Итого R':>9} "
                f"{'MaxDD':>8} {'Avg R':>8}\n")
        f.write("  "+"─"*66+"\n")
        for trader in TRADERS:
            s=result["stats"][trader]
            f.write(f"  {trader:<14} {s['total_trades']:>4} "
                    f"{s['long_trades']}L/{s['short_trades']}S".ljust(9)+
                    f" {s['win_rate']:>7.1f} {s['profit_factor']:>8.3f} "
                    f"{s['total_r']:>9.4f} {s['max_drawdown_r']:>8.4f} "
                    f"{s['avg_r']:>8.4f}\n")
        f.write("\n"+"═"*70+"\n")
    print(f"[OUT] 📊 {p.name}")


def save_comparison(all_results, out_dir, symbol, htf_name, ltf_name):
    ts_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    p = Path(out_dir) / f"bt3_{symbol}_{htf_name}_{ltf_name}_comparison_{ts_str}.txt"
    with open(p,"w",encoding="utf-8") as f:
        f.write("═"*72+"\n")
        f.write(f"  v3 СРАВНЕНИЕ ВЫХОДОВ — {symbol} {htf_name}→{ltf_name}\n")
        f.write("═"*72+"\n\n")
        for exit_mode in EXIT_MODES:
            f.write(f"  EXIT: {exit_mode}\n")
            f.write(f"  {'Стратег':<14} {'Сд':>4} {'WR%':>7} "
                    f"{'PF':>8} {'R':>9} {'MaxDD':>8}\n")
            f.write("  "+"─"*52+"\n")
            res = all_results.get(exit_mode, {})
            for trader in TRADERS:
                s = res.get("stats",{}).get(trader,{})
                if not s or not s.get("total_trades"):
                    f.write(f"  {trader:<14} нет сделок\n")
                    continue
                f.write(f"  {trader:<14} {s['total_trades']:>4} "
                        f"{s['win_rate']:>7.1f} {s['profit_factor']:>8.3f} "
                        f"{s['total_r']:>9.4f} {s['max_drawdown_r']:>8.4f}\n")
            f.write("\n")
        f.write("═"*72+"\n")
    print(f"\n[OUT] 🏆 {p.name}")


# ════════════════════════════════════════════════════════════
# ТОЧКА ВХОДА
# ════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="ШАГ 9 v3 — 3 стратега")
    parser.add_argument("htf_csv",  help="CSV старшего ТФ (контекст)")
    parser.add_argument("ltf_csv",  help="CSV младшего ТФ (сигнал)")
    parser.add_argument("symbol",   help="Тикер")
    parser.add_argument("htf_name", help="Имя старшего ТФ (D1, H4...)")
    parser.add_argument("ltf_name", help="Имя младшего ТФ (H4, H1...)")
    parser.add_argument("--exit", choices=EXIT_MODES+["all"], default="all")
    args = parser.parse_args()

    htf_bars = read_mt5_csv(args.htf_csv)
    ltf_bars = read_mt5_csv(args.ltf_csv)
    if not htf_bars or not ltf_bars:
        print("[ERR] Нет данных"); sys.exit(1)

    out_dir = str(Path(args.htf_csv).parent)
    modes   = EXIT_MODES if args.exit=="all" else [args.exit]
    all_res = {}

    for mode in modes:
        result = run_backtest(htf_bars, ltf_bars, args.symbol,
                              args.htf_name, args.ltf_name, mode)
        all_res[mode] = result
        save_results(result, out_dir, args.symbol,
                     args.htf_name, args.ltf_name, mode)

    if args.exit == "all":
        save_comparison(all_res, out_dir, args.symbol,
                        args.htf_name, args.ltf_name)

        print("\n" + "═"*72)
        print(f"  ИТОГ — {args.symbol} {args.htf_name}→{args.ltf_name}")
        print("═"*72)
        for mode in EXIT_MODES:
            print(f"\n  {mode}:")
            print(f"  {'Стратег':<14} {'Сд':>4} {'WR%':>7} "
                  f"{'PF':>8} {'R':>9} {'MaxDD':>8}")
            print("  "+"─"*50)
            res = all_res.get(mode, {})
            for trader in TRADERS:
                s = res.get("stats",{}).get(trader,{})
                if not s or not s.get("total_trades"):
                    print(f"  {trader:<14} нет сделок")
                    continue
                print(f"  {trader:<14} {s['total_trades']:>4} "
                      f"{s['win_rate']:>7.1f} {s['profit_factor']:>8.3f} "
                      f"{s['total_r']:>9.4f} {s['max_drawdown_r']:>8.4f}")
        print("═"*72)

if __name__ == "__main__":
    main()
