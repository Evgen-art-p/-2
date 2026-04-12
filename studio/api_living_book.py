# studio/api_living_book.py — API генерации Живых Книг
# Студия «Шесть Пальцев» · 2026
#
# Автономный API для Маяка (LIVING_BOOK_APP).
# Маяк отправляет заказ → Сет формирует бриф → Студия прогоняет полный
# пайплайн living_book (18 агентов, ревизия Веры, ДНК, память) → book_package.
#
# НЕ ТРЕБУЕТ открытый браузер — работает headless через CartridgeRunner.
#
# Подключение в main.py:
#   from studio.api_living_book import register_living_book_api
#   register_living_book_api(app)

from __future__ import annotations

import json
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Optional

from pydantic import BaseModel
from nicegui import app

from studio.cartridge import CartridgeManifest, CartridgeRunner, PipelineCallbacks
from studio.workshop.pipeline import (
    build_settings_ctx, build_files_ctx,
    build_agent_context, call_agent, process_agent_result,
    summarize_session,
)
from studio.llm import chat
from studio.modules_registry import get_worker_prompt, get_worker_knowledge


# ═══════════════════════════════════════════════════════════
# REQUEST / RESPONSE MODELS
# ═══════════════════════════════════════════════════════════

class BookRequest(BaseModel):
    """Запрос от Маяка на генерацию книги."""
    child_name: str
    child_age: str
    task_context: str                    # «Женя боится темноты»
    parent_email: Optional[str] = None
    child_interests: Optional[str] = None
    child_notes: Optional[str] = None


class BookResponse(BaseModel):
    """Ответ студии с готовым book_package."""
    status: str          # "completed", "error", "running"
    child_name: str
    book_package: Optional[dict] = None
    run_id: Optional[str] = None
    error: Optional[str] = None
    agents_log: Optional[list] = None
    set_brief: Optional[str] = None      # Бриф от Сета


# ═══════════════════════════════════════════════════════════
# СЕТ — ОРКЕСТРАТОР (Шаг 0)
# ═══════════════════════════════════════════════════════════

