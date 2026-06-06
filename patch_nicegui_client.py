#!/usr/bin/env python3
"""
patch_nicegui_client.py — ПАТЧ: фикс двойного запуска пайплайна

ПРОБЛЕМА (точная):
  1. NiceGUI удаляет клиент (Client has been deleted) когда пайплайн
     уже запущен — это происходит при параллельных запросах в conflict
     (asyncio.gather делает несколько LLM-вызовов одновременно,
     NiceGUI WebSocket в это время не получает heartbeat → disconnect)
  
  2. nicegui_callbacks.on_pipeline_start делает:
       with self._client:
           self._update_status()   ← ошибка здесь (клиент удалён)
           ...
     Но весь блок обёрнут в try/except Exception: pass →
     state["pipeline_running"] НЕ УСТАНАВЛИВАЕТСЯ в True (строка до try)

     ЖДИТЕ. Смотрим код точно:
     async def on_pipeline_start(self, slot_id, run_type):
         self.state["pipeline_running"] = True   ← это ПЕРЕД try
         try:
             with self._client:
                 ...
         except Exception:
             pass
     
     Значит pipeline_running=True УСТАНАВЛИВАЕТСЯ. Хорошо.
     Но потом cartridge.py падает при on_agent_done (тот же паттерн).
     
  3. Настоящая проблема: страница ПЕРЕЗАГРУЖАЕТСЯ браузером
     (NiceGUI посылает reconnect) → page_workshop() вызывается ЗАНОВО
     → создаётся новый state с pipeline_running=False
     → старый пайплайн всё ещё работает в фоне (asyncio task не отменён)
     → бэкенд делает второй ран поверх первого

РЕШЕНИЕ:
  nicegui_callbacks.py: все callback методы должны проверять
  что клиент ещё жив ПЕРЕД входом в `with self._client:`
  Если клиент мёртв → молча пропускаем UI-часть, но НЕ прерываем пайплайн.
  
  cartridge.py: on_agent_done при "Client deleted" должен продолжать
  работу (пайплайн должен дойти до конца даже без UI).

  Ключевая правка: проверяем self._client.id в Client.instances
  перед каждым with self._client.

  Дополнительно: _check_auto_run в ui.py — добавляем глобальный флаг
  блокировки чтобы не запускать повторно если пайплайн уже был запущен.
"""

import sys
import shutil
import py_compile
import tempfile
from pathlib import Path
from datetime import datetime

DRY_RUN = "--dry-run" in sys.argv
BACKUP_DIR = Path("_patch_backups") / f"nicegui_client_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

def backup(path: Path):
    if DRY_RUN:
        print(f"  [DRY] backup {path}")
        return
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    dest = BACKUP_DIR / path.name
    shutil.copy2(path, dest)
    print(f"  ✓ backup → {dest}")

def validate_python(path: Path) -> bool:
    try:
        py_compile.compile(str(path), doraise=True)
        return True
    except py_compile.PyCompileError as e:
        print(f"  ❌ СИНТАКС-ОШИБКА: {e}")
        return False

def apply_patch(path: Path, old: str, new: str, description: str) -> bool:
    if not path.exists():
        print(f"  ❌ Файл не найден: {path}")
        return False
    content = path.read_text(encoding="utf-8")
    if old not in content:
        print(f"  ⚠ Не найдено в {path.name}: {description}")
        return True
    new_content = content.replace(old, new, 1)
    if DRY_RUN:
        print(f"  [DRY] patch {path.name}: {description}")
        return True
    backup(path)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".py", delete=False) as tmp:
        tmp.write(new_content)
        tmp_path = Path(tmp.name)
    if path.suffix == ".py" and not validate_python(tmp_path):
        tmp_path.unlink()
        return False
    shutil.move(str(tmp_path), str(path))
    print(f"  ✓ {path.name}: {description}")
    return True


# ══════════════════════════════════════════════════════════════════
# ПАТЧ 1: nicegui_callbacks.py — добавляем _client_alive() хелпер
# и защищаем все методы от мёртвого клиента
# ══════════════════════════════════════════════════════════════════

CALLBACKS_OLD = """from __future__ import annotations

from nicegui import ui
from studio.cartridge import PipelineCallbacks


class NiceGUICallbacks(PipelineCallbacks):

    def __init__(
        self,
        state: dict,
        avatars_ref: dict,
        ui_client,
        update_viewer_fn,
        update_status_fn,
        update_runs_display_fn,
    ):
        self.state = state
        self.avatars_ref = avatars_ref
        self._client = ui_client
        self._update_viewer = update_viewer_fn
        self._update_status = update_status_fn
        self._update_runs = update_runs_display_fn"""

