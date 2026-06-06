"""
patch_ui_safety.py
Два фикса:

1. nicegui_callbacks.py — все UI-вызовы обёрнуты в try/except.
   Если клиент удалён (вкладка закрыта) — молча пропускаем.

2. studio/workshop/ui.py строка 2492 — duration слайдер:
   int(e.value) → int(e.value or 30)
   Защита от None когда слайдер сбрасывается при смене цеха.
"""
import sys, shutil, re
from pathlib import Path
from datetime import datetime

CB_TARGET = Path("studio/workshop/nicegui_callbacks.py")
UI_TARGET = Path("studio/workshop/ui.py")
BACKUP    = Path("_patch_backups")

# ─── Фикс 1: nicegui_callbacks.py — safe UI calls ────────────────────────────

OLD_AGENT_DONE = """    async def on_agent_done(
        self, slot_id: str, worker_id: str, label: str,
        human_text: str, meta: dict, ghost_ids: list[str]
    ):
        with self._client:
            if worker_id in self.avatars_ref['elements']:
                self.avatars_ref['elements'][worker_id].classes(remove='working')
                self.avatars_ref['elements'][worker_id].classes(add='done')
            ui.notify(f"✅ {label}!", type="positive")

            if ghost_ids:
                warn = f"⚠️ {worker_id}: галлюцинации asset_id ({len(ghost_ids)}): " + ", ".join(ghost_ids[:5])
                ui.notify(warn, type="warning", timeout=8000)"""

NEW_AGENT_DONE = """    async def on_agent_done(
        self, slot_id: str, worker_id: str, label: str,
        human_text: str, meta: dict, ghost_ids: list[str]
    ):
        try:
            with self._client:
                if worker_id in self.avatars_ref['elements']:
                    self.avatars_ref['elements'][worker_id].classes(remove='working')
                    self.avatars_ref['elements'][worker_id].classes(add='done')
                ui.notify(f"✅ {label}!", type="positive")

                if ghost_ids:
                    warn = f"⚠️ {worker_id}: галлюцинации asset_id ({len(ghost_ids)}): " + ", ".join(ghost_ids[:5])
                    ui.notify(warn, type="warning", timeout=8000)
        except Exception:
            pass  # Клиент закрылся — не страшно"""

OLD_VIEWER_UPDATE = """    async def on_viewer_update(self, slot_id: str, worker_id: str, content: str):
        with self._client:
            self._update_viewer(content)"""

NEW_VIEWER_UPDATE = """    async def on_viewer_update(self, slot_id: str, worker_id: str, content: str):
        try:
            with self._client:
                self._update_viewer(content)
        except Exception:
            pass  # Клиент закрылся — не страшно"""

OLD_AGENT_START = """    async def on_agent_start(self, slot_id: str, worker_id: str, label: str, phase: str):
        with self._client:
            if worker_id in self.avatars_ref['elements']:
                self.avatars_ref['elements'][worker_id].classes(remove='done')
                self.avatars_ref['elements'][worker_id].classes(add='working')
            tag = f" [{phase}]" if phase else ""
            ui.notify(f"🤖 {label}{tag}...", type="info")"""

NEW_AGENT_START = """    async def on_agent_start(self, slot_id: str, worker_id: str, label: str, phase: str):
        try:
            with self._client:
                if worker_id in self.avatars_ref['elements']:
                    self.avatars_ref['elements'][worker_id].classes(remove='done')
                    self.avatars_ref['elements'][worker_id].classes(add='working')
                tag = f" [{phase}]" if phase else ""
                ui.notify(f"🤖 {label}{tag}...", type="info")
        except Exception:
            pass"""

OLD_AGENT_ERROR = """    async def on_agent_error(self, slot_id: str, worker_id: str, error: str):
        with self._client:
            if worker_id in self.avatars_ref['elements']:
                self.avatars_ref['elements'][worker_id].classes(remove='working')
            ui.notify(f"❌ {worker_id}: {error}", type="negative")"""

NEW_AGENT_ERROR = """    async def on_agent_error(self, slot_id: str, worker_id: str, error: str):
        try:
            with self._client:
                if worker_id in self.avatars_ref['elements']:
                    self.avatars_ref['elements'][worker_id].classes(remove='working')
                ui.notify(f"❌ {worker_id}: {error}", type="negative")
        except Exception:
            pass"""

# ─── Фикс 2: ui.py — duration слайдер None guard ─────────────────────────────

OLD_DURATION = "on_change=lambda e: state['settings'].update({'duration': int(e.value)})"
NEW_DURATION  = "on_change=lambda e: state['settings'].update({'duration': int(e.value or 30)})"


def patch_callbacks(dry_run=False):
    if not CB_TARGET.exists():
        print(f"[ERROR] {CB_TARGET} не найден")
        return False

    content = CB_TARGET.read_text(encoding="utf-8")

    fixes = [
        ("on_agent_done",    OLD_AGENT_DONE,    NEW_AGENT_DONE),
        ("on_viewer_update", OLD_VIEWER_UPDATE,  NEW_VIEWER_UPDATE),
        ("on_agent_start",   OLD_AGENT_START,    NEW_AGENT_START),
        ("on_agent_error",   OLD_AGENT_ERROR,    NEW_AGENT_ERROR),
    ]

    new_content = content
    for label, old, new in fixes:
        if old in new_content:
            new_content = new_content.replace(old, new, 1)
            print(f"  [OK] {label}")
        else:
            print(f"  [SKIP] {label} — уже пропатчено")

    if dry_run or new_content == content:
        return True

    BACKUP.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    shutil.copy2(CB_TARGET, BACKUP / f"nicegui_callbacks.py.bak_{ts}")
    CB_TARGET.write_text(new_content, encoding="utf-8")
    print(f"  → {CB_TARGET} обновлён")
    return True


def patch_ui(dry_run=False):
    if not UI_TARGET.exists():
        print(f"[SKIP] {UI_TARGET} не найден (нормально)")
        return True

    content = UI_TARGET.read_text(encoding="utf-8")

    if OLD_DURATION not in content:
        print(f"  [SKIP] duration guard — уже есть или строка изменилась")
        return True

    new_content = content.replace(OLD_DURATION, NEW_DURATION, 1)

    if dry_run:
        print(f"  [DRY] duration guard применится")
        return True

    BACKUP.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    shutil.copy2(UI_TARGET, BACKUP / f"ui.py.bak_dur_{ts}")
    UI_TARGET.write_text(new_content, encoding="utf-8")
    print(f"  [OK] duration guard → {UI_TARGET}")
    return True


def main():
    dry = "--dry-run" in sys.argv
    print("=== nicegui_callbacks.py ===")
    patch_callbacks(dry_run=dry)
    print("\n=== ui.py ===")
    patch_ui(dry_run=dry)
    if not dry:
        print("\n[DONE] Теперь закрытая вкладка не роняет ран.")

if __name__ == "__main__":
    main()
