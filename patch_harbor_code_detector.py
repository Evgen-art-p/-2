#!/usr/bin/env python3
"""
patch_harbor_code_detector.py — Code-detector для Гавани Смыслов.

Проблема:
  JS/React/TS файлы просачиваются в индекс как "narrative" или "lore".
  json_ratio и template_markers не срабатывают на коде.

Решение:
  1. В _detect_content_type() — новый детектор "code":
     - по расширению файла (.js, .jsx, .ts, .tsx, .vue, .css, .html если попал)
     - по характерным паттернам кода (import React, useState, const =>, function, etc.)
  2. В index_file() — ранний выход если content_type == "code"
  3. В search_harbor() — "code" фильтруется как "template" (уже не попадёт,
     но на случай если в индексе остались старые чанки)

Запуск:
  python patch_harbor_code_detector.py
"""

from pathlib import Path
import re

TARGET = Path("studio/harbor_of_meanings.py")

# ─── ПАТЧ 1: _detect_content_type — добавляем code-детектор ─────────────────
# Вставляем после строки с проверкой расширения файла (в начало функции)

OLD_DETECT = '''def _detect_content_type(text: str, filepath_str: str) -> str:
    """
    Определяет тип контента: narrative / template / log / lore.

    - narrative: истории, рефлексии, описания персонажей, чистые смыслы
    - template: промпты агентов, JSON-шаблоны, output-форматы
    - log: результаты runs (chain_data, оценки, JSON-выходы агентов)
    - lore: концепции города, документация, философия
    """
    fp = filepath_str.lower()
    text_lower = text.lower()

    # По пути файла — ранние выходы
    if "grondheim_city" in fp and ("concept" in fp or "lore" in fp or "hexagon" in fp):
        return "lore"'''

NEW_DETECT = '''# Расширения которые всегда считаются кодом
_CODE_EXTENSIONS = {".js", ".jsx", ".ts", ".tsx", ".vue", ".svelte", ".css", ".scss", ".less"}

# Паттерны кода (достаточно 2 совпадений → это код)
_CODE_PATTERNS = [
    r"^import\s+React",
    r"^import\s+\{",
    r"^from\s+['\"]react['\"]",
    r"useState\s*\(",
    r"useEffect\s*\(",
    r"const\s+\w+\s*=\s*\(",   # const Component = (
    r"=>\s*\{",                 # стрелочные функции
    r"export\s+default\s+",
    r"export\s+const\s+",
    r"className\s*=",
    r"<[A-Z]\w+",               # JSX компоненты <Component
    r"ReactDOM\.render",
    r"\.map\s*\(\s*\(",
    r"props\.\w+",
    r"^\s*function\s+\w+\s*\(", # function declaration
    r"npm\s+install",
    r"require\s*\(['\"]",
]


def _is_code(text: str, filepath_str: str) -> bool:
    """Возвращает True если файл — программный код, а не нарратив."""
    fp = filepath_str.lower()

    # По расширению — сразу да
    suffix = Path(filepath_str).suffix.lower()
    if suffix in _CODE_EXTENSIONS:
        return True

    # По паттернам — нужно 2+ совпадения
    hits = sum(
        1 for pattern in _CODE_PATTERNS
        if re.search(pattern, text, re.MULTILINE)
    )
    return hits >= 2


def _detect_content_type(text: str, filepath_str: str) -> str:
    """
    Определяет тип контента: narrative / template / log / lore / code.

    - narrative: истории, рефлексии, описания персонажей, чистые смыслы
    - template: промпты агентов, JSON-шаблоны, output-форматы
    - log: результаты runs (chain_data, оценки, JSON-выходы агентов)
    - lore: концепции города, документация, философия
    - code: JS/React/TS/Vue и любой программный код — НЕ индексируется
    """
    fp = filepath_str.lower()
    text_lower = text.lower()

    # ── Code-детектор: первый, самый важный ──
    if _is_code(text, filepath_str):
        return "code"

    # По пути файла — ранние выходы
    if "grondheim_city" in fp and ("concept" in fp or "lore" in fp or "hexagon" in fp):
        return "lore"'''

