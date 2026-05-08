# studio/economy/cost_intuition.py
"""
ЭТАП 2 — COST INTUITION (Глубокое Резюме Системы)

Агент НЕ видит деньги напрямую.
Он видит:
  - "ощущение дороговизны"
  - "вес решения"
  - "риск потери бюджета"

Это превращает экономику в интуицию.
get_prompt_hint() → вставляй в промпт агента перед работой.
"""

from studio.economy import ledger

COST_THRESHOLDS = {
    "cheap":     0.0005,
    "medium":    0.003,
    "expensive": 0.010,
}
WINDOW = 10


def _classify(avg_cost: float) -> str:
    if avg_cost < COST_THRESHOLDS["cheap"]:
        return "cheap"
    elif avg_cost < COST_THRESHOLDS["medium"]:
        return "medium"
    elif avg_cost < COST_THRESHOLDS["expensive"]:
        return "expensive"
    return "risky"


def _feeling(level: str) -> str:
    return {
        "cheap":     "Ты чувствуешь лёгкость — твои последние действия не создавали давления на бюджет. Работай уверенно.",
        "medium":    "Ты чувствуешь умеренный вес своих решений. Каждый шаг имеет значение — выбирай стратегии осознанно.",
        "expensive": "Ты ощущаешь тяжесть — твои последние вызовы стоили дорого. Думай экономно, ищи более лёгкие пути.",
        "risky":     "Ты чувствуешь давление — бюджет под угрозой. Действуй с максимальной осторожностью.",
    }[level]


def get_intuition(agent_id: str, slot_id: str = None) -> dict:
    """Полная экономическая интуиция агента."""
    recent = ledger.recent_by_agent(agent_id, slot_id=slot_id, n=WINDOW)
    total  = ledger.agent_spent(agent_id, slot_id=slot_id)

    if not recent:
        return {
            "level": "medium", "label": "нет истории",
            "avg_cost": 0.0, "total_spent": 0.0, "calls_seen": 0,
            "prompt_hint": "",
        }

    avg_cost = sum(e["cost_usd"] for e in recent) / len(recent)
    level    = _classify(avg_cost)

    hint = f"[ЭКОНОМИЧЕСКОЕ ОЩУЩЕНИЕ]\n{_feeling(level)}\nУровень: {level.upper()}"

    return {
        "level":       level,
        "avg_cost":    round(avg_cost, 8),
        "total_spent": total,
        "calls_seen":  len(recent),
        "prompt_hint": hint,
    }


def get_prompt_hint(agent_id: str, slot_id: str = None) -> str:
    """Быстрый доступ: только строка для вставки в промпт."""
    return get_intuition(agent_id, slot_id)["prompt_hint"]
