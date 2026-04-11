# studio/modules/video_long/hooks.py — Хуки Видео Long
# Студия «Шесть Пальцев» · 2026
#
# Длинные видео. Checkpoint после A03 (сценарий).
# Правь этот файл вместо ui.py!


def on_before_agent(state: dict, worker_id: str, context: str) -> str:
    """Модифицирует контекст агента перед вызовом.
    
    Примеры:
    - if worker_id == "A01": context += "\n=== ДОППАРАМЕТРЫ ===\n..."
    - if worker_id == "A05": context += state.get("extra_data", "")
    """
    return context


def on_after_agent(state: dict, worker_id: str, human_text: str, meta: dict) -> dict:
    """Обрабатывает результат агента после вызова.
    
    Примеры:
    - if worker_id == "A03": state["script"] = human_text[:2000]
    - return {"human_text": modified_text} для перезаписи
    """
    return {}
