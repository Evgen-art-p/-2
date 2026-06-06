#!/usr/bin/env python3
"""
patch_nicegui_timeout.py — ПАТЧ: увеличиваем WebSocket timeout в NiceGUI

ПРОБЛЕМА:
  Пока агент думает (LLM-запрос 20-60 сек), браузер не получает данных
  по WebSocket. NiceGUI по умолчанию разрывает соединение через ~30 сек
  неактивности → "Connection lost. Trying to reconnect."
  Страница виснет в вечной загрузке.

РЕШЕНИЕ:
  ui.run() принимает параметры reconnect_timeout и uvicorn_logging_level.
  Поднимаем reconnect_timeout до 300 секунд (5 минут).
  Это даёт агентам время думать без потери соединения.

  Дополнительно: добавляем keep-alive ping от сервера каждые 15 сек
  через ping_interval — браузер не закрывает "мёртвое" соединение.
"""

import sys
import shutil
import py_compile
import tempfile
from pathlib import Path
from datetime import datetime

DRY_RUN = "--dry-run" in sys.argv
BACKUP_DIR = Path("_patch_backups") / f"nicegui_timeout_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

def backup(path: Path):
    if DRY_RUN:
        print(f"  [DRY] backup {path}")
        return
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    dest = BACKUP_DIR / path.name
    shutil.copy2(path, dest)
    print(f"  ✓ backup → {dest}")

OLD = """if __name__ in {"__main__", "__mp_main__"}:
    ui.run(reload=False)"""

NEW = """if __name__ in {"__main__", "__mp_main__"}:
    # ПАТЧ nicegui_timeout:
    # reconnect_timeout=300 — браузер ждёт переподключения 5 минут
    #   (LLM-запросы могут идти 30-90 сек, дефолт NiceGUI ~30 сек)
    # ping_interval=15, ping_timeout=60 — сервер пингует браузер каждые 15 сек
    #   чтобы WebSocket не считался мёртвым при длинных запросах
    ui.run(
        reload=False,
        reconnect_timeout=300,
        ping_interval=15,
        ping_timeout=60,
    )"""

def main():
    print("=" * 55)
    print("ПАТЧ: NiceGUI WebSocket timeout (Connection lost fix)")
    print("=" * 55)
    if DRY_RUN:
        print("РЕЖИМ: DRY-RUN\n")

    path = Path("main.py")
    if not path.exists():
        print("❌ main.py не найден")
        sys.exit(1)

    content = path.read_text(encoding="utf-8")

    if OLD not in content:
        print("⚠ Строка не найдена — возможно уже пропатчено")
        # Показываем текущий ui.run чтобы убедиться
        for line in content.splitlines():
            if "ui.run" in line:
                print(f"  Текущий: {line.strip()}")
        sys.exit(0)

    new_content = content.replace(OLD, NEW, 1)

    if DRY_RUN:
        print("  [DRY] main.py: ui.run → ui.run с timeout параметрами")
        sys.exit(0)

    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".py", delete=False) as tmp:
        tmp.write(new_content)
        tmp_path = Path(tmp.name)

    try:
        py_compile.compile(str(tmp_path), doraise=True)
        print("  ✓ Синтаксис OK")
    except py_compile.PyCompileError as e:
        tmp_path.unlink()
        print(f"❌ Синтакс-ошибка: {e}")
        sys.exit(1)

    backup(path)
    shutil.move(str(tmp_path), str(path))

    print("✅ Готово!")
    print(f"   Бекап: {BACKUP_DIR}")
    print()
    print("Что изменилось в main.py:")
    print("  reconnect_timeout=300  — 5 минут ждём переподключения")
    print("  ping_interval=15       — ping каждые 15 сек (держит WS живым)")
    print("  ping_timeout=60        — 60 сек на ответ ping")
    print()
    print("Перезапусти: python main.py")

if __name__ == "__main__":
    main()
