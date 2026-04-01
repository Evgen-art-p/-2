"""
Патч для studio/cabinet/tools.py — подключение библиотечных инструментов.

Добавляет library_tools (search_library, browse_shelf, read_book_excerpt, 
library_stats, recommend_for_agent) в Кабинет.

Запуск: python patch_tools_library.py
"""

import re
from pathlib import Path

TOOLS_FILE = Path("studio/cabinet/tools.py")

def patch():
    if not TOOLS_FILE.exists():
        print(f"❌ Файл не найден: {TOOLS_FILE}")
        return False

    text = TOOLS_FILE.read_text(encoding="utf-8")

    # Проверка: уже патчено?
    if "library_tools" in text:
        print("✅ library_tools уже подключены в tools.py")
        return True

    # 1. Добавляем импорт library_tools ПОСЛЕ импорта soul_tools
    soul_import_block = "try:\n    from studio.cabinet.soul_tools import SOUL_TOOLS_SCHEMA, dispatch_soul_tool"
    
    library_import = '''

# ══ Библиотека: library tools ══
try:
    from studio.cabinet.library_tools import LIBRARY_TOOLS_SCHEMA, dispatch_library_tool
    _LIBRARY_TOOLS_ENABLED = True
except ImportError:
    _LIBRARY_TOOLS_ENABLED = False
    async def dispatch_library_tool(fn, args): return None
    LIBRARY_TOOLS_SCHEMA = []'''

    # Вставляем после блока soul_tools (после его except)
    # Ищем конец блока soul_tools
    soul_end = "    SOUL_TOOLS_SCHEMA = []"
    if soul_end in text:
        text = text.replace(soul_end, soul_end + library_import, 1)
    else:
        print("⚠ Не нашёл конец блока soul_tools, вставляю после импортов")
        # Фоллбэк: вставляем перед TOOLS_SCHEMA
        text = text.replace("TOOLS_SCHEMA = [", library_import + "\n\nTOOLS_SCHEMA = [", 1)

    # 2. Добавляем library tools в TOOLS_SCHEMA (после soul tools extend)
    soul_extend = "if _SOUL_TOOLS_ENABLED:\n    TOOLS_SCHEMA.extend(SOUL_TOOLS_SCHEMA)"
    library_extend = """

# Добавляем library tools (Библиотека)
if _LIBRARY_TOOLS_ENABLED:
    TOOLS_SCHEMA.extend(LIBRARY_TOOLS_SCHEMA)"""

    if soul_extend in text:
        text = text.replace(soul_extend, soul_extend + library_extend, 1)
    else:
        print("⚠ Не нашёл SOUL_TOOLS extend, добавляю в конец TOOLS_SCHEMA")
        text += library_extend

    # 3. Добавляем dispatch в execute_tool (перед основными executors)
    dispatch_soul = "    # ══ Soul tools (Грондхейм) ══\n    if _SOUL_TOOLS_ENABLED:"
    dispatch_library = """    # ══ Library tools (Библиотека) ══
    if _LIBRARY_TOOLS_ENABLED:
        result = await dispatch_library_tool(fn, args)
        if result is not None:
            return result
"""

    if dispatch_soul in text:
        text = text.replace(dispatch_soul, dispatch_library + dispatch_soul, 1)
    else:
        print("⚠ Не нашёл dispatch_soul, добавляю перед executors dict")
        text = text.replace(
            '    executors = {',
            dispatch_library + '    executors = {',
            1,
        )

    # Сохраняем
    TOOLS_FILE.write_text(text, encoding="utf-8")
    print(f"✅ tools.py патчен: library_tools подключены")
    print(f"   Новые инструменты: search_library, browse_shelf, read_book_excerpt, library_stats, recommend_for_agent")
    return True


if __name__ == "__main__":
    patch()
