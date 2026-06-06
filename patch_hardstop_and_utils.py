#!/usr/bin/env python3
"""
patch_hardstop_and_utils.py — три фикса:

1. cartridge.py — хард-стоп Виктора ОСТАНАВЛИВАЕТ пайплайн
   Сейчас: Виктор вызывается → пайплайн идёт дальше на A05
   Нужно: Виктор вызывается → пайплайн ждёт команды CONTINUE

2. cartridge.py — save_before_stop: файлы пишутся ДО остановки
   (патч из прошлой сессии, применяем напрямую в репо-версию)

3. utils.py — AttributeError: 'list' object has no attribute 'get'
   В _validate_asset_ids() нет проверки типа selected
"""

import sys
import shutil
import py_compile
import tempfile
from pathlib import Path
from datetime import datetime

DRY_RUN = "--dry-run" in sys.argv
BACKUP_DIR = Path("_patch_backups") / f"hardstop_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

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
# ПАТЧ 1: cartridge.py — хард-стоп Виктора останавливает пайплайн
# ══════════════════════════════════════════════════════════════════

HARDSTOP_OLD = """                # ── Виктор на ХАРД-СТОПе (независимо от checkpoint_after) ──
                # PATCH audit-sprint19 [1]: вынесен из-под checkpoint_after.
                # hard_stop — отдельный механизм, checkpoint_after — отдельный.
                _hard_stop = self.manifest.hard_stop
                if (
                    _hard_stop.get("after_agent") == worker_id
                    and "victor" in _hard_stop.get("residents", [])
                ):
                    try:
                        from studio.residents_manager import run_victor_critique
                        print(f"[VICTOR] ⚡ Запускаю критику после {worker_id}...")
                        critique = run_victor_critique(
                            chain_data=previous_output,
                            dept=self.slot_id,
                            knowledge=_hard_stop.get("knowledge", []),
                            web_search=_hard_stop.get("web_search", False),
                        )
                        self.state["victor_critique"] = critique
                        self.state["victor_ready"] = True
                        await self.callbacks.on_victor_ready(
                            self.slot_id, critique
                        )
                        print(f"[VICTOR] ✅ Вердикт: {critique.get('verdict', '?')}")
                    except Exception as _ve:
                        print(f"[VICTOR] ❌ Ошибка: {_ve}")
                # ── END Виктор ──

                # Checkpoint?"""

HARDSTOP_NEW = """                # ── Виктор на ХАРД-СТОПе (независимо от checkpoint_after) ──
                # PATCH audit-sprint19 [1]: вынесен из-под checkpoint_after.
                # hard_stop — отдельный механизм, checkpoint_after — отдельный.
                _hard_stop = self.manifest.hard_stop
                if (
                    _hard_stop.get("after_agent") == worker_id
                    and "victor" in _hard_stop.get("residents", [])
                ):
                    try:
                        from studio.residents_manager import run_victor_critique
                        print(f"[VICTOR] ⚡ Запускаю критику после {worker_id}...")
                        critique = run_victor_critique(
                            chain_data=previous_output,
                            dept=self.slot_id,
                            knowledge=_hard_stop.get("knowledge", []),
                            web_search=_hard_stop.get("web_search", False),
                        )
                        self.state["victor_critique"] = critique
                        self.state["victor_ready"] = True
                        await self.callbacks.on_victor_ready(
                            self.slot_id, critique
                        )
                        print(f"[VICTOR] ✅ Вердикт: {critique.get('verdict', '?')}")
                    except Exception as _ve:
                        print(f"[VICTOR] ❌ Ошибка: {_ve}")

                    # ПАТЧ hardstop: Виктор = ПАУЗА, не просто информация.
                    # Пайплайн останавливается — Шеф читает критику.
                    # Нажать CONTINUE чтобы идти дальше (A05+).
                    self.state["paused_at"] = worker_id
                    self.state["paused_output"] = previous_output
                    await self.callbacks.on_status(
                        self.slot_id,
                        f"⚡ Виктор дал оценку. Читай критику — нажми CONTINUE чтобы продолжить.",
                        "warning",
                    )
                    await self.callbacks.on_pipeline_done(
                        self.slot_id, self.state.get("results", {})
                    )
                    return  # ← СТОП. Возобновление через CONTINUE
                # ── END Виктор ──

                # Checkpoint?"""


