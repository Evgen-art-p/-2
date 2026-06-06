#!/usr/bin/env python3
"""
patch_utils_fix.py — точечный фикс utils.py

Находит ЛЮБУЮ строку с selected.get(cat, []) и добавляет
isinstance проверку перед ней с правильными отступами.
"""

import sys
import shutil
import py_compile
import tempfile
from pathlib import Path
from datetime import datetime

DRY_RUN = "--dry-run" in sys.argv
BACKUP_DIR = Path("_patch_backups") / f"utils_fix_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

def main():
    print("=" * 55)
    print("ПАТЧ: utils.py — isinstance fix (точечный)")
    print("=" * 55)

    path = Path("studio/workshop/utils.py")
    if not path.exists():
        print("❌ utils.py не найден")
        sys.exit(1)

    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    
    # Ищем строку с selected.get(cat, [])
    target_idx = None
    for i, line in enumerate(lines):
        if "selected.get(cat, [])" in line and "for item in" in line:
            target_idx = i
            break
    
    if target_idx is None:
        print("⚠ Строка 'for item in selected.get(cat, [])' не найдена")
        print("Возможно уже пропатчено или структура изменилась")
        sys.exit(0)
    
    print(f"  Найдена строка {target_idx + 1}: {lines[target_idx].rstrip()}")
    
    # Определяем отступ
    line_content = lines[target_idx]
    indent = len(line_content) - len(line_content.lstrip())
    indent_str = " " * indent
    
    # Проверяем что предыдущая строка не уже содержит isinstance
    prev_lines = "".join(lines[max(0, target_idx-3):target_idx])
    if "isinstance(selected, dict)" in prev_lines:
        print("✓ Уже пропатчено — isinstance проверка уже есть")
        sys.exit(0)
    
    # Вставляем проверку перед строкой
    check_line = f"{indent_str}if not isinstance(selected, dict):\n"
    reset_line = f"{indent_str}    selected = {{}}\n"
    
    new_lines = lines[:target_idx] + [check_line, reset_line] + lines[target_idx:]
    new_content = "".join(new_lines)
    
    if DRY_RUN:
        print(f"  [DRY] Вставим перед строкой {target_idx + 1}:")
        print(f"    {check_line.rstrip()}")
        print(f"    {reset_line.rstrip()}")
        sys.exit(0)
    
    # Валидация
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8",
                                     suffix=".py", delete=False) as tmp:
        tmp.write(new_content)
        tmp_path = Path(tmp.name)
    
    try:
        py_compile.compile(str(tmp_path), doraise=True)
        print("  ✓ Синтаксис OK")
    except py_compile.PyCompileError as e:
        tmp_path.unlink()
        print(f"  ❌ Синтакс-ошибка: {e}")
        sys.exit(1)
    
    # Бекап и запись
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, BACKUP_DIR / path.name)
    print(f"  ✓ backup → {BACKUP_DIR / path.name}")
    
    shutil.move(str(tmp_path), str(path))
    print(f"  ✓ utils.py пропатчен (строка {target_idx + 1})")
    
    print("\n✅ Готово! Перезапусти: python main.py")

if __name__ == "__main__":
    main()
