# revizor.py
# ─────────────────────────────────────────────────────────────
# РЕВИЗОР — кто кого зовёт?
# Только ЧИТАЕТ всю репу. Ничего не меняет, не сносит.
# Для каждого подозреваемого файла прогона считает: дёргает ли его
# хоть кто-то ЖИВОЙ — или он лежит мёртвым грузом (сирота).
#
# Запуск из корня репы:  python revizor.py
# ─────────────────────────────────────────────────────────────
import re
from pathlib import Path

ROOT = Path(".")

# Подозреваемые — файлы прогона истории. Имя модуля = по чему ищем import/зов.
SUSPECTS = {
    "tester_express":    "studio/modules/trading/tester_express.py",
    "engine":            "studio/modules/trading/engine.py",
    "backtest_runner_v3":"studio/modules/trading/backtest_runner_v3.py",
    "probe_engine":      "studio/modules/trading/probe_engine.py",
    "stats_probe":       "studio/modules/trading/stats_probe.py",
}

# Папки, которые НЕ считаем (мусор, кэш, бэкапы, история git)
SKIP_DIRS = {".git", "__pycache__", "node_modules", ".venv", "venv"}

def is_backup(p: Path) -> bool:
    s = p.name
    return (".bak" in s) or s.endswith("~") or "_OLD" in s or "_old" in s

def all_py_files():
    for p in ROOT.rglob("*.py"):
        if any(part in SKIP_DIRS for part in p.parts):
            continue
        if is_backup(p):
            continue
        yield p

print("═" * 68)
print("РЕВИЗОР — кто зовёт файлы прогона истории")
print("═" * 68)

files = list(all_py_files())
print(f"Просканировано живых .py файлов: {len(files)}")
print(f"(бэкапы .bak и __pycache__ пропущены)\n")

for mod, selfpath in SUSPECTS.items():
    self_p = Path(selfpath)
    exists = self_p.exists()
    # Кто упоминает этот модуль: import ... mod  /  from ...mod import  /  mod.func(
    # Ищем имя модуля как отдельное слово рядом с import или с точкой-вызовом.
    pat_import = re.compile(rf"\b{re.escape(mod)}\b")
    callers = []
    for p in files:
        if p.resolve() == self_p.resolve():
            continue  # сам себя не считаем
        try:
            txt = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        # строки, где встречается имя модуля
        hits = [ln.strip() for ln in txt.splitlines()
                if pat_import.search(ln)
                and ("import" in ln or f"{mod}." in ln or f"{mod}(" in ln)]
        if hits:
            callers.append((str(p), hits[:3]))  # до 3 строк-улик

    print("─" * 68)
    status_file = "✅ есть" if exists else "❌ НЕТ ФАЙЛА"
    print(f"📄 {mod}.py   [{status_file}]")
    if not callers:
        print("   🪦 СИРОТА — НИКТО не зовёт. Мёртвый груз, можно в архив.")
    else:
        print(f"   🔌 ЖИВОЙ — зовут {len(callers)} файл(ов):")
        for path, hits in callers:
            print(f"      • {path}")
            for h in hits:
                print(f"          └ {h[:90]}")
    print()

print("═" * 68)
print("ЧИТАЙ ТАК:")
print("  🪦 СИРОТА → никто не дёргает → в архив смело (наследил прошлый Брат).")
print("  🔌 ЖИВОЙ  → дёргает кабинет/кнопка → оставляем, это рабочая дверь.")
print("  Решает ШЕФ. Ревизор только показал правду, не тронул ничего.")
print("═" * 68)
