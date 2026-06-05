# studio/modules/video_shorts/hooks.py — Хуки Видео Shorts
# Студия «Шесть Пальцев» · Спринт 18
#
# Правь этот файл вместо ui.py!
#
# Ключевая логика:
#   on_before_agent → A01 (Трикси): инъекция history_dna в контекст
#   on_after_agent  → A08 (Стэн):   парсинг + запись compatibility_snapshot
#   on_after_agent  → A12 (Тамб Том): CulturalFieldTracker + history_dna + outcome_signal

import json
import os
import sys
from datetime import datetime

# Путь к корню студии — поднимаемся из modules/video_shorts/
_HERE = os.path.dirname(os.path.abspath(__file__))
_STUDIO_ROOT = os.path.abspath(os.path.join(_HERE, "..", "..", ".."))
if _STUDIO_ROOT not in sys.path:
    sys.path.insert(0, _STUDIO_ROOT)

INTERACTION_LOG = os.path.join(
    _STUDIO_ROOT, "studio", "economy", "data", "interaction_log_video_shorts.jsonl"
)

# ─── Вспомогательные ──────────────────────────────────────────────────────────

def _append_interaction_log(entry: dict) -> None:
    """Дописывает запись в interaction_log (append-only)."""
    os.makedirs(os.path.dirname(INTERACTION_LOG), exist_ok=True)
    with open(INTERACTION_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _get_project_id(state: dict) -> str:
    return (
        state.get("chain_data", {}).get("master_brief", {}).get("project_id")
        or state.get("project_id")
        or "VS_UNKNOWN"
    )


def _get_episode(state: dict) -> int:
    return (
        state.get("chain_data", {}).get("history_dna", {}).get("series_map", {}).get("current_episode")
        or state.get("episode", 1)
    )


def _parse_json_block(text: str) -> dict:
    """Пытается вытащить JSON из текста агента (ищет {...})."""
    import re
    match = re.search(r'\{[\s\S]+\}', text)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return {}


# ─── on_before_agent ──────────────────────────────────────────────────────────

def on_before_agent(state: dict, worker_id: str, context: str) -> str:
    """Модифицирует контекст агента перед вызовом.

    A01 (Трикси Тренд):
        Инжектирует history_dna в контекст — client_relationship и cultural_trace.
        Без этого Трикси не знает историю клиента и культурный след цеха.
    """
    if worker_id == "A01":
        history_dna = state.get("chain_data", {}).get("history_dna", {})
        if history_dna:
            client_rel = history_dna.get("client_relationship", {})
            cultural_trace = history_dna.get("cultural_trace", [])
            client_info = history_dna.get("client", {})
            series_map = history_dna.get("series_map", {})

            injection = "\n=== HISTORY_DNA (читай внимательно) ===\n"
            injection += f"Клиент: {json.dumps(client_info, ensure_ascii=False)}\n"
            injection += f"Позиция в сезоне: {json.dumps(series_map, ensure_ascii=False)}\n"
            injection += f"client_relationship: {json.dumps(client_rel, ensure_ascii=False)}\n"
            if cultural_trace:
                injection += f"cultural_trace (stable-паттерны цеха): {json.dumps(cultural_trace, ensure_ascii=False)}\n"
            else:
                injection += "cultural_trace: [] — данных пока нет (нужно 10+ серий)\n"
            injection += "=== КОНЕЦ HISTORY_DNA ===\n"

            context += injection

    return context


# ─── on_after_agent ───────────────────────────────────────────────────────────

def on_after_agent(state: dict, worker_id: str, human_text: str, meta: dict) -> dict:
    """Обрабатывает результат агента после вызова.

    A08 (Стэн):
        Парсит compatibility_snapshot из вывода Стэна и дописывает
        структурированную запись в interaction_log_video_shorts.jsonl.
        friction_note — только Стэн пишет, никто другой.

    A12 (Тамб Том):
        1. Запрашивает CulturalFieldTracker → записывает в state для history_dna
        2. Заполняет outcome_signal в последней записи interaction_log
        3. Обновляет history_dna (narrative_memory, learnings_pack, client_relationship)
    """

    # ── A08: Стэн Стрим — логируем compatibility_snapshot ────────────────────
    if worker_id == "A08":
        parsed = _parse_json_block(human_text)
        stan_video = parsed.get("stan_video", parsed)

        snapshot = stan_video.get("compatibility_snapshot", {})
        friction = stan_video.get("friction_note", "")

        # Если Стэн не вернул snapshot — ставим нули, чтобы не потерять запись
        if not snapshot:
            snapshot = {"technical": 0.0, "creative": 0.0, "rhythm": 0.0}

        entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "episode": _get_episode(state),
            "from_agent": "vera",       # A07 — Вера Вертикаль
            "to_agent": "stan",         # A08 — Стрим Стэн
            "project_id": _get_project_id(state),
            "compatibility_snapshot": {
                "technical": float(snapshot.get("technical", 0.0)),
                "creative":  float(snapshot.get("creative",  0.0)),
                "rhythm":    float(snapshot.get("rhythm",    0.0)),
            },
            "friction_note": friction,
            "outcome_signal": None,     # заполнит Тамб Том (A12)
        }
        _append_interaction_log(entry)

    # ── A12: Тамб Том — CulturalFieldTracker + outcome_signal + history_dna ──
    elif worker_id == "A12":
        project_id = _get_project_id(state)
        parsed = _parse_json_block(human_text)
        tom_data = parsed.get("tom_thumbnail", parsed)

        # 1. CulturalFieldTracker → cultural_trace
        # update_slot_field() обновляет поле и возвращает его целиком.
        # studio_root = studio/ (не корень проекта — так прописано в __init__)
        cultural_trace = []
        try:
            from pathlib import Path
            from studio.culture.field_tracker import CulturalFieldTracker
            tracker = CulturalFieldTracker(
                studio_root=Path(_STUDIO_ROOT) / "studio"
            )
            field = tracker.update_slot_field("video_shorts")
            # Берём только stable и global — candidate и declining не нужны Трикси
            cultural_trace = [
                p for p in field.get("patterns", [])
                if p.get("status") in ("stable", "global")
            ]
        except Exception as e:
            print(f"  ⚠️  CulturalFieldTracker недоступен: {e}")

        # 2. Собираем outcome_signal из вывода Тамб Тома
        outcome_signal = tom_data.get("outcome_signal", None)
        if not outcome_signal:
            # Минимальная структура если агент не вернул
            outcome_signal = {
                "viral_score": tom_data.get("viral_score"),
                "client_feedback": tom_data.get("client_feedback"),
                "retention_peak": tom_data.get("retention_peak"),
            }

        # 3. Дописываем outcome_signal в последнюю запись interaction_log
        _patch_last_outcome_signal(outcome_signal)

        # 4. Обновляем history_dna в state для передачи дальше
        chain = state.setdefault("chain_data", {})
        history_dna = chain.get("history_dna", {})

        # cultural_trace
        history_dna["cultural_trace"] = cultural_trace

        # client_relationship — берём из вывода Тамб Тома если есть
        if "client_relationship" in tom_data:
            history_dna["client_relationship"] = tom_data["client_relationship"]

        # narrative_memory — добавляем текущую серию
        narrative_memory = history_dna.get("narrative_memory", [])
        episode_record = tom_data.get("episode_record")
        if episode_record:
            narrative_memory.append(episode_record)
            history_dna["narrative_memory"] = narrative_memory

        # learnings_pack — обновляем если есть
        if "learnings_pack" in tom_data:
            history_dna["learnings_pack"] = tom_data["learnings_pack"]

        history_dna["updated_at"] = datetime.utcnow().strftime("%Y-%m-%d")
        chain["history_dna"] = history_dna

        # 5. Обновляем client_relationship в dna.json Тамб Тома
        _update_tom_dna_client_relationship(
            tom_data.get("client_relationship"),
            project_id=project_id,
        )

        # 6. Ministry — реальный score из outcome_signal
        # Стандарт раздел 7: ministry.record_outcome в финализаторе.
        _record_ministry_outcome(state, outcome_signal)

    return {}


