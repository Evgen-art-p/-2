# studio/economy/memory_embedding.py
"""
ЭТАП 3 — MEMORY EMBEDDING (Глубокое Резюме Системы)

Превращает экономические числа в текстовые ощущения
и записывает их в sensory память агента.

Агент не хранит "$0.003 за ран" — он помнит:
  "heavy but successful"
  "cheap but unstable"
  "costly mistake"
  "effortless win"

Это основа интуиции. Cost Intuition (Этап 2) читает ledger.
Memory Embedding пишет в душу агента — в sensory_memory.json.

Вызывается из pipeline.py после каждого рана (post-fact).
"""

from studio.economy import ledger as _ledger

# ═══════════════════════════════════════════════════════════
# ПОРОГИ — как числа превращаются в ощущения
# ═══════════════════════════════════════════════════════════

# cost_usd за один ран (все агенты вместе)
COST_LEVELS = [
    (0.0005, "featherlight"),   # почти бесплатно
    (0.002,  "light"),          # лёгкий
    (0.005,  "medium"),         # средний
    (0.015,  "heavy"),          # тяжёлый
    (float("inf"), "crushing"), # раздавливающий
]

# score (0-10) от QA
QUALITY_LEVELS = [
    (4.0,  "failed"),       # провал
    (6.0,  "unstable"),     # нестабильный
    (7.5,  "decent"),       # нормальный
    (9.0,  "successful"),   # успешный
    (10.1, "brilliant"),    # блестящий
]


def _cost_label(cost_usd: float) -> str:
    for threshold, label in COST_LEVELS:
        if cost_usd < threshold:
            return label
    return "crushing"


def _quality_label(score: float) -> str:
    for threshold, label in QUALITY_LEVELS:
        if score < threshold:
            return label
    return "brilliant"


# ═══════════════════════════════════════════════════════════
# КОМБИНАЦИИ — ощущение из пары (cost, quality)
# ═══════════════════════════════════════════════════════════

def _combine(cost_label: str, quality_label: str) -> str:
    """
    Строит текстовое ощущение из пары (стоимость, качество).
    Ключ: f"{cost_label}:{quality_label}"
    """
    combos = {
        # Дёшево
        "featherlight:brilliant":  "effortless win",
        "featherlight:successful": "cheap and clean",
        "featherlight:decent":     "light but fragile",
        "featherlight:unstable":   "cheap but unstable",
        "featherlight:failed":     "wasted even at low cost",
        # Легко
        "light:brilliant":         "light touch, bright result",
        "light:successful":        "efficient and solid",
        "light:decent":            "light but okay",
        "light:unstable":          "low cost, rough edges",
        "light:failed":            "cheap failure",
        # Средне
        "medium:brilliant":        "worth every token",
        "medium:successful":       "balanced run",
        "medium:decent":           "medium effort, medium result",
        "medium:unstable":         "costly for the quality",
        "medium:failed":           "expensive mistake",
        # Тяжело
        "heavy:brilliant":         "heavy but glorious",
        "heavy:successful":        "heavy but successful",
        "heavy:decent":            "heavy investment, weak return",
        "heavy:unstable":          "burning budget, shaky result",
        "heavy:failed":            "costly mistake",
        # Давит
        "crushing:brilliant":      "exhausting masterpiece",
        "crushing:successful":     "worth the sacrifice",
        "crushing:decent":         "slow but precise",
        "crushing:unstable":       "brutal and unstable",
        "crushing:failed":         "catastrophic waste",
    }
    key = f"{cost_label}:{quality_label}"
    return combos.get(key, f"{cost_label}, {quality_label}")


# ═══════════════════════════════════════════════════════════
# ПУБЛИЧНЫЙ API
# ═══════════════════════════════════════════════════════════

def build_embedding(
    agent_id: str,
    slot_id: str,
    score: float,
    run_cost_usd: float = None,
) -> str:
    """
    Строит текстовое ощущение рана для агента.

    Args:
        agent_id:     ID агента
        slot_id:      ID цеха
        score:        Оценка QA (0-10)
        run_cost_usd: Стоимость рана (если None — берём из ledger)

    Returns:
        Текстовое ощущение ("heavy but successful", ...)
    """
    if run_cost_usd is None:
        # Берём суммарные расходы агента в этом цехе
        # (грубая оценка — для точности нужен run_id в ledger, Этап 1+)
        recent = _ledger.recent_by_agent(agent_id, slot_id=slot_id, n=3)
        run_cost_usd = sum(e["cost_usd"] for e in recent) if recent else 0.0

    cost_label    = _cost_label(run_cost_usd)
    quality_label = _quality_label(score)
    feeling       = _combine(cost_label, quality_label)

    return feeling


def embed_to_sensory(
    agent_id: str,
    slot_id: str,
    score: float,
    run_cost_usd: float = None,
    dept: str = "",
) -> str:
    """
    Строит ощущение и записывает его в sensory память агента.
    Возвращает текст ощущения.

    Вызывается из pipeline.py post-fact после QA оценки.
    """
    feeling = build_embedding(agent_id, slot_id, score, run_cost_usd)

    # Пишем в sensory память агента
    try:
        from studio.grondheim_memory import record_sensory_event
        record_sensory_event(
            agent_id=agent_id,
            content=f"[economy:{slot_id}] {feeling}",
            event_type="reflection",
            source="economy",
            tags=["economy", "embedding", slot_id],
            emotional_weight=_emotional_weight(score),
            dept=dept,
        )
    except Exception as e:
        print(f"[EMBEDDING] Ошибка записи в sensory {agent_id}: {e}")

    return feeling


def _emotional_weight(score: float) -> float:
    """
    Определяет emotional_weight для sensory.
    Яркие события (победы и провалы) запоминаются сильнее.
      score >= 8  → 0.7 (победа — важно)
      score >= 6  → 0.4 (норма — умеренно)
      score < 4   → 0.8 (провал — очень важно, не забыть)
      иначе       → 0.3
    """
    if score >= 8.0:
        return 0.7
    elif score < 4.0:
        return 0.8
    elif score >= 6.0:
        return 0.4
    else:
        return 0.3


def embed_all_agents(
    agents_scores: dict[str, float],
    slot_id: str,
    dept: str = "",
) -> dict[str, str]:
    """
    Массовая запись ощущений для всех агентов рана.

    Args:
        agents_scores: {"A03": 8.5, "A07": 6.0, ...}
        slot_id:       ID цеха
        dept:          ID отдела (для grondheim)

    Returns:
        {"A03": "heavy but successful", "A07": "balanced run", ...}
    """
    results = {}
    for agent_id, score in agents_scores.items():
        feeling = embed_to_sensory(
            agent_id=agent_id,
            slot_id=slot_id,
            score=score,
            dept=dept,
        )
        results[agent_id] = feeling
        print(f"[EMBEDDING] {agent_id} in {slot_id}: score={score} → \"{feeling}\"")
    return results
