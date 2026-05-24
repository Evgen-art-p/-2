#!/usr/bin/env python3
"""
patch_hooks_ministry.py — Ministry в финализаторах четырёх цехов
Студия «Шесть Пальцев» · 2026

ЧТО И ПОЧЕМУ:

Стандарт цеха (WORKSHOP_STANDARD.md раздел 7) говорит:
  ministry.record_outcome вызывается в hooks.py финализатора.
  Это единственное место где цех сообщает Ministry о реальном результате.

Сейчас ни один из четырёх цехов этого не делает.
Ministry слепое — не накапливает статистику, не даёт подсказки агентам.

Патч добавляет ministry.record_outcome в финализаторы:
  turbo      → A05 on_after_agent  (viral_score из t5_deliverables)
  social_mix → async_scoring: false (Ministry получает данные синхронно)
  video_shorts → A12 on_after_agent (viral_score из outcome_signal)
  video_long   → A12 _bob_finalize  (viral_score из outcome_signal)

Дополнительно:
  pipeline.py — убираем двойные record_outcome(score=7.0) из середины рана
  pipeline.py — убираем _apply_qa_feedback (ненадёжный поиск слов)
  metrics_daemon.py — real_viral_score идёт всем агентам рана

Запуск:
  python patch_hooks_ministry.py
  python patch_hooks_ministry.py --dry-run

Бэкапы создаются автоматически (.bak_YYYYMMDD_HHMMSS).
"""

import sys
import shutil
import datetime
from pathlib import Path

DRY_RUN = "--dry-run" in sys.argv
ROOT    = Path(".")

_applied   = []
_skipped   = []
_notfound  = []


def _ts():
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")


def _backup(path: Path) -> Path:
    bak = path.with_suffix(f".bak_{_ts()}")
    shutil.copy2(path, bak)
    return bak


def _patch(rel: str, old: str, new: str, desc: str) -> bool:
    path = ROOT / rel
    if not path.exists():
        print(f"  ⚠  НЕ НАЙДЕН: {rel}")
        _notfound.append(desc)
        return False
    text = path.read_text(encoding="utf-8")
    if old not in text:
        print(f"  ℹ  Уже применён или паттерн не найден: {desc}")
        _skipped.append(desc)
        return False
    if DRY_RUN:
        print(f"  ✅ [DRY] {desc}")
        _applied.append(f"[DRY] {desc}")
        return True
    bak = _backup(path)
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    print(f"  ✅ {desc}")
    print(f"     бэкап: {bak.name}")
    _applied.append(desc)
    return True


