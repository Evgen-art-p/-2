"""
patch_conflict_memory.py — Спринт 22
Переписывает studio/economy/conflict_memory.py

Что меняется:
  - record_conflict_outcome() получает run_id + reserve_pool
  - save_run_reserve()    — сохраняет резерв привязанный к run_id
  - get_run_reserve()     — Демон достаёт резерв по run_id
  - consume_from_reserve() — достаёт следующую идею, обновляет резерв
  - close_run_reserve()   — хороший сигнал: резерв → interaction_log как опыт
  - _update_stats()       — расширен: released_agent + reserve_size

Запуск: python patch_conflict_memory.py
"""

import shutil
from pathlib import Path

TARGET = Path("studio/economy/conflict_memory.py")

NEW_CONTENT = '''# studio/economy/conflict_memory.py — ПАМЯТЬ КОНФЛИКТОВ (Этап 6, v2)
# Резерв идей привязан к run_id. Демон — единственный арбитр выживания.
#
# Философия:
#   conflict.py выпускает первую идею в мир (шлюз, не судья).
#   Остальные живут в reserve_pool этого рана.
#   Демон возвращает сигнал через 24ч:
#     хороший → close_run_reserve() → резерв уходит в interaction_log как опыт
#     плохой  → consume_from_reserve() → следующая идея идёт в мир
#   Проигравших нет — есть генетический резерв и накопленная мудрость.

import json
import time
from pathlib import Path
from typing import Dict, List, Optional


DATA_DIR = Path(__file__).parent / "data"
CONFLICT_LOG_PATH    = DATA_DIR / "conflict_log.jsonl"
CONFLICT_STATS_PATH  = DATA_DIR / "conflict_stats.json"
RESERVE_DIR          = DATA_DIR / "reserves"          # per-run резервы
INTERACTION_LOG_DIR  = DATA_DIR                        # interaction_log_{slot}.jsonl


# ═══════════════════════════════════════════════════════════
# ЗАПИСЬ КОНФЛИКТА — вызывается из conflict.py
# ═══════════════════════════════════════════════════════════

def record_conflict_outcome(
    phase_id: str,
    slot_id: str,
    proposals: Dict[str, str],
    released_agent_id: str,
    conflict_mode: str,
    run_id: str = "",
    reserve_pool: Optional[Dict[str, dict]] = None,
) -> dict:
    """
    Записывает исход конфликта.

    released_agent_id: агент чья идея выпущена первой (не "победитель")
    reserve_pool:      остальные идеи — {agent_id: {intent, human_text, meta}}
                       если None — резерв не сохраняется (старый режим)
    run_id:            уникальный ID рана для привязки резерва
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    log_entry = {
        "timestamp":         time.time(),
        "run_id":            run_id,
        "phase_id":          phase_id,
        "slot_id":           slot_id,
        "conflict_mode":     conflict_mode,
        "pool_size":         len(proposals),
        "agents":            list(proposals.keys()),
        "released_agent_id": released_agent_id,
        "reserve_size":      len(reserve_pool) if reserve_pool else 0,
        "proposals_summary": proposals,
    }

    with open(CONFLICT_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry, ensure_ascii=False) + "\\n")

    _update_stats(log_entry)

    # Сохраняем резерв если есть
    if reserve_pool and run_id:
        save_run_reserve(
            run_id=run_id,
            slot_id=slot_id,
            phase_id=phase_id,
            released_agent_id=released_agent_id,
            reserve_pool=reserve_pool,
        )

    return log_entry


# ═══════════════════════════════════════════════════════════
# РЕЗЕРВ — хранение, доступ, потребление
# ═══════════════════════════════════════════════════════════

def save_run_reserve(
    run_id: str,
    slot_id: str,
    phase_id: str,
    released_agent_id: str,
    reserve_pool: Dict[str, dict],
) -> Path:
    """
    Сохраняет резерв идей для конкретного рана.
    Файл: economy/data/reserves/{run_id}_{phase_id}.json

    reserve_pool структура:
    {
      "A02": {
        "intent":     "структура + ключевые решения идеи",  # не готовый текст
        "human_text": "полный текст если нужен для аварийного случая",
        "meta":       {...},
        "is_mutation": False,   # флаг — идёт против культурного поля
      },
      ...
    }
    """
    RESERVE_DIR.mkdir(parents=True, exist_ok=True)
    reserve_path = RESERVE_DIR / f"{run_id}_{phase_id}.json"

    reserve_data = {
        "run_id":             run_id,
        "slot_id":            slot_id,
        "phase_id":           phase_id,
        "released_agent_id":  released_agent_id,
        "created_at":         time.time(),
        "status":             "waiting",    # waiting | consumed | closed
        "daemon_checked_at":  None,
        "pool":               reserve_pool, # {agent_id: idea_data}
        "consumed_order":     [],           # порядок в котором доставали идеи
    }

    reserve_path.write_text(
        json.dumps(reserve_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"[RESERVE] 💾 Сохранён резерв {run_id}/{phase_id}: {len(reserve_pool)} идей")
    return reserve_path


def get_run_reserve(run_id: str, phase_id: str) -> Optional[dict]:
    """
    Достаёт резерв по run_id и phase_id.
    Вызывается из metrics_daemon.py когда пришёл сигнал от Демона.
    Возвращает None если резерв не найден или уже закрыт.
    """
    reserve_path = RESERVE_DIR / f"{run_id}_{phase_id}.json"
    if not reserve_path.exists():
        return None

    try:
        data = json.loads(reserve_path.read_text(encoding="utf-8"))
    except Exception:
        return None

    if data.get("status") == "closed":
        print(f"[RESERVE] Резерв {run_id}/{phase_id} уже закрыт (хороший сигнал был)")
        return None

    return data


def consume_from_reserve(run_id: str, phase_id: str) -> Optional[dict]:
    """
    Плохой сигнал Демона — достаёт следующую идею из резерва.
    Возвращает идею (intent + контекст) для лёгкого прогона финализатора.
    Обновляет файл резерва.

    Возвращает:
    {
      "agent_id":   "A02",
      "intent":     "структура идеи",
      "human_text": "полный текст если нужен",
      "meta":       {...},
      "is_mutation": bool,
      "attempt_number": 2,   # сколько раз уже пробовали
      "reserve_remaining": 1, # сколько ещё осталось
    }
    или None если резерв пуст.
    """
    reserve = get_run_reserve(run_id, phase_id)
    if not reserve:
        return None

    pool = reserve.get("pool", {})
    consumed = reserve.get("consumed_order", [])

    # Уже выпущенный и потреблённые — пропускаем
    skip = set(consumed) | {reserve.get("released_agent_id", "")}
    available = {k: v for k, v in pool.items() if k not in skip}

    if not available:
        print(f"[RESERVE] Резерв {run_id}/{phase_id} исчерпан")
        return None

    # Приоритет: сначала мутации (is_mutation=True), потом остальные
    mutations = {k: v for k, v in available.items() if v.get("is_mutation")}
    next_agent_id, next_idea = next(
        iter(mutations.items()) if mutations else iter(available.items())
    )

    # Обновляем резерв
    consumed.append(next_agent_id)
    reserve["consumed_order"] = consumed
    reserve["daemon_checked_at"] = time.time()
    reserve["status"] = "waiting"  # остаётся waiting пока не закроем

    reserve_path = RESERVE_DIR / f"{run_id}_{phase_id}.json"
    reserve_path.write_text(
        json.dumps(reserve, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    remaining = len(available) - 1
    attempt = len(consumed) + 1  # +1 потому что первый выпуск не в consumed

    print(
        f"[RESERVE] 🔄 Достаю из резерва {run_id}/{phase_id}: "
        f"агент={next_agent_id}, "
        f"мутация={next_idea.get('is_mutation', False)}, "
        f"попытка={attempt}, осталось={remaining}"
    )

    return {
        "agent_id":          next_agent_id,
        "intent":            next_idea.get("intent", ""),
        "human_text":        next_idea.get("human_text", ""),
        "meta":              next_idea.get("meta", {}),
        "is_mutation":       next_idea.get("is_mutation", False),
        "attempt_number":    attempt,
        "reserve_remaining": remaining,
        "slot_id":           reserve.get("slot_id", ""),
        "phase_id":          phase_id,
        "run_id":            run_id,
    }


def close_run_reserve(
    run_id: str,
    phase_id: str,
    winning_agent_id: str,
    viral_score: float,
    slot_id: str = "",
) -> bool:
    """
    Хороший сигнал Демона — закрывает резерв.
    Всё что было в резерве уходит в interaction_log как накопленный опыт.
    Winning_agent_id — тот чья идея выжила у Демона.

    Возвращает True если успешно закрыт.
    """
    reserve = get_run_reserve(run_id, phase_id)
    if not reserve:
        return False

    _slot = slot_id or reserve.get("slot_id", "unknown")

    # Пишем в interaction_log — весь резерв как опыт
    log_path = INTERACTION_LOG_DIR / f"interaction_log_{_slot}.jsonl"
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            # Победившая идея
            winner_entry = {
                "ts":              _iso_now(),
                "run_id":          run_id,
                "phase_id":        phase_id,
                "slot_id":         _slot,
                "event":           "daemon_approved",
                "agent_id":        winning_agent_id,
                "viral_score":     round(viral_score, 3),
                "is_mutation":     reserve["pool"].get(
                                     winning_agent_id, {}
                                   ).get("is_mutation", False),
                "attempt_number":  len(reserve.get("consumed_order", [])) + 1,
            }
            f.write(json.dumps(winner_entry, ensure_ascii=False) + "\\n")

            # Резервные идеи — как альтернативный опыт
            pool = reserve.get("pool", {})
            skip = {winning_agent_id}
            for agent_id, idea in pool.items():
                if agent_id in skip:
                    continue
                alt_entry = {
                    "ts":          _iso_now(),
                    "run_id":      run_id,
                    "phase_id":    phase_id,
                    "slot_id":     _slot,
                    "event":       "reserve_experience",
                    "agent_id":    agent_id,
                    "intent":      idea.get("intent", "")[:300],
                    "is_mutation": idea.get("is_mutation", False),
                    "was_tried":   agent_id in reserve.get("consumed_order", []),
                }
                f.write(json.dumps(alt_entry, ensure_ascii=False) + "\\n")

        print(f"[RESERVE] ✅ Закрыт резерв {run_id}/{phase_id}, опыт записан в {log_path.name}")
    except Exception as e:
        print(f"[RESERVE] ⚠️ Ошибка записи в interaction_log: {e}")

    # Помечаем резерв закрытым
    reserve["status"] = "closed"
    reserve["closed_at"] = time.time()
    reserve["winning_agent_id"] = winning_agent_id
    reserve["viral_score"] = round(viral_score, 3)

    reserve_path = RESERVE_DIR / f"{run_id}_{phase_id}.json"
    reserve_path.write_text(
        json.dumps(reserve, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # Обновляем stats — отмечаем реального победителя по Демону
    _update_daemon_win(
        slot_id=_slot,
        phase_id=phase_id,
        winning_agent_id=winning_agent_id,
        viral_score=viral_score,
        is_mutation=reserve["pool"].get(winning_agent_id, {}).get("is_mutation", False),
    )

    return True


# ═══════════════════════════════════════════════════════════
# СТАТИСТИКА
# ═══════════════════════════════════════════════════════════

def _update_stats(log_entry: dict):
    """Обновляет агрегированную статистику."""
    stats = {}
    if CONFLICT_STATS_PATH.exists():
        try:
            stats = json.loads(CONFLICT_STATS_PATH.read_text(encoding="utf-8"))
        except Exception:
            stats = {}

    released_id = log_entry.get("released_agent_id", log_entry.get("winner_id", ""))
    slot_id     = log_entry["slot_id"]
    phase_id    = log_entry["phase_id"]

    # Ключ: released (не winner — это шлюз, не судья)
    key = f"{slot_id}::{phase_id}::{released_id}"
    if "released" not in stats:
        stats["released"] = {}
    stats["released"][key] = stats["released"].get(key, 0) + 1

    # Совместимость со старым кодом (wins остаётся)
    if "wins" not in stats:
        stats["wins"] = {}
    stats["wins"][key] = stats["wins"].get(key, 0) + 1

    stats["total_conflicts"]    = stats.get("total_conflicts", 0) + 1
    stats["last_updated"]       = time.time()

    CONFLICT_STATS_PATH.write_text(
        json.dumps(stats, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _update_daemon_win(
    slot_id: str,
    phase_id: str,
    winning_agent_id: str,
    viral_score: float,
    is_mutation: bool = False,
):
    """
    Отдельная статистика побед по Демону.
    Это и есть реальная культура цеха — что выжило у зрителя.
    """
    stats = {}
    if CONFLICT_STATS_PATH.exists():
        try:
            stats = json.loads(CONFLICT_STATS_PATH.read_text(encoding="utf-8"))
        except Exception:
            stats = {}

    if "daemon_wins" not in stats:
        stats["daemon_wins"] = {}

    key = f"{slot_id}::{phase_id}::{winning_agent_id}"
    entry = stats["daemon_wins"].get(key, {
        "count": 0,
        "total_viral_score": 0.0,
        "mutations": 0,
    })
    entry["count"]             += 1
    entry["total_viral_score"] += viral_score
    entry["avg_viral_score"]   = round(
        entry["total_viral_score"] / entry["count"], 3
    )
    if is_mutation:
        entry["mutations"] += 1

    stats["daemon_wins"][key]  = entry
    stats["last_updated"]      = time.time()

    CONFLICT_STATS_PATH.write_text(
        json.dumps(stats, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    marker = "🧬 МУТАЦИЯ" if is_mutation else "✅"
    print(
        f"[RESERVE] {marker} Демон утвердил: {winning_agent_id} "
        f"в {slot_id}/{phase_id}, viral={viral_score}"
    )


# ═══════════════════════════════════════════════════════════
# ПУБЛИЧНЫЙ API — запросы
# ═══════════════════════════════════════════════════════════

def get_conflict_stats(
    slot_id: Optional[str] = None,
    phase_id: Optional[str] = None,
) -> dict:
    """Возвращает статистику конфликтов с фильтрацией."""
    if not CONFLICT_STATS_PATH.exists():
        return {"total_conflicts": 0, "wins": {}, "daemon_wins": {}}

    stats = json.loads(CONFLICT_STATS_PATH.read_text(encoding="utf-8"))

    if slot_id or phase_id:
        def _filter(d: dict) -> dict:
            return {
                k: v for k, v in d.items()
                if (not slot_id or k.startswith(f"{slot_id}::")) and
                   (not phase_id or f"::{phase_id}::" in k)
            }
        return {
            "total_conflicts": stats.get("total_conflicts", 0),
            "wins":            _filter(stats.get("wins", {})),
            "released":        _filter(stats.get("released", {})),
            "daemon_wins":     _filter(stats.get("daemon_wins", {})),
            "filtered_by":     {"slot_id": slot_id, "phase_id": phase_id},
        }

    return stats


def get_agent_win_rate(agent_id: str, slot_id: Optional[str] = None) -> float:
    """
    Win rate агента по реальным Демон-победам.
    Если daemon_wins пуст (до первого рана) — fallback на released.
    """
    stats = get_conflict_stats(slot_id=slot_id)

    daemon_wins = stats.get("daemon_wins", {})
    if daemon_wins:
        agent_daemon_wins = sum(
            v.get("count", 0) for k, v in daemon_wins.items()
            if k.endswith(f"::{agent_id}")
        )
        total = stats.get("total_conflicts", 1) or 1
        return round(agent_daemon_wins / total, 3)

    # Fallback: старая логика через released
    wins = stats.get("wins", {})
    agent_wins = sum(
        count for key, count in wins.items()
        if key.endswith(f"::{agent_id}")
    )
    total = stats.get("total_conflicts", 1) or 1
    return round(agent_wins / total, 3)


def get_slot_daemon_culture(slot_id: str) -> List[dict]:
    """
    Возвращает культуру цеха по данным Демона — что реально выживало у зрителя.
    Используется field_tracker.py как источник правды вместо internal QA.

    Возвращает список:
    [
      {
        "agent_id": "A03",
        "phase_id": "phase_2",
        "count": 5,
        "avg_viral_score": 0.72,
        "mutations": 1,
      },
      ...
    ]
    сортировка: avg_viral_score DESC
    """
    stats = get_conflict_stats(slot_id=slot_id)
    daemon_wins = stats.get("daemon_wins", {})

    result = []
    for key, entry in daemon_wins.items():
        parts = key.split("::")
        if len(parts) < 3:
            continue
        s_slot, s_phase, s_agent = parts[0], parts[1], parts[2]
        if s_slot != slot_id:
            continue
        result.append({
            "agent_id":        s_agent,
            "phase_id":        s_phase,
            "count":           entry.get("count", 0),
            "avg_viral_score": entry.get("avg_viral_score", 0.0),
            "mutations":       entry.get("mutations", 0),
        })

    result.sort(key=lambda x: x["avg_viral_score"], reverse=True)
    return result


def list_open_reserves(slot_id: Optional[str] = None) -> List[dict]:
    """
    Возвращает все незакрытые резервы (ждут Демона).
    Используется metrics_daemon.py для обхода.
    """
    if not RESERVE_DIR.exists():
        return []

    result = []
    for f in RESERVE_DIR.glob("*.json"):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        if data.get("status") == "closed":
            continue
        if slot_id and data.get("slot_id") != slot_id:
            continue
        result.append({
            "run_id":            data.get("run_id"),
            "phase_id":          data.get("phase_id"),
            "slot_id":           data.get("slot_id"),
            "created_at":        data.get("created_at"),
            "reserve_remaining": len(data.get("pool", {})) - len(data.get("consumed_order", [])) - 1,
            "status":            data.get("status"),
        })

    return result


# ═══════════════════════════════════════════════════════════
# УТИЛИТЫ
# ═══════════════════════════════════════════════════════════

def _iso_now() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()
'''


def apply_patch():
    if not TARGET.exists():
        print(f"[PATCH] ❌ Файл не найден: {TARGET}")
        return False

    # Бэкап
    bak = TARGET.with_suffix(f".bak_sprint22")
    shutil.copy2(TARGET, bak)
    print(f"[PATCH] 📦 Бэкап: {bak}")

    TARGET.write_text(NEW_CONTENT, encoding="utf-8")
    print(f"[PATCH] ✅ conflict_memory.py обновлён — резерв + Демон-культура")

    # Проверка синтаксиса
    import subprocess
    result = subprocess.run(
        ["python", "-m", "py_compile", str(TARGET)],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        print("[PATCH] ✅ Синтаксис OK")
    else:
        print(f"[PATCH] ❌ Синтаксис ERROR:\n{result.stderr}")
        print("[PATCH] 🔄 Восстанавливаю бэкап...")
        shutil.copy2(bak, TARGET)
        return False

    return True


if __name__ == "__main__":
    apply_patch()
