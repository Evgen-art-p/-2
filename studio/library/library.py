"""
📚 БИБЛИОТЕКА ГРОНДХЕЙМА — Курированные знания Студии

Маяк смотрит наружу (web_search).
Гавань смотрит внутрь (RAG по сырым архивам).
Библиотека даёт структурированные знания — книги по полкам.

Принцип тот же: Локация = Инструмент.
Агент приходит на прогулке → library_visit() → «Прочитанный Смысл» → sensory_memory.
При работе → get_library_book() подбирает книгу под задачу.

Структура:
  library/
  ├── catalog.json        ← реестр всех книг
  ├── craft/              ← Ремесло
  ├── psychology/         ← Психология
  ├── marketing/          ← Маркетинг
  ├── tech/               ← Технологии
  ├── grondheim/          ← Лор города
  └── product/            ← Продукт

Каждая книга = единица знания с id, section, tags, depth, for_depts.
"""

import json
import re
import random
from pathlib import Path
from typing import Optional

# ═══════════════════════════════════════════════════════
# КОНФИГ
# ═══════════════════════════════════════════════════════

LIBRARY_ROOT = Path("studio/library")
CATALOG_FILE = LIBRARY_ROOT / "catalog.json"

# Маппинг depth → минимальный порог ДНК (Aesthetic или Empathy)
DEPTH_DNA_MAP = {
    "basic": 0.0,
    "applied": 0.3,
    "deep": 0.6,
}

# ═══════════════════════════════════════════════════════
# КАТАЛОГ
# ═══════════════════════════════════════════════════════

_catalog_cache = None


def _load_catalog() -> dict:
    """Загружает каталог книг. Кешируется."""
    global _catalog_cache
    if _catalog_cache is not None:
        return _catalog_cache

    if not CATALOG_FILE.exists():
        print("[БИБЛИОТЕКА] ⚠ catalog.json не найден")
        return {"books": [], "sections": {}}

    try:
        data = json.loads(CATALOG_FILE.read_text(encoding="utf-8"))
        _catalog_cache = data
        print(f"[БИБЛИОТЕКА] 📚 Каталог загружен: {len(data.get('books', []))} книг")
        return data
    except Exception as e:
        print(f"[БИБЛИОТЕКА] ❌ Ошибка загрузки каталога: {e}")
        return {"books": [], "sections": {}}


def reload_catalog():
    """Принудительная перезагрузка каталога."""
    global _catalog_cache
    _catalog_cache = None
    return _load_catalog()


def get_all_books() -> list[dict]:
    """Все книги из каталога."""
    return _load_catalog().get("books", [])


def get_book_by_id(book_id: str) -> Optional[dict]:
    """Находит книгу по ID."""
    for book in get_all_books():
        if book["id"] == book_id:
            return book
    return None


def get_books_by_section(section: str) -> list[dict]:
    """Все книги из секции."""
    return [b for b in get_all_books() if b.get("section") == section]


def get_books_by_tag(tag: str) -> list[dict]:
    """Все книги с указанным тегом."""
    return [b for b in get_all_books() if tag in b.get("tags", [])]


def get_books_for_dept(dept: str) -> list[dict]:
    """Книги, подходящие для конкретного цеха."""
    result = []
    for book in get_all_books():
        depts = book.get("for_depts", [])
        if "_all" in depts or dept in depts:
            result.append(book)
    return result


# ═══════════════════════════════════════════════════════
# ЧТЕНИЕ КНИГИ
# ═══════════════════════════════════════════════════════

def read_book(book: dict, max_chars: int = 3000) -> str:
    """
    Читает содержимое книги с диска.
    Возвращает текст, обрезанный до max_chars.
    """
    filepath = LIBRARY_ROOT / book.get("file", "")
    if not filepath.exists():
        return ""

    try:
        text = filepath.read_text(encoding="utf-8")
        if len(text) > max_chars:
            text = text[:max_chars] + "\n\n[...книга продолжается...]"
        return text
    except Exception as e:
        print(f"[БИБЛИОТЕКА] ⚠ Не прочитать {filepath}: {e}")
        return ""


