# studio/economy/cost_intuition.py
"""
ЭТАП 2 — COST INTUITION · v2.0 «ROI-ощущение» (Спринт 44)

Агент НЕ видит деньги напрямую. Он чувствует ОКУПАЕМОСТЬ:
не «сколько я потратил», а «стоило ли оно того».

Исходная спека ЭТАПА 2 требовала пару (cost, outcome_quality) —
v1 читала только cost, и художник с честными flat-вызовами вечно
чувствовал «бюджет под угрозой» независимо от качества работы.

Качество берётся из task_score в billing_ledger (finalize-записи
финализаторов цехов, chain-шкала 0–6.0).

get_prompt_hint() → вставляй в промпт агента перед работой.
"""

from studio.economy import ledger

COST_THRESHOLDS = {
    "cheap":     0.0005,
    "medium":    0.003,
    "expensive": 0.010,
}
WINDOW_COST    = 10   # последних платных вызовов для среднего чека
WINDOW_QUALITY = 5    # последних task_score для среднего качества
SCAN_DEPTH     = 40   # сколько записей леджера сканируем


def _classify(avg_cost: float) -> str:
    if avg_cost < COST_THRESHOLDS["cheap"]:
        return "cheap"
    elif avg_cost < COST_THRESHOLDS["medium"]:
        return "medium"
    elif avg_cost < COST_THRESHOLDS["expensive"]:
        return "expensive"
    return "risky"


def _quality_bucket(avg_q: float | None) -> str:
    """Chain-шкала 0–6: clean (>=5.5) / solid (4.0–5.4) / weak (<4.0) / none."""
    if avg_q is None:
        return "none"
    if avg_q >= 5.5:
        return "clean"
    if avg_q >= 4.0:
        return "solid"
    return "weak"


# Ощущение = пара (вес расходов, окупаемость)
_FEELINGS = {
    ("cheap", "clean"):     "Лёгкая рука и чистый результат — работаешь без потерь, так держать.",
    ("cheap", "solid"):     "Расходы лёгкие, ремесло держится. Есть запас — можно копнуть глубже.",
    ("cheap", "weak"):      "Дёшево, но цепочка сыпется. Дешевизна не оправдывает брак — собери качество.",
    ("cheap", "none"):      "Ты чувствуешь лёгкость — последние действия не давили на бюджет. Работай уверенно.",
    ("medium", "clean"):    "Каждый вложенный токен окупается. Сбалансированная, честная работа.",
    ("medium", "solid"):    "Умеренный вес решений, ремесло на уровне. Выбирай стратегии осознанно.",
    ("medium", "weak"):     "Тратишь умеренно, но результат не держится. Пересмотри подход, не бюджет.",
    ("medium", "none"):     "Ты чувствуешь умеренный вес своих решений. Каждый шаг имеет значение.",
    ("expensive", "clean"): "Дорого — но чисто. Тяжёлая работа, которая того стоит. Следи за весом.",
    ("expensive", "solid"): "Тяжёлые вызовы при среднем результате. Ищи более лёгкие пути к тому же качеству.",
    ("expensive", "weak"):  "Дорого и не окупается. Остановись, подумай: меньше попыток — точнее замысел.",
    ("expensive", "none"):  "Ты ощущаешь тяжесть — последние вызовы стоили дорого. Думай экономно.",
    ("risky", "clean"):     "На грани бюджета, но результат блестит. Оправданный риск — не превращай его в привычку.",
    ("risky", "solid"):     "Бюджет под давлением, отдача средняя. Режь расход, качество держи.",
    ("risky", "weak"):      "Давление на пределе и работа сыпется. Максимальная осторожность: один точный шаг вместо пяти.",
    ("risky", "none"):      "Ты чувствуешь давление — бюджет под угрозой. Действуй с максимальной осторожностью.",
}


def get_intuition(agent_id: str, slot_id: str = None) -> dict:
    """Полная экономическая интуиция агента: вес расходов × окупаемость."""
    recent = ledger.recent_by_agent(agent_id, slot_id=slot_id, n=SCAN_DEPTH)
    total  = ledger.agent_spent(agent_id, slot_id=slot_id)

    if not recent:
        return {
            "level": "medium", "label": "нет истории",
            "avg_cost": 0.0, "total_spent": 0.0, "calls_seen": 0,
            "avg_quality": None, "quality_bucket": "none",
            "prompt_hint": "",
        }

    # средний чек — только по платным вызовам (finalize-нули не разбавляют)
    paid = [e for e in recent if e.get("cost_usd", 0) > 0]
    paid_window = paid[-WINDOW_COST:] if paid else recent[-WINDOW_COST:]
    avg_cost = (sum(e.get("cost_usd", 0) for e in paid_window) / len(paid_window)
                if paid_window else 0.0)

    # качество — из task_score (finalize-записи финализаторов)
    scores = [e["task_score"] for e in recent
              if e.get("task_score") is not None]
    q_window = scores[-WINDOW_QUALITY:]
    avg_q = round(sum(q_window) / len(q_window), 2) if q_window else None

    level   = _classify(avg_cost)
    bucket  = _quality_bucket(avg_q)
    feeling = _FEELINGS.get((level, bucket),
                            _FEELINGS[(level, "none")])

    q_line = (f"\nОкупаемость: качество последних ранов {avg_q}/6.0"
              if avg_q is not None else "")
    hint = (f"[ЭКОНОМИЧЕСКОЕ ОЩУЩЕНИЕ]\n{feeling}"
            f"\nУровень расходов: {level.upper()}{q_line}")

    return {
        "level":          level,
        "avg_cost":       round(avg_cost, 8),
        "total_spent":    total,
        "calls_seen":     len(recent),
        "avg_quality":    avg_q,
        "quality_bucket": bucket,
        "prompt_hint":    hint,
    }


def get_prompt_hint(agent_id: str, slot_id: str = None) -> str:
    """Быстрый доступ: только строка для вставки в промпт."""
    return get_intuition(agent_id, slot_id)["prompt_hint"]
