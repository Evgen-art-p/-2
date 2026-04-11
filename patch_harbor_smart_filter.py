"""
🔧 ПАТЧ: Умная фильтрация Гавани Смыслов v2

Что делает:
  1. Фикс print (рассинхрон названия модели)
  2. Новая функция _clean_text() — вырезает JSON-блоки, шаблоны, мусор
  3. Новая функция _detect_content_type() — narrative/template/log/lore
  4. Обогащение метаданных: content_type при индексации
  5. Авто-фильтрация template при поиске (content_type != template)
  6. Контекстный prefix для passage: (dept-aware)
  7. Дедупликация: max 2 чанка с одного source
  8. Минимальный размер чанка после очистки: 100 символов

Запуск:
  python patch_harbor_smart_filter.py

Бэкап создаётся автоматически.
"""

import re
import shutil
from pathlib import Path
from datetime import datetime

TARGET = Path("studio/harbor_of_meanings.py")
BACKUP = TARGET.with_suffix(f".py.bak2")


def patch():
    if not TARGET.exists():
        print(f"❌ Файл не найден: {TARGET}")
        return False

    text = TARGET.read_text(encoding="utf-8")

    # ═══════════════════════════════════════════════════
    # ПАТЧ 1: Фикс print рассинхрона модели
    # ═══════════════════════════════════════════════════

    old_print = 'print("[ГАВАНЬ] 🌍 Embedding: paraphrase-multilingual-MiniLM-L12-v2")'
    new_print = 'print("[ГАВАНЬ] 🌍 Embedding: intfloat/multilingual-e5-large")'

    if old_print in text:
        text = text.replace(old_print, new_print)
        print("✅ Патч 1: Фикс print модели")
    else:
        print("⏭  Патч 1: print уже актуален или не найден")

    # ═══════════════════════════════════════════════════
    # ПАТЧ 2: Добавить _clean_text() и _detect_content_type()
    #         ПЕРЕД секцией ЧАНКИРОВАНИЕ
    # ═══════════════════════════════════════════════════

    clean_text_block = '''
# ═══════════════════════════════════════════════════════
# ОЧИСТКА И КЛАССИФИКАЦИЯ ТЕКСТА
# ═══════════════════════════════════════════════════════

# Паттерны шума, которые вырезаются перед индексацией
_NOISE_PATTERNS = [
    # JSON-блоки из промптов агентов
    (r'👇\s*SYSTEM_JSON_START\s*👇.*?👆\s*SYSTEM_JSON_END\s*👆', re.DOTALL),
    # chain_data блоки
    (r'"chain_data"\s*:\s*\{[^}]*\{\{inherit\}\}[^}]*\}', re.DOTALL),
    # Целые JSON-объекты (многострочные)
    (r'^\s*\{[\\s\\S]*?"next_step"\s*:.*?\}\s*$', re.MULTILINE | re.DOTALL),
    # Строки с {{inherit}}
    (r'^.*\{\{inherit\}\}.*$', re.MULTILINE),
    # Markdown таблицы-шаблоны (пустые: | ... | ... |)
    (r'^\|[\s.]+\|[\s.]+\|$', re.MULTILINE),
]

# Маркеры шаблонного контента
_TEMPLATE_MARKERS = [
    '{{inherit}}', 'SYSTEM_JSON_START', 'SYSTEM_JSON_END',
    '{{my_output}}', 'next_step', '"chain_data"',
    '👇 SYSTEM_JSON', '👆 SYSTEM_JSON',
]

# Маркеры нарративного контента
_NARRATIVE_MARKERS = [
    'история', 'сказка', 'рассказ', 'персонаж', 'сцена',
    'глава', 'диалог', 'чувств', 'эмоци', 'мораль',
    'ребёнок', 'ребенок', 'герой', 'приключени',
    'НАЙДЕННЫЙ СМЫСЛ', 'ЧИСТЫЙ СМЫСЛ', 'рефлекси',
]


def _clean_text(text: str) -> str:
    """
    Очищает текст от JSON-шаблонов, chain_data, {{inherit}} и прочего мусора.
    Возвращает чистый текст, пригодный для embedding.
    """
    cleaned = text

    # Вырезаем JSON-блоки между маркерами
    cleaned = re.sub(
        r'👇\s*SYSTEM_JSON_START\s*👇.*?👆\s*SYSTEM_JSON_END\s*👆',
        '', cleaned, flags=re.DOTALL
    )

    # Вырезаем блоки ```json ... ``` и ``` ... ```
    cleaned = re.sub(r'```(?:json)?\s*\n.*?\n```', '', cleaned, flags=re.DOTALL)

    # Вырезаем строки с {{inherit}} и {{my_output}}
    cleaned = re.sub(r'^.*\{\{(?:inherit|my_output)\}\}.*$', '', cleaned, flags=re.MULTILINE)

    # Вырезаем многострочные JSON-объекты (начинаются с { и содержат "key":)
    # Но только если это > 5 строк (маленькие JSON могут быть полезны)
    def _remove_large_json(match):
        block = match.group(0)
        if block.count('\\n') > 5 or len(block) > 500:
            return ''
        return block

    cleaned = re.sub(
        r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}',
        _remove_large_json, cleaned, flags=re.DOTALL
    )

    # Убираем пустые строки (больше 2 подряд → 2)
    cleaned = re.sub(r'\n{3,}', '\\n\\n', cleaned)

    # Убираем строки только из пунктуации/пробелов
    cleaned = re.sub(r'^[\s|\\-=_*#>]+$', '', cleaned, flags=re.MULTILINE)

    return cleaned.strip()


def _detect_content_type(text: str, filepath_str: str) -> str:
    """
    Определяет тип контента: narrative / template / log / lore.

    - narrative: истории, рефлексии, описания персонажей, чистые смыслы
    - template: промпты агентов, JSON-шаблоны, output-форматы
    - log: результаты runs (chain_data, оценки, JSON-выходы агентов)
    - lore: концепции города, документация, философия
    """
    fp = filepath_str.lower()
    text_lower = text.lower()

    # По пути файла
    if 'grondheim_city' in fp and ('concept' in fp or 'lore' in fp or 'hexagon' in fp):
        return 'lore'

    # Шаблон-детектор: считаем маркеры
    template_hits = sum(1 for m in _TEMPLATE_MARKERS if m.lower() in text_lower)
    if template_hits >= 2:
        return 'template'

    # JSON-ratio: если > 30% текста — фигурные скобки и кавычки → template/log
    json_chars = sum(1 for c in text if c in '{}[]":\\')
    json_ratio = json_chars / max(len(text), 1)

    if json_ratio > 0.30:
        if 'runs' in fp:
            return 'log'
        return 'template'

    # Нарратив-детектор
    narrative_hits = sum(1 for m in _NARRATIVE_MARKERS if m in text_lower)
    if narrative_hits >= 2:
        return 'narrative'

    # По пути
    if 'runs' in fp:
        return 'log'
    if 'knowledge' in fp:
        return 'lore'
    if 'promt' in fp or 'prompt' in fp:
        return 'template'
    if 'grondheim_city' in fp:
        return 'lore'
    if 'anchor_points' in fp or 'home_prompt' in fp:
        return 'narrative'
    if 'sensory' in fp:
        return 'narrative'

    return 'lore'  # default для неопределённых


def _build_passage_prefix(filepath_str: str, content_type: str) -> str:
    """
    Строит контекстный prefix для passage: embedding.
    Даёт e5-large дополнительный семантический сигнал.
    """
    fp = filepath_str.lower()
    parts = []

    # Определяем цех
    dept_map = {
        'living_book': 'детская книга сказка',
        'web_story': 'веб-история визуал',
        'video_long': 'видео сценарий',
        'video_shorts': 'короткое видео',
        'social_mix': 'соцсети контент',
        'turbo': 'быстрый контент',
        'clipmakers': 'клипы монтаж',
        'advertising': 'реклама маркетинг',
        'emo_card': 'эмоциональная открытка',
        'logo_design': 'логотип дизайн',
        'market_hit': 'маркетинг хит',
    }

    for dept_key, dept_desc in dept_map.items():
        if dept_key in fp:
            parts.append(dept_desc)
            break

    # Тип контента
    type_map = {
        'narrative': 'история персонаж сюжет',
        'lore': 'знания концепция документация',
        'log': 'результат проект отчёт',
        'template': 'шаблон промпт инструкция',
    }
    parts.append(type_map.get(content_type, ''))

    prefix = ' '.join(parts).strip()
    return f"passage: {prefix} — " if prefix else "passage: "

'''

    # Вставляем перед секцией ЧАНКИРОВАНИЕ
    anchor_chunk = '# ═══════════════════════════════════════════════════════\n# ЧАНКИРОВАНИЕ'

    if '_clean_text' not in text:
        if anchor_chunk in text:
            text = text.replace(anchor_chunk, clean_text_block + '\n' + anchor_chunk)
            print("✅ Патч 2: _clean_text() + _detect_content_type() + _build_passage_prefix()")
        else:
            print("❌ Патч 2: не нашёл якорь ЧАНКИРОВАНИЕ")
            return False
    else:
        print("⏭  Патч 2: _clean_text уже существует")

    # ═══════════════════════════════════════════════════
    # ПАТЧ 3: Модифицируем index_file() — очистка + content_type + prefix
    # ═══════════════════════════════════════════════════

    # Заменяем блок от "if len(text.strip()) < 50:" до "chunks = _chunk_text("
    old_index_block = '''    if len(text.strip()) < 50:
        return 0

    # Метаданные
    metadata = {
        "category": category,
        "filename": filepath.name,
    }

    # Для runs/ — извлекаем клиента и дату
    parts = filepath.parts
    if "runs" in parts:
        try:
            run_idx = list(parts).index("runs")
            if run_idx + 1 < len(parts):
                metadata["run_dir"] = parts[run_idx + 1]
        except (ValueError, IndexError):
            pass

    # Для knowledge/ — извлекаем dept
    if "knowledge" in parts:
        if filepath.name.startswith("set_"):
            dept = filepath.stem.replace("set_", "")
            metadata["dept"] = dept

    chunks = _chunk_text(f"passage: {text}", str(filepath), metadata)'''

    new_index_block = '''    if len(text.strip()) < 50:
        return 0

    # ── Очистка текста от JSON-шума ──
    cleaned = _clean_text(text)
    if len(cleaned) < 100:
        print(f"[ГАВАНЬ] 🧹 Пропуск {filepath.name} — после очистки < 100 символов")
        return 0

    # ── Определяем тип контента ──
    content_type = _detect_content_type(text, str(filepath))

    # Метаданные
    metadata = {
        "category": category,
        "filename": filepath.name,
        "content_type": content_type,
    }

    # Для runs/ — извлекаем клиента и дату
    parts = filepath.parts
    if "runs" in parts:
        try:
            run_idx = list(parts).index("runs")
            if run_idx + 1 < len(parts):
                metadata["run_dir"] = parts[run_idx + 1]
        except (ValueError, IndexError):
            pass

    # Для knowledge/ — извлекаем dept
    if "knowledge" in parts:
        if filepath.name.startswith("set_"):
            dept = filepath.stem.replace("set_", "")
            metadata["dept"] = dept

    # ── Контекстный prefix для embedding ──
    prefix = _build_passage_prefix(str(filepath), content_type)
    chunks = _chunk_text(f"{prefix}{cleaned}", str(filepath), metadata)'''

    if old_index_block in text:
        text = text.replace(old_index_block, new_index_block)
        print("✅ Патч 3: index_file() — очистка + content_type + prefix")
    else:
        print("⚠  Патч 3: блок index_file не совпал (возможно уже пропатчен)")

    # ═══════════════════════════════════════════════════
    # ПАТЧ 4: Модифицируем search_harbor() — авто-exclude template + дедупликация
    # ═══════════════════════════════════════════════════

    # Добавляем авто-exclude для template и дедупликацию
    old_search_output = '''    # Форматируем результаты
    output = []
    if results and results.get("documents") and results["documents"][0]:
        docs = results["documents"][0]
        metas = results["metadatas"][0] if results.get("metadatas") else [{}] * len(docs)
        distances = results["distances"][0] if results.get("distances") else [0.0] * len(docs)

        for doc, meta, dist in zip(docs, metas, distances):
            score = round(1.0 - dist, 3)  # cosine distance → similarity

            # ── Фильтр 1: порог релевантности ──
            if score < min_score:
                continue

            # ── Фильтр 2: исключить нежелательные категории ──
            cat = meta.get("category", "")
            if exclude_categories and cat in exclude_categories:
                continue

            output.append({
                "text": doc,
                "source": meta.get("source", ""),
                "category": cat,
                "score": score,
                "metadata": meta,
            })

    if not output:
        print(f"[ГАВАНЬ] 🔇 Релевантных данных не обнаружено (порог {min_score:.0%})")

    return output'''

    new_search_output = '''    # Форматируем результаты
    output = []
    source_count = {}  # дедупликация: max 2 чанка с одного файла

    if results and results.get("documents") and results["documents"][0]:
        docs = results["documents"][0]
        metas = results["metadatas"][0] if results.get("metadatas") else [{}] * len(docs)
        distances = results["distances"][0] if results.get("distances") else [0.0] * len(docs)

        for doc, meta, dist in zip(docs, metas, distances):
            score = round(1.0 - dist, 3)  # cosine distance → similarity

            # ── Фильтр 1: порог релевантности ──
            if score < min_score:
                continue

            # ── Фильтр 2: исключить нежелательные категории ──
            cat = meta.get("category", "")
            if exclude_categories and cat in exclude_categories:
                continue

            # ── Фильтр 3: понижаем template если запрос не мета ──
            ct = meta.get("content_type", "")
            if ct == "template" and not exclude_templates_override:
                continue

            # ── Фильтр 4: дедупликация по source ──
            src = meta.get("source", "")
            source_count[src] = source_count.get(src, 0) + 1
            if source_count[src] > 2:
                continue

            output.append({
                "text": doc,
                "source": src,
                "category": cat,
                "content_type": ct,
                "score": score,
                "metadata": meta,
            })

    if not output:
        print(f"[ГАВАНЬ] 🔇 Релевантных данных не обнаружено (порог {min_score:.0%})")

    return output'''

    if old_search_output in text:
        text = text.replace(old_search_output, new_search_output)
        print("✅ Патч 4: search_harbor() — авто-exclude template + дедупликация")
    else:
        print("⚠  Патч 4: блок search_harbor output не совпал")

    # ═══════════════════════════════════════════════════
    # ПАТЧ 5: Добавить exclude_templates_override в сигнатуру search_harbor
    # ═══════════════════════════════════════════════════

    old_sig = '''def search_harbor(
    query: str,
    top_k: int = DEFAULT_TOP_K,
    category: str = None,
    dept: str = None,
    min_score: float = 0.38,
    exclude_categories: list = None,
) -> list[dict]:
    """
    Поиск по Гавани Смыслов.

    Args:
        query: что ищем (текст запроса)
        top_k: сколько результатов
        category: фильтр по категории (set_knowledge, project_results, city_lore, agent_knowledge)
        dept: фильтр по цеху
        min_score: минимальный порог релевантности (0.0–1.0). По умолчанию 0.38.
                   Всё ниже — мусор, не попадает в выдачу.
                   Примечание: paraphrase-multilingual-MiniLM-L12-v2 редко даёт > 0.55
                   на смешанном контенте, поэтому 0.6 отрежет всё.
        exclude_categories: список категорий которые исключить из выдачи.
                   Например: ["project_results"] уберёт архивы клиентских проектов.

    Returns:
        Список результатов: [{"text": "...", "source": "...", "score": 0.85, ...}]
    """'''

    new_sig = '''def search_harbor(
    query: str,
    top_k: int = DEFAULT_TOP_K,
    category: str = None,
    dept: str = None,
    min_score: float = 0.40,
    exclude_categories: list = None,
    exclude_templates_override: bool = False,
) -> list[dict]:
    """
    Поиск по Гавани Смыслов.

    Args:
        query: что ищем (текст запроса)
        top_k: сколько результатов
        category: фильтр по категории (set_knowledge, project_results, city_lore, agent_knowledge)
        dept: фильтр по цеху
        min_score: минимальный порог релевантности (0.0–1.0). По умолчанию 0.40.
                   Всё ниже — мусор, не попадает в выдачу.
                   Модель intfloat/multilingual-e5-large редко даёт > 0.55
                   на смешанном контенте.
        exclude_categories: список категорий которые исключить из выдачи.
                   Например: ["project_results"] уберёт архивы клиентских проектов.
        exclude_templates_override: если True — показывать template контент.
                   По умолчанию False — шаблоны/промпты фильтруются из выдачи.

    Returns:
        Список результатов: [{"text": "...", "source": "...", "score": 0.85, ...}]
    """'''

    if old_sig in text:
        text = text.replace(old_sig, new_sig)
        print("✅ Патч 5: search_harbor() — новая сигнатура + порог 0.40")
    else:
        print("⚠  Патч 5: сигнатура search_harbor не совпала")

    # ═══════════════════════════════════════════════════
    # ПАТЧ 6: CLI --search показывает content_type
    # ═══════════════════════════════════════════════════

    old_cli_search = '''        results = search_harbor(query)
        if not results:
            print("🔇 Релевантных данных не обнаружено")
        for r in results:
            print(f"\\n[{r['score']:.0%}] {r['category']}")
            print(f"  {r['text'][:200]}")
            print(f"  📄 {r['source']}")'''

    new_cli_search = '''        results = search_harbor(query)
        if not results:
            print("🔇 Релевантных данных не обнаружено")
        for r in results:
            ct = r.get('content_type', '?')
            print(f"\\n[{r['score']:.0%}] {r['category']} ({ct})")
            print(f"  {r['text'][:200]}")
            print(f"  📄 {r['source']}")'''

    if old_cli_search in text:
        text = text.replace(old_cli_search, new_cli_search)
        print("✅ Патч 6: CLI --search показывает content_type")
    else:
        print("⚠  Патч 6: CLI блок не совпал")

    # ═══════════════════════════════════════════════════
    # ПАТЧ 7: format_harbor_results — показывает content_type
    # ═══════════════════════════════════════════════════

    old_format_entry = '''        entry = f"  {i}. [{category}] (релевантность {score:.0%}) {text}"'''
    new_format_entry = '''        ct = r.get("content_type", "")
        ct_label = f" [{ct}]" if ct else ""
        entry = f"  {i}. [{category}]{ct_label} (релевантность {score:.0%}) {text}"'''

    if old_format_entry in text:
        text = text.replace(old_format_entry, new_format_entry)
        print("✅ Патч 7: format_harbor_results — content_type в выдаче")
    else:
        print("⚠  Патч 7: format entry не совпал")

    # ═══════════════════════════════════════════════════
    # ЗАПИСЬ
    # ═══════════════════════════════════════════════════

    # Бэкап
    shutil.copy2(TARGET, BACKUP)
    print(f"\n💾 Бэкап: {BACKUP}")

    TARGET.write_text(text, encoding="utf-8")
    print(f"✅ Записано: {TARGET}")
    print(f"\n🔄 Теперь запусти: python -m studio.harbor_of_meanings --reindex")
    print(f"   И тестируй:    python -m studio.harbor_of_meanings --search \"история про смелость для ребёнка\"")

    return True


if __name__ == "__main__":
    print("=" * 60)
    print("🔧 ПАТЧ: Умная фильтрация Гавани Смыслов v2")
    print("=" * 60)
    print()
    patch()
