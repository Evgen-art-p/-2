#!/usr/bin/env python3
"""
patch_complaint_book_pipeline.py
Вставляет вызов complaint_book в pipeline.py после _sync_feedback_scores_to_dna().

Одна точка вставки — работает для всех 11 цехов автоматически,
потому что qa_agent берётся из manifest (A05 / A12 / A18 и т.д.).

Запуск: python patch_complaint_book_pipeline.py
"""

from pathlib import Path

PIPELINE_PATH = Path("studio/workshop/pipeline.py")

# ── Строка после которой вставляем ──
ANCHOR = "        _sync_feedback_scores_to_dna(client_slug, state.get(\"active_dept\", \"\"))"

# ── Что вставляем ──
INSERTION = """
        # ══ КНИГА ЖАЛОБ И БЛАГОДАРНОСТЕЙ · Спринт 25 ══
        # Проверяем каждого агента цеха на триггер жалобы.
        # qa_agent уже известен (A05/A12/A18 из manifest).
        # Благодарности — отдельный механизм, пишется из hooks.py когда
        # один агент явно спас другого (например, A08 закрыл слабый блок A05).
        try:
            from studio.complaint_book import check_and_write_complaint
            _book_dept = state.get("active_dept", "")
            _book_qa = qa_agent  # A05 / A12 / A18 — из manifest, уже правильный
            # Читаем feedback.json чтобы знать реальные оценки
            from pathlib import Path as _P
            import json as _J
            _fb_path = _P("clients") / client_slug / "feedback.json"
            if _fb_path.exists():
                _fb_data = _J.loads(_fb_path.read_text(encoding="utf-8"))
                _agents_fb = _fb_data.get("agents", {})
                for _book_agent_id, _book_fb in _agents_fb.items():
                    if _book_agent_id == _book_qa:
                        continue  # QA сам на себя не жалуется
                    _book_score = float(_book_fb.get("score", 5.0))
                    entry = check_and_write_complaint(
                        agent_id=_book_agent_id,
                        qa_agent_id=_book_qa,
                        qa_score=_book_score,
                        dept=_book_dept,
                    )
                    if entry:
                        print(f"[BOOK] 🗡 {_book_agent_id} написал жалобу (score={_book_score})")
        except Exception as _book_err:
            print(f"[BOOK] ⚠ Книга Жалоб: {_book_err}")
        # ══ END КНИГА ══"""


def patch():
    if not PIPELINE_PATH.exists():
        print(f"❌ Файл не найден: {PIPELINE_PATH}")
        return False

    content = PIPELINE_PATH.read_text(encoding="utf-8")

    if "КНИГА ЖАЛОБ И БЛАГОДАРНОСТЕЙ" in content:
        print("✅ Патч уже применён — пропускаем")
        return True

    if ANCHOR not in content:
        print(f"❌ Якорь не найден в pipeline.py:")
        print(f"   {ANCHOR}")
        print("   Возможно файл изменился — проверь вручную")
        return False

    new_content = content.replace(ANCHOR, ANCHOR + INSERTION)
    PIPELINE_PATH.write_text(new_content, encoding="utf-8")
    print(f"✅ Патч применён → {PIPELINE_PATH}")
    print(f"   Вставлено {len(INSERTION)} символов после _sync_feedback_scores_to_dna()")
    return True


if __name__ == "__main__":
    ok = patch()
    if ok:
        print("\nКнига Жалоб активна для всех цехов.")
        print("Следующий шаг: вкладка «Книга» в ui_cabinet.py")
    else:
        print("\n⚠ Патч не применён — проверь вывод выше")
