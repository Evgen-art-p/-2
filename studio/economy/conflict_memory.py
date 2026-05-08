# studio/economy/conflict_memory.py — ПАМЯТЬ КОНФЛИКТОВ (Этап 6)
# Записывает исходы конфликтов для будущего анализа Ministry

import json
import time
from pathlib import Path
from typing import Dict, Optional


DATA_DIR = Path(__file__).parent / "data"
CONFLICT_LOG_PATH = DATA_DIR / "conflict_log.jsonl"
CONFLICT_STATS_PATH = DATA_DIR / "conflict_stats.json"


def record_conflict_outcome(
    phase_id: str,
    slot_id: str,
    proposals: Dict[str, str],
    winner_id: str,
    conflict_mode: str,
) -> dict:
    """
    Записывает исход конфликта.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    log_entry = {
        "timestamp": time.time(),
        "phase_id": phase_id,
        "slot_id": slot_id,
        "conflict_mode": conflict_mode,
        "pool_size": len(proposals),
        "agents": list(proposals.keys()),
        "winner_id": winner_id,
        "proposals": proposals,
    }
    
    with open(CONFLICT_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
    
    _update_stats(log_entry)
    
    return log_entry


def _update_stats(log_entry: dict):
    """Обновляет агрегированную статистику."""
    stats = {}
    if CONFLICT_STATS_PATH.exists():
        try:
            stats = json.loads(CONFLICT_STATS_PATH.read_text(encoding="utf-8"))
        except Exception:
            stats = {}
    
    winner_id = log_entry["winner_id"]
    slot_id = log_entry["slot_id"]
    phase_id = log_entry["phase_id"]
    
    key = f"{slot_id}::{phase_id}::{winner_id}"
    
    if "wins" not in stats:
        stats["wins"] = {}
    stats["wins"][key] = stats["wins"].get(key, 0) + 1
    
    stats["total_conflicts"] = stats.get("total_conflicts", 0) + 1
    stats["last_updated"] = time.time()
    
    CONFLICT_STATS_PATH.write_text(
        json.dumps(stats, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def get_conflict_stats(
    slot_id: Optional[str] = None,
    phase_id: Optional[str] = None,
) -> dict:
    """Возвращает статистику конфликтов с фильтрацией."""
    if not CONFLICT_STATS_PATH.exists():
        return {"total_conflicts": 0, "wins": {}}
    
    stats = json.loads(CONFLICT_STATS_PATH.read_text(encoding="utf-8"))
    
    if slot_id or phase_id:
        filtered = {}
        for key, count in stats.get("wins", {}).items():
            key_slot, key_phase, agent = key.split("::")
            if (not slot_id or key_slot == slot_id) and \
               (not phase_id or key_phase == phase_id):
                filtered[key] = count
        return {
            "total_conflicts": stats.get("total_conflicts", 0),
            "wins": filtered,
            "filtered_by": {"slot_id": slot_id, "phase_id": phase_id},
        }
    
    return stats


def get_agent_win_rate(agent_id: str, slot_id: Optional[str] = None) -> float:
    """Возвращает win rate агента (0.0 - 1.0)."""
    stats = get_conflict_stats(slot_id=slot_id)
    wins = stats.get("wins", {})
    
    agent_wins = sum(
        count for key, count in wins.items()
        if key.endswith(f"::{agent_id}")
    )
    
    total = stats.get("total_conflicts", 1) or 1
    return round(agent_wins / total, 3)