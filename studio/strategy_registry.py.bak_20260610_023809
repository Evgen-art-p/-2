# studio/strategy_registry.py
"""
Strategy Registry — банк успешных стратегий агентов.

Когда ран завершается с высокой оценкой (score >= 8),
система фиксирует ЧТО сработало: какой агент, в каком слоте,
с какими параметрами задачи.

При следующем ране в том же слоте — агент получает подсказку:
"В похожей ситуации раньше сработало вот это..."

Два уровня стратегий:
  • slot_strategies  — работают только в конкретном слоте/цехе
  • global_strategies — работают везде (помечаются как transferable)

Файл хранения: studio/strategy_registry.json
"""

import json
import re
from pathlib import Path
from datetime import datetime

# ═══════════════════════════════════════════
# КОНФИГ
# ═══════════════════════════════════════════

REGISTRY_PATH = Path("studio") / "strategy_registry.json"

# Порог оценки для фиксации стратегии
STRATEGY_SCORE_THRESHOLD = 8.0

# Макс стратегий на агента в слоте
MAX_SLOT_STRATEGIES = 10

# Макс глобальных (transferable) стратегий на агента
MAX_GLOBAL_STRATEGIES = 5

# Сколько раз стратегия должна сработать чтобы стать transferable
TRANSFERABLE_MIN_WINS = 3


# ═══════════════════════════════════════════
# ХРАНИЛИЩЕ
# ═══════════════════════════════════════════

def _load_registry() -> dict:
    """Загружает реестр стратегий."""
    if REGISTRY_PATH.exists():
        try:
            return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {
        "version": 1,
        "total_wins": 0,
        "slots": {},       # slot_id → agent_id → [strategies]
        "global": {},      # agent_id → [transferable strategies]
        "updated_at": "",
    }


def _save_registry(data: dict):
    """Сохраняет реестр."""
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    data["updated_at"] = datetime.now().isoformat()
    REGISTRY_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


# ═══════════════════════════════════════════
# ЗАПИСЬ СТРАТЕГИЙ
# ═══════════════════════════════════════════

def record_strategy(
    agent_id: str,
    slot_id: str,
    score: float,
    result_summary: str,
    run_type: str = "",
    client_slug: str = "",
    problems: list = None,
):
    """
    Фиксирует успешную стратегию если score >= порога.

    agent_id:       кто отработал хорошо (A03, A07...)
    slot_id:        в каком слоте (turbo, living_book...)
    score:          оценка QA (0–10)
    result_summary: краткое описание результата (первые 300 симв.)
    run_type:       тип рана (turbo_pipeline, living_book_pipeline...)
    client_slug:    имя клиента (для контекста)
    problems:       список проблем (для понимания что НЕ делать)
    """
    if score < STRATEGY_SCORE_THRESHOLD:
        return  # Не фиксируем посредственные результаты

    registry = _load_registry()
    registry["total_wins"] = registry.get("total_wins", 0) + 1

    # ── Слотовые стратегии ──
    if slot_id:
        slots = registry.setdefault("slots", {})
        slot_agents = slots.setdefault(slot_id, {})
        agent_strategies = slot_agents.setdefault(agent_id, [])

        strategy = {
            "ts": datetime.now().isoformat(),
            "score": score,
            "run_type": run_type,
            "summary": result_summary[:300],
            "wins": 1,
            "transferable": False,
        }

        # Проверяем не дубль ли это (похожий run_type + похожий summary)
        merged = False
        for existing in agent_strategies:
            if (
                existing.get("run_type") == run_type
                and _similarity(existing.get("summary", ""), result_summary) > 0.6
            ):
                # Обновляем существующую — она подтверждена снова
                existing["wins"] = existing.get("wins", 1) + 1
                existing["score"] = round((existing["score"] + score) / 2, 1)
                existing["ts"] = strategy["ts"]
                # Если достаточно побед → помечаем как transferable
                if existing["wins"] >= TRANSFERABLE_MIN_WINS:
                    existing["transferable"] = True
                merged = True
                break

        if not merged:
            agent_strategies.append(strategy)

        # Лимит: оставляем топ по wins + score
        if len(agent_strategies) > MAX_SLOT_STRATEGIES:
            agent_strategies.sort(
                key=lambda s: (s.get("wins", 1), s.get("score", 0)),
                reverse=True,
            )
            slot_agents[agent_id] = agent_strategies[:MAX_SLOT_STRATEGIES]

    # ── Глобальные (transferable) стратегии ──
    # Попадают сюда только если wins >= порога
    global_strategies = registry.setdefault("global", {})
    agent_globals = global_strategies.setdefault(agent_id, [])

    # Собираем transferable из всех слотов этого агента
    all_slot_strategies = []
    for _, agents in registry.get("slots", {}).items():
        for sid, strats in agents.items():
            if sid == agent_id:
                all_slot_strategies.extend(
                    s for s in strats if s.get("transferable")
                )

    # Обновляем global из transferable
    for ts in all_slot_strategies:
        already_global = any(
            _similarity(g.get("summary", ""), ts.get("summary", "")) > 0.7
            for g in agent_globals
        )
        if not already_global:
            agent_globals.append({
                "ts": ts["ts"],
                "score": ts["score"],
                "summary": ts["summary"],
                "wins": ts.get("wins", TRANSFERABLE_MIN_WINS),
                "run_type": ts.get("run_type", ""),
            })

    # Лимит глобальных
    if len(agent_globals) > MAX_GLOBAL_STRATEGIES:
        agent_globals.sort(key=lambda s: s.get("wins", 1), reverse=True)
        global_strategies[agent_id] = agent_globals[:MAX_GLOBAL_STRATEGIES]

    _save_registry(registry)

    transferable_count = sum(
        1 for s in registry.get("slots", {}).get(slot_id or "", {}).get(agent_id, [])
        if s.get("transferable")
    )
    print(
        f"[STRATEGY] ✅ {agent_id} @ {slot_id or 'global'}: "
        f"score={score} → стратегия записана "
        f"(transferable: {transferable_count})"
    )


