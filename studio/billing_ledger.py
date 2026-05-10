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
from datetime import datetime, timedelta, timezone
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

# Модели с фиксированной ценой за вызов (не per-token)
# Используется когда prompt_tokens=0 и completion_tokens=0
MODEL_FLAT_PRICES: dict[str, float] = {
    "fal/Nano Banana Pro":   0.04,
    "fal/Seedream 4.5":      0.04,
    # Suno, ElevenLabs, SiliconFlow — добавишь позже
    # "suno/...":            0.05,
    # "elevenlabs/...":      0.03,
    # "siliconflow/...":     0.02,
}


def _calc_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """Считает стоимость в USD по токенам или фиксированной цене."""
    # Flat-price модели (FAL, Suno, ElevenLabs и т.д.)
    if model in MODEL_FLAT_PRICES:
        return MODEL_FLAT_PRICES[model]
    # Per-token модели
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
    call_type: str = "chat",
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
# АНАЛИТИКА (только чтение)
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
    """Последние N записей агента."""
    entries = read_ledger()
    filtered = [e for e in entries if e["agent_id"] == agent_id]
    if slot_id:
        filtered = [e for e in filtered if e["slot_id"] == slot_id]
    return filtered[-n:]


# ═══════════════════════════════════════════════════════════
# DASHBOARD API (v1.0)
# ═══════════════════════════════════════════════════════════

def get_economy_data(days: int = 1) -> dict:
    """
    Агрегаты за период для дашборда.

    Args:
        days: 1 (сегодня), 7 (неделя), 30 (месяц)

    Returns:
        {
            "total": float,
            "burn_rate": float,
            "by_provider": {provider: cost},
            "by_model": {model: cost},
            "by_agent": {agent_id: cost},
            "by_slot": {slot_id: cost}
        }
    """
    entries = read_ledger()
    if not entries:
        return {
            "total": 0, "prev_total": 0, "burn_rate": 0,
            "by_provider": {}, "by_model": {},
            "by_agent": {}, "by_slot": {}
        }

    now        = datetime.now(timezone.utc)
    cutoff     = now - timedelta(days=days)
    prev_cutoff = cutoff - timedelta(days=days)   # ← предыдущий эквивалентный период

    total      = 0.0
    prev_total = 0.0
    by_provider: dict[str, float] = {}
    by_model:    dict[str, float] = {}
    by_agent:    dict[str, float] = {}
    by_slot:     dict[str, float] = {}

    for entry in entries:
        try:
            entry_time = datetime.fromisoformat(entry["ts"])
            cost       = entry.get("cost_usd", 0)

            # Предыдущий период (для TRENDS)
            if prev_cutoff <= entry_time < cutoff:
                prev_total += cost

            if entry_time < cutoff:
                continue

            provider = entry.get("provider", "openrouter")
            model    = entry.get("model",    "unknown")
            agent    = entry.get("agent_id", "unknown")
            slot     = entry.get("slot_id",  "unknown")

            total += cost
            by_provider[provider] = by_provider.get(provider, 0) + cost
            by_model[model]       = by_model.get(model, 0)       + cost
            by_agent[agent]       = by_agent.get(agent, 0)       + cost
            by_slot[slot]         = by_slot.get(slot, 0)         + cost
        except Exception:
            continue

    minutes   = max(days * 24 * 60, 1)
    burn_rate = total / minutes

    return {
        "total":      round(total, 4),
        "prev_total": round(prev_total, 4),          # ← TRENDS ячейка
        "burn_rate":  round(burn_rate, 4),
        "by_provider": dict(sorted(
            {k: round(v, 4) for k, v in by_provider.items()}.items(),
            key=lambda x: x[1], reverse=True
        )),
        "by_model": dict(sorted(
            {k: round(v, 4) for k, v in by_model.items()}.items(),
            key=lambda x: x[1], reverse=True
        )),
        "by_agent": dict(sorted(
            {k: round(v, 4) for k, v in by_agent.items()}.items(),
            key=lambda x: x[1], reverse=True
        )),
        "by_slot": dict(sorted(
            {k: round(v, 4) for k, v in by_slot.items()}.items(),
            key=lambda x: x[1], reverse=True
        )),
    }


