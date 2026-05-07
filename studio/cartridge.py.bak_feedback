# studio/cartridge.py — Ядро картриджной архитектуры
# Студия «Шесть Пальцев» · 2026
#
# Картридж = самостоятельный цех с собственным pipeline.
# Студия = шасси + N слотов для картриджей.
# Каждый картридж описан через manifest.json и реализует CartridgeInterface.
#
# НИЧЕГО НЕ ЛОМАЕТ — ui.py работает как раньше.
# Это новый слой ПОВЕРХ существующей архитектуры.

from __future__ import annotations

import json
import asyncio
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Any, Callable, Awaitable

from studio.modules_registry import (
    MODULES_DIR,
    get_worker_prompt, get_worker_info, get_worker_knowledge,
    get_dept_workers, get_dept_all_workers,
    DEPT_PIPELINE_CONFIG,
)


# ═══════════════════════════════════════════════════════════
# MANIFEST — описание картриджа (читается из manifest.json)
# ═══════════════════════════════════════════════════════════

@dataclass
class CartridgeManifest:
    """Описание картриджа — загружается из manifest.json в папке модуля."""
    id: str                          # Уникальный ID модуля: "turbo", "living_book"
    label: str                       # Человекочитаемое: "⚡ TURBO Шортсы"
    icon: str = "🔧"                 # Иконка
    version: str = "1.0"

    # Фазы пайплайна: {"PRE-PROD": ["A01","A02",...], ...}
    phases: dict[str, list[str]] = field(default_factory=dict)

    # Checkpoint-ы: после каких агентов ставить паузу
    checkpoint_after: list[str] = field(default_factory=list)

    # Ревизионный цикл (A00a → A00 для living_book)
    revision_loop: Optional[dict] = None

    # TURBO-режим: какие агенты, какие параллельно
    turbo_workers: list[str] = field(default_factory=list)
    turbo_parallel: list[list[str]] = field(default_factory=list)

    # Режим работы: stop_after, описание
    stop_after: Optional[int] = None
    description: str = ""

    # Run type — для совместимости с PIPELINE_MODES
    run_type: str = ""

    @classmethod
    def load(cls, module_id: str) -> "CartridgeManifest":
        """Загружает manifest.json из папки модуля."""
        manifest_path = MODULES_DIR / module_id / "manifest.json"
        if not manifest_path.exists():
            # Fallback: строим из существующих данных
            return cls._build_from_legacy(module_id)

        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        return cls(
            id=data.get("id", module_id),
            label=data.get("label", module_id),
            icon=data.get("icon", "🔧"),
            version=data.get("version", "1.0"),
            phases=data.get("phases", {}),
            checkpoint_after=data.get("checkpoint_after", []),
            revision_loop=data.get("revision_loop"),
            turbo_workers=data.get("turbo_workers", []),
            turbo_parallel=data.get("turbo_parallel", []),
            stop_after=data.get("stop_after"),
            description=data.get("description", ""),
            run_type=data.get("run_type", module_id),
        )

    @classmethod
    def _build_from_legacy(cls, module_id: str) -> "CartridgeManifest":
        """Строит manifest из существующих info.json + DEPT_PIPELINE_CONFIG."""
        info_path = MODULES_DIR / module_id / "info.json"
        info = {}
        if info_path.exists():
            try:
                info = json.loads(info_path.read_text(encoding="utf-8"))
            except Exception:
                pass

        # Фазы из modules_registry
        phases = {}
        config = DEPT_PIPELINE_CONFIG.get(module_id)
        if config:
            phases = config.get("phases", {})
        else:
            # Дефолт 3×4
            phases = dict(get_dept_workers(module_id))

        return cls(
            id=module_id,
            label=info.get("label", module_id),
            icon=info.get("icon", "🔧"),
            phases=phases,
            run_type=module_id,
        )

    def get_all_agents(self) -> list[str]:
        """Плоский список всех агентов в порядке фаз."""
        result = []
        for agents in self.phases.values():
            result.extend(agents)
        return result

    def get_agent_phase(self, agent_id: str) -> Optional[str]:
        """Возвращает название фазы для агента."""
        for phase_name, agents in self.phases.items():
            if agent_id in agents:
                return phase_name
        return None