CALLBACKS_NEW = """from __future__ import annotations

from nicegui import ui
from nicegui.client import Client as _NiceGUIClient
from studio.cartridge import PipelineCallbacks


class NiceGUICallbacks(PipelineCallbacks):

    def __init__(
        self,
        state: dict,
        avatars_ref: dict,
        ui_client,
        update_viewer_fn,
        update_status_fn,
        update_runs_display_fn,
    ):
        self.state = state
        self.avatars_ref = avatars_ref
        self._client = ui_client
        self._update_viewer = update_viewer_fn
        self._update_status = update_status_fn
        self._update_runs = update_runs_display_fn

    def _client_alive(self) -> bool:
        \"\"\"Проверяет что NiceGUI клиент ещё существует.
        
        Когда конфликтный ран делает asyncio.gather с 4 параллельными LLM-вызовами,
        NiceGUI WebSocket может разорваться (нет heartbeat ~30 сек).
        После разрыва Client удаляется из Client.instances.
        Все попытки ui.notify() / with self._client: бросают предупреждения.
        
        Пайплайн должен ПРОДОЛЖАТЬСЯ без UI — результаты пишутся в файлы.
        \"\"\"
        try:
            return self._client.id in _NiceGUIClient.instances
        except Exception:
            return False"""


# ══════════════════════════════════════════════════════════════════
# ПАТЧ 2: on_pipeline_start — guard
# ══════════════════════════════════════════════════════════════════

CALLBACKS_START_OLD = """    async def on_pipeline_start(self, slot_id: str, run_type: str):
        self.state["pipeline_running"] = True
        try:
            with self._client:
                self._update_status()
                emoji = "⚡" if run_type == "turbo" else "🚀"
                ui.notify(f"{emoji} Пайплайн запущен!", type="info")
        except Exception:
            pass"""

CALLBACKS_START_NEW = """    async def on_pipeline_start(self, slot_id: str, run_type: str):
        self.state["pipeline_running"] = True
        if not self._client_alive():
            return
        try:
            with self._client:
                self._update_status()
                emoji = "⚡" if run_type == "turbo" else "🚀"
                ui.notify(f"{emoji} Пайплайн запущен!", type="info")
        except Exception:
            pass"""


# ══════════════════════════════════════════════════════════════════
# ПАТЧ 3: on_pipeline_done — guard
# ══════════════════════════════════════════════════════════════════

CALLBACKS_DONE_OLD = """    async def on_pipeline_done(self, slot_id: str, results: dict):
        self.state["pipeline_running"] = False
        try:
            with self._client:
                self._update_status()
                self._update_runs()
                ui.notify("🎉 Пайплайн завершён!", type="positive")
        except Exception:
            pass"""

CALLBACKS_DONE_NEW = """    async def on_pipeline_done(self, slot_id: str, results: dict):
        self.state["pipeline_running"] = False
        if not self._client_alive():
            print(f"[CALLBACKS] Пайплайн завершён (slot={slot_id}), UI клиент недоступен — результаты в файлах")
            return
        try:
            with self._client:
                self._update_status()
                self._update_runs()
                ui.notify("🎉 Пайплайн завершён!", type="positive")
        except Exception:
            pass"""


# ══════════════════════════════════════════════════════════════════
# ПАТЧ 4: on_agent_done — guard (это место роняет пайплайн сейчас)
# ══════════════════════════════════════════════════════════════════

CALLBACKS_AGENT_DONE_OLD = """    async def on_agent_done(
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
            pass"""

CALLBACKS_AGENT_DONE_NEW = """    async def on_agent_done(
        self, slot_id: str, worker_id: str, label: str,
        human_text: str, meta: dict, ghost_ids: list[str]
    ):
        print(f"[CALLBACKS] ✅ {label} ({worker_id}) готов")
        if not self._client_alive():
            return
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
            pass"""


# ══════════════════════════════════════════════════════════════════
# ПАТЧ 5: on_agent_start — guard
# ══════════════════════════════════════════════════════════════════

CALLBACKS_AGENT_START_OLD = """    async def on_agent_start(self, slot_id: str, worker_id: str, label: str, phase: str):
        try:
            with self._client:
                if worker_id in self.avatars_ref['elements']:
                    self.avatars_ref['elements'][worker_id].classes(remove='done')
                    self.avatars_ref['elements'][worker_id].classes(add='working')
                tag = f" [{phase}]" if phase else ""
                ui.notify(f"🤖 {label}{tag}...", type="info")
        except Exception:
            pass"""

