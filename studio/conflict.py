# studio/conflict.py — УНИВЕРСАЛЬНАЯ СИСТЕМА КОНФЛИКТОВ (Этап 6)
# ══ Глубокое Резюме: конфликты = генератор разнообразия ══
#
# Поддерживает 3 режима:
#   "none"       — обычный одиночный агент (дефолт)
#   "divergent"  — параллельные提案ы → QA выбирает победителя
#   "adversarial" — агенты видят提案ы друг друга → спорят → синтез
#
# Интеграция: CartridgeRunner.run_phase() вызывает run_conflict_phase()
# если phase_config содержит "conflict_mode" != "none"

import asyncio
import json
import re
import time
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path


# ══════════════════════════════════════════════════════════════
# ОСНОВНАЯ ФУНКЦИЯ — ВЫЗЫВАЕТСЯ ИЗ CARTRIDGE RUNNER
# ══════════════════════════════════════════════════════════════

async def run_conflict_phase(
    state: dict,
    phase_config: dict,
    build_context_fn,
    call_agent_fn,
    slot_id: str = "",
) -> Dict[str, Any]:
    """
    Универсальный вход для конфликтной фазы.
    
    Args:
        state: состояние рантайма
        phase_config: конфиг фазы из manifest.json
        build_context_fn: build_agent_context() из pipeline.py
        call_agent_fn: call_agent() из pipeline.py
        slot_id: текущий slot_id
    
    Returns:
        {
            "winner_id": str,
            "winner_result": (human_text, meta, raw_result),
            "all_proposals": {agent_id: proposal_data},
            "conflict_log": {...}
        }
        или None если конфликт не нужен
    """
    conflict_mode = phase_config.get("conflict_mode", "none")
    
    if conflict_mode == "none":
        return None
    
    agent_pool = phase_config.get("divergent_agents", phase_config.get("agents", []))
    
    if len(agent_pool) < 2:
        print(f"[CONFLICT] ⚠️ Недостаточно агентов для конфликта: {agent_pool}")
        return None
    
    print(f"[CONFLICT] ⚔️ Запуск конфликтной фазы: mode={conflict_mode}, agents={agent_pool}")
    
    # ── Раунд 1: Параллельный запуск всех агентов ──
    proposals = await _run_parallel_proposals(
        state=state,
        agent_pool=agent_pool,
        build_context_fn=build_context_fn,
        call_agent_fn=call_agent_fn,
        phase_config=phase_config,
    )
    
    if conflict_mode == "divergent":
        winner_id = await _select_winner_qa(
            state=state,
            proposals=proposals,
            phase_config=phase_config,
            build_context_fn=build_context_fn,
            call_agent_fn=call_agent_fn,
        )
    
    elif conflict_mode == "adversarial":
        winner_id = await _adversarial_rounds(
            state=state,
            proposals=proposals,
            agent_pool=agent_pool,
            phase_config=phase_config,
            build_context_fn=build_context_fn,
            call_agent_fn=call_agent_fn,
            max_rounds=phase_config.get("adversarial_rounds", 2),
        )
    
    else:
        print(f"[CONFLICT] ⚠️ Неизвестный режим: {conflict_mode}")
        return None
    
    # ── Запись в conflict_memory ──
    winner_result = proposals[winner_id]
    conflict_log = _build_conflict_log(
        phase_id=phase_config.get("id", "unknown"),
        slot_id=slot_id,
        proposals=proposals,
        winner_id=winner_id,
        conflict_mode=conflict_mode,
        state=state,
    )
    
    _record_conflict(conflict_log)
    
    print(f"[CONFLICT] 🏆 Победитель: {winner_id} (mode={conflict_mode})")
    
    return {
        "winner_id": winner_id,
        "winner_result": winner_result,
        "all_proposals": proposals,
        "conflict_log": conflict_log,
    }


# ══════════════════════════════════════════════════════════════
# ПАРАЛЛЕЛЬНЫЙ ЗАПУСК
# ══════════════════════════════════════════════════════════════