# ═══════════════════════════════════════════════════════
# ПОДБОР КНИГИ ПО ДНК
# ═══════════════════════════════════════════════════════

def pick_book_for_agent(
    dept: str,
    agent_dna: dict = None,
    preferred_tags: list = None,
    exclude_ids: list = None,
) -> Optional[dict]:
    """
    Умный подбор книги для агента на основе:
    - Его цеха (dept)
    - Его ДНК (Aesthetic_Threshold / Empathy → depth)
    - Предпочтений по тегам
    - Исключений (уже читал)

    Возвращает dict книги или None.
    """
    candidates = get_books_for_dept(dept)
    if not candidates:
        candidates = get_all_books()

    if not candidates:
        return None

    # Только книги с реальным файлом
    candidates = [b for b in candidates if (LIBRARY_ROOT / b.get("file", "")).exists()]
    if not candidates:
        return None

    # Фильтр: исключаем уже прочитанные
    if exclude_ids:
        filtered = [b for b in candidates if b["id"] not in exclude_ids]
        if filtered:
            candidates = filtered

    # Фильтр: depth по ДНК
    if agent_dna:
        aesthetic = agent_dna.get("Aesthetic_Threshold", 0.5)
        empathy = agent_dna.get("Empathy", 0.5)
        agent_score = max(aesthetic, empathy)

        filtered = []
        for book in candidates:
            depth = book.get("depth", "basic")
            min_score = DEPTH_DNA_MAP.get(depth, 0.0)
            if agent_score >= min_score:
                filtered.append(book)

        if filtered:
            candidates = filtered

    # Буст: если есть preferred_tags, сортируем по совпадению тегов
    if preferred_tags:
        def tag_score(book):
            return sum(1 for t in preferred_tags if t in book.get("tags", []))
        candidates.sort(key=tag_score, reverse=True)
        top = candidates[:3]
        return random.choice(top)

    return random.choice(candidates)


# ═══════════════════════════════════════════════════════
# ИНТЕГРАЦИЯ С CITY_WALKER (при визите в Библиотеку)
# ═══════════════════════════════════════════════════════

async def library_visit(
    agent_name: str,
    agent_profession: str,
    agent_dna: dict,
    dept: str = "",
    system_prompt: str = "",
    temperature: float = 0.7,
) -> str:
    """
    Агент пришёл в Библиотеку Грондхейма на прогулке.

    1. Подбирает книгу по ДНК и цеху
    2. Читает её
    3. Рефлексирует — что понял, как применит
    4. Возвращает «Прочитанный Смысл»
    """
    import asyncio
    from studio.llm import chat

    # Шаг 1: Подбираем книгу
    book = pick_book_for_agent(dept=dept, agent_dna=agent_dna)

    if not book:
        print(f"[БИБЛИОТЕКА] 📭 {agent_name}: каталог пуст")
        return "Библиотека была пуста. Полки ждут своих книг."

    content = read_book(book, max_chars=2000)
    if not content:
        print(f"[БИБЛИОТЕКА] ⚠ {agent_name}: книга '{book['title']}' пуста")
        return "Взял книгу с полки, но страницы оказались чистыми."

    book_title = book["title"]
    print(f"[БИБЛИОТЕКА] 📖 {agent_name} читает: «{book_title}»")

    # Шаг 2: Рефлексия через LLM
    reflect_prompt = (
        f"Ты — {agent_name}, {agent_profession}.\n"
        f"Ты в Библиотеке Грондхейма. Взял книгу с полки:\n"
        f"«{book_title}» (секция: {book.get('section', '?')})\n\n"
        f"Вот отрывок:\n{content[:1500]}\n\n"
        f"Запиши ВЫЖИМКУ — что ты понял и как это пригодится в твоей работе.\n"
        f"2-3 предложения. Формат:\n"
        f"ПРОЧИТАННЫЙ СМЫСЛ: <что узнал и зачем это нужно>"
    )

    try:
        loop = asyncio.get_event_loop()
        reflection = await loop.run_in_executor(
            None,
            lambda: chat(
                system_prompt or f"Ты {agent_name}.",
                reflect_prompt, "",
                temperature=temperature,
            )
        )

        match = re.search(r"ПРОЧИТАННЫЙ СМЫСЛ:\s*(.+)", reflection, re.DOTALL)
        if match:
            found_meaning = match.group(1).strip()[:500]
        else:
            found_meaning = reflection[:500]

        print(f"[БИБЛИОТЕКА] ✨ {agent_name} усвоил: {found_meaning[:120]}...")
        return found_meaning

    except Exception as e:
        print(f"[БИБЛИОТЕКА] ❌ {agent_name}: ошибка рефлексии — {e}")
        return f"Читал «{book_title}», но мысли пока не улеглись."


