# -*- coding: utf-8 -*-
# run_council_batch.py
# ─────────────────────────────────────────────────────────────
# Прогоняет Военный Совет последовательно по списку сигналов.
# ДНК, Атлас, PnL — живут сами, скрипт просто запускает очередь.
#
# Использование (из корня репо):
#   python run_council_batch.py EURUSDDaily.csv
#
# В конце выводит итог: сколько APPROVED/REJECTED у каждого
# трейдера и суммарный PnL по закрытым позициям.
# ─────────────────────────────────────────────────────────────

import sys
import asyncio
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(ROOT))

from studio.cartridge import run_cartridge, PipelineCallbacks

# ── 30 последних сигналов из EURUSD D1 (2011-2026) ──────────
# Найдены математически через williams_core.divergence_ao + squat.
# Последние 30 из 363 — свежий рынок 2024-2026.
SIGNALS = [
    "2024.10.03", "2024.10.04", "2024.10.07", "2024.10.08",
    "2024.10.09", "2024.10.10", "2024.10.11", "2024.10.14",
    "2024.11.22", "2024.11.25", "2024.11.26", "2024.11.27",
    "2024.12.02", "2024.12.03", "2025.01.13", "2025.01.14",
    "2025.03.03", "2025.03.04", "2025.03.05", "2025.03.06",
    "2026.01.13", "2026.01.14", "2026.01.15", "2026.01.16",
    "2026.04.02", "2026.04.03", "2026.04.06",
    "2026.06.01", "2026.06.02", "2026.06.03",
]

# ── Лог-колбэки (тихие — только терминал, не пишем протокол) ─
class BatchCallbacks(PipelineCallbacks):
    def __init__(self, date_label: str):
        self.date_label = date_label
        self.verdicts = {}   # worker_id → verdict

    async def on_agent_done(self, slot_id, worker_id, label,
                             human_text, meta, ghost_ids=None):
        my_output = (meta.get("my_output") if isinstance(meta, dict) else None) or {}
        verdict_key = next((k for k in my_output if "verdict" in k.lower()), None)
        if verdict_key:
            self.verdicts[worker_id] = my_output[verdict_key]
            print(f"  {worker_id}: {my_output[verdict_key]}")

    async def on_pipeline_error(self, slot_id, error):
        print(f"  ❌ ошибка: {error}")

    async def on_agent_error(self, slot_id, worker_id, error):
        print(f"  ⚠ {worker_id} упал: {error}")

    async def on_status(self, slot_id, message, level="info"):
        pass  # тихо


