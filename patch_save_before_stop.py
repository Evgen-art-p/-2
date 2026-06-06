#!/usr/bin/env python3
"""
patch_save_before_stop.py — сохраняем результаты ПЕРЕД остановкой

ПРОБЛЕМА:
  В cartridge.py порядок такой:
    1. call_agent() → результат получен
    2. on_after_agent() → хук возвращает {"action": "stop"}
    3. cartridge видит stop → break (выход из цикла)
    4. process_agent_result() → НЕ ВЫЗЫВАЕТСЯ → файлы не пишутся

  В режиме content_plan хук A04 возвращает {"action": "stop"}.
  Все 4 агента отработали, но ни один файл не записан на диск.

ФИКС:
  В cartridge.py — если hook_result["action"] == "stop",
  сначала вызываем process_agent_result() для текущего агента,
  потом делаем break.
"""

import sys
import shutil
import py_compile
import tempfile
from pathlib import Path
from datetime import datetime

DRY_RUN = "--dry-run" in sys.argv
BACKUP_DIR = Path("_patch_backups") / f"save_before_stop_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

def backup(path: Path):
    if DRY_RUN:
        print(f"  [DRY] backup {path}")
        return
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    dest = BACKUP_DIR / path.name
    shutil.copy2(path, dest)
    print(f"  ✓ backup → {dest}")

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


CARTRIDGE_OLD = """                # ═══ HOOK: on_after_agent ═══
                hook_result = self._call_hook("on_after_agent", self.state, worker_id, human_text, meta)
                if hook_result and isinstance(hook_result, dict):
                    if hook_result.get("action") == "stop":  # patch_sprint20_smm
                        print(f"[HOOKS] ⏹ Пайплайн остановлен после {worker_id}.")
                        await self.callbacks.on_status(
                            self.slot_id, f"Стоп после {worker_id}.", "info"
                        )
                        break
                    human_text = hook_result.get("human_text", human_text)
                    meta = hook_result.get("meta", meta)

                # Обрабатываем результат
                human_text, previous_output, ghost_ids = await process_agent_result("""

CARTRIDGE_NEW = """                # ═══ HOOK: on_after_agent ═══
                hook_result = self._call_hook("on_after_agent", self.state, worker_id, human_text, meta)
                _stop_after_save = False
                if hook_result and isinstance(hook_result, dict):
                    if hook_result.get("action") == "stop":  # patch_sprint20_smm
                        print(f"[HOOKS] ⏹ Пайплайн остановлен после {worker_id}.")
                        await self.callbacks.on_status(
                            self.slot_id, f"Стоп после {worker_id}.", "info"
                        )
                        # ПАТЧ save_before_stop: не делаем break сразу —
                        # сначала сохраняем результат текущего агента на диск
                        _stop_after_save = True
                    else:
                        human_text = hook_result.get("human_text", human_text)
                        meta = hook_result.get("meta", meta)

                # Обрабатываем результат
                human_text, previous_output, ghost_ids = await process_agent_result("""

CARTRIDGE_BREAK_OLD = """                await self.callbacks.on_viewer_update(
                    self.slot_id, worker_id,
                    f"# {label} ({worker_id})\\n\\n{human_text}"
                )

                # ── Виктор на ХАРД-СТОПе"""

CARTRIDGE_BREAK_NEW = """                await self.callbacks.on_viewer_update(
                    self.slot_id, worker_id,
                    f"# {label} ({worker_id})\\n\\n{human_text}"
                )

                # ПАТЧ save_before_stop: теперь можно остановиться
                if _stop_after_save:
                    break

                # ── Виктор на ХАРД-СТОПе"""


def main():
    print("=" * 55)
    print("ПАТЧ: Сохраняем файлы ПЕРЕД остановкой пайплайна")
    print("=" * 55)
    if DRY_RUN:
        print("РЕЖИМ: DRY-RUN\n")

    path = Path("studio/cartridge.py")

    print("\n[1/2] cartridge.py — флаг _stop_after_save вместо немедленного break")
    ok1 = apply(path, CARTRIDGE_OLD, CARTRIDGE_NEW,
                "откладываем break до после process_agent_result")

    print("\n[2/2] cartridge.py — break после on_viewer_update")
    ok2 = apply(path, CARTRIDGE_BREAK_OLD, CARTRIDGE_BREAK_NEW,
                "останавливаемся после записи файлов")

    print("\n" + "=" * 55)
    if DRY_RUN:
        print("DRY-RUN завершён.")
        return

    if ok1 and ok2:
        print("✅ Патч применён!")
        print(f"   Бекап: {BACKUP_DIR}")
        print()
        print("Что изменилось:")
        print("  • При content_plan хук говорит 'stop' после A04")
        print("  • Теперь: A04 сначала записывает .md файл на диск")
        print("  • Потом: пайплайн останавливается")
        print("  • Все 4 агента (A01-A04) оставят файлы в runs/")
        print()
        print("Перезапусти: python main.py")
    else:
        print("⚠ Не все патчи применены — проверь файл")


if __name__ == "__main__":
    main()
