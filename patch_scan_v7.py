"""
patch_scan_v7.py — убирает bdb_candidate из фильтра any_flag.
Проблема: bdb_candidate срабатывает на ~44% баров → 1888 сигналов.
Решение: в JSON пишем только bdb_strong + редкие события агентов.
"""
from pathlib import Path
import shutil, ast
from datetime import datetime

STAMP  = datetime.now().strftime("%Y%m%d_%H%M%S")
TARGET = Path(__file__).resolve().parent / "main.py"
if not TARGET.exists():
    print("[!] main.py не найден"); raise SystemExit(1)

txt = TARGET.read_text(encoding="utf-8")

OLD = """                # Только значимые бары
                any_flag = (
                    bdb_strong or bdb_candidate or alligator_wake
                    or fractal_outside or has_bell or confirmed
                    or panic_phase in ("FOMO", "LIQUIDATION")
                )
                if not any_flag:
                    continue"""

NEW = """                # Только значимые бары — bdb_candidate НЕ рисуется
                # (он контекст для агентов, не для индикатора)
                any_flag = (
                    bdb_strong or alligator_wake or fractal_outside
                    or has_bell or confirmed
                )
                if not any_flag:
                    continue"""

if OLD not in txt:
    print("[!] Строка не найдена. Покажи текущий any_flag в main.py.")
    idx = txt.find("any_flag")
    if idx >= 0:
        print(txt[idx:idx+300])
    raise SystemExit(1)

new_txt = txt.replace(OLD, NEW, 1)

try:
    ast.parse(new_txt)
    print("синтаксис: OK")
except SyntaxError as e:
    print(f"[!] СЛОМАН: {e}"); raise SystemExit(1)

bak = TARGET.with_name(TARGET.name + f".bak_{STAMP}")
shutil.copy2(TARGET, bak)
TARGET.write_text(new_txt, encoding="utf-8")
print(f"бэкап: {bak.name}")
print(f"✓ main.py — bdb_candidate убран из фильтра")
print()
print("Перезапусти студию. В консоли должно быть:")
print("  [MT5-BRIDGE] XAUUSD H4: N сигналов")
print("  N = единицы или несколько десятков — не сотни.")
