# studio/modules/trading/probe_engine.py — ВЕРСТАК, временный, НЕ часть цеха.
# ENGINE_ONE_DOOR_V1
# ─────────────────────────────────────────────────────────────
# ПУТЬ 1: гонит ОДИН файл (один этаж) через единый движок.
# На каждом баре — логика Шефа: математика → ведение → Совет по звонку.
# Совет ЖИВОЙ (LLM). Спуск Искры заперт (путь 1 = один этаж).
# Лента сделок 🟢/🔴 в консоль. Шеф жмёт раз — машина гонит сама.
#
# Запуск из корня:
#   python -m studio.modules.trading.probe_engine <csv> <symbol> <tf>
#   python -m studio.modules.trading.probe_engine \
#          studio/modules/trading/test_data/XAUUSD_H4.csv XAUUSD H4
#
# Флаги:
#   --dry   только математика, Совет НЕ будим (как ломоть 1 — проверка реки)
#   --signals N  остановиться после N разбуженных Советов (по умолч. все)
# ─────────────────────────────────────────────────────────────
import sys, argparse, json
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv"); ap.add_argument("symbol"); ap.add_argument("tf")
    ap.add_argument("--point", default=None)
    ap.add_argument("--warmup", type=int, default=60)
    ap.add_argument("--dry", action="store_true",
                    help="только математика, Совет не будить (проверка реки)")
    ap.add_argument("--signals", type=int, default=0,
                    help="стоп после N разбуженных Советов (0 = вся история)")
    args = ap.parse_args()

    from studio.modules.trading.engine import run_history, read_facts
    from studio.modules.trading.williams_core import read_mt5_csv

    pts = {"XAUUSD": 0.01, "XAGUSD": 0.001, "EURUSD": 0.00001,
           "GBPUSD": 0.00001, "USDJPY": 0.001, "AUDUSD": 0.00001,
           "USDCHF": 0.00001, "USDCAD": 0.00001, "BTCUSD": 0.01}
    point = float(args.point) if args.point else pts.get(args.symbol.upper())
    if point is None:
        print(f"point для {args.symbol} неизвестен — задай --point"); sys.exit(1)

    csv_path = args.csv if Path(args.csv).is_absolute() else args.csv
    bars = read_mt5_csv(csv_path)
    if not bars:
        print(f"CSV пуст: {csv_path}"); sys.exit(1)
    total = len(bars)

    print("=" * 60)
    print(f"  ВЕРСТАК · ПУТЬ 1 · {args.symbol} {args.tf} · {total} баров")
    print(f"  движок гонит бар за баром (рекой). Совет: "
          f"{'НЕ будим (--dry)' if args.dry else 'ЖИВОЙ на точках'}")
    print(f"  спуск Искры заперт (путь 1 = один этаж/файл)")
    print("=" * 60)

    # PROBE_FEED_TESTER_V1: включаем кран tester ДО любого спуска.
    # Без этого feed_source идёт в терминал (mode=real по умолч.)
    # за старшими ТФ и получает 'Нет котировок'. Лесенка золота
    # лежит в test_data/ — кран tester её и читает. Терминал спит.
    _feed_prev = None
    try:
        from studio.modules.trading.feed_source import (
            get_feed_mode, set_feed_mode)
        _feed_prev = get_feed_mode()
        set_feed_mode("tester", args.symbol.upper())
        print(f"  кран → TESTER (папка test_data), символ "
              f"{args.symbol.upper()} · терминал не трогаем")
    except Exception as e:
        print(f"  (кран не переключился: {e})")

    # ── чистим стол этого символа перед заходом (как тестер Шефа) ──
    try:
        from studio.modules.trading.hooks import load_trading_state, save_trading_state
        t = load_trading_state()
        sym = args.symbol.upper()
        before = t.get("positions", []) or []
        t["positions"] = [p for p in before
                          if p.get("symbol") and p.get("symbol", "").upper() != sym]
        t.setdefault("iskra", {})
        t["iskra"] = {"t1_status": "NOT_FOUND", "zero_point_price": None, "history_dna": ""}
        save_trading_state(t)
    except Exception as e:
        print(f"  (стол не почистился: {e})")

    # ── счётчики ленты ──
    pnl_path = Path("economy/data/trading_pnl.jsonl")
    seen = len(pnl_path.read_text(encoding="utf-8").strip().splitlines()) if pnl_path.exists() else 0

    woke_count = [0]

    def _flush_closures():
        if not pnl_path.exists():
            return
        lines = pnl_path.read_text(encoding="utf-8").strip().splitlines()
        for ln in lines[seen[0]:]:
            try:
                r = json.loads(ln)
            except Exception:
                continue
            rr = r.get("pnl_r")
            sign = "+" if (rr or 0) >= 0 else ""
            print(f"  🔴 ЗАКРЫТА: {r.get('trader')} {sign}{rr}R "
                  f"({r.get('close_reason')}) {r.get('opened_at')}→{r.get('closed_at')}")
        seen[0] = len(lines)
    seen = [seen]

    # ── будилка Совета (живая) + событие в ленту ──
    def wake(md):
        woke_count[0] += 1
        bt = md.get("bar_time", "")
        print(f"\n  📡 ТОЧКА #{woke_count[0]} (бар {bt}) — бужу Совет...")
        if args.dry:
            return
        from studio.modules.trading.council import wake_council
        # снимок открытых ДО — чтоб увидеть новые
        try:
            from studio.modules.trading.hooks import load_trading_state
            before = {p.get("magic") for p in load_trading_state().get("positions", [])
                      if p.get("status") == "OPEN"}
        except Exception:
            before = set()
        s = wake_council(args.symbol, args.tf)
        for aid in s.get("woke", []):
            pass
        # новые открытые → лента
        try:
            from studio.modules.trading.hooks import load_trading_state
            now = load_trading_state().get("positions", []) or []
            for p in now:
                if p.get("status") == "OPEN" and p.get("magic") not in before:
                    print(f"  🟢 ОТКРЫТА: {p.get('trader')} {p.get('direction')} "
                          f"@ {p.get('entry')} стоп {p.get('stop')}")
        except Exception:
            pass

    def settle(md):
        from studio.modules.trading.hooks import _settle_positions, load_trading_state
        t = load_trading_state()
        st = {"chain_data": {"market_data": md,
                             "open_positions": t.get("positions", []) or []}}
        try:
            _settle_positions(st)
        except Exception as e:
            print(f"  (settle: {e})")
        _flush_closures()

    def should_stop():
        return args.signals > 0 and woke_count[0] >= args.signals

    res = run_history(bars, args.symbol, args.tf, point,
                      wake=(None if args.dry else wake),
                      settle=settle, warmup=args.warmup,
                      should_stop=should_stop)
    # в dry-режиме точки считаем через read_facts отдельным проходом
    if args.dry:
        cnt = 0
        for i in range(args.warmup, total):
            f = read_facts(bars[max(0, i-299):i+1], args.symbol, args.tf, point)
            if f and f.get("has_point"):
                cnt += 1
        res["council_woke"] = cnt

    # PROBE_FEED_TESTER_V1: возвращаем кран как был — не оставляем
    # цех в тестовом режиме после верстака.
    try:
        if _feed_prev is not None:
            set_feed_mode(_feed_prev.get("mode", "real"),
                          _feed_prev.get("symbol"))
    except Exception:
        pass
    print("\n" + "=" * 60)
    print(f"  прошёл баров: {res['bars']}")
    print(f"  Точек Ноль (звонков Совету): {res['council_woke']}")
    if not args.dry:
        print(f"  Советов разбужено: {woke_count[0]}")
    _flush_closures()
    print(f"  ВЫВОД: движок прошёл историю рекой. Совет вставал только на")
    print(f"  Точках Ноль. Сделки жили от открытия до колокола. Один движок.")
    print("=" * 60)


if __name__ == "__main__":
    main()
