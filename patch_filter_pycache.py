"""
patch_filter_pycache.py
═══════════════════════════════════════════════════════════
Добавляет фильтр системного мусора (__pycache__, .DS_Store и т.д.)
во все функции, которые итерируют папки цехов и резидентов.

Затронутые файлы:
  • studio/modules_registry.py  (list_workers, load_depts)

Запускать из корня проекта:
  python patch_filter_pycache.py
═══════════════════════════════════════════════════════════
"""

import shutil
from pathlib import Path

TARGET = Path("studio/modules_registry.py")
BACKUP = Path("studio/modules_registry.py.bak_pycache_filter")

# ─── Константа-мусорник (добавим в начало файла, после импортов) ─────────────
GARBAGE_NAMES_INJECT = '''\n# ── Системный мусор — папки которые никогда не являются агентами/цехами ──────
_FS_GARBAGE: set[str] = {
    "__pycache__", ".DS_Store", "desktop.ini", "Thumbs.db",
    ".git", ".idea", ".vscode", "__MACOSX",
}

def _is_valid_dir(d: Path) -> bool:
    """True если папка — реальный модуль, не системный мусор."""
    return d.is_dir() and d.name not in _FS_GARBAGE and not d.name.startswith(".")
\n'''

# ─── Правки в list_workers() ─────────────────────────────────────────────────
OLD_LIST_WORKERS = '''\    workers = []
    for d in sorted(dept_path.iterdir()):
        if d.is_dir() and d.name.startswith("A"):
            workers.append(d.name)'''

NEW_LIST_WORKERS = '''\    workers = []
    for d in sorted(dept_path.iterdir()):
        if _is_valid_dir(d) and d.name.startswith("A"):
            workers.append(d.name)'''

# ─── Правки в load_depts() ───────────────────────────────────────────────────
OLD_LOAD_DEPTS = '''\    for d in MODULES_DIR.iterdir():
        if not d.is_dir():
            continue
        info_path = d / "info.json"
        if not info_path.exists():
            continue'''

NEW_LOAD_DEPTS = '''\    for d in MODULES_DIR.iterdir():
        if not _is_valid_dir(d):
            continue
        info_path = d / "info.json"
        if not info_path.exists():
            continue'''

# ─── Правки в get_dept_workers() — строчка с is_dir() ───────────────────────
OLD_GET_DEPT = '''\        existing = [a for a in agents if (dept_path / a).is_dir()]'''

NEW_GET_DEPT = '''\        existing = [a for a in agents if _is_valid_dir(dept_path / a)]'''


def patch():
    if not TARGET.exists():
        print(f"[ОШИБКА] Файл не найден: {TARGET}")
        return

    # Бэкап
    shutil.copy2(TARGET, BACKUP)
    print(f"[OK] Бэкап: {BACKUP}")

    text = TARGET.read_text(encoding="utf-8")
    original = text

    # ── 1. Вставляем константу _FS_GARBAGE после строки "import json" ────────
    if "_FS_GARBAGE" in text:
        print("[SKIP] _FS_GARBAGE уже есть — пропускаем вставку константы")
    else:
        inject_after = "import json"
        if inject_after in text:
            text = text.replace(inject_after, inject_after + GARBAGE_NAMES_INJECT, 1)
            print("[OK] Добавлена константа _FS_GARBAGE + _is_valid_dir()")
        else:
            print("[WARN] Не нашёл 'import json' — константу не вставил")

    # ── 2. list_workers() ─────────────────────────────────────────────────────
    if OLD_LIST_WORKERS in text:
        text = text.replace(OLD_LIST_WORKERS, NEW_LIST_WORKERS, 1)
        print("[OK] Пропатчен list_workers()")
    else:
        print("[WARN] list_workers() — старый код не найден (уже пропатчен?)")

    # ── 3. load_depts() ───────────────────────────────────────────────────────
    if OLD_LOAD_DEPTS in text:
        text = text.replace(OLD_LOAD_DEPTS, NEW_LOAD_DEPTS, 1)
        print("[OK] Пропатчен load_depts()")
    else:
        print("[WARN] load_depts() — старый код не найден (уже пропатчен?)")

    # ── 4. get_dept_workers() ─────────────────────────────────────────────────
    if OLD_GET_DEPT in text:
        text = text.replace(OLD_GET_DEPT, NEW_GET_DEPT, 1)
        print("[OK] Пропатчен get_dept_workers()")
    else:
        print("[WARN] get_dept_workers() — старый код не найден (уже пропатчен?)")

    # ── Сохраняем только если что-то изменилось ───────────────────────────────
    if text == original:
        print("\n[INFO] Файл не изменился — патч уже применён или код отличается.")
        return

    TARGET.write_text(text, encoding="utf-8")
    print(f"\n[DONE] {TARGET} обновлён.")

    # ── Синтаксическая проверка ───────────────────────────────────────────────
    import py_compile, sys
    try:
        py_compile.compile(str(TARGET), doraise=True)
        print("[OK] Синтаксис: OK ✅")
    except py_compile.PyCompileError as e:
        print(f"[ERROR] Синтаксическая ошибка! Восстанавливаю бэкап...\n{e}")
        shutil.copy2(BACKUP, TARGET)
        sys.exit(1)


if __name__ == "__main__":
    patch()
