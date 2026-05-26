# studio/workshop/ui_cabinet.py — Кабинет Архитектора v2.2
# Роут: /cabinet
# Layout: [Агенты 300px] [Чат 1fr] [Правая панель 320px]
#
# v2.2:
#   - Режим диалога с агентом: промпт + знания + память + тулы
#   - Резиденты: полная память (конспекты) + веб-инструменты
#   - Рабочие: лёгкая память (последний диалог) + без тулов
#   - Авто-финализация при смене агента/промпта/очистке
#   - Двухзонная левая колонка: Резиденты (фикс) + Аккордеон цехов
#   - Глобальный поиск агентов

import re
import json
import asyncio
import base64
import mimetypes
from datetime import datetime

from nicegui import ui, app

from studio.cabinet.css import CABINET_CSS
from studio.cabinet.api import (
    call_openrouter, DEFAULT_MODEL, MODELS_CATALOG, TAVILY_KEY,
)
from studio.cabinet.tools import (
    TOOLS_SCHEMA, get_pending_nav,
)
from studio.cabinet.archive import (
    save_chat_archive, load_archive_list, load_chat_from_archive,
    delete_archive_chat, load_memory, save_memory, format_memory_context,
    finalize_agent_dialog, build_agent_context,
)
from studio.cabinet.prompts import load_cabinet_prompts
from studio.cabinet.agents import (
    DEPARTMENTS, CITY_DEPARTMENTS,
    list_dept_agents, list_all_agents, search_agents_global,
    render_agent_card, render_resident_card, render_agent_detail,
    _get_agent_home,
)
from studio.modules_registry import CURRENT_DEPT


def _format_size(size: int) -> str:
    if size < 1024:
        return f"{size} B"
    if size < 1048576:
        return f"{size / 1024:.1f} KB"
    return f"{size / 1048576:.1f} MB"


