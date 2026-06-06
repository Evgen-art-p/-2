# studio/workshop/nicegui_callbacks.py — Мост: CartridgeRunner ↔ NiceGUI
# Студия «Шесть Пальцев» · 2026
#
# Все UI-вызовы обёрнуты в try/except.
# Если клиент удалён (вкладка закрыта/обновлена во время рана) —
# ошибка молча игнорируется, ран продолжается, результат пишется в файлы.

from __future__ import annotations

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
        self._update_runs = update_runs_display_fn

    # ── Pipeline lifecycle ────────────────────────────────

    async def on_pipeline_start(self, slot_id: str, run_type: str):
        self.state["pipeline_running"] = True
        try:
            with self._client:
                self._update_status()
                emoji = "⚡" if run_type == "turbo" else "🚀"
                ui.notify(f"{emoji} Пайплайн запущен!", type="info")
        except Exception:
            pass

    async def on_pipeline_done(self, slot_id: str, results: dict):
        self.state["pipeline_running"] = False
        try:
            with self._client:
                self._update_status()
                self._update_runs()
                ui.notify("🎉 Пайплайн завершён!", type="positive")
        except Exception:
            pass

    async def on_pipeline_error(self, slot_id: str, error: str):
        self.state["pipeline_running"] = False
        try:
            with self._client:
                self._update_status()
                ui.notify(f"❌ Ошибка пайплайна: {error}", type="negative")
        except Exception:
            pass

    # ── Agent lifecycle ───────────────────────────────────

    async def on_agent_start(self, slot_id: str, worker_id: str, label: str, phase: str):
        try:
            with self._client:
                if worker_id in self.avatars_ref['elements']:
                    self.avatars_ref['elements'][worker_id].classes(remove='done')
                    self.avatars_ref['elements'][worker_id].classes(add='working')
                tag = f" [{phase}]" if phase else ""
                ui.notify(f"🤖 {label}{tag}...", type="info")
        except Exception:
            pass

    async def on_agent_done(
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
            pass

    async def on_agent_error(self, slot_id: str, worker_id: str, error: str):
        try:
            with self._client:
                if worker_id in self.avatars_ref['elements']:
                    self.avatars_ref['elements'][worker_id].classes(remove='working')
                ui.notify(f"❌ {worker_id}: {error}", type="negative")
        except Exception:
            pass

    async def on_agent_retry(self, slot_id: str, worker_id: str, reason: str):
        try:
            with self._client:
                ui.notify(f"🔁 {worker_id} retry: {reason}", type="warning")
        except Exception:
            pass

    # ── Виктор ───────────────────────────────────────────

    async def on_victor_ready(self, slot_id: str, critique: dict):
        self.state["victor_ready"] = True
        self.state["victor_critique"] = critique
        try:
            with self._client:
                victor_el = self.avatars_ref["elements"].get("VICTOR")
                if victor_el:
                    victor_el.classes(add="victor-ready")
                ui.notify("⚡ Виктор готов — посмотри критику", type="warning", timeout=6000)
        except Exception:
            pass

    # ── Viewer ────────────────────────────────────────────

    async def on_viewer_update(self, slot_id: str, worker_id: str, content: str):
        try:
            with self._client:
                self._update_viewer(content)
        except Exception:
            pass

    # ── Status / notifications ────────────────────────────

    async def on_status(self, slot_id: str, message: str, level: str = "info"):
        try:
            with self._client:
                ui.notify(message, type=level)
        except Exception:
            pass

    # ── Revision loop ─────────────────────────────────────

    async def on_revision_loop(
        self, slot_id: str, reviewer_id: str, return_to: str,
        loop_number: int, max_loops: int, notes: str
    ):
        try:
            with self._client:
                ui.notify(
                    f"🔄 Ревизия #{loop_number}/{max_loops}. Возврат к {return_to}.",
                    type="warning", timeout=8000
                )
        except Exception:
            pass

    async def on_revision_approved(self, slot_id: str, reviewer_id: str):
        try:
            with self._client:
                ui.notify("✅ Ревизия одобрена!", type="positive")
        except Exception:
            pass

    # ── Checkpoint ────────────────────────────────────────

    async def on_checkpoint(self, slot_id: str, worker_id: str, label: str) -> bool:
        try:
            with self._client:
                ui.notify(
                    f"⏸ Checkpoint после {label}. Нажмите CONTINUE для продолжения.",
                    type="warning", timeout=10000
                )
                self._update_runs()
        except Exception:
            pass
        return False

    # ── Parallel (TURBO) ──────────────────────────────────

    async def on_parallel_start(self, slot_id: str, agent_ids: list[str]):
        try:
            with self._client:
                names = " + ".join(agent_ids)
                ui.notify(f"⚡ {names} — ПАРАЛЛЕЛЬНО!", type="info")
        except Exception:
            pass

    async def on_parallel_done(self, slot_id: str, agent_ids: list[str], results: list):
        try:
            with self._client:
                ok = sum(1 for r in results if not isinstance(r, Exception))
                fail = len(results) - ok
                if fail:
                    ui.notify(f"⚠️ Параллельный блок: {ok} ок, {fail} ошибок", type="warning")
        except Exception:
            pass
