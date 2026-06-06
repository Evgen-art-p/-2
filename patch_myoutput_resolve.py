#!/usr/bin/env python3
"""
patch_myoutput_resolve.py — подставляем реальный my_output вместо {{my_output}}

ПРОБЛЕМА:
  A01 пишет в chain_data:
    "adam_bible": "{{my_output}}"
  
  Это шаблон — агент должен был подставить реальный my_output.
  Но подстановки нигде нет — Катя получает строку "{{my_output}}".

РЕШЕНИЕ:
  В process_agent_result() — после парсинга meta,
  заменяем все значения "{{my_output}}" в chain_data
  на реальный meta["my_output"].
  
  Это одна строка логики. Без инжекта в контекст — просто резолв шаблона.
"""

import sys
import shutil
import py_compile
import tempfile
from pathlib import Path
from datetime import datetime

DRY_RUN = "--dry-run" in sys.argv
BACKUP_DIR = Path("_patch_backups") / f"myoutput_resolve_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

def backup(path: Path):
    if DRY_RUN:
        print(f"  [DRY] backup {path}")
        return
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, BACKUP_DIR / path.name)
    print(f"  ✓ backup → {BACKUP_DIR / path.name}")

def apply(path: Path, old: str, new: str, desc: str) -> bool:
    if not path.exists():
        print(f"  ❌ Файл не найден: {path}")
        return False
    content = path.read_text(encoding="utf-8")
    if old not in content:
        print(f"  ⚠ Не найдено: {desc}")
        return False
    new_content = content.replace(old, new, 1)
    if DRY_RUN:
        print(f"  [DRY] {path.name}: {desc}")
        return True
    backup(path)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8",
                                     suffix=".py", delete=False) as tmp:
        tmp.write(new_content)
        tmp_path = Path(tmp.name)
    try:
        py_compile.compile(str(tmp_path), doraise=True)
    except py_compile.PyCompileError as e:
        tmp_path.unlink()
        print(f"  ❌ Синтакс-ошибка: {e}")
        return False
    shutil.move(str(tmp_path), str(path))
    print(f"  ✓ {path.name}: {desc}")
    return True


# Находим место где сохраняем результат в state
# и добавляем резолв {{my_output}} в chain_data

OLD = (
    "    # Сохраняем в state\n"
    "    state[\"results\"][worker_id] = {\n"
    "        \"text\": human_text,\n"
    "        \"meta\": meta,\n"
    "        \"raw\": raw_result\n"
    "    }"
)

NEW = (
    "    # Резолв {{my_output}} в chain_data — агенты пишут шаблон вместо данных\n"
    "    # Заменяем строку-заглушку на реальный my_output до сохранения в state\n"
    "    _my_out_real = meta.get(\"my_output\", {})\n"
    "    _chain_raw = meta.get(\"chain_data\", {})\n"
    "    if _chain_raw and isinstance(_chain_raw, dict) and _my_out_real:\n"
    "        for _ck in list(_chain_raw.keys()):\n"
    "            if _chain_raw[_ck] == \"{{my_output}}\":\n"
    "                _chain_raw[_ck] = _my_out_real\n"
    "                print(f\"[CHAIN] {worker_id}: {{my_output}} → реальный my_output для '{_ck}'\")\n"
    "        meta[\"chain_data\"] = _chain_raw\n"
    "\n"
    "    # Сохраняем в state\n"
    "    state[\"results\"][worker_id] = {\n"
    "        \"text\": human_text,\n"
    "        \"meta\": meta,\n"
    "        \"raw\": raw_result\n"
    "    }"
)


def main():
    print("=" * 55)
    print("ПАТЧ: резолв {{my_output}} в chain_data")
    print("=" * 55)
    if DRY_RUN:
        print("DRY-RUN\n")

    path = Path("studio/workshop/pipeline.py")

    print("\n[1/1] pipeline.py — заменяем {{my_output}} на реальный my_output")
    ok = apply(path, OLD, NEW, "резолв шаблона в chain_data")

    print("\n" + "=" * 55)
    if DRY_RUN:
        print("DRY-RUN завершён.")
        return

    if ok:
        print("✅ Готово! Перезапусти: python main.py")
        print()
        print("Что изменилось:")
        print("  • A01 пишет chain_data.adam_bible = '{{my_output}}'")
        print("  • Pipeline видит шаблон и заменяет на реальный my_output")
        print("  • A04 (Катя) получает настоящую библию, а не строку-заглушку")
        print("  • Никакого инжекта JSON в контекст — только резолв шаблона")
    else:
        print("⚠ Не применено — проверь файл")

if __name__ == "__main__":
    main()
