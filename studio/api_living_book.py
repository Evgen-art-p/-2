# studio/api_living_book.py — API генерации Живых Книг
# СТАНДАРТ v3.0 compliant. Dual-format intake.
# + POST /api/living_book/prepare_book — Цех разделки (загрузка книги на Витрину)

from __future__ import annotations
import json, asyncio, os, uuid
from pathlib import Path
from datetime import datetime
from typing import Any, Optional

import httpx
from pydantic import BaseModel
from nicegui import app

from studio.cartridge import CartridgeManifest, CartridgeRunner, PipelineCallbacks
from studio.workshop.pipeline import (
    build_settings_ctx, build_files_ctx,
    build_agent_context, call_agent, process_agent_result, summarize_session,
)

BEACON_URL = os.getenv("BEACON_URL", "http://localhost:8001")


# ── MODELS ──────────────────────────────────────────────────────────────────

class BookRequest(BaseModel):
    """Legacy-запрос (плоский формат)."""
    child_name: str
    child_age: str
    task_context: str
    parent_email: Optional[str] = None
    child_interests: Optional[str] = None
    child_notes: Optional[str] = None


class BookResponse(BaseModel):
    status: str
    child_name: str
    book_package: Optional[dict] = None
    run_id: Optional[str] = None
    error: Optional[str] = None
    agents_log: Optional[list] = None


class PrepareBookRequest(BaseModel):
    """Запрос на подготовку книги для Витрины (Цех разделки)."""
    book_id: str
    title: str
    text: str                    # сырой текст книги
    description: str = ""
    age_group: str = "7-12"
    main_character: str = "eirik"
    home_world: str = "cave"


class PrepareBookResponse(BaseModel):
    status: str
    book_id: str
    chapters_found: int = 0
    chapter_id: Optional[str] = None
    ready_book_path: Optional[str] = None
    showcase_path: Optional[str] = None
    error: Optional[str] = None


# ── DUAL-FORMAT PARSER ───────────────────────────────────────────────────────

def _parse_request(body: Any) -> dict:
    """Нормализует legacy BookRequest и story_package v3.0 в единый dict."""
    if isinstance(body, BookRequest):
        return {
            "child_name": body.child_name,
            "child_age": body.child_age,
            "task_context": body.task_context,
            "child_interests": body.child_interests or "",
            "child_notes": body.child_notes or "",
            "child_uid": None,
            "order": {},
            "biography_snapshot": None,
            "package_id": f"pkg_{uuid.uuid4().hex[:8]}",
            "version": "legacy",
        }

    if not isinstance(body, dict):
        raise ValueError(f"Неожиданный тип: {type(body)}")

    meta  = body.get("meta", {})
    child = body.get("child", {})
    order = body.get("order", {})

    if meta.get("version") == "3.0" or child.get("uid"):
        slots = order.get("slots", {})
        task_parts = []
        if slots.get("plot"):     task_parts.append(f"сюжет: {slots['plot']}")
        if slots.get("location"): task_parts.append(f"место: {slots['location']}")
        if slots.get("finale"):   task_parts.append(f"финал: {slots['finale']}")
        task_context = order.get("task_context") or (", ".join(task_parts) if task_parts else "Новая глава")
        return {
            "child_name": child.get("name", "Ребёнок"),
            "child_age": child.get("age_group", "7-12"),
            "task_context": task_context,
            "child_interests": "",
            "child_notes": "",
            "child_uid": child.get("uid"),
            "order": order,
            "biography_snapshot": body.get("biography_snapshot"),
            "package_id": meta.get("package_id", f"pkg_{uuid.uuid4().hex[:8]}"),
            "version": "3.0",
        }

    # legacy dict
    return {
        "child_name": body.get("child_name", "Ребёнок"),
        "child_age": body.get("child_age", "7-12"),
        "task_context": body.get("task_context", ""),
        "child_interests": body.get("child_interests", ""),
        "child_notes": body.get("child_notes", ""),
        "child_uid": None,
        "order": {},
        "biography_snapshot": None,
        "package_id": f"pkg_{uuid.uuid4().hex[:8]}",
        "version": "legacy",
    }


# ── HEADLESS CALLBACKS ───────────────────────────────────────────────────────

