# studio/economy/ledger.py
"""
ЭТАП 1 — БИЛЛИНГ КАК ИСТИНА (Глубокое Резюме Системы)

Физический слой экономики студии.
Никакой логики. Только запись реальности.

Каждый LLM вызов = реальный расход.
Это "гравитация системы" — единственная жёсткая правда.

Хранение: studio/economy/data/billing_ledger.jsonl
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
    "google/gemini-2.5-flash":          {"input": 0.15,  "output": 0.60},
    "google/gemini-2.0-flash":          {"input": 0.10,  "output": 0.40},
    "google/gemini-1.5-flash":          {"input": 0.075, "output": 0.30},
    "anthropic/claude-sonnet-4-5":      {"input": 3.00,  "output": 15.00},
    "anthropic/claude-3-haiku":         {"input": 0.25,  "output": 1.25},
    "openai/gpt-4o-mini":               {"input": 0.15,  "output": 0.60},
    "openai/gpt-4o":                    {"input": 2.50,  "output": 10.00},
    "_default":                         {"input": 0.50,  "output": 2.00},
}

DATA_DIR   = BASE_DIR / "studio" / "economy" / "data"
LEDGER_FILE = DATA_DIR / "billing_ledger.jsonl"
_lock = threading.Lock()


def _ensure() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def _calc_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    prices = MODEL_PRICES.get(model, MODEL_PRICES["_default"])
    return round(
        prompt_tokens     / 1_000_000 * prices["input"] +
        completion_tokens / 1_000_000 * prices["output"],
        8
    )


def record(
    agent_id: str,
    slot_id: str,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    call_type: str = "chat",
) -> dict:
    """
    Записывает один LLM вызов в лог.

    Args:
        agent_id:          ID агента ("A03", "loka", ...)
        slot_id:           ID цеха ("turbo", "living_book", ...)
        model:             Модель OpenRouter
        prompt_tokens:     Входные токены из usage
        completion_tokens: Выходные токены из usage
        call_type:         chat | chat_with_tools | chat_with_images
    """
    _ensure()
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


def read_all(limit: int = None) -> list[dict]:
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
    return entries[-limit:] if limit else entries


def total_spent() -> float:
    return round(sum(e["cost_usd"] for e in read_all()), 6)


def agent_spent(agent_id: str, slot_id: str = None) -> float:
    entries = [e for e in read_all() if e["agent_id"] == agent_id]
    if slot_id:
        entries = [e for e in entries if e["slot_id"] == slot_id]
    return round(sum(e["cost_usd"] for e in entries), 6)


def slot_spent(slot_id: str) -> float:
    return round(
        sum(e["cost_usd"] for e in read_all() if e["slot_id"] == slot_id), 6
    )


def recent_by_agent(agent_id: str, slot_id: str = None, n: int = 20) -> list[dict]:
    entries = [e for e in read_all() if e["agent_id"] == agent_id]
    if slot_id:
        entries = [e for e in entries if e["slot_id"] == slot_id]
    return entries[-n:]