def get_agent_stats(agent_id: str, days: int = 1) -> dict:
    """
    Детальная статистика по одному агенту за период.

    Args:
        agent_id: ID агента ("A03", "loka", ...)
        days: период

    Returns:
        {
            "agent_id": str,
            "total": float,
            "burn_rate": float,
            "total_calls": int,
            "avg_cost": float,
            "by_provider": {provider: cost},
            "by_model": {model: cost},
            "recent": [list of recent entries]
        }
    """
    entries = read_ledger()
    if not entries:
        return {
            "agent_id": agent_id, "total": 0, "burn_rate": 0,
            "total_calls": 0, "avg_cost": 0,
            "by_provider": {}, "by_model": {}, "recent": []
        }

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=days)

    total = 0.0
    call_count = 0
    by_provider: dict[str, float] = {}
    by_model: dict[str, float] = {}
    recent: list[dict] = []

    for entry in entries:
        try:
            if entry.get("agent_id") != agent_id:
                continue

            entry_time = datetime.fromisoformat(entry["ts"])
            if entry_time < cutoff:
                continue

            cost = entry.get("cost_usd", 0)
            provider = entry.get("provider", "openrouter")
            model = entry.get("model", "unknown")

            total += cost
            call_count += 1
            by_provider[provider] = by_provider.get(provider, 0) + cost
            by_model[model] = by_model.get(model, 0) + cost

            recent.append({
                "ts": entry["ts"],
                "model": model,
                "cost": cost,
                "tokens": entry.get("total_tokens", 0),
            })
        except Exception:
            continue

    minutes = max(days * 24 * 60, 1)
    burn_rate = total / minutes
    avg_cost = round(total / call_count, 6) if call_count > 0 else 0
    recent = sorted(recent, key=lambda x: x["ts"], reverse=True)[:10]

    return {
        "agent_id": agent_id,
        "total": round(total, 4),
        "burn_rate": round(burn_rate, 4),
        "total_calls": call_count,
        "avg_cost": avg_cost,
        "by_provider": dict(sorted(
            {k: round(v, 4) for k, v in by_provider.items()}.items(),
            key=lambda x: x[1], reverse=True
        )),
        "by_model": dict(sorted(
            {k: round(v, 4) for k, v in by_model.items()}.items(),
            key=lambda x: x[1], reverse=True
        )),
        "recent": recent,
    }
def get_timeseries(period_days=7):
    """
    Возвращает временные ряды с заполненными пустыми слотами.

    period_days == 1  → группировка по часам ("00:00" … "23:00")
    period_days > 1   → группировка по дням  ("03.05" … "09.05")

    Пустые слоты всегда заполняются нулями — Chart.js не ломается.

    → {
        "labels":   ["00:00", "01:00", ...] | ["03.05", "04.05", ...],
        "cost":     [0.12, 0.45, ...],
        "calls":    [3, 8, ...],
        "avg_cost": [0.04, 0.056, ...]
    }
    """
    from collections import OrderedDict
    from datetime import datetime, timedelta, timezone

    now    = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=period_days)
    hourly = (period_days == 1)

    # ── 1. Предзаполняем ВСЕ слоты нулями ──────────────────────────────
    buckets: OrderedDict[str, dict] = OrderedDict()

    if hourly:
        # Округляем до начала часа
        slot = cutoff.replace(minute=0, second=0, microsecond=0)
        while slot <= now + timedelta(hours=1):
            buckets[slot.strftime("%H:00")] = {"cost": 0.0, "calls": 0}
            slot += timedelta(hours=1)
    else:
        slot = cutoff.replace(hour=0, minute=0, second=0, microsecond=0)
        while slot <= now + timedelta(days=1):
            buckets[slot.strftime("%d.%m")] = {"cost": 0.0, "calls": 0}
            slot += timedelta(days=1)

    # ── 2. Читаем леджер и заливаем данные ─────────────────────────────
    if LEDGER_FILE.exists():
        with open(LEDGER_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec  = json.loads(line)
                    ts   = datetime.fromisoformat(rec["ts"])
                    if ts < cutoff or ts > now:
                        continue
                    key  = ts.strftime("%H:00") if hourly else ts.strftime("%d.%m")
                    cost = rec.get("cost_usd", 0)
                    if key in buckets:
                        buckets[key]["cost"]  += cost
                        buckets[key]["calls"] += 1
                except Exception:
                    continue

    # ── 3. Собираем массивы ─────────────────────────────────────────────
    labels   = list(buckets.keys())
    cost     = [round(v["cost"],  4) for v in buckets.values()]
    calls    = [v["calls"]           for v in buckets.values()]
    avg_cost = [
        round(c / cs, 4) if cs > 0 else 0
        for c, cs in zip(cost, calls)
    ]

    return {
        "labels":   labels,
        "cost":     cost,
        "calls":    calls,
        "avg_cost": avg_cost,
    }
