# studio/modules/social_mix/hooks.py
# Студия «Шесть Пальцев» · 2026
# v2.0 — Ревижн-лупы убраны. Два режима: POST (полный) / PLAN (стоп после A04).


def on_before_agent(state: dict, worker_id: str, context: str) -> str:
    """Модифицирует контекст агента перед вызовом.
    
    В v2.0 контекст не модифицируется — ревижн-лупы отключены.
    """
    return context


def on_after_agent(state: dict, worker_id: str, human_text: str, meta: dict) -> dict:
    """Проверяет, нужно ли остановить пайплайн.
    
    Режим PLAN (run_type == "content_plan"):
        Стоп после A04 — контент-план готов.
    
    Режим POST (всё остальное):
        Пайплайн идёт до A12.
    
    Возвращает:
        {} — продолжаем пайплайн
        {"action": "stop"} — остановить пайплайн
    """
    run_type = state.get("run_type", state.get("active_dept", ""))
    
    # PLAN: стоп после PRE-PROD (A04)
    if run_type == "content_plan" and worker_id == "A04":
        print(f"[HOOKS] 📋 PLAN: контент-план готов. Стоп после {worker_id}.")
        return {"action": "stop"}
    
    # POST: идём до конца
    return {}