# ═══════════════════════════════════════════
# ЧТЕНИЕ СТРАТЕГИЙ
# ═══════════════════════════════════════════

def get_strategies(agent_id: str, slot_id: str = "") -> str:
    """
    Возвращает подсказки агенту на основе прошлых побед.

    Сначала — слотовые (если slot_id передан),
    потом — глобальные transferable.
    Итого не более 3 подсказок чтобы не засорять промпт.
    """
    registry = _load_registry()
    parts = []
    hints = []

    # 1. Слотовые стратегии — самые релевантные
    if slot_id:
        slot_agents = registry.get("slots", {}).get(slot_id, {})
        agent_strats = slot_agents.get(agent_id, [])

        # Сортируем: сначала многократно подтверждённые
        agent_strats_sorted = sorted(
            agent_strats,
            key=lambda s: (s.get("wins", 1), s.get("score", 0)),
            reverse=True,
        )

        for s in agent_strats_sorted[:2]:  # max 2 слотовых
            wins = s.get("wins", 1)
            score = s.get("score", 0)
            summary = s.get("summary", "")
            if summary:
                badge = f"[{wins}x побед, оценка {score}/10]"
                hints.append(f"  • {badge} {summary}")

    # 2. Глобальные transferable стратегии
    agent_globals = registry.get("global", {}).get(agent_id, [])
    agent_globals_sorted = sorted(
        agent_globals,
        key=lambda s: s.get("wins", 1),
        reverse=True,
    )

    for s in agent_globals_sorted[:1]:  # max 1 глобальная
        wins = s.get("wins", 1)
        score = s.get("score", 0)
        summary = s.get("summary", "")
        if summary:
            badge = f"[работает везде, {wins}x, оценка {score}/10]"
            hints.append(f"  • {badge} {summary}")

    if not hints:
        return ""

    slot_label = f" в цехе '{slot_id}'" if slot_id else ""
    parts.append(f"=== 🏆 СТРАТЕГИИ КОТОРЫЕ РАБОТАЮТ{slot_label} ===")
    parts.append("Из прошлого опыта — эти подходы давали высокие оценки:")
    parts.extend(hints)
    parts.append("Используй эти стратегии как ориентир, адаптируй под текущую задачу.")
    parts.append("=== КОНЕЦ СТРАТЕГИЙ ===")

    return "\n".join(parts)


def get_registry_summary() -> str:
    """Краткая сводка для логов и UI."""
    registry = _load_registry()
    total_wins = registry.get("total_wins", 0)
    slots = registry.get("slots", {})
    glob = registry.get("global", {})

    lines = [f"📚 Strategy Registry: {total_wins} побед"]

    for slot_id, agents in slots.items():
        for agent_id, strats in agents.items():
            transferable = sum(1 for s in strats if s.get("transferable"))
            lines.append(
                f"  {agent_id} @ {slot_id}: "
                f"{len(strats)} стратегий ({transferable} transferable)"
            )

    global_count = sum(len(v) for v in glob.values())
    if global_count:
        lines.append(f"  🌍 Глобальных: {global_count}")

    return "\n".join(lines)


# ═══════════════════════════════════════════
# УТИЛИТЫ
# ═══════════════════════════════════════════

def _similarity(a: str, b: str) -> float:
    """
    Грубая оценка похожести двух строк (0.0–1.0).
    Без внешних зависимостей — считаем пересечение слов.
    """
    if not a or not b:
        return 0.0

    def words(text):
        return set(re.findall(r'\w+', text.lower()))

    wa, wb = words(a), words(b)
    if not wa or not wb:
        return 0.0

    intersection = len(wa & wb)
    union = len(wa | wb)
    return intersection / union if union else 0.0
