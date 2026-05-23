# studio/assembly/pub_panel.py
# Студия «Шесть Пальцев» · 2026 · Спринт 20
#
# Pub Panel — "глупый пульт" в сборочном цехе.
# Показывает: статус поста + одна кнопка.
# Никакого ввода токенов. Никаких таймеров. Никакой логики.
# Вся логика — в broadcaster.py.
#
# Подключение в studio/assembly/__init__.py:
#   from studio.assembly.pub_panel import refresh_pub_panel
#   В конец load_md() добавить: refresh_pub_panel(state, refs)

from __future__ import annotations
from nicegui import ui
from studio.assembly.broadcaster import publish, get_status

_S = "font-size:11px; font-weight:700; letter-spacing:0.04em;"


def refresh_pub_panel(state: dict, refs: dict) -> None:
    """
    Точка входа из __init__.py / actions.py.
    Вызывается после load_md().
    """
    panel = refs.get("pub_panel")
    if panel is None:
        return

    client_id  = state.get("current_client") or state.get("client_id", "")
    project_id = state.get("project_id") or state.get("current_project_id", "")
    dept       = state.get("active_dept", "")

    panel.clear()
    with panel:
        _render(state, client_id, project_id, dept)


def _render(state: dict, client_id: str, project_id: str, dept: str) -> None:

    # ── Не SMM ──────────────────────────────────────────────────────────────
    if dept and dept != "social_mix":
        ui.html('<span style="color:rgba(255,255,255,0.15);font-size:10px;">н/д для этого цеха</span>')
        return

    # ── Нет клиента или проекта ──────────────────────────────────────────────
    if not client_id or not project_id:
        ui.html('<span style="color:rgba(255,255,255,0.2);font-size:10px;">Загрузи .md</span>')
        return

    # ── Статус с бэкенда ─────────────────────────────────────────────────────
    try:
        status = get_status(client_id, project_id)
    except Exception as e:
        ui.html(f'<span style="color:rgba(255,80,80,0.8);font-size:10px;">Ошибка: {e}</span>')
        return

    state_val = status["state"]

    if state_val == "idle":
        _render_idle(state, client_id, project_id)
    elif state_val == "published":
        _render_published(status)
    elif state_val == "scored":
        _render_scored(status)


# ── Ещё не опубликован ──────────────────────────────────────────────────────

def _render_idle(state: dict, client_id: str, project_id: str) -> None:
    def _on_click():
        try:
            result = publish(client_id, project_id)
            ui.notify(f"✅ Опубликовано · post_id {result['post_id']}", type="positive")
            # Перерисовываем
            state["_pub_refresh"] = True
            _do_refresh(state)
        except RuntimeError as e:
            ui.notify(str(e), type="negative", timeout=8000)
        except Exception as e:
            ui.notify(f"Ошибка публикации: {e}", type="negative", timeout=8000)

    ui.button("📤 ОПУБЛИКОВАТЬ", on_click=_on_click).props("flat dense").style(
        "width:100%; height:36px; border-radius:10px;"
        "border:1px solid rgba(0,255,136,0.4); background:rgba(0,255,136,0.08);"
        f"color:rgba(0,255,136,0.95); {_S}"
    )


# ── Опубликован, ждёт метрик ────────────────────────────────────────────────

def _render_published(status: dict) -> None:
    pub = (status.get("published_at") or "")[:16].replace("T", " ")
    forecast = status.get("tim_forecast")
    f_str = f"· прогноз Тима: {forecast}" if forecast is not None else ""

    with ui.element("div").style(
        "background:rgba(255,149,0,0.06); border:1px solid rgba(255,149,0,0.2);"
        "border-radius:10px; padding:10px 12px;"
    ):
        ui.html(
            f'<div style="color:rgba(255,149,0,0.9);{_S}">⏳ ОПУБЛИКОВАН</div>'
            f'<div style="color:rgba(255,255,255,0.25);font-size:10px;margin-top:4px;">'
            f'{pub} {f_str}</div>'
            f'<div style="color:rgba(255,255,255,0.2);font-size:10px;margin-top:2px;">'
            f'Metrics Daemon заберёт данные через ~24ч</div>'
        )


# ── Оценён, есть реальный viral_score ──────────────────────────────────────

def _render_scored(status: dict) -> None:
    score    = status.get("real_viral_score", 0) or 0
    forecast = status.get("tim_forecast")
    color    = "#00ff88" if score >= 7 else ("#ff9500" if score >= 4 else "#ff4444")

    with ui.element("div").style(
        "background:rgba(0,255,136,0.04); border:1px solid rgba(0,255,136,0.15);"
        "border-radius:10px; padding:10px 12px;"
    ):
        with ui.row().style("align-items:baseline; gap:4px;"):
            ui.html(f'<span style="color:{color};font-size:26px;font-weight:900;">{score}</span>')
            ui.html(f'<span style="color:rgba(255,255,255,0.3);font-size:12px;">/10</span>')

        if forecast is not None:
            diff     = round(score - forecast, 1)
            sign     = "+" if diff >= 0 else ""
            d_color  = "#00ff88" if diff >= 0 else "#ff4444"
            ui.html(
                f'<div style="color:rgba(255,255,255,0.3);font-size:10px;margin-top:4px;">'
                f'Тим прогнозировал: {forecast} '
                f'<span style="color:{d_color};">({sign}{diff})</span></div>'
            )


# ── Вспомогательный рефреш (вызывается после публикации) ───────────────────

def _do_refresh(state: dict) -> None:
    """Вызывает refresh через ui.timer один раз."""
    refs = state.get("_refs", {})
    if not refs:
        return

    def _once():
        refresh_pub_panel(state, refs)

    ui.timer(0.1, _once, once=True)
