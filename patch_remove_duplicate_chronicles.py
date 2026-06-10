# -*- coding: utf-8 -*-
"""
ПАТЧ city_yellow №12 (часть 2) — удаление дубля chronicles.py из корня репо.

Что делает:
  В корне репо лежит chronicles.py — побайтовая копия
  studio/cabinet/chronicles.py (одинаковый md5, 489 строк).
  Рабочая версия — та, что в studio/cabinet/. Корневая — забытый дубль.

Безопасность:
  1. Сравнивает md5 ОБОИХ файлов перед любыми действиями.
     Если хеши НЕ совпадают — ничего не делает (файлы разошлись,
     значит это уже не "тот самый" дубль, нужен ручной разбор).
  2. Если хеши совпадают — НЕ удаляет файл, а переименовывает его
     в chronicles.py.removed_duplicate (можно вернуть одной командой
     mv обратно, если что-то сломается).
  3. Если корневого chronicles.py уже нет — считает что патч уже применён.

Запуск:
  python patch_remove_duplicate_chronicles.py
  (запускать из корня репо)

Откат (если что-то пошло не так):
  mv chronicles.py.removed_duplicate chronicles.py
"""

import hashlib
from pathlib import Path

ROOT_FILE = Path("chronicles.py")
CABINET_FILE = Path("studio/cabinet/chronicles.py")
RENAMED = Path("chronicles.py.removed_duplicate")


def md5_of(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


def main():
    if not ROOT_FILE.exists():
        if RENAMED.exists():
            print("✅ Уже применено — корневой файл уже переименован.")
        else:
            print("✅ Корневого chronicles.py нет — нечего удалять.")
        return

    if not CABINET_FILE.exists():
        print(f"⚠️  Не найден рабочий файл: {CABINET_FILE}")
        print("    Ничего не трогаю — нечего сравнивать.")
        return

    root_hash = md5_of(ROOT_FILE)
    cabinet_hash = md5_of(CABINET_FILE)

    print(f"  {ROOT_FILE}      md5: {root_hash}")
    print(f"  {CABINET_FILE}   md5: {cabinet_hash}")

    if root_hash != cabinet_hash:
        print("⚠️  Хеши НЕ совпадают — файлы уже разные.")
        print("    Это больше не точный дубль. Ничего не изменено.")
        print("    Нужен ручной разбор — что в корневом отличается.")
        return

    # Файлы идентичны — переименовываем (не удаляем!) корневой
    ROOT_FILE.rename(RENAMED)
    print(f"✅ Идентичны. Корневой файл переименован → {RENAMED}")
    print(f"   Рабочая версия осталась нетронутой: {CABINET_FILE}")
    print()
    print("   Если через какое-то время всё работает нормально —")
    print(f"   можно удалить {RENAMED} вручную.")
    print()
    print("   Откат (если что-то сломалось):")
    print(f"   mv {RENAMED} {ROOT_FILE}")


if __name__ == "__main__":
    main()
