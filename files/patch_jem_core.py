#!/usr/bin/env python3
"""
Патч для knowledge/jem_core.md
Добавляет условие: контент-план ТОЛЬКО для social_mix
Добавляет правило: не переключай цеха

Запуск из корня проекта:
    python patch_jem_core.py
"""

import shutil
from pathlib import Path
import sys

FILE = Path("knowledge") / "jem_core.md"

if not FILE.exists():
    # Попробуем .txt
    FILE = Path("knowledge") / "jem_core.txt"
    if not FILE.exists():
        print(f"❌ Не найден jem_core.md / jem_core.txt в knowledge/")
        sys.exit(1)

code = FILE.read_text(encoding="utf-8")
backup = FILE.with_suffix(FILE.suffix + ".backup")
shutil.copy2(FILE, backup)
print(f"💾 Бэкап: {backup}")

changed = False

# ═══ ПАТЧ 1: Добавить правило "не переключай цеха" после IDENTITY ═══
anchor1 = "Ты — первый контакт с пользователем и единственный проводник между Шефом и производственными цехами."
insert1 = """Ты — первый контакт с пользователем и единственный проводник между Шефом и производственными цехами.

**ВАЖНО:** Ты НЕ переключаешь цеха. Цех уже выбран на ресепшене и указан в блоке «ТЕКУЩИЙ ЦЕХ» внизу.
Не предлагай другой цех, не спрашивай «переключить?». Работай в том цехе, который указан."""

if anchor1 in code:
    code = code.replace(anchor1, insert1, 1)
    print("   ✅ 1/2  Правило 'не переключай цеха' добавлено")
    changed = True
else:
    print("   ❌ 1/2  Якорь не найден")

# ═══ ПАТЧ 2: Контент-план только для social_mix ═══
anchor2 = "## ОСОБЫЙ СЛУЧАЙ: КОНТЕНТ-ПЛАН"
insert2 = """## ОСОБЫЙ СЛУЧАЙ: КОНТЕНТ-ПЛАН

> ⚠️ Контент-план доступен ТОЛЬКО в цехе social_mix.
> Если текущий цех НЕ social_mix — НЕ предлагай контент-план.
> Если Шеф просит контент-план в другом цехе — скажи:
> «Шеф, контент-планы делаем в цехе Соцсети. Переключись через ресепшен.»"""

if anchor2 in code:
    code = code.replace(anchor2, insert2, 1)
    print("   ✅ 2/2  Контент-план ограничен social_mix")
    changed = True
else:
    print("   ❌ 2/2  Якорь 'ОСОБЫЙ СЛУЧАЙ' не найден")

if changed:
    FILE.write_text(code, encoding="utf-8")
    print(f"\n✅ Файл обновлён: {FILE}")
    print(f"   Откат: copy {backup} {FILE}")
else:
    print("\n⚠️ Ничего не изменено")
