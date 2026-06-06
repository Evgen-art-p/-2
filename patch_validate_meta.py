"""
patch_validate_meta.py
Fix: AttributeError 'str' object has no attribute 'get'
в _validate_asset_ids() когда meta — строка, а не dict.
"""
import sys, shutil
from pathlib import Path
from datetime import datetime

TARGET = Path("studio/workshop/utils.py")
BACKUP = Path("_patch_backups")

OLD = '''def _validate_asset_ids(meta: dict, worker_id: str) -> list[str]:
    """
    Проверяет все ref_ids в ответе агента по загруженному каталогу.
    Возвращает список несуществующих ID (галлюцинации).
    """
    try:
        from studio.fal_client import get_asset_path
    except ImportError:
        return []

    ghost_ids = []'''

NEW = '''def _validate_asset_ids(meta, worker_id: str) -> list[str]:
    """
    Проверяет все ref_ids в ответе агента по загруженному каталогу.
    Возвращает список несуществующих ID (галлюцинации).
    """
    # Защита: meta может прийти строкой если JSON не распарсился
    if not isinstance(meta, dict):
        return []

    try:
        from studio.fal_client import get_asset_path
    except ImportError:
        return []

    ghost_ids = []'''

def main():
    if not TARGET.exists():
        print(f"[ERROR] {TARGET} не найден")
        sys.exit(1)

    content = TARGET.read_text(encoding="utf-8")

    if OLD not in content:
        print("[SKIP] Уже пропатчено или структура изменилась")
        return

    BACKUP.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    shutil.copy2(TARGET, BACKUP / f"utils.py.bak_{ts}")

    TARGET.write_text(content.replace(OLD, NEW, 1), encoding="utf-8")
    print(f"[DONE] {TARGET} — _validate_asset_ids защищена от str")

if __name__ == "__main__":
    main()
