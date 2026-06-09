"""
🧠 ИНСТРУМЕНТЫ ПАМЯТИ ГОРОДА — Оле (004_OLE)

Не библиотека. Не каталог. Память.

Четыре операции над памятью города:
  remember()  — принять в память
  remind()    — извлечь в нужный момент
  release()   — отпустить (не удалить)
  decline()   — отказать во входе

Структура memory_entry:
  Центр — loss_if_forgotten.
  Если его невозможно заполнить осмысленно — запись не нужна.

Хранилище: studio/memory/city_memory.jsonl (append-only)
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

# ── Гавань Смыслов (RAG) ─────────────────────────────
# Память города индексируется в Гавань — один океан знаний.
try:
    from studio.harbor_of_meanings import (
        _get_collection as _harbor_collection,
        search_harbor as _harbor_search,
    )
    _HARBOR_ENABLED = True
except ImportError:
    _HARBOR_ENABLED = False
    def _harbor_collection(): return None
    def _harbor_search(query, **kwargs): return []

# ═══════════════════════════════════════════════════════
# КОНФИГ
# ═══════════════════════════════════════════════════════

MEMORY_DIR  = Path("studio/memory")
MEMORY_FILE = MEMORY_DIR / "city_memory.jsonl"

# Куда может положить память
STORAGE_OPTIONS = {
    "library":    "Библиотека — чистое, зрелое, эталонное",
    "harbor":     "Гавань Смыслов — сырое, черновое, рискованное",
    "chronicles": "Хроники — последовательность событий",
    "reference":  "Эталоны — на что стоит равняться",
}

# Типы памяти (структурная категория)
MEMORY_TYPES = {
    "lesson":      "Урок — что не повторять",
    "tradition":   "Традиция — что держит город вместе",
    "warning":     "Предупреждение — сигнал опасности",
    "inspiration": "Вдохновение — источник энергии",
    "identity":    "Идентичность — часть того кто мы есть",
}

# Статусы записи
STATUS_ACTIVE   = "active"    # живёт в памяти
STATUS_ARCHIVED = "archived"  # глубокий архив, но не стёрто
STATUS_RELEASED = "released"  # отпущено — с причиной и датой


# ═══════════════════════════════════════════════════════
# СТРУКТУРА ЗАПИСИ ПАМЯТИ
# ═══════════════════════════════════════════════════════

def _new_entry(
    title:             str,
    event:             str,
    significance:      str,
    loss_if_forgotten: str,
    memory_type:       str,
    storage:           str,
    source:            str = "",
) -> dict:
    """
    Создаёт структуру memory_entry.

    loss_if_forgotten — ГЛАВНОЕ ПОЛЕ.
    Если его невозможно заполнить осмысленно — запись не нужна.
    """
    return {
        "id":                str(uuid.uuid4())[:12],
        "title":             title,
        "event":             event,
        "significance":      significance,
        "loss_if_forgotten": loss_if_forgotten,
        "memory_type":       memory_type,
        "storage":           storage,
        "status":            STATUS_ACTIVE,
        "source":            source,
        "created_by":        "004_OLE",
        "created_at":        datetime.now().isoformat(),
        "released_at":       None,
        "release_reason":    None,
    }


# ═══════════════════════════════════════════════════════
# ХРАНИЛИЩЕ (append-only JSONL)
# ═══════════════════════════════════════════════════════

def _load_all() -> list[dict]:
    """Загружает все записи из city_memory.jsonl."""
    if not MEMORY_FILE.exists():
        return []
    entries = []
    for line in MEMORY_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                entries.append(json.loads(line))
            except Exception:
                pass
    return entries


def _append(entry: dict):
    """Дописывает запись в конец файла (append-only)."""
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    with open(MEMORY_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _patch(entry_id: str, updates: dict):
    """
    Патч-запись в конец файла (не перезаписываем старые строки).
    Append-only: история решений сохраняется.
    """
    patch = {
        "_patch":     True,
        "_target_id": entry_id,
        "_patched_at": datetime.now().isoformat(),
        **updates,
    }
    _append(patch)


def _resolve(entries: list[dict]) -> list[dict]:
    """
    Применяет патчи к записям — возвращает актуальное состояние каждой.
    Последний патч побеждает.
    """
    base: dict[str, dict] = {}
    for e in entries:
        if e.get("_patch"):
            tid = e.get("_target_id")
            if tid and tid in base:
                base[tid].update({
                    k: v for k, v in e.items()
                    if not k.startswith("_")
                })
        else:
            base[e["id"]] = dict(e)
    return list(base.values())


# ═══════════════════════════════════════════════════════
# ГАВАНЬ — индексация памяти
# ═══════════════════════════════════════════════════════

def _harbor_index(entry: dict) -> bool:
    """
    Индексирует запись памяти в Гавань Смыслов.

    Текст для embedding — title + loss_if_forgotten + significance.
    loss_if_forgotten главное: именно по нему Гавань найдёт смысл.

    Метаданные сохраняют entry_id — чтобы remind() мог восстановить
    полную запись из JSONL по результатам семантического поиска.
    """
    if not _HARBOR_ENABLED:
        return False

    collection = _harbor_collection()
    if not collection:
        return False

    try:
        import hashlib
        # Текст для семантического поиска
        text = (
            f"passage: память города — {entry.get('memory_type','?')} · "
            f"{entry['title']}\n"
            f"Потеря при забвении: {entry['loss_if_forgotten']}\n"
            f"Значимость: {entry.get('significance','')}"
        )

        doc_id = hashlib.md5(
            f"city_memory:{entry['id']}".encode()
        ).hexdigest()

        collection.upsert(
            ids=[doc_id],
            documents=[text],
            metadatas=[{
                "source":      "studio/memory/city_memory.jsonl",
                "category":    "city_memory",
                "content_type": "narrative",
                "entry_id":    entry["id"],
                "title":       entry["title"],
                "memory_type": entry.get("memory_type", ""),
                "storage":     entry.get("storage", ""),
                "created_by":  "004_OLE",
            }],
        )
        print(f"[ОЛЕ→ГАВАНЬ] ⚓ '{entry['title']}' проиндексирована")
        return True
    except Exception as e:
        print(f"[ОЛЕ→ГАВАНЬ] ⚠️  Ошибка индексации: {e}")
        return False


# ═══════════════════════════════════════════════════════
# ЧЕТЫРЕ ОПЕРАЦИИ ОЛЕ
# ═══════════════════════════════════════════════════════

def remember(
    title:             str,
    event:             str,
    significance:      str,
    loss_if_forgotten: str,
    memory_type:       str,
    storage:           str,
    source:            str = "",
) -> Optional[dict]:
    """
    Принять событие в память города.

    Начинается не с сохранения — а с вопроса:
    "Что город потеряет, если забудет это?"

    Если loss_if_forgotten пустой или натянутый — не сохраняем.
    Вернёт None если запись не прошла проверку.
    """
    # Проверка главного поля
    if not loss_if_forgotten or len(loss_if_forgotten.strip()) < 10:
        print(f"[ОЛЕ] remember(): отклонено — loss_if_forgotten не заполнено осмысленно.")
        print(f"[ОЛЕ] Если невозможно ответить что город потеряет — запись не нужна.")
        return None

    if memory_type not in MEMORY_TYPES:
        print(f"[ОЛЕ] remember(): неизвестный memory_type '{memory_type}'. "
              f"Допустимые: {list(MEMORY_TYPES.keys())}")
        return None

    if storage not in STORAGE_OPTIONS:
        print(f"[ОЛЕ] remember(): неизвестный storage '{storage}'. "
              f"Допустимые: {list(STORAGE_OPTIONS.keys())}")
        return None

    entry = _new_entry(
        title=title,
        event=event,
        significance=significance,
        loss_if_forgotten=loss_if_forgotten,
        memory_type=memory_type,
        storage=storage,
        source=source,
    )
    _append(entry)

    # ── Индексируем в Гавань Смыслов ──────────────────
    # Память города — часть единого океана знаний.
    # Поле loss_if_forgotten — главное для семантического поиска.
    _harbor_index(entry)

    print(f"[ОЛЕ] ✅ remember(): '{title}' → {storage} [{memory_type}]")
    print(f"[ОЛЕ]    Потеря при забвении: {loss_if_forgotten[:80]}...")
    return entry


def remind(
    query: str,
    memory_type: str = None,
    storage: str = None,
    top_k: int = 3,
) -> list[dict]:
    """
    Извлечь память в нужный момент.

    Ищет в двух источниках:
      1. city_memory.jsonl — точные активные записи
      2. Гавань Смыслов   — семантический поиск по смыслу

    Один раз. Спокойно. Без навязывания.
    """
    results = []
    seen_ids = set()

    # ── 1. Поиск в city_memory.jsonl ──────────────────
    entries = _resolve(_load_all())
    active = [e for e in entries if e.get("status") == STATUS_ACTIVE
              and not e.get("_declined")]

    q = query.lower()
    for e in active:
        if memory_type and e.get("memory_type") != memory_type:
            continue
        if storage and e.get("storage") != storage:
            continue

        haystack = " ".join(filter(None, [
            e.get("title", ""),
            e.get("event", ""),
            e.get("significance", ""),
            e.get("loss_if_forgotten", ""),
        ])).lower()

        if q in haystack:
            results.append(e)
            seen_ids.add(e["id"])

        if len(results) >= top_k:
            break

    # ── 2. Семантический поиск в Гавани ───────────────
    # Дополняем если нашли меньше top_k
    if _HARBOR_ENABLED and len(results) < top_k:
        try:
            harbor_hits = _harbor_search(
                query=query,
                top_k=top_k * 2,
                category="city_memory",
            )
            for hit in harbor_hits:
                if len(results) >= top_k:
                    break
                # Восстанавливаем entry из метаданных Гавани
                meta = hit.get("metadata", {})
                entry_id = meta.get("entry_id", "")
                if entry_id and entry_id not in seen_ids:
                    # Ищем полную запись в JSONL
                    full = next(
                        (e for e in active if e.get("id") == entry_id),
                        None
                    )
                    if full:
                        results.append(full)
                        seen_ids.add(entry_id)
                    else:
                        # Гавань нашла — но JSONL уже не содержит (released?)
                        # Показываем как фрагмент из Гавани
                        results.append({
                            "id":                entry_id,
                            "title":             meta.get("title", hit["text"][:60]),
                            "memory_type":       meta.get("memory_type", "?"),
                            "storage":           meta.get("storage", "harbor"),
                            "status":            "harbor_fragment",
                            "loss_if_forgotten": hit["text"][:300],
                            "event":             "",
                        })
                        seen_ids.add(entry_id)
        except Exception as e:
            print(f"[ОЛЕ] ⚠️  Гавань недоступна: {e}")

    if results:
        print(f"[ОЛЕ] remind(): найдено {len(results)} записей по '{query}'")
        for r in results:
            print(f"[ОЛЕ]   • {r['title']} [{r.get('memory_type','?')}] → {r.get('storage','?')}")
    else:
        print(f"[ОЛЕ] remind(): по '{query}' ничего не нашлось.")

    return results


def release(
    entry_id: str,
    reason: str,
) -> bool:
    """
    Отпустить запись памяти.

    Не удаление. Отпущенное — не уничтоженное.
    Город может однажды спросить почему перестали хранить —
    и Оле сможет ответить.

    reason обязателен — Оле всегда объясняет почему отпускает.
    """
    if not reason or len(reason.strip()) < 5:
        print("[ОЛЕ] release(): причина обязательна. Оле всегда объясняет почему отпускает.")
        return False

    entries = _resolve(_load_all())
    target = next((e for e in entries if e["id"] == entry_id), None)

    if not target:
        print(f"[ОЛЕ] release(): запись '{entry_id}' не найдена.")
        return False

    if target.get("status") == STATUS_RELEASED:
        print(f"[ОЛЕ] release(): '{target['title']}' уже отпущена.")
        return False

    _patch(entry_id, {
        "status":         STATUS_RELEASED,
        "released_at":    datetime.now().isoformat(),
        "release_reason": reason,
    })

    print(f"[ОЛЕ] 🕊 release(): '{target['title']}' отпущена.")
    print(f"[ОЛЕ]    Причина: {reason}")
    print(f"[ОЛЕ]    Запись сохранена в архиве — история решения не стёрта.")
    return True


def decline(
    title:  str,
    reason: str,
    source: str = "",
) -> dict:
    """
    Отказать событию во входе в память города.

    "Нет. Это не войдёт в память города."
    Финальное слово — Оле. Но с объяснением — всегда.

    Отказ тоже записывается — как факт решения.
    """
    if not reason or len(reason.strip()) < 5:
        print("[ОЛЕ] decline(): причина обязательна.")
        return {}

    record = {
        "id":          str(uuid.uuid4())[:12],
        "_declined":   True,
        "title":       title,
        "reason":      reason,
        "source":      source,
        "decided_by":  "004_OLE",
        "decided_at":  datetime.now().isoformat(),
    }
    _append(record)

    print(f"[ОЛЕ] ✗ decline(): '{title}' не войдёт в память города.")
    print(f"[ОЛЕ]   Причина: {reason}")
    return record


# ═══════════════════════════════════════════════════════
# УТИЛИТЫ
# ═══════════════════════════════════════════════════════

def get_active_memories(memory_type: str = None, storage: str = None) -> list[dict]:
    """Все активные записи памяти. Опционально — по типу или хранилищу."""
    entries = _resolve(_load_all())
    result = [e for e in entries if e.get("status") == STATUS_ACTIVE
              and not e.get("_declined")]
    if memory_type:
        result = [e for e in result if e.get("memory_type") == memory_type]
    if storage:
        result = [e for e in result if e.get("storage") == storage]
    return result


def get_declined() -> list[dict]:
    """Все отказы — история решений Оле."""
    entries = _load_all()
    return [e for e in entries if e.get("_declined")]


def get_released() -> list[dict]:
    """Все отпущенные записи — с причинами."""
    entries = _resolve(_load_all())
    return [e for e in entries if e.get("status") == STATUS_RELEASED]


def memory_stats() -> dict:
    """Статистика памяти города."""
    entries = _resolve(_load_all())
    all_raw = _load_all()

    active   = [e for e in entries if e.get("status") == STATUS_ACTIVE and not e.get("_declined")]
    archived = [e for e in entries if e.get("status") == STATUS_ARCHIVED]
    released = [e for e in entries if e.get("status") == STATUS_RELEASED]
    declined = [e for e in all_raw  if e.get("_declined")]

    by_type    = {}
    by_storage = {}
    for e in active:
        mt = e.get("memory_type", "?")
        st = e.get("storage", "?")
        by_type[mt]    = by_type.get(mt, 0) + 1
        by_storage[st] = by_storage.get(st, 0) + 1

    return {
        "active":   len(active),
        "archived": len(archived),
        "released": len(released),
        "declined": len(declined),
        "by_type":    by_type,
        "by_storage": by_storage,
    }


def format_for_agent(memories: list[dict], max_chars: int = 2000) -> str:
    """
    Форматирует записи памяти для инжекта в контекст агента.
    Используется в remind() → pipeline context.
    """
    if not memories:
        return ""

    lines = ["=== 🧠 ПАМЯТЬ ГОРОДА (от Оле) ==="]
    total = 0

    for m in memories:
        entry = (
            f"\n[{m.get('memory_type','?')}] {m['title']}\n"
            f"  Событие: {m.get('event','')[:200]}\n"
            f"  Потеря при забвении: {m.get('loss_if_forgotten','')[:200]}\n"
        )
        if total + len(entry) > max_chars:
            break
        lines.append(entry)
        total += len(entry)

    lines.append("\nПомни: это не инструкция. Это то, что город уже прошёл.")
    lines.append("=== КОНЕЦ ПАМЯТИ ===")
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys

    if "--stats" in sys.argv:
        stats = memory_stats()
        print(f"\n🧠 Память города — статистика:")
        print(f"  Активных записей : {stats['active']}")
        print(f"  Архивировано     : {stats['archived']}")
        print(f"  Отпущено         : {stats['released']}")
        print(f"  Отказов          : {stats['declined']}")
        if stats["by_type"]:
            print(f"\n  По типу:")
            for k, v in stats["by_type"].items():
                print(f"    {k}: {v}")
        if stats["by_storage"]:
            print(f"\n  По хранилищу:")
            for k, v in stats["by_storage"].items():
                print(f"    {k}: {v}")

    elif "--list" in sys.argv:
        memories = get_active_memories()
        if not memories:
            print("🧠 Память города пуста.")
        else:
            print(f"\n🧠 Активных записей: {len(memories)}\n")
            for m in memories:
                print(f"  [{m['id']}] {m['title']}")
                print(f"    Тип: {m['memory_type']} → {m['storage']}")
                print(f"    Потеря: {m['loss_if_forgotten'][:80]}...")
                print()

    elif "--declined" in sys.argv:
        declined = get_declined()
        if not declined:
            print("🧠 Отказов пока не было.")
        else:
            print(f"\n🧠 Отказов: {len(declined)}\n")
            for d in declined:
                print(f"  ✗ {d['title']}")
                print(f"    Причина: {d['reason']}")
                print(f"    Когда: {d['decided_at'][:10]}")
                print()

    elif "--released" in sys.argv:
        released = get_released()
        if not released:
            print("🧠 Ничего не отпущено.")
        else:
            print(f"\n🧠 Отпущено: {len(released)}\n")
            for r in released:
                print(f"  🕊 {r['title']}")
                print(f"    Причина: {r.get('release_reason','?')}")
                print(f"    Когда: {r.get('released_at','?')[:10]}")
                print()

    else:
        print("🧠 memory_tools.py — инструменты памяти города (Оле)")
        print()
        print("Команды:")
        print("  --stats      Статистика памяти")
        print("  --list       Все активные записи")
        print("  --declined   История отказов")
        print("  --released   Отпущенные записи")
