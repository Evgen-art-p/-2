# studio/economy/ministry.py
"""
ЭТАПЫ 6-7 — MINISTRY AS SELECTION · v2.0 «Закон двух валют» (Спринт 44)

Министерство НЕ принимает решения во время рана. Только post-fact:
фиксирует исходы, усиливает успешные паттерны, ослабляет неуспешные,
формирует режим для следующего рана. Естественный отбор, не контроль.

ДВЕ ВАЛЮТЫ (одна шкала 0–10, два источника):
  CHAIN (source="chain", 0–6.0) — ремесло. Детерминированная оценка
    цепочки после QA. Потолок 6.0 = «выжил, сделал по ТЗ, чисто».
    Успех = score >= 6.0 (чистая шестёрка). Провал = score < 4.0.
    Писатель: workshop/pipeline.py после QA-агента.
  REAL (source="real", 0–10) — зритель. Реальные метрики после
    публикации (real_viral_score) или живой QA Шефа.
    Успех = score >= 7.0. Провал = score < 5.0.
    Писатель: economy/metrics_daemon.py.

Манифест: Reward > Punishment. Режим generous открывает ТОЛЬКО
real-успех — скрипт не имеет права чеканить девятки.

Хранение: studio/economy/data/ministry.json
"""

import json
import threading
from pathlib import Path

from studio.config import BASE_DIR

DATA_DIR      = BASE_DIR / "studio" / "economy" / "data"
MINISTRY_FILE = DATA_DIR / "ministry.json"
_lock = threading.Lock()

# Пороги валют
CHAIN_SUCCESS = 6.0   # чистое ремесло
CHAIN_FAIL    = 4.0   # развал цепочки
REAL_SUCCESS  = 7.0   # зритель отозвался
REAL_FAIL     = 5.0   # глухо


def _ensure() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def _load() -> dict:
    if not MINISTRY_FILE.exists():
        return {}
    try:
        return json.loads(MINISTRY_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save(data: dict) -> None:
    _ensure()
    MINISTRY_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _key(agent_id: str, slot_id: str) -> str:
    return f"{agent_id}::{slot_id}"


def _empty_record(agent_id: str, slot_id: str) -> dict:
    return {
        "agent_id":       agent_id,
        "slot_id":        slot_id,
        "runs_total":     0,
        "runs_success":   0,
        "runs_fail":      0,
        "cost_success":   0.0,
        "cost_fail":      0.0,
        "score_sum":      0.0,
        "economy_rating": 1.0,
        "mode":           "normal",
        # Спринт 44 — раздельные счётчики валют
        "chain": {"runs": 0, "success": 0, "fail": 0},
        "real":  {"runs": 0, "success": 0, "fail": 0},
        "last_source": "",
        "last_score":  None,
    }


def record_outcome(
    agent_id: str,
    slot_id: str,
    score: float,
    cost_usd: float,
    source: str = "chain",
) -> None:
    """
    Фиксирует исход рана. Вызывается post-fact.

    Args:
        agent_id: ID агента
        slot_id:  ID цеха
        score:    Оценка (chain: 0–6.0; real: 0–10)
        cost_usd: Стоимость РАНА (дельта, не пожизненная сумма!)
        source:   "chain" (pipeline после QA) | "real" (Metrics Daemon)
    """
    if source not in ("chain", "real"):
        source = "chain"

    with _lock:
        data = _load()
        k = _key(agent_id, slot_id)

        if k not in data:
            data[k] = _empty_record(agent_id, slot_id)
        r = data[k]
        # миграция старых записей (до Спринта 44)
        r.setdefault("chain", {"runs": 0, "success": 0, "fail": 0})
        r.setdefault("real",  {"runs": 0, "success": 0, "fail": 0})

        r["runs_total"] += 1
        r["score_sum"]  += score
        r["last_source"] = source
        r["last_score"]  = score

        bucket = r[source]
        bucket["runs"] += 1

        if source == "chain":
            ok, bad = (score >= CHAIN_SUCCESS), (score < CHAIN_FAIL)
        else:
            ok, bad = (score >= REAL_SUCCESS), (score < REAL_FAIL)

        if ok:
            bucket["success"]  += 1
            r["runs_success"]  += 1
            r["cost_success"]  += cost_usd
        elif bad:
            bucket["fail"]     += 1
            r["runs_fail"]     += 1
            r["cost_fail"]     += cost_usd

        r["economy_rating"] = _calc_rating(r)
        r["mode"]           = _calc_mode(r)
        _save(data)


def get_agent_stats(agent_id: str, slot_id: str) -> dict:
    """Статистика агента в цехе."""
    return _load().get(_key(agent_id, slot_id), {
        "agent_id": agent_id, "slot_id": slot_id,
        "runs_total": 0, "economy_rating": 1.0, "mode": "normal",
    })


def get_mode(agent_id: str, slot_id: str) -> str:
    """Режим для следующего рана: frugal | normal | generous."""
    return get_agent_stats(agent_id, slot_id).get("mode", "normal")


def get_prompt_hint(agent_id: str, slot_id: str) -> str:
    """Текстовый блок от Министерства для промпта агента.

    Манифест: «Не наказывай жёстко — получится забитый отличник».
    Frugal говорит про экономику путей, не про слабость агента.
    """
    stats = get_agent_stats(agent_id, slot_id)
    if stats.get("runs_total", 0) < 3:
        return ""  # мало данных — молчим

    mode = stats.get("mode", "normal")
    return {
        "frugal":   "[МИНИСТЕРСТВО] Последние раны не окупались. Ищи более экономные пути: меньше токенов — точнее результат. Качество держи, расход режь.",
        "normal":   "",
        "generous": "[МИНИСТЕРСТВО] Зритель отозвался на твою работу. Можешь позволить себе глубже проработать задачу.",
    }.get(mode, "")


def leaderboard(slot_id: str = None) -> list[dict]:
    """Рейтинг агентов по экономической эффективности."""
    records = list(_load().values())
    if slot_id:
        records = [r for r in records if r.get("slot_id") == slot_id]
    return sorted(records, key=lambda r: r.get("economy_rating", 1.0), reverse=True)


def _calc_rating(r: dict) -> float:
    total = r["runs_total"]
    if total == 0:
        return 1.0
    success_rate = r["runs_success"] / total
    avg_sc = r["cost_success"] / r["runs_success"] if r["runs_success"] else 0.0
    avg_fc = r["cost_fail"]    / r["runs_fail"]    if r["runs_fail"]    else 0.0
    penalty = min(0.3, avg_fc / avg_sc * 0.15) if avg_sc > 0 and avg_fc > 0 else 0.0
    return round(max(0.1, min(2.0, 0.5 + success_rate * 1.5 - penalty)), 3)


def _calc_mode(r: dict) -> str:
    """frugal | normal | generous.

    Закон двух валют: generous открывает ТОЛЬКО real-успех (зритель/Шеф).
    Чистое ремесло (серия chain-6.0) держит normal с высоким рейтингом —
    девятки скрипт не чеканит.
    """
    if r["runs_total"] < 3:
        return "normal"
    rating = r["economy_rating"]
    real_success = r.get("real", {}).get("success", 0)
    if rating >= 1.4 and real_success >= 1:
        return "generous"
    if rating <= 0.6:
        return "frugal"
    return "normal"
