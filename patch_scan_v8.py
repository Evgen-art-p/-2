"""
patch_scan_v8.py — финальная чистка фильтра _scan.

Проблема (видна в живом JSON): бары попадают из-за alligator_wake /
fractal_outside / confirmed, которые на трендовом золоте срабатывают
постоянно. fractal_outside_jaw на падающем рынке = почти всегда true.

Решение: для ИСТОРИИ рисуем ТОЛЬКО bdb_strong (Точка Ноль, ~3-4/год).
Морж/Ганс/Паникёр/Трибунал — это работа живых агентов на КРАЮ графика,
не разметка истории. Их флаги остаются в JSON для информации, но НЕ
вызывают запись бара.

Запуск из корня студии:
  python patch_scan_v8.py
"""
from pathlib import Path
import shutil, ast
from datetime import datetime

STAMP  = datetime.now().strftime("%Y%m%d_%H%M%S")
TARGET = Path(__file__).resolve().parent / "main.py"
if not TARGET.exists():
    print("[!] main.py не найден"); raise SystemExit(1)

txt = TARGET.read_text(encoding="utf-8")

# ── 1. Чистим дубль _suppress ────────────────────────────────────────────
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

# ── 2. Фильтр: только bdb_strong ─────────────────────────────────────────
OLD_FILTER = '''                # Только значимые бары — bdb_candidate НЕ рисуется
                # (он контекст для агентов, не для индикатора)
                any_flag = (
                    bdb_strong or alligator_wake or fractal_outside
                    or has_bell or confirmed
                )
                if not any_flag:
                    continue'''

NEW_FILTER = '''                # ИСТОРИЯ: рисуем ТОЛЬКО bdb_strong — Точка Ноль (~3-4/год).
                # Морж/Ганс/Паникёр/confirmed работают на живом КРАЮ графика
                # (см. live_signal), а не размечают всю историю — на тренде
                # они срабатывают постоянно и дают кашу.
                if not bdb_strong:
                    continue'''

if OLD_FILTER not in txt:
    print("[!] Фильтр any_flag не найден. Покажи текущую версию.")
    raise SystemExit(1)

txt = txt.replace(OLD_FILTER, NEW_FILTER, 1)
print("    фильтр сужен до bdb_strong")

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
print(" Теперь в JSON попадают ТОЛЬКО bdb_strong бары.")
print(" Перезапусти студию. В консоли:")
print("   [MT5-BRIDGE] XAUUSD H4: N сигналов")
print(" N должно быть ОЧЕНЬ маленьким — единицы (3-4 на год истории).")
print(" Если N=0 — значит на текущих 2000 барах золота не было")
print(" идеальной Точки Ноль, это тоже честный результат.")
print("─" * 60)
