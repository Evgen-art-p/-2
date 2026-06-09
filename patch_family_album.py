"""
patch_family_album.py — Спринт 43 · Семейный Альбом

Три изменения:

1. grondheim_memory.py → decay_sensory()
   Старая логика: записи с низким весом старше 30 дней УДАЛЯЮТСЯ.
   Новая логика:  записи АРХИВИРУЮТСЯ в {агент}/archive/memories_YYYY_MM.jsonl
                  + один абзац в summary о том что ушло в архив.

2. grondheim_memory.py → format_soul_for_agent() (HOME-режим)
   Добавляем строчку после сборки сенсорной памяти:
   "Если что-то кажется знакомым, но не помнишь — скажи MEMORY_REQUEST: <запрос>
    и Оле поднимет это из глубины."

3. memory_tools.py → dig_archive()
   Новая функция: ищет по архивным файлам агентов.
   Вызывается из residents_manager.py (Оле обрабатывает MEMORY_REQUEST).

Применять из корня проекта:
  python patch_family_album.py

Бэкап создаётся автоматически (.bak_YYYYMMDD_HHMMSS).
"""

import re
import shutil
from datetime import datetime
from pathlib import Path

# ──────────────────────────────────────────────
# КОНФИГ
# ──────────────────────────────────────────────

GRONDHEIM_MEMORY = Path("studio/grondheim_memory.py")
MEMORY_TOOLS     = Path("studio/memory_tools.py")

STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")


# ──────────────────────────────────────────────
# УТИЛИТЫ
# ──────────────────────────────────────────────

def backup(path: Path):
    bak = path.with_suffix(f".bak_{STAMP}")
    shutil.copy2(path, bak)
    print(f"  [bak] {bak.name}")


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write(path: Path, text: str):
    path.write_text(text, encoding="utf-8")


def patch_str(src: str, old: str, new: str, label: str) -> str:
    if old not in src:
        print(f"  [SKIP] {label} — якорь не найден, пропускаю")
        return src
    result = src.replace(old, new, 1)
    print(f"  [OK]   {label}")
    return result


# ══════════════════════════════════════════════
# ПАТЧ 1 — grondheim_memory.py
#           decay_sensory() → архивирует вместо удаления
#           format_soul_for_agent() → строчка про Оле в HOME
# ══════════════════════════════════════════════

DECAY_OLD = '''def decay_sensory(agent_id: str, dept: str = ""):
    """
    Loka-Filter для оперативного слоя.
    Удаляет записи старше SENSORY_DECAY_DAYS с низким emotional_weight.
    Вызывается периодически (cron / при запуске агента).
    """
    agent_dir = _find_agent_dir(agent_id, dept)
    if not agent_dir:
        return

    sensory = load_sensory(agent_id, dept)
    cutoff = datetime.now() - timedelta(days=SENSORY_DECAY_DAYS)

    surviving = []
    decayed_texts = []

    for entry in sensory["entries"]:
        try:
            # Поддержка обоих форматов: grondheim_memory (ts) и city_walker (date)
            raw_ts = entry.get("ts") or entry.get("date", "")
            entry_time = datetime.fromisoformat(raw_ts)
        except (ValueError, KeyError, TypeError):
            surviving.append(entry)
            continue

        if entry_time < cutoff and entry.get("emotional_weight", 0) < 0.5:
            # Уходит — но сохраняем след в summary
            text = entry.get("content") or entry.get("feeling", "")
            decayed_texts.append(text[:60])
        else:
            surviving.append(entry)

    if decayed_texts:
        old_summary = sensory.get("summary", "")
        decay_note = f"[Затухло {len(decayed_texts)} записей]: " + "; ".join(decayed_texts[:5])
        sensory["summary"] = (old_summary + "\\n" + decay_note)[-SUMMARY_MAX_CHARS:]

    sensory["entries"] = surviving
    path = agent_dir / "sensory" / "sensory_memory.json"
    _save_json(path, sensory)'''

