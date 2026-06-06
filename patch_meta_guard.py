"""
patch_meta_guard.py
Fix: AttributeError 'str' object has no attribute 'get'
в process_agent_result когда meta — строка.

Причина: конфликтный ран возвращает агента без JSON блока.
parse_agent_response возвращает (text, {}) — но где-то
между call_agent и process_agent_result meta становится строкой.

Решение: в начале process_agent_result нормализуем meta к dict.
Одна строка — закрывает все падения разом.
"""
import sys, shutil
from pathlib import Path
from datetime import datetime

TARGET = Path("studio/workshop/pipeline.py")
BACKUP = Path("_patch_backups")

OLD = '''    info = get_worker_info(worker_id, state.get("active_dept", ""))
    label = info.get("label", worker_id) if info else worker_id

    # Валидация asset_ids
    ghost_ids = _validate_asset_ids(meta, worker_id)'''

NEW = '''    info = get_worker_info(worker_id, state.get("active_dept", ""))
    label = info.get("label", worker_id) if info else worker_id

    # Защита: meta должна быть dict. Если агент не вернул JSON —
    # parse_agent_response даёт {}, но конфликтный ран может дать строку.
    if not isinstance(meta, dict):
        meta = {}

    # Валидация asset_ids
    ghost_ids = _validate_asset_ids(meta, worker_id)'''

def main():
    if not TARGET.exists():
        print(f"[ERROR] {TARGET} не найден")
        sys.exit(1)

    content = TARGET.read_text(encoding="utf-8")

    if "if not isinstance(meta, dict):" in content:
        print("[OK] Защита уже есть в pipeline.py")
        return

    if OLD not in content:
        print("[ERROR] Якорь не найден — структура изменилась")
        sys.exit(1)

    BACKUP.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    shutil.copy2(TARGET, BACKUP / f"pipeline.py.bak_meta_{ts}")

    TARGET.write_text(content.replace(OLD, NEW, 1), encoding="utf-8")
    print(f"[DONE] {TARGET} — meta нормализуется к dict в начале process_agent_result")

if __name__ == "__main__":
    main()
