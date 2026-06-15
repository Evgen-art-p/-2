"""
patch_scan_v6.py — заменяет _scan() в main.py.
Целевая версия: та что сейчас в репе (машина состояний из patch_main_bridge_v4).
Новая логика: читаем divergent_bar.bdb_strong из ядра.
"""
from pathlib import Path
import shutil, ast
from datetime import datetime

STAMP  = datetime.now().strftime("%Y%m%d_%H%M%S")
TARGET = Path(__file__).resolve().parent / "main.py"
if not TARGET.exists():
    print("[!] main.py не найден"); raise SystemExit(1)

txt = TARGET.read_text(encoding="utf-8")

# Якорь — уникальная строка которая точно есть в текущей версии
ANCHOR_START = "        def _scan(bars, symbol, timeframe):\n            point = get_point(symbol)\n            signals   = []\n\n            # ── Машина состояний Искры"
ANCHOR_END   = "            return signals"

if ANCHOR_START not in txt:
    print("[!] Якорь не найден. Версия main.py не та.")
    print("Ищу что есть в _scan...")
    idx = txt.find("def _scan(bars, symbol, timeframe):")
    if idx >= 0:
        print(txt[idx:idx+300])
    raise SystemExit(1)

# Вырезаем весь _scan от якоря до первого return signals
start = txt.find(ANCHOR_START)
end   = txt.find(ANCHOR_END, start) + len(ANCHOR_END)

OLD_SCAN = txt[start:end]

NEW_SCAN = '''        def _suppress(fn, *a, **kw):
            import io, sys as _s
            old = _s.stdout; _s.stdout = io.StringIO()
            try:    return fn(*a, **kw)
            finally: _s.stdout = old

        def _scan(bars, symbol, timeframe):
            point   = get_point(symbol)
            signals = []
            prev_sleeping = True

            for i in range(40, len(bars)):
                window = bars[max(0, i - 199):i + 1]
                md = _suppress(build_market_data, window,
                               symbol=symbol, timeframe=timeframe, point=point)
                if not md:
                    continue

                db       = md.get("divergent_bar", {})
                sleeping = bool(md.get("alligator", {}).get("sleeping", True))
                has_bell = bool(md.get("exit_bell"))
                ao       = md.get("ao", {})

                # ── Искра ─────────────────────────────────────────────
                bdb_strong    = bool(db.get("bdb_strong"))
                bdb_candidate = bool(db.get("bdb_candidate"))
                direction     = db.get("direction")
                # AO пересёк ноль снизу вверх — CONFIRMED (звезда)
                confirmed = bool(
                    ao.get("crossed_zero") and ao.get("zero_dir") == "UP"
                )

                # ── Морж: аллигатор только что проснулся ──────────────
                alligator_wake = (not sleeping and prev_sleeping)

                # ── Ганс: фрактал ниже Jaw ────────────────────────────
                jaw  = md.get("alligator", {}).get("jaw")
                frac = md.get("fractals",  {}).get("last_down")
                fractal_outside = bool(jaw and frac and frac.get("price", 0) < jaw)

                # ── Паникёр: фаза по MFI ─────────────────────────────
                mfi_type = md.get("mfi", {}).get("type", "")
                panic_phase = (
                    "LIQUIDATION" if mfi_type == "SQUAT" else
                    "FOMO"        if mfi_type == "GREEN" else
                    "DISBELIEF"   if mfi_type == "FADE"  else
                    "NEUTRAL"
                )

                prev_sleeping = sleeping

                # Только значимые бары
                any_flag = (
                    bdb_strong or bdb_candidate or alligator_wake
                    or fractal_outside or has_bell or confirmed
                    or panic_phase in ("FOMO", "LIQUIDATION")
                )
                if not any_flag:
                    continue

                # Цена входа — только по bdb_strong
                entry_price = None
                stop_price  = None
                if bdb_strong:
                    entry_price = round(bars[i]["high"] + point, 6)
                    stop_price  = round(bars[i]["low"]  - point, 6)

                signals.append({
                    "date":                bars[i]["date"],
                    "bar_index":           i,
                    "bdb_strong":          bdb_strong,
                    "bdb_candidate":       bdb_candidate,
                    "bdb_direction":       direction,
                    "confirmed":           confirmed,
                    "alligator_wake":      alligator_wake,
                    "alligator_sleeping":  sleeping,
                    "fractal_outside_jaw": fractal_outside,
                    "panic_phase":         panic_phase,
                    "exit_bell":           has_bell,
                    "entry_price":         entry_price,
                    "stop_price":          stop_price,
                })
            return signals'''

new_txt = txt[:start] + NEW_SCAN + txt[end:]

try:
    ast.parse(new_txt)
    print("синтаксис: OK")
except SyntaxError as e:
    print(f"[!] СИНТАКСИС СЛОМАН: {e}"); raise SystemExit(1)

bak = TARGET.with_name(TARGET.name + f".bak_{STAMP}")
shutil.copy2(TARGET, bak)
TARGET.write_text(new_txt, encoding="utf-8")
print(f"бэкап: {bak.name}")
print(f"✓ main.py обновлён — мост теперь читает divergent_bar.bdb_strong")
print()
print("Перезапусти студию. Жди в консоли:")
print("  [MT5-BRIDGE] XAUUSD H4: N сигналов")
print("N должно быть маленьким (единицы-десятки, не тысячи).")