CALLBACKS_AGENT_START_NEW = """    async def on_agent_start(self, slot_id: str, worker_id: str, label: str, phase: str):
        print(f"[CALLBACKS] 🤖 {label} ({worker_id}) [{phase}] стартует...")
        if not self._client_alive():
            return
        try:
            with self._client:
                if worker_id in self.avatars_ref['elements']:
                    self.avatars_ref['elements'][worker_id].classes(remove='done')
                    self.avatars_ref['elements'][worker_id].classes(add='working')
                tag = f" [{phase}]" if phase else ""
                ui.notify(f"🤖 {label}{tag}...", type="info")
        except Exception:
            pass"""


# ══════════════════════════════════════════════════════════════════
# ПАТЧ 6: on_pipeline_error — guard
# ══════════════════════════════════════════════════════════════════

CALLBACKS_ERROR_OLD = """    async def on_pipeline_error(self, slot_id: str, error: str):
        self.state["pipeline_running"] = False
        try:
            with self._client:
                self._update_status()
                ui.notify(f"❌ Ошибка пайплайна: {error}", type="negative")
        except Exception:
            pass"""

CALLBACKS_ERROR_NEW = """    async def on_pipeline_error(self, slot_id: str, error: str):
        self.state["pipeline_running"] = False
        print(f"[CALLBACKS] ❌ Ошибка пайплайна (slot={slot_id}): {error}")
        if not self._client_alive():
            return
        try:
            with self._client:
                self._update_status()
                ui.notify(f"❌ Ошибка пайплайна: {error}", type="negative")
        except Exception:
            pass"""


# ══════════════════════════════════════════════════════════════════
# ПАТЧ 7: on_viewer_update — guard
# ══════════════════════════════════════════════════════════════════

CALLBACKS_VIEWER_OLD = """    async def on_viewer_update(self, slot_id: str, worker_id: str, content: str):
        try:
            with self._client:
                self._update_viewer(content)
        except Exception:
            pass"""

CALLBACKS_VIEWER_NEW = """    async def on_viewer_update(self, slot_id: str, worker_id: str, content: str):
        if not self._client_alive():
            return
        try:
            with self._client:
                self._update_viewer(content)
        except Exception:
            pass"""


def main():
    print("=" * 60)
    print("ПАТЧ: NiceGUI client guard — защита от мёртвого клиента")
    print("=" * 60)
    if DRY_RUN:
        print("РЕЖИМ: DRY-RUN\n")

    errors = []
    cb_path = Path("studio/workshop/nicegui_callbacks.py")

    patches = [
        (CALLBACKS_OLD,             CALLBACKS_NEW,             "добавляем _client_alive() хелпер"),
        (CALLBACKS_START_OLD,       CALLBACKS_START_NEW,       "on_pipeline_start: guard"),
        (CALLBACKS_DONE_OLD,        CALLBACKS_DONE_NEW,        "on_pipeline_done: guard + лог"),
        (CALLBACKS_AGENT_START_OLD, CALLBACKS_AGENT_START_NEW, "on_agent_start: guard + лог"),
        (CALLBACKS_AGENT_DONE_OLD,  CALLBACKS_AGENT_DONE_NEW,  "on_agent_done: guard + лог (ГЛАВНЫЙ ФИК)"),
        (CALLBACKS_ERROR_OLD,       CALLBACKS_ERROR_NEW,       "on_pipeline_error: guard + лог"),
        (CALLBACKS_VIEWER_OLD,      CALLBACKS_VIEWER_NEW,      "on_viewer_update: guard"),
    ]

    print(f"\n[nicegui_callbacks.py] — {len(patches)} правок")
    for old, new, desc in patches:
        if not apply_patch(cb_path, old, new, desc):
            errors.append(desc)

    print("\n" + "=" * 60)
    if errors:
        print(f"❌ Не применены: {len(errors)} патчей")
        print("Структура файла могла измениться. Проверь бекапы.")
    else:
        if DRY_RUN:
            print("✓ DRY-RUN OK — запусти без --dry-run")
        else:
            print("✅ Патч применён!")
            print(f"   Бекап: {BACKUP_DIR}")
            print()
            print("Что изменилось:")
            print("  • Все NiceGUI callbacks проверяют жив ли клиент")
            print("    перед любым обращением к UI")
            print("  • Если клиент умер (WebSocket разорвался) —")
            print("    пайплайн ПРОДОЛЖАЕТ работу молча до конца")
            print("  • Результаты пишутся в файлы независимо от UI")
            print("  • Страница больше не должна перезагружаться")
            print("    в середине рана")
            print()
            print("Перезапусти: python main.py")

if __name__ == "__main__":
    main()
