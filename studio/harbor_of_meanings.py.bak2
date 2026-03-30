"""
⚓ ГАВАНЬ СМЫСЛОВ — Внутренняя мудрость Студии (RAG)

Маяк смотрит наружу (web_search).
Гавань смотрит внутрь (vector_search по проектам, знаниям, архивам).

Принцип тот же: Локация = Инструмент.
Агент приходит на прогулке → search_harbor() → «Найденный Смысл» → sensory_memory.
При работе → Рюкзак Знаний подхватывает записи с тегом «найденный_смысл».

Источники индексации:
  1. runs/ — результаты проектов (*.md файлы)
  2. knowledge/ — базы знаний SET (set_*.md)
  3. modules/*/forge/knowledge/ — базы знаний агентов
  4. sensory с тегом «чистый_смысл» — записи с Маяка (web_search)
  5. GRONDHEIM_CITY/ — концепции, документы, лор

ChromaDB хранится локально: studio/harbor_db/
Пересборка индекса: python -m studio.harbor_of_meanings --reindex
"""

import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Optional

# ═══════════════════════════════════════════════════════
# КОНФИГ
# ═══════════════════════════════════════════════════════

HARBOR_DB_PATH = Path("studio/harbor_db")
HARBOR_COLLECTION = "grondheim_knowledge_v2"

# Источники для индексации
INDEX_SOURCES = {
    "knowledge":    Path("knowledge"),
    "runs":         Path("runs"),
    "city_docs":    Path("GRONDHEIM_CITY"),
}

# Расширения для индексации
INDEX_EXTENSIONS = {".md", ".txt", ".json"}

# Размер чанка (символов)
CHUNK_SIZE = 1500
CHUNK_OVERLAP = 200

# Сколько результатов возвращать
DEFAULT_TOP_K = 5

# ═══════════════════════════════════════════════════════
# ИНИЦИАЛИЗАЦИЯ ChromaDB
# ═══════════════════════════════════════════════════════

# ═══ МУЛЬТИЯЗЫЧНЫЕ EMBEDDINGS ═══
_embedding_fn = None
_embedding_type = "default"

def _get_embedding_function():
    global _embedding_fn, _embedding_type
    if _embedding_fn is not None:
        return _embedding_fn
    try:
        from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
        _embedding_fn = SentenceTransformerEmbeddingFunction(
            model_name="intfloat/multilingual-e5-large"
        )
        _embedding_type = "multilingual"
        print("[ГАВАНЬ] 🌍 Embedding: paraphrase-multilingual-MiniLM-L12-v2")
        return _embedding_fn
    except Exception as e:
        print(f"[ГАВАНЬ] ⚠ sentence-transformers недоступен: {e}")
        _embedding_type = "default"
        _embedding_fn = None
        return None

_client = None
_collection = None


def _get_collection():
    """Ленивая инициализация ChromaDB."""
    global _client, _collection

    if _collection is not None:
        return _collection

    try:
        import chromadb
        HARBOR_DB_PATH.mkdir(parents=True, exist_ok=True)
        _client = chromadb.PersistentClient(path=str(HARBOR_DB_PATH))
        ef = _get_embedding_function()
        if ef:
            _collection = _client.get_or_create_collection(
                name=HARBOR_COLLECTION,
                metadata={"hnsw:space": "cosine"},
                embedding_function=ef,
            )
        else:
            _collection = _client.get_or_create_collection(
                name=HARBOR_COLLECTION,
                metadata={"hnsw:space": "cosine"},
            )
        count = _collection.count()
        print(f"[ГАВАНЬ] ⚓ ChromaDB подключена: {count} документов в индексе")
        return _collection
    except ImportError:
        print("[ГАВАНЬ] ⚠ ChromaDB не установлена: pip install chromadb --break-system-packages")
        return None
    except Exception as e:
        print(f"[ГАВАНЬ] ❌ Ошибка инициализации: {e}")
        return None


# ═══════════════════════════════════════════════════════
# ЧАНКИРОВАНИЕ
# ═══════════════════════════════════════════════════════

