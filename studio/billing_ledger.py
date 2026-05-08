# studio/billing_ledger.py
"""
ЭТАП 1 — БИЛЛИНГ КАК ИСТИНА (Глубокое Резюме Системы)

Это физический слой экономики студии.
Никакой логики. Только запись реальности.

Каждый LLM вызов = реальный расход.
Лог хранит: кто, в каком цехе, какая модель, сколько стоило, когда.

Это "гравитация системы" — единственная жёсткая правда.
"""

import json
import threading
from datetime import datetime, timezone
from pathlib import Path

from studio.config import BASE_DIR

# ═══════════════════════════════════════════════════════════
# СТОИМОСТЬ МОДЕЛЕЙ (per 1M tokens, USD)
# Обновляй при изменении тарифов OpenRouter
# ═══════════════════════════════════════════════════════════
MODEL_PRICES: dict[str, dict[str, float]] = {
    # Gemini
    "google/gemini-2.5-flash":          {"input": 0.15,  "output": 0.60},
    "google/gemini-2.0-flash":          {"input": 0.10,  "output": 0.40},
    "google/gemini-1.5-flash":          {"input": 0.075, "output": 0.30},
    # Claude
    "anthropic/claude-sonnet-4-5":      {"input": 3.00,  "output": 15.00},
    "anthropic/claude-3-haiku":         {"input": 0.25,  "output": 1.25},
    # GPT
    "openai/gpt-4o-mini":               {"input": 0.15,  "output": 0.60},
    "openai/gpt-4o":                    {"input": 2.50,  "output": 10.00},
    # Fallback (неизвестная модель)
    "_default":                         {"input": 0.50,  "output": 2.00},
}


def _calc_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """Считает стоимость в USD по токенам."""
    prices = MODEL_PRICES.get(model, MODEL_PRICES["_default"])
    cost = (
        prompt_tokens     / 1_000_000 * prices["input"] +
        completion_tokens / 1_000_000 * prices["output"]
    )
    return round(cost, 8)


# ═══════════════════════════════════════════════════════════
# ХРАНИЛИЩЕ
# ═══════════════════════════════════════════════════════════
LEDGER_FILE = BASE_DIR / "studio" / "billing_ledger.jsonl"
_lock = threading.Lock()


def record(
    agent_id: str,
    slot_id: str,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    call_type: str = "chat",  # chat | chat_with_tools | chat_with_images
) -> dict:
    """
    Записывает один LLM вызов в лог.

    Args:
        agent_id:          ID агента ("A03", "loka", ...)
        slot_id:           ID цеха/слота ("turbo", "living_book", ...)
        model:             Имя модели OpenRouter
        prompt_tokens:     Входные токены (из usage.prompt_tokens)
        completion_tokens: Выходные токены (из usage.completion_tokens)
        call_type:         Тип вызова

    Returns:
        Запись лога (dict)
    """
    cost_usd = _calc_cost(model, prompt_tokens, completion_tokens)

    entry = {
        "ts":                datetime.now(timezone.utc).isoformat(),
        "agent_id":          agent_id,
        "slot_id":           slot_id,
        "model":             model,
        "prompt_tokens":     prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens":      prompt_tokens + completion_tokens,
        "cost_usd":          cost_usd,
        "call_type":         call_type,
    }

    with _lock:
        with open(LEDGER_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    return entry


# ═══════════════════════════════════════════════════════════
# АНАЛИТИКА (только чтение — для Этапа 2 Cost Intuition)
# ═══════════════════════════════════════════════════════════

def read_ledger(limit: int = None) -> list[dict]:
    """Читает все записи лога (или последние N)."""
    if not LEDGER_FILE.exists():
        return []
    with _lock:
        lines = LEDGER_FILE.read_text(encoding="utf-8").strip().splitlines()
    entries = []
    for line in lines:
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    if limit:
        return entries[-limit:]
    return entries


def total_spent() -> float:
    """Суммарные расходы студии за всё время (USD)."""
    return round(sum(e["cost_usd"] for e in read_ledger()), 6)


def agent_spent(agent_id: str, slot_id: str = None) -> float:
    """Расходы конкретного агента (опционально — в конкретном цехе)."""
    entries = read_ledger()
    filtered = [e for e in entries if e["agent_id"] == agent_id]
    if slot_id:
        filtered = [e for e in filtered if e["slot_id"] == slot_id]
    return round(sum(e["cost_usd"] for e in filtered), 6)


def slot_spent(slot_id: str) -> float:
    """Расходы конкретного цеха за всё время."""
    return round(
        sum(e["cost_usd"] for e in read_ledger() if e["slot_id"] == slot_id),
        6
    )


def recent_by_agent(agent_id: str, slot_id: str = None, n: int = 20) -> list[dict]:
    """Последние N записей агента (для Cost Intuition — Этап 2)."""
    entries = read_ledger()
    filtered = [e for e in entries if e["agent_id"] == agent_id]
    if slot_id:
        filtered = [e for e in filtered if e["slot_id"] == slot_id]
    return filtered[-n:]
