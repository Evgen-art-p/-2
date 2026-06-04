"""
patch_council_emoji.py — убирает аватары из плиток, везде эмодзи
"""
import shutil, subprocess
from pathlib import Path

DASHBOARD = Path("studio/economy/ui_dashboard.py")

OLD = '''                    with _tile:
                        if _ava:
                            _img_style = (
                                "width:44px;height:44px;border-radius:50%;"
                                "background-image:url('" + _ava + "');"
                                "background-size:cover;background-position:center;"
                                "margin-bottom:6px;border:2px solid " + _color + "44;"
                            )
                            ui.html("<div style='" + _img_style + "'></div>")
                        else:
                            ui.html("<div style='font-size:1.6rem;margin-bottom:4px;'>" + _emoji + "</div>")
                        _lbl_style = (
                            "font-family:JetBrains Mono;font-size:0.6rem;"
                            "color:" + _color + ";font-weight:600;text-align:center;"
                        )
                        ui.html("<div style='" + _lbl_style + "'>" + _label + "</div>")'''

NEW = '''                    with _tile:
                        ui.html("<div style='font-size:1.6rem;margin-bottom:4px;line-height:1;'>" + _emoji + "</div>")
                        _lbl_style = (
                            "font-family:JetBrains Mono;font-size:0.6rem;"
                            "color:" + _color + ";font-weight:600;text-align:center;"
                        )
                        ui.html("<div style='" + _lbl_style + "'>" + _label + "</div>")'''

src = DASHBOARD.read_text(encoding="utf-8")

if OLD not in src:
    print("❌ Блок не найден — ищем альтернативу")
    # Ищем любой if _ava блок
    if "if _ava:" in src:
        import re
        # Находим позицию
        idx = src.find("                    with _tile:")
        if idx != -1:
            print(f"  Нашли 'with _tile:' на позиции {idx}")
            snippet = src[idx:idx+600]
            print(f"  Контекст:\n{snippet[:300]}")
    else:
        print("  'if _ava:' не найден вообще")
else:
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
        print("↩ Бэкап восстановлен")
