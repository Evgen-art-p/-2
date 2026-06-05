"""
patch_council_ids.py
====================
Исправляет ID резидентов в ui_dashboard.py:
  007_KEI  → 008_KEI
  008_JUST → 009_JUST

Запуск: python patch_council_ids.py
"""

import shutil, subprocess
from pathlib import Path

DASHBOARD = Path("studio/economy/ui_dashboard.py")

bak = DASHBOARD.with_suffix(".py.bak_ids")
shutil.copy2(DASHBOARD, bak)
print(f"📦 Бэкап: {bak}")

src = DASHBOARD.read_text(encoding="utf-8")

before = src.count("007_KEI") + src.count("008_JUST")

src = src.replace("007_KEI", "008_KEI")
src = src.replace("008_JUST", "009_JUST")

after = src.count("008_KEI") + src.count("009_JUST")

DASHBOARD.write_text(src, encoding="utf-8")
print(f"✅ Заменено вхождений: {before} → теперь 008_KEI и 009_JUST")

r = subprocess.run(["python", "-m", "py_compile", str(DASHBOARD)], capture_output=True, text=True)
if r.returncode == 0:
    print("✅ Синтаксис OK — перезапусти студию")
else:
    print(f"❌ {r.stderr}")
    shutil.copy2(bak, DASHBOARD)
    print("↩ Бэкап восстановлен")
