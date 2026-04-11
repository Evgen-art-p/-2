"""
🔧 Патч для studio/ui_registry.py — фикс именования папок резидентов

Проблема: при создании резидента через Страницу Жизни, если выбрана
роль (administrator, keeper, mentor, guardian), система использует
ЭТУ РОЛЬ как имя папки. Результат: studio/modules/residents/administrator/
вместо studio/modules/residents/004_OLE/

Фикс: для цеха "residents" ВСЕГДА используем ID_Object как имя папки.
Роль (keeper/administrator) — это лор, не имя директории.

Запуск:
  python patch_registry_folder.py          — применить
  python patch_registry_folder.py --check  — только проверить
"""

import sys
from pathlib import Path

REGISTRY_FILE = Path("studio/ui_registry.py")


def patch():
    check_only = "--check" in sys.argv

    if not REGISTRY_FILE.exists():
        print(f"❌ Файл не найден: {REGISTRY_FILE}")
        return False

    text = REGISTRY_FILE.read_text(encoding="utf-8")

    # Ищем текущую логику
    old_logic = '    folder_name = agent_role.strip() if agent_role.strip() else agent_id'

    new_logic = '''    # Для резидентов: ВСЕГДА используем ID_Object как папку.
    # Роль (keeper/administrator) — это лор, не имя директории.
    # Для рабочих агентов: роль (A01, T1...) = имя папки.
    if workshop == "residents":
        folder_name = agent_id
    else:
        folder_name = agent_role.strip() if agent_role.strip() else agent_id'''

    if old_logic not in text:
        if "workshop == \"residents\"" in text and "folder_name = agent_id" in text:
            print("✅ ui_registry.py уже патчен.")
            return True
        print("⚠ Не нашёл точный паттерн. Проверь generate_agent_files() вручную.")
        print(f"  Ищу: {old_logic[:60]}...")
        return False

    if check_only:
        print("⚠ ui_registry.py НЕ патчен — резиденты получают роль как папку.")
        print("  Запусти без --check чтобы применить.")
        return False

    text = text.replace(old_logic, new_logic, 1)

    REGISTRY_FILE.write_text(text, encoding="utf-8")
    print("✅ ui_registry.py патчен!")
    print("   Для residents: папка = ID_Object (004_OLE, 005_SOMEONE...)")
    print("   Для рабочих: папка = роль (A01, T1...) как было")
    print()
    print("💡 Теперь в Странице Жизни можешь спокойно выбирать роль")
    print("   (keeper, administrator) — папка всё равно будет по ID.")
    return True


if __name__ == "__main__":
    patch()
