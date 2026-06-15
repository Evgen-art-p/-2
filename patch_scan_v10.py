"""
patch_scan_v10.py — ПОЛНАЯ замена функции _scan целиком.
Вырезает от 'def _scan(bars, symbol, timeframe):' до 'def _live_signal'
и вставляет чистую версию. Не зависит от текущего состояния тела.

Все агенты пишут свои флаги. Ганс уже исправлен (LONG/SHORT) — но на
случай если нет, _scan читает его напрямую через готовую функцию.
"""
from pathlib import Path
import shutil, ast
from datetime import datetime

STAMP  = datetime.now().strftime("%Y%m%d_%H%M%S")
TARGET = Path(__file__).resolve().parent / "main.py"
if not TARGET.exists():
    print("[!] main.py не найден"); raise SystemExit(1)

txt = TARGET.read_text(encoding="utf-8")

MARK_START = "        def _scan(bars, symbol, timeframe):"
MARK_END   = "        def _live_signal(bars, symbol, timeframe):"

i_start = txt.find(MARK_START)
i_end   = txt.find(MARK_END)
if i_start < 0 or i_end < 0 or i_end <= i_start:
    print("[!] Границы _scan не найдены."); raise SystemExit(1)

# Что между ними — выкидываем целиком, ставим новую функцию + пустые строки
NEW_SCAN = '''        def _scan(bars, symbol, timeframe):
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
                confirmed = bool(
                    ao.get("crossed_zero") and ao.get("zero_dir") == "UP"
                )

                # ── Морж: только что проснулся ───────────────────────
                alligator_wake = (not sleeping and prev_sleeping)

                # ── Ганс: фрактал вне пасти (LONG/SHORT/None) ────────
                hans = _fractal_outside_jaw(md)
                fractal_outside = (hans is not None)

                # ── Паникёр: фаза по MFI ─────────────────────────────
                mfi_type = md.get("mfi", {}).get("type", "")
                panic_phase = (
                    "LIQUIDATION" if mfi_type == "SQUAT" else
                    "FOMO"        if mfi_type == "GREEN" else
                    "DISBELIEF"   if mfi_type == "FADE"  else
                    "NEUTRAL"
                )

                prev_sleeping = sleeping

                # Значимый бар = есть хоть один сигнал любого агента.
                # bdb_candidate сам по себе НЕ триггерит (он на ~44% баров).
                any_flag = (
                    bdb_strong or confirmed              # Искра
                    or alligator_wake                    # Морж
                    or fractal_outside                   # Ганс
                    or has_bell                          # Искра (выход)
                    or panic_phase in ("FOMO", "LIQUIDATION")  # Паникёр
                )
                if not any_flag:
                    continue

                entry_price = None
                stop_price  = None
                if bdb_strong:
                    entry_price = round(bars[i]["high"] + point, 6)
                    stop_price  = round(bars[i]["low"]  - point, 6)

                signals.append({
                    "date":                bars[i]["date"],
                    "bar_index":           i,
                    # Искра
                    "bdb_strong":          bdb_strong,
                    "bdb_candidate":       bdb_candidate,
                    "bdb_direction":       direction,
                    "confirmed":           confirmed,
                    # Морж
                    "alligator_wake":      alligator_wake,
                    "alligator_sleeping":  sleeping,
                    # Ганс
                    "fractal_outside_jaw": fractal_outside,
                    "hans_direction":      hans,
                    # Паникёр
                    "panic_phase":         panic_phase,
                    # Выход
                    "exit_bell":           has_bell,
                    # Цены
                    "entry_price":         entry_price,
                    "stop_price":          stop_price,
                })
            return signals

'''

new_txt = txt[:i_start] + NEW_SCAN + txt[i_end:]

# Гарантируем что _fractal_outside_jaw возвращает LONG/SHORT/None.
# Если в файле осталась старая булева версия — заменим её.
OLD_FN_BOOL = '''        def _fractal_outside_jaw(md):
            jaw  = md.get("alligator", {}).get("jaw")
            frac = md.get("fractals",  {}).get("last_down")
            if jaw is None or frac is None: return False
            return frac.get("price", 0) < jaw'''
NEW_FN_DIR = '''        def _fractal_outside_jaw(md):
            """Фрактал вне пасти: LONG если верхний выше Jaw, SHORT если нижний ниже."""
            jaw  = md.get("alligator", {}).get("jaw")
            up   = md.get("fractals", {}).get("last_up")
            down = md.get("fractals", {}).get("last_down")
            if jaw is None:
                return None
            if up   and up.get("price", 0)   > jaw:
                return "LONG"
            if down and down.get("price", 0) < jaw:
                return "SHORT"
            return None'''
if OLD_FN_BOOL in new_txt:
    new_txt = new_txt.replace(OLD_FN_BOOL, NEW_FN_DIR, 1)
    print("    _fractal_outside_jaw: булева версия заменена на LONG/SHORT")
elif 'return "LONG"' in new_txt:
    print("    _fractal_outside_jaw уже в версии LONG/SHORT — ок")

# Проверка: вдруг остался дубль булевой функции (с другим отступом тела)
import re
# подчистим возможный «осиротевший» старый кусок тела (маловероятно, но проверим синтаксис)

try:
    ast.parse(new_txt)
    print("    синтаксис: OK")
except SyntaxError as e:
    print(f"[!] СЛОМАН: {e}")
    # покажем окрестность
    lines = new_txt.splitlines()
    ln = e.lineno or 1
    for k in range(max(0, ln-4), min(len(lines), ln+3)):
        print(f"   {k+1}: {lines[k]}")
    raise SystemExit(1)

bak = TARGET.with_name(TARGET.name + f".bak_{STAMP}")
shutil.copy2(TARGET, bak)
TARGET.write_text(new_txt, encoding="utf-8")
print(f"    бэкап: {bak.name}")
print(f"    ✓ main.py — _scan переписан целиком, все агенты на месте")
print()
print(" Перезапусти студию. Жди [MT5-BRIDGE] N сигналов.")
print(" Потом индикатор v10 в MT5 — каждый агент своя форма.")