async def _call_set(request: BookRequest) -> str:
    """Сет формирует master_brief из сырого запроса родителя.

    Сет — главный оркестратор студии. Он:
    1. Анализирует задачу родителя
    2. Определяет creative_soul (что должен ПОЧУВСТВОВАТЬ ребёнок)
    3. Ставит эмоциональную задачу для пайплайна
    4. Формирует полный бриф для 18 агентов

    Использует промпт Сета и его знания из knowledge/ (set_core.md + set_living_book.md)
    """
    from studio.modules_registry import MODULES_DIR
    from studio.config import BASE_DIR

    set_system = ""
    set_knowledge = ""

    # 1. Промпт Сета из его forge/
    set_prompt_path = MODULES_DIR / "residents" / "003_LEGACY_SET" / "forge" / "prompt.md"
    if set_prompt_path.exists():
        set_system = set_prompt_path.read_text(encoding="utf-8")

    # 2. Знания Сета — из knowledge/ в корне проекта (НЕ из forge/knowledge/)
    knowledge_dir = BASE_DIR / "knowledge"
    if not knowledge_dir.exists():
        knowledge_dir = Path("knowledge")  # fallback — относительный путь

    # Грузим core + модуль living_book
    for filename in ["set_core.md", "set_living_book.md"]:
        kpath = knowledge_dir / filename
        if kpath.exists():
            set_knowledge += kpath.read_text(encoding="utf-8") + "\n\n"
            print(f"[СЕТ] 📚 Загружены знания: {filename} ({kpath.stat().st_size} байт)")

    # Fallback: если knowledge/ не найден — ищем в forge/knowledge/
    if not set_knowledge.strip():
        set_knowledge_dir = MODULES_DIR / "residents" / "003_LEGACY_SET" / "forge" / "knowledge"
        if set_knowledge_dir.exists():
            for f in sorted(set_knowledge_dir.glob("*.md")) + sorted(set_knowledge_dir.glob("*.txt")):
                set_knowledge += f.read_text(encoding="utf-8") + "\n\n"

    # Если промпт пустой — используем set_core.md как system prompt
    if not set_system.strip() or len(set_system.strip()) < 50:
        if set_knowledge.strip():
            # Знания Сета уже содержат полный промпт — используем их
            set_system = set_knowledge
            set_knowledge = ""  # чтобы не дублировать
        else:
            set_system = (
                "Ты — Сет, главный оркестратор студии «Шесть Пальцев».\n"
                "Твоя задача — получить запрос от родителя и сформировать "
                "MASTER BRIEF для цеха Живой Книги.\n\n"
                "Ты определяешь:\n"
                "- Что должен ПОЧУВСТВОВАТЬ ребёнок (creative_soul)\n"
                "- Какой волшебный мир создать\n"
                "- Что категорически нельзя (страх, стыд, насилие)\n"
                "- Ради чего эта история (понимание, принятие, рост)\n"
                "- Эмоциональную дугу: от чего → к чему\n\n"
                "ПРАВИЛА:\n"
                "- Ребёнок может быть незрячим — никаких визуальных заданий\n"
                "- Метод Гиппенрейтер: никогда не давать готовых решений\n"
                "- История должна быть безопасной и терапевтичной\n"
                "- Персонализация: ребёнок узнаёт себя в герое\n"
            )

    # Контекст для Сета
    user_context = f"""=== ЗАКАЗ ОТ РОДИТЕЛЯ ===
Имя ребёнка: {request.child_name}
Возраст: {request.child_age}
Задача/проблема: {request.task_context}
Интересы ребёнка: {request.child_interests or 'не указаны'}
Особенности: {request.child_notes or 'нет'}
Email родителя: {request.parent_email or 'не указан'}
=== КОНЕЦ ЗАКАЗА ===

Сформируй MASTER BRIEF для цеха Живой Книги.

Включи:
1. **creative_soul** — что должен почувствовать ребёнок
2. **magic_world** — какой мир создать (Грондхейм? Другой?)
3. **emotional_arc** — от какого чувства к какому (от тревоги → к уверенности)
4. **forbidden** — что нельзя (конкретно для этого ребёнка и возраста)
5. **key_message** — главное послание
6. **hero_traits** — каким должен быть герой (похож на ребёнка)
7. **age_adaptation** — как адаптировать под возраст
8. **accessibility** — как обеспечить доступность (если незрячий)

Пиши развёрнуто, это бриф для 18 агентов-специалистов.
Каждый из них будет читать твой бриф и работать по нему."""

    print(f"[СЕТ] 🤖 Формирую бриф для {request.child_name}...")

    # Вызываем Сета через LLM
    try:
        # Грондхейм: пробуждаем Сета — он получает свою душу
        try:
            from studio.grondheim_memory import on_agent_wake, on_agent_done
            soul = on_agent_wake("003_LEGACY_SET", "residents")
            if soul:
                user_context = soul + "\n\n" + user_context
        except ImportError:
            pass

        brief = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: chat(set_system, user_context, set_knowledge)
        )

        # Записываем что Сет отработал
        try:
            from studio.grondheim_memory import on_agent_done
            on_agent_done("003_LEGACY_SET", f"Бриф для {request.child_name}: {brief[:100]}", 0.8, "residents")
        except Exception:
            pass

        print(f"[СЕТ] ✅ Бриф готов ({len(brief)} символов)")
        return brief

    except Exception as e:
        print(f"[СЕТ] ❌ Ошибка: {e}")
        # Fallback: формируем бриф программно
        return json.dumps({
            "creative_soul": f"{request.child_name} должен почувствовать себя смелым и любимым",
            "magic_world": "Грондхейм — мир где каждый звук имеет значение",
            "emotional_arc": f"От тревоги ({request.task_context}) → к уверенности и принятию",
            "forbidden": "Страх, стыд, насилие, обесценивание, визуальные задания",
            "key_message": f"{request.child_name} справится!",
            "hero_traits": f"Похож на {request.child_name}, возраст {request.child_age}",
            "age_adaptation": f"Адаптировано для {request.child_age}",
            "accessibility": "100% доступно для незрячих: только звук, тактильность, движение",
            "child": {
                "name": request.child_name,
                "age": request.child_age,
                "interests": request.child_interests or "",
                "notes": request.child_notes or "",
            },
        }, ensure_ascii=False, indent=2)


# ═══════════════════════════════════════════════════════════
# HEADLESS CALLBACKS
# ═══════════════════════════════════════════════════════════

