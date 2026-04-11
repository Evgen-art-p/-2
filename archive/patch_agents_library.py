"""
Патч для studio/cabinet/agents.py — добавляем _get_library_context() 
для инъекции каталога в system prompt Оле.

Когда в Кабинете выбирают Оле → home_prompt.md загружается как обычно,
а к нему добавляется полный каталог книг из catalog.json.

Запуск: python patch_agents_library.py

ПРИМЕЧАНИЕ: Этот патч добавляет ОДНУ функцию в agents.py.
Вызов _get_library_context() нужно добавить в ui_cabinet.py 
при сборке system_prompt для резидента (если agent_id == "004_OLE").
"""

from pathlib import Path

AGENTS_FILE = Path("studio/cabinet/agents.py")

LIBRARY_CONTEXT_FUNC = '''

# ═══════════════════════════════════════════════════
#  LIBRARY CONTEXT (для Оле)
# ═══════════════════════════════════════════════════

def _get_library_context() -> str:
    """Загружает каталог библиотеки как контекст для Оле.
    
    Вызывается при сборке system_prompt когда выбран агент 004_OLE.
    Возвращает строку с полным каталогом книг для инъекции в промпт.
    """
    import json
    catalog_file = Path("studio/library/catalog.json")
    if not catalog_file.exists():
        return "\\n[КАТАЛОГ БИБЛИОТЕКИ: не найден]\\n"
    
    try:
        catalog = json.loads(catalog_file.read_text(encoding="utf-8"))
        books = catalog.get("books", [])
        sections = catalog.get("sections", {})
        
        lines = ["\\n=== КАТАЛОГ БИБЛИОТЕКИ ГРОНДХЕЙМА ==="]
        lines.append(f"Всего книг: {len(books)}\\n")
        
        for sec_id, sec_desc in sections.items():
            sec_books = [b for b in books if b.get("section") == sec_id]
            if not sec_books:
                continue
            lines.append(f"📚 {sec_desc} [{sec_id}]:")
            for b in sec_books:
                annotation = b.get("annotation", "")
                tags = ", ".join(b.get("tags", [])[:5])
                linked = b.get("linked_books", [])
                lines.append(f"  • {b['id']}: «{b['title']}» ({b['depth']})")
                if annotation:
                    lines.append(f"    📝 {annotation}")
                lines.append(f"    Теги: [{tags}]")
                if linked:
                    lines.append(f"    Связи: {', '.join(linked)}")
            lines.append("")
        
        lines.append("=== КОНЕЦ КАТАЛОГА ===")
        return "\\n".join(lines)
    except Exception as e:
        return f"\\n[КАТАЛОГ БИБЛИОТЕКИ: ошибка загрузки — {e}]\\n"
'''

def patch():
    if not AGENTS_FILE.exists():
        print(f"❌ Файл не найден: {AGENTS_FILE}")
        return False

    text = AGENTS_FILE.read_text(encoding="utf-8")

    if "_get_library_context" in text:
        print("✅ _get_library_context уже есть в agents.py")
        return True

    # Добавляем функцию в конец файла (перед UI RENDER HELPERS)
    marker = "# ═══════════════════════════════════════════════════\n#  UI RENDER HELPERS"
    if marker in text:
        text = text.replace(marker, LIBRARY_CONTEXT_FUNC + "\n" + marker, 1)
    else:
        # Фоллбэк — просто в конец
        text += LIBRARY_CONTEXT_FUNC

    AGENTS_FILE.write_text(text, encoding="utf-8")
    print(f"✅ agents.py патчен: _get_library_context() добавлена")
    print(f"")
    print(f"СЛЕДУЮЩИЙ ШАГ: в ui_cabinet.py при сборке system_prompt резидента,")
    print(f"если agent_id == '004_OLE', добавь:")
    print(f"  from studio.cabinet.agents import _get_library_context")
    print(f"  system_prompt += _get_library_context()")
    return True


if __name__ == "__main__":
    patch()