class HeadlessCallbacks(PipelineCallbacks):
    def __init__(self):
        self.log: list[dict] = []
        self.errors: list[str] = []

    async def on_pipeline_start(self, slot_id, run_type):
        print(f"[API] 🚀 {slot_id} ({run_type})")

    async def on_pipeline_done(self, slot_id, results):
        print(f"[API] 🎉 {slot_id} done ({len(results)} results)")

    async def on_pipeline_error(self, slot_id, error):
        print(f"[API] ❌ {error}"); self.errors.append(error)

    async def on_agent_start(self, slot_id, worker_id, label, phase):
        print(f"[API] 🤖 {worker_id} {label} [{phase}]")
        self.log.append({"agent": worker_id, "label": label, "status": "started"})

    async def on_agent_done(self, slot_id, worker_id, label, human_text, meta, ghost_ids):
        print(f"[API] ✅ {worker_id} {label}")
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
        print(f"[API] 🔄 rev #{loop_number}/{max_loops}: {reviewer_id}→{return_to}")
        self.log.append({"agent": reviewer_id, "status": "revision", "loop": loop_number})

    async def on_revision_approved(self, slot_id, reviewer_id):
        print(f"[API] ✅ approved: {reviewer_id}")

    async def on_checkpoint(self, slot_id, worker_id, label) -> bool:
        print(f"[API] ⏭ checkpoint {worker_id} — skip (API mode)")
        return True

    async def on_status(self, slot_id, message, level="info"):
        print(f"[API] [{level}] {message}")

    async def on_viewer_update(self, slot_id, worker_id, content): pass
    async def on_parallel_start(self, slot_id, agent_ids): print(f"[API] ⚡ {'+'.join(agent_ids)}")
    async def on_parallel_done(self, slot_id, agent_ids, results): pass


# ── BUILD STATE ──────────────────────────────────────────────────────────────

def _build_headless_state(parsed: dict) -> dict:
    """Создаёт state. biography_snapshot → state['biography_snapshot'] для hooks.py."""
    run_date = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    child_name = parsed["child_name"]
    project_dir = Path("runs") / f"livingbook_{child_name}_{run_date}"
    project_dir.mkdir(parents=True, exist_ok=True)

    master_brief = json.dumps({
        "project": {"name": f"История для {child_name}", "workshop": "living_book"},
        "story": {"real_task": parsed["task_context"], "desired_emotion": "радость, уверенность, безопасность"},
        "child": {"name": child_name, "age": parsed["child_age"],
                  "interests": parsed["child_interests"], "notes": parsed["child_notes"]},
        "key_message": f"{child_name} справится!",
        "order": parsed.get("order", {}),
    }, ensure_ascii=False, indent=2)

    return {
        "master_brief": master_brief,
        "active_dept": "living_book",
        "active_worker": "A00",
        "run_type": "living_book",
        "run_date": run_date,
        "current_client": parsed.get("child_uid") or "_api",
        "project_dir": project_dir,
        "results": {},
        "chat_history": [],
        "uploaded_files": [],
        "file_processor": None,
        "pipeline_running": False,
        "paused_at": None,
        "paused_output": "",
        "paused_context": {},
        "settings": {"format": "interactive_book", "duration": "0", "style": "children_story"},
        # Данные ребёнка — hooks.py A00
        "child_info": {
            "name": child_name,
            "age": parsed["child_age"],
            "interests": parsed["child_interests"],
            "notes": parsed["child_notes"],
            "task": parsed["task_context"],
            "uid": parsed.get("child_uid"),
        },
        # biography_snapshot (STANDARD §4.5) — hooks.py A00 + A16 validation
        "biography_snapshot": parsed.get("biography_snapshot"),
        "_package_id": parsed["package_id"],
        "_request_version": parsed["version"],
    }


# ── DELIVER ──────────────────────────────────────────────────────────────────

async def _deliver_to_beacon(package: dict, child_uid: str, in_response_to: str, run_date: str):
    """POST /api/package/deliver → Маяк сохраняет главу."""
    chapter = package.get("chapter")
    if not chapter:
        print(f"[API] ⚠️ deliver: нет 'chapter' в package — пропускаем")
        return

    story_package = {
        "meta": {
            "version": "3.0",
            "type": "chapter",
            "timestamp": datetime.now().isoformat(),
            "package_id": f"pkg_{uuid.uuid4().hex[:8]}",
            "in_response_to": in_response_to,
        },
        "child": {"uid": child_uid},
        "chapter": chapter,
    }
    for key in ("bridges", "rewards"):
        if package.get(key):
            story_package[key] = package[key]

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(f"{BEACON_URL}/api/package/deliver", json=story_package)
            r.raise_for_status()
            print(f"[API] 📬 deliver OK → {r.json()}")
    except Exception as e:
        print(f"[API] ❌ deliver ERROR: {e}")