async def _run_parallel_proposals(
    state: dict,
    agent_pool: List[str],
    build_context_fn,
    call_agent_fn,
    phase_config: dict,
) -> Dict[str, dict]:
    """
    Запускает всех агентов пула параллельно.
    Каждый получает одинаковый контекст, но разный system_prompt и knowledge.
    """
    async def _call_single(agent_id: str):
        ctx = build_context_fn(
            state=state,
            worker_id=agent_id,
            client_slug=state.get("client_slug", "_sandbox"),
            settings_ctx=_build_settings_from_state(state),
            files_ctx="",
            previous_output=state.get("_previous_output", ""),
            anchor_ctx=(
                f"=== КОНФЛИКТНЫЙ РЕЖИМ ===\n"
                f"Ты участвуешь в параллельной генерации. "
                f"Предложи свой лучший вариант. Твоё решение будет сравниваться с другими.\n"
            ),
            run_mode=state.get("run_type", ""),
        )
        return agent_id, await call_agent_fn(state, agent_id, ctx)
    
    tasks = [_call_single(aid) for aid in agent_pool]
    results = await asyncio.gather(*tasks)
    
    proposals = {}
    for agent_id, result in results:
        human_text, meta, raw_result = result
        proposals[agent_id] = {
            "human_text": human_text,
            "meta": meta,
            "raw_result": raw_result,
        }
    
    print(f"[CONFLICT] 📥 Получено {len(proposals)}提案ов: {list(proposals.keys())}")
    return proposals


# ══════════════════════════════════════════════════════════════
# QA-СЕЛЕКТОР (divergent mode)
# ══════════════════════════════════════════════════════════════

async def _select_winner_qa(
    state: dict,
    proposals: Dict[str, dict],
    phase_config: dict,
    build_context_fn,
    call_agent_fn,
) -> str:
    """
    QA-агент получает все提案ы и выбирает лучший.
    Возвращает agent_id победителя.
    """
    qa_agent = state.get("_qa_agent", "A12")
    
    # Формируем提案ы для QA
    proposals_text = ""
    for i, (agent_id, data) in enumerate(proposals.items(), 1):
        proposals_text += (
            f"\n─── ВАРИАНТ {i} (агент {agent_id}) ───\n"
            f"{data['human_text'][:1000]}\n"
        )
    
    qa_prompt = (
        f"=== ТЫ — СУДЬЯ ===\n"
        f"Твоя задача: выбрать ЛУЧШИЙ вариант из предложенных ниже.\n\n"
        f"Критерии:\n"
        f"1. Соответствие задаче и брифу\n"
        f"2. Качество и глубина проработки\n"
        f"3. Оригинальность и креативность\n"
        f"4. Практическая применимость\n\n"
        f"{proposals_text}\n\n"
        f"=== ТВОЙ ВЕРДИКТ ===\n"
        f"Выбери ОДИН вариант. Ответь строго в формате:\n"
        f"WINNER: <agent_id>\n"
        f"REASON: <одно предложение почему>\n"
        f"LOSERS: <что не хватило остальным>\n"
    )
    
    # QA получает контекст с提案ами
    ctx = build_context_fn(
        state=state,
        worker_id=qa_agent,
        client_slug=state.get("client_slug", "_sandbox"),
        settings_ctx=_build_settings_from_state(state),
        files_ctx="",
        previous_output=qa_prompt,
        anchor_ctx="",
        run_mode="qa_selection",
    )
    
    _, meta, raw_result = await call_agent_fn(state, qa_agent, ctx)
    
    # Парсим вердикт
    winner_id = _parse_winner_from_qa(raw_result, list(proposals.keys()))
    
    # Сохраняем вердикт в state
    if "_conflict_verdicts" not in state:
        state["_conflict_verdicts"] = []
    state["_conflict_verdicts"].append({
        "phase_id": phase_config.get("id"),
        "qa_agent": qa_agent,
        "verdict": raw_result[:500],
        "winner_id": winner_id,
        "timestamp": time.time(),
    })
    
    return winner_id


def _parse_winner_from_qa(qa_response: str, agent_pool: List[str]) -> str:
    """Извлекает agent_id победителя из ответа QA."""
    # Ищем строку WINNER: A01
    match = re.search(r'WINNER:\s*(\w+)', qa_response)
    if match:
        winner = match.group(1)
        if winner in agent_pool:
            return winner
    
    # Fallback: ищем любое упоминание агента из пула
    for agent_id in agent_pool:
        if agent_id in qa_response:
            return agent_id
    
    # Совсем fallback — первый из пула
    print(f"[CONFLICT] ⚠️ Не удалось определить победителя из ответа QA, беру первого")
    return agent_pool[0]


# ══════════════════════════════════════════════════════════════
# ADVERSARIAL MODE — агенты видят提案ы друг друга
# ══════════════════════════════════════════════════════════════

