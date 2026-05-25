#!/usr/bin/env python3
"""
patch_dna_single_source.py — Спринт 21 · Аудит памяти

ПРОБЛЕМА:
  За один ран DNA агента обновляется ДВАЖДЫ:
    1. on_agent_done(quality=0.3/0.5/0.6/0.8) — эвристика по синтаксису, ДО QA
    2. _sync_feedback_scores_to_dna() — реальный score от QA, ПОСЛЕ QA

  Агент получает "награду" за правильные скобки, потом
  "наказание" (или другую награду) за реальное качество.
  Это шизофрения, а не обучение.

РЕШЕНИЕ:
  [1] pipeline.py → process_agent_result():
      - убираем вычисление quality=0.3/0.5/0.6/0.8
      - on_agent_done() вызываем БЕЗ quality_score (только sensory log)
      - on_agents_interact() оставляем — это социальные связи, не DNA

  [2] grondheim_memory.py → on_agent_done():
      - убираем sync_to_dna() изнутри
      - убираем update_profile_vector() изнутри
      - функция пишет ТОЛЬКО в sensory_memory — фактологический журнал

  [3] _apply_qa_feedback() в pipeline.py — удаляем тело (мёртвый код)

  Единственный источник правды для DNA:
      _sync_feedback_scores_to_dna() → вызывается один раз после QA

ЗАПУСК:
  python patch_dna_single_source.py
  python patch_dna_single_source.py --dry-run  # только показать что изменится
"""

import sys
import shutil
import argparse
from pathlib import Path
from datetime import datetime

# ═══════════════════════════════════════════
# КОНФИГ
# ═══════════════════════════════════════════

PIPELINE_PATH = Path("studio/workshop/pipeline.py")
GRONDHEIM_PATH = Path("studio/grondheim_memory.py")

TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")


# ═══════════════════════════════════════════
# УТИЛИТЫ
# ═══════════════════════════════════════════

def backup(path: Path) -> Path:
    bak = path.with_suffix(f".bak_{TIMESTAMP}")
    shutil.copy2(path, bak)
    print(f"  [BAK] {path} → {bak.name}")
    return bak


def apply_patch(path: Path, old: str, new: str, label: str, dry_run: bool) -> bool:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        print(f"  [SKIP] {label} — фрагмент не найден (уже пропатчено?)")
        return False
    if dry_run:
        print(f"  [DRY] {label} — найден, будет заменён")
        return True
    patched = text.replace(old, new, 1)
    path.write_text(patched, encoding="utf-8")
    print(f"  [OK] {label}")
    return True


# ═══════════════════════════════════════════
# ПАТЧ 1: pipeline.py — убираем фантомный quality
# ═══════════════════════════════════════════

PIPELINE_OLD = '''    # ══ NEW: Личная память агента (Грондхейм) ══
    if _GRONDHEIM_ENABLED:
        # Определяем quality_score
        # ИСПРАВЛЕНО: deliverables есть только у финализатора.
        # Для промежуточных агентов смотрим на my_output и ghost_ids.
        quality = 0.6  # дефолт — нейтральная хорошая работа
        has_my_output = bool(meta.get("my_output") or meta.get("deliverables"))
        has_ghost_ids = bool(ghost_ids)

        if has_my_output and not has_ghost_ids:
            quality = 0.8  # агент выдал результат без ошибок
        elif has_my_output and has_ghost_ids:
            quality = 0.5  # есть результат, но с галлюцинациями
        elif not has_my_output and has_ghost_ids:
            quality = 0.3  # нет вывода и есть ошибки
        # has_my_output=False, has_ghost_ids=False → quality=0.6 (текстовый ответ без JSON)

        on_agent_done(
            agent_id=worker_id,
            result_summary=human_text[:200],
            quality_score=quality,
            dept=state.get("active_dept", ""),
        )

        # Межагентное взаимодействие: текущий агент использует результат предыдущего
        prev_agents = [k for k in state.get("results", {}).keys() if k != worker_id]
        if prev_agents:
            last_agent = prev_agents[-1]
            _my_out = meta.get("my_output", {}) or {}
            # compatibility_snapshot — вложен в felix_vfx согласно CHAIN_CONTRACT
            # PATCH audit-sprint19 [3]: был .get("compatibility_snapshot") на корне my_output
            _compat = _my_out.get("felix_vfx", {}).get("compatibility_snapshot") \\
                if worker_id == "A08" else None
            # final_dna — финализатор любого цеха (всегда A12 по стандарту qa_agent)
            _outcome = _my_out.get("final_dna") \\
                if worker_id == state.get("_qa_agent", "A12") else None
            on_agents_interact(
                agent_a=last_agent,
                agent_b=worker_id,
                interaction_type="collaboration",
                quality=quality,
                note=f"Передача работы в пайплайне {run_type}",
                dept=state.get("active_dept", ""),
                compatibility_snapshot=_compat,
                outcome_signal=_outcome,
            )
    # ══ END NEW ══'''

