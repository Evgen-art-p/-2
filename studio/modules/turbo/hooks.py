# studio/modules/turbo/hooks.py — Хуки TURBO
# Студия «Шесть Пальцев» · 2026
#
# Кастомная логика TURBO-пайплайна.
# Пример минимального hooks.py — можно не менять.


def on_before_agent(state: dict, worker_id: str, context: str) -> str:
    """Контекст для TURBO-агентов — без изменений."""
    return context


def on_after_agent(state: dict, worker_id: str, human_text: str, meta: dict) -> dict:
    """Обработка результата TURBO — без изменений."""
    return {}