class HeadlessCallbacks(PipelineCallbacks):
    """Callbacks без NiceGUI — для headless API."""

    def __init__(self):
        self.log: list[dict] = []
        self.errors: list[str] = []

    async def on_pipeline_start(self, slot_id, run_type):
        print(f"[API] 🚀 Пайплайн {slot_id} запущен (run_type={run_type})")

    async def on_pipeline_done(self, slot_id, results):
        print(f"[API] 🎉 Пайплайн {slot_id} завершён ({len(results)} результатов)")

    async def on_pipeline_error(self, slot_id, error):
        print(f"[API] ❌ Ошибка: {error}")
        self.errors.append(error)

    async def on_agent_start(self, slot_id, worker_id, label, phase):
        print(f"[API] 🤖 {worker_id} {label} [{phase}]...")
        self.log.append({"agent": worker_id, "label": label, "status": "started"})

    async def on_agent_done(self, slot_id, worker_id, label, human_text, meta, ghost_ids):
        print(f"[API] ✅ {worker_id} {label} (ghosts={len(ghost_ids)})")
        self.log.append({
            "agent": worker_id, "label": label, "status": "done",
            "preview": human_text[:200],
            "ghost_ids": ghost_ids[:3] if ghost_ids else [],
        })

    async def on_agent_error(self, slot_id, worker_id, error):
        print(f"[API] ❌ {worker_id}: {error}")
        self.log.append({"agent": worker_id, "status": "error", "error": str(error)})
        self.errors.append(f"{worker_id}: {error}")

    async def on_revision_loop(self, slot_id, reviewer_id, return_to, loop_number, max_loops, notes):
        print(f"[API] 🔄 Ревизия #{loop_number}/{max_loops}: {reviewer_id} → {return_to}")
        self.log.append({"agent": reviewer_id, "status": "revision", "loop": loop_number})

    async def on_revision_approved(self, slot_id, reviewer_id):
        print(f"[API] ✅ Ревизия одобрена: {reviewer_id}")

    async def on_checkpoint(self, slot_id, worker_id, label) -> bool:
        print(f"[API] ⏭ Checkpoint {worker_id} — пропускаем (API-режим)")
        return True

    async def on_status(self, slot_id, message, level="info"):
        print(f"[API] [{level}] {message}")

    async def on_viewer_update(self, slot_id, worker_id, content):
        pass

    async def on_parallel_start(self, slot_id, agent_ids):
        print(f"[API] ⚡ Параллельно: {' + '.join(agent_ids)}")

    async def on_parallel_done(self, slot_id, agent_ids, results):
        pass


# ═══════════════════════════════════════════════════════════
# BUILD STATE
# ═══════════════════════════════════════════════════════════

def _build_headless_state(request: BookRequest, set_brief: str) -> dict:
    """Создаёт state для CartridgeRunner. Бриф от Сета."""

    run_date = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    project_name = f"livingbook_{request.child_name}_{run_date}"
    project_dir = Path("runs") / project_name
    project_dir.mkdir(parents=True, exist_ok=True)

    return {
        "master_brief": set_brief,       # ← бриф от Сета, НЕ программный JSON
        "active_dept": "living_book",
        "active_worker": "A00",
        "run_type": "living_book",
        "run_date": run_date,
        "current_client": "_api",
        "project_dir": project_dir,
        "results": {},
        "chat_history": [],
        "uploaded_files": [],
        "file_processor": None,
        "pipeline_running": False,
        "paused_at": None,
        "paused_output": "",
        "paused_context": {},
        "settings": {
            "format": "interactive_book",
            "duration": "0",
            "style": "children_story",
        },
        "child_info": {
            "name": request.child_name,
            "age": request.child_age,
            "interests": request.child_interests or "",
            "notes": request.child_notes or "",
            "task": request.task_context,
        },
    }


# ═══════════════════════════════════════════════════════════
# EXTRACT BOOK PACKAGE
# ═══════════════════════════════════════════════════════════

def _extract_book_package(state: dict) -> Optional[dict]:
    """Извлекает book_package из результатов пайплайна."""
    results = state.get("results", {})

    # A16 (Марка Файн) должен выдать готовый package
    a16 = results.get("A16", {})
    if a16:
        raw = a16.get("raw", "") if isinstance(a16, dict) else str(a16)
        package = _try_parse_json(raw)
        if package and ("book" in package or "chapters" in package):
            return package

    # Ищем в любом результате
    for wid in reversed(list(results.keys())):
        res = results[wid]
        raw = res.get("raw", "") if isinstance(res, dict) else str(res)
        package = _try_parse_json(raw)
        if package and "book" in package:
            return package

    return _build_minimal_package(state, results)


def _try_parse_json(text: str) -> Optional[dict]:
    import re
    json_blocks = re.findall(r'```json\s*(.*?)```', text, re.DOTALL)
    for block in json_blocks:
        try:
            return json.loads(block.strip())
        except Exception:
            continue
    try:
        return json.loads(text.strip())
    except Exception:
        pass
    return None


