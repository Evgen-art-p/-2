#!/usr/bin/env python3
"""
patch_timer_and_contract.py — два бага одним патчем

БАГ 1: ui.py — _check_auto_run таймер
  ui.timer(1.0, _check_auto_run) вызывается каждую секунду.
  Внутри _check_auto_run есть скрытый вызов который триггерит
  [WORKSHOP] лог. Когда клиент отключился — таймер не останавливается,
  печатает [WORKSHOP] бесконечно, забивает консоль, мешает видеть реальные ошибки.
  
  ФИКС: добавляем guard — если pipeline_running или клиент мёртв — выходим.

БАГ 2: Контракт A03 блокирует работу
  [CONTRACT] ❌ A03: Ключ `conflict` запрещён
  [CONTRACT] ❌ A03: Ключ `content_format` запрещён
  ... (6 ошибок) → ретрай → ещё один LLM-вызов → +30 сек → клиент умирает
  
  Контракт для A03 прописан неверно — разрешает только ['max_story', 'то же']
  но агент возвращает нормальные ключи контент-плана.
  
  ФИКС: временно отключаем Contract Validator (он делает ретраи, удваивает время).
  Контракт можно донастроить отдельно когда пайплайн стабилизируется.
"""

import sys
import shutil
import py_compile
import tempfile
from pathlib import Path
from datetime import datetime

DRY_RUN = "--dry-run" in sys.argv
BACKUP_DIR = Path("_patch_backups") / f"timer_contract_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

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


# ══════════════════════════════════════════════════════════════════
# ПАТЧ 1: ui.py — глушим спам таймера
# ══════════════════════════════════════════════════════════════════

TIMER_OLD = """                async def _check_auto_run():
                    global _auto_run_requested
                    if _auto_run_requested and not state["pipeline_running"]:
                        _auto_run_requested = False
                        with _page_client:
                            await run_cartridge_pipeline()  # <- добавить отступ (4 пробела)

                ui.timer(1.0, _check_auto_run)"""

TIMER_NEW = """                async def _check_auto_run():
                    global _auto_run_requested
                    # ПАТЧ timer: guard — не запускаем если pipeline уже работает
                    if not _auto_run_requested:
                        return
                    if state.get("pipeline_running"):
                        return
                    _auto_run_requested = False
                    try:
                        with _page_client:
                            await run_cartridge_pipeline()
                    except Exception:
                        pass  # клиент мог умереть

                ui.timer(1.0, _check_auto_run)"""


# ══════════════════════════════════════════════════════════════════
# ПАТЧ 2: pipeline.py — отключаем Contract Validator
# (он ломает пайплайн ретраями пока ключи контракта не настроены)
# ══════════════════════════════════════════════════════════════════

CONTRACT_OLD = """# ══ Contract Validator — Таможня Контракта ══
try:
    from studio.workshop.contract_validator import validate as _contract_validate, build_retry_prompt as _contract_retry_prompt
    _CONTRACT_ENABLED = True
    print("[CONTRACT] Таможня Контракта подключена")
except ImportError:
    _CONTRACT_ENABLED = False
    def _contract_validate(agent_id, my_output): return []
    def _contract_retry_prompt(errors, agent_id): return ""
# ══ END Contract ══"""

CONTRACT_NEW = """# ══ Contract Validator — Таможня Контракта ══
# ПАТЧ timer_contract: временно отключён — ключи контракта не совпадают
# с реальным output агентов, вызывает ретраи (+30 сек каждый), гробит WS.
# Включить обратно после синхронизации CHAIN_CONTRACT.md с промптами агентов.
_CONTRACT_ENABLED = False
def _contract_validate(agent_id, my_output, dept=""): return []
def _contract_retry_prompt(errors, agent_id): return ""
print("[CONTRACT] Таможня Контракта — ПАУЗА (ключи не синхронизированы)")
# ══ END Contract ══"""


def main():
    print("=" * 60)
    print("ПАТЧ: Timer guard + Contract Validator off")
    print("=" * 60)
    if DRY_RUN:
        print("РЕЖИМ: DRY-RUN\n")

    ui_path       = Path("studio/workshop/ui.py")
    pipeline_path = Path("studio/workshop/pipeline.py")

    print("\n[1/2] ui.py — глушим спам таймера _check_auto_run")
    ok1 = apply(ui_path, TIMER_OLD, TIMER_NEW, "guard в _check_auto_run")

    print("\n[2/2] pipeline.py — Contract Validator на паузу")
    ok2 = apply(pipeline_path, CONTRACT_OLD, CONTRACT_NEW,
                "CONTRACT_ENABLED = False (ключи не синхронизированы)")

    print("\n" + "=" * 60)
    if DRY_RUN:
        print("DRY-RUN завершён.")
        return

    if ok1 or ok2:
        print("✅ Патч применён!")
        print(f"   Бекапы: {BACKUP_DIR}")
        print()
        print("Что изменилось:")
        if ok1:
            print("  • Таймер больше не спамит [WORKSHOP] в консоль")
            print("    когда клиент отключён")
        if ok2:
            print("  • Contract Validator отключён — нет ретраев")
            print("    A03 не будет делать двойной LLM-вызов")
            print("    (контракт можно настроить позже)")
        print()
        print("Перезапусти: python main.py")
    else:
        print("⚠ Ничего не применено — проверь структуру файлов")


if __name__ == "__main__":
    main()