# ═══════════════════════════════════════════════════════════
# CALLBACKS — интерфейс связи картриджа с UI
# ═══════════════════════════════════════════════════════════

class PipelineCallbacks:
    """Интерфейс обратного вызова для UI.

    UI реализует этот класс и передаёт в CartridgeRunner.
    Pipeline вызывает callbacks вместо прямых ui.notify / avatars_ref.

    Это РАЗДЕЛЯЕТ логику пайплайна от конкретного UI-фреймворка.
    Картридж можно запустить без NiceGUI (тесты, CLI, API).
    """

    async def on_pipeline_start(self, slot_id: str, run_type: str):
        """Пайплайн начался."""
        pass

    async def on_pipeline_done(self, slot_id: str, results: dict):
        """Пайплайн завершился."""
        pass

    async def on_pipeline_error(self, slot_id: str, error: str):
        """Критическая ошибка пайплайна."""
        pass

    async def on_agent_start(self, slot_id: str, worker_id: str, label: str, phase: str):
        """Агент начал работу."""
        pass

    async def on_agent_done(
        self, slot_id: str, worker_id: str, label: str,
        human_text: str, meta: dict, ghost_ids: list[str]
    ):
        """Агент завершил работу."""
        pass

    async def on_agent_error(self, slot_id: str, worker_id: str, error: str):
        """Ошибка агента."""
        pass

    async def on_agent_retry(self, slot_id: str, worker_id: str, reason: str):
        """Агент перезапускается."""
        pass

    async def on_revision_loop(
        self, slot_id: str, reviewer_id: str, return_to: str,
        loop_number: int, max_loops: int, notes: str
    ):
        """Ревизионный цикл: ревьюер вернул задачу."""
        pass

    async def on_revision_approved(self, slot_id: str, reviewer_id: str):
        """Ревизия одобрена."""
        pass

    async def on_checkpoint(
        self, slot_id: str, worker_id: str, label: str
    ) -> bool:
        """Checkpoint: пауза перед продолжением.
        Возвращает True = продолжить, False = остановить.
        """
        return True

    async def on_status(self, slot_id: str, message: str, level: str = "info"):
        """Статусное сообщение: info, warning, positive, negative."""
        pass

    async def on_viewer_update(self, slot_id: str, worker_id: str, content: str):
        """Обновление просмотрщика результатов."""
        pass

    async def on_parallel_start(self, slot_id: str, agent_ids: list[str]):
        """Параллельный запуск группы агентов (TURBO)."""
        pass

    async def on_parallel_done(self, slot_id: str, agent_ids: list[str], results: list):
        """Параллельная группа завершилась."""
        pass


# ═══════════════════════════════════════════════════════════
# CARTRIDGE RUNNER — запуск пайплайна по manifest
# ═══════════════════════════════════════════════════════════