# ── EXTRACT PACKAGE ──────────────────────────────────────────────────────────

def _try_parse_json(text: str) -> Optional[dict]:
    import re
    for block in re.findall(r'```json\s*(.*?)```', text, re.DOTALL):
        try: return json.loads(block.strip())
        except Exception: continue
    try: return json.loads(text.strip())
    except Exception: pass
    return None


def _extract_book_package(state: dict) -> Optional[dict]:
    results = state.get("results", {})
    a16 = results.get("A16", {})
    if a16:
        raw = a16.get("raw", "") if isinstance(a16, dict) else str(a16)
        p = _try_parse_json(raw)
        if p and ("chapter" in p or "book" in p or "chapters" in p):
            return p
    for wid in reversed(list(results.keys())):
        res = results[wid]
        raw = res.get("raw", "") if isinstance(res, dict) else str(res)
        p = _try_parse_json(raw)
        if p and ("chapter" in p or "book" in p):
            return p
    return _build_minimal_package(state, results)


def _build_minimal_package(state: dict, results: dict) -> dict:
    child = state.get("child_info", {})
    a00 = results.get("A00", {})
    story_text = (a00.get("text", "") if isinstance(a00, dict) else str(a00)) if a00 else ""
    return {
        "book": {
            "id": f"book_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "title": f"История для {child.get('name', 'ребёнка')}",
            "description": story_text[:300] or "Сгенерировано студией",
            "age_group": child.get("age", "7-12"),
            "language": "ru",
            "version": "1.0.0",
            "created_by": "Six Fingers Studio",
            "chapters": [{"id": "ch01", "title": "Начало", "file": "chapters/ch01.json"}],
            "starting_chapter": "ch01",
            "starting_scene": "scene_01",
        },
        "raw_results": {
            wid: (res.get("text", "")[:500] if isinstance(res, dict) else str(res)[:500])
            for wid, res in results.items()
        },
        "_note": "Минимальный пакет — A16 не вернул полный book_package",
    }


# ── REGISTER ─────────────────────────────────────────────────────────────────

