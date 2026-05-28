#!/usr/bin/env python3
"""
patch_fix_empty_night.py
Добавляет "все спят 💤" в пустую ночную карточку отчёта.
"""
from pathlib import Path
from datetime import datetime

UI = Path("studio/cabinet/ui_cabinet.py")
code = UI.read_text(encoding="utf-8")
backup = UI.with_suffix(".py.bak_empty_night")
backup.write_text(code, encoding="utf-8")
print(f"Бэкап: {backup.name}")

OLD = """                            if restless_d:
                                ui.html(
                                    f\'<div style="font-family:JetBrains Mono;\'
                                    f\'font-size:0.55rem;color:rgba(200,180,80,0.6);\'
                                    f\'margin-top:3px;">\'
                                    f\'<b>😰 Тревожный сон ({len(restless_d)})</b><br>\'
                                    + ", ".join(restless_d[:10])
                                    + "</div>"
                                )"""

NEW = """                            if restless_d:
                                ui.html(
                                    f\'<div style="font-family:JetBrains Mono;\'
                                    f\'font-size:0.55rem;color:rgba(200,180,80,0.6);\'
                                    f\'margin-top:3px;">\'
                                    f\'<b>😰 Тревожный сон ({len(restless_d)})</b><br>\'
                                    + ", ".join(restless_d[:10])
                                    + "</div>"
                                )
                            if not revolts_d and not resentful_d and not restless_d:
                                ui.html(
                                    \'<div style="font-family:JetBrains Mono;\'
                                    \'font-size:0.55rem;color:rgba(140,150,180,0.25);\'
                                    \'padding-top:8px;text-align:center;">\'
                                    \'все спят 💤 — город спокоен\'
                                    \'</div>\'
                                )"""

if OLD in code:
    code = code.replace(OLD, NEW, 1)
    UI.write_text(code, encoding="utf-8")
    print("✅ Готово. Перезапусти студию.")
else:
    print("⚠ Якорь не найден — возможно карточки уже изменились")
    print("  Добавь вручную после блока 'if restless_d:' в _render_reports_tab:")
    print("""
    if not revolts_d and not resentful_d and not restless_d:
        ui.html(
            '<div style="font-family:JetBrains Mono;'
            'font-size:0.55rem;color:rgba(140,150,180,0.25);'
            'padding-top:8px;text-align:center;">'
            'все спят 💤 — город спокоен'
            '</div>'
        )
""")
