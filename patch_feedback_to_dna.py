#!/usr/bin/env python3
"""
patch_feedback_to_dna.py
════════════════════════
Студия «Шесть Пальцев» — Патч: feedback score → DNA агентов.

Что делает:
  Добавляет в pipeline.py функцию _sync_feedback_scores_to_dna()
  которая после save_feedback() читает реальные оценки из feedback.json
  и передаёт их в sync_to_dna() каждого агента.

  Было: quality_score считался примитивно (0.3 / 0.5 / 0.8 по deliverables)
  Стало: quality_score = реальная оценка от QA-агента (0.0–10.0 → 0.0–1.0)

  Два источника правды становятся одним.

Запуск из корня проекта:
  python patch_feedback_to_dna.py
"""

import shutil
from pathlib import Path

PIPELINE = Path("studio/workshop/pipeline.py")


def backup(path: Path):
    bak = path.with_suffix(path.suffix + ".bak_dna")
    shutil.copy2(path, bak)
    print(f"  📦 Бэкап: {bak.name}")


# ── Новая функция которую вставляем в pipeline.py ──────────────────

NEW_FUNCTION = '''

def _sync_feedback_scores_to_dna(client_slug: str, dept: str = ""):
    """
    Читает свежий feedback.json и синхронизирует реальные оценки QA
    в DNA каждого агента через sync_to_dna().

    Вызывается сразу после save_feedback() — один раз в конце рана.
    Это единственный источник правды для quality_score.

    score 0–4   → bad_work  (intensity = 1 - score/10)
    score 5–7   → нейтрально, лёгкий good_work
    score 8–10  → good_work (intensity = score/10)
    """
    if not _GRONDHEIM_ENABLED:
        return

    from pathlib import Path as _Path
    import json as _json

    feedback_path = _Path("clients") / client_slug / "feedback.json"
    if not feedback_path.exists():
        return

    try:
        feedback = _json.loads(feedback_path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[DNA-SYNC] Не удалось прочитать feedback: {e}")
        return

    agents_data = feedback.get("agents", {})
    if not agents_data:
        return

    print(f"[DNA-SYNC] Синхронизируем оценки → DNA ({len(agents_data)} агентов)")

    for agent_id, data in agents_data.items():
        score = data.get("score", 5.0)       # 0.0–10.0
        normalized = score / 10.0             # 0.0–1.0

        if score >= 8.0:
            event = "good_work"
            intensity = normalized
        elif score < 5.0:
            event = "bad_work"
            intensity = 1.0 - normalized      # чем хуже — тем сильнее
        else:
            event = "good_work"
            intensity = 0.4                   # нейтральная работа

        try:
            sync_to_dna(agent_id, event, intensity=intensity, dept=dept)
            emoji = "✅" if score >= 8 else "⚠️" if score >= 5 else "❌"
            print(f"  {emoji} {agent_id}: score={score} → {event}(i={intensity:.2f})")
        except Exception as e:
            print(f"  ⚠️ {agent_id}: sync_to_dna ошибка — {e}")

'''

# ── Место вставки: после _apply_qa_feedback ────────────────────────

# Маркер ПОСЛЕ которого вставляем новую функцию
INSERT_AFTER_MARKER = "def _apply_qa_feedback(state: dict, raw_result: str, qa_agent: str):"

# Альтернативный маркер (старое название если патч 1 не применялся)
INSERT_AFTER_MARKER_OLD = "def _apply_arthur_feedback(state: dict, raw_result: str):"

# ── Место вызова: после save_feedback() ───────────────────────────

OLD_CALL = """        try:
            save_feedback(client_slug, raw_result)
            print(f"[FEEDBACK] ✅ {worker_id} → feedback для {client_slug}")
        except Exception as _fb_err:
            print(f"[FEEDBACK] Ошибка: {_fb_err}")
        if _GRONDHEIM_ENABLED:
            _apply_qa_feedback(state, raw_result, qa_agent)"""

NEW_CALL = """        try:
            save_feedback(client_slug, raw_result)
            print(f"[FEEDBACK] ✅ {worker_id} → feedback для {client_slug}")
        except Exception as _fb_err:
            print(f"[FEEDBACK] Ошибка: {_fb_err}")
        if _GRONDHEIM_ENABLED:
            _apply_qa_feedback(state, raw_result, qa_agent)
        # ══ SYNC: реальные оценки QA → DNA агентов ══
        _sync_feedback_scores_to_dna(client_slug, state.get("active_dept", ""))"""

# Старый вариант вызова (если патч 1 не применялся)
OLD_CALL_LEGACY = """    if worker_id == "A12" and client_slug != "_sandbox":
        try:
            save_feedback(client_slug, raw_result)
        except Exception as _fb_err:
            print(f"[FEEDBACK] Ошибка сохранения: {_fb_err}")

        # ══ NEW: Артур оценивает коллег → влияет на их DNA ══
        if _GRONDHEIM_ENABLED:
            _apply_arthur_feedback(state, raw_result)
        # ══ END NEW ══"""

NEW_CALL_LEGACY = """    qa_agent = state.get("_qa_agent", "A12")
    if worker_id == qa_agent and client_slug != "_sandbox":
        try:
            save_feedback(client_slug, raw_result)
            print(f"[FEEDBACK] ✅ {worker_id} → feedback для {client_slug}")
        except Exception as _fb_err:
            print(f"[FEEDBACK] Ошибка: {_fb_err}")
        if _GRONDHEIM_ENABLED:
            _apply_arthur_feedback(state, raw_result)
        # ══ SYNC: реальные оценки QA → DNA агентов ══
        _sync_feedback_scores_to_dna(client_slug, state.get("active_dept", ""))"""


