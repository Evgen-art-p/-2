"""
patch_scan_v9.py — возвращаем ВСЕХ агентов в разметку истории.
Каждый пишет свой флаг честно. Чиним кривое условие Ганса.

Искра:   bdb_strong (Точка Ноль) + bdb_candidate (кружок) + confirmed (звезда)
Морж:    alligator_wake (проснулся)
Ганс:    fractal_outside_jaw — ПРАВИЛЬНО: верхний фрактал ВЫШЕ Jaw (лонг)
                              или нижний фрактал НИЖЕ Jaw (шорт), по направлению
Паникёр: panic_phase (FOMO/LIQUIDATION/DISBELIEF)

Фильтр: пишем бар если есть ХОТЬ ОДИН значимый флаг.
Каждый агент = свой буфер в индикаторе = своя форма.
"""
from pathlib import Path
import shutil, ast
from datetime import datetime

STAMP  = datetime.now().strftime("%Y%m%d_%H%M%S")
TARGET = Path(__file__).resolve().parent / "main.py"
if not TARGET.exists():
    print("[!] main.py не найден"); raise SystemExit(1)

txt = TARGET.read_text(encoding="utf-8")

# ── 1. Чистим дубль _suppress (если ещё есть) ────────────────────────────
DUP = '''        def _suppress(fn, *a, **kw):
            """Вызывает fn без вывода в stdout."""
            import io, sys as _s
            old = _s.stdout; _s.stdout = io.StringIO()
            try:    return fn(*a, **kw)
            finally: _s.stdout = old

        def _suppress(fn, *a, **kw):
            import io, sys as _s
            old = _s.stdout; _s.stdout = io.StringIO()
            try:    return fn(*a, **kw)
            finally: _s.stdout = old'''
SINGLE = '''        def _suppress(fn, *a, **kw):
            import io, sys as _s
            old = _s.stdout; _s.stdout = io.StringIO()
            try:    return fn(*a, **kw)
            finally: _s.stdout = old'''
if DUP in txt:
    txt = txt.replace(DUP, SINGLE, 1)
    print("    дубль _suppress убран")

# ── 2. Чиним кривую функцию _fractal_outside_jaw ────────────────────────
OLD_FN = '''        def _fractal_outside_jaw(md):
            jaw  = md.get("alligator", {}).get("jaw")
            frac = md.get("fractals",  {}).get("last_down")
            if jaw is None or frac is None: return False
            return frac.get("price", 0) < jaw'''
NEW_FN = '''        def _fractal_outside_jaw(md):
            """
            Фрактал ВНЕ пасти по Вильямсу — сигнал Ганса (ВТОРОЙ вход).
            LONG:  верхний фрактал ВЫШЕ Jaw (рынок пробил пасть вверх).
            SHORT: нижний  фрактал НИЖЕ Jaw (пробил вниз).
            Возвращает "LONG" / "SHORT" / None.
            """
            jaw   = md.get("alligator", {}).get("jaw")
            up    = md.get("fractals", {}).get("last_up")
            down  = md.get("fractals", {}).get("last_down")
            if jaw is None:
                return None
            if up   and up.get("price", 0)   > jaw:
                return "LONG"
            if down and down.get("price", 0) < jaw:
                return "SHORT"
            return None'''
if OLD_FN in txt:
    txt = txt.replace(OLD_FN, NEW_FN, 1)
    print("    _fractal_outside_jaw исправлена (LONG/SHORT по направлению)")

# ── 3. Переписываем тело _scan: все флаги + правильный фильтр ────────────
# Находим блок от "# ── Ганс" до конца signals.append
OLD_SCAN_BODY = '''                # ── Ганс: фрактал ниже Jaw ────────────────────────────
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

                # Только значимые бары — bdb_candidate НЕ рисуется
                # (он контекст для агентов, не для индикатора)
                any_flag = (
                    bdb_strong or alligator_wake or fractal_outside
                    or has_bell or confirmed
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
                })'''

NEW_SCAN_BODY = '''                # ── Ганс: фрактал вне пасти (LONG/SHORT/None) ────────
                hans = _fractal_outside_jaw(md)   # "LONG" / "SHORT" / None
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
                # bdb_candidate НЕ триггерит запись (он на 44% баров),
                # но если бар записан по другой причине — его значение
                # пишется как есть, для контекста.
                any_flag = (
                    bdb_strong or confirmed              # Искра
                    or alligator_wake                    # Морж
                    or fractal_outside                   # Ганс
                    or has_bell                          # Искра (выход)
                    or panic_phase in ("FOMO", "LIQUIDATION")  # Паникёр
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
                })'''

if OLD_SCAN_BODY not in txt:
    print("[!] Тело _scan не найдено точно.")
    raise SystemExit(1)

txt = txt.replace(OLD_SCAN_BODY, NEW_SCAN_BODY, 1)
print("    тело _scan переписано — все агенты пишут свои флаги")

try:
    ast.parse(txt)
    print("    синтаксис: OK")
except SyntaxError as e:
    print(f"[!] СЛОМАН: {e}"); raise SystemExit(1)

bak = TARGET.with_name(TARGET.name + f".bak_{STAMP}")
shutil.copy2(TARGET, bak)
TARGET.write_text(txt, encoding="utf-8")
print(f"    бэкап: {bak.name}")
print(f"    ✓ main.py обновлён")
print()
print("─" * 60)
print(" Все агенты вернулись в разметку. Каждый — свой флаг.")
print(" Ганс теперь правильный: фрактал ВЫШЕ Jaw (long) / НИЖЕ (short).")
print(" Перезапусти студию, смотри [MT5-BRIDGE] N сигналов.")
print(" Дальше дам индикатор v10 — каждый агент свой символ/форма.")
print("─" * 60)
