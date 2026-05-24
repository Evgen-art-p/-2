# studio/conflict.py — УНИВЕРСАЛЬНАЯ СИСТЕМА КОНФЛИКТОВ (Этап 6, v2)
# Демон — единственный арбитр. QA — шлюз, не судья.
#
# Режимы:
#   "none"        — одиночный агент (дефолт)
#   "divergent"   — параллельные предложения → первое в мир → остальные в резерв
#   "adversarial" — агенты видят предложения друг друга → синтез → шлюз
#
# Философия:
#   Финализатор не выбирает "лучшего" — выпускает первую идею в реальность.
#   Победителя определяет Демон через 24ч по реакции зрителя.
#   Резерв привязан к run_id и ждёт сигнала Демона.
#   Мутации получают приоритет в резерве — источник новых паттернов.

import asyncio
import json
import random
import re
import time
from typing import Dict, List, Any
from pathlib import Path


async def run_conflict_phase(
    state: dict,
    phase_config: dict,
    build_context_fn,
    call_agent_fn,
    slot_id: str = "",
) -> Dict[str, Any]:
    """
    Универсальный вход для конфликтной фазы.

    Returns dict с ключами:
        released_id, released_result, all_proposals,
        conflict_log, run_id,
        winner_id (алиас), winner_result (алиас)
    или None если conflict_mode == "none"
    """
    conflict_mode = phase_config.get("conflict_mode", "none")
    if conflict_mode == "none":
        return None

    agent_pool = phase_config.get("divergent_agents", phase_config.get("agents", []))
    if len(agent_pool) < 2:
        print(f"[CONFLICT] Недостаточно агентов: {agent_pool}")
        return None

    run_id = state.get("run_id") or f"{slot_id}_{phase_config.get('id', 'ph')}_{int(time.time())}"
    state["_conflict_run_id"] = run_id
    print(f"[CONFLICT] Запуск: mode={conflict_mode}, agents={agent_pool}, run_id={run_id}")

    proposals = await _run_parallel_proposals(state, agent_pool, build_context_fn, call_agent_fn, phase_config)

    if conflict_mode == "adversarial":
        proposals = await _adversarial_rounds(
            state, proposals, agent_pool, phase_config,
            build_context_fn, call_agent_fn,
            max_rounds=phase_config.get("adversarial_rounds", 2),
        )

    phase_id     = phase_config.get("id", "unknown")
    released_id  = _select_first_for_release(proposals, slot_id, phase_id)
    reserve_pool = _build_reserve_pool(proposals, released_id, slot_id, phase_id)
    conflict_log = _build_conflict_log(phase_id, slot_id, proposals, released_id, conflict_mode, run_id, state)

    _record_conflict(conflict_log, reserve_pool)

    mutation_count = sum(1 for v in reserve_pool.values() if v.get("is_mutation"))
    print(f"[CONFLICT] Шлюз открыт: {released_id} в мир (резерв={len(reserve_pool)}, мутаций={mutation_count})")

    released_result = proposals[released_id]
    return {
        "released_id":     released_id,
        "released_result": released_result,
        "all_proposals":   proposals,
        "conflict_log":    conflict_log,
        "run_id":          run_id,
        "winner_id":       released_id,       # обратная совместимость
        "winner_result":   released_result,   # обратная совместимость
    }


async def _run_parallel_proposals(state, agent_pool, build_context_fn, call_agent_fn, phase_config):
    """Запускает всех агентов пула параллельно."""
    async def _call_single(agent_id):
        ctx = build_context_fn(
            state=state,
            worker_id=agent_id,
            client_slug=state.get("client_slug", "_sandbox"),
            settings_ctx=_build_settings_from_state(state),
            files_ctx="",
            previous_output=state.get("_previous_output", ""),
            anchor_ctx=(
                "=== КОНФЛИКТНЫЙ РЕЖИМ ===\n"
                "Ты участвуешь в параллельной генерации идей. "
                "Предложи свой лучший вариант честно. "
                "Судья — реальный зритель, не внутренняя оценка.\n"
            ),
            run_mode=state.get("run_type", ""),
        )
        return agent_id, await call_agent_fn(state, agent_id, ctx)

    results   = await asyncio.gather(*[_call_single(a) for a in agent_pool])
    proposals = {}
    for agent_id, (human_text, meta, raw_result) in results:
        proposals[agent_id] = {"human_text": human_text, "meta": meta, "raw_result": raw_result}

    print(f"[CONFLICT] Получено {len(proposals)} предложений: {list(proposals.keys())}")
    return proposals


def _select_first_for_release(proposals, slot_id, phase_id):
    """
    Кто идёт первым в мир.
    1. Есть данные Демона → агент с лучшим avg_viral_score в этом слоте/фазе
    2. Нет данных → случайный выбор (не [0] — позиция не решает судьбу)
    """
    agent_ids = list(proposals.keys())
    try:
        from studio.economy.conflict_memory import get_slot_daemon_culture
        culture       = get_slot_daemon_culture(slot_id)
        phase_culture = [c for c in culture if c["phase_id"] == phase_id]
        if phase_culture:
            scores     = {c["agent_id"]: c["avg_viral_score"] for c in phase_culture}
            pool_scored = sorted([(a, scores.get(a, 0.0)) for a in agent_ids], key=lambda x: x[1], reverse=True)
            best = pool_scored[0][0]
            print(f"[CONFLICT] Культура Демона: {best} идёт первым (viral={scores.get(best, 0):.2f})")
            return best
    except Exception as e:
        print(f"[CONFLICT] Культура Демона недоступна: {e}")

    chosen = random.choice(agent_ids)
    print(f"[CONFLICT] Нет данных Демона — случайный выбор: {chosen}")
    return chosen