async def _adversarial_rounds(
    state: dict,
    proposals: Dict[str, dict],
    agent_pool: List[str],
    phase_config: dict,
    build_context_fn,
    call_agent_fn,
    max_rounds: int = 2,
) -> str:
    """
    Агенты видят提案ы друг друга, комментируют, синтезируют.
    После раундов QA выбирает финального победителя.
    """
    current_proposals = dict(proposals)
    
    for round_num in range(1, max_rounds + 1):
        print(f"[CONFLICT] 🗣️ Adversarial раунд {round_num}/{max_rounds}")
        
        new_proposals = {}
        for agent_id in agent_pool:
            # Формируем контекст:提案ы всех + просим улучшить свой
            others_text = ""
            for other_id, data in current_proposals.items():
                if other_id != agent_id:
                    others_text += f"\n─── Вариант {other_id} ───\n{data['human_text'][:500]}\n"
            
            critique_prompt = (
                f"=== РАУНД {round_num}: УЛУЧШИ СВОЙ ВАРИАНТ ===\n"
                f"Ты видишь提案ы других агентов. Вот твой предыдущий вариант:\n"
                f"{current_proposals[agent_id]['human_text'][:500]}\n\n"
                f"Вот提案ы коллег:\n{others_text}\n\n"
                f"Улучши свой вариант: возьми сильное из чужих提案ов, "
                f"исправь слабое в своём. Предложи ФИНАЛЬНЫЙ синтезированный вариант."
            )
            
            ctx = build_context_fn(
                state=state,
                worker_id=agent_id,
                client_slug=state.get("client_slug", "_sandbox"),
                settings_ctx=_build_settings_from_state(state),
                files_ctx="",
                previous_output=critique_prompt,
                anchor_ctx="",
                run_mode=state.get("run_type", ""),
            )
            
            _, meta, raw = await call_agent_fn(state, agent_id, ctx)
            new_proposals[agent_id] = {
                "human_text": _clean_response(raw),
                "meta": meta,
                "raw_result": raw,
            }
        
        current_proposals = new_proposals
    
    # Финальный QA-выбор
    return await _select_winner_qa(
        state=state,
        proposals=current_proposals,
        phase_config=phase_config,
        build_context_fn=build_context_fn,
        call_agent_fn=call_agent_fn,
    )


# ══════════════════════════════════════════════════════════════
# ЗАПИСЬ В CONFLICT MEMORY
# ══════════════════════════════════════════════════════════════

def _build_conflict_log(
    phase_id: str,
    slot_id: str,
    proposals: Dict[str, dict],
    winner_id: str,
    conflict_mode: str,
    state: dict,
) -> dict:
    """Строит лог конфликта для записи."""
    return {
        "timestamp": time.time(),
        "slot_id": slot_id,
        "phase_id": phase_id,
        "conflict_mode": conflict_mode,
        "agent_pool": list(proposals.keys()),
        "winner_id": winner_id,
        "proposals_summary": {
            aid: data["human_text"][:200]
            for aid, data in proposals.items()
        },
        "client_slug": state.get("client_slug", ""),
        "run_type": state.get("run_type", ""),
    }


def _record_conflict(conflict_log: dict):
    """Записывает конфликт в conflict_memory или fallback."""
    try:
        from studio.economy import conflict_memory as _cm
        _cm.record_conflict_outcome(
            phase_id=conflict_log["phase_id"],
            slot_id=conflict_log["slot_id"],
            proposals=conflict_log["proposals_summary"],
            winner_id=conflict_log["winner_id"],
            conflict_mode=conflict_log["conflict_mode"],
        )
        print(f"[CONFLICT] 📝 Конфликт записан в память")
    except ImportError:
        _fallback_record(conflict_log)
    except Exception as e:
        print(f"[CONFLICT] ⚠️ Ошибка записи: {e}")


def _fallback_record(conflict_log: dict):
    """Fallback-запись если conflict_memory не готов."""
    try:
        log_path = Path("studio/economy/data/conflict_log.jsonl")
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(conflict_log, ensure_ascii=False) + "\n")
    except Exception:
        pass


# ══════════════════════════════════════════════════════════════
# ВСПОМОГАТЕЛЬНЫЕ
# ══════════════════════════════════════════════════════════════

def _build_settings_from_state(state: dict) -> str:
    """Извлекает settings из state для контекста."""
    settings = state.get("settings", {})
    return (
        f"=== PROJECT SETTINGS ===\n"
        f"Format: {settings.get('format', 'unknown')}\n"
        f"Duration: {settings.get('duration', 'unknown')} sec\n"
        f"Style: {settings.get('style', 'unknown')}\n"
    )


def _clean_response(text: str) -> str:
    """Очистка ответа от INSIGHT и лишних маркеров."""
    text = re.sub(r'\n*INSIGHT:\s*.+', '', text)
    text = re.sub(r'WINNER:\s*.+\n*', '', text)
    text = re.sub(r'REASON:\s*.+\n*', '', text)
    text = re.sub(r'LOSERS:\s*.+\n*', '', text)
    return text.strip()