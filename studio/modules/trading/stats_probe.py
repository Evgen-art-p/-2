# studio/modules/trading/stats_probe.py — ВЕРСТАК, временный, НЕ часть цеха.
# ENGINE_ONE_DOOR_V1 · спутник probe_engine
# ─────────────────────────────────────────────────────────────
# Читает economy/data/trading_pnl.jsonl (журнал закрытых сделок),
# сводит в кривую прибыльности. Ноль LLM, ноль правок движка —
# только читает факт со стола. Отвечает на ГЛАВНЫЙ вопрос Шефа:
# «зарабатывает или теряет» — суммарной R, без болтовни.
#
# Запуск из корня:
#   python -m studio.modules.trading.stats_probe
#   python -m studio.modules.trading.stats_probe --symbol XAUUSD
#   python -m studio.modules.trading.stats_probe --since 2026-06-24
#   python -m studio.modules.trading.stats_probe --pnl path/to/trading_pnl.jsonl
#
# Закон верстака: ничего не решает, ничего не пишет. Только зеркало.
# ─────────────────────────────────────────────────────────────
import sys, argparse, json
from pathlib import Path

DEFAULT_PNL = "economy/data/trading_pnl.jsonl"


def _load(pnl_path: str, symbol_filter=None, since=None):
    """Читает журнал, возвращает список закрытых сделок (pnl_r не None)."""
    p = Path(pnl_path)
    if not p.exists():
        print(f"журнал не найден: {pnl_path}")
        print("сначала прогони probe_engine — он наполнит журнал.")
        sys.exit(1)
    rows = []
    for ln in p.read_text(encoding="utf-8").strip().splitlines():
        ln = ln.strip()
        if not ln:
            continue
        try:
            r = json.loads(ln)
        except Exception:
            continue
        if r.get("pnl_r") is None:
            continue
        if symbol_filter and str(r.get("symbol", "")).upper() != symbol_filter.upper():
            continue
        if since:
            ca = r.get("closed_at") or r.get("ts") or ""
            if ca[:len(since)] < since:
                continue
        rows.append(r)
    return rows


def _curve(rows):
    """Кривая equity в R + максимальная просадка. Порядок — как в журнале
    (append-only = хронология закрытий)."""
    eq, peak, max_dd = 0.0, 0.0, 0.0
    curve = []
    for r in rows:
        eq += r.get("pnl_r") or 0.0
        peak = max(peak, eq)
        dd = peak - eq
        max_dd = max(max_dd, dd)
        curve.append(round(eq, 4))
    return curve, round(max_dd, 4)


def _block(rows, title):
    """Считает и печатает блок метрик по набору сделок."""
    n = len(rows)
    if n == 0:
        print(f"\n── {title} ──")
        print("  нет сделок")
        return
    Rs = [r.get("pnl_r") or 0.0 for r in rows]
    wins = [x for x in Rs if x > 0]
    losses = [x for x in Rs if x < 0]
    flat = [x for x in Rs if x == 0]
    total_r = round(sum(Rs), 4)
    winrate = round(100 * len(wins) / n, 1)
    gross_win = sum(wins)
    gross_loss = abs(sum(losses))
    pf = round(gross_win / gross_loss, 3) if gross_loss > 0 else float("inf")
    avg_win = round(sum(wins) / len(wins), 4) if wins else 0.0
    avg_loss = round(sum(losses) / len(losses), 4) if losses else 0.0
    expectancy = round(total_r / n, 4)
    curve, max_dd = _curve(rows)

    print(f"\n── {title} ──")
    print(f"  сделок:           {n}  (W:{len(wins)} L:{len(losses)} 0:{len(flat)})")
    print(f"  СУММАРНАЯ R:      {'+' if total_r >= 0 else ''}{total_r}R")
    print(f"  winrate:          {winrate}%")
    pf_str = "∞" if pf == float("inf") else f"{pf}"
    print(f"  profit factor:    {pf_str}")
    print(f"  ожидание/сделку:  {'+' if expectancy >= 0 else ''}{expectancy}R")
    print(f"  средний плюс:     +{avg_win}R   средний минус: {avg_loss}R")
    print(f"  макс. просадка:   -{max_dd}R")
    print(f"  пик equity:       +{round(max(curve), 4) if curve else 0}R   "
          f"финал: {'+' if curve and curve[-1] >= 0 else ''}{curve[-1] if curve else 0}R")


