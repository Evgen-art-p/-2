"""
patch_a00_prompt.py — Патч промпта Фабулы Фейн (A00)
Добавляет психологические принципы (Гиппенрейтер, экстернализация, Я-сообщения)
для устранения конфликта с A00a (Вера Душа).

Запуск: python patch_a00_prompt.py
"""

import shutil
from pathlib import Path
from datetime import datetime

# === КОНФИГУРАЦИЯ ===
# Путь к промпту A00 (подстрой под свою структуру если нужно)
STUDIO_ROOT = Path(__file__).parent
PROMPT_PATH = STUDIO_ROOT / "studio" / "modules" / "living_book" / "A00" / "forge" / "prompt.md"
PATCH_SOURCE = STUDIO_ROOT / "A00_forge_prompt.md"  # новый файл рядом со скриптом


def main():
    print("=" * 60)
    print("🔧 ПАТЧ: A00 Фабула Фейн — промпт с психопринципами")
    print("=" * 60)

    # Проверяем что файл существует
    if not PROMPT_PATH.exists():
        print(f"❌ Файл не найден: {PROMPT_PATH}")
        print("   Проверь путь к студии.")
        return

    # Проверяем что патч-файл существует
    if not PATCH_SOURCE.exists():
        print(f"❌ Файл-патч не найден: {PATCH_SOURCE}")
        print("   Он должен лежать рядом со скриптом.")
        return

    # Бэкап
    backup_name = f"prompt.md.bak_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    backup_path = PROMPT_PATH.parent / backup_name
    shutil.copy2(PROMPT_PATH, backup_path)
    print(f"📦 Бэкап: {backup_path}")

    # Размер до
    old_size = PROMPT_PATH.stat().st_size
    print(f"📄 Старый промпт: {old_size} байт")

    # Копируем новый промпт
    shutil.copy2(PATCH_SOURCE, PROMPT_PATH)
    new_size = PROMPT_PATH.stat().st_size
    print(f"📄 Новый промпт:  {new_size} байт")

    # Проверяем что ключевые блоки на месте
    content = PROMPT_PATH.read_text(encoding="utf-8")
    checks = [
        ("Гиппенрейтер", "Метод Гиппенрейтер" in content),
        ("Экстернализация", "экстернализации" in content.lower() or "Эпстон" in content),
        ("Я-сообщения", "Розенберг" in content),
        ("Запрещённые фразы", "не бойся" in content),
        ("safety_self_check", "safety_self_check" in content),
        ("Чеклист", "Чеклист перед отправкой" in content),
    ]

    print("\n✅ Проверка содержимого:")
    all_ok = True
    for name, ok in checks:
        status = "✅" if ok else "❌"
        print(f"   {status} {name}")
        if not ok:
            all_ok = False

    if all_ok:
        print("\n🎉 ПАТЧ УСПЕШНО ПРИМЕНЁН!")
        print("   Фабула Фейн теперь знает правила Веры Души.")
        print("   Следующий ран living_book должен пройти без петли A00↔A00a.")
    else:
        print("\n⚠️  Некоторые проверки не прошли. Проверь файл вручную.")

    print(f"\n📁 Файл: {PROMPT_PATH}")
    print(f"📁 Бэкап: {backup_path}")


if __name__ == "__main__":
    main()
