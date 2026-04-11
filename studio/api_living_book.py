# studio/api_living_book.py — API генерации Живых Книг
# Студия «Шесть Пальцев» · 2026
#
# Автономный API для Маяка (LIVING_BOOK_APP).
# Маяк отправляет заказ → Студия прогоняет полный пайплайн living_book
# (18 агентов, ревизия Веры, ДНК, память) → возвращает book_package.
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
    book_package: Optional[dict] = None  # Полный BOOK_PACKAGE
    run_id: Optional[str] = None
    error: Optional[str] = None
    agents_log: Optional[list] = None    # Краткий лог агентов


# ═══════════════════════════════════════════════════════════
# HEADLESS CALLBACKS — логирует без UI
# ═══════════════════════════════════════════════════════════

class HeadlessCallbacks(PipelineCallbacks):
    """Callbacks без NiceGUI — для headless API.
    
    Просто логирует прогресс в консоль и собирает результаты.
    """
    
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
        self.log.append({
            "agent": reviewer_id, "status": "revision",
            "loop": loop_number, "max": max_loops,
        })
    
    async def on_revision_approved(self, slot_id, reviewer_id):
        print(f"[API] ✅ Ревизия одобрена: {reviewer_id}")
    
    async def on_checkpoint(self, slot_id, worker_id, label) -> bool:
        # API-режим: пропускаем checkpoints, не останавливаемся
        print(f"[API] ⏭ Checkpoint {worker_id} — пропускаем (API-режим)")
        return True
    
    async def on_status(self, slot_id, message, level="info"):
        print(f"[API] [{level}] {message}")
    
    async def on_viewer_update(self, slot_id, worker_id, content):
        pass  # Нет viewer в headless
    
    async def on_parallel_start(self, slot_id, agent_ids):
        print(f"[API] ⚡ Параллельно: {' + '.join(agent_ids)}")
    
    async def on_parallel_done(self, slot_id, agent_ids, results):
        pass


# ═══════════════════════════════════════════════════════════
# BUILD STATE — создаём state для headless запуска
# ═══════════════════════════════════════════════════════════

def _build_headless_state(request: BookRequest) -> dict:
    """Создаёт state для CartridgeRunner без UI."""
    
    run_date = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    project_name = f"livingbook_{request.child_name}_{run_date}"
    project_dir = Path("runs") / project_name
    project_dir.mkdir(parents=True, exist_ok=True)
    
    master_brief = json.dumps({
        "project": {
            "name": f"История для {request.child_name}",
            "workshop": "living_book",
        },
        "story": {
            "real_task": request.task_context,
            "desired_emotion": "радость, уверенность, безопасность",
        },
        "child": {
            "name": request.child_name,
            "age": request.child_age,
            "interests": request.child_interests or "",
            "notes": request.child_notes or "",
        },
        "key_message": f"{request.child_name} справится!",
    }, ensure_ascii=False, indent=2)
    
    return {
        "master_brief": master_brief,
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
        # Данные ребёнка — hooks.py подхватит
        "child_info": {
            "name": request.child_name,
            "age": request.child_age,
            "interests": request.child_interests or "",
            "notes": request.child_notes or "",
            "task": request.task_context,
        },
    }


# ═══════════════════════════════════════════════════════════
# EXTRACT BOOK PACKAGE — собираем результат
# ═══════════════════════════════════════════════════════════

def _extract_book_package(state: dict) -> Optional[dict]:
    """Извлекает book_package из результатов пайплайна.
    
    Ищет в результате последнего агента (A16) JSON-структуру
    book_package. Если не находит — собирает из промежуточных.
    """
    results = state.get("results", {})
    
    # Попытка 1: A16 (Марка Файн) должен выдать готовый package
    a16 = results.get("A16", {})
    if a16:
        raw = a16.get("raw", "") if isinstance(a16, dict) else str(a16)
        package = _try_parse_json(raw)
        if package and ("book" in package or "chapters" in package):
            return package
    
    # Попытка 2: ищем в любом результате структуру book
    for wid in reversed(list(results.keys())):
        res = results[wid]
        raw = res.get("raw", "") if isinstance(res, dict) else str(res)
        package = _try_parse_json(raw)
        if package and "book" in package:
            return package
    
    # Попытка 3: собираем базовый package из того что есть
    return _build_minimal_package(state, results)


def _try_parse_json(text: str) -> Optional[dict]:
    """Пытается извлечь JSON из текста агента."""
    import re
    # Ищем JSON-блоки в markdown
    json_blocks = re.findall(r'```json\s*(.*?)```', text, re.DOTALL)
    for block in json_blocks:
        try:
            return json.loads(block.strip())
        except Exception:
            continue
    
    # Пробуем весь текст
    try:
        return json.loads(text.strip())
    except Exception:
        pass
    
    return None


def _build_minimal_package(state: dict, results: dict) -> dict:
    """Собирает минимальный book_package из промежуточных результатов."""
    child = state.get("child_info", {})
    
    # Собираем текст сценария из A00 (Фабула)
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
    """Регистрирует API-роуты для Маяка.
    
    Вызывается из main.py:
        from studio.api_living_book import register_living_book_api
        register_living_book_api(app)
    """
    
    @fastapi_app.post("/api/living_book/generate")
    async def generate_book(request: BookRequest):
        """Генерация книги через полный пайплайн living_book.
        
        Маяк вызывает этот эндпоинт.
        Студия прогоняет 18 агентов и возвращает book_package.
        """
        print(f"\n{'='*60}")
        print(f"[API] 📖 Заказ от Маяка: {request.child_name}, {request.child_age}")
        print(f"[API] 📝 Задача: {request.task_context}")
        print(f"{'='*60}\n")
        
        try:
            # Строим state
            state = _build_headless_state(request)
            
            # Загружаем картридж
            manifest = CartridgeManifest.load("living_book")
            
            # Headless callbacks — без UI
            callbacks = HeadlessCallbacks()
            
            # Запуск пайплайна
            runner = CartridgeRunner(manifest, state, callbacks, slot_id="living_book")
            await runner.run()
            
            # Извлекаем book_package
            book_package = _extract_book_package(state)
            
            # Сохраняем на диск (для Искорки через /api/beacon/stories)
            if book_package:
                stories_dir = Path("stories") / request.child_name
                stories_dir.mkdir(parents=True, exist_ok=True)
                
                filename = f"book_{datetime.now().strftime('%Y%m%d_%H%M%S')}_pending.json"
                (stories_dir / filename).write_text(
                    json.dumps(book_package, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
                print(f"[API] 💾 Сохранено: {stories_dir / filename}")
            
            return BookResponse(
                status="completed" if not callbacks.errors else "completed_with_errors",
                child_name=request.child_name,
                book_package=book_package,
                run_id=state["run_date"],
                agents_log=callbacks.log,
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
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    print("[API] 📖 Living Book API зарегистрирован: /api/living_book/generate")