PIPELINE_NEW = '''    # ══ Личная память агента (Грондхейм) · Спринт 21 ══
    # ПАТЧ: on_agent_done() пишет ТОЛЬКО в sensory_memory (фактологический журнал).
    # sync_to_dna() и update_profile_vector() убраны отсюда.
    # Единственный источник правды для DNA → _sync_feedback_scores_to_dna() после QA.
    if _GRONDHEIM_ENABLED:
        on_agent_done(
            agent_id=worker_id,
            result_summary=human_text[:200],
            dept=state.get("active_dept", ""),
        )

        # Межагентное взаимодействие: социальные связи (не DNA!)
        # quality здесь — нейтральный сигнал о факте передачи, не оценка.
        prev_agents = [k for k in state.get("results", {}).keys() if k != worker_id]
        if prev_agents:
            last_agent = prev_agents[-1]
            _my_out = meta.get("my_output", {}) or {}
            _compat = _my_out.get("felix_vfx", {}).get("compatibility_snapshot") \\
                if worker_id == "A08" else None
            _outcome = _my_out.get("final_dna") \\
                if worker_id == state.get("_qa_agent", "A12") else None
            on_agents_interact(
                agent_a=last_agent,
                agent_b=worker_id,
                interaction_type="collaboration",
                quality=0.5,  # нейтрально — реальная оценка придёт от QA
                note=f"Передача работы в пайплайне {run_type}",
                dept=state.get("active_dept", ""),
                compatibility_snapshot=_compat,
                outcome_signal=_outcome,
            )
    # ══ END Личная память ══'''


# ═══════════════════════════════════════════
# ПАТЧ 2: pipeline.py — _apply_qa_feedback() мёртвый код
# ═══════════════════════════════════════════

APPLY_QA_OLD = '''def _apply_qa_feedback(state: dict, raw_result: str, qa_agent: str):
    """
    Парсит ответ QA-агента и транслирует оценки в DNA коллег.
    Универсальная версия — работает для любого qa_agent цеха.
    """
    dept = state.get("active_dept", "")
    raw_lower = raw_result.lower()

    # Все рабочие агенты кроме QA
    worker_ids = [k for k in state.get("results", {}).keys() if k != qa_agent]

    positive_markers = ["отлично", "хорошо", "качественно", "сильно", "точно", "великолепно", "браво"]
    negative_markers = ["ошибка", "правки", "слабо", "не соответствует", "переделать", "проблема", "критично"]

    for wid in worker_ids:
        if wid not in raw_result:
            continue

        # Ищем контекст вокруг упоминания агента (±200 символов)
        idx = raw_result.find(wid)
        context_window = raw_lower[max(0, idx-200):idx+200]

        is_positive = any(m in context_window for m in positive_markers)
        is_negative = any(m in context_window for m in negative_markers)

        if is_positive and not is_negative:
            on_agents_interact(qa_agent, wid, "praise", 0.8, "Положительная оценка QA", dept)
        elif is_negative and not is_positive:
            on_agents_interact(qa_agent, wid, "critique", 0.7, "Замечания QA", dept)
        elif is_positive and is_negative:
            # Смешанная оценка — лёгкая критика
            on_agents_interact(qa_agent, wid, "critique", 0.3, "Смешанная оценка QA", dept)'''

APPLY_QA_NEW = '''def _apply_qa_feedback(state: dict, raw_result: str, qa_agent: str):
    """
    УДАЛЕНО · Спринт 21.
    Парсинг ключевых слов ("отлично", "ошибка") из текста QA ненадёжен.
    DNA синхронизируется через _sync_feedback_scores_to_dna()
    которая читает структурированный feedback.json.
    Функция оставлена как заглушка для совместимости импортов.
    """
    pass  # намеренно пусто — см. _sync_feedback_scores_to_dna()'''


# ═══════════════════════════════════════════
# ПАТЧ 3: grondheim_memory.py → on_agent_done()
# убираем sync_to_dna() и update_profile_vector()
# ═══════════════════════════════════════════

GRONDHEIM_OLD = '''def on_agent_done(
    agent_id: str,
    result_summary: str,
    quality_score: float = 0.5,
    dept: str = "",
):
    """
    Вызывается после завершения работы агента.
    - Записывает рабочее событие в sensory
    - Если quality_score высокий — записывает в resonance
    """
    # Всегда в оперативку
    record_sensory_event(
        agent_id=agent_id,
        content=f"Выполнил задачу: {result_summary[:200]}",
        event_type="work",
        source="pipeline",
        emotional_weight=min(quality_score, 0.8),
        dept=dept,
    )

    # ══ Character Drift (Спринт 17) ══
    if quality_score >= 0.8:
        update_profile_vector(agent_id, dept)
    # ══ END Drift ══

    # Значимое — в резонансный лог
    if quality_score >= 0.7:
        record_resonance_event(
            agent_id=agent_id,
            event_type="achievement",
            content=f"Отличная работа: {result_summary[:200]}",
            significance=quality_score,
            dept=dept,
        )

    # ══ SYNC TO DNA: город дышит ══
    if quality_score >= 0.7:
        sync_to_dna(agent_id, "good_work", intensity=quality_score, dept=dept)
    elif quality_score < 0.3:
        sync_to_dna(agent_id, "bad_work", intensity=1.0 - quality_score, dept=dept)
    # Нейтральная работа (0.3–0.7) — не трогаем DNA.
    # Стресс снижается только за реально хорошую работу, иначе агенты
    # дрейфуют к нулевому стрессу даже без реальных достижений.'''

GRONDHEIM_NEW = '''def on_agent_done(
    agent_id: str,
    result_summary: str,
    quality_score: float = 0.5,  # параметр сохранён для совместимости, но не используется
    dept: str = "",
):
    """
    Вызывается после завершения работы агента.

    ПАТЧ Спринт 21 · Единственный источник правды:
    - Эта функция пишет ТОЛЬКО в sensory_memory (фактологический журнал).
    - sync_to_dna() и update_profile_vector() УДАЛЕНЫ отсюда.
    - DNA меняется только через _sync_feedback_scores_to_dna() в pipeline.py
      после реального QA score от финального агента цеха.

    Причина: quality_score здесь был эвристикой (0.3/0.5/0.6/0.8 по синтаксису),
    что вызывало двойную запись в DNA — сначала мусором, потом правдой.
    """
    # Только в оперативку — факт выполнения работы, без оценки
    record_sensory_event(
        agent_id=agent_id,
        content=f"Выполнил задачу: {result_summary[:200]}",
        event_type="work",
        source="pipeline",
        emotional_weight=0.3,  # нейтральный вес — оценка придёт от QA
        dept=dept,
    )'''


# ═══════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Патч: единственный источник правды для DNA")
    parser.add_argument("--dry-run", action="store_true", help="только показать изменения")
    args = parser.parse_args()

    dry = args.dry_run
    mode = "DRY RUN" if dry else "ПРИМЕНЕНИЕ"

    print(f"\n{'='*60}")
    print(f"patch_dna_single_source.py · {mode}")
    print(f"{'='*60}\n")

    # Проверяем наличие файлов
    for p in [PIPELINE_PATH, GRONDHEIM_PATH]:
        if not p.exists():
            print(f"[ERROR] Файл не найден: {p}")
            print("  Запускай из корня проекта (рядом со студией).")
            sys.exit(1)

    # Бэкапы
    if not dry:
        print("Создаём бэкапы...")
        backup(PIPELINE_PATH)
        backup(GRONDHEIM_PATH)
        print()

    # ── Патч 1: фантомный quality в process_agent_result ──
    print("ПАТЧ 1 · pipeline.py: убираем эвристический quality score")
    apply_patch(PIPELINE_PATH, PIPELINE_OLD, PIPELINE_NEW,
                "process_agent_result() → on_agent_done() без эвристики", dry)
    print()

    # ── Патч 2: _apply_qa_feedback() → заглушка ──
    print("ПАТЧ 2 · pipeline.py: _apply_qa_feedback() → пустая заглушка")
    apply_patch(PIPELINE_PATH, APPLY_QA_OLD, APPLY_QA_NEW,
                "_apply_qa_feedback() мёртвый код → pass", dry)
    print()

    # ── Патч 3: on_agent_done() → только sensory ──
    print("ПАТЧ 3 · grondheim_memory.py: on_agent_done() → только sensory_memory")
    apply_patch(GRONDHEIM_PATH, GRONDHEIM_OLD, GRONDHEIM_NEW,
                "on_agent_done(): убираем sync_to_dna() и update_profile_vector()", dry)
    print()

    # ── Итог ──
    print(f"{'='*60}")
    if dry:
        print("DRY RUN завершён. Файлы не изменены.")
        print("Запусти без --dry-run чтобы применить патч.")
    else:
        print("ПАТЧ ПРИМЕНЁН.")
        print()
        print("Что изменилось:")
        print("  • on_agent_done() — только sensory_memory, без DNA")
        print("  • process_agent_result() — нет quality=0.3/0.5/0.6/0.8")
        print("  • on_agents_interact() — quality=0.5 нейтрально (факт передачи)")
        print("  • _apply_qa_feedback() — пустая заглушка")
        print()
        print("Единственный источник правды для DNA:")
        print("  _sync_feedback_scores_to_dna() → после реального QA score")
        print()
        print("Бэкапы:")
        print(f"  studio/workshop/pipeline.bak_{TIMESTAMP}")
        print(f"  studio/grondheim_memory.bak_{TIMESTAMP}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