def _record_ministry_outcome(state: dict, outcome_signal: dict) -> None:
    """
    Сообщает Ministry о результате рана video_shorts.
    viral_score из outcome_signal — реальная оценка, не LLM-фантазия.
    Если viral_score нет — считаем детерминированно по наличию deliverables.
    """
    try:
        from studio.economy import ministry as _min
        slot_id = state.get("_slot_id", "video_shorts")

        # Score: берём viral_score если есть, иначе детерминированный минимум
        viral = outcome_signal.get("viral_score") if outcome_signal else None
        if viral is not None:
            try:
                score = float(viral)
            except (TypeError, ValueError):
                score = 5.0
        else:
            # Fallback: есть ли deliverables в chain_data
            chain  = state.get("chain_data", {})
            has_kf = bool(chain.get("key_frames") or chain.get("eva_visuals"))
            has_th = bool(chain.get("thumbnail") or chain.get("tracy_smm"))
            score  = 5.0 + (2.0 if has_kf else 0) + (1.5 if has_th else 0)

        score = round(min(10.0, max(0.0, score)), 2)

        # Все агенты рана
        agents = list(state.get("results", {}).keys()) or [
            "A01","A02","A03","A04","A05",
            "A06","A07","A08","A09","A10","A11","A12",
        ]
        for agent_id in agents:
            try:
                from studio.economy import ledger as _led
                cost = _led.agent_spent(agent_id, slot_id=slot_id)
            except Exception:
                cost = 0.0
            _min.record_outcome(
                agent_id=agent_id,
                slot_id=slot_id,
                score=score,
                cost_usd=cost,
            )

        print(f"[VS A12] 🏛 Ministry: score={score} "
              f"viral_raw={viral} agents={len(agents)}")

    except Exception as e:
        print(f"[VS A12] ⚠ ministry.record_outcome: {e}")


# ─── Вспомогательные для A12 ──────────────────────────────────────────────────

def _patch_last_outcome_signal(outcome_signal: dict) -> None:
    """Находит последнюю запись в interaction_log и заполняет outcome_signal."""
    if not os.path.exists(INTERACTION_LOG):
        return
    try:
        with open(INTERACTION_LOG, "r", encoding="utf-8") as f:
            lines = f.readlines()
        if not lines:
            return

        last = json.loads(lines[-1])
        last["outcome_signal"] = outcome_signal
        lines[-1] = json.dumps(last, ensure_ascii=False) + "\n"

        with open(INTERACTION_LOG, "w", encoding="utf-8") as f:
            f.writelines(lines)
    except Exception as e:
        print(f"  ⚠️  Не удалось обновить outcome_signal: {e}")


def _update_tom_dna_client_relationship(client_relationship: dict | None, project_id: str) -> None:
    """Обновляет client_relationship в dna.json Тамб Тома (A12)."""
    if not client_relationship:
        return
    try:
        from studio.grondheim_memory import GrondheimMemory
        mem = GrondheimMemory(agent_id="A12", slot_id="video_shorts")
        mem.sync_to_dna({
            "client_relationship": client_relationship,
            "last_project_id": project_id,
        })
    except Exception as e:
        print(f"  ⚠️  Не удалось обновить dna.json Тамб Тома: {e}")