def _build_minimal_package(state: dict, results: dict) -> dict:
    child = state.get("child_info", {})
    story_text = ""
    a00 = results.get("A00", {})
    if a00:
        story_text = a00.get("text", "") if isinstance(a00, dict) else str(a00)

    return {
        "book": {
            "id": f"book_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "title": f"История для {child.get('name', 'ребёнка')}",
            "description": story_text[:300] if story_text else "Сгенерировано студией",
            "age_group": child.get("age", "7-12"),
            "language": "ru",
            "version": "1.0.0",
            "created_by": "Six Fingers Studio",
            "chapters": [{"id": "ch01", "title": "Начало", "file": "chapters/ch01.json"}],
            "characters": [{"id": "eirik", "file": "characters/eirik.json"}],
            "starting_chapter": "ch01",
            "starting_scene": "scene_01",
        },
        "raw_results": {
            wid: (res.get("text", "")[:500] if isinstance(res, dict) else str(res)[:500])
            for wid, res in results.items()
        },
        "_note": "Минимальный пакет — A16 не вернул полный book_package",
    }


# ═══════════════════════════════════════════════════════════
# REGISTER API ROUTES
# ═══════════════════════════════════════════════════════════

def register_living_book_api(fastapi_app):
    """Регистрирует API-роуты для Маяка."""

    @fastapi_app.post("/api/living_book/generate")
    async def generate_book(request: BookRequest):
        """Генерация книги: Сет → 18 агентов → book_package.

        Полный цикл:
        1. Сет получает запрос родителя и формирует master_brief
        2. CartridgeRunner запускает living_book (18 агентов)
        3. Результат упаковывается в book_package
        4. Сохраняется для Искорки
        """
        print(f"\n{'='*60}")
        print(f"[API] 📖 Заказ от Маяка: {request.child_name}, {request.child_age}")
        print(f"[API] 📝 Задача: {request.task_context}")
        print(f"{'='*60}\n")

        try:
            # ═══ ШАГ 0: СЕТ ФОРМИРУЕТ БРИФ ═══
            set_brief = await _call_set(request)

            # Сохраняем бриф на диск
            run_date = datetime.now().strftime("%Y-%m-%d_%H%M%S")
            project_dir = Path("runs") / f"livingbook_{request.child_name}_{run_date}"
            project_dir.mkdir(parents=True, exist_ok=True)
            (project_dir / "set_brief.md").write_text(
                f"# Бриф от Сета\n\n{set_brief}", encoding="utf-8"
            )

            # ═══ ШАГ 1: ПАЙПЛАЙН LIVING BOOK ═══
            state = _build_headless_state(request, set_brief)
            state["project_dir"] = project_dir  # уже создан выше

            manifest = CartridgeManifest.load("living_book")
            callbacks = HeadlessCallbacks()

            runner = CartridgeRunner(manifest, state, callbacks, slot_id="living_book")
            await runner.run()

            # ═══ ШАГ 2: УПАКОВКА РЕЗУЛЬТАТА ═══
            book_package = _extract_book_package(state)

            if book_package:
                stories_dir = Path("stories") / request.child_name
                stories_dir.mkdir(parents=True, exist_ok=True)
                filename = f"book_{run_date}_pending.json"
                (stories_dir / filename).write_text(
                    json.dumps(book_package, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
                print(f"[API] 💾 Сохранено: {stories_dir / filename}")

            return BookResponse(
                status="completed" if not callbacks.errors else "completed_with_errors",
                child_name=request.child_name,
                book_package=book_package,
                run_id=run_date,
                agents_log=callbacks.log,
                set_brief=set_brief[:500],
                error="; ".join(callbacks.errors) if callbacks.errors else None,
            ).model_dump()

        except Exception as e:
            import traceback
            traceback.print_exc()
            return BookResponse(
                status="error",
                child_name=request.child_name,
                error=str(e),
            ).model_dump()

    @fastapi_app.get("/api/living_book/status")
    async def living_book_status():
        """Статус картриджа living_book."""
        try:
            manifest = CartridgeManifest.load("living_book")
            return {
                "status": "ready",
                "agents": len(manifest.get_all_agents()),
                "phases": list(manifest.phases.keys()),
                "has_revision_loop": manifest.revision_loop is not None,
                "orchestrator": "Сет (003_LEGACY_SET)",
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    print("[API] 📖 Living Book API зарегистрирован: Сет → 18 агентов → book_package")
