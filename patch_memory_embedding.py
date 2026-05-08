#!/usr/bin/env python3
"""
ПАТЧ: Этап 3 — Memory Embedding (Глубокое Резюме Системы)

Запускать из корня проекта:
    python patch_memory_embedding.py

Что делает:
  1. Создаёт studio/economy/memory_embedding.py
  2. Бэкапит studio/workshop/pipeline.py → pipeline.py.bak_embedding
  3. Патчит pipeline.py — после on_agent_done() записывает
     экономическое ощущение в sensory память агента

Суть Этапа 3:
  Числа (cost_usd, score) → текстовое ощущение:
    "heavy but successful"
    "cheap but unstable"
    "slow but precise"
    "costly mistake"
    "effortless win"

  Хранится в sensory_memory.json агента с тегом "economy".
  Это основа интуиции — агент ПОМНИТ не цифры, а ощущения.
"""

import shutil
from pathlib import Path

ROOT     = Path(__file__).resolve().parent
STUDIO   = ROOT / "studio"
ECONOMY  = STUDIO / "economy"
PIPELINE = STUDIO / "workshop" / "pipeline.py"
BAK      = STUDIO / "workshop" / "pipeline.py.bak_embedding"

# ═══════════════════════════════════════════════════════════
# НОВЫЙ ФАЙЛ: studio/economy/memory_embedding.py
# ═══════════════════════════════════════════════════════════

MEMORY_EMBEDDING_CODE = '''\
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
        print(f"[EMBEDDING] {agent_id} in {slot_id}: score={score} → \\"{feeling}\\"")
    return results
'''

# ═══════════════════════════════════════════════════════════
# ПАТЧ pipeline.py — вызов embed_all_agents после QA
# ═══════════════════════════════════════════════════════════

OLD_PIPELINE = """\
        # ══ Ministry: фиксируем исходы post-fact (Этапы 6-7) ══"""

NEW_PIPELINE = """\
        # ══ Memory Embedding: числа → ощущения (Этап 3) ══
        if _ECONOMY_ENABLED:
            try:
                from studio.economy import memory_embedding as _membed
                _fb_agents_scores = {
                    _wid: float(_wdata.get("score", 5.0))
                    for _wid, _wdata in _agents_fb.items()
                } if "_agents_fb" in dir() and _agents_fb else {}
                if not _fb_agents_scores:
                    # Fallback: читаем feedback напрямую
                    try:
                        from pathlib import Path as _P
                        import json as _J
                        _fp = _P("clients") / client_slug / "feedback.json"
                        if _fp.exists():
                            _fd = _J.loads(_fp.read_text(encoding="utf-8"))
                            _fb_agents_scores = {
                                _w: float(_d.get("score", 5.0))
                                for _w, _d in _fd.get("agents", {}).items()
                            }
                    except Exception:
                        pass
                if _fb_agents_scores:
                    _membed.embed_all_agents(
                        agents_scores=_fb_agents_scores,
                        slot_id=state.get("_slot_id", ""),
                        dept=state.get("active_dept", ""),
                    )
            except Exception as _emb_err:
                print(f"[EMBEDDING] Ошибка: {_emb_err}")
        # ══ END Memory Embedding ══

        # ══ Ministry: фиксируем исходы post-fact (Этапы 6-7) ══"""


# ═══════════════════════════════════════════════════════════
# ПРИМЕНЯЕМ
# ═══════════════════════════════════════════════════════════

def main():
    print("=" * 60)
    print("ПАТЧ: Этап 3 — Memory Embedding")
    print("=" * 60)
    print()

    # 1. Создаём memory_embedding.py
    target = ECONOMY / "memory_embedding.py"
    if target.exists():
        bak = target.with_suffix(".py.bak_embedding")
        shutil.copy2(target, bak)
        print(f"[BAK]  {target.name} → {bak.name}")
    target.write_text(MEMORY_EMBEDDING_CODE, encoding="utf-8")
    print(f"[OK]   Создан {target.relative_to(ROOT)}")

    # 2. Обновляем __init__.py — добавляем memory_embedding
    init_path = ECONOMY / "__init__.py"
    init_src = init_path.read_text(encoding="utf-8")
    if "memory_embedding" not in init_src:
        old_line = 'from studio.economy import ministry         # noqa: F401'
        new_line  = (
            'from studio.economy import ministry         # noqa: F401\n'
            'from studio.economy import memory_embedding  # noqa: F401'
        )
        init_src = init_src.replace(old_line, new_line)

        old_all = '__all__ = ["ledger", "cost_intuition", "ministry"]'
        new_all  = '__all__ = ["ledger", "cost_intuition", "ministry", "memory_embedding"]'
        init_src = init_src.replace(old_all, new_all)

        init_path.write_text(init_src, encoding="utf-8")
        print(f"[OK]   Обновлён economy/__init__.py")
    else:
        print(f"[SKIP] economy/__init__.py — memory_embedding уже есть")

    print()

    # 3. Патчим pipeline.py
    if not PIPELINE.exists():
        print(f"[ERR] {PIPELINE} не найден")
        return

    src = PIPELINE.read_text(encoding="utf-8")

    if "Memory Embedding" in src:
        print(f"[SKIP] pipeline.py — Memory Embedding уже встроен")
    elif OLD_PIPELINE not in src:
        print(f"[ERR] pipeline.py — не найдена точка вставки")
        print(f"      Ищем: '# ══ Ministry: фиксируем исходы post-fact'")
        print(f"      Убедись что patch_pipeline_economy.py уже был запущен")
        return
    else:
        shutil.copy2(PIPELINE, BAK)
        print(f"[BAK]  pipeline.py → {BAK.name}")
        src = src.replace(OLD_PIPELINE, NEW_PIPELINE, 1)
        PIPELINE.write_text(src, encoding="utf-8")
        print(f"[OK]   pipeline.py — Memory Embedding встроен")

    print()
    print("─" * 60)
    print("Готово! Что добавлено:")
    print()
    print("  studio/economy/memory_embedding.py")
    print("    build_embedding()   — числа → текстовое ощущение")
    print("    embed_to_sensory()  — пишет ощущение в sensory агента")
    print("    embed_all_agents()  — массовая запись после рана")
    print()
    print("  pipeline.py (post-fact после QA):")
    print("    score=8.5, slot=turbo → A03: \"heavy but successful\"")
    print("    score=3.0, slot=turbo → A07: \"costly mistake\"")
    print("    → записывается в sensory_memory.json агента")
    print("    → агент помнит ощущение, а не цифру")
    print()
    print("Статус Глубокого Резюме:")
    print("  Этап 1 — Billing Reality    ✅")
    print("  Этап 2 — Cost Intuition     ✅")
    print("  Этап 3 — Memory Embedding   ✅")
    print("  Этап 4 — Strategy Registry  ✅ (был)")
    print("  Этап 5 — Reflection Engine  ✅ (был)")
    print("  Этап 6 — Ministry Selection ✅")
    print("  Этапы 7-10                  ⬜ следующие итерации")


if __name__ == "__main__":
    main()