def page_cabinet() -> None:
    """Личный кабинет студии — /cabinet"""

    cabinet_prompts = load_cabinet_prompts()

    state = {
        "chat_history": [],
        "system_prompt": "",
        "knowledge": "",
        "active_prompt": None,
        "model": DEFAULT_MODEL,
        "waiting": False,
        "files": [],
        "selected_agent": None,
        "talking_agent": None,        # agent dict — АКТИВНЫЙ диалог
        "open_dept": None,
        "search_query": "",
        "all_agents": {},
        "active_tab": "agent",
    }

    refs = {
        "chat": None, "input": None,
        "prompt_bar": None, "prompt_name": None,
        "residents_list": None, "city_zone": None,
        "search_input": None, "search_results": None,
        "right_tabs": {}, "right_panels": {},
    }

    ui.add_head_html(f"<style>{CABINET_CSS}</style>")

    def reload_all_agents():
        state["all_agents"] = list_all_agents()
    reload_all_agents()

    # ═══ AGENT DIALOG HELPERS ═══

    def _is_agent_resident(agent):
        if not agent:
            return False
        return agent.get("is_resident", False)

    async def _finalize_current_dialog():
        agent = state["talking_agent"]
        if not agent or len(state["chat_history"]) < 2:
            return
        agent_id = agent["id"]
        dept = agent.get("dept", "")
        is_resident = _is_agent_resident(agent)

        summary = ""
        if is_resident:
            try:
                chat_text = "\n".join([
                    f"{'АРХИТЕКТОР' if m['role']=='user' else agent_id}: {m['content'][:300]}"
                    for m in state["chat_history"][-20:]
                ])
                summary_messages = [
                    {"role": "system", "content": (
                        f"Ты — архивариус агента {agent_id}. Сожми диалог в краткий конспект "
                        f"(3-5 предложений). Что обсуждали с Архитектором, решения, выводы. "
                        f"Пиши от третьего лица."
                    )},
                    {"role": "user", "content": f"Сожми этот диалог:\n\n{chat_text}"}
                ]
                summary = await call_openrouter(summary_messages, state["model"])
                print(f"[CABINET] 🧠 Конспект для {agent_id}: {len(summary)} симв.")
            except Exception as e:
                print(f"[CABINET] ⚠ Конспект {agent_id} не создан: {e}")

        finalize_agent_dialog(
            agent_id=agent_id, chat_history=state["chat_history"],
            summary=summary, model=state["model"],
            dept=dept, is_resident=is_resident,
        )

    # ═══ UPDATE FUNCTIONS ═══

    def update_chat():
        el = refs["chat"]
        if not el:
            return
        el.clear()
        with el:
            if not state["chat_history"]:
                with ui.element("div").classes("cab-empty"):
                    ui.html('<div class="cab-empty-icon">✦</div>')
                    ui.html('<div class="cab-empty-text">выбери промпт или начни диалог</div>')
            else:
                for msg in state["chat_history"]:
                    role = msg["role"]
                    cls = "cab-msg cab-msg-user" if role == "user" else "cab-msg cab-msg-ai"
                    if role == "user":
                        role_label = "ты"
                    elif state["talking_agent"]:
                        role_label = state["talking_agent"].get("label", "модель")
                    else:
                        role_label = "модель"
                    with ui.element("div").classes(cls):
                        ui.html(f'<div class="cab-msg-role">{role_label}</div>')
                        raw = msg["content"]
                        _nav_re = re.compile(r'(\n*→ <a href="[^"]*"[^>]*>[^<]*</a>)')
                        parts = _nav_re.split(raw)
                        rendered = ""
                        for part in parts:
                            if part and part.strip().startswith("→ <a "):
                                rendered += part
                            else:
                                rendered += (
                                    part.replace("&", "&amp;")
                                    .replace("<", "&lt;")
                                    .replace(">", "&gt;")
                                )
                        ui.html(f'<div class="cab-msg-text">{rendered}</div>')
                        t = msg.get("time", "")
                        if t:
                            ui.html(f'<div class="cab-msg-time">{t}</div>')
        if el:
            ui.run_javascript(
                'document.querySelector(".cab-chat").scrollTop = '
                'document.querySelector(".cab-chat").scrollHeight;'
            )

    def update_residents():
        el = refs["residents_list"]
        if not el:
            return
        el.clear()
        residents = state["all_agents"].get("residents", [])
        with el:
            if not residents:
                ui.html('<div style="text-align:center;padding:8px;font-family:JetBrains Mono;font-size:0.52rem;color:rgba(140,150,180,0.3)">нет резидентов</div>')
            else:
                for agent in residents:
                    is_active = state["selected_agent"] and state["selected_agent"]["id"] == agent["id"]
                    render_resident_card(agent, is_active, on_click=select_agent)

    def update_city_zone():
        el = refs["city_zone"]
        if not el:
            return
        el.clear()
        with el:
            for dept in CITY_DEPARTMENTS:
                dept_id = dept["id"]
                agents = state["all_agents"].get(dept_id, [])
                count = len(agents)
                is_open = state["open_dept"] == dept_id
                with ui.element("div").classes("cab-dept-section"):
                    hdr_cls = "cab-dept-header open" if is_open else "cab-dept-header"
                    hdr = ui.element("div").classes(hdr_cls)
                    hdr.on("click", lambda e, _did=dept_id: toggle_dept(_did))
                    with hdr:
                        with ui.element("div").classes("cab-dept-header-left"):
                            ui.html('<span class="cab-dept-arrow">▶</span>')
                            ui.html(f'<span class="cab-dept-name">{dept["label"]}</span>')
                        ui.html(f'<span class="cab-dept-count">{count}</span>')
                    body_cls = "cab-dept-body open" if is_open else "cab-dept-body"
                    with ui.element("div").classes(body_cls):
                        if not agents:
                            ui.html('<div style="text-align:center;padding:12px;font-family:JetBrains Mono;font-size:0.52rem;color:rgba(140,150,180,0.3)">пусто</div>')
                        else:
                            for agent in agents:
                                is_active = (state["selected_agent"] and
                                             state["selected_agent"]["id"] == agent["id"] and
                                             state["selected_agent"].get("dept") == agent.get("dept"))
                                render_agent_card(agent, is_active, on_click=select_agent)

    def update_search_results():
        el = refs["search_results"]
        if not el:
            return
        el.clear()
        query = state["search_query"]
        if not query:
            el.style("display: none")
            if refs["residents_list"]:
                refs["residents_list"].style("display: flex")
            if refs["city_zone"]:
                refs["city_zone"].style("display: block")
            return
        if refs["residents_list"]:
            refs["residents_list"].style("display: none")
        if refs["city_zone"]:
            refs["city_zone"].style("display: none")
        el.style("display: block")
        results = search_agents_global(query)
        with el:
            ui.html(f'<div style="padding:4px 6px;font-family:JetBrains Mono;font-size:0.52rem;color:rgba(140,150,180,0.4);margin-bottom:4px">найдено: {len(results)}</div>')
            if not results:
                ui.html('<div style="text-align:center;padding:16px;font-family:JetBrains Mono;font-size:0.56rem;color:rgba(140,150,180,0.3)">ничего не найдено</div>')
            else:
                for agent in results[:20]:
                    is_active = (state["selected_agent"] and
                                 state["selected_agent"]["id"] == agent["id"] and
                                 state["selected_agent"].get("dept") == agent.get("dept"))
                    render_agent_card(agent, is_active, on_click=select_agent)

    def on_search_change(e):
        state["search_query"] = (e.value or "").strip()
        update_search_results()

    def select_agent(agent_id, agent_dept=""):
        """Выбрать агента. agent_dept нужен для различения A01 в разных цехах."""
        # ole_mode -> home при клике из панели (fix9_ole.py)
        # open_ole_library() не проходит через select_agent, поэтому
        # библиотечный режим не сбрасывается при нажатии кнопки 📚
        state["ole_mode"] = "home"
        agent = None
        if agent_dept:
            for a in state["all_agents"].get(agent_dept, []):
                if a["id"] == agent_id:
                    agent = a
                    break
        if not agent:
            for dept_id, agents in state["all_agents"].items():
                found = next((a for a in agents if a["id"] == agent_id), None)
                if found:
                    agent = found
                    break
        state["selected_agent"] = agent
        update_residents()
        update_city_zone()
        if state["search_query"]:
            update_search_results()
        panel = refs["right_panels"].get("agent")
        if panel:
            panel.style("display: block")
        update_right_panel("agent")
        switch_tab("agent")
        # Скрываем карту — показываем чат
        _hide_map()

    def toggle_dept(dept_id):
        if state["open_dept"] == dept_id:
            state["open_dept"] = None
        else:
            state["open_dept"] = dept_id
        update_city_zone()

    # ═══ КАРТА ГОРОДА ═══

    def _show_map():
        """Показать карту, скрыть чат."""
        if refs.get("map_wrap"):
            refs["map_wrap"].style("display: flex")
        if refs.get("back_btn"):
            refs["back_btn"].classes(remove="visible")
        if refs.get("chat"):
            refs["chat"].style("display: none")
        if refs.get("input_area"):
            refs["input_area"].style("display: none")
        if refs.get("prompt_bar"):
            refs["prompt_bar"].classes(remove="visible")
        _refresh_map()

    def _hide_map():
        """Скрыть карту, показать чат."""
        if refs.get("map_wrap"):
            refs["map_wrap"].style("display: none")
        if refs.get("back_btn"):
            refs["back_btn"].classes(add="visible")
        if refs.get("chat"):
            refs["chat"].style("display: flex; flex: 1; flex-direction: column; overflow-y: auto; padding: 24px 32px")
        if refs.get("input_area"):
            refs["input_area"].style("display: block")

    def _load_map_locations() -> list[dict]:
        """Загрузить локации из catalog.json для карты."""
        try:
            from pathlib import Path
            catalog_path = Path("00_REGISTRY_NFT") / "catalog.json"
            if not catalog_path.exists():
                return []
            import json as _json
            catalog = _json.loads(catalog_path.read_text(encoding="utf-8"))
            locations = []
            for obj in catalog:
                if obj.get("Object_Type_Class") != "location":
                    continue
                # Пропускаем сам Грондхейм (весь город) — он не зона на карте
                if obj.get("ID_Object", "").startswith("0000_CITY"):
                    continue
                x = int(obj.get("Map_X", 0))
                y = int(obj.get("Map_Y", 0))
                w = int(obj.get("Map_W", 300))
                h = int(obj.get("Map_H", 200))
                if w < 10 or h < 10:
                    continue
                locations.append({
                    "id": obj.get("ID_Object", ""),
                    "name": obj.get("Official_Name", ""),
                    "x": x, "y": y, "w": w, "h": h,
                    "tags": obj.get("Style_Tags", ""),
                    "lighting": obj.get("Lighting", ""),
                    "capacity": int(obj.get("Capacity", 10)),
                })
            return locations
        except Exception as e:
            print(f"[MAP] Ошибка загрузки локаций: {e}")
            return []

    def _find_agent_zone(agent, dept_id, last_walk_loc, locations_by_name):
        """Определить в какой зоне находится агент.
        Приоритет: свежая прогулка (< 30 мин) > дом.
        Резиденты → Высотка, рабочие → Квартал Мастеров.
        """
        def _fuzzy_find(keyword):
            """Найти локацию по вхождению ключевого слова."""
            kw = keyword.lower().strip().rstrip(".")
            for loc_name, loc in locations_by_name.items():
                clean = loc_name.lower().strip().rstrip(".")
                if kw in clean or clean in kw:
                    return loc
            return None

        # Если агент гулял — проверяем свежесть прогулки
        if last_walk_loc:
            # Парсим время из формата "[2026-03-23 17:50] Локация: ..."
            try:
                import re as _re
                m = _re.match(r'\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2})\]', last_walk_loc)
                if m:
                    walk_time = datetime.strptime(m.group(1), "%Y-%m-%d %H:%M")
                    minutes_ago = (datetime.now() - walk_time).total_seconds() / 60
                    if minutes_ago < 30:
                        # Ещё гуляет — показываем в локации прогулки
                        # Извлекаем название локации после "]"
                        loc_part = last_walk_loc.split("]", 1)[-1].split(":")[0].strip()
                        found = _fuzzy_find(loc_part)
                        if found:
                            return found
                    # Прогулка старше 30 мин — вернулся домой
            except Exception:
                pass

        # Дом: резиденты → Высотка, рабочие → Квартал Мастеров
        is_resident = agent.get("is_resident", False) or dept_id == "residents"
        home_keyword = "Высотка" if is_resident else "Квартал Мастеров"
        return _fuzzy_find(home_keyword)

    def _refresh_map():
        """Обновить агентов и погоду на карте."""
        try:
            from studio.city_walker import load_city_state, get_agent_last_walk
            from studio.cabinet.agents import _get_agent_dna, DEPARTMENTS

            city = load_city_state()
            weather = city.get("weather", "ясно")
            walk_count = city.get("walk_count", 0)

            if refs.get("map_weather"):
                refs["map_weather"].content = f'<span class="cab-map-weather">☁ {weather} · прогулок: {walk_count}</span>'

            if not refs.get("map_canvas"):
                return

            # ═══ ЛОКАЦИИ ИЗ КАТАЛОГА ═══
            locations = _load_map_locations()
            locations_by_name = {loc["name"]: loc for loc in locations}

            # Нейтральный цвет для всех зон (пока без индивидуальных цветов)
            zone_color = "rgba(180,200,220,0.25)"
            zone_bg = "rgba(180,200,220,0.04)"
            zone_text = "rgba(180,200,220,0.6)"

            html = ""

            # Рендер локаций
            for loc in locations:
                html += (
                    f'<div class="cab-map-sector" style="'
                    f'left:{loc["x"]}px;top:{loc["y"]}px;'
                    f'width:{loc["w"]}px;height:{loc["h"]}px;'
                    f'border-color:{zone_color};'
                    f'background:{zone_bg};'
                    f'color:{zone_text}">'
                    f'{loc["name"]}</div>'
                )

            if not locations:
                html += (
                    '<div style="position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);'
                    'font-family:JetBrains Mono;font-size:0.7rem;color:rgba(180,200,220,0.3);'
                    'text-align:center;pointer-events:none">'
                    '📍 Создай локации в Странице Жизни<br>'
                    'чтобы разметить карту</div>'
                )

            # ═══ АГЕНТЫ — ПРИВЯЗКА К ЗОНАМ ═══
            # Счётчик агентов в каждой зоне (для раскладки внутри зоны)
            zone_counters = {loc["name"]: 0 for loc in locations}

            for dept in DEPARTMENTS:
                dept_id = dept["id"]
                agents = state["all_agents"].get(dept_id, [])

                for agent in agents:
                    aid = agent["id"]
                    name = agent.get("label", aid)
                    icon = agent.get("avatar_icon", "🤖")

                    # Читаем DNA для стресса
                    dna = _get_agent_dna(aid, dept_id)
                    dynamic = dna.get("dynamic", {})
                    stress = float(dynamic.get("Stress", 0))
                    selected = (state.get("selected_agent") and
                                state["selected_agent"]["id"] == aid and
                                state["selected_agent"].get("dept") == dept_id)

                    # Последняя локация из sensory memory
                    last_walk = ""
                    try:
                        last_walk = get_agent_last_walk(dept_id, aid)
                        if last_walk and len(last_walk) > 40:
                            last_walk = last_walk[:40] + "..."
                    except Exception:
                        pass

                    # Определяем зону агента
                    zone = _find_agent_zone(agent, dept_id, last_walk, locations_by_name)

                    if zone:
                        # Раскладка внутри зоны: плотная сетка для точек
                        idx = zone_counters.get(zone["name"], 0)
                        zone_counters[zone["name"]] = idx + 1
                        step_x = min(35, max(18, zone["w"] // 5))
                        step_y = min(30, max(18, zone["h"] // 5))
                        cols = max(1, (zone["w"] - 10) // step_x)
                        col = idx % cols
                        row = idx // cols
                        ax = zone["x"] + 6 + col * step_x
                        ay = zone["y"] + 22 + row * step_y
                    else:
                        # Нет подходящей зоны — рисуем внизу карты
                        ax = 100 + hash(aid) % 600
                        ay = 1350 + hash(aid) % 100

                    cls = "cab-map-agent"
                    if selected: cls += " selected"
                    elif stress > 0.7: cls += " stressed"

                    html += (
                        f'<div class="{cls}" '
                        f'style="left:{ax}px;top:{ay}px" '
                        f'data-agent-id="{aid}" data-dept="{dept_id}" '
                        f'onclick="cabSelectAgent(\'{aid}\',\'{dept_id}\')">'
                        f'{icon}'
                        f'<div class="cab-map-agent-label">{aid} {name}</div>'
                        f'{"<div class=\'cab-map-agent-loc\'>" + last_walk + "</div>" if last_walk else ""}'
                        f'</div>'
                    )

            refs["map_canvas"].clear()
            with refs["map_canvas"]:
                ui.html(html)

        except Exception as e:
            print(f"[MAP] Ошибка рендера: {e}")
            import traceback
            traceback.print_exc()

    async def _do_city_walk():
        """Запустить прогулку всех агентов."""
        try:
            from studio.cabinet.tools import exec_city_walk
            ui.notify("🚶 Агенты выходят в город...", type="info")
            result = await exec_city_walk()
            try:
                ui.notify("✅ Прогулка завершена", type="positive")
                _refresh_map()
                reload_all_agents()
                update_residents()
                update_city_zone()
                # Показываем результат в чате если есть активный агент
                if state.get("selected_agent"):
                    state["chat_history"].append({
                        "role": "assistant",
                        "content": result,
                        "time": datetime.now().strftime("%H:%M")
                    })
                    update_chat()
            except Exception:
                # Клиент мог быть удалён (страница обновлена)
                print("[CITY] ⚠ UI обновлён во время прогулки — результат записан в память")
        except Exception as e:
            try:
                ui.notify(f"❌ {e}", type="negative")
            except Exception:
                print(f"[CITY] ❌ {e}")

    # ═══ RIGHT PANEL ═══

    def update_right_panel(tab_name):
        el = refs["right_panels"].get(tab_name)
        if not el:
            return
        el.clear()
        with el:
            if tab_name == "agent":
                _render_agent_tab()
            elif tab_name == "matrix":
                _render_matrix_tab()
            elif tab_name == "files":
                _render_files_tab()
            elif tab_name == "prompts":
                _render_prompts_tab()
            elif tab_name == "archive":
                _render_archive_tab()
        try:
            el.update()
        except Exception:
            pass

    def _render_agent_tab():
        agent = state["selected_agent"]
        if not agent:
            ui.html('<div style="text-align:center;padding:32px;font-family:JetBrains Mono;font-size:0.56rem;color:rgba(140,150,180,0.3)">выбери агента слева</div>')
            return
        _dept = agent.get("dept", "")
        # OLE: ветка library/home (fix6)
        if agent.get("id") == "004_OLE":
            if state.get("ole_mode") == "library":
                _render_library_widget()
                return
            # Клик на Оле из панели — явно home-режим
            def _ole_home_talk(aid, _d=_dept):
                state["ole_mode"] = "home"
                talk_to_agent(aid, _d)
            render_agent_detail(agent, on_talk=_ole_home_talk)
            return
        render_agent_detail(agent, on_talk=lambda aid, _d=_dept: talk_to_agent(aid, _d))

    def _render_matrix_tab():
        """Живая матрица ДНК — все агенты всех цехов."""
        _MATRIX_CSS = """
        <style>
        .mtx-wrap{padding:4px 4px;overflow-y:auto;max-height:calc(100vh - 130px);scrollbar-width:thin}
        .mtx-title{font-family:JetBrains Mono;font-size:0.72rem;color:#00f2ff;text-transform:uppercase;letter-spacing:2px;padding:10px 0 8px;text-align:center;text-shadow:0 0 10px rgba(0,242,255,0.3)}
        .mtx-dept{font-family:JetBrains Mono;font-size:0.62rem;color:#d4af37;padding:10px 8px 4px;text-transform:uppercase;letter-spacing:1px}
        .mtx-tbl{width:100%;border-collapse:collapse;font-family:JetBrains Mono;font-size:0.62rem}
        .mtx-tbl th{padding:6px 5px;color:rgba(201,168,76,0.8);font-weight:600;text-align:center;border-bottom:1px solid rgba(0,242,255,0.15);font-size:0.56rem;text-transform:uppercase}
        .mtx-tbl th:first-child{text-align:left;padding-left:8px}
        .mtx-tbl td{padding:5px 5px;text-align:center;border-bottom:1px solid rgba(255,255,255,0.04)}
        .mtx-tbl td:first-child{text-align:left;color:rgba(220,225,240,0.9);font-weight:500;padding-left:8px}
        .mtx-tbl tr:hover{background:rgba(0,242,255,0.06)}
        .mtx-val{font-weight:500;font-size:0.6rem}
        .mtx-bar{display:block;height:3px;border-radius:2px;margin-top:2px}
        .mtx-cell{display:flex;flex-direction:column;align-items:center;gap:1px}
        .mtx-temp{color:rgba(240,240,255,0.95);font-weight:600;font-size:0.6rem}
        .mtx-streak-pos{color:#50fa7b;font-weight:700;font-size:0.62rem}
        .mtx-streak-neg{color:#ff5555;font-weight:700;font-size:0.62rem}
        .mtx-streak-zero{color:rgba(140,150,180,0.4);font-size:0.58rem}
        .mtx-empty{color:rgba(140,150,180,0.3);font-size:0.56rem}
        </style>
        """
        ui.html(_MATRIX_CSS)
        ui.html('<div class="mtx-title">⚡ матрица днк</div>')

        # Цвета баров по параметру
        BAR_PARAM_COLORS = {
            "Respect": "#a78bfa",
            "Patience": "#c9a84c",
            "Stress": "#f87171",
            "Internal_Light": "#fbbf24",
        }

        def _val_color(param, val):
            """Цвет числа по опасности."""
            if param == "Stress":
                if val > 0.8: return "#ff5555"
                if val > 0.5: return "#fbbf24"
                return "#50fa7b"
            else:
                if val < 0.2: return "#ff5555"
                if val < 0.4: return "#fbbf24"
                return "#50fa7b"

        def _cell_html(param, val):
            pct = max(4, int(val * 100))
            num_color = _val_color(param, val)
            bar_color = BAR_PARAM_COLORS.get(param, "#6c8cff")
            return (
                f'<div class="mtx-cell">'
                f'<span class="mtx-val" style="color:{num_color}">{val:.2f}</span>'
                f'<span class="mtx-bar" style="width:{pct}%;background:{bar_color}"></span>'
                f'</div>'
            )

        def _temp_html(stress, light):
            t = 0.7 - stress * 0.4 + (light - 0.5) * 0.2
            t = round(max(0.2, min(1.0, t)), 2)
            return f'<span class="mtx-temp">{t}</span>'

        with ui.element("div").classes("mtx-wrap"):
            for dept_info in DEPARTMENTS:
                dept_id = dept_info["id"]
                agents = state["all_agents"].get(dept_id, [])
                if not agents:
                    continue

                prefix = "✦ " if dept_info.get("is_permanent") else "▸ "
                ui.html(f'<div class="mtx-dept">{prefix}{dept_info["label"]} ({len(agents)})</div>')

                rows_html = ""
                for a in agents:
                    dyn = a.get("dynamic", {})
                    name = f'{a["id"]} {a["label"][:10]}'
                    if not dyn:
                        rows_html += f'<tr><td>{name}</td><td colspan="6" class="mtx-empty">—</td></tr>'
                        continue

                    rsp = float(dyn.get("Respect", 1.0))
                    pat = float(dyn.get("Patience", 1.0))
                    stress = float(dyn.get("Stress", 0.0))
                    light = float(dyn.get("Internal_Light", 0.8))
                    streak = int(dyn.get("streak", 0))

                    if streak > 0:
                        streak_html = f'<span class="mtx-streak-pos">+{streak}</span>'
                    elif streak < 0:
                        streak_html = f'<span class="mtx-streak-neg">{streak}</span>'
                    else:
                        streak_html = '<span class="mtx-streak-zero">0</span>'

                    rows_html += (
                        f'<tr>'
                        f'<td>{name}</td>'
                        f'<td>{_cell_html("Respect", rsp)}</td>'
                        f'<td>{_cell_html("Patience", pat)}</td>'
                        f'<td>{_cell_html("Stress", stress)}</td>'
                        f'<td>{_cell_html("Internal_Light", light)}</td>'
                        f'<td>{streak_html}</td>'
                        f'<td>{_temp_html(stress, light)}</td>'
                        f'</tr>'
                    )

                ui.html(
                    f'<table class="mtx-tbl">'
                    f'<thead><tr><th>агент</th><th>rsp</th><th>pat</th><th>str</th><th>lgt</th><th>ser</th><th>t°</th></tr></thead>'
                    f'<tbody>{rows_html}</tbody>'
                    f'</table>'
                )

        # Кнопка обновления
        def _refresh_matrix():
            reload_all_agents()
            update_right_panel("matrix")
            ui.notify("Матрица обновлена", type="info")

        with ui.element("div").style("text-align:center;padding:10px 0 4px;"):
            ui.button("🔄 обновить", on_click=_refresh_matrix).props("flat dense").style(
                "font-family:JetBrains Mono;font-size:0.58rem;color:rgba(0,242,255,0.6);"
                "border:1px solid rgba(0,242,255,0.15);border-radius:6px;padding:5px 16px;"
            )

    def _render_files_tab():
        if not state["files"]:
            ui.html('<div style="text-align:center;padding:16px;font-family:JetBrains Mono;font-size:0.56rem;color:rgba(140,150,180,0.3)">загруженные файлы<br>появятся здесь</div>')
        else:
            for f in state["files"]:
                with ui.element("div").classes("cab-file-item"):
                    ui.label(f["name"]).style("color:rgba(220,225,240,0.85);font-family:JetBrains Mono;font-size:0.62rem;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;flex:1;").props(f'title="{f["name"]}"')
                    ui.label(_format_size(f["size"])).style("color:rgba(140,150,180,0.35);font-family:JetBrains Mono;font-size:0.52rem;margin:0 8px;")
                    def _make_remove(fi):
                        def _remove():
                            state["files"] = [x for x in state["files"] if x is not fi]
                            update_right_panel("files")
                        return _remove
                    ui.button("✕", on_click=_make_remove(f)).props("flat dense size=xs").style("color:rgba(140,150,180,0.35);min-width:24px;font-size:0.6rem;")
        ui.upload(label="⇧ перетащи или выбери", multiple=True, auto_upload=True, on_upload=handle_upload).props('accept="image/*,.pdf,.txt,.md,.csv,.json" flat bordered').style("margin-top:8px;background:#08090e;border:1.5px dashed rgba(108,140,255,0.15);border-radius:10px;color:rgba(180,190,220,0.6);font-family:JetBrains Mono;font-size:0.62rem;")

    def _render_prompts_tab():
        file_count = sum(1 for pid in cabinet_prompts if pid != "free")
        ui.html(f'<div style="padding:4px 8px;font-family:JetBrains Mono;font-size:0.52rem;color:rgba(140,150,180,0.35);margin-bottom:4px">{len(cabinet_prompts)} промптов · {file_count} из файлов</div>')
        for pid, p in cabinet_prompts.items():
            is_active = pid == state["active_prompt"]
            cls = "cab-prompt-item active" if is_active else "cab-prompt-item"
            btn = ui.element("div").classes(cls)
            with btn:
                label = p["name"]
                if p.get("knowledge"):
                    label += "  📚"
                ui.label(label).style("font-size:inherit;color:inherit;cursor:pointer;pointer-events:none;")
            btn.on("click", lambda e, _pid=pid: select_prompt(_pid))

    def _render_archive_tab():
        archive = load_archive_list()
        if not archive:
            ui.html('<div style="text-align:center;padding:24px;font-family:JetBrains Mono;font-size:0.56rem;color:rgba(140,150,180,0.3)">архив пуст</div>')
        else:
            for item in archive:
                with ui.element("div").classes("cab-archive-item"):
                    with ui.element("div").style("flex:1;min-width:0;"):
                        ui.label(item["title"]).style("font-family:JetBrains Mono;font-size:0.62rem;color:rgba(220,225,240,0.85);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;")
                        date_str = ""
                        try:
                            dt = datetime.fromisoformat(item["date"])
                            date_str = dt.strftime("%d %b %H:%M")
                        except Exception:
                            date_str = item.get("date", "")[:16]
                        ui.label(f'{date_str} · {item["prompt"]} · {item["msg_count"]} сообщ.').style("font-family:JetBrains Mono;font-size:0.48rem;color:rgba(140,150,180,0.35);")
                    with ui.row().style("gap:4px;flex-shrink:0;"):
                        def _make_load(fn):
                            def _load():
                                data = load_chat_from_archive(fn)
                                if not data:
                                    return
                                state["chat_history"] = [{"role":m["role"],"content":m["content"],"time":""} for m in data.get("messages",[])]
                                pid = data.get("prompt","")
                                if pid and pid in cabinet_prompts:
                                    select_prompt(pid)
                                if data.get("model"):
                                    state["model"] = data["model"]
                                update_chat()
                                ui.notify("Чат загружен", type="positive")
                                switch_tab("prompts")
                            return _load
                        ui.button("↩", on_click=_make_load(item["file"])).props("flat dense size=xs").style("color:rgba(108,140,255,0.6);min-width:24px;font-size:0.65rem;")
                        def _make_del(fn):
                            def _del():
                                delete_archive_chat(fn)
                                update_right_panel("archive")
                                ui.notify("Удалён", type="info")
                            return _del
                        ui.button("✕", on_click=_make_del(item["file"])).props("flat dense size=xs").style("color:rgba(140,150,180,0.35);min-width:24px;font-size:0.6rem;")

    # ═══ ACTIONS ═══

    def select_prompt(pid):
        p = cabinet_prompts.get(pid)
        if not p:
            return
        if state["talking_agent"] and len(state["chat_history"]) >= 2:
            ui.timer(0, lambda: _finalize_current_dialog(), once=True)
        state["talking_agent"] = None
        state["active_prompt"] = pid
        state["system_prompt"] = p.get("system", "")
        state["knowledge"] = p.get("knowledge", "")
        if refs["prompt_bar"]:
            refs["prompt_bar"].style("display: flex")
        if refs["prompt_name"]:
            refs["prompt_name"].set_text(p["name"])
        update_right_panel("prompts")

    def deselect_prompt():
        if state["talking_agent"] and len(state["chat_history"]) >= 2:
            ui.timer(0, lambda: _finalize_current_dialog(), once=True)
        state["talking_agent"] = None
        state["active_prompt"] = None
        state["system_prompt"] = ""
        state["knowledge"] = ""
        if refs["prompt_bar"]:
            refs["prompt_bar"].style("display: none")
        update_right_panel("prompts")

    def switch_tab(tab_name):
        state["active_tab"] = tab_name
        for name, el in refs["right_panels"].items():
            if el:
                el.style(f'display: {"block" if name == tab_name else "none"}')
        for name, el in refs["right_tabs"].items():
            if el:
                el.classes(replace="cab-tab active" if name == tab_name else "cab-tab")
        if tab_name == "archive":
            update_right_panel("archive")
        if tab_name == "matrix":
            reload_all_agents()
            update_right_panel("matrix")

    def talk_to_agent(agent_id, agent_dept=""):
        """Начать разговор с агентом — полноценный режим диалога."""
        if state["talking_agent"] and len(state["chat_history"]) >= 2:
            ui.timer(0, lambda: _finalize_current_dialog(), once=True)

        agent = None
        # Сначала ищем в конкретном цехе если dept передан
        if agent_dept:
            for a in state["all_agents"].get(agent_dept, []):
                if a["id"] == agent_id:
                    agent = a
                    break
        # Фоллбэк: поиск по всем цехам
        if not agent:
            for dept_id, agents in state["all_agents"].items():
                found = next((a for a in agents if a["id"] == agent_id), None)
                if found:
                    agent = found
                    break
        if not agent:
            return

        agent_id = agent["id"]
        dept = agent.get("dept", "")
        is_resident = _is_agent_resident(agent)
        label = agent.get("label", agent_id)

        # System prompt — dlya Ole uchityvaem rezhim (patch_ole.py)
        if agent_id == "004_OLE":
            from studio.residents_manager import get_ole_system_prompt as _ole_sys
            home_prompt = _ole_sys(state.get("ole_mode", "home")) or _get_agent_home(agent_id, dept)
        else:
            home_prompt = _get_agent_home(agent_id, dept)
        if not home_prompt:
            dna = agent.get("dna", {})
            static = dna.get("static", {})
            traits = ", ".join(f"{k}={v}" for k, v in static.items()) if static else "стандартный характер"
            home_prompt = (
                f"Ты — {label} ({agent_id}), агент студии «Шесть пальцев».\n"
                f"Характер: {traits}.\n"
                f"Отвечай от первого лица, в своём стиле. Будь собой."
            )

        # База знаний
        from studio.cabinet.prompts import KNOWLEDGE_DIR_CAB
        knowledge = ""
        kb_file = KNOWLEDGE_DIR_CAB / f"{agent_id.lower()}.md"
        if kb_file.exists():
            try:
                knowledge = kb_file.read_text(encoding="utf-8").strip()
            except Exception:
                pass

        # Память агента (кабинетная — конспекты диалогов)
        agent_memory_ctx = build_agent_context(agent_id, dept, is_resident)

        # Грондхейм: душа агента (якоря + ДНК + геопозиция + резонанс + оперативная память)
        soul_ctx = ""
        try:
            from studio.grondheim_memory import on_agent_wake
            soul_ctx = on_agent_wake(agent_id, dept) or ""
            if soul_ctx:
                print(f"[CABINET] 🧬 Душа {agent_id}: {len(soul_ctx)} симв.")
        except Exception as e:
            print(f"[CABINET] ⚠ Грондхейм-память не загружена: {e}")

        # Собираем system prompt
        sys_parts = [home_prompt]
        if knowledge:
            sys_parts.append(f"\n[БАЗА ЗНАНИЙ]\n{knowledge}")
        if soul_ctx:
            sys_parts.append(f"\n{soul_ctx}")
        if agent_memory_ctx:
            sys_parts.append(f"\n{agent_memory_ctx}")

         # Библиотека: каталог для Оле
        if agent_id == "004_OLE":
            try:
                from studio.cabinet.agents import _get_library_context
                library_ctx = _get_library_context()
                if library_ctx:
                    sys_parts.append(f"\n{library_ctx}")
                    print(f"[CABINET] 📚 Каталог библиотеки для Оле: {len(library_ctx)} симв.")
            except Exception as e:
                print(f"[CABINET] ⚠ Каталог библиотеки не загружен: {e}")   

        # Tools hint — только для резидентов
        if is_resident:
            sys_parts.append(
                "\n\n[ИНСТРУМЕНТЫ]\n"
                "У тебя есть инструменты:\n"
                "- navigate — открыть страницу студии\n"
                "- list_clients / create_client / get_client_info — клиенты\n"
                "- view_assets — каталог ассетов\n"
                "- list_agents / get_agent_state — состояние агентов\n"
                "- update_agent_dynamic — изменить параметры агента\n"
                "- find_stressed_agents — найти агентов в стрессе\n"
                "- get_agent_soul — полная личная память агента\n"
                "- get_relationships — карта отношений агента\n"
                "- record_interaction — записать взаимодействие\n"
                "- city_pulse — пульс города\n"
                "- jem_digest — дайджест для администратора\n"
                "- search_library — поиск книг в библиотеке по тегам\n"
                "- browse_shelf — посмотреть полку секции\n"
                "- read_book_excerpt — прочитать начало книги\n"
                "- library_stats — статистика библиотеки\n"
                "- recommend_for_agent — подобрать книгу для агента\n"
                "- web_search — поиск в интернете\n"
                "- fetch_url — загрузить веб-страницу\n"
                "Используй когда уместно. Не описывай — делай.\n"
                "Когда просят 'душу' или 'память' агента — вызывай get_agent_soul.\n"
                "Когда просят 'пульс города' — вызывай city_pulse.\n"
                "Отвечай на русском."
            )

        state["talking_agent"] = agent
        state["active_prompt"] = f"agent_{agent_id}"
        state["system_prompt"] = "\n".join(sys_parts)
        state["knowledge"] = ""
        state["chat_history"] = []

        bar_label = f"{'✦' if is_resident else '⚡'} {label}"
        if refs["prompt_bar"]:
            refs["prompt_bar"].style("display: flex")
        if refs["prompt_name"]:
            refs["prompt_name"].set_text(bar_label)

        greeting = agent.get("greeting", f"{label} на связи.")
        state["chat_history"].append({
            "role": "assistant", "content": greeting,
            "time": datetime.now().strftime("%H:%M"),
        })
        update_chat()

        print(f"[CABINET] 💬 Диалог с {agent_id} ({label}) | "
              f"{'резидент' if is_resident else 'рабочий'} | "
              f"память: {len(agent_memory_ctx)} симв. | "
              f"душа: {len(soul_ctx)} симв.")

    async def handle_upload(e):
        for upload in e.files if hasattr(e, 'files') else [e]:
            name = upload.name
            content = upload.content.read() if hasattr(upload.content, 'read') else upload.content
            size = len(content)
            b64 = base64.b64encode(content).decode()
            media_type = mimetypes.guess_type(name)[0] or "application/octet-stream"
            is_image = media_type.startswith("image/")
            is_text = any(name.endswith(ext) for ext in [".txt", ".md", ".csv", ".json"])
            text_content = content.decode("utf-8", errors="replace") if is_text else None
            state["files"].append({"name": name, "size": size, "path": name, "base64": b64, "media_type": media_type, "is_image": is_image, "is_text": is_text, "text_content": text_content})
        update_right_panel("files")
        switch_tab("files")
        ui.notify(f"📎 {len(state['files'])} файлов", type="positive")

    def on_model_change(e):
        state["model"] = e.value

    async def save_chat():
        if len(state["chat_history"]) < 2:
            ui.notify("Нечего сохранять", type="warning")
            return
        if state.get("_saving"):
            return
        state["_saving"] = True
        try:
            if state["talking_agent"]:
                await _finalize_current_dialog()

            prompt_id = state["active_prompt"] or "free"
            save_chat_archive(state["chat_history"], prompt_id, state["model"])
            ui.notify("💾 Чат сохранён", type="positive")
            switch_tab("archive")
            update_right_panel("archive")

            if not state["talking_agent"]:
                try:
                    chat_text = "\n".join([f"{'USER' if m['role']=='user' else 'AI'}: {m['content'][:300]}" for m in state["chat_history"][-20:]])
                    summary_messages = [
                        {"role": "system", "content": "Ты — архивариус. Сожми диалог в краткий конспект (3-5 предложений). Только факты: что обсуждали, решения, выводы. Без воды."},
                        {"role": "user", "content": f"Сожми этот чат:\n\n{chat_text}"}
                    ]
                    summary = await call_openrouter(summary_messages, state["model"])
                    entries = load_memory()
                    entries.append({"date": datetime.now().strftime("%Y-%m-%d %H:%M"), "prompt": prompt_id, "summary": summary.strip()})
                    save_memory(entries)
                    print(f"[CABINET] 🧠 Конспект сохранён ({len(summary)} симв.)")
                except Exception as e:
                    print(f"[CABINET] ⚠ Конспект не создан: {e}")
        finally:
            state["_saving"] = False

    async def clear_chat():
        if state["talking_agent"] and len(state["chat_history"]) >= 2:
            await _finalize_current_dialog()
        state["talking_agent"] = None
        state["chat_history"].clear()
        if refs["prompt_bar"]:
            refs["prompt_bar"].style("display: none")
        state["active_prompt"] = None
        state["system_prompt"] = ""
        state["knowledge"] = ""
        update_chat()

    async def send():
        inp = refs["input"]
        if not inp:
            return
        text = inp.value.strip()
        if not text or state["waiting"]:
            return
        inp.set_value("")

        now = datetime.now().strftime("%H:%M")
        state["chat_history"].append({"role": "user", "content": text, "time": now})
        update_chat()
        state["waiting"] = True

        try:
            messages = []
            talking = state["talking_agent"]
            is_resident = _is_agent_resident(talking)

            if talking:
                sys_content = state["system_prompt"]
            else:
                sys_content = state["system_prompt"] or ""
                if state["knowledge"]:
                    sys_content += f"\n\n[БАЗА ЗНАНИЙ]\n{state['knowledge']}"
                memory_ctx = format_memory_context()
                if memory_ctx:
                    sys_content += f"\n\n{memory_ctx}"
                sys_content += (
                    "\n\n[ИНСТРУМЕНТЫ СТУДИИ]\n"
                    "У тебя есть инструменты управления студией:\n"
                    "- navigate — открыть страницу (workshop, reception, cabinet, registry)\n"
                    "- list_clients / create_client / get_client_info — клиенты\n"
                    "- view_assets — каталог ассетов\n"
                    "- list_agents — список агентов цеха с состоянием ДНК\n"
                    "- get_agent_state — полное состояние агента\n"
                    "- update_agent_dynamic — изменить Respect/Patience/Stress/Internal_Light\n"
                    "- find_stressed_agents — найти агентов в критическом состоянии\n"
                    "- web_search / fetch_url — веб\n"
                    "Используй инструменты когда уместно. Не описывай процесс — просто делай.\n"
                    "Отвечай на русском, кратко и по делу."
                )

            if sys_content.strip():
                messages.append({"role": "system", "content": sys_content})

            for i, msg in enumerate(state["chat_history"]):
                role = msg["role"]
                content_text = msg["content"]
                if role == "user" and i == len(state["chat_history"]) - 1 and state["files"]:
                    content_parts = []
                    for f in state["files"]:
                        if f["is_image"]:
                            content_parts.append({"type": "image_url", "image_url": {"url": f"data:{f['media_type']};base64,{f['base64']}"}})
                        elif f.get("is_text") and f.get("text_content"):
                            content_parts.append({"type": "text", "text": f"[Файл: {f['name']}]\n{f['text_content']}"})
                        elif f["media_type"] == "application/pdf":
                            content_parts.append({"type": "image_url", "image_url": {"url": f"data:application/pdf;base64,{f['base64']}"}})
                    content_parts.append({"type": "text", "text": content_text})
                    messages.append({"role": role, "content": content_parts})
                else:
                    messages.append({"role": role, "content": content_text})

            # Tools (patch_ole.py): rabochie=None, Ole-home=None, rezidenty=vse
            if talking and not is_resident:
                tools = None
            elif (talking
                  and talking.get("id") == "004_OLE"
                  and state.get("ole_mode") == "home"):
                tools = None
            else:
                tools = TOOLS_SCHEMA

            agent_label = talking["label"] if talking else "промпт"
            print(f"[CABINET] 📤 → {agent_label} | {len(messages)} msg | tools={'да' if tools else 'нет'} | {state['model']}")

            reply = await call_openrouter(messages, state["model"], tools_schema=tools)
            print(f"[CABINET] 📥 Ответ: {len(reply)} симв.")

            nav_route = get_pending_nav()
            if nav_route:
                ui.run_javascript(f'window.open("{nav_route}", "_blank")')
                page_names = {"/workshop": "мастерскую", "/": "ресепшен", "/cabinet": "кабинет", "/registry": "реестр"}
                page_label = page_names.get(nav_route, nav_route)
                reply += f'\n\n→ <a href="{nav_route}" target="_blank" style="color:#6c8cff;text-decoration:underline;cursor:pointer">Открыть {page_label}</a>'

            state["chat_history"].append({"role": "assistant", "content": reply, "time": datetime.now().strftime("%H:%M")})

            reload_all_agents()
            update_residents()
            update_city_zone()

        except Exception as e:
            print(f"[CABINET] ❌ Ошибка API: {e}")
            import traceback
            traceback.print_exc()
            state["chat_history"].append({"role": "assistant", "content": f"⚠ Ошибка: {e}", "time": datetime.now().strftime("%H:%M")})
        finally:
            state["waiting"] = False
            update_chat()

    # ============================================================
    # OLE 004: funktsii biblioteki (patch_ole.py)
    # ============================================================

    def _set_ole_section(section_id):
        """Vybrat' sektsiju v vidzzhete kataloga i obnovit' pravuyu panel'."""
        state["ole_library_section"] = section_id
        update_right_panel("agent")

    def _render_library_widget():
        """Правая панель — виджет каталога Библиотеки (режим library)."""
        from studio.library.library import get_all_books, LIBRARY_ROOT

        agent      = state.get("selected_agent") or {}
        label_text = agent.get("label", "Оле")
        avatar_url = agent.get("avatar_url", "")

        # avatar via avatar_url (fix10) — так же как в render_agent_detail
        with ui.element("div").style("text-align:center;padding:8px 0 6px;"):
            if avatar_url:
                ui.element("div").classes("cab-detail-avatar").style(
                    f"background-image: url('{avatar_url}');"
                )
            ui.label(f'{agent.get("id", "004_OLE")} {label_text}').style(
                "font-family:'JetBrains Mono';font-size:0.75rem;font-weight:500;"
                "color:rgba(220,225,240,0.92);display:block;margin-top:4px;"
            )
            ui.label("📚 библиотека").style(
                "font-family:'JetBrains Mono';font-size:0.52rem;"
                "color:rgba(0,242,255,0.5);display:block;margin-top:2px;"
            )

        ui.html('''<style>
  .ole-lib-sep{height:1px;background:rgba(0,242,255,0.08);margin:6px 10px;}
  .ole-sec-label{font-family:JetBrains Mono;font-size:0.48rem;
    color:rgba(140,150,180,0.35);padding:6px 10px 2px;
    text-transform:uppercase;letter-spacing:1px;}
</style><div class="ole-lib-sep"></div>''')

        # ── Секции (ui.button — надёжнее div.on("click")) ──────────────────────
        SECS = {
            "craft":      "📖 Ремесло",
            "psychology": "🧠 Психология",
            "marketing":  "📣 Маркетинг",
            "tech":       "⚙️ Технологии",
            "grondheim":  "🏰 Грондхейм",
            "product":    "📦 Продукт",
        }
        active_sec = state.get("ole_library_section", "craft")

        ui.html('<div class="ole-sec-label">секции</div>')
        with ui.element("div").style("padding:0 4px;"):
            for sec_id, sec_label in SECS.items():
                is_act = (sec_id == active_sec)
                btn = ui.button(
                    sec_label,
                    on_click=lambda _s=sec_id: _set_ole_section(_s),
                ).props("flat no-caps align-left").style(
                    "width:100%;font-family:JetBrains Mono;font-size:0.62rem;"
                    "border-radius:6px;margin-bottom:1px;padding:3px 10px;"
                    + (
                        "background:rgba(0,242,255,0.08)!important;"
                        "color:#00f2ff!important;"
                        "border:1px solid rgba(0,242,255,0.2);"
                        if is_act else
                        "background:transparent!important;"
                        "color:rgba(180,190,220,0.55)!important;"
                        "border:1px solid transparent;"
                    )
                )

        ui.html('<div class="ole-lib-sep"></div>')

        # ── Загрузчик ───────────────────────────────────────────────────────────
        ui.html(f'<div class="ole-sec-label">добавить → {active_sec}</div>')
        with ui.element("div").style("padding:0 6px 6px;"):
            ui.upload(
                label="⇧  .md / .txt",
                multiple=False,
                auto_upload=True,
                on_upload=handle_library_upload_book,
            ).props('accept=".txt,.md" flat bordered').style(
                "background:#08090e;"
                "border:1.5px dashed rgba(0,242,255,0.12);"
                "border-radius:8px;color:rgba(180,190,220,0.4);"
                "font-family:JetBrains Mono;font-size:0.58rem;"
            )

        ui.html('<div class="ole-lib-sep"></div>')

        # ── Книги секции ────────────────────────────────────────────────────────
        all_books = get_all_books()
        sec_books = [b for b in all_books if b.get("section") == active_sec]
        last_10   = sec_books[-10:]

        ui.html(
            f'<div class="ole-sec-label">'
            f'книги · {len(sec_books)} в секции / {len(all_books)} всего'
            f'</div>'
        )

        if not last_10:
            ui.html(
                '<div style="text-align:center;padding:10px;'
                'font-family:JetBrains Mono;font-size:0.55rem;'
                'color:rgba(140,150,180,0.22)">полка пуста</div>'
            )
        else:
            with ui.element("div").style(
                "padding:0 6px;overflow-y:auto;"
                "max-height:220px;scrollbar-width:thin;"
            ):
                for book in reversed(last_10):
                    has_f = "✓" if (LIBRARY_ROOT / book.get("file", "")).exists() else "·"
                    tags  = ", ".join(book.get("tags", [])[:3])
                    depth = book.get("depth", "basic")
                    ui.html(
                        f'<div style="padding:5px 2px;'
                        f'border-bottom:1px solid rgba(255,255,255,0.035);">'
                        f'<div style="font-family:JetBrains Mono;font-size:0.6rem;'
                        f'color:rgba(220,225,240,0.85);">'
                        f'{has_f} <b>{book["id"]}</b> {book["title"]}'
                        f'<span style="color:rgba(0,242,255,0.4);font-size:0.5rem;"'
                        f'> [{depth}]</span></div>'
                        f'<div style="font-family:JetBrains Mono;font-size:0.5rem;'
                        f'color:rgba(140,150,180,0.35);">{tags}</div>'
                        f'</div>'
                    )

    async def handle_library_upload_book(e):
        """Zagruzhaet .md/.txt v biblioteku, registriruet, uvedomlyaet Ole."""
        from pathlib import Path as _P
        try:
            name    = e.name
            content = e.content.read() if hasattr(e.content, "read") else e.content

            if not name.endswith((".txt", ".md")):
                ui.notify("Tol'ko .txt i .md fayly", type="warning")
                return

            section   = state.get("ole_library_section", "craft")
            dest_path = _P("studio/library") / section / name
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            dest_path.write_bytes(content)

            from studio.library.register_book import register_file as _reg
            result = _reg(str(dest_path), section)

            if not result.get("success"):
                ui.notify(f"Oshibka: {result.get('error', '?')}", type="negative")
                return

            book = result["book"]

            from studio.library.library import reload_catalog as _reload
            _reload()

            # Podtverzhdenie ot Ole v chate
            if state.get("talking_agent") and state["talking_agent"].get("id") == "004_OLE":
                msg = (
                    f"Kniga '{book['title']}' uzhe zaregistrirovana pod ID [{book['id']}]."
                    if result.get("already_registered") else
                    f"Kniga '{book['title']}' dobavlena na polku [{book['section']}] pod ID [{book['id']}]."
                )
                state["chat_history"].append({
                    "role": "assistant",
                    "content": msg,
                    "time": datetime.now().strftime("%H:%M"),
                })
                update_chat()

            ui.notify(f"OK: {book['id']}: {book['title']}", type="positive")
            update_right_panel("agent")

        except Exception as ex:
            import traceback; traceback.print_exc()
            ui.notify(f"Oshibka zagruzki: {ex}", type="negative")

    def open_ole_library():
        """Открыть Библиотеку — Оле в режиме library."""
        # Режим ПЕРЕД talk_to_agent — он прочитает его при сборке промпта
        state["ole_mode"] = "library"
        residents = state["all_agents"].get("residents", [])
        ole = next((a for a in residents if a.get("id") == "004_OLE"), None)
        if ole:
            state["selected_agent"] = ole
            talk_to_agent("004_OLE", ole.get("dept", "residents"))
        else:
            ui.notify("Резидент 004_OLE не найден в системе.", type="warning")
        update_right_panel("agent")
        switch_tab("agent")
        _hide_map()

    # ═══ LAYOUT ═══


    with ui.element("div").classes("cabinet-page"):
        with ui.element("div").classes("cab-grid"):

            with ui.element("div").classes("cab-header"):
                ui.html('<div class="cab-brand">🤚🤚 <b>шесть пальцев</b> / кабинет</div>')
                with ui.element("div").classes("cab-controls"):
                    model_options = {m["id"]: f'{m["name"]}  ({m["price"]})' for m in MODELS_CATALOG}
                    ui.select(model_options, value=state["model"], on_change=on_model_change).props('dense borderless dark options-dense').style("font-family:JetBrains Mono;font-size:0.65rem;min-width:200px;color:#6c8cff;")
                    web_cls = "cab-btn active" if TAVILY_KEY else "cab-btn"
                    web_title = "Web активен" if TAVILY_KEY else "Вставь TAVILY_KEY"
                    ui.html(f'<div class="{web_cls}" title="{web_title}">🌐 web</div>')
                    ui.button("💰 дашборд", on_click=lambda: ui.open("/dashboard")).props("flat dense").style("background:#141722;border:1px solid rgba(212,175,55,0.15);color:rgba(212,175,55,0.7);font-family:JetBrains Mono;font-size:0.65rem;padding:5px 11px;border-radius:6px;")
                    ui.button("💾", on_click=lambda: save_chat()).props("flat dense").style("background:#141722;border:1px solid rgba(99,130,255,0.08);color:rgba(108,140,255,0.6);font-family:JetBrains Mono;font-size:0.7rem;padding:5px 11px;border-radius:6px;min-width:32px;").props('title="Сохранить чат + конспект"')
                    ui.button("📋 реестр", on_click=lambda: ui.run_javascript('window.open("/registry","_blank")')).props("flat dense").style("background:#141722;border:1px solid rgba(201,168,76,0.15);color:rgba(201,168,76,0.7);font-family:JetBrains Mono;font-size:0.65rem;padding:5px 11px;border-radius:6px;")
                    ui.button("✕", on_click=lambda: clear_chat()).props("flat dense").style("background:#141722;border:1px solid rgba(99,130,255,0.08);color:rgba(180,190,220,0.6);font-family:JetBrains Mono;font-size:0.62rem;padding:5px 11px;border-radius:6px;")

            with ui.element("div").classes("cab-left"):
                with ui.element("div").classes("cab-panel-title"):
                    ui.html("👥 агенты")
                    with ui.element("div").classes("cab-panel-title-right"):
                        # Кнопка загрузки файлов — открывает скрытый upload
                        refs["_hidden_upload"] = ui.upload(
                            multiple=True, auto_upload=True, on_upload=handle_upload
                        ).props('accept="image/*,.pdf,.txt,.md,.csv,.json" flat').style(
                            "display:none;"
                        )
                        upload_btn = ui.button("📎", on_click=lambda: ui.run_javascript(
                            'document.querySelector(".cab-left .q-uploader__input").click()'
                        )).props("flat dense").style(
                            "font-size:0.8rem;min-width:28px;padding:2px 6px;"
                            "background:transparent;color:rgba(140,150,180,0.5);"
                            "border:1px solid rgba(99,130,255,0.1);border-radius:5px;"
                            "cursor:pointer;"
                        )
                        upload_btn.props('title="Загрузить файлы"')
                        total = sum(len(v) for v in state["all_agents"].values())
                        ui.label(str(total)).classes("cab-badge")
                with ui.element("div").classes("cab-search-wrap"):
                    refs["search_input"] = ui.input(placeholder="🔍 найти агента...").props("borderless dense").style("width:100%;background:#08090e;border:1px solid rgba(99,130,255,0.08);border-radius:6px;padding:2px 8px;font-family:JetBrains Mono;font-size:0.65rem;color:rgba(220,225,240,0.85);").on("update:model-value", on_search_change)
                with ui.element("div").classes("cab-residents-zone"):
                    ui.html('<div class="cab-residents-label">✦ резиденты</div>')
                    refs["residents_list"] = ui.element("div").classes("cab-residents-list")
                    update_residents()
                refs["city_zone"] = ui.element("div").classes("cab-city-zone")
                update_city_zone()
                refs["search_results"] = ui.element("div").style("display:none;flex:1;overflow-y:auto;padding:6px 8px;scrollbar-width:thin;")

            with ui.element("div").classes("cab-center"):

                # ═══ КАРТА ГОРОДА ═══
                with ui.element("div").classes("cab-map-wrap") as map_wrap:
                    refs["map_wrap"] = map_wrap
                    # Хедер карты
                    with ui.element("div").classes("cab-map-header"):
                        ui.html('<span class="cab-map-title">🌆 грондхейм</span>')
                        refs["map_weather"] = ui.html('<span class="cab-map-weather">загрузка...</span>')
                        with ui.row().style("gap:6px"):
                            with ui.element("div").classes("cab-map-btn walk").style("cursor:pointer").on(
                                "click", lambda: ui.timer(0, _do_city_walk, once=True)
                            ):
                                ui.html("🚶 прогулка")
                            # Кнопка Библиотека (fix2_ole.py)
                            with ui.element("div").classes("cab-map-btn").style(
                                "cursor:pointer;"
                                "background:rgba(0,242,255,0.04);"
                                "border:1px solid rgba(0,242,255,0.15);"
                            ).on("click", lambda: open_ole_library()):
                                ui.html("📚 библиотека")
                    # Вьюпорт карты
                    with ui.element("div").classes("cab-map-viewport") as map_vp:
                        refs["map_canvas"] = ui.element("div").classes("cab-map-canvas has-bg")
                    # JS: drag + zoom — запускается после загрузки DOM
                    ui.add_body_html("""
<script>
// Глобальный обработчик кликов по агентам на карте
window.cabSelectAgent = function(agentId, dept) {
    emitEvent('cab-agent-select', {id: agentId, dept: dept});
};

// Инициализация карты — ждём DOM
function initCabMap() {
  const vp = document.querySelector('.cab-map-viewport');
  if(!vp) { setTimeout(initCabMap, 100); return; }

  let scale=0.55, pos={x:0,y:0}, dragging=false, dragStart={x:0,y:0};

  function applyTransform(){
    const c=vp.querySelector('.cab-map-canvas');
    if(c) c.style.transform=`translate(${pos.x}px,${pos.y}px) scale(${scale})`;
  }

  vp.addEventListener('wheel',e=>{
    e.preventDefault();
    const s=e.deltaY*-0.001;
    let ns=Math.min(Math.max(0.15,scale+s),2.5);
    if(ns===scale) return;
    const r=vp.getBoundingClientRect();
    const mx=e.clientX-r.left, my=e.clientY-r.top;
    pos.x=mx-((mx-pos.x)*(ns/scale));
    pos.y=my-((my-pos.y)*(ns/scale));
    scale=ns; applyTransform();
  },{passive:false});

  vp.addEventListener('pointerdown',e=>{
    if(e.target.closest('[data-agent-id]')) return;
    dragging=true;
    dragStart={x:e.clientX-pos.x,y:e.clientY-pos.y};
    vp.setPointerCapture(e.pointerId);
  });

  window.addEventListener('pointermove',e=>{
    if(!dragging) return;
    pos.x=e.clientX-dragStart.x; pos.y=e.clientY-dragStart.y;
    applyTransform();
  });

  window.addEventListener('pointerup',()=>{ dragging=false; });

  applyTransform();

  window.cabMapSetScale=function(s){ scale=s; applyTransform(); };
  window.cabMapCenterOn=function(x,y){
    const r=vp.getBoundingClientRect();
    pos.x=r.width/2-x*scale; pos.y=r.height/2-y*scale;
    applyTransform();
  };
}

// Запускаем после загрузки страницы
if(document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initCabMap);
} else {
  setTimeout(initCabMap, 200);
}
</script>""")

                # ═══ КНОПКА "НАЗАД К КАРТЕ" ═══
                with ui.element("div").classes("cab-back-to-map") as back_btn:
                    refs["back_btn"] = back_btn
                    ui.html("← карта города").on("click", lambda: _show_map())

                # ═══ ЧАТ (скрыт по умолчанию — показывается при клике на агента) ═══
                refs["prompt_bar"] = ui.element("div").classes("cab-active-prompt")
                with refs["prompt_bar"]:
                    refs["prompt_name"] = ui.label("—")
                    ui.button("✕", on_click=lambda: deselect_prompt()).props("flat dense size=xs").style("color:rgba(180,190,220,0.6);min-width:24px;font-size:0.68rem;")
                refs["chat"] = ui.element("div").classes("cab-chat").style("display: none")
                update_chat()
                refs["input_area"] = ui.element("div").classes("cab-input-area").style("display: none")
                with refs["input_area"]:
                    with ui.row().style("gap:8px;align-items:flex-end;width:100%;"):
                        refs["input"] = ui.textarea(placeholder="напиши что-нибудь...").props("borderless autogrow").style("flex:1;background:#141722;border:1px solid rgba(99,130,255,0.08);border-radius:6px;color:rgba(220,225,240,0.92);font-family:JetBrains Mono;font-size:0.88rem;padding:10px 14px;min-height:60px;max-height:140px;")
                        refs["input"].on("keydown.ctrl.enter", lambda e: send())
                        ui.button("▶ send", on_click=lambda: send()).style("background:rgba(108,140,255,0.12);border:1px solid rgba(108,140,255,0.2);color:#6c8cff;font-family:JetBrains Mono;font-size:0.7rem;padding:10px 20px;border-radius:6px;height:40px;")
                    ui.html('<div style="font-family:JetBrains Mono;font-size:0.52rem;color:rgba(140,150,180,0.3);margin-top:6px;text-align:right">Ctrl+Enter — отправить</div>')

            with ui.element("div").classes("cab-right"):
                with ui.element("div").classes("cab-tabs"):
                    for tab_name, tab_label in [("agent","агент"),("matrix","матрица"),("files","файлы"),("prompts","промпты"),("archive","архив")]:
                        is_active = tab_name == state["active_tab"]
                        cls = "cab-tab active" if is_active else "cab-tab"
                        tab_el = ui.element("div").classes(cls)
                        with tab_el:
                            ui.label(tab_label).style("font-size:inherit;color:inherit;cursor:pointer;pointer-events:none;")
                        tab_el.on("click", lambda e, _t=tab_name: switch_tab(_t))
                        refs["right_tabs"][tab_name] = tab_el
                for tab_name in ["agent","matrix","files","prompts","archive"]:
                    is_active = tab_name == state["active_tab"]
                    panel = ui.element("div").classes("cab-tab-content").style(f'display:{"block" if is_active else "none"}')
                    refs["right_panels"][tab_name] = panel
                update_right_panel("agent")
                update_right_panel("prompts")

        # Инициализация карты
        _refresh_map()

        # JS bridge: клик по агенту на карте → select_agent
        ui.on("cab-agent-select", lambda e: select_agent(
            e.args.get("id", ""), e.args.get("dept", "")
        ))