def _chunk_text(text: str, source_path: str, metadata: dict = None) -> list[dict]:
    """Разбивает текст на чанки с метаданными."""
    chunks = []
    text = text.strip()
    if not text:
        return chunks

    # Разбиваем по параграфам сначала
    paragraphs = text.split("\n\n")
    current_chunk = ""

    for para in paragraphs:
        if len(current_chunk) + len(para) + 2 > CHUNK_SIZE:
            if current_chunk.strip():
                chunk_id = hashlib.md5(
                    f"{source_path}:{len(chunks)}:{current_chunk[:50]}".encode()
                ).hexdigest()

                chunk_meta = {
                    "source": source_path,
                    "chunk_index": len(chunks),
                    "indexed_at": datetime.now().isoformat(),
                }
                if metadata:
                    chunk_meta.update(metadata)

                chunks.append({
                    "id": chunk_id,
                    "text": current_chunk.strip(),
                    "metadata": chunk_meta,
                })

            # Overlap: берём последние N символов
            if len(current_chunk) > CHUNK_OVERLAP:
                current_chunk = current_chunk[-CHUNK_OVERLAP:] + "\n\n" + para
            else:
                current_chunk = para
        else:
            current_chunk += "\n\n" + para if current_chunk else para

    # Последний чанк
    if current_chunk.strip():
        chunk_id = hashlib.md5(
            f"{source_path}:{len(chunks)}:{current_chunk[:50]}".encode()
        ).hexdigest()
        chunk_meta = {
            "source": source_path,
            "chunk_index": len(chunks),
            "indexed_at": datetime.now().isoformat(),
        }
        if metadata:
            chunk_meta.update(metadata)

        chunks.append({
            "id": chunk_id,
            "text": current_chunk.strip(),
            "metadata": chunk_meta,
        })

    return chunks


# ═══════════════════════════════════════════════════════
# ИНДЕКСАЦИЯ
# ═══════════════════════════════════════════════════════

def index_file(filepath: Path, category: str = "general") -> int:
    """Индексирует один файл в ChromaDB. Возвращает количество чанков."""
    collection = _get_collection()
    if not collection:
        return 0

    if not filepath.exists():
        return 0

    try:
        text = filepath.read_text(encoding="utf-8")
    except Exception as e:
        print(f"[ГАВАНЬ] ⚠ Не прочитать {filepath}: {e}")
        return 0

    if len(text.strip()) < 50:
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

    chunks = _chunk_text(f"passage: {text}", str(filepath), metadata)
    if not chunks:
        return 0

    # Upsert в ChromaDB
    try:
        collection.upsert(
            ids=[c["id"] for c in chunks],
            documents=[c["text"] for c in chunks],
            metadatas=[c["metadata"] for c in chunks],
        )
        return len(chunks)
    except Exception as e:
        print(f"[ГАВАНЬ] ❌ Ошибка индексации {filepath}: {e}")
        return 0


def index_directory(dirpath: Path, category: str = "general",
                    extensions: set = None, recursive: bool = True) -> int:
    """Индексирует все файлы в директории."""
    extensions = extensions or INDEX_EXTENSIONS
    total = 0

    if not dirpath.exists():
        return 0

    glob_fn = dirpath.rglob if recursive else dirpath.glob
    for ext in extensions:
        for filepath in sorted(glob_fn(f"*{ext}")):
            if filepath.is_file():
                n = index_file(filepath, category)
                if n > 0:
                    total += n

    return total


def index_agent_knowledge() -> int:
    """Индексирует knowledge/ из forge/ каждого агента."""
    total = 0
    modules_dir = Path("studio/modules")
    if not modules_dir.exists():
        return 0

    for dept_dir in sorted(modules_dir.iterdir()):
        if not dept_dir.is_dir():
            continue
        for agent_dir in sorted(dept_dir.iterdir()):
            if not agent_dir.is_dir() or not agent_dir.name.startswith("A"):
                continue
            for knowledge_dir in [
                agent_dir / "forge" / "knowledge",
                agent_dir / "knowledge",
            ]:
                if knowledge_dir.exists():
                    n = index_directory(
                        knowledge_dir,
                        category=f"agent_knowledge:{dept_dir.name}:{agent_dir.name}",
                        recursive=False,
                    )
                    total += n

    return total


