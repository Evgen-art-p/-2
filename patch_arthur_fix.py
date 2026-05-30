"""
patch_arthur_fix.py
===================
Фикс одной строки в studio/assembly/monteur.py.

Исправляет невалидный escape в regex внутри _arthur_look():
  было:  r'\\{.*\\}'   — ищет буквальные \\{ — JSON не найдёт
  стало: r'\{.*\}'     — ищет JSON-блок — правильно

Запускать из корня проекта:
  python patch_arthur_fix.py
"""

from pathlib import Path

TARGET = Path("studio/assembly/monteur.py")

OLD = r"        m = _re.search(r'\\{.*\\}', raw, _re.DOTALL)"
NEW = r"        m = _re.search(r'\{.*\}', raw, _re.DOTALL)"


def patch():
    if not TARGET.exists():
        print(f"❌ Файл не найден: {TARGET}")
        return

    src = TARGET.read_text(encoding="utf-8")

    if OLD not in src:
        # Проверим что правильная версия уже на месте
        if NEW in src:
            print("✅ Уже исправлено — всё чисто")
        else:
            print("⚠️  Строка не найдена — проверь monteur.py вручную")
            print(f"   Ищу: {OLD}")
        return

    src = src.replace(OLD, NEW)
    TARGET.write_text(src, encoding="utf-8")
    print("✅ Исправлено:")
    print(f"   было:  {OLD.strip()}")
    print(f"   стало: {NEW.strip()}")


if __name__ == "__main__":
    patch()
