# studio/cabinet/archive.py — Архив чатов + двухуровневая память агентов
# v2.1:
#   - Глобальная память кабинета (как раньше)
#   - Полная память резидентов: до 10 конспектов в modules/{dept}/{ID}/memory/
#   - Лёгкая память рабочих агентов: последний диалог в modules/{dept}/{ID}/memory/
#   - Архив чатов агентов: сохраняется в modules/{dept}/{ID}/memory/archive/

import json
from pathlib import Path
from datetime import datetime

CABINET_DATA_DIR = Path("prompts/cabinet/data")
CABINET_DATA_DIR.mkdir(parents=True, exist_ok=True)

MEMORY_FILE = CABINET_DATA_DIR / "memory.json"
MAX_MEMORY_ENTRIES = 10

# Настройки памяти агентов
MAX_AGENT_MEMORY_ENTRIES = 10    # для резидентов — сколько конспектов хранить
MAX_LAST_CHAT_MESSAGES = 30      # для лёгкой памяти — сколько сообщений из последнего диалога


# ═══════════════════════════════════════════════════
#  GLOBAL CHAT ARCHIVE (как раньше)
# ═══════════════════════════════════════════════════

def save_chat_archive(chat_history: list, prompt_id: str, model: str) -> Path:
    """Сохраняет чат в JSON-файл. Возвращает путь."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    slug = (prompt_id or "free").replace(":", "_").replace("/", "_").replace("\\", "_")
    filename = f"{ts}_{slug}.json"
    filepath = CABINET_DATA_DIR / filename

    first_user = next((m["content"][:60] for m in chat_history if m["role"] == "user"), "без названия")

    data = {
        "title": first_user,
        "prompt": prompt_id or "free",
        "model": model,
        "date": datetime.now().isoformat(),
        "messages": [{"role": m["role"], "content": m["content"]} for m in chat_history],
    }
    filepath.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[CABINET] 💾 Чат сохранён: {filename}")
    return filepath


def load_archive_list() -> list[dict]:
    """Возвращает список архивных чатов (метаданные без сообщений)."""
    archive = []
    if not CABINET_DATA_DIR.exists():
        return archive
    for fp in sorted(CABINET_DATA_DIR.glob("*.json"), reverse=True):
        if fp.name == "memory.json":
            continue
        try:
            data = json.loads(fp.read_text(encoding="utf-8"))
            archive.append({
                "file": fp.name,
                "title": data.get("title", "?")[:50],
                "prompt": data.get("prompt", ""),
                "model": data.get("model", ""),
                "date": data.get("date", ""),
                "msg_count": len(data.get("messages", [])),
            })
        except Exception:
            pass
    return archive


def load_chat_from_archive(filename: str) -> dict | None:
    """Загружает полный чат из архива."""
    fp = CABINET_DATA_DIR / filename
    if not fp.exists():
        return None
    try:
        return json.loads(fp.read_text(encoding="utf-8"))
    except Exception:
        return None


def delete_archive_chat(filename: str):
    """Удаляет чат из архива."""
    fp = CABINET_DATA_DIR / filename
    if fp.exists():
        fp.unlink()
        print(f"[CABINET] 🗑️ Удалён: {filename}")


# ═══════════════════════════════════════════════════
#  GLOBAL MEMORY (конспекты кабинета — legacy, обратная совместимость)
# ═══════════════════════════════════════════════════

def load_memory() -> list[dict]:
    if not MEMORY_FILE.exists():
        return []
    try:
        return json.loads(MEMORY_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []


def save_memory(entries: list[dict]):
    MEMORY_FILE.write_text(
        json.dumps(entries[-MAX_MEMORY_ENTRIES:], ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


def format_memory_context() -> str:
    """Форматирует глобальные конспекты для инжекта в system prompt."""
    entries = load_memory()
    if not entries:
        return ""
    parts = ["[ПАМЯТЬ ПРОШЛЫХ СЕССИЙ]"]
    for e in entries:
        parts.append(f"\n📅 {e.get('date', '?')} | {e.get('prompt', 'free')}:")
        parts.append(e.get("summary", ""))
    parts.append("[КОНЕЦ ПАМЯТИ]")
    return "\n".join(parts)


# ═══════════════════════════════════════════════════
#  AGENT MEMORY — Двухуровневая система
# ═══════════════════════════════════════════════════
#
# Структура на диске:
#   modules/{dept}/{agent_id}/memory/
#     memory.json       — конспекты (для резидентов, до 10 штук)
#     last_chat.json    — последний диалог (для всех агентов)
#     archive/          — архив чатов агента
#       20260316_1430_LOKA.json
#
# Резиденты (is_resident=True):
#   - Полная память: memory.json с конспектами
#   - Последний диалог: last_chat.json
#   - Архив: сохраняется каждый диалог
#
# Рабочие агенты (is_resident=False):
#   - Только последний диалог: last_chat.json (перезаписывается)
#   - Без конспектов, без архива


def _get_agent_memory_dir(agent_id: str, dept: str = "") -> Path:
    """Путь к папке memory/ агента."""
    from studio.modules_registry import MODULES_DIR, CURRENT_DEPT

    target_dept = dept or CURRENT_DEPT

    # Пробуем точный путь
    mem_dir = MODULES_DIR / target_dept / agent_id / "memory"
    if mem_dir.parent.exists():
        mem_dir.mkdir(parents=True, exist_ok=True)
        return mem_dir

    # Поиск по всем цехам
    if MODULES_DIR.exists():
        for d in MODULES_DIR.iterdir():
            if d.is_dir():
                candidate = d / agent_id / "memory"
                if candidate.parent.exists():
                    candidate.mkdir(parents=True, exist_ok=True)
                    return candidate

    # Fallback — создаём в текущем
    mem_dir = MODULES_DIR / target_dept / agent_id / "memory"
    mem_dir.mkdir(parents=True, exist_ok=True)
    return mem_dir


# ── Полная память резидентов (конспекты) ──────────

def load_agent_memory(agent_id: str, dept: str = "") -> list[dict]:
    """Загружает конспекты агента (для резидентов).

    Returns:
        [{date, summary, model}, ...]
    """
    mem_dir = _get_agent_memory_dir(agent_id, dept)
    mem_file = mem_dir / "memory.json"
    if not mem_file.exists():
        return []
    try:
        return json.loads(mem_file.read_text(encoding="utf-8"))
    except Exception:
        return []


def save_agent_memory(agent_id: str, summary: str, model: str = "",
                      dept: str = "") -> None:
    """Добавляет конспект в память резидента.

    Хранит до MAX_AGENT_MEMORY_ENTRIES записей (FIFO).
    """
    mem_dir = _get_agent_memory_dir(agent_id, dept)
    mem_file = mem_dir / "memory.json"

    entries = load_agent_memory(agent_id, dept)
    entries.append({
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "summary": summary.strip(),
        "model": model,
    })

    # Обрезаем до лимита
    entries = entries[-MAX_AGENT_MEMORY_ENTRIES:]

    mem_file.write_text(
        json.dumps(entries, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print(f"[CABINET] 🧠 Память {agent_id}: +1 конспект (всего {len(entries)})")


def format_agent_memory_context(agent_id: str, dept: str = "") -> str:
    """Форматирует конспекты агента для инжекта в system prompt.

    Используется для резидентов.
    """
    entries = load_agent_memory(agent_id, dept)
    if not entries:
        return ""

    parts = [f"[ПАМЯТЬ ДИАЛОГОВ С АРХИТЕКТОРОМ]"]
    for e in entries:
        parts.append(f"\n📅 {e.get('date', '?')}:")
        parts.append(e.get("summary", ""))
    parts.append("[КОНЕЦ ПАМЯТИ]")
    return "\n".join(parts)


# ── Лёгкая память (последний диалог) ─────────────

def save_agent_last_chat(agent_id: str, chat_history: list,
                         dept: str = "") -> None:
    """Сохраняет последний диалог агента.

    Для рабочих агентов это единственная память.
    Для резидентов — дополнение к конспектам.
    Перезаписывается при каждом новом диалоге.
    """
    mem_dir = _get_agent_memory_dir(agent_id, dept)
    last_file = mem_dir / "last_chat.json"

    # Обрезаем до лимита сообщений
    messages = [
        {"role": m["role"], "content": m["content"][:500]}
        for m in chat_history[-MAX_LAST_CHAT_MESSAGES:]
    ]

    data = {
        "agent_id": agent_id,
        "date": datetime.now().isoformat(),
        "messages": messages,
    }
    last_file.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print(f"[CABINET] 💬 Последний диалог {agent_id}: {len(messages)} сообщений")


def load_agent_last_chat(agent_id: str, dept: str = "") -> dict | None:
    """Загружает последний диалог агента.

    Returns:
        {agent_id, date, messages: [{role, content}]} или None
    """
    mem_dir = _get_agent_memory_dir(agent_id, dept)
    last_file = mem_dir / "last_chat.json"
    if not last_file.exists():
        return None
    try:
        return json.loads(last_file.read_text(encoding="utf-8"))
    except Exception:
        return None


def format_last_chat_context(agent_id: str, dept: str = "") -> str:
    """Форматирует последний диалог для инжекта в system prompt.

    Используется для рабочих агентов (лёгкая память).
    """
    data = load_agent_last_chat(agent_id, dept)
    if not data or not data.get("messages"):
        return ""

    date = data.get("date", "")
    try:
        dt = datetime.fromisoformat(date)
        date_str = dt.strftime("%d %b %H:%M")
    except Exception:
        date_str = date[:16] if date else "?"

    parts = [f"[ПРЕДЫДУЩИЙ РАЗГОВОР ({date_str})]"]
    for m in data["messages"]:
        role_label = "АРХИТЕКТОР" if m["role"] == "user" else "Я"
        parts.append(f"{role_label}: {m['content']}")
    parts.append("[КОНЕЦ ПРЕДЫДУЩЕГО РАЗГОВОРА]")
    return "\n".join(parts)


# ── Архив чатов агента (для резидентов) ───────────

def save_agent_chat_archive(agent_id: str, chat_history: list,
                            model: str = "", dept: str = "") -> Path:
    """Сохраняет диалог в архив агента (для резидентов).

    Путь: modules/{dept}/{agent_id}/memory/archive/{timestamp}_{agent_id}.json
    """
    mem_dir = _get_agent_memory_dir(agent_id, dept)
    archive_dir = mem_dir / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{ts}_{agent_id}.json"
    filepath = archive_dir / filename

    first_user = next(
        (m["content"][:60] for m in chat_history if m["role"] == "user"),
        "без названия"
    )

    data = {
        "agent_id": agent_id,
        "title": first_user,
        "model": model,
        "date": datetime.now().isoformat(),
        "messages": [
            {"role": m["role"], "content": m["content"]}
            for m in chat_history
        ],
    }
    filepath.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print(f"[CABINET] 📂 Архив {agent_id}: {filename}")
    return filepath


def load_agent_archive_list(agent_id: str, dept: str = "") -> list[dict]:
    """Список архивных чатов агента (метаданные)."""
    mem_dir = _get_agent_memory_dir(agent_id, dept)
    archive_dir = mem_dir / "archive"
    if not archive_dir.exists():
        return []

    archive = []
    for fp in sorted(archive_dir.glob("*.json"), reverse=True):
        try:
            data = json.loads(fp.read_text(encoding="utf-8"))
            archive.append({
                "file": fp.name,
                "title": data.get("title", "?")[:50],
                "model": data.get("model", ""),
                "date": data.get("date", ""),
                "msg_count": len(data.get("messages", [])),
            })
        except Exception:
            pass
    return archive


# ═══════════════════════════════════════════════════
#  CONVENIENCE — сохранить всю память агента за один вызов
# ═══════════════════════════════════════════════════

def finalize_agent_dialog(agent_id: str, chat_history: list,
                          summary: str, model: str = "",
                          dept: str = "", is_resident: bool = False) -> None:
    """Финализация диалога с агентом — вызывается при завершении.

    Для резидентов:
      1. Конспект → memory.json (полная память)
      2. Последний диалог → last_chat.json
      3. Архив → archive/{timestamp}.json

    Для рабочих агентов:
      1. Последний диалог → last_chat.json (перезаписывается)
    """
    if not chat_history or len(chat_history) < 2:
        return

    # Последний диалог — для всех
    save_agent_last_chat(agent_id, chat_history, dept)

    if is_resident:
        # Конспект — только резиденты
        if summary:
            save_agent_memory(agent_id, summary, model, dept)

        # Архив — только резиденты
        save_agent_chat_archive(agent_id, chat_history, model, dept)

    print(f"[CABINET] ✅ Диалог с {agent_id} финализирован "
          f"({'резидент' if is_resident else 'рабочий'})")


def build_agent_context(agent_id: str, dept: str = "",
                        is_resident: bool = False) -> str:
    """Собирает контекст памяти агента для инжекта в system prompt.

    Резиденты: полные конспекты (до 10)
    Рабочие: предыдущий диалог (1 штука)

    Returns:
        Строка для добавления в system prompt (может быть пустой)
    """
    if is_resident:
        return format_agent_memory_context(agent_id, dept)
    else:
        return format_last_chat_context(agent_id, dept)