def register_living_book_api(fastapi_app):

    # ── /api/living_book/generate ────────────────────────────────────────────
    @fastapi_app.post("/api/living_book/generate")
    async def generate_book(body: Any = None):
        try:
            parsed = _parse_request(body if isinstance(body, (dict, BookRequest)) else {})

            print(f"\n{'='*60}")
            print(f"[API] 📖 {parsed['child_name']} {parsed['child_age']} [{parsed['version']}]")
            print(f"[API] 📝 {parsed['task_context']}")
            if parsed.get("biography_snapshot"):
                s = parsed["biography_snapshot"]
                print(f"[API] 🧠 hero={s.get('main_character')} karma={s.get('karma')} arts={len(s.get('artifacts',[]))}")
            print(f"{'='*60}\n")

            state = _build_headless_state(parsed)
            manifest = CartridgeManifest.load("living_book")
            callbacks = HeadlessCallbacks()
            runner = CartridgeRunner(manifest, state, callbacks, slot_id="living_book")
            await runner.run()

            book_package = _extract_book_package(state)
            child_name = parsed["child_name"]

            if book_package:
                stories_dir = Path("stories") / child_name
                stories_dir.mkdir(parents=True, exist_ok=True)
                fn = f"book_{datetime.now().strftime('%Y%m%d_%H%M%S')}_pending.json"
                (stories_dir / fn).write_text(
                    json.dumps(book_package, ensure_ascii=False, indent=2), encoding="utf-8"
                )
                print(f"[API] 💾 {stories_dir / fn}")

            if parsed.get("child_uid") and book_package and parsed["version"] == "3.0":
                await _deliver_to_beacon(
                    package=book_package,
                    child_uid=parsed["child_uid"],
                    in_response_to=parsed["package_id"],
                    run_date=state["run_date"],
                )

            return BookResponse(
                status="completed" if not callbacks.errors else "completed_with_errors",
                child_name=child_name,
                book_package=book_package,
                run_id=state["run_date"],
                agents_log=callbacks.log,
                error="; ".join(callbacks.errors) if callbacks.errors else None,
            ).model_dump()

        except Exception as e:
            import traceback; traceback.print_exc()
            return BookResponse(status="error", child_name="unknown", error=str(e)).model_dump()

    # ── /api/living_book/status ──────────────────────────────────────────────
    @fastapi_app.get("/api/living_book/status")
    async def living_book_status():
        try:
            manifest = CartridgeManifest.load("living_book")
            return {
                "status": "ready",
                "standard": "3.0",
                "intake_formats": ["legacy", "story_package_v3"],
                "agents": len(manifest.get_all_agents()),
                "phases": list(manifest.phases.keys()),
                "has_revision_loop": manifest.revision_loop is not None,
                "deliver_url": f"{BEACON_URL}/api/package/deliver",
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    # ── /api/living_book/prepare_book — ЦЕХ РАЗДЕЛКИ ────────────────────────
    @fastapi_app.post("/api/living_book/prepare_book")
    async def prepare_book(req: PrepareBookRequest):
        """
        Цех разделки: принимает сырой текст книги,
        режет на главы, прогоняет первую через пайплайн,
        кладёт готовый JSON в system_registry/ready_books/.
        Маяк подхватывает автоматически через /api/showcase.
        """
        try:
            from studio.modules.living_book.ui_book_loader import (
                split_into_chapters,
                save_raw_chapters,
                run_pipeline_for_chapter,
            )

            book_id = req.book_id.strip()
            if not book_id:
                return PrepareBookResponse(
                    status="error", book_id="", error="book_id обязателен"
                ).model_dump()

            print(f"\n[PREPARE] {'='*50}")
            print(f"[PREPARE] 📖 Новая книга: {req.title} ({book_id})")
            print(f"[PREPARE] 📏 Текст: {len(req.text)} символов")

            # 1. Режем на главы
            chapters = split_into_chapters(req.text, book_id)
            print(f"[PREPARE] ✂️ Найдено {len(chapters)} глав")

            if not chapters:
                return PrepareBookResponse(
                    status="error",
                    book_id=book_id,
                    chapters_found=0,
                    error="Не удалось разбить текст на главы",
                ).model_dump()

            # 2. Сохраняем сырые главы
            save_raw_chapters(book_id, chapters)

            # 3. Лог-заглушка для API режима
            api_log_lines = []
            async def api_log(msg: str):
                api_log_lines.append(msg)
                print(f"[PREPARE] {msg}")

            # 4. Прогоняем пайплайн для первой главы
            result = await run_pipeline_for_chapter(
                book_id=book_id,
                chapter=chapters[0],
                title=req.title,
                description=req.description or f"{req.title} — первое приключение",
                age_group=req.age_group,
                main_character=req.main_character,
                home_world=req.home_world,
                on_log=api_log,
            )

            if not result:
                return PrepareBookResponse(
                    status="error",
                    book_id=book_id,
                    chapters_found=len(chapters),
                    error="Пайплайн завершился без результата",
                ).model_dump()

            ready_path = f"system_registry/ready_books/{book_id}.json"
            showcase_path = f"system_registry/showcase/{book_id}.json"
            chapter_id = result.get("chapter", {}).get("id", "ch01")

            print(f"[PREPARE] ✅ Готово! {ready_path}")
            print(f"[PREPARE] {'='*50}\n")

            return PrepareBookResponse(
                status="ready",
                book_id=book_id,
                chapters_found=len(chapters),
                chapter_id=chapter_id,
                ready_book_path=ready_path,
                showcase_path=showcase_path,
            ).model_dump()

        except Exception as e:
            import traceback
            traceback.print_exc()
            return PrepareBookResponse(
                status="error",
                book_id=req.book_id,
                error=str(e),
            ).model_dump()

    # ── /api/living_book/showcase — список книг на витрине ───────────────────
    @fastapi_app.get("/api/living_book/showcase")
    async def living_book_showcase():
        """Список готовых книг в system_registry/ready_books/."""
        ready_dir = Path("system_registry/ready_books")
        if not ready_dir.exists():
            return {"books": [], "count": 0}
        books = []
        for f in sorted(ready_dir.glob("*.json")):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                books.append({
                    "book_id": data.get("book_id", f.stem),
                    "title": data.get("title", f.stem),
                    "description": data.get("description", ""),
                    "age_group": data.get("age_group", "7-12"),
                    "main_character": data.get("main_character", "—"),
                    "created_at": data.get("created_at", ""),
                })
            except Exception:
                pass
        return {"books": books, "count": len(books)}

    print(f"[API] 📖 Living Book API:")
    print(f"[API]   POST /api/living_book/generate")
    print(f"[API]   POST /api/living_book/prepare_book  ← Цех разделки")
    print(f"[API]   GET  /api/living_book/showcase")
    print(f"[API] 📡 Deliver callback → {BEACON_URL}/api/package/deliver")