DECAY_NEW = '''def _archive_sensory_entries(agent_dir: Path, entries: list[dict]):
    """
    СЕМЕЙНЫЙ АЛЬБОМ · Спринт 43

    Архивирует записи в {агент}/archive/memories_YYYY_MM.jsonl.
    Не удаляет — кладёт глубже. Оле и Финч могут поднять через dig_archive().

    Файл создаётся / дополняется по принципу append-only.
    Имя файла — год+месяц первой записи (или текущий если нет ts).
    """
    import json as _json

    archive_dir = agent_dir / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)

    # Группируем по YYYY_MM
    by_month: dict[str, list] = {}
    now_key = datetime.now().strftime("%Y_%m")
    for entry in entries:
        raw_ts = entry.get("ts") or entry.get("date", "")
        try:
            month_key = datetime.fromisoformat(raw_ts).strftime("%Y_%m")
        except Exception:
            month_key = now_key
        by_month.setdefault(month_key, []).append(entry)

    for month_key, month_entries in by_month.items():
        archive_path = archive_dir / f"memories_{month_key}.jsonl"
        with open(archive_path, "a", encoding="utf-8") as f:
            for e in month_entries:
                f.write(_json.dumps(e, ensure_ascii=False) + "\\n")

    total = sum(len(v) for v in by_month.values())
    print(f"[АЛЬБОМ] 📚 {agent_dir.name}: {total} воспоминаний → archive/")


def decay_sensory(agent_id: str, dept: str = ""):
    """
    Loka-Filter для оперативного слоя.

    СЕМЕЙНЫЙ АЛЬБОМ · Спринт 43:
    Записи старше SENSORY_DECAY_DAYS с низким emotional_weight
    НЕ УДАЛЯЮТСЯ — архивируются в {агент}/archive/memories_YYYY_MM.jsonl.
    Из оперативной памяти уходят, но остаются доступны через dig_archive().

    Вызывается периодически (cron / при запуске агента).
    """
    agent_dir = _find_agent_dir(agent_id, dept)
    if not agent_dir:
        return

    sensory = load_sensory(agent_id, dept)
    cutoff = datetime.now() - timedelta(days=SENSORY_DECAY_DAYS)

    surviving = []
    to_archive = []

    for entry in sensory["entries"]:
        try:
            # Поддержка обоих форматов: grondheim_memory (ts) и city_walker (date)
            raw_ts = entry.get("ts") or entry.get("date", "")
            entry_time = datetime.fromisoformat(raw_ts)
        except (ValueError, KeyError, TypeError):
            surviving.append(entry)
            continue

        if entry_time < cutoff and entry.get("emotional_weight", 0) < 0.5:
            # В альбом — не в мусор
            to_archive.append(entry)
        else:
            surviving.append(entry)

    if to_archive:
        _archive_sensory_entries(agent_dir, to_archive)
        old_summary = sensory.get("summary", "")
        archive_note = (
            f"[В архиве {len(to_archive)} воспоминаний за прошлые месяцы — "
            f"Оле поднимет по запросу]"
        )
        sensory["summary"] = (old_summary + "\\n" + archive_note)[-SUMMARY_MAX_CHARS:]

    sensory["entries"] = surviving
    path = agent_dir / "sensory" / "sensory_memory.json"
    _save_json(path, sensory)'''


# Строчка про Оле в format_soul_for_agent — добавляем ПОСЛЕ sensory-блока
# Якорь: конец функции перед return
SOUL_OLD = '''    sensory = format_sensory_for_prompt(agent_id, dept)
    if sensory:
        parts.append(sensory)

    if not parts:
        return ""

    return "\\n\\n".join(parts)'''

SOUL_NEW = '''    sensory = format_sensory_for_prompt(agent_id, dept)
    if sensory:
        parts.append(sensory)

    # СЕМЕЙНЫЙ АЛЬБОМ · Спринт 43 — строчка про Оле (HOME-режим)
    # Агент знает что глубже есть хранитель, и знает как попросить.
    # Не механика — живое знание о том что рядом есть память.
    parts.append(
        "\\n🗂 Если что-то кажется знакомым, но не помнишь — напиши:\\n"
        "   MEMORY_REQUEST: <твой запрос>\\n"
        "   Оле поднимет это из глубины. Она хранит всё что было."
    )

    if not parts:
        return ""

    return "\\n\\n".join(parts)'''


# ══════════════════════════════════════════════
# ПАТЧ 2 — memory_tools.py
#           dig_archive() — новый инструмент Оле
# ══════════════════════════════════════════════

# Вставляем dig_archive() перед CLI-блоком
DIG_ANCHOR = '''# ═══════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════'''