# ══════════════════════════════════════════════════════════════════
# ПАТЧ 2: cartridge.py — save_before_stop (hook "stop" → файлы сначала)
# ══════════════════════════════════════════════════════════════════

SAVE_OLD = """                # ═══ HOOK: on_after_agent ═══
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

SAVE_NEW = """                # ═══ HOOK: on_after_agent ═══
                hook_result = self._call_hook("on_after_agent", self.state, worker_id, human_text, meta)
                _stop_after_save = False
                if hook_result and isinstance(hook_result, dict):
                    if hook_result.get("action") == "stop":  # patch_sprint20_smm
                        print(f"[HOOKS] ⏹ Пайплайн остановлен после {worker_id}.")
                        await self.callbacks.on_status(
                            self.slot_id, f"Стоп после {worker_id}.", "info"
                        )
                        # Не делаем break сразу — сначала сохраняем файл агента
                        _stop_after_save = True
                    else:
                        human_text = hook_result.get("human_text", human_text)
                        meta = hook_result.get("meta", meta)

                # Обрабатываем результат
                human_text, previous_output, ghost_ids = await process_agent_result("""

SAVE_BREAK_OLD = """                await self.callbacks.on_viewer_update(
                    self.slot_id, worker_id,
                    f"# {label} ({worker_id})\\n\\n{human_text}"
                )

                # ── Виктор на ХАРД-СТОПе"""

SAVE_BREAK_NEW = """                await self.callbacks.on_viewer_update(
                    self.slot_id, worker_id,
                    f"# {label} ({worker_id})\\n\\n{human_text}"
                )

                # Файл записан — теперь можно остановиться если хук просил
                if _stop_after_save:
                    break

                # ── Виктор на ХАРД-СТОПе"""


# ══════════════════════════════════════════════════════════════════
# ПАТЧ 3: utils.py — защита от list в _validate_asset_ids
# ══════════════════════════════════════════════════════════════════

UTILS_OLD = """    for item in selected.get(cat, []):"""

UTILS_NEW = """    # ПАТЧ hardstop: selected может быть list (если агент вернул массив вместо dict)
    if not isinstance(selected, dict):
        selected = {}
    for item in selected.get(cat, []):"""


def main():
    print("=" * 60)
    print("ПАТЧ: Хард-стоп Виктора + save_before_stop + utils fix")
    print("=" * 60)
    if DRY_RUN:
        print("DRY-RUN\n")

    cartridge = Path("studio/cartridge.py")
    utils     = Path("studio/workshop/utils.py")

    print("\n[1/4] cartridge.py — Виктор = ПАУЗА (return вместо continue)")
    apply(cartridge, HARDSTOP_OLD, HARDSTOP_NEW,
          "hard_stop останавливает пайплайн, CONTINUE продолжает")

    print("\n[2/4] cartridge.py — save_before_stop (флаг вместо break)")
    apply(cartridge, SAVE_OLD, SAVE_NEW,
          "_stop_after_save откладывает break")

    print("\n[3/4] cartridge.py — break после viewer_update")
    apply(cartridge, SAVE_BREAK_OLD, SAVE_BREAK_NEW,
          "break после записи файла")

    print("\n[4/4] utils.py — защита от list в _validate_asset_ids")
    apply(utils, UTILS_OLD, UTILS_NEW,
          "isinstance(selected, dict) перед .get()")

    print("\n" + "=" * 60)
    if not DRY_RUN:
        print("✅ Готово! Перезапусти: python main.py")
        print()
        print("Что изменилось:")
        print("  • Виктор после A04 = ПАУЗА. Читаешь критику.")
        print("  • Нажимаешь CONTINUE → идёт дальше на A05+")
        print("  • Файлы агентов пишутся ДО остановки (content_plan)")
        print("  • utils.py не падает если агент вернул list вместо dict")
    else:
        print("DRY-RUN завершён.")

if __name__ == "__main__":
    main()
