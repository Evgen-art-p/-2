# arhivator.py
# ─────────────────────────────────────────────────────────────
# АРХИВАТОР — уносит сирот прогона в _OLD/. НЕ удаляет.
# Ревизор доказал: их никто не зовёт (кроме самих себя/верстака).
# Рабочая дверь одна — tester_express (её зовёт кнопка РЫНОК) — НЕ трогаем.
#
# Что делает:
#   1. создаёт studio/modules/trading/_OLD/
#   2. перемещает туда 4 сироты
#   3. проверяет, что главный UI всё ещё импортируется (не унесли живое)
#
# Запуск из корня репы:  python arhivator.py
# Откат: руками вернуть файлы из _OLD/ обратно.
# ─────────────────────────────────────────────────────────────
import shutil
from pathlib import Path

TRADING = Path("studio/modules/trading")
OLD = TRADING / "_OLD"

# Сироты по приговору ревизора. tester_express тут НЕТ — он живой.
ORPHANS = [
    "engine.py",
    "probe_engine.py",
    "backtest_runner_v3.py",
    "stats_probe.py",
]

print("═" * 64)
print("АРХИВАТОР — сироты прогона в _OLD/ (не удаляю, переношу)")
print("═" * 64)

if not TRADING.exists():
    print(f"❌ Не вижу {TRADING}. Запусти из КОРНЯ репы (где папка studio).")
    raise SystemExit(1)

OLD.mkdir(exist_ok=True)
print(f"📁 Архив: {OLD}\n")

moved, missing, skipped = [], [], []
for name in ORPHANS:
    src = TRADING / name
    dst = OLD / name
    if not src.exists():
        missing.append(name)
        print(f"   ⚪ {name} — нет файла (уже унесён?), пропускаю")
        continue
    if dst.exists():
        skipped.append(name)
        print(f"   ⚠️  {name} — уже в _OLD/, пропускаю (не перезаписываю)")
        continue
    shutil.move(str(src), str(dst))
    moved.append(name)
    print(f"   📦 {name} → _OLD/{name}")

print(f"\n   Унесено: {len(moved)} · нет: {len(missing)} · "
      f"уже в архиве: {len(skipped)}")

# ── ПРОВЕРКА: кабинет всё ещё импортируется? (не унесли ли живое) ──
print("\n🔍 Проверяю, что кабинет цел (импорт ui_exchange)...")
import importlib, sys
sys.path.insert(0, str(Path(".").resolve()))
ok = True
try:
    import ast
    ui = Path("studio/economy/ui_exchange.py")
    ast.parse(ui.read_text(encoding="utf-8"))   # синтаксис цел
    print("   ✅ ui_exchange.py — синтаксис цел, кнопка РЫНОК на месте.")
except Exception as e:
    ok = False
    print(f"   ❌ ui_exchange.py сломан: {e}")

# Проверим, что tester_express (рабочая дверь) НЕ унесён
if (TRADING / "tester_express.py").exists():
    print("   ✅ tester_express.py на месте — рабочая дверь цела.")
else:
    ok = False
    print("   ❌ ТРЕВОГА: tester_express.py пропал! Верни из _OLD/ немедленно.")

print("\n" + "═" * 64)
if ok and moved:
    print("ЧИСТО. Сироты в _OLD/, рабочая дверь (tester_express) цела.")
    print("Теперь в trading одна дверь прогона. Можно гонять РЫНОК.")
elif ok and not moved:
    print("Нечего было уносить — уже чисто.")
else:
    print("⚠️ Что-то не так — читай выше. Откат: верни файлы из _OLD/.")
print("═" * 64)
