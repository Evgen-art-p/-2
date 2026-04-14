"""
╔══════════════════════════════════════════════════════════════╗
║  ЦЕХ РАЗДЕЛКИ — ЗАГРУЗЧИК КНИГ НА ВИТРИНУ                  ║
║  NiceGUI страница · /living_book_loader                     ║
║  Студия «Шесть Пальцев»                                    ║
╚══════════════════════════════════════════════════════════════╝

Логика:
  1. Шеф загружает .txt файл книги и задаёт book_id
  2. Студия режет текст на главы (по маркерам или по размеру)
  3. Запускает Полный Пайплайн (A00→A16) для первой главы
     с biography_snapshot=null (первая встреча, герой ещё не выбран)
  4. Результат A16 кладётся в system_registry/ready_books/{book_id}.json
  5. Маяк автоматически отдаёт книгу на Витрину (/api/showcase)

Никакой ручной работы с папками.
"""

import json
import re
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Optional

from nicegui import ui, app, events

# ══════════════════════════════════════════════════════════
# КОНФИГ ПУТЕЙ
# ══════════════════════════════════════════════════════════

READY_BOOKS_DIR = Path("system_registry/ready_books")
RAW_CHAPTERS_DIR = Path("system_registry/raw_chapters")

READY_BOOKS_DIR.mkdir(parents=True, exist_ok=True)
RAW_CHAPTERS_DIR.mkdir(parents=True, exist_ok=True)


# ══════════════════════════════════════════════════════════
# ПАРСЕР ГЛАВ
# ══════════════════════════════════════════════════════════

def split_into_chapters(text: str, book_id: str) -> list[dict]:
    """
    Режет сырой текст на главы.
    Алгоритм (ищем маркеры в порядке приоритета):
      1. # Глава / ## Глава / Глава 1 / Chapter 1 / ГЛАВА I
      2. *** / --- / === (горизонтальные разделители)
      3. Двойные переносы строк (абзацный режим, каждые ~2000 символов)
    Возвращает список: [{id, title, text, index}]
    """
    # Паттерны маркеров глав
    chapter_markers = [
        r'^#{1,3}\s*(Глава|Chapter|ГЛАВА|CHAPTER)\s*[\dIVXivx]+.*$',
        r'^(Глава|Chapter|ГЛАВА|CHAPTER)\s*[\dIVXivx]+.*$',
        r'^[\*\-=]{3,}\s*$',
    ]

    combined_pattern = '|'.join(chapter_markers)
    lines = text.splitlines()

    # Пробуем найти маркеры
    splits = []  # индексы строк где начинается новая глава
    for i, line in enumerate(lines):
        if re.match(combined_pattern, line.strip(), re.IGNORECASE):
            splits.append(i)

    if len(splits) >= 2:
        # Есть маркеры — режем по ним
        chapters = []
        for idx, start in enumerate(splits):
            end = splits[idx + 1] if idx + 1 < len(splits) else len(lines)
            chapter_lines = lines[start:end]
            title_line = chapter_lines[0].strip().lstrip('#').strip()
            body = '\n'.join(chapter_lines[1:]).strip()
            if not body:
                continue
            chapter_id = f"ch{idx + 1:02d}"
            chapters.append({
                "id": chapter_id,
                "title": title_line or f"Глава {idx + 1}",
                "text": body,
                "index": idx + 1,
            })
        return chapters

    # Нет маркеров — режем по двойным переносам строк / примерно по 2000 символов
    paragraphs = re.split(r'\n{2,}', text.strip())
    chunks = []
    current = []
    current_len = 0
    for para in paragraphs:
        if current_len > 1800 and current:
            chunks.append('\n\n'.join(current))
            current = [para]
            current_len = len(para)
        else:
            current.append(para)
            current_len += len(para)
    if current:
        chunks.append('\n\n'.join(current))

    chapters = []
    for idx, chunk in enumerate(chunks):
        chapter_id = f"ch{idx + 1:02d}"
        chapters.append({
            "id": chapter_id,
            "title": f"Часть {idx + 1}",
            "text": chunk.strip(),
            "index": idx + 1,
        })
    return chapters