def _by_reason(rows):
    """Разбивка по причине выхода — где утекает/копится R."""
    agg = {}
    for r in rows:
        reason = r.get("close_reason", "?")
        d = agg.setdefault(reason, {"n": 0, "r": 0.0})
        d["n"] += 1
        d["r"] += r.get("pnl_r") or 0.0
    print(f"\n── по причине выхода ──")
    for reason, d in sorted(agg.items(), key=lambda kv: kv[1]["r"]):
        print(f"  {reason:14s} {d['n']:4d} сделок   "
              f"{'+' if d['r'] >= 0 else ''}{round(d['r'], 2)}R")


def _spark(curve):
    """Грубая ASCII-искра кривой equity — увидеть форму глазом."""
    if not curve:
        return
    blocks = "▁▂▃▄▅▆▇█"
    lo, hi = min(curve), max(curve)
    rng = hi - lo or 1.0
    # прореживаем до ~60 точек
    step = max(1, len(curve) // 60)
    sampled = curve[::step]
    line = "".join(blocks[min(7, int((v - lo) / rng * 7))] for v in sampled)
    print(f"\n── форма equity (слева старое → справа свежее) ──")
    print(f"  {line}")
    print(f"  низ {round(lo, 1)}R · верх {round(hi, 1)}R")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pnl", default=DEFAULT_PNL, help="путь к trading_pnl.jsonl")
    ap.add_argument("--symbol", default=None, help="фильтр по тикеру (XAUUSD)")
    ap.add_argument("--since", default=None,
                    help="только сделки с closed_at >= даты (2026-06-24)")
    args = ap.parse_args()

    rows = _load(args.pnl, args.symbol, args.since)
    flt = []
    if args.symbol:
        flt.append(args.symbol.upper())
    if args.since:
        flt.append(f"с {args.since}")
    flt_str = ("  [" + ", ".join(flt) + "]") if flt else ""

    print("=" * 60)
    print(f"  СТАТИСТИКА ЦЕХА · {len(rows)} закрытых сделок{flt_str}")
    print("=" * 60)

    if not rows:
        print("\n  нечего считать — журнал пуст под этот фильтр.")
        return

    # ОБЩИЙ итог — ответ на главный вопрос
    _block(rows, "ВСЕ ТРЕЙДЕРЫ ВМЕСТЕ (главный итог)")

    # ИСКРА (форма equity) — глазом
    curve, _ = _curve(rows)
    _spark(curve)

    # по причине выхода
    _by_reason(rows)

    # по каждому трейдеру отдельно
    traders = sorted({r.get("trader") for r in rows if r.get("trader")})
    for t in traders:
        _block([r for r in rows if r.get("trader") == t], f"трейдер: {t}")

    # вердикт одной строкой
    total_r = round(sum(r.get("pnl_r") or 0.0 for r in rows), 4)
    print("\n" + "=" * 60)
    if total_r > 0:
        print(f"  ВЕРДИКТ: суммарно +{total_r}R — цех в плюсе на этой выборке.")
    elif total_r < 0:
        print(f"  ВЕРДИКТ: суммарно {total_r}R — цех в минусе на этой выборке.")
    else:
        print(f"  ВЕРДИКТ: ровно 0R — цех в нуле.")
    print(f"  Помни: это PAPER-история, не статистика рынка вообще. Выборка"
          f" мала — три сделки или триста, число говорит лишь за себя.")
    print("=" * 60)


if __name__ == "__main__":
    main()
