"""
patch_hans_final.py — финальная правка _scan.

ТРИ изменения, основанные на замере частоты каждого флага на ядре:
  Ганс 99% → ПРОБОЙ фрактала (11%): цена пересекла на этом баре уровень
            фрактала, который был вне пасти. Удар, не координата.
  Паникёр 50% → убран из триггера: MFI на каждом баре, это раскраска.
  exit_bell 24% → убран из триггера записи: это раскраска выхода, не
            повод создавать бар. Пишется в бар если он значим иначе.

Остаются редкие: bdb_strong (0.1%), confirmed (1%), wake (0.1%), Ганс-пробой (11%).
panic_phase и exit_bell продолжают писаться в КАЖДЫЙ записанный сигнал
(для раскраски/контекста), но сами бар не создают.
"""
from pathlib import Path
import shutil, ast
from datetime import datetime

STAMP  = datetime.now().strftime("%Y%m%d_%H%M%S")
TARGET = Path(__file__).resolve().parent / "main.py"
if not TARGET.exists():
    print("[!] main.py не найден"); raise SystemExit(1)

txt = TARGET.read_text(encoding="utf-8")

# ── 1. Ганс: заменяем функцию на ПРОБОЙ ──────────────────────────────────
OLD_FN = '''        def _fractal_outside_jaw(md):
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

NEW_FN = '''        def _hans_breakout(md, window):
            """
            Ганс: ПРОБОЙ фрактала вне пасти (момент удара, не координата).
            LONG:  верхний фрактал был выше Jaw, и close пересёк его уровень
                   снизу вверх на этом баре (close[-2] < fp <= close[-1]).
            SHORT: нижний фрактал был ниже Jaw, close пересёк сверху вниз.
            Возвращает "LONG"/"SHORT"/None.
            Формирование фрактала — лишь координата. Сигнал рождается
            в момент пробоя: рынок принял решение, Волна 3 жива.
            """
            jaw = md.get("alligator", {}).get("jaw")
            if jaw is None or len(window) < 2:
                return None
            up   = md.get("fractals", {}).get("last_up")
            down = md.get("fractals", {}).get("last_down")
            c_prev = window[-2]["close"]
            c_cur  = window[-1]["close"]
            if up and up.get("price", 0) > jaw:
                fp = up["price"]
                if c_prev < fp <= c_cur:
                    return "LONG"
            if down and down.get("price", 0) < jaw:
                fp = down["price"]
                if c_prev > fp >= c_cur:
                    return "SHORT"
            return None'''

if OLD_FN not in txt:
    print("[!] _fractal_outside_jaw не найдена. Уже заменена?")
    raise SystemExit(1)
txt = txt.replace(OLD_FN, NEW_FN, 1)
print("    Ганс → _hans_breakout (пробой)")

# ── 2. Вызов Ганса в _scan ───────────────────────────────────────────────
OLD_CALL = '''                # ── Ганс: фрактал вне пасти (LONG/SHORT/None) ────────
                hans = _fractal_outside_jaw(md)
                fractal_outside = (hans is not None)'''
NEW_CALL = '''                # ── Ганс: ПРОБОЙ фрактала вне пасти ──────────────────
                hans = _hans_breakout(md, window)
                fractal_outside = (hans is not None)'''
if OLD_CALL not in txt:
    print("[!] вызов _fractal_outside_jaw в _scan не найден")
    raise SystemExit(1)
txt = txt.replace(OLD_CALL, NEW_CALL, 1)
print("    вызов Ганса обновлён")

# ── 3. any_flag: убираем Паникёра и exit_bell из триггера ───────────────
OLD_FLAG = '''                any_flag = (
                    bdb_strong or confirmed              # Искра
                    or alligator_wake                    # Морж
                    or fractal_outside                   # Ганс
                    or has_bell                          # Искра (выход)
                    or panic_phase in ("FOMO", "LIQUIDATION")  # Паникёр
                )'''
NEW_FLAG = '''                # Триггер записи — только РЕДКИЕ событийные сигналы.
                # exit_bell (24%) и panic_phase (50%) — раскраска, не повод
                # записи: они пишутся в бар если он значим по другой причине.
                any_flag = (
                    bdb_strong or confirmed              # Искра: Точка Ноль, подтверждение
                    or alligator_wake                    # Морж: проснулся
                    or fractal_outside                   # Ганс: пробой
                )'''
if OLD_FLAG not in txt:
    print("[!] any_flag не найден")
    raise SystemExit(1)
txt = txt.replace(OLD_FLAG, NEW_FLAG, 1)
print("    any_flag сужен (Паникёр и exit_bell — раскраска)")

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
print(" Ожидаемая частота на истории (по замеру на ядре):")
print("   bdb_strong  ~0.1%   Искра звезда")
print("   confirmed   ~1%     Искра кружок")
print("   wake        ~0.1%   Морж треугольник")
print("   Ганс пробой ~11%    Ганс ромб")
print("   Σ записей   ~12% баров — это уже сигналы, не каша.")
print()
print(" panic_phase / exit_bell — в каждом записанном сигнале,")
print(" индикатор раскрашивает их на тех барах что уже есть.")
print()
print(" Перезапусти студию. Жди [MT5-BRIDGE] N — около 200-250 на 2000.")
print("─" * 60)
