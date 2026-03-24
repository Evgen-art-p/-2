# studio/ui_turbo.py — Редирект на Workshop в режиме TURBO
# Оригинальный файл (876 строк) был дубликатом workshop turbo mode.
# Вся функциональность TURBO живёт в ui_workshop.py (dept="turbo").
# Этот файл сохранён для совместимости с main.py роутом /turbo.

from nicegui import ui


def page_turbo():
    """Перенаправляет /turbo → /workshop?dept=turbo"""
    ui.navigate.to('/workshop?dept=turbo')
