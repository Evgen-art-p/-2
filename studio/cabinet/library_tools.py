# studio/cabinet/library_tools.py — Инструменты Библиотеки для Кабинета
# Оле (и любой резидент) может использовать их через tool use.
# Подключается в tools.py аналогично soul_tools.py.

import json
from pathlib import Path
from typing import Optional

# Используем функции из library.py
from studio.library.library import (
    get_all_books,
    get_book_by_id,
    get_books_by_section,
    get_books_by_tag,
    read_book,
    browse_shelf,
    format_book_card,
    pick_book_for_agent,
    reload_catalog,
    LIBRARY_ROOT,
    CATALOG_FILE,
)

# ═══════════════════════════════════════════════════
#  TOOL SCHEMA (OpenRouter function calling)
# ═══════════════════════════════════════════════════

LIBRARY_TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "search_library",
            "description": "Поиск книг в Библиотеке Грондхейма по тегам или ключевым словам. Возвращает список книг с аннотациями.",
            "parameters": {
                "type": "object",
                "properties": {
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Теги для поиска (напр. ['привязанность', 'ребёнок'] или ['сторителлинг'])"
                    },
                    "query": {
                        "type": "string",
                        "description": "Текстовый запрос — ищет в названиях, аннотациях и тегах книг"
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browse_shelf",
            "description": "Посмотреть полку секции Библиотеки. Показывает все книги секции с аннотациями.",
            "parameters": {
                "type": "object",
                "properties": {
                    "section": {
                        "type": "string",
                        "enum": ["craft", "psychology", "marketing", "tech", "grondheim", "product"],
                        "description": "Секция библиотеки"
                    }
                },
                "required": ["section"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_book_excerpt",
            "description": "Прочитать начало книги из Библиотеки по её ID. Возвращает первые 2000 символов текста.",
            "parameters": {
                "type": "object",
                "properties": {
                    "book_id": {
                        "type": "string",
                        "description": "ID книги из каталога (напр. psych_001, craft_001, grond_001)"
                    }
                },
                "required": ["book_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "library_stats",
            "description": "Общая статистика Библиотеки Грондхейма: количество книг, секции, глубина, аннотации.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "recommend_for_agent",
            "description": "Подобрать книгу для конкретного агента по его ДНК и задаче. Учитывает depth и теги.",
            "parameters": {
                "type": "object",
                "properties": {
                    "agent_id": {
                        "type": "string",
                        "description": "ID агента (напр. A01, T1, A00)"
                    },
                    "task_tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Теги задачи агента (напр. ['сценарий', 'ребёнок', 'сказка'])"
                    }
                },
                "required": ["agent_id"]
            }
        }
    },
]


# ═══════════════════════════════════════════════════
#  TOOL EXECUTORS
# ═══════════════════════════════════════════════════

async def dispatch_library_tool(fn: str, args: dict) -> Optional[str]:
    """Диспетчер библиотечных инструментов. Возвращает None если fn не наш."""
    executors = {
        "search_library": _exec_search_library,
        "browse_shelf": _exec_browse_shelf,
        "read_book_excerpt": _exec_read_book_excerpt,
        "library_stats": _exec_library_stats,
        "recommend_for_agent": _exec_recommend_for_agent,
    }
    executor = executors.get(fn)
    if executor is None:
        return None
    return await executor(args)


async def _exec_search_library(args: dict) -> str:
    """Поиск книг по тегам и/или текстовому запросу."""
    tags = args.get("tags", [])
    query = args.get("query", "").lower().strip()

    all_books = get_all_books()
    if not all_books:
        return "📭 Библиотека пуста. Каталог не загружен."

    results = []

    for book in all_books:
        score = 0

        # Матч по тегам
        if tags:
            book_tags = book.get("tags", [])
            for t in tags:
                if t.lower() in [bt.lower() for bt in book_tags]:
                    score += 2

        # Матч по текстовому запросу
        if query:
            title = book.get("title", "").lower()
            annotation = book.get("annotation", "").lower()
            tags_str = " ".join(book.get("tags", [])).lower()
            searchable = f"{title} {annotation} {tags_str}"
            if query in searchable:
                score += 1

        if score > 0:
            results.append((score, book))

    if not results:
        search_desc = []
        if tags:
            search_desc.append(f"теги: {', '.join(tags)}")
        if query:
            search_desc.append(f"запрос: '{query}'")
        return f"📭 По запросу ({'; '.join(search_desc)}) ничего не нашлось. Попробуй другие теги."

    # Сортируем по score
    results.sort(key=lambda x: x[0], reverse=True)

    lines = [f"📚 Найдено {len(results)} книг:\n"]
    for score, book in results[:10]:
        has_file = "✅" if (LIBRARY_ROOT / book.get("file", "")).exists() else "📝"
        annotation = book.get("annotation", "без аннотации")
        lines.append(
            f"{has_file} {book['id']}: «{book['title']}» ({book['depth']})\n"
            f"   📝 {annotation}\n"
            f"   Теги: {', '.join(book.get('tags', [])[:5])}"
        )

    return "\n".join(lines)


async def _exec_browse_shelf(args: dict) -> str:
    """Показать все книги секции."""
    section = args.get("section", "")
    if not section:
        return "Укажи секцию: craft, psychology, marketing, tech, grondheim, product"

    books = get_books_by_section(section)
    if not books:
        return f"📭 Секция '{section}' пуста. Пока ни одной книги."

    # Названия секций
    section_names = {
        "craft": "Ремесло",
        "psychology": "Психология",
        "marketing": "Маркетинг",
        "tech": "Технологии",
        "grondheim": "Грондхейм",
        "product": "Продукт",
    }

    lines = [f"📚 Полка «{section_names.get(section, section)}» — {len(books)} книг:\n"]
    for book in books:
        has_file = "✅" if (LIBRARY_ROOT / book.get("file", "")).exists() else "📝"
        annotation = book.get("annotation", "")
        source = book.get("source", "")
        lines.append(
            f"{has_file} {book['id']}: «{book['title']}» ({book['depth']})"
        )
        if annotation:
            lines.append(f"   📝 {annotation}")
        if source:
            lines.append(f"   ← {source}")
        lines.append(f"   Теги: {', '.join(book.get('tags', [])[:5])}")
        linked = book.get("linked_books", [])
        if linked:
            lines.append(f"   Связи: {', '.join(linked)}")
        lines.append("")

    return "\n".join(lines)


async def _exec_read_book_excerpt(args: dict) -> str:
    """Прочитать начало книги."""
    book_id = args.get("book_id", "")
    if not book_id:
        return "Укажи book_id (напр. psych_001, craft_001)."

    book = get_book_by_id(book_id)
    if not book:
        return f"📭 Книга '{book_id}' не найдена в каталоге."

    content = read_book(book, max_chars=2000)
    if not content:
        return f"📝 Книга «{book['title']}» зарегистрирована, но файл пуст или не найден."

    annotation = book.get("annotation", "")
    annotation_line = f"\n📝 {annotation}\n" if annotation else ""

    return (
        f"📖 «{book['title']}» ({book['section']}, {book['depth']})\n"
        f"{annotation_line}"
        f"Теги: {', '.join(book.get('tags', []))}\n"
        f"{'─' * 40}\n"
        f"{content}"
    )


async def _exec_library_stats(args: dict) -> str:
    """Статистика библиотеки."""
    all_books = get_all_books()
    if not all_books:
        return "📭 Каталог пуст."

    existing = sum(1 for b in all_books if (LIBRARY_ROOT / b.get("file", "")).exists())
    with_annotation = sum(1 for b in all_books if b.get("annotation"))

    by_depth = {}
    by_section = {}
    for b in all_books:
        d = b.get("depth", "?")
        s = b.get("section", "?")
        by_depth[d] = by_depth.get(d, 0) + 1
        by_section[s] = by_section.get(s, 0) + 1

    lines = [
        f"📚 Библиотека Грондхейма",
        f"",
        f"Всего книг: {len(all_books)}",
        f"  С файлом: {existing}",
        f"  Без файла: {len(all_books) - existing}",
        f"  С аннотацией: {with_annotation}",
        f"",
        f"По секциям:",
    ]
    section_names = {
        "craft": "Ремесло", "psychology": "Психология", "marketing": "Маркетинг",
        "tech": "Технологии", "grondheim": "Грондхейм", "product": "Продукт",
    }
    for sec, count in sorted(by_section.items()):
        lines.append(f"  {section_names.get(sec, sec)}: {count}")

    lines.append(f"\nПо глубине:")
    depth_names = {"basic": "Основы", "applied": "Практика", "deep": "Глубина"}
    for dep, count in sorted(by_depth.items()):
        lines.append(f"  {depth_names.get(dep, dep)}: {count}")

    return "\n".join(lines)


async def _exec_recommend_for_agent(args: dict) -> str:
    """Подобрать книгу для агента по его ДНК."""
    from studio.cabinet.agents import _get_agent_dna, _get_agent_info

    agent_id = args.get("agent_id", "")
    task_tags = args.get("task_tags", [])

    if not agent_id:
        return "Укажи agent_id."

    info = _get_agent_info(agent_id)
    dna = _get_agent_dna(agent_id)

    if not dna:
        return f"ДНК агента {agent_id} не найдена."

    label = info.get("label", agent_id)
    static = dna.get("static", {})
    aesthetic = static.get("Aesthetic_Threshold", 0.5)
    empathy = static.get("Empathy", 0.5)

    # Подбираем 3 книги
    shelf = browse_shelf(
        agent_dna=static,
        preferred_tags=task_tags or None,
        n=3,
    )

    if not shelf:
        return f"📭 Для {label} ({agent_id}) ничего не подобрать — каталог пуст."

    lines = [
        f"📚 Рекомендации для {label} ({agent_id})",
        f"   Aesthetic={aesthetic:.2f}, Empathy={empathy:.2f}",
    ]
    if task_tags:
        lines.append(f"   Задача: {', '.join(task_tags)}")
    lines.append("")

    for i, book in enumerate(shelf, 1):
        annotation = book.get("annotation", "без аннотации")
        lines.append(
            f"{i}. «{book['title']}» ({book['depth']})\n"
            f"   📝 {annotation}\n"
            f"   Теги: {', '.join(book.get('tags', [])[:5])}"
        )

    return "\n".join(lines)
