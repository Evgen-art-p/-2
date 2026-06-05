"""
fix_lifecycle_syntax.py
Исправляет SyntaxError в residents_manager.py:
  positional argument follows keyword argument
  
Проблема: в _run_resident() вызов resident_lifecycle()
передавал user_context как позиционный после именованных аргументов.

Запуск из корня проекта:
    python fix_lifecycle_syntax.py
"""

import shutil
from pathlib import Path

TARGET = Path("studio/residents_manager.py")
BACKUP = Path("studio/residents_manager.py.bak_syntax_fix")

shutil.copy2(TARGET, BACKUP)
print(f"[BACKUP] {BACKUP}")

src = TARGET.read_text(encoding="utf-8")

# Исправление: в _run_resident() user_context передаётся
# как позиционный после именованных → заменяем на *[user_context]
OLD = """    return resident_lifecycle(
        resident_id=resident_id,
        resident_dir=resident_dir,
        work_fn=_work,
        user_context,
        dept=dept,"""

NEW = """    return resident_lifecycle(
        resident_id,
        resident_dir,
        _work,
        user_context,
        dept=dept,"""

if OLD in src:
    src = src.replace(OLD, NEW, 1)
    print("[OK] _run_resident: именованные → позиционные (первые 3 + user_context)")
else:
    print("[WARN] паттерн не найден — ищем альтернативу")
    # Пробуем найти через другой паттерн
    OLD2 = "work_fn=_work,\n        user_context,"
    NEW2 = "_work,\n        user_context,"
    if OLD2 in src:
        # Нужно заменить и предыдущие именованные
        import re
        pattern = r'resident_lifecycle\(\s*resident_id=resident_id,\s*resident_dir=resident_dir,\s*work_fn=_work,\s*user_context,'
        replacement = 'resident_lifecycle(\n        resident_id,\n        resident_dir,\n        _work,\n        user_context,'
        new_src = re.sub(pattern, replacement, src, count=1)
        if new_src != src:
            src = new_src
            print("[OK] _run_resident исправлен через regex")
        else:
            print("[ERROR] не удалось исправить")
    else:
        print("[ERROR] паттерн не найден вообще")

TARGET.write_text(src, encoding="utf-8")
print(f"[WRITTEN] {TARGET}")

import subprocess
r = subprocess.run(
    ["python", "-m", "py_compile", str(TARGET)],
    capture_output=True, text=True
)
if r.returncode == 0:
    print("[SYNTAX OK] residents_manager.py")
    print()
    print("Готово! Все резиденты живут в городе.")
else:
    print(f"[SYNTAX ERROR]:\n{r.stderr}")
    print()
    print("Восстанавливаем бэкап...")
    shutil.copy2(BACKUP, TARGET)
    print(f"[RESTORED] {TARGET}")
