"""
patch_scan_v5.py — переписывает _scan() в main.py.

Ядро (williams_core.py) уже считает divergent_bar.bdb_strong.
Мост должен читать это поле, а не старую divergence_ao.

БЫЛО: читаем divergence_ao (шум) → 1961 сигнал
СТАЛО: читаем divergent_bar.bdb_strong → единицы в год

Запуск из корня студии:
  python patch_scan_v5.py
"""

from pathlib import Path
import shutil, ast
from datetime import datetime

STAMP  = datetime.now().strftime("%Y%m%d_%H%M%S")
TARGET = Path(__file__).resolve().parent / "main.py"
if not TARGET.exists():
    print("[!] main.py не найден"); raise SystemExit(1)

txt = TARGET.read_text(encoding="utf-8")

# ── Точный матч старого _scan ──────────────────────────────────────────
OLD = '''        def _scan(bars, symbol, timeframe):
            point = get_point(symbol)
            signals = []
            for i in range(40, len(bars)):
                window = bars[max(0, i-199):i+1]
                import io, sys as _sys
                _old = _sys.stdout
                _sys.stdout = io.StringIO()
                try:
                    md = build_market_data(window, symbol=symbol, timeframe=timeframe, point=point)
                finally:
                    _sys.stdout = _old
                if not md:
                    continue
                has_div  = bool(md.get("divergence_ao"))
                has_bell = bool(md.get("exit_bell"))
                has_sq   = bool(md.get("squat", {}).get("last_squat"))
                sleeping = bool(md.get("alligator", {}).get("sleeping"))
                if not (has_div or has_bell or has_sq):
                    continue
                entry_price = None
                stop_price  = None
                if has_div and not sleeping:
                    sq = md.get("squat", {}).get("last_squat")
                    if sq:
                        entry_price = round(sq["high"] + point, 6)
                        if i >= 1:
                            stop_price = round(bars[i-1]["low"] - point, 6)
                signals.append({
                    "date":               bars[i]["date"],
                    "bar_index":          i,
                    "divergence":         has_div,
                    "exit_bell":          has_bell,
                    "squat":              has_sq,
                    "alligator_sleeping": sleeping,
                    "ao_confirmed":       bool(md.get("ao", {}).get("crossed_zero")),
                    "entry_price":        entry_price,
                    "stop_price":         stop_price,
                })
            return signals'''

NEW = '''        def _suppress(fn, *a, **kw):
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

                # ── Искра: только bdb_strong — Точка Ноль, ~3-4 в год ──
                bdb_strong    = bool(db.get("bdb_strong"))
                bdb_candidate = bool(db.get("bdb_candidate"))
                direction     = db.get("direction")

                # ── Морж: аллигатор только что проснулся ──────────────
                alligator_wake = (not sleeping and prev_sleeping)

                # ── Ганс: фрактал ниже Jaw ────────────────────────────
                jaw  = md.get("alligator", {}).get("jaw")
                frac = md.get("fractals",  {}).get("last_down")
                fractal_outside = bool(
                    jaw and frac and frac.get("price", 0) < jaw
                )

                # ── Паникёр: фаза по MFI ─────────────────────────────
                mfi_type = md.get("mfi", {}).get("type", "")
                panic_phase = (
                    "LIQUIDATION" if mfi_type == "SQUAT" else
                    "FOMO"        if mfi_type == "GREEN" else
                    "DISBELIEF"   if mfi_type == "FADE"  else
                    "NEUTRAL"
                )

                # ── Искра confirmed: AO пересёк ноль вверх ───────────
                ao = md.get("ao", {})
                confirmed = bool(
                    ao.get("crossed_zero") and ao.get("zero_dir") == "UP"
                )

                prev_sleeping = sleeping

                # Пишем только значимые бары
                any_flag = (
                    bdb_strong or alligator_wake or fractal_outside
                    or has_bell or confirmed
                    or panic_phase in ("FOMO", "LIQUIDATION")
                )
                if not any_flag:
                    continue

                # Цена входа — только по bdb_strong (Авантюрист входит на BuDB)
                entry_price = None
                stop_price  = None
                if bdb_strong:
                    entry_price = round(bars[i]["high"] + point, 6)
                    # стоп — за лоу волны 2 (текущий бар = BuDB = дно)
                    stop_price = round(bars[i]["low"] - point, 6)

                signals.append({
                    "date":                bars[i]["date"],
                    "bar_index":           i,
                    # ── Искра ──────────────────────────────────
                    "bdb_strong":          bdb_strong,      # звезда (главный)
                    "bdb_candidate":       bdb_candidate,   # кружок (слабый)
                    "bdb_direction":       direction,
                    "confirmed":           confirmed,        # AO пересёк ноль
                    # ── Морж ───────────────────────────────────
                    "alligator_wake":      alligator_wake,
                    "alligator_sleeping":  sleeping,
                    # ── Ганс ───────────────────────────────────
                    "fractal_outside_jaw": fractal_outside,
                    # ── Паникёр ────────────────────────────────
                    "panic_phase":         panic_phase,
                    # ── Выход ──────────────────────────────────
                    "exit_bell":           has_bell,
                    # ── Цены ───────────────────────────────────
                    "entry_price":         entry_price,
                    "stop_price":          stop_price,
                })
            return signals'''

if OLD not in txt:
    print("[!] Старый _scan не найден точно.")
    if "ao_confirmed" in txt:
        print("    Попробуй накатить patch_main_bridge_v4.py сначала.")
    raise SystemExit(1)

new_txt = txt.replace(OLD, NEW, 1)

try:
    ast.parse(new_txt)
    print("синтаксис: OK")
except SyntaxError as e:
    print(f"[!] СИНТАКСИС СЛОМАН: {e}"); raise SystemExit(1)

bak = TARGET.with_name(TARGET.name + f".bak_{STAMP}")
shutil.copy2(TARGET, bak)
TARGET.write_text(new_txt, encoding="utf-8")
print(f"бэкап: {bak.name}")
print(f"✓ main.py обновлён")
print()
print("─" * 60)
print(" Мост теперь читает divergent_bar.bdb_strong из ядра.")
print(" В JSON попадают только значимые бары:")
print("   bdb_strong=true     — Точка Ноль (~3-4 в год)")
print("   bdb_candidate=true  — кандидат (контекст)")
print("   alligator_wake      — Морж")
print("   fractal_outside_jaw — Ганс")
print("   confirmed           — AO пересёк ноль (Искра ★)")
print("   exit_bell           — конец импульса")
print("   panic_phase         — FOMO/LIQUIDATION/DISBELIEF")
print()
print(" Перезапусти студию → мост пересчитает JSON.")
print(" Перегрузи AI_Tribunal_v8 в MT5.")
print("─" * 60)