# ═══════════════════════════════════════════════════════
# ИНТЕГРАЦИЯ С ПАЙПЛАЙНОМ
# ═══════════════════════════════════════════════════════

def get_library_book(
    worker_id: str,
    dept: str,
    task_tags: list = None,
    max_chars: int = 2000,
) -> str:
    """
    Достаёт книгу из Библиотеки для агента во время работы.
    Вызывается из pipeline.py → build_agent_context().

    Возвращает отформатированный текст для инжекта в контекст.
    """
    book = pick_book_for_agent(dept=dept, preferred_tags=task_tags)

    if not book:
        return ""

    content = read_book(book, max_chars=max_chars)
    if not content:
        return ""

    result = (
        f"=== 📚 КНИГА ИЗ БИБЛИОТЕКИ ===\n"
        f"«{book['title']}» (секция: {book.get('section', '?')}, "
        f"глубина: {book.get('depth', '?')})\n\n"
        f"{content}\n"
        f"=== КОНЕЦ КНИГИ ==="
    )

    print(f"[БИБЛИОТЕКА→PIPELINE] 📚 {worker_id} получил «{book['title']}»")
    return result


# ═══════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys

    if "--list" in sys.argv:
        catalog = _load_catalog()
        books = catalog.get("books", [])
        sections = catalog.get("sections", {})

        print(f"📚 Библиотека Грондхейма: {len(books)} книг\n")
        for sec_id, sec_desc in sections.items():
            sec_books = [b for b in books if b.get("section") == sec_id]
            print(f"  [{sec_id}] {sec_desc}")
            for b in sec_books:
                has_file = "✅" if (LIBRARY_ROOT / b.get("file", "")).exists() else "📝"
                print(f"    {has_file} {b['id']}: {b['title']} ({b['depth']})")
            if not sec_books:
                print("    (пусто)")
            print()

    elif "--read" in sys.argv:
        idx = sys.argv.index("--read")
        book_id = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else ""
        if not book_id:
            print("Использование: --read <book_id>")
            sys.exit(1)
        book = get_book_by_id(book_id)
        if not book:
            print(f"❌ Книга '{book_id}' не найдена")
            sys.exit(1)
        content = read_book(book)
        print(f"📖 {book['title']}\n")
        print(content[:2000])

    elif "--pick" in sys.argv:
        idx = sys.argv.index("--pick")
        dept = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else "living_book"
        book = pick_book_for_agent(dept=dept)
        if book:
            print(f"📚 Для цеха [{dept}] подобрана:")
            print(f"   «{book['title']}» ({book['depth']})")
            print(f"   Теги: {', '.join(book.get('tags', []))}")
            print(f"   Файл: {book.get('file', '?')}")
        else:
            print(f"📭 Для цеха [{dept}] книг не нашлось")

    elif "--stats" in sys.argv:
        catalog = _load_catalog()
        books = catalog.get("books", [])
        existing = sum(1 for b in books if (LIBRARY_ROOT / b.get("file", "")).exists())
        print(f"📚 Всего книг в каталоге: {len(books)}")
        print(f"✅ С содержимым: {existing}")
        print(f"📝 Без файла: {len(books) - existing}")
        print(f"📂 Секций: {len(catalog.get('sections', {}))}")

    else:
        print("📚 Библиотека Грондхейма")
        print()
        print("Команды:")
        print("  --list              Все книги по секциям")
        print("  --read <book_id>    Прочитать книгу")
        print("  --pick <dept>       Подобрать книгу для цеха")
        print("  --stats             Статистика библиотеки")
