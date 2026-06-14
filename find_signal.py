# -*- coding: utf-8 -*-
# find_signal.py
# ─────────────────────────────────────────────────────────────
# Ищет бары где Искра бы сказала DETECTED:
#   - divergence_ao=True (бычья дивергенция AO)
#   - squat.last_squat не пустой (есть приседающий)
#
# Без LLM. Чистая математика williams_core.py.
#
# Использование:
#   python find_signal.py путь/к/csv.csv XAUUSD
#   python find_signal.py путь/к/csv.csv EURUSD --last 500
#
# Выводит список дат и цен — выбираешь интересную,
# потом запускаешь run_council.py на куске вокруг неё.
# ─────────────────────────────────────────────────────────────

import sys
import csv
import argparse
from pathlib import Path

ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(ROOT))

from studio.modules.trading.williams_core import build_market_data


def load_csv(path: Path) -> list[dict]:
    """Читает MT5-CSV в список баров."""
    bars = []
    with open(path, encoding="utf-8", errors="replace") as f:
        # Пробуем определить разделитель
        sample = f.read(2048)
        f.seek(0)
        delimiter = "\t" if "\t" in sample else ","
        reader = csv.DictReader(f, delimiter=delimiter)
        for row in reader:
            try:
                # MT5 может давать DATE+TIME или DATE отдельно
                date = row.get("DATE") or row.get("Date") or row.get("<DATE>") or ""
                time = row.get("TIME") or row.get("Time") or row.get("<TIME>") or "00:00"
                dt   = f"{date} {time}".strip()

                bars.append({
                    "date":   dt,
                    "open":   float(row.get("OPEN")  or row.get("Open")  or row.get("<OPEN>")  or 0),
                    "high":   float(row.get("HIGH")  or row.get("High")  or row.get("<HIGH>")  or 0),
                    "low":    float(row.get("LOW")   or row.get("Low")   or row.get("<LOW>")   or 0),
                    "close":  float(row.get("CLOSE") or row.get("Close") or row.get("<CLOSE>") or 0),
                    "volume": float(row.get("TICKVOL") or row.get("VOL") or
                                    row.get("Volume") or row.get("<TICKVOL>") or 1),
                    "spread": float(row.get("SPREAD") or row.get("<SPREAD>") or 1),
                })
            except (ValueError, KeyError):
                continue
    return bars


def find_signals(bars: list[dict], symbol: str) -> list[dict]:
    """
    Прогоняет williams_core по всем барам,
    находит где divergence_ao=True + squat есть.
    Нужно минимум 35 баров для AO.
    """
    signals = []
    min_window = 35

    for i in range(min_window, len(bars)):
        window = bars[: i + 1]  # все бары до текущего включительно
        try:
            md = build_market_data(window, symbol=symbol, timeframe="?")
        except Exception:
            continue

        if not md.get("divergence_ao"):
            continue

        squat = md.get("squat", {}) or {}
        last_sq = squat.get("last_squat")
        if not last_sq:
            continue

        signals.append({
            "bar_index":  i,
            "date":       bars[i]["date"],
            "close":      bars[i]["close"],
            "squat_high": last_sq["high"],
            "squat_low":  last_sq["low"],
            "squat_date": last_sq["date"],
            "ao":         round(md.get("ao") or 0, 6),
            "morj":       md.get("alligator", {}).get("state", "?"),
        })

    return signals


def main():
    parser = argparse.ArgumentParser(
        description="Найти бары с сигналом Искры (divergence_ao + squat)."
    )
    parser.add_argument("csv_path", help="Путь к MT5-CSV.")
    parser.add_argument("symbol",   help="Тикер (XAUUSD, EURUSD, ...).")
    parser.add_argument("--last", type=int, default=0,
                        help="Взять только последние N баров (0 = все).")
    args = parser.parse_args()

    csv_path = Path(args.csv_path).resolve()
    if not csv_path.exists():
        print(f"❌ CSV не найден: {csv_path}")
        sys.exit(1)

    print(f"\n📂 Читаю {csv_path.name}...")
    bars = load_csv(csv_path)
    print(f"   Загружено баров: {len(bars)}")

    if args.last and args.last < len(bars):
        bars = bars[-args.last:]
        print(f"   Беру последние {args.last} баров.")

    print(f"\n🔍 Ищу сигналы ({args.symbol})...\n")
    signals = find_signals(bars, args.symbol)

    if not signals:
        print("❌ Сигналов не найдено на этом куске.")
        print("   Попробуй другой актив или увеличь --last.")
        sys.exit(0)

    print(f"✅ Найдено сигналов: {len(signals)}\n")
    print(f"{'№':>4}  {'Дата бара':<22}  {'Цена':>10}  "
          f"{'Squat дата':<22}  {'AO':>10}  Аллигатор")
    print("─" * 90)
    for n, s in enumerate(signals, 1):
        print(f"{n:>4}  {s['date']:<22}  {s['close']:>10.5f}  "
              f"{s['squat_date']:<22}  {s['ao']:>10.6f}  {s['morj']}")

    print(f"\n{'─' * 90}")
    print(f"Выбери интересный бар из списка.")
    print(f"Запусти Совет на куске вокруг него:")
    print(f"")

    # Подсказка для последнего сигнала
    last = signals[-1]
    print(f"  Последний сигнал: {last['date']}")
    print(f"  Для прогона Совета вокруг него:")
    print(f"  python run_council.py {args.csv_path} {args.symbol} <TF> --bars 150")
    print(f"  (150 баров хватит чтобы Морж/Искра видели контекст)")
    print()


if __name__ == "__main__":
    main()