# ── Читаем CSV (UTF-16, без заголовка) ───────────────────────
def load_csv(path: Path) -> list[dict]:
    bars = []
    for line in path.read_text(encoding="utf-16", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split(",")
        if len(parts) < 6:
            continue
        try:
            bars.append({
                "date":   parts[0],
                "open":   float(parts[1]),
                "high":   float(parts[2]),
                "low":    float(parts[3]),
                "close":  float(parts[4]),
                "volume": float(parts[5]),
                "spread": float(parts[6]) if len(parts) > 6 else 1.0,
            })
        except ValueError:
            continue
    return bars


def get_window(bars: list[dict], target_date: str, window: int = 150) -> list[dict]:
    """Берёт N баров до целевой даты включительно."""
    for i, b in enumerate(bars):
        if b["date"] == target_date:
            start = max(0, i - window + 1)
            return bars[start : i + 1]
    return []


# ── Один прогон Совета на дате ───────────────────────────────
async def run_one(bars_window: list[dict], symbol: str,
                  timeframe: str, date_label: str) -> dict:
    cb = BatchCallbacks(date_label)

    # Считаем market_data напрямую через williams_core
    # и кладём в chain_data — hooks увидит webhook-режим и не будет читать CSV
    from studio.modules.trading.williams_core import build_market_data
    market_data = build_market_data(bars_window, symbol=symbol, timeframe=timeframe)

    if not market_data:
        print(f"  ⚠ williams_core вернул пустой результат для {date_label}")
        return {}

    # Подушка безопасности (второй бар назад)
    bar_back2_low  = bars_window[-3]["low"]  if len(bars_window) >= 3 else None
    bar_back2_high = bars_window[-3]["high"] if len(bars_window) >= 3 else None

    state = {
        "active_dept":  "trading",
        "run_type":     "batch_council",
        "master_brief": (
            f"Военный Совет · {symbol} {timeframe} · {date_label}. "
            f"Батч-прогон для накопления Атласа и обновления ДНК. "
            f"Принять решение по текущему состоянию рынка."
        ),
        "settings": {
            "symbol":     symbol,
            "timeframe":  timeframe,
        },
        "chain_data": {
            "market_data":    market_data,
            "_bar_back2_low":  bar_back2_low,
            "_bar_back2_high": bar_back2_high,
        },
        "results":    {},
        "_agent_ids": [],
    }
    tmp = None  # файла нет

    # Регистрируем агентов как работающих — иначе pipeline даёт HOME-режим
    _slot = f"batch_{date_label}"
    _agents = ["A01","A02","A03","A04","A05","A06","A07","A08","A09"]
    try:
        from studio.city_pulse import work_start as _ws
        for _a in _agents:
            try: _ws(_a, dept="trading", slot_id=_slot)
            except Exception: pass
    except Exception: pass

    try:
        await run_cartridge(
            module_id="trading",
            state=state,
            callbacks=cb,
            slot_id=_slot,
            turbo=True,
        )
    except Exception as e:
        print(f"  ❌ Прогон упал: {e}")
    finally:
        try:
            from studio.city_pulse import work_end as _we
            for _a in _agents:
                try: _we(_a, dept="trading", slot_id=_slot)
                except Exception: pass
        except Exception: pass
        if tmp: tmp.unlink(missing_ok=True)

    return cb.verdicts


# ── Читаем итоговый PnL из файла ─────────────────────────────
def read_pnl_summary() -> dict:
    """Читает trading_pnl.jsonl и считает итог по трейдерам."""
    pnl_paths = list(ROOT.rglob("trading_pnl.jsonl"))
    if not pnl_paths:
        return {}

    summary = {}  # trader → {approved, rejected, total_r, trades}
    for path in pnl_paths:
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                rec = json.loads(line)
                trader = rec.get("trader", "?")
                if trader not in summary:
                    summary[trader] = {"approved": 0, "closed": 0, "total_r": 0.0}
                summary[trader]["approved"] += 1
                if rec.get("pnl_r") is not None:
                    summary[trader]["closed"] += 1
                    summary[trader]["total_r"] += float(rec["pnl_r"])
            except Exception:
                continue
    return summary


# ── MAIN ─────────────────────────────────────────────────────
async def main():
    if len(sys.argv) < 2:
        print("Использование: python run_council_batch.py <csv_path> [SYMBOL] [TF]")
        sys.exit(1)

    csv_path  = Path(sys.argv[1]).resolve()
    symbol    = sys.argv[2] if len(sys.argv) > 2 else "EURUSD"
    timeframe = sys.argv[3] if len(sys.argv) > 3 else "D1"

    if not csv_path.exists():
        print(f"❌ CSV не найден: {csv_path}")
        sys.exit(1)

    print(f"\n{'═'*60}")
    print(f"  БАТЧ-ПРОГОН · {symbol} {timeframe}")
    print(f"  Сигналов: {len(SIGNALS)}")
    print(f"  CSV: {csv_path.name}")
    print(f"{'═'*60}\n")

    bars = load_csv(csv_path)
    print(f"Загружено баров: {len(bars)}\n")

    all_verdicts = []  # список dict {date, A06, A07, A08}

    for i, date in enumerate(SIGNALS, 1):
        window = get_window(bars, date)
        if not window:
            print(f"[{i:02d}/{len(SIGNALS)}] {date} — ⚠ не найдено в CSV, пропуск")
            continue

        print(f"[{i:02d}/{len(SIGNALS)}] {date} · {len(window)} баров")
        verdicts = await run_one(window, symbol, timeframe, date)
        all_verdicts.append({"date": date, **verdicts})
        print()

        # Небольшая пауза между прогонами чтобы не перегрузить API
        await asyncio.sleep(2)

    # ── Итоговая таблица решений ─────────────────────────────
    print(f"\n{'═'*60}")
    print(f"  ИТОГ ТРИБУНАЛА — {len(all_verdicts)} заседаний")
    print(f"{'═'*60}")
    print(f"{'Дата':<14} {'Брут':^10} {'Авантюрист':^12} {'Консерватор':^12}")
    print(f"{'─'*50}")

    counts = {
        "A06": {"APPROVED": 0, "REJECTED": 0},
        "A07": {"APPROVED": 0, "REJECTED": 0},
        "A08": {"APPROVED": 0, "REJECTED": 0},
    }
    for row in all_verdicts:
        b  = row.get("A06", "—")
        av = row.get("A07", "—")
        c  = row.get("A08", "—")
        print(f"{row['date']:<14} {b:^10} {av:^12} {c:^12}")
        for wid, v in [("A06", b), ("A07", av), ("A08", c)]:
            if v in counts[wid]:
                counts[wid][v] += 1

    print(f"{'─'*50}")
    print(f"{'APPROVED':<14} "
          f"{counts['A06']['APPROVED']:^10} "
          f"{counts['A07']['APPROVED']:^12} "
          f"{counts['A08']['APPROVED']:^12}")
    print(f"{'REJECTED':<14} "
          f"{counts['A06']['REJECTED']:^10} "
          f"{counts['A07']['REJECTED']:^12} "
          f"{counts['A08']['REJECTED']:^12}")

    # ── PnL из Атласа ────────────────────────────────────────
    pnl = read_pnl_summary()
    if pnl:
        print(f"\n{'─'*50}")
        print(f"  PnL по закрытым позициям:")
        for trader, data in sorted(pnl.items()):
            print(f"  {trader}: "
                  f"сделок {data['closed']}, "
                  f"итого {data['total_r']:+.2f}R")

    print(f"\n{'═'*60}")
    print(f"  Атлас обновлён. ДНК изменена. Прогон завершён.")
    print(f"{'═'*60}\n")


if __name__ == "__main__":
    asyncio.run(main())
