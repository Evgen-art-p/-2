"""
patch_council_emoji.py
Убирает аватары из плиток — везде эмодзи.
Заодно фиксит сломанный url() с кавычками.
"""
import shutil, subprocess
from pathlib import Path

DASHBOARD = Path("studio/economy/ui_dashboard.py")

OLD = '''                        if _ava:
                            ui.html(
                                "<div style='width:40px;height:40px;border-radius:50%;"
                                "background-image:url("" + _ava + "");"
                                "background-size:cover;background-position:center;"
                                "margin-bottom:5px;flex-shrink:0;'></div>"
                            )
                        else:
                            ui.html(
                                "<div style='font-size:1.5rem;margin-bottom:5px;"
                                "line-height:1;'>" + _emoji + "</div>"
                            )'''

NEW = '''                        ui.html(
                                "<div style='font-size:1.6rem;margin-bottom:5px;"
                                "line-height:1;'>" + _emoji + "</div>"
                            )'''

src = DASHBOARD.read_text(encoding="utf-8")
if OLD in src:
    bak = DASHBOARD.with_suffix(".py.bak6")
    shutil.copy2(DASHBOARD, bak)
    src = src.replace(OLD, NEW)
    DASHBOARD.write_text(src, encoding="utf-8")
    r = subprocess.run(["python", "-m", "py_compile", str(DASHBOARD)], capture_output=True, text=True)
    if r.returncode == 0:
        print("✅ Готово — эмодзи на всех плитках. Перезапусти студию.")
    else:
        print(f"❌ {r.stderr}")
        shutil.copy2(bak, DASHBOARD)
        print("↩ Бэкап")
else:
    print("❌ Блок не найден")
    # Показываем что реально в файле вместо if _ava
    idx = src.find("if _ava:")
    if idx != -1:
        print(f"Найден 'if _ava:' на позиции {idx}, контекст:")
        print(repr(src[idx-100:idx+400]))
    else:
        print("'if _ava:' вообще не найден в файле")