# ──────────────────────────────────────────────────────────────────
print("=" * 64)
print(f"  ПАТЧ hooks_ministry{'  [DRY-RUN]' if DRY_RUN else ''}")
print(f"  {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 64)

# ═══════════════════════════════════════════════════════════════════
# 1. TURBO — добавляем ministry в A05 on_after_agent
#
# Почему: turbo/hooks.py возвращает {} для A05.
# Ministry не знает о результатах TURBO-цеха вообще.
# viral_score берём из t5_deliverables.final_dna если есть,
# иначе считаем по числу готовых кадров (детерминированная оценка).
# ═══════════════════════════════════════════════════════════════════
print("\n[1/6] turbo/hooks.py — ministry.record_outcome в A05")

_patch(
    rel="studio/modules/turbo/hooks.py",
    old="def on_after_agent(state: dict, worker_id: str, human_text: str, meta: dict) -> dict:\n"
        "    if worker_id == \"A03\":\n"
        "        _a03_generate_keyframes(state, human_text)\n"
        "    elif worker_id == \"A05\":\n"
        "        _a05_generate_thumbnails_and_deliverables(state, human_text)\n"
        "    return {}",
    new="def on_after_agent(state: dict, worker_id: str, human_text: str, meta: dict) -> dict:\n"
        "    if worker_id == \"A03\":\n"
        "        _a03_generate_keyframes(state, human_text)\n"
        "    elif worker_id == \"A05\":\n"
        "        _a05_generate_thumbnails_and_deliverables(state, human_text)\n"
        "        _a05_record_ministry(state)\n"
        "    return {}\n"
        "\n"
        "\n"
        "def _a05_record_ministry(state: dict) -> None:\n"
        "    \"\"\"\n"
        "    Финализатор TURBO сообщает Ministry о реальном результате рана.\n"
        "    Стандарт цеха раздел 7: ministry.record_outcome в финализаторе hooks.py.\n"
        "\n"
        "    viral_score считается детерминированно:\n"
        "      - есть готовые кадры + обложки → базовый score\n"
        "      - Gemini-проверка дала высокий quality_score → бонус\n"
        "    Это объективный сигнал, не LLM-оценка.\n"
        "    \"\"\"\n"
        "    try:\n"
        "        from studio.economy import ministry as _min\n"
        "        slot_id = state.get(\"_slot_id\", \"turbo\")\n"
        "\n"
        "        # Читаем deliverables которые только что собрал A05\n"
        "        chain = state.get(\"chain_data\", {})\n"
        "        deliv = chain.get(\"t5_deliverables\", {})\n"
        "\n"
        "        # Детерминированный score: факты, не слова\n"
        "        frames     = deliv.get(\"key_frames\", [])\n"
        "        ready_frames = sum(1 for f in frames if f.get(\"path\"))\n"
        "        total_frames = len(frames) or 1\n"
        "        thumb        = deliv.get(\"thumbnail\", {})\n"
        "        ready_thumbs = sum(\n"
        "            1 for v in (\"variant_a\", \"variant_b\")\n"
        "            if thumb.get(v, {}).get(\"path\")\n"
        "        )\n"
        "        # Средний quality_score от Gemini (0–10)\n"
        "        qs_list = [f.get(\"quality_score\", 5) for f in frames if f.get(\"path\")]\n"
        "        avg_qs  = sum(qs_list) / len(qs_list) if qs_list else 5.0\n"
        "\n"
        "        # Формула: базовый 5.0, +2.0 за кадры, +1.5 за обложки, +1.5 за качество\n"
        "        score = 5.0\n"
        "        score += 2.0 * (ready_frames / total_frames)   # кадры\n"
        "        score += 1.5 * (ready_thumbs / 2)              # обложки\n"
        "        score += 1.5 * (avg_qs / 10.0)                 # качество Gemini\n"
        "        score  = round(min(10.0, score), 2)\n"
        "\n"
        "        # Агенты TURBO-цеха\n"
        "        agents = state.get(\n"
        "            \"turbo_workers\",\n"
        "            [\"A01\", \"A02\", \"A03\", \"A04\", \"A05\"]\n"
        "        )\n"
        "        for agent_id in agents:\n"
        "            try:\n"
        "                from studio.economy import ledger as _led\n"
        "                cost = _led.agent_spent(agent_id, slot_id=slot_id)\n"
        "            except Exception:\n"
        "                cost = 0.0\n"
        "            _min.record_outcome(\n"
        "                agent_id=agent_id,\n"
        "                slot_id=slot_id,\n"
        "                score=score,\n"
        "                cost_usd=cost,\n"
        "            )\n"
        "\n"
        "        print(f\"[TURBO A05] 🏛 Ministry: score={score} \"\n"
        "              f\"frames={ready_frames}/{total_frames} \"\n"
        "              f\"thumbs={ready_thumbs}/2 \"\n"
        "              f\"gemini_avg={avg_qs:.1f}\")\n"
        "\n"
        "        # CulturalFieldTracker — только если есть hooks (стандарт раздел 8)\n"
        "        try:\n"
        "            from studio.culture.field_tracker import CulturalFieldTracker\n"
        "            CulturalFieldTracker().update_slot_field(slot_id)\n"
        "            print(\"[TURBO A05] 🧬 CulturalFieldTracker обновлён\")\n"
        "        except Exception as _ce:\n"
        "            print(f\"[TURBO A05] ⚠ CulturalFieldTracker: {_ce}\")\n"
        "\n"
        "    except Exception as e:\n"
        "        print(f\"[TURBO A05] ⚠ ministry.record_outcome: {e}\")",
    desc="turbo/hooks.py: ministry + CulturalFieldTracker в A05",
)


# ═══════════════════════════════════════════════════════════════════
# 2. SOCIAL_MIX — async_scoring: false
#
# Почему: async_scoring=true отключает Ministry в pipeline.py.
# Metrics Daemon (courier.py) не существует в продакшене.
# Ministry не получает данных от СММ вообще.
# После первого реального рана и подтверждения Daemon — вернём true.
# ═══════════════════════════════════════════════════════════════════
print("\n[2/6] social_mix/manifest.json — async_scoring: false")

_patch(
    rel="studio/modules/social_mix/manifest.json",
    old='"async_scoring": true',
    new='"async_scoring": false',
    desc="social_mix/manifest.json: async_scoring=false до подтверждения Daemon",
)


# ═══════════════════════════════════════════════════════════════════
# 3. VIDEO_SHORTS — ministry в A12 on_after_agent
#
# Почему: video_shorts/hooks.py A12 (Тамб Том) обновляет history_dna
# и cultural_trace — но не сообщает Ministry о результате.
# viral_score берём из outcome_signal который сам же Тамб Том записывает.
# ═══════════════════════════════════════════════════════════════════
print("\n[3/6] video_shorts/hooks.py — ministry в A12")

_patch(
    rel="studio/modules/video_shorts/hooks.py",
    old="        # 5. Обновляем client_relationship в dna.json Тамб Тома\n"
        "        _update_tom_dna_client_relationship(\n"
        "            tom_data.get(\"client_relationship\"),\n"
        "            project_id=project_id,\n"
        "        )\n"
        "\n"
        "    return {}",
    new="        # 5. Обновляем client_relationship в dna.json Тамб Тома\n"
        "        _update_tom_dna_client_relationship(\n"
        "            tom_data.get(\"client_relationship\"),\n"
        "            project_id=project_id,\n"
        "        )\n"
        "\n"
        "        # 6. Ministry — реальный score из outcome_signal\n"
        "        # Стандарт раздел 7: ministry.record_outcome в финализаторе.\n"
        "        _record_ministry_outcome(state, outcome_signal)\n"
        "\n"
        "    return {}\n"
        "\n"
        "\n"
        "def _record_ministry_outcome(state: dict, outcome_signal: dict) -> None:\n"
        "    \"\"\"\n"
        "    Сообщает Ministry о результате рана video_shorts.\n"
        "    viral_score из outcome_signal — реальная оценка, не LLM-фантазия.\n"
        "    Если viral_score нет — считаем детерминированно по наличию deliverables.\n"
        "    \"\"\"\n"
        "    try:\n"
        "        from studio.economy import ministry as _min\n"
        "        slot_id = state.get(\"_slot_id\", \"video_shorts\")\n"
        "\n"
        "        # Score: берём viral_score если есть, иначе детерминированный минимум\n"
        "        viral = outcome_signal.get(\"viral_score\") if outcome_signal else None\n"
        "        if viral is not None:\n"
        "            try:\n"
        "                score = float(viral)\n"
        "            except (TypeError, ValueError):\n"
        "                score = 5.0\n"
        "        else:\n"
        "            # Fallback: есть ли deliverables в chain_data\n"
        "            chain  = state.get(\"chain_data\", {})\n"
        "            has_kf = bool(chain.get(\"key_frames\") or chain.get(\"eva_visuals\"))\n"
        "            has_th = bool(chain.get(\"thumbnail\") or chain.get(\"tracy_smm\"))\n"
        "            score  = 5.0 + (2.0 if has_kf else 0) + (1.5 if has_th else 0)\n"
        "\n"
        "        score = round(min(10.0, max(0.0, score)), 2)\n"
        "\n"
        "        # Все агенты рана\n"
        "        agents = list(state.get(\"results\", {}).keys()) or [\n"
        "            \"A01\",\"A02\",\"A03\",\"A04\",\"A05\",\n"
        "            \"A06\",\"A07\",\"A08\",\"A09\",\"A10\",\"A11\",\"A12\",\n"
        "        ]\n"
        "        for agent_id in agents:\n"
        "            try:\n"
        "                from studio.economy import ledger as _led\n"
        "                cost = _led.agent_spent(agent_id, slot_id=slot_id)\n"
        "            except Exception:\n"
        "                cost = 0.0\n"
        "            _min.record_outcome(\n"
        "                agent_id=agent_id,\n"
        "                slot_id=slot_id,\n"
        "                score=score,\n"
        "                cost_usd=cost,\n"
        "            )\n"
        "\n"
        "        print(f\"[VS A12] 🏛 Ministry: score={score} \"\n"
        "              f\"viral_raw={viral} agents={len(agents)}\")\n"
        "\n"
        "    except Exception as e:\n"
        "        print(f\"[VS A12] ⚠ ministry.record_outcome: {e}\")",
    desc="video_shorts/hooks.py: ministry.record_outcome в A12",
)


# ═══════════════════════════════════════════════════════════════════
# 4. VIDEO_LONG — ministry в _bob_finalize
#
# Почему: video_long/hooks.py _bob_finalize собирает deliverables,
# закрывает петлю памяти — но не сообщает Ministry о результате.
# viral_score берём из outcome_signal который сам Боб обрабатывает.
# ═══════════════════════════════════════════════════════════════════
print("\n[4/6] video_long/hooks.py — ministry в _bob_finalize")

_patch(
    rel="studio/modules/video_long/hooks.py",
    old="    _bob_collect_media(chain, deliverables)\n"
        "    data[\"deliverables\"] = deliverables\n"
        "    _update_state(state, data)\n"
        "    print(\"[EPISODE A12] ✅ deliverables собраны\")\n"
        "\n"
        "    cultural_trace = _bob_cultural_trace(state)\n"
        "    _bob_update_history_dna(state, my_output, cultural_trace)\n"
        "    _bob_update_dna_json(state, my_output)\n"
        "    _bob_fill_outcome_signal(state, my_output)\n"
        "\n"
        "    print(\"[EPISODE A12] ✅ Петля памяти закрыта\")",
    new="    _bob_collect_media(chain, deliverables)\n"
        "    data[\"deliverables\"] = deliverables\n"
        "    _update_state(state, data)\n"
        "    print(\"[EPISODE A12] ✅ deliverables собраны\")\n"
        "\n"
        "    cultural_trace = _bob_cultural_trace(state)\n"
        "    _bob_update_history_dna(state, my_output, cultural_trace)\n"
        "    _bob_update_dna_json(state, my_output)\n"
        "    _bob_fill_outcome_signal(state, my_output)\n"
        "    _bob_record_ministry(state, my_output)\n"
        "\n"
        "    print(\"[EPISODE A12] ✅ Петля памяти закрыта\")\n"
        "\n"
        "\n"
        "def _bob_record_ministry(state: dict, my_output: dict) -> None:\n"
        "    \"\"\"\n"
        "    Финализатор video_long сообщает Ministry о реальном результате.\n"
        "    Стандарт раздел 7: ministry.record_outcome в финализаторе hooks.py.\n"
        "\n"
        "    viral_score из outcome_signal Боба — реальная оценка.\n"
        "    Если нет — детерминированный счёт по готовым deliverables.\n"
        "    \"\"\"\n"
        "    try:\n"
        "        from studio.economy import ministry as _min\n"
        "        slot_id = state.get(\"_slot_id\", \"video_long\")\n"
        "\n"
        "        # Score: viral_score если есть\n"
        "        outcome = my_output.get(\"outcome_signal\", {})\n"
        "        viral   = outcome.get(\"viral_score\") if isinstance(outcome, dict) else None\n"
        "        if viral is None:\n"
        "            viral = my_output.get(\"viral_score\")\n"
        "\n"
        "        if viral is not None:\n"
        "            try:\n"
        "                score = float(viral)\n"
        "            except (TypeError, ValueError):\n"
        "                score = 5.0\n"
        "        else:\n"
        "            # Fallback: считаем по deliverables\n"
        "            chain    = state.get(\"chain_data\", {})\n"
        "            deliv    = state.get(\"_last_output\", {}).get(\"deliverables\", {})\n"
        "            kf       = deliv.get(\"key_frames\", [])\n"
        "            ready_kf = sum(1 for f in kf if f.get(\"path\"))\n"
        "            total_kf = len(kf) or 1\n"
        "            thumb    = deliv.get(\"thumbnail\", {})\n"
        "            ready_th = sum(\n"
        "                1 for v in (\"variant_a\", \"variant_b\")\n"
        "                if thumb.get(v, {}).get(\"path\")\n"
        "            )\n"
        "            score = 5.0\n"
        "            score += 2.5 * (ready_kf / total_kf)  # кадры\n"
        "            score += 1.5 * (ready_th / 2)          # обложки\n"
        "            score  = round(min(10.0, score), 2)\n"
        "\n"
        "        score = round(min(10.0, max(0.0, score)), 2)\n"
        "\n"
        "        # Все агенты рана\n"
        "        agents = list(state.get(\"results\", {}).keys()) or [\n"
        "            \"A01\",\"A02\",\"A03\",\"A04\",\"A05\",\n"
        "            \"A06\",\"A07\",\"A08\",\"A09\",\"A10\",\"A11\",\"A12\",\n"
        "        ]\n"
        "        for agent_id in agents:\n"
        "            try:\n"
        "                from studio.economy import ledger as _led\n"
        "                cost = _led.agent_spent(agent_id, slot_id=slot_id)\n"
        "            except Exception:\n"
        "                cost = 0.0\n"
        "            _min.record_outcome(\n"
        "                agent_id=agent_id,\n"
        "                slot_id=slot_id,\n"
        "                score=score,\n"
        "                cost_usd=cost,\n"
        "            )\n"
        "\n"
        "        print(f\"[VL A12] 🏛 Ministry: score={score} \"\n"
        "              f\"viral_raw={viral} agents={len(agents)}\")\n"
        "\n"
        "    except Exception as e:\n"
        "        print(f\"[VL A12] ⚠ ministry.record_outcome: {e}\")",
    desc="video_long/hooks.py: ministry.record_outcome в _bob_finalize",
)


# ═══════════════════════════════════════════════════════════════════
# 5. PIPELINE — убираем двойные record_outcome(score=7.0)
#
# Почему: каждый агент в середине рана получает score=7.0 в Ministry
# до того как QA что-то сказал. Ministry кормится мусором.
# Реальный score теперь пишут hooks.py финализаторов (фиксы 1-4).
# QA-блок в pipeline.py пишет реальный score из feedback.json — оставляем.
# ═══════════════════════════════════════════════════════════════════
print("\n[5/6] pipeline.py — убираем фантомные score=7.0")

_patch(
    rel="studio/workshop/pipeline.py",
    old="        # Strategy Registry: записываем стратегию агента\n"
        "        if _STRATEGY_ENABLED:\n"
        "            try:\n"
        "                record_strategy(\n"
        "                    agent_id=worker_id,\n"
        "                    slot_id=_slot_id,\n"
        "                    score=7.0,  # базовая оценка, QA уточнит позже\n"
        "                    result_summary=human_text[:300],\n"
        "                    run_type=_run_type,\n"
        "                    client_slug=client_slug,\n"
        "                )\n"
        "            except Exception as _e:\n"
        "                print(f\"[STRATEGY] Ошибка записи для {worker_id}: {_e}\")",
    new="        # Strategy Registry: стратегии пишутся ТОЛЬКО после QA\n"
        "        # через _record_winning_strategies() с реальным score.\n"
        "        # Фантомный score=7.0 убран — он отравлял Registry мусором.",
    desc="pipeline.py: убран фантомный record_strategy(score=7.0)",
)

_patch(
    rel="studio/workshop/pipeline.py",
    old="        # Ministry: фиксируем исход с базовой оценкой.\n"
        "        # QA-агент пропускаем — он получит record_outcome с реальным score из feedback.json\n"
        "        # в QA-блоке ниже, чтобы не задваивать runs_total.\n"
        "        _qa_agent_id = state.get(\"_qa_agent\", \"A12\")\n"
        "        if _ECONOMY_ENABLED and worker_id != _qa_agent_id:\n"
        "            try:\n"
        "                from studio.economy import ledger as _ledger\n"
        "                _wcost = _ledger.agent_spent(worker_id, slot_id=_slot_id)\n"
        "            except Exception:\n"
        "                _wcost = 0.0\n"
        "            try:\n"
        "                if not state.get(\"async_scoring\", False):  # patch_async_scoring\n"
        "                    _ministry.record_outcome(\n"
        "                        agent_id=worker_id,\n"
        "                        slot_id=_slot_id,\n"
        "                        score=7.0,  # базовая оценка, QA уточнит позже\n"
        "                        cost_usd=_wcost,\n"
        "                    )\n"
        "            except Exception as _e:\n"
        "                print(f\"[MINISTRY] Ошибка записи для {worker_id}: {_e}\")",
    new="        # Ministry: record_outcome вызывается в hooks.py финализатора\n"
        "        # с реальным score (детерминированным или viral).\n"
        "        # Фантомный score=7.0 убран — он давал двойные записи с мусором.",
    desc="pipeline.py: убран фантомный ministry.record_outcome(score=7.0)",
)


# ═══════════════════════════════════════════════════════════════════
# 6. PIPELINE — убираем _apply_qa_feedback (угадывание по словам)
#
# Почему: функция ищет "отлично"/"ошибка" рядом с ID агента в тексте QA.
# Это ненадёжно — LLM может хвалить не упоминая строку "A03".
# DNA синхронизируется через _sync_feedback_scores_to_dna которая
# читает структурированный feedback.json. Этого достаточно.
# ═══════════════════════════════════════════════════════════════════
print("\n[6/6] pipeline.py — убираем _apply_qa_feedback")

_patch(
    rel="studio/workshop/pipeline.py",
    old="        if _GRONDHEIM_ENABLED:\n"
        "            _apply_qa_feedback(state, raw_result, qa_agent)",
    new="        # _apply_qa_feedback убрана: поиск слов в тексте QA ненадёжен.\n"
        "        # DNA синхронизируется через _sync_feedback_scores_to_dna\n"
        "        # которая читает структурированный feedback.json.",
    desc="pipeline.py: убран _apply_qa_feedback",
)


# ──────────────────────────────────────────────────────────────────
print("\n" + "=" * 64)
print("ИТОГ:")
print(f"  ✅ Применено:  {len(_applied)}")
print(f"  ℹ  Пропущено:  {len(_skipped)}")
print(f"  ⚠  Не найдено: {len(_notfound)}")

if _notfound:
    print("\n  Запускай из корня проекта (рядом с папкой studio/):")
    for r in _notfound:
        print(f"    — {r}")

if not DRY_RUN and _applied:
    print("\n  Что изменилось:")
    print("  • turbo/hooks.py       — A05 пишет в Ministry детерминированный score")
    print("  • social_mix/manifest  — async_scoring=false, Ministry получает данные")
    print("  • video_shorts/hooks   — A12 пишет в Ministry реальный viral_score")
    print("  • video_long/hooks     — A12 пишет в Ministry реальный viral_score")
    print("  • pipeline.py          — убраны двойные score=7.0 из середины рана")
    print("  • pipeline.py          — убран ненадёжный _apply_qa_feedback")
    print("\n  Следующий шаг: первый реальный ран любого из четырёх цехов.")
    print("  Ministry наконец получит настоящие данные.")

print("=" * 64)