def _build_reserve_pool(proposals, released_id, slot_id, phase_id):
    """Формирует резерв: все идеи кроме выпущенной, с intent и is_mutation."""
    reserve = {}
    for agent_id, data in proposals.items():
        if agent_id == released_id:
            continue
        is_mut = _detect_mutation(agent_id, slot_id, phase_id)
        reserve[agent_id] = {
            "intent":      data["human_text"][:500],
            "human_text":  data["human_text"],
            "meta":        data.get("meta", {}),
            "is_mutation": is_mut,
        }
    return reserve


def _detect_mutation(agent_id, slot_id, phase_id):
    """
    Мутация = агент которого Демон исторически не выбирал в этом слоте/фазе.
    Или агент без истории — все новички потенциальные мутанты.
    Мутации получают приоритет в резерве.
    """
    try:
        from studio.economy.conflict_memory import get_slot_daemon_culture
        culture       = get_slot_daemon_culture(slot_id)
        phase_culture = [c for c in culture if c["phase_id"] == phase_id]
        if not phase_culture:
            return True
        known = {c["agent_id"] for c in phase_culture if c["count"] > 0}
        is_mut = agent_id not in known
        if is_mut:
            print(f"[CONFLICT] Мутация: {agent_id} (нет в истории Демона)")
        return is_mut
    except Exception:
        return False


async def _adversarial_rounds(state, proposals, agent_pool, phase_config, build_context_fn, call_agent_fn, max_rounds=2):
    """Агенты видят предложения друг друга и синтезируют. Возвращает обновлённые предложения."""
    current = dict(proposals)
    for round_num in range(1, max_rounds + 1):
        print(f"[CONFLICT] Adversarial раунд {round_num}/{max_rounds}")
        new_proposals = {}
        for agent_id in agent_pool:
            others_text = "".join(
                f"\n--- Вариант {oid} ---\n{d['human_text'][:500]}\n"
                for oid, d in current.items() if oid != agent_id
            )
            critique_prompt = (
                f"=== РАУНД {round_num}: СИНТЕЗ ===\n"
                f"Твой предыдущий вариант:\n{current[agent_id]['human_text'][:500]}\n\n"
                f"Варианты коллег:\n{others_text}\n\n"
                f"Возьми сильное из чужих вариантов, усиль своё. "
                f"Предложи финальный синтез. Судья — реальный зритель."
            )
            ctx = build_context_fn(
                state=state, worker_id=agent_id,
                client_slug=state.get("client_slug", "_sandbox"),
                settings_ctx=_build_settings_from_state(state),
                files_ctx="", previous_output=critique_prompt,
                anchor_ctx="", run_mode=state.get("run_type", ""),
            )
            _, meta, raw = await call_agent_fn(state, agent_id, ctx)
            new_proposals[agent_id] = {"human_text": _clean_response(raw), "meta": meta, "raw_result": raw}
        current = new_proposals
    return current


def _build_conflict_log(phase_id, slot_id, proposals, released_id, conflict_mode, run_id, state):
    return {
        "timestamp":         time.time(),
        "run_id":            run_id,
        "slot_id":           slot_id,
        "phase_id":          phase_id,
        "conflict_mode":     conflict_mode,
        "agent_pool":        list(proposals.keys()),
        "released_id":       released_id,
        "reserve_size":      len(proposals) - 1,
        "proposals_summary": {aid: d["human_text"][:200] for aid, d in proposals.items()},
        "client_slug":       state.get("client_slug", ""),
        "run_type":          state.get("run_type", ""),
    }


def _record_conflict(conflict_log, reserve_pool):
    try:
        from studio.economy import conflict_memory as _cm
        _cm.record_conflict_outcome(
            phase_id=          conflict_log["phase_id"],
            slot_id=           conflict_log["slot_id"],
            proposals=         conflict_log["proposals_summary"],
            released_agent_id= conflict_log["released_id"],
            conflict_mode=     conflict_log["conflict_mode"],
            run_id=            conflict_log["run_id"],
            reserve_pool=      reserve_pool,
        )
        print(f"[CONFLICT] Конфликт + резерв записаны (run_id={conflict_log['run_id']})")
    except Exception as e:
        print(f"[CONFLICT] Ошибка записи: {e}")
        _fallback_record(conflict_log)


def _fallback_record(conflict_log):
    try:
        log_path = Path("studio/economy/data/conflict_log.jsonl")
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(conflict_log, ensure_ascii=False) + "\n")
    except Exception:
        pass


def _build_settings_from_state(state):
    s = state.get("settings", {})
    return f"Format: {s.get('format', 'unknown')}\nDuration: {s.get('duration', '?')}\nStyle: {s.get('style', '?')}\n"


def _clean_response(text):
    for pat in [r'\nINSIGHT:\s*.+', r'WINNER:\s*.+\n*', r'REASON:\s*.+\n*', r'LOSERS:\s*.+\n*']:
        text = re.sub(pat, '', text)
    return text.strip()