def index_sensory_lighthouse() -> int:
    """Индексирует записи «Чистый Смысл» с Маяка из sensory_memory."""
    total = 0
    collection = _get_collection()
    if not collection:
        return 0

    modules_dir = Path("studio/modules")
    if not modules_dir.exists():
        return 0

    for dept_dir in sorted(modules_dir.iterdir()):
        if not dept_dir.is_dir():
            continue
        for agent_dir in sorted(dept_dir.iterdir()):
            sensory_path = agent_dir / "sensory" / "sensory_memory.json"
            if not sensory_path.exists():
                continue

            try:
                data = json.loads(sensory_path.read_text(encoding="utf-8"))
            except Exception:
                continue

            entries = data.get("entries", [])
            for entry in entries:
                tags = entry.get("tags", [])
                if "чистый_смысл" not in tags and "маяк" not in tags:
                    continue

                feeling = entry.get("feeling", "") or entry.get("content", "")
                if not feeling or len(feeling) < 20:
                    continue

                chunk_id = hashlib.md5(
                    f"sensory:{agent_dir.name}:{entry.get('date', '')}:{feeling[:30]}".encode()
                ).hexdigest()

                try:
                    collection.upsert(
                        ids=[chunk_id],
                        documents=[feeling],
                        metadatas=[{
                            "source": str(sensory_path),
                            "category": "lighthouse_knowledge",
                            "agent": agent_dir.name,
                            "dept": dept_dir.name,
                            "date": entry.get("date", ""),
                        }],
                    )
                    total += 1
                except Exception:
                    pass

    return total


def reindex_all() -> dict:
    """Полная пересборка индекса Гавани Смыслов."""
    collection = _get_collection()
    if not collection:
        return {"error": "ChromaDB не подключена"}

    print("[ГАВАНЬ] 🔄 Полная пересборка индекса...")

    stats = {}

    # 1. Knowledge (SET промпты)
    n = index_directory(INDEX_SOURCES["knowledge"], category="set_knowledge")
    stats["knowledge"] = n
    print(f"[ГАВАНЬ]   knowledge/: {n} чанков")

    # 2. Runs (результаты проектов)
    n = index_directory(INDEX_SOURCES["runs"], category="project_results")
    stats["runs"] = n
    print(f"[ГАВАНЬ]   runs/: {n} чанков")

    # 3. City docs (концепции, лор)
    n = index_directory(INDEX_SOURCES["city_docs"], category="city_lore")
    stats["city_docs"] = n
    print(f"[ГАВАНЬ]   GRONDHEIM_CITY/: {n} чанков")

    # 4. Agent knowledge bases
    n = index_agent_knowledge()
    stats["agent_knowledge"] = n
    print(f"[ГАВАНЬ]   agent knowledge/: {n} чанков")

    # 5. Lighthouse sensory (Чистый Смысл)
    n = index_sensory_lighthouse()
    stats["lighthouse"] = n
    print(f"[ГАВАНЬ]   Маяк (sensory): {n} записей")

    total = sum(stats.values())
    stats["total"] = total
    stats["collection_count"] = collection.count()
    print(f"[ГАВАНЬ] ✅ Индекс готов: {collection.count()} документов")

    return stats


# ═══════════════════════════════════════════════════════
# ПОИСК (главная функция для агентов)
# ═══════════════════════════════════════════════════════