# ─── ПАТЧ 2: index_file — ранний выход для code ──────────────────────────────

OLD_INDEX = '''    # ── Определяем тип контента ──
    content_type = _detect_content_type(text, str(filepath))

    # Метаданные'''

NEW_INDEX = '''    # ── Определяем тип контента ──
    content_type = _detect_content_type(text, str(filepath))

    # ── Код не индексируем — никогда ──
    if content_type == "code":
        print(f"[ГАВАНЬ] ⏭  Пропуск кода: {filepath.name}")
        return 0

    # Метаданные'''

# ─── ПАТЧ 3: search_harbor — фильтр code в выдаче (защита от старых чанков) ──

OLD_FILTER = '''            # ── Фильтр 3: скрываем template если не запрошено ──
            ct = meta.get("content_type", "")
            if ct == "template" and not include_templates:
                continue'''

NEW_FILTER = '''            # ── Фильтр 3: скрываем template и code если не запрошено ──
            ct = meta.get("content_type", "")
            if ct == "code":
                continue  # код никогда не показываем
            if ct == "template" and not include_templates:
                continue'''


def main():
    if not TARGET.exists():
        print(f"[ПАТЧ] ❌ Файл не найден: {TARGET}")
        return

    text = TARGET.read_text(encoding="utf-8")
    original = text
    applied = 0

    # Проверяем не пропатчено ли уже
    if "_is_code" in text:
        print("[ПАТЧ] ⚠️  _is_code уже существует — возможно уже пропатчено")
        return

    # ПАТЧ 1 — code-детектор в _detect_content_type
    if OLD_DETECT in text:
        text = text.replace(OLD_DETECT, NEW_DETECT, 1)
        print("[ПАТЧ] ✅ Добавлен _is_code() + обновлён _detect_content_type()")
        applied += 1
    else:
        print("[ПАТЧ] ❌ Не найден якорь ПАТЧ 1 (_detect_content_type)")

    # ПАТЧ 2 — ранний выход в index_file
    if OLD_INDEX in text:
        text = text.replace(OLD_INDEX, NEW_INDEX, 1)
        print("[ПАТЧ] ✅ Добавлен ранний выход для code в index_file()")
        applied += 1
    else:
        print("[ПАТЧ] ❌ Не найден якорь ПАТЧ 2 (index_file)")

    # ПАТЧ 3 — фильтр в search_harbor
    if OLD_FILTER in text:
        text = text.replace(OLD_FILTER, NEW_FILTER, 1)
        print("[ПАТЧ] ✅ Добавлен фильтр code в search_harbor()")
        applied += 1
    else:
        print("[ПАТЧ] ❌ Не найден якорь ПАТЧ 3 (search_harbor)")

    if text == original:
        print("[ПАТЧ] ℹ️  Файл не изменён")
        return

    if applied < 3:
        print(f"[ПАТЧ] ⚠️  Применено только {applied}/3 патчей — проверь вручную")

    # Бэкап
    backup = TARGET.with_suffix(".py.bak_codedetector")
    backup.write_text(original, encoding="utf-8")
    print(f"[ПАТЧ] 💾 Бэкап: {backup}")

    TARGET.write_text(text, encoding="utf-8")
    print(f"[ПАТЧ] ✅ Записано: {TARGET}")
    print()
    print(f"[ПАТЧ] 🏁 Готово ({applied}/3 патчей)")
    print()
    print("  Теперь:")
    print("  • .js/.jsx/.ts/.tsx/.vue → пропускаются при индексации")
    print("  • Код с 2+ паттернами (import React, useState, =>) → пропускается")
    print("  • Старые code-чанки в индексе → фильтруются при поиске")
    print()
    print("  Рекомендую пересобрать индекс чтобы выгнать старые чанки:")
    print("  python -m studio.harbor_of_meanings --reindex")


if __name__ == "__main__":
    main()