class CartridgeRunner:
    """Запускает пайплайн картриджа по его manifest.json.

    Заменяет run_pipeline() и turbo_pipeline() из ui.py.
    Вся бизнес-логика здесь, UI — через callbacks.

    Использование:
        manifest = CartridgeManifest.load("turbo")
        runner = CartridgeRunner(manifest, state, callbacks, slot_id="turbo_1")
        await runner.run()
        # или
        await runner.run_turbo()
    """

    def __init__(
        self,
        manifest: CartridgeManifest,
        state: dict,
        callbacks: PipelineCallbacks,
        slot_id: str = "",
    ):
        self.manifest = manifest
        self.state = state
        self.callbacks = callbacks
        self.slot_id = slot_id or manifest.id
        self._revision_count = 0
        self._hooks = self._load_hooks()

    async def run(
        self,
        from_worker: Optional[str] = None,
        with_chat_context: bool = False,
    ):
        """Запуск полного пайплайна картриджа.

        Логика:
        1. Проходим по всем агентам из manifest.phases
        2. На checkpoint_after — вызываем callbacks.on_checkpoint
        3. Если есть revision_loop — обрабатываем ревизии
        4. Каждый шаг: build_context → hooks.on_before_agent → call_agent → hooks.on_after_agent → process_result
        """
        from studio.workshop.pipeline import (
            build_settings_ctx, build_files_ctx,
            build_agent_context, call_agent, process_agent_result,
            summarize_session,
        )

        all_agents = self.manifest.get_all_agents()
        if not all_agents:
            await self.callbacks.on_pipeline_error(self.slot_id, "Нет агентов в картридже")
            return

        # Определяем стартовую позицию
        start_index = 0
        if from_worker:
            for i, w in enumerate(all_agents):
                if w == from_worker:
                    start_index = i
                    break

        run_type = self.manifest.run_type or self.manifest.id
        client_slug = self.state.get("current_client", "_sandbox")
        run_date = self.state.get("run_date", "")
        settings_ctx = build_settings_ctx(self.state)
        files_ctx = build_files_ctx(self.state)
        previous_output = ""

        await self.callbacks.on_pipeline_start(self.slot_id, run_type)

        i = start_index
        while i < len(all_agents):
            worker_id = all_agents[i]

            # stop_after check
            if self.manifest.stop_after and i >= self.manifest.stop_after:
                await self.callbacks.on_status(
                    self.slot_id,
                    f"Пайплайн остановлен после {self.manifest.stop_after} агентов (stop_after).",
                    "info",
                )
                break

            # Rewind check (ревизионный цикл)
            rewind_to = self.state.get("_rewind_to")
            if rewind_to:
                self.state.pop("_rewind_to", None)
                for j, w in enumerate(all_agents):
                    if w == rewind_to:
                        i = j
                        worker_id = w
                        break

            info = get_worker_info(worker_id)
            label = info.get("label", worker_id) if info else worker_id
            phase = self.manifest.get_agent_phase(worker_id) or ""

            await self.callbacks.on_agent_start(self.slot_id, worker_id, label, phase)

            try:
                # Собираем контекст
                anchor_ctx = ""
                if with_chat_context and worker_id == (from_worker or ""):
                    chat_text = "\n".join([
                        f"{m.get('role','')}: {m.get('content','')[:200]}"
                        for m in self.state.get("chat_history", [])[-10:]
                    ])
                    if chat_text:
                        anchor_ctx = f"=== КОНТЕКСТ ЧАТА ===\n{chat_text}\n"

                context = build_agent_context(
                    self.state, worker_id, client_slug,
                    settings_ctx, files_ctx, previous_output,
                    anchor_ctx=anchor_ctx,
                    run_mode=run_type,
                )

                # ═══ HOOK: on_before_agent ═══
                context = self._call_hook("on_before_agent", self.state, worker_id, context) or context

                # Вызываем агента
                human_text, meta, raw_result = await call_agent(
                    self.state, worker_id, context
                )

                # Ревизионный цикл
                if self.manifest.revision_loop and self._handle_revision(
                    worker_id, meta, human_text, raw_result, previous_output
                ):
                    # _rewind_to уже установлен, цикл продолжится
                    i += 1
                    continue

                # ═══ HOOK: on_after_agent ═══
                hook_result = self._call_hook("on_after_agent", self.state, worker_id, human_text, meta)
                if hook_result and isinstance(hook_result, dict):
                    human_text = hook_result.get("human_text", human_text)
                    meta = hook_result.get("meta", meta)

                # Обрабатываем результат
                human_text, previous_output, ghost_ids = process_agent_result(
                    self.state, worker_id, human_text, meta, raw_result,
                    client_slug, run_date, run_type, previous_output,
                )

                await self.callbacks.on_agent_done(
                    self.slot_id, worker_id, label,
                    human_text, meta, ghost_ids,
                )

                await self.callbacks.on_viewer_update(
                    self.slot_id, worker_id,
                    f"# {label} ({worker_id})\n\n{human_text}"
                )

                # Checkpoint?
                if worker_id in self.manifest.checkpoint_after:
                    should_continue = await self.callbacks.on_checkpoint(
                        self.slot_id, worker_id, label
                    )
                    if not should_continue:
                        # Сохраняем состояние паузы
                        self.state["paused_at"] = worker_id
                        self.state["paused_context"] = context
                        self.state["paused_output"] = previous_output
                        await self.callbacks.on_status(
                            self.slot_id,
                            f"Checkpoint после {label}. Пайплайн на паузе.",
                            "warning",
                        )
                        return

            except Exception as e:
                import traceback
                traceback.print_exc()
                await self.callbacks.on_agent_error(
                    self.slot_id, worker_id, str(e)
                )

            i += 1

        # Пайплайн завершён
        await self.callbacks.on_pipeline_done(self.slot_id, self.state.get("results", {}))

        # Суммаризация сессии
        try:
            await summarize_session(self.state, client_slug, run_date, run_type)
        except Exception as e:
            print(f"[CARTRIDGE] Ошибка суммаризации: {e}")

    async def run_turbo(self):
        """Запуск TURBO-режима: короткий пайплайн с параллелизмом.

        Использует turbo_workers и turbo_parallel из manifest:
        - turbo_workers: ["A01", "A02", "A03", "A04", "A05"]
        - turbo_parallel: [["A02", "A03"]]  # эти идут параллельно
        """
        from studio.workshop.pipeline import (
            build_settings_ctx, build_files_ctx,
            build_agent_context, call_agent, process_agent_result,
        )

        turbo_agents = self.manifest.turbo_workers
        if not turbo_agents:
            # Fallback: первые 5 агентов
            turbo_agents = self.manifest.get_all_agents()[:5]

        parallel_groups = self.manifest.turbo_parallel
        run_type = "turbo"
        client_slug = self.state.get("current_client", "_sandbox")
        run_date = self.state.get("run_date", "")
        settings_ctx = build_settings_ctx(self.state)
        files_ctx = build_files_ctx(self.state)
        previous_output = ""

        await self.callbacks.on_pipeline_start(self.slot_id, run_type)

        i = 0
        while i < len(turbo_agents):
            worker_id = turbo_agents[i]

            # Проверяем: входит ли этот агент в параллельную группу?
            parallel_group = None
            for pg in parallel_groups:
                if worker_id in pg:
                    parallel_group = pg
                    break

            if parallel_group and worker_id == parallel_group[0]:
                # Параллельный запуск группы
                await self.callbacks.on_parallel_start(self.slot_id, parallel_group)

                async def _run_one(wid: str):
                    _info = get_worker_info(wid)
                    _label = _info.get("label", wid) if _info else wid
                    await self.callbacks.on_agent_start(self.slot_id, wid, _label, "TURBO")
                    ctx = build_agent_context(
                        self.state, wid, client_slug,
                        settings_ctx, files_ctx, previous_output,
                        run_mode=run_type,
                    )
                    return await call_agent(self.state, wid, ctx)

                tasks = [_run_one(wid) for wid in parallel_group]
                results = await asyncio.gather(*tasks, return_exceptions=True)

                for j, wid in enumerate(parallel_group):
                    _info = get_worker_info(wid)
                    _label = _info.get("label", wid) if _info else wid
                    if isinstance(results[j], Exception):
                        await self.callbacks.on_agent_error(self.slot_id, wid, str(results[j]))
                    else:
                        h_text, meta, raw = results[j]
                        h_text, previous_output, ghost_ids = process_agent_result(
                            self.state, wid, h_text, meta, raw,
                            client_slug, run_date, run_type, previous_output,
                        )
                        await self.callbacks.on_agent_done(
                            self.slot_id, wid, _label, h_text, meta, ghost_ids
                        )

                await self.callbacks.on_parallel_done(self.slot_id, parallel_group, results)
                # Перескакиваем всю параллельную группу
                i += len(parallel_group)
                continue

            elif parallel_group and worker_id != parallel_group[0]:
                # Этот агент часть группы, но не первый — уже обработан
                i += 1
                continue

            # Обычный последовательный агент
            info = get_worker_info(worker_id)
            label = info.get("label", worker_id) if info else worker_id

            await self.callbacks.on_agent_start(self.slot_id, worker_id, label, "TURBO")

            try:
                context = build_agent_context(
                    self.state, worker_id, client_slug,
                    settings_ctx, files_ctx, previous_output,
                    run_mode=run_type,
                )
                human_text, meta, raw_result = await call_agent(
                    self.state, worker_id, context
                )
                human_text, previous_output, ghost_ids = process_agent_result(
                    self.state, worker_id, human_text, meta, raw_result,
                    client_slug, run_date, run_type, previous_output,
                )
                await self.callbacks.on_agent_done(
                    self.slot_id, worker_id, label, human_text, meta, ghost_ids
                )
            except Exception as e:
                await self.callbacks.on_agent_error(self.slot_id, worker_id, str(e))

            i += 1

        await self.callbacks.on_pipeline_done(self.slot_id, self.state.get("results", {}))

    def _handle_revision(
        self, worker_id: str, meta: dict, human_text: str,
        raw_result: str, previous_output: str,
    ) -> bool:
        """Обрабатывает ревизионный цикл. Возвращает True если rewind активирован."""
        rev = self.manifest.revision_loop
        if not rev:
            return False
        if worker_id != rev.get("reviewer"):
            return False

        status_field = rev.get("status_field", "verdict")
        revision_value = rev.get("revision_value", "REVISION")
        approved_value = rev.get("approved_value", "APPROVED")
        max_loops = rev.get("max_loops", 3)
        return_to = rev.get("return_to", "A00")

        verdict = (
            meta.get(status_field)
            or meta.get("my_output", {}).get(status_field, "")
        ).upper().strip()

        if verdict == revision_value and self._revision_count < max_loops:
            self._revision_count += 1
            rev_notes = (
                meta.get("revision_notes")
                or meta.get("my_output", {}).get("revision_notes", "")
                or human_text[:500]
            )

            # ═══ HOOK: on_revision_notes ═══
            rev_notes = self._call_hook(
                "on_revision_notes", self.state, rev_notes, self._revision_count
            ) or rev_notes

            # Сохраняем результат ревьюера
            self.state["results"][worker_id] = {
                "text": human_text, "meta": meta, "raw": raw_result
            }

            # Rewind
            self.state["_rewind_to"] = return_to

            # Уведомляем UI через корутину
            asyncio.ensure_future(
                self.callbacks.on_revision_loop(
                    self.slot_id, worker_id, return_to,
                    self._revision_count, max_loops, rev_notes
                )
            )

            print(f"[REVISION] {worker_id} → {return_to}: loop {self._revision_count}/{max_loops}")
            return True

        elif verdict == approved_value or self._revision_count >= max_loops:
            self._revision_count = 0
            asyncio.ensure_future(
                self.callbacks.on_revision_approved(self.slot_id, worker_id)
            )
            return False

        return False

    # ═══════════════════════════════════════════════════════
    # HOOKS — загрузка и вызов кастомной логики картриджа
    # ═══════════════════════════════════════════════════════

    def _load_hooks(self):
        """Загружает hooks.py из папки модуля.

        Ищет: studio/modules/{module_id}/hooks.py
        Если файл есть — импортирует как модуль.
        Если нет — возвращает None (хуки необязательны).
        """
        hooks_path = MODULES_DIR / self.manifest.id / "hooks.py"
        if not hooks_path.exists():
            return None

        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location(
                f"hooks_{self.manifest.id}", str(hooks_path)
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            print(f"[HOOKS] Загружены хуки: {self.manifest.id}")
            return module
        except Exception as e:
            print(f"[HOOKS] Ошибка загрузки хуков {self.manifest.id}: {e}")
            return None

    def _call_hook(self, hook_name: str, *args, **kwargs):
        """Безопасный вызов хука. Если хук не существует — ничего не делает."""
        if not self._hooks:
            return None

        hook_fn = getattr(self._hooks, hook_name, None)
        if not hook_fn or not callable(hook_fn):
            return None

        try:
            return hook_fn(*args, **kwargs)
        except Exception as e:
            print(f"[HOOKS] Ошибка в {self.manifest.id}.{hook_name}: {e}")
            import traceback
            traceback.print_exc()
            return None


# ═══════════════════════════════════════════════════════════
# CONVENIENCE: быстрый запуск картриджа
# ═══════════════════════════════════════════════════════════

def load_cartridge(module_id: str) -> CartridgeManifest:
    """Загрузить картридж по ID модуля."""
    return CartridgeManifest.load(module_id)


async def run_cartridge(
    module_id: str,
    state: dict,
    callbacks: PipelineCallbacks,
    slot_id: str = "",
    turbo: bool = False,
    from_worker: Optional[str] = None,
):
    """Удобная функция: загрузить картридж и запустить."""
    manifest = CartridgeManifest.load(module_id)
    runner = CartridgeRunner(manifest, state, callbacks, slot_id=slot_id or module_id)
    if turbo:
        await runner.run_turbo()
    else:
        await runner.run(from_worker=from_worker)