def save_raw_chapters(book_id: str, chapters: list[dict]) -> Path:
    """Сохраняет сырые главы в system_registry/raw_chapters/{book_id}/"""
    book_raw_dir = RAW_CHAPTERS_DIR / book_id
    book_raw_dir.mkdir(parents=True, exist_ok=True)
    for ch in chapters:
        fname = f"{ch['id']}_raw.txt"
        (book_raw_dir / fname).write_text(
            f"{ch['title']}\n\n{ch['text']}",
            encoding="utf-8"
        )
    # Индекс глав
    index = [{"id": c["id"], "title": c["title"], "file": f"{c['id']}_raw.txt"} for c in chapters]
    (book_raw_dir / "index.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    return book_raw_dir


# ══════════════════════════════════════════════════════════
# СБОРКА READY_BOOK (формат STANDARD.md §7.5)
# ══════════════════════════════════════════════════════════

def wrap_as_ready_book(
    book_id: str,
    title: str,
    description: str,
    age_group: str,
    main_character: str,
    home_world: str,
    chapter_json: dict,
) -> dict:
    """
    Оборачивает готовую главу в формат ready_books (STANDARD §7.5).
    Этот файл Маяк копирует ребёнку при mode=first_book.
    """
    return {
        "book_id": book_id,
        "title": title,
        "description": description,
        "age_group": age_group,
        "main_character": main_character,
        "home_world": home_world,
        "chapter": chapter_json,
        "initial_bridges": [
            {
                "id": "bridge_intro",
                "task": "Найди в комнате предмет, который издаёт мягкий звук",
                "karma_reward": 2,
            }
        ],
        "initial_karma": 0,
        "created_at": datetime.now().isoformat(),
        "created_by": "Six Fingers Studio · Цех разделки",
    }


# ══════════════════════════════════════════════════════════
# ЗАПУСК ПАЙПЛАЙНА ДЛЯ ПЕРВОЙ ГЛАВЫ
# ══════════════════════════════════════════════════════════

async def run_pipeline_for_chapter(
    book_id: str,
    chapter: dict,
    title: str,
    description: str,
    age_group: str,
    main_character: str,
    home_world: str,
    on_log,
) -> Optional[dict]:
    """
    Прогоняет living_book пайплайн (A00→A16) для первой главы.
    biography_snapshot=null → первая встреча, герой ещё не выбран.
    Возвращает готовый ready_book dict или None при ошибке.
    """
    try:
        from studio.api_living_book import _build_headless_state, _extract_book_package
        from studio.cartridge import CartridgeManifest, CartridgeRunner
    except ImportError as e:
        await on_log(f"❌ Ошибка импорта: {e}")
        return None

    await on_log(f"⚙️ Формирую бриф для '{title}'...")

    # Строим parsed-dict вручную (имитируем _parse_request для prepare_book режима)
    parsed = {
        "child_name": "_витрина",
        "child_age": age_group,
        "task_context": f"Стандартный старт · первая встреча · {title}",
        "child_interests": "",
        "child_notes": f"Сырой текст главы:\n\n{chapter['text'][:3000]}",
        "child_uid": None,
        "order": {
            "mode": "first_book",
            "book_id": book_id,
            "raw_chapter_text": chapter["text"],
            "chapter_title": chapter["title"],
        },
        "biography_snapshot": None,  # ← первая встреча
        "package_id": f"pkg_prepare_{book_id}",
        "version": "prepare_book",
    }

    state = _build_headless_state(parsed)

    # Добавляем сырой текст в uploaded_files чтобы A00 мог его прочитать
    raw_path = RAW_CHAPTERS_DIR / book_id / f"{chapter['id']}_raw.txt"
    if raw_path.exists():
        state["uploaded_files"] = [str(raw_path)]

    await on_log("🤖 Запускаю пайплайн A00 → A16...")

    try:
        manifest = CartridgeManifest.load("living_book")
        callbacks = HeadlessUICallbacks(on_log)
        runner = CartridgeRunner(manifest, state, callbacks, slot_id="living_book_prepare")
        await runner.run()
    except Exception as e:
        await on_log(f"❌ Пайплайн завершился с ошибкой: {e}")
        return None

    await on_log("📦 Извлекаю результат A16...")
    book_package = _extract_book_package(state)

    if not book_package or "chapter" not in book_package:
        await on_log("⚠️ A16 не вернул chapter — формирую заглушку из текста главы")
        # Минимальный chapter для витрины (без психологии, просто чтобы не падало)
        chapter_json = {
            "id": chapter["id"],
            "title": chapter["title"],
            "world_id": home_world,
            "scenes": [
                {
                    "scene_id": "scene_01",
                    "speaker": main_character,
                    "text": chapter["text"][:500],
                    "mode": "voice_choice",
                    "choices": [
                        {
                            "id": "continue",
                            "label": "Продолжить",
                            "keywords": ["продолжить", "да", "вперёд", "дальше"],
                            "next_scene": "scene_01",
                            "memory_vector": "curious",
                        }
                    ],
                }
            ],
            "on_end": {
                "action": "end",
                "message": "Первое испытание пройдено!",
            },
        }
    else:
        chapter_json = book_package["chapter"]

    ready_book = wrap_as_ready_book(
        book_id=book_id,
        title=title,
        description=description,
        age_group=age_group,
        main_character=main_character,
        home_world=home_world,
        chapter_json=chapter_json,
    )

    # Сохраняем в ready_books
    out_path = READY_BOOKS_DIR / f"{book_id}.json"
    out_path.write_text(
        json.dumps(ready_book, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    # Дублируем в showcase (Маяк читает /api/showcase из system_registry/showcase/)
    showcase_dir = Path("system_registry/showcase")
    showcase_dir.mkdir(parents=True, exist_ok=True)
    showcase_path = showcase_dir / f"{book_id}.json"
    showcase_path.write_text(
        json.dumps({
            "title": title,
            "description": description,
            "book_id": book_id,
            "age_group": age_group,
            "main_character": main_character,
            "created_at": ready_book["created_at"],
        }, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    await on_log(f"✅ Готово! {out_path}")
    await on_log(f"📚 Витрина обновлена: showcase/{book_id}.json")
    return ready_book


# ══════════════════════════════════════════════════════════
# HEADLESS CALLBACKS ДЛЯ UI-РЕЖИМА
# ══════════════════════════════════════════════════════════

try:
    from studio.api_living_book import HeadlessCallbacks

    class HeadlessUICallbacks(HeadlessCallbacks):
        """Расширяет HeadlessCallbacks — пишет лог в NiceGUI UI."""
        def __init__(self, on_log):
            super().__init__()
            self._on_log = on_log

        async def on_agent_start(self, slot_id, worker_id, label, phase):
            await super().on_agent_start(slot_id, worker_id, label, phase)
            await self._on_log(f"🤖 {worker_id} · {label} [{phase}]")

        async def on_agent_done(self, slot_id, worker_id, label, human_text, meta, ghost_ids):
            await super().on_agent_done(slot_id, worker_id, label, human_text, meta, ghost_ids)
            await self._on_log(f"✅ {worker_id} готов")

        async def on_agent_error(self, slot_id, worker_id, error):
            await super().on_agent_error(slot_id, worker_id, error)
            await self._on_log(f"❌ {worker_id}: {error}")

        async def on_status(self, slot_id, message, level="info"):
            await self._on_log(f"[{level}] {message}")

except ImportError:
    # Fallback если api_living_book не доступен
    class HeadlessUICallbacks:
        def __init__(self, on_log):
            self._on_log = on_log
        async def on_pipeline_start(self, *a): pass
        async def on_pipeline_done(self, *a): pass
        async def on_pipeline_error(self, *a): pass
        async def on_agent_start(self, slot_id, worker_id, label, phase):
            await self._on_log(f"🤖 {worker_id} · {label}")
        async def on_agent_done(self, *a): pass
        async def on_agent_error(self, slot_id, worker_id, error):
            await self._on_log(f"❌ {worker_id}: {error}")
        async def on_revision_loop(self, *a): pass
        async def on_revision_approved(self, *a): pass
        async def on_checkpoint(self, *a): return True
        async def on_status(self, slot_id, message, level="info"):
            await self._on_log(f"[{level}] {message}")
        async def on_viewer_update(self, *a): pass
        async def on_parallel_start(self, *a): pass
        async def on_parallel_done(self, *a): pass


# ══════════════════════════════════════════════════════════
# СПИСОК ГОТОВЫХ КНИГ (ДЛЯ ОТОБРАЖЕНИЯ В UI)
# ══════════════════════════════════════════════════════════

def list_ready_books() -> list[dict]:
    """Список книг уже лежащих в ready_books/"""
    result = []
    if not READY_BOOKS_DIR.exists():
        return result
    for f in sorted(READY_BOOKS_DIR.glob("*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            result.append({
                "book_id": data.get("book_id", f.stem),
                "title": data.get("title", f.stem),
                "description": data.get("description", ""),
                "age_group": data.get("age_group", "7-12"),
                "main_character": data.get("main_character", "—"),
                "created_at": data.get("created_at", ""),
            })
        except Exception:
            pass
    return result


# ══════════════════════════════════════════════════════════
# CSS
# ══════════════════════════════════════════════════════════

LOADER_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Fira+Code:wght@300;400;500&family=Playfair+Display:wght@600;700&display=swap');

:root {
    --lb-bg: #08080d;
    --lb-surface: #0e0e16;
    --lb-border: #1e1e30;
    --lb-gold: #c9a84c;
    --lb-gold-dim: #8a6e2a;
    --lb-gold-glow: rgba(201,168,76,0.10);
    --lb-text: #a0a0b8;
    --lb-text-hi: #d0d0e0;
    --lb-text-dim: #55556a;
    --lb-green: #3a8a5a;
    --lb-red: #b83a3a;
}

.lb-page { background: var(--lb-bg) !important; font-family: 'Fira Code', monospace; color: var(--lb-text); min-height: 100vh; }
.lb-page .q-page, .lb-page .q-layout { background: var(--lb-bg) !important; }

.lb-header { text-align: center; padding: 24px 0 16px; border-bottom: 1px solid var(--lb-border); margin-bottom: 20px; }
.lb-header h1 { font-family: 'Playfair Display', serif; font-size: 1.6rem; color: var(--lb-gold); margin: 0; }
.lb-header .sub { font-size: 0.68rem; color: var(--lb-text-dim); letter-spacing: 0.15em; text-transform: uppercase; margin-top: 4px; }

.lb-card { background: var(--lb-surface); border: 1px solid var(--lb-border); border-radius: 8px; padding: 18px 20px; margin-bottom: 16px; }
.lb-card h2 { font-family: 'Playfair Display', serif; font-size: 1.05rem; color: var(--lb-gold); margin: 0 0 14px; padding-bottom: 8px; border-bottom: 1px solid var(--lb-border); }

.lb-field .q-field__control { background: var(--lb-bg) !important; border: 1px solid var(--lb-border) !important; border-radius: 4px !important; }
.lb-field .q-field__native, .lb-field .q-field__input { color: var(--lb-text-hi) !important; font-family: 'Fira Code', monospace !important; font-size: 0.85rem !important; }
.lb-field .q-field__label { color: var(--lb-text-dim) !important; font-size: 0.68rem !important; letter-spacing: 0.08em; text-transform: uppercase; }
.lb-field .q-field__bottom { display: none; }

.lb-btn { font-family: 'Fira Code', monospace !important; font-size: 0.82rem !important; letter-spacing: 0.04em; text-transform: none !important; border-radius: 4px !important; }

.lb-log { background: var(--lb-bg); border: 1px solid var(--lb-border); border-radius: 6px; padding: 12px 14px; font-family: 'Fira Code', monospace; font-size: 0.78rem; color: var(--lb-text); max-height: 340px; overflow-y: auto; line-height: 1.6; white-space: pre-wrap; }

.lb-badge { display: inline-block; font-size: 0.62rem; padding: 2px 8px; border-radius: 3px; letter-spacing: 0.06em; font-family: 'Fira Code', monospace; text-transform: uppercase; font-weight: 500; }
.lb-badge-ready { background: rgba(58,138,90,0.15); color: #4aaa6a; }
.lb-badge-raw   { background: rgba(201,168,76,0.12); color: var(--lb-gold); }

.lb-book-row { display: flex; align-items: center; gap: 12px; padding: 10px 12px; border: 1px solid var(--lb-border); border-radius: 6px; margin-bottom: 8px; background: var(--lb-bg); transition: border-color .2s; }
.lb-book-row:hover { border-color: #2a2a44; }
.lb-book-title { font-size: 0.9rem; color: var(--lb-text-hi); flex: 1; }
.lb-book-meta  { font-size: 0.68rem; color: var(--lb-text-dim); }
</style>
"""


# ══════════════════════════════════════════════════════════
# NICEGUI СТРАНИЦА
# ══════════════════════════════════════════════════════════

def page_book_loader():
    """Страница Цеха разделки — загрузчик книг на Витрину."""

    # ── Состояние ──
    uploaded_text = {"value": "", "filename": ""}
    parsed_chapters = {"value": []}
    pipeline_running = {"value": False}
    log_lines = {"value": []}

    ui.add_head_html(LOADER_CSS)
    ui.query("body").classes("lb-page")

    with ui.column().classes("w-full items-center").style(
        "max-width: 900px; margin: 0 auto; padding: 16px 20px 60px"
    ):
        # ── HEADER ──
        with ui.element("div").classes("lb-header w-full"):
            ui.html("<h1>Цех разделки · Загрузчик книг</h1>")
            ui.html('<div class="sub">Студия «Шесть Пальцев» · Витрина Живых Книг</div>')

        # ════════════════════════════════════════
        # БЛОК 1: ЗАГРУЗКА ФАЙЛА + ПАРАМЕТРЫ
        # ════════════════════════════════════════
        with ui.element("div").classes("lb-card w-full"):
            ui.html("<h2>① Загрузи книгу и задай параметры</h2>")

            with ui.grid(columns=2).classes("w-full gap-3 mb-4"):
                with ui.column().classes("w-full lb-field gap-0"):
                    book_id_input = ui.input(
                        label="book_id (латиница, без пробелов)",
                        placeholder="eirik_cave_intro"
                    ).classes("w-full")
                with ui.column().classes("w-full lb-field gap-0"):
                    title_input = ui.input(
                        label="Название книги",
                        placeholder="Эйрик и Тайна Фонаря"
                    ).classes("w-full")
                with ui.column().classes("w-full lb-field gap-0"):
                    description_input = ui.input(
                        label="Описание (для витрины)",
                        placeholder="Первое приключение в пещере"
                    ).classes("w-full")
                with ui.column().classes("w-full lb-field gap-0"):
                    age_group_input = ui.select(
                        label="Возраст",
                        options={"3-6": "3-6 лет", "7-12": "7-12 лет", "13+": "13+ лет"},
                        value="7-12"
                    ).classes("w-full")
                with ui.column().classes("w-full lb-field gap-0"):
                    character_input = ui.input(
                        label="Главный герой (id)",
                        placeholder="eirik"
                    ).classes("w-full")
                    character_input.value = "eirik"
                with ui.column().classes("w-full lb-field gap-0"):
                    world_input = ui.input(
                        label="Мир / локация (id)",
                        placeholder="cave"
                    ).classes("w-full")
                    world_input.value = "cave"

            # Загрузка файла
            async def handle_txt_upload(e: events.UploadEventArguments):
                content = e.content.read().decode("utf-8", errors="replace")
                uploaded_text["value"] = content
                uploaded_text["filename"] = e.name

                # Авто-заполнение book_id из имени файла
                if not book_id_input.value:
                    auto_id = re.sub(r'[^a-z0-9_]', '_', e.name.replace(".txt", "").lower())
                    book_id_input.value = auto_id

                # Авто-парсинг
                book_id = book_id_input.value or e.name.replace(".txt", "")
                chapters = split_into_chapters(content, book_id)
                parsed_chapters["value"] = chapters
                refresh_chapters_preview()
                ui.notify(f"Найдено {len(chapters)} глав", type="positive")

            ui.upload(
                label="Перетащи .txt файл книги",
                on_upload=handle_txt_upload,
                auto_upload=True,
                max_file_size=5_000_000,
            ).props('accept=".txt" flat bordered').classes("w-full").style(
                "background: var(--lb-bg); border: 2px dashed var(--lb-border); border-radius: 6px"
            )

        # ════════════════════════════════════════
        # БЛОК 2: ПРЕДПРОСМОТР ГЛАВ
        # ════════════════════════════════════════
        chapters_card = ui.element("div").classes("lb-card w-full")
        chapters_card.set_visibility(False)

        def refresh_chapters_preview():
            chapters_card.clear()
            chs = parsed_chapters["value"]
            if not chs:
                chapters_card.set_visibility(False)
                return
            chapters_card.set_visibility(True)
            with chapters_card:
                ui.html(f'<h2>② Главы найдены: {len(chs)}</h2>')
                with ui.column().classes("w-full gap-1"):
                    for ch in chs[:10]:
                        badge = '<span class="lb-badge lb-badge-ready">→ на Витрину</span>' if ch["index"] == 1 \
                            else '<span class="lb-badge lb-badge-raw">сырая</span>'
                        ui.html(f'''
                            <div class="lb-book-row">
                                <div class="lb-book-title">{ch["id"]} · {ch["title"]}</div>
                                {badge}
                                <div class="lb-book-meta">{len(ch["text"])} симв.</div>
                            </div>
                        ''')
                    if len(chs) > 10:
                        ui.html(f'<div style="color:var(--lb-text-dim);font-size:0.75rem;padding:6px">... и ещё {len(chs) - 10} глав (все будут сохранены)</div>')

        # ════════════════════════════════════════
        # БЛОК 3: ЗАПУСК ПАЙПЛАЙНА
        # ════════════════════════════════════════
        with ui.element("div").classes("lb-card w-full"):
            ui.html("<h2>③ Запуск · Отправить на Витрину</h2>")
            ui.html('''
                <div style="font-size:0.78rem;color:var(--lb-text-dim);margin-bottom:14px;line-height:1.7">
                    Студия прогонит первую главу через полный пайплайн (A00→A16):<br>
                    biography_snapshot = null · первая встреча · герой ещё не выбран<br>
                    Результат появится на Витрине Кабинета родителя автоматически.
                </div>
            ''')

            status_label = ui.html('<div style="color:var(--lb-text-dim);font-size:0.8rem">Ожидание загрузки файла...</div>')

            run_btn = ui.button(
                "🚀 Запустить Цех разделки",
                on_click=lambda: asyncio.ensure_future(run_pipeline())
            ).classes("lb-btn w-full").style(
                "background: var(--lb-gold); color: var(--lb-bg); "
                "padding: 14px; font-size: 0.95rem; font-weight: 600; margin-top: 4px"
            )

            # Лог выполнения
            log_area = ui.html('<div class="lb-log">Лог появится здесь после запуска...</div>')

        async def on_log(message: str):
            """Добавляет строку в лог UI."""
            log_lines["value"].append(message)
            if message.startswith("✅") or message.startswith("🎉"):
                cls = "color:#4aaa6a"
            elif message.startswith("❌"):
                cls = "color:#cc4444"
            elif message.startswith("🤖") or message.startswith("⚙️"):
                cls = "color:#9977ee"
            else:
                cls = "color:var(--lb-text)"

            lines_html = "".join(
                f'<div style="{cls if i == len(log_lines["value"]) - 1 else "color:var(--lb-text-dim)"}">{line}</div>'
                for i, line in enumerate(log_lines["value"])
            )
            log_area.set_content(f'<div class="lb-log">{lines_html}</div>')
            await ui.run_javascript(
                'var el = document.querySelector(".lb-log"); if(el) el.scrollTop = el.scrollHeight;'
            )

        async def run_pipeline():
            """Основной запуск: разрезать → сохранить → пайплайн → витрина."""
            if pipeline_running["value"]:
                ui.notify("Пайплайн уже запущен!", type="warning")
                return

            book_id = (book_id_input.value or "").strip()
            title = (title_input.value or "").strip()

            if not book_id:
                ui.notify("Укажи book_id!", type="negative")
                return
            if not uploaded_text["value"] and not parsed_chapters["value"]:
                ui.notify("Сначала загрузи .txt файл!", type="negative")
                return

            # Парсим если ещё не парсили
            if not parsed_chapters["value"] and uploaded_text["value"]:
                chapters = split_into_chapters(uploaded_text["value"], book_id)
                parsed_chapters["value"] = chapters
                refresh_chapters_preview()

            chapters = parsed_chapters["value"]
            if not chapters:
                ui.notify("Не удалось разбить текст на главы!", type="negative")
                return

            pipeline_running["value"] = True
            run_btn.props("disabled")
            log_lines["value"] = []
            status_label.set_content(
                '<div style="color:var(--lb-gold);font-size:0.8rem">⏳ Работаю...</div>'
            )

            try:
                await on_log(f"📖 Книга: {title or book_id} ({len(chapters)} глав)")
                await on_log(f"📂 book_id: {book_id}")

                # Шаг 1: сохранить сырые главы
                await on_log(f"✂️ Сохраняю {len(chapters)} глав в raw_chapters/{book_id}/...")
                raw_dir = save_raw_chapters(book_id, chapters)
                await on_log(f"✅ Сырые главы: {raw_dir}")

                # Шаг 2: пайплайн для первой главы
                first_chapter = chapters[0]
                await on_log(f"\n🎬 Запускаю пайплайн для: '{first_chapter['title']}'")
                await on_log(f"   biography_snapshot = null (первая встреча)")
                await on_log("   " + "─" * 40)

                result = await run_pipeline_for_chapter(
                    book_id=book_id,
                    chapter=first_chapter,
                    title=title or book_id,
                    description=description_input.value or f"{title} — первое приключение",
                    age_group=age_group_input.value or "7-12",
                    main_character=character_input.value or "eirik",
                    home_world=world_input.value or "cave",
                    on_log=on_log,
                )

                if result:
                    status_label.set_content(
                        f'<div style="color:#4aaa6a;font-size:0.85rem;font-weight:600">'
                        f'✅ Книга на Витрине! book_id: {book_id}</div>'
                    )
                    ui.notify(f"🎉 {title or book_id} — на Витрине!", type="positive", timeout=6000)
                    refresh_ready_books()
                else:
                    status_label.set_content(
                        '<div style="color:#cc4444;font-size:0.8rem">❌ Ошибка пайплайна — проверь лог</div>'
                    )

            except Exception as e:
                await on_log(f"❌ Критическая ошибка: {e}")
                import traceback
                await on_log(traceback.format_exc()[:600])
                status_label.set_content(
                    '<div style="color:#cc4444;font-size:0.8rem">❌ Ошибка — проверь лог</div>'
                )
            finally:
                pipeline_running["value"] = False
                run_btn.props(remove="disabled")

        # ════════════════════════════════════════
        # БЛОК 4: КНИГИ НА ВИТРИНЕ (текущие)
        # ════════════════════════════════════════
        with ui.element("div").classes("lb-card w-full"):
            ui.html("<h2>📚 Витрина · Готовые книги</h2>")
            ready_books_container = ui.column().classes("w-full gap-1")

        def refresh_ready_books():
            ready_books_container.clear()
            books = list_ready_books()
            with ready_books_container:
                if not books:
                    ui.html(
                        '<div style="color:var(--lb-text-dim);font-size:0.8rem;padding:8px">'
                        'Витрина пуста — загрузи первую книгу выше.</div>'
                    )
                    return
                for b in books:
                    created = b.get("created_at", "")[:10]
                    ui.html(f'''
                        <div class="lb-book-row">
                            <div>
                                <div class="lb-book-title">{b["title"]}</div>
                                <div class="lb-book-meta">{b["book_id"]} · {b["age_group"]} · герой: {b["main_character"]}</div>
                            </div>
                            <span class="lb-badge lb-badge-ready">на витрине</span>
                            <div class="lb-book-meta">{created}</div>
                        </div>
                    ''')

        refresh_ready_books()
