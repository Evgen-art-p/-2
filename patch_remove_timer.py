"""
patch_remove_timer.py
Убирает ui.timer(5.0, _refresh_map) из ui_cabinet.py.
Карта обновляется только вручную — по кнопке или после прогулки.
Это устраняет конфликт с NiceGUI event loop во время рана.
"""
import sys, shutil
from pathlib import Path
from datetime import datetime

TARGET = Path("studio/cabinet/ui_cabinet.py")
BACKUP = Path("_patch_backups")

OLD = """        # Автообновление карты каждые 5 секунд — живые перемещения
        ui.timer(5.0, _refresh_map)

        # JS bridge"""

NEW = """        # JS bridge"""

def main():
    if not TARGET.exists():
        print(f"[ERROR] {TARGET} не найден")
        sys.exit(1)

    content = TARGET.read_text(encoding="utf-8")

    if OLD not in content:
        print("[SKIP] Таймер уже убран или не найден")
        return

    BACKUP.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    shutil.copy2(TARGET, BACKUP / f"ui_cabinet.py.bak_notimer_{ts}")

    TARGET.write_text(content.replace(OLD, NEW, 1), encoding="utf-8")
    print("[DONE] Автотаймер карты убран — обновление только по кнопке")

if __name__ == "__main__":
    main()