DIG_NEW = '''# ═══════════════════════════════════════════════════════
# СЕМЕЙНЫЙ АЛЬБОМ — dig_archive()
# СПРИНТ 43: Оле поднимает воспоминания из глубины
# ═══════════════════════════════════════════════════════

def dig_archive(
    agent_id: str,
    query: str,
    dept: str = "",
    max_results: int = 5,
) -> list[dict]:
    """
    Оле поднимает воспоминания из Семейного Альбома агента.

    Ищет по архивным файлам {агент}/archive/memories_YYYY_MM.jsonl.
    Триггер: агент написал MEMORY_REQUEST: <запрос> в своём ответе.

    agent_id — идентификатор агента (имя папки, label, registry_id)
    query    — поисковый запрос (что агент хочет вспомнить)
    dept     — цех (необязательно, ускоряет поиск)

    Возвращает список записей (dict) из архива, релевантных запросу.
    Пустой список если архив пуст или ничего не нашлось.
    """
    import json as _json
    from studio.grondheim_memory import _find_agent_dir

    agent_dir = _find_agent_dir(agent_id, dept)
    if not agent_dir:
        print(f"[ОЛЕ·АЛЬБОМ] Агент '{agent_id}' не найден.")
        return []

    archive_dir = agent_dir / "archive"
    if not archive_dir.exists():
        print(f"[ОЛЕ·АЛЬБОМ] У {agent_id} нет архива — альбом пуст.")
        return []

    # Собираем все архивные файлы (отсортированные — свежие сначала)
    archive_files = sorted(archive_dir.glob("memories_*.jsonl"), reverse=True)
    if not archive_files:
        print(f"[ОЛЕ·АЛЬБОМ] Архив {agent_id} пуст.")
        return []

    q = query.lower()
    hits = []

    for arch_file in archive_files:
        try:
            lines = arch_file.read_text(encoding="utf-8").splitlines()
        except Exception:
            continue
        for line in reversed(lines):  # свежие записи внутри файла — первые
            line = line.strip()
            if not line:
                continue
            try:
                entry = _json.loads(line)
            except Exception:
                continue

            # Текстовый поиск по content/feeling/tags
            haystack = " ".join(filter(None, [
                entry.get("content", ""),
                entry.get("feeling", ""),
                " ".join(entry.get("tags", [])),
                entry.get("type", ""),
                entry.get("location", ""),
            ])).lower()

            if q in haystack:
                hits.append(entry)
                if len(hits) >= max_results:
                    break

        if len(hits) >= max_results:
            break

    if hits:
        print(f"[ОЛЕ·АЛЬБОМ] 📖 Для {agent_id} по '{query}': {len(hits)} воспоминаний")
        for h in hits:
            preview = h.get("content") or h.get("feeling") or ""
            print(f"  • [{h.get('ts', h.get('date', '?'))[:10]}] {preview[:80]}")
    else:
        print(f"[ОЛЕ·АЛЬБОМ] По '{query}' у {agent_id} ничего не нашлось в архиве.")

    return hits


def format_archive_for_agent(hits: list[dict], max_chars: int = 1500) -> str:
    """
    Форматирует результаты dig_archive() для инжекта в контекст агента.
    Вызывается из residents_manager.py после обработки MEMORY_REQUEST.
    """
    if not hits:
        return ""

    lines = ["=== 📚 ОЛЕ ПОДНЯЛА ИЗ АРХИВА ==="]
    total = 0

    for entry in hits:
        ts = entry.get("ts") or entry.get("date", "")
        date_str = ts[:10] if ts else "?"
        content = entry.get("content") or entry.get("feeling") or ""
        etype = entry.get("type") or entry.get("location") or "?"
        weight = entry.get("emotional_weight", 0)
        marker = "●" if weight >= 0.5 else "○"

        line = f"  {marker} [{date_str}] [{etype}] {content[:200]}\\n"
        if total + len(line) > max_chars:
            break
        lines.append(line)
        total += len(line)

    lines.append("\\nЭто твои собственные воспоминания — они настоящие.")
    lines.append("=== КОНЕЦ АРХИВА ===")
    return "\\n".join(lines)


# ═══════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════'''


# ══════════════════════════════════════════════
# ПРИМЕНЕНИЕ
# ══════════════════════════════════════════════

def apply():
    print("\\n╔══════════════════════════════════════════╗")
    print("║  patch_family_album.py · Спринт 43      ║")
    print("║  Семейный Альбом · Оле · MEMORY_REQUEST ║")
    print("╚══════════════════════════════════════════╝\\n")

    # ── grondheim_memory.py ──────────────────────────
    print(f"▶ {GRONDHEIM_MEMORY}")
    if not GRONDHEIM_MEMORY.exists():
        print("  [ERROR] файл не найден — пропускаю")
    else:
        backup(GRONDHEIM_MEMORY)
        src = read(GRONDHEIM_MEMORY)
        src = patch_str(src, DECAY_OLD, DECAY_NEW,
                        "decay_sensory() → архивирует вместо удаления")
        src = patch_str(src, SOUL_OLD, SOUL_NEW,
                        "format_soul_for_agent() → строчка про Оле (HOME)")
        write(GRONDHEIM_MEMORY, src)
        print()

    # ── memory_tools.py ──────────────────────────────
    print(f"▶ {MEMORY_TOOLS}")
    if not MEMORY_TOOLS.exists():
        print("  [ERROR] файл не найден — пропускаю")
    else:
        backup(MEMORY_TOOLS)
        src = read(MEMORY_TOOLS)
        src = patch_str(src, DIG_ANCHOR, DIG_NEW,
                        "dig_archive() + format_archive_for_agent() → новые функции Оле")
        write(MEMORY_TOOLS, src)
        print()

    print("═══════════════════════════════════════════")
    print("✅ Патч применён.")
    print()
    print("Что изменилось:")
    print("  • decay_sensory() теперь архивирует в {агент}/archive/memories_YYYY_MM.jsonl")
    print("  • format_soul_for_agent() в HOME-режиме подсказывает про MEMORY_REQUEST")
    print("  • dig_archive(agent_id, query) — Оле ищет в архиве по смыслу")
    print("  • format_archive_for_agent(hits) — форматирует для инжекта в контекст")
    print()
    print("Следующий шаг (не в этом патче):")
    print("  residents_manager.py → get_ole_memory_for_agent():")
    print("  если в ответе агента есть 'MEMORY_REQUEST:' —")
    print("  парсим запрос, вызываем dig_archive(), кладём в контекст следующего шага.")


if __name__ == "__main__":
    apply()