def search_harbor(
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
    """
    collection = _get_collection()
    if not collection:
        return []

    if collection.count() == 0:
        print("[ГАВАНЬ] ⚠ Индекс пуст. Запусти reindex: python -m studio.harbor_of_meanings --reindex")
        return []

    # Фильтры
    where = {}
    if category:
        where["category"] = category
    if dept:
        where["dept"] = dept

    try:
        results = collection.query(
            query_texts=[f"query: {query}"],
            n_results=min(top_k, collection.count()),
            where=where if where else None,
        )
    except Exception as e:
        print(f"[ГАВАНЬ] ❌ Ошибка поиска: {e}")
        return []

    # Форматируем результаты
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

    return output


def format_harbor_results(results: list[dict], max_chars: int = 2000) -> str:
    """Форматирует результаты поиска для инжекта в контекст агента."""
    if not results:
        return ""

    lines = ["=== ⚓ НАЙДЕННЫЕ СМЫСЛЫ (из Гавани) ==="]

    total_chars = 0
    for i, r in enumerate(results, 1):
        text = r["text"][:400]
        source = r.get("source", "")
        score = r.get("score", 0)
        category = r.get("category", "")

        entry = f"  {i}. [{category}] (релевантность {score:.0%}) {text}"
        if source:
            # Показываем только имя файла
            source_name = Path(source).name
            entry += f"\n     📄 {source_name}"

        if total_chars + len(entry) > max_chars:
            lines.append(f"  ... ещё {len(results) - i + 1} результатов")
            break

        lines.append(entry)
        total_chars += len(entry)

    lines.append("Используй эти данные если они релевантны текущей задаче.")
    lines.append("=== КОНЕЦ НАЙДЕННЫХ СМЫСЛОВ ===")
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════
# ИНТЕГРАЦИЯ С CITY_WALKER (при визите на Гавань)
# ═══════════════════════════════════════════════════════

async def harbor_visit(
    agent_name: str,
    agent_profession: str,
    agent_dna: dict,
    system_prompt: str = "",
    temperature: float = 0.7,
) -> str:
    """
    Агент пришёл в Гавань Смыслов на прогулке.
    Аналог Маяка — но ищет внутри, а не снаружи.

    1. Генерирует поисковый запрос исходя из того кто он
    2. Ищет в ChromaDB
    3. Рефлексирует над найденным
    4. Возвращает «Найденный Смысл»
    """
    import asyncio
    from studio.llm import chat

    # Шаг 1: Агент формулирует что ищет
    query_prompt = (
        f"Ты — {agent_name}, {agent_profession}.\n"
        f"Ты стоишь в Гавани Смыслов — архиве всех проектов и знаний Студии.\n"
        f"Тебе нужно найти что-то полезное для своей работы.\n\n"
        f"Сформулируй ОДИН поисковый запрос (2-5 слов) — "
        f"что тебе сейчас нужно знать или вспомнить?\n"
        f"Отвечай ТОЛЬКО запрос, без объяснений."
    )

    try:
        loop = asyncio.get_event_loop()
        query = await loop.run_in_executor(
            None,
            lambda: chat(system_prompt or f"Ты {agent_name}.", query_prompt, "", temperature=temperature)
        )
        query = query.strip().strip('"').strip("'")[:100]
        print(f"[ГАВАНЬ] 🔍 {agent_name} ищет: «{query}»")
    except Exception as e:
        print(f"[ГАВАНЬ] ❌ {agent_name}: не смог сформулировать запрос — {e}")
        return "Гавань молчала сегодня — мысли путались."

    # Шаг 2: Поиск
    results = search_harbor(query, top_k=3)
    if not results:
        print(f"[ГАВАНЬ] 📭 {agent_name}: ничего не нашёл по «{query}»")
        return "В Гавани тихо. Архивы не откликнулись на мой запрос."

    # Шаг 3: Рефлексия
    found_text = "\n\n".join([
        f"[{r['category']}] {r['text'][:300]}"
        for r in results
    ])

    reflect_prompt = (
        f"Ты — {agent_name}, {agent_profession}.\n"
        f"Ты искал в Гавани Смыслов: «{query}»\n\n"
        f"Вот что нашлось:\n{found_text}\n\n"
        f"Запиши ВЫЖИМКУ — что ты понял и как это пригодится в работе.\n"
        f"2-3 предложения. Формат:\n"
        f"НАЙДЕННЫЙ СМЫСЛ: <что узнал и зачем это нужно>"
    )

    try:
        reflection = await loop.run_in_executor(
            None,
            lambda: chat(system_prompt or f"Ты {agent_name}.", reflect_prompt, "", temperature=temperature)
        )

        import re
        match = re.search(r'НАЙДЕННЫЙ СМЫСЛ:\s*(.+)', reflection, re.DOTALL)
        if match:
            found_meaning = match.group(1).strip()[:500]
        else:
            found_meaning = reflection[:500]

        print(f"[ГАВАНЬ] ✨ {agent_name} нашёл: {found_meaning[:120]}...")
        return found_meaning

    except Exception as e:
        print(f"[ГАВАНЬ] ❌ {agent_name}: ошибка рефлексии — {e}")
        return "Нашёл кое-что в архивах, но не успел осмыслить."


# ═══════════════════════════════════════════════════════
# ИНТЕГРАЦИЯ С ПАЙПЛАЙНОМ (Рюкзак Знаний v2)
# ═══════════════════════════════════════════════════════

def get_harbor_knowledge(worker_id: str, dept: str, task_context: str = "") -> str:
    """
    Рюкзак Знаний v2: при работе агента — ищем в Гавани
    релевантные данные для текущей задачи.

    Вызывается из pipeline.py → build_agent_context().
    """
    collection = _get_collection()
    if not collection or collection.count() == 0:
        return ""

    # Формируем запрос из контекста задачи
    query = task_context[:200] if task_context else f"знания для {worker_id} {dept}"

    results = search_harbor(query, top_k=3)
    if not results:
        return ""

    formatted = format_harbor_results(results, max_chars=1500)
    if formatted:
        print(f"[ГАВАНЬ→РЮКЗАК] ⚓ {worker_id} получил {len(results)} смыслов из Гавани")

    return formatted


# ═══════════════════════════════════════════════════════
# ИНКРЕМЕНТАЛЬНАЯ ИНДЕКСАЦИЯ
# ═══════════════════════════════════════════════════════

_LAST_INDEX_FILE = HARBOR_DB_PATH / "_last_index.json"


def _load_last_index() -> dict:
    if _LAST_INDEX_FILE.exists():
        try:
            return json.loads(_LAST_INDEX_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"files": {}, "last_run": ""}


def _save_last_index(state: dict):
    _LAST_INDEX_FILE.parent.mkdir(parents=True, exist_ok=True)
    _LAST_INDEX_FILE.write_text(
        json.dumps(state, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


def index_new_files() -> int:
    """Инкрементальная индексация — только новые/изменённые файлы."""
    state = _load_last_index()
    known_files = state.get("files", {})
    total_new = 0

    for source_name, source_path in INDEX_SOURCES.items():
        if not source_path.exists():
            continue
        for ext in INDEX_EXTENSIONS:
            for filepath in sorted(source_path.rglob(f"*{ext}")):
                if not filepath.is_file():
                    continue
                key = str(filepath)
                mtime = filepath.stat().st_mtime

                if key in known_files and known_files[key] >= mtime:
                    continue  # Не изменился

                n = index_file(filepath, category=source_name)
                if n > 0:
                    known_files[key] = mtime
                    total_new += n

    # Agent knowledge
    modules_dir = Path("studio/modules")
    if modules_dir.exists():
        for dept_dir in sorted(modules_dir.iterdir()):
            if not dept_dir.is_dir():
                continue
            for agent_dir in sorted(dept_dir.iterdir()):
                for kdir in [agent_dir / "forge" / "knowledge", agent_dir / "knowledge"]:
                    if not kdir.exists():
                        continue
                    for ext in INDEX_EXTENSIONS:
                        for filepath in sorted(kdir.glob(f"*{ext}")):
                            key = str(filepath)
                            mtime = filepath.stat().st_mtime
                            if key in known_files and known_files[key] >= mtime:
                                continue
                            n = index_file(filepath, f"agent_knowledge:{dept_dir.name}:{agent_dir.name}")
                            if n > 0:
                                known_files[key] = mtime
                                total_new += n

    state["files"] = known_files
    state["last_run"] = datetime.now().isoformat()
    _save_last_index(state)

    if total_new:
        print(f"[ГАВАНЬ] 📥 Проиндексировано {total_new} новых чанков")
    return total_new


# ═══════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys

    if "--reindex" in sys.argv:
        stats = reindex_all()
        print(f"\n📊 Итого: {json.dumps(stats, ensure_ascii=False, indent=2)}")

    elif "--update" in sys.argv:
        n = index_new_files()
        print(f"\n📥 Новых чанков: {n}")

    elif "--search" in sys.argv:
        query = " ".join(sys.argv[sys.argv.index("--search") + 1:])
        if not query:
            print("Использование: --search <запрос>")
            sys.exit(1)
        results = search_harbor(query)
        if not results:
            print("🔇 Релевантных данных не обнаружено")
        for r in results:
            print(f"\n[{r['score']:.0%}] {r['category']}")
            print(f"  {r['text'][:200]}")
            print(f"  📄 {r['source']}")

    elif "--stats" in sys.argv:
        collection = _get_collection()
        if collection:
            print(f"Документов в индексе: {collection.count()}")
        state = _load_last_index()
        print(f"Файлов отслеживается: {len(state.get('files', {}))}")
        print(f"Последний индекс: {state.get('last_run', 'никогда')}")

    else:
        print("⚓ Гавань Смыслов — RAG-модуль Студии")
        print()
        print("Команды:")
        print("  --reindex         Полная пересборка индекса")
        print("  --update          Индексировать только новые файлы")
        print("  --search <текст>  Поиск по Гавани")
        print("  --stats           Статистика индекса")
