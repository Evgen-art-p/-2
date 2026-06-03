"""
patch_city_traces.py
====================
1. Копирует studio/city_traces.py
2. Добавляет вызов maybe_run_traces() в morning_checkout.py
"""
import shutil, sys
from pathlib import Path

CHECKOUT = Path("studio/morning_checkout.py")
ok = 0
err = 0

def patch(path, old, new, label):
    global ok, err
    text = path.read_text(encoding="utf-8")
    if old not in text: print(f"  MISS [{label}]"); err += 1; return
    if new.strip() in text: print(f"  SKIP [{label}]"); ok += 1; return
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    print(f"  OK   [{label}]"); ok += 1

print("\n=== patch_city_traces.py ===\n")
print(f"{CHECKOUT.name}:")

_old = '    # 🌱 Финч обходит сад каждое утро\n    try:\n        from studio.garden_tools import finch_morning\n        finch_morning(on_progress=on_progress)\n    except Exception as e:\n        print(f"[CHECKOUT] ⚠ Финч не смог обойти сад: {e}")'

_new = '    # 🌱 Финч обходит сад каждое утро\n    try:\n        from studio.garden_tools import finch_morning\n        finch_morning(on_progress=on_progress)\n    except Exception as e:\n        print(f"[CHECKOUT] ⚠ Финч не смог обойти сад: {e}")\n\n    # 📊 Следы города — Слой 2 (раз в сутки, если пульс обновился)\n    try:\n        from studio.city_traces import maybe_run_traces\n        maybe_run_traces(last_n_days=30)\n    except Exception as e:\n        print(f"[CHECKOUT] ⚠ city_traces: {e}")'

patch(CHECKOUT, _old, _new, "maybe_run_traces после Финча")

print(f"\n{chr(61)*55}")
print(f"Готово. {ok} патчей применено, {err} ошибок.")
if err == 0:
    print("""
Что изменилось:
  studio/city_traces.py   — Слой 2, паттерны из пульса
  morning_checkout.py     — maybe_run_traces() каждое утро

Commit:
  feat: city_traces.py — Слой 2, паттерны из пульса города
""")
else:
    sys.exit(1)