def patch_pipeline():
    print("\n── pipeline.py ──")

    if not PIPELINE.exists():
        print("  ❌ Файл не найден:", PIPELINE)
        return False

    text = PIPELINE.read_text(encoding="utf-8")

    # Уже пропатчен?
    if "_sync_feedback_scores_to_dna" in text:
        print("  ✅ Уже пропатчен, пропускаем")
        return True

    backup(PIPELINE)
    changed = False

    # ── Шаг 1: вставляем новую функцию ──────────────────────────

    # Ищем место вставки — после _apply_qa_feedback или _apply_arthur_feedback
    if INSERT_AFTER_MARKER in text:
        marker = INSERT_AFTER_MARKER
    elif INSERT_AFTER_MARKER_OLD in text:
        marker = INSERT_AFTER_MARKER_OLD
    else:
        marker = None

    if marker:
        # Находим конец функции (следующий def или async def на уровне модуля)
        idx = text.find(marker)
        # Ищем следующую функцию после idx
        import re
        next_def = re.search(r'\n(async def |def )', text[idx + len(marker):])
        if next_def:
            insert_pos = idx + len(marker) + next_def.start()
            text = text[:insert_pos] + NEW_FUNCTION + text[insert_pos:]
            print("  ✅ Функция _sync_feedback_scores_to_dna добавлена")
            changed = True
        else:
            # Вставляем в конец файла
            text = text + NEW_FUNCTION
            print("  ⚠️ Функция добавлена в конец файла")
            changed = True
    else:
        # Вставляем перед summarize_session
        if "async def summarize_session" in text:
            text = text.replace(
                "async def summarize_session",
                NEW_FUNCTION + "\nasync def summarize_session"
            )
            print("  ⚠️ Функция вставлена перед summarize_session")
            changed = True
        else:
            text = text + NEW_FUNCTION
            print("  ⚠️ Функция добавлена в конец файла")
            changed = True

    # ── Шаг 2: добавляем вызов после save_feedback() ─────────────

    if OLD_CALL in text:
        text = text.replace(OLD_CALL, NEW_CALL)
        print("  ✅ Вызов _sync_feedback_scores_to_dna добавлен")
        changed = True
    elif OLD_CALL_LEGACY in text:
        text = text.replace(OLD_CALL_LEGACY, NEW_CALL_LEGACY)
        print("  ✅ Вызов добавлен (legacy вариант)")
        changed = True
    else:
        # Мягкий поиск — просто после save_feedback
        if "save_feedback(client_slug, raw_result)" in text:
            text = text.replace(
                "save_feedback(client_slug, raw_result)",
                "save_feedback(client_slug, raw_result)\n        _sync_feedback_scores_to_dna(client_slug, state.get(\"active_dept\", \"\"))",
                1  # только первое вхождение
            )
            print("  ⚠️ Вызов добавлен (мягкий вариант — после save_feedback)")
            changed = True
        else:
            print("  ❌ Не нашли место для вызова — добавь вручную:")
            print("     _sync_feedback_scores_to_dna(client_slug, state.get('active_dept', ''))")
            print("     Сразу после save_feedback(client_slug, raw_result)")

    if changed:
        PIPELINE.write_text(text, encoding="utf-8")
        print("  ✅ pipeline.py сохранён")

    return changed


def verify():
    print("\n── Проверка ──")

    if not PIPELINE.exists():
        print("  ❌ pipeline.py не найден")
        return False

    text = PIPELINE.read_text(encoding="utf-8")
    ok = True

    if "_sync_feedback_scores_to_dna" in text:
        # Считаем сколько раз встречается — должно быть минимум 2 (def + вызов)
        count = text.count("_sync_feedback_scores_to_dna")
        if count >= 2:
            print(f"  ✅ pipeline.py: функция и вызов на месте ({count} вхождений)")
        else:
            print(f"  ⚠️ pipeline.py: только {count} вхождение (нужно минимум 2)")
            ok = False
    else:
        print("  ❌ pipeline.py: функция не найдена")
        ok = False

    return ok


def main():
    print("=" * 55)
    print("  Патч: feedback score → DNA агентов")
    print("  Студия «Шесть Пальцев»")
    print("=" * 55)

    if not Path("studio").exists():
        print(f"\n❌ Папка studio/ не найдена")
        print("   Запусти скрипт из корня проекта!")
        return

    patch_pipeline()

    print("\n" + "=" * 55)
    if verify():
        print("  🎉 Патч применён успешно!")
        print("\n  Что изменилось:")
        print("  • После каждого рана QA-агент оценивает команду")
        print("  • Реальный score (0–10) идёт в sync_to_dna каждого агента")
        print("  • score ≥ 8 → good_work → Stress↓, Light↑, streak↑")
        print("  • score < 5 → bad_work → Stress↑, Light↓, streak↓")
        print("  • Кабинет сразу показывает изменения в DNA барах")
        print("  • Один источник правды вместо двух параллельных")
        print("\n  Бэкап: pipeline.py.bak_dna")
    else:
        print("  ⚠️  Проверь файл вручную")
    print("=" * 55)


if __name__ == "__main__":
    main()
