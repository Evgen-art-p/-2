"""
patch_filter_pycache_v2.py
══════════════════════════════════════════════════════════
Патчит studio/modules_registry.py — заменяет d.is_dir()
на _is_valid_dir(d) в трёх функциях сканирования папок.

Константа _FS_GARBAGE уже добавлена предыдущим патчем.
Этот патч только чинит три замены которые не прошли.

Запускать из корня проекта:
  python patch_filter_pycache_v2.py
══════════════════════════════════════════════════════════
"""

import shutil
import py_compile
import sys
from pathlib import Path

TARGET = Path("studio/modules_registry.py")
BACKUP = Path("studio/modules_registry.py.bak_pycache_filter_v2")


PATCHES = [
    # ── 1. list_workers() ────────────────────────────────────────────────────
    (
        "list_workers",
        "if d.is_dir() and d.name.startswith(\"A\"):",
        "if _is_valid_dir(d) and d.name.startswith(\"A\"):",
    ),
    # ── 2. load_depts() ──────────────────────────────────────────────────────
    (
        "load_depts",
        "if not d.is_dir():",
        "if not _is_valid_dir(d):",
    ),
    # ── 3. get_dept_workers() ────────────────────────────────────────────────
    (
        "get_dept_workers",
        "existing = [a for a in agents if (dept_path / a).is_dir()]",
        "existing = [a for a in agents if _is_valid_dir(dept_path / a)]",
    ),
]


def patch():
    if not TARGET.exists():
        print(f"[ОШИБКА] Файл не найден: {TARGET}")
        sys.exit(1)

    shutil.copy2(TARGET, BACKUP)
    print(f"[OK] Бэкап: {BACKUP}")

    text = TARGET.read_text(encoding="utf-8")
    original = text

    # Проверяем что _is_valid_dir уже определена (от предыдущего патча)
    if "_is_valid_dir" not in text:
        print("[ОШИБКА] Функция _is_valid_dir не найдена в файле.")
        print("         Сначала запусти patch_filter_pycache.py")
        sys.exit(1)

    for name, old, new in PATCHES:
        if old in text:
            count = text.count(old)
            text = text.replace(old, new, 1)
            print(f"[OK] Пропатчен {name}() (вхождений было: {count})")
        elif new in text:
            print(f"[SKIP] {name}() — уже содержит новый код")
        else:
            print(f"[WARN] {name}() — фрагмент не найден совсем, пропускаю")

    if text == original:
        print("\n[INFO] Файл не изменился — всё уже пропатчено.")
        return

    TARGET.write_text(text, encoding="utf-8")
    print(f"\n[DONE] {TARGET} обновлён.")

    try:
        py_compile.compile(str(TARGET), doraise=True)
        print("[OK] Синтаксис: OK ✅")
    except py_compile.PyCompileError as e:
        print(f"[ERROR] Синтаксическая ошибка! Восстанавливаю бэкап...\n{e}")
        shutil.copy2(BACKUP, TARGET)
        sys.exit(1)


if __name__ == "__main__":
    patch()
