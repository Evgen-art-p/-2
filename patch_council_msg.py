"""
patch_council_msg.py
====================
Убирает render_council_grid() из обработчика клика на плитку.
Это убивает council_chat_el после каждого клика.

Запуск: python patch_council_msg.py
"""
import shutil, subprocess
from pathlib import Path

DASHBOARD = Path("studio/economy/ui_dashboard.py")

OLD = '''                    ).on("click", lambda _, r=_res: (
                        select_council_resident(r),
                        render_council_grid(),
                    )):'''

NEW = '''                    ).on("click", lambda _, r=_res: (
                        select_council_resident(r),
                    )):'''

src = DASHBOARD.read_text(encoding="utf-8")

if OLD in src:
    bak = DASHBOARD.with_suffix(".py.bak_msg3")
    shutil.copy2(DASHBOARD, bak)
    src = src.replace(OLD, NEW)
    DASHBOARD.write_text(src, encoding="utf-8")
    r = subprocess.run(["python", "-m", "py_compile", str(DASHBOARD)], capture_output=True, text=True)
    if r.returncode == 0:
        print("✅ Готово — перезапусти студию")
    else:
        print(f"❌ {r.stderr}")
        shutil.copy2(bak, DASHBOARD)
        print("↩ Бэкап")
else:
    print("❌ Маркер не найден")
    idx = src.find("render_council_grid(),")
    if idx != -1:
        print(f"Найден на позиции {idx}:")
        print(repr(src[idx-100:idx+100]))
    else:
        print("render_council_grid() в обработчике не найден вообще")
