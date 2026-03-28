# ═══════════════════════════════════════════════════════════
# ПАТЧ для studio/cabinet/agents.py
# Два фикса: 1) добавить 6 новых цехов  2) бары у резидентов
# ═══════════════════════════════════════════════════════════
#
# Применяй вручную или через поиск-замену в редакторе.
#
# ═══════════════════════════════════════════════════════════
# FIX 1: DEPARTMENTS — добавить 6 новых цехов
# ═══════════════════════════════════════════════════════════
#
# Найди строку ~83:
#
#   DEPARTMENTS = [
#       {"id": "residents",    "label": "резиденты",    "prefix": "", "is_permanent": True},
#       {"id": "turbo",        "label": "turbo",        "prefix": "T"},
#       {"id": "video_long",   "label": "video-long",   "prefix": "A"},
#       {"id": "video_shorts", "label": "video-shorts",  "prefix": "A"},
#       {"id": "social_mix",   "label": "social-mix",   "prefix": "A"},
#       {"id": "web_story",    "label": "web-story",    "prefix": "A"},
#   ]
#
# ЗАМЕНИ НА:
#
#   DEPARTMENTS = [
#       {"id": "residents",    "label": "резиденты",    "prefix": "", "is_permanent": True},
#       {"id": "turbo",        "label": "turbo",        "prefix": "T"},
#       {"id": "video_long",   "label": "video-long",   "prefix": "A"},
#       {"id": "video_shorts", "label": "video-shorts",  "prefix": "A"},
#       {"id": "social_mix",   "label": "social-mix",   "prefix": "A"},
#       {"id": "web_story",    "label": "web-story",    "prefix": "A"},
#       {"id": "clipmakers",   "label": "clipmakers",   "prefix": "A"},
#       {"id": "advertising",  "label": "advertising",  "prefix": "A"},
#       {"id": "emo_card",     "label": "emo-card",     "prefix": "A"},
#       {"id": "logo_design",  "label": "logo-design",  "prefix": "A"},
#       {"id": "market_hit",   "label": "market-hit",   "prefix": "A"},
#       {"id": "living_book",  "label": "living-book",  "prefix": "A"},
#   ]
#
#
# ═══════════════════════════════════════════════════════════
# FIX 2: render_resident_card — добавить мини-бары ДНК
# ═══════════════════════════════════════════════════════════
#
# Найди функцию render_resident_card (строка ~220).
# Текущий код:
#
#   def render_resident_card(agent: dict, is_active: bool, on_click) -> None:
#       """Компактная карточка резидента (верхняя зона)."""
#       cls = "cab-resident-card"
#       if is_active:
#           cls += " active"
#
#       card = ui.element("div").classes(cls)
#       card.on("click", lambda e, _id=agent["id"], _dept=agent.get("dept", ""): on_click(_id, _dept))
#
#       with card:
#           # Avatar
#           avatar_url = agent["avatar_url"]
#           if avatar_url:
#               ui.element("div").classes("cab-resident-avatar").style(
#                   f"background-image: url('{avatar_url}');"
#               )
#           else:
#               ui.element("div").classes("cab-resident-avatar").style(
#                   "display: flex; align-items: center; justify-content: center; "
#                   "font-family: 'JetBrains Mono'; font-size: 0.48rem; color: #c9a84c;"
#               ).props(f'inner-html="{agent["id"]}"')
#
#           ui.label(f'{agent["label"]}').classes("cab-resident-name")
#           ui.html(
#               f'<span class="cab-resident-status cab-status-resident">'
#               f'{agent["status_text"]}</span>'
#           )
#
#
# ЗАМЕНИ НА:

def render_resident_card(agent: dict, is_active: bool, on_click) -> None:
    """Компактная карточка резидента (верхняя зона) + мини-бары ДНК."""
    cls = "cab-resident-card"
    if is_active:
        cls += " active"

    card = ui.element("div").classes(cls)
    card.on("click", lambda e, _id=agent["id"], _dept=agent.get("dept", ""): on_click(_id, _dept))

    with card:
        # Avatar
        avatar_url = agent["avatar_url"]
        if avatar_url:
            ui.element("div").classes("cab-resident-avatar").style(
                f"background-image: url('{avatar_url}');"
            )
        else:
            ui.element("div").classes("cab-resident-avatar").style(
                "display: flex; align-items: center; justify-content: center; "
                "font-family: 'JetBrains Mono'; font-size: 0.48rem; color: #c9a84c;"
            ).props(f'inner-html="{agent["id"]}"')

        ui.label(f'{agent["label"]}').classes("cab-resident-name")

        # ═══ FIX: Мини-бары ДНК (как у рабочих агентов) ═══
        dynamic = agent.get("dynamic", {})
        if dynamic:
            with ui.element("div").classes("cab-bars").style("margin: 2px 0;"):
                for param in ["Respect", "Patience", "Stress", "Internal_Light"]:
                    val = float(dynamic.get(param, 0.5))
                    pct = round(val * 100)
                    color = BAR_COLORS.get(param, "#6c8cff")
                    lbl = BAR_LABELS.get(param, param[:3])
                    with ui.element("div").classes("cab-bar-group"):
                        ui.html(f'<div class="cab-bar-label">{lbl}</div>')
                        ui.html(
                            f'<div class="cab-bar-track">'
                            f'<div class="cab-bar-fill" style="width:{pct}%;background:{color}"></div>'
                            f'</div>'
                        )

        ui.html(
            f'<span class="cab-resident-status cab-status-resident">'
            f'{agent["status_text"]}</span>'
        )
