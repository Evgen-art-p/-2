# patch_cabinet_trading_dept.py
# ═══════════════════════════════════════════════════════════════
# ТОРГОВЫЙ ЦЕХ — ШАГ 10 (часть 1): регистрация в Кабинете
#
# Проблема: Искра (A01) родилась в studio/modules/trading/,
# но Кабинет её не видит. Причина: Кабинет строит аккордеон цехов,
# карту города, матрицу и глобальный поиск из захардкоженного
# списка DEPARTMENTS в studio/cabinet/agents.py — а trading
# в этом списке нет.
#
# Что делает патч: добавляет одну строку в DEPARTMENTS.
# После этого в Кабинете появится секция "trading" со всеми
# агентами Совета, у которых есть папка в modules/trading/.
#
# Запуск:  python patch_cabinet_trading_dept.py
# ═══════════════════════════════════════════════════════════════
import shutil
import py_compile
from datetime import datetime
from pathlib import Path

TARGET = Path("studio/cabinet/agents.py")
BACKUP_DIR = Path("_patch_backups")

OLD = '''    {"id": "living_book",  "label": "living-book",  "prefix": "A"},
]'''

NEW = '''    {"id": "living_book",  "label": "living-book",  "prefix": "A"},
    {"id": "trading",      "label": "trading",      "prefix": "A"},
]'''


def main():
    if not TARGET.exists():
        print(f"❌ Файл не найден: {TARGET}")
        print("   Запускай из корня проекта (там где main.py).")
        return

    text = TARGET.read_text(encoding="utf-8")

    # Идемпотентность: не применять дважды
    if '"id": "trading"' in text:
        print("✅ trading уже зарегистрирован в DEPARTMENTS — патч не нужен.")
        return

    if OLD not in text:
        print("❌ Якорная строка не найдена — файл изменился.")
        print("   Нужно добавить вручную в DEPARTMENTS (studio/cabinet/agents.py):")
        print('   {"id": "trading", "label": "trading", "prefix": "A"},')
        return

    # Бэкап
    BACKUP_DIR.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = BACKUP_DIR / f"agents.py.bak_trading_dept_{stamp}"
    shutil.copy2(TARGET, backup)
    print(f"📦 Бэкап: {backup}")

    # Правка
    TARGET.write_text(text.replace(OLD, NEW, 1), encoding="utf-8")
    print(f"✏️  DEPARTMENTS += trading → {TARGET}")

    # Проверка компиляции
    try:
        py_compile.compile(str(TARGET), doraise=True)
        print("✅ Компиляция OK")
    except py_compile.PyCompileError as e:
        print(f"❌ Ошибка компиляции, откатываю: {e}")
        shutil.copy2(backup, TARGET)
        return

    print()
    print("═" * 50)
    print("ГОТОВО. Перезапусти студию → /cabinet →")
    print("в аккордеоне цехов появится секция «trading»,")
    print("внутри — Искра A01 (и все A02–A09, у кого есть папки).")
    print("═" * 50)


if __name__ == "__main__":
    main()
