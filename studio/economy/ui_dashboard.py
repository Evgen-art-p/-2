# studio/economy/ui_dashboard.py
"""
ECONOMY DASHBOARD — страница /dashboard
Читает billing_ledger.jsonl, показывает расходы агентов
Layout: [Агенты 320px] [Центр 1fr] [Детали 480px]

v2.0:
  - Единый источник правды: billing_ledger.get_economy_data()
  - Правая панель: детальные показатели агента + последние транзакции
  - Burn Rate агента = cost / (days * 24 * 60)
"""
import json
from datetime import datetime
from pathlib import Path
from nicegui import ui
from studio.cabinet.css import CABINET_CSS
from studio.cabinet.agents import list_all_agents
from studio.billing_ledger import get_economy_data, get_agent_stats, get_cognitive_data

# Chart.js CDN убран — используем ui.echart (встроен в NiceGUI, CDN не нужен)

# ── Подключаем CSS ──
_css_path = Path(__file__).parent / "dashboard.css"
DASHBOARD_CSS = _css_path.read_text(encoding="utf-8")


@ui.page('/dashboard')
def dashboard_page():
    ui.add_head_html(f'<style>{CABINET_CSS}</style>')
    ui.add_head_html(f'<style>{DASHBOARD_CSS}</style>')

    # ── STATE ──
    state = {
        "selected_agent": None,
        "selected_dept": "",
        "open_slot": None,
        "period": 1,
        "economy_data": {},
        "agent_stats": {},
        "all_agents": {},
        "center_view": "economy",   # "economy" | "observability"
    }

    refs = {
        "agent_list":    None,
        "detail_panel":  None,
        "metrics_grid":  None,
        "total_label":   None,
        "burn_label":    None,
        "provider_chart": None,
        "agent_chart":   None,
        # ECharts — встроены в NiceGUI, создаются в render_metrics_grid
        "ec_cost":       None,
        "ec_calls":      None,
        "ec_avg":        None,
        "ec_provider":   None,
        # Observability 2×2
        "ec_obs_pie":      None,
        "ec_obs_roi":      None,
        "ec_obs_dna":      None,
        "ec_obs_pressure": None,
    }

    # ── DATA SOURCE: billing_ledger ──

    def update_all():
        state["economy_data"] = get_economy_data(state["period"])
        state["all_agents"]   = list_all_agents()
        render_agent_list()
        render_center_grid()    # рендерит активную сетку (economy или observability)
        render_charts()         # заливает данные в echart (только economy-рефы)
        render_detail()

    # ── OBSERVABILITY GRID 2×2 ──────────────────────────────────────
    def render_observability_grid():
        """Строит сетку 2×2 с когнитивными индикаторами."""
        el = refs["metrics_grid"]
        if not el:
            return
        el.clear()
        el.style(
            'display:grid;'
            'grid-template-columns: repeat(2, 1fr);'
            'grid-template-rows: repeat(2, 1fr);'
            'gap:16px;'
            'margin:0 20px 20px 20px;'
            'flex:1;'
            'min-height:0;'
        )

        cog = get_cognitive_data(state["period"])
        src = cog["source_split"]
        roi = cog["roi_series"]
        mode_changes = cog["mode_changes"]
        total_calls  = cog["total_calls"]
        pressure     = cog["pressure_level"]   # 0..1

        with el:
            # [0,0] — SOURCE SPLIT (Pie)
            with ui.card().classes('dashboard-stat-card').style('overflow:hidden; display:flex; flex-direction:column;'):
                ui.label('АВТОНОМИЯ · ИСТОЧНИК ЗНАНИЙ').classes('dashboard-stat-label')
                pie_data = [
                    {"name": "Гавань",    "value": src.get("harbor",   0)},
                    {"name": "Маяк",      "value": src.get("beacon",   0)},
                    {"name": "Внутр.",    "value": src.get("internal", 0)},
                ]
                refs["ec_obs_pie"] = ui.echart({
                    'backgroundColor': 'transparent',
                    'animation': False,
                    'color': ['#50fa7b', '#f87171', '#6c8cff'],
                    'legend': {
                        'orient': 'vertical', 'right': '5%', 'top': 'center',
                        'textStyle': {'color': 'rgba(180,190,220,0.55)', 'fontSize': 9},
                    },
                    'series': [{
                        'type': 'pie',
                        'radius': ['38%', '65%'],
                        'center': ['38%', '50%'],
                        'data': pie_data,
                        'label': {'show': False},
                    }],
                }).style('flex:1; min-height:0;')

            # [0,1] — ROI LINE (Мудрость)
            with ui.card().classes('dashboard-stat-card').style('overflow:hidden; display:flex; flex-direction:column;'):
                ui.label('МУДРОСТЬ · ROI (токены/$)').classes('dashboard-stat-label')
                refs["ec_obs_roi"] = ui.echart({
                    'backgroundColor': 'transparent',
                    'animation': False,
                    'grid': {'left': '12%', 'right': '4%', 'top': '6%', 'bottom': '18%'},
                    'xAxis': {
                        'type': 'category',
                        'data': roi["labels"],
                        'axisLabel': {'color': 'rgba(180,190,220,0.4)', 'fontSize': 9},
                    },
                    'yAxis': {
                        'type': 'value',
                        'axisLabel': {'color': 'rgba(180,190,220,0.4)', 'fontSize': 9},
                        'splitLine': {'lineStyle': {'color': 'rgba(99,130,255,0.07)'}},
                    },
                    'series': [{
                        'type': 'line',
                        'data': roi["roi"],
                        'smooth': True,
                        'symbol': 'none',
                        'lineStyle': {'color': '#c9a84c', 'width': 1.5},
                        'areaStyle': {'color': 'rgba(201,168,76,0.08)'},
                    }],
                }).style('flex:1; min-height:0;')

            # [1,0] — DNA ADAPTABILITY (Gauge пластичности)
            with ui.card().classes('dashboard-stat-card').style('overflow:hidden; display:flex; flex-direction:column;'):
                ui.label('ПЛАСТИЧНОСТЬ · СМЕНЫ РЕЖИМА').classes('dashboard-stat-label')
                # Нормализуем: максимум ~20 смен = 100%
                dna_val = min(100, round(mode_changes / max(total_calls, 1) * 1000))
                refs["ec_obs_dna"] = ui.echart({
                    'backgroundColor': 'transparent',
                    'animation': False,
                    'series': [{
                        'type': 'gauge',
                        'startAngle': 200,
                        'endAngle': -20,
                        'min': 0,
                        'max': 100,
                        'splitNumber': 4,
                        'radius': '88%',
                        'center': ['50%', '58%'],
                        'axisLine': {
                            'lineStyle': {
                                'width': 8,
                                'color': [
                                    [0.3,  '#50fa7b'],
                                    [0.7,  '#c9a84c'],
                                    [1.0,  '#f87171'],
                                ],
                            },
                        },
                        'pointer': {'length': '55%', 'width': 3, 'itemStyle': {'color': 'auto'}},
                        'axisTick':    {'show': False},
                        'splitLine':   {'show': False},
                        'axisLabel':   {'color': 'rgba(180,190,220,0.4)', 'fontSize': 8, 'distance': 12},
                        'detail': {
                            'valueAnimation': False,
                            'formatter': f'{mode_changes} смен',
                            'color': 'rgba(200,210,240,0.7)',
                            'fontSize': 10,
                            'offsetCenter': [0, '30%'],
                        },
                        'data': [{'value': dna_val}],
                    }],
                }).style('flex:1; min-height:0;')

            # [1,1] — ENVIRONMENTAL PRESSURE (Барометр)
            with ui.card().classes('dashboard-stat-card').style('overflow:hidden; display:flex; flex-direction:column;'):
                ui.label('КЛИМАТ · ДАВЛЕНИЕ СРЕДЫ').classes('dashboard-stat-label')
                pressure_val = round(pressure * 100)
                if pressure_val < 30:
                    pressure_label = 'Ясно'
                    pressure_color = '#50fa7b'
                elif pressure_val < 60:
                    pressure_label = 'Переменно'
                    pressure_color = '#c9a84c'
                elif pressure_val < 80:
                    pressure_label = 'Напряжённо'
                    pressure_color = '#f87171'
                else:
                    pressure_label = 'Шторм'
                    pressure_color = '#ff5555'
                refs["ec_obs_pressure"] = ui.echart({
                    'backgroundColor': 'transparent',
                    'animation': False,
                    'series': [{
                        'type': 'gauge',
                        'startAngle': 200,
                        'endAngle': -20,
                        'min': 0,
                        'max': 100,
                        'splitNumber': 4,
                        'radius': '88%',
                        'center': ['50%', '58%'],
                        'axisLine': {
                            'lineStyle': {
                                'width': 8,
                                'color': [
                                    [0.3,  '#50fa7b'],
                                    [0.6,  '#c9a84c'],
                                    [0.8,  '#f87171'],
                                    [1.0,  '#ff5555'],
                                ],
                            },
                        },
                        'pointer': {'length': '55%', 'width': 3, 'itemStyle': {'color': 'auto'}},
                        'axisTick':    {'show': False},
                        'splitLine':   {'show': False},
                        'axisLabel':   {'color': 'rgba(180,190,220,0.4)', 'fontSize': 8, 'distance': 12},
                        'detail': {
                            'valueAnimation': False,
                            'formatter': pressure_label,
                            'color': pressure_color,
                            'fontSize': 11,
                            'fontWeight': 'bold',
                            'offsetCenter': [0, '30%'],
                        },
                        'data': [{'value': pressure_val}],
                    }],
                }).style('flex:1; min-height:0;')

    # ── ПЕРЕКЛЮЧАТЕЛЬ ЦЕНТРАЛЬНОЙ СЕТКИ ──────────────────────────
    def render_center_grid():
        """Выбирает какую сетку рендерить в центре."""
        if state["center_view"] == "observability":
            render_observability_grid()
        else:
            _restore_economy_grid_style()
            render_metrics_grid()

    def _restore_economy_grid_style():
        el = refs["metrics_grid"]
        if el:
            el.style(
                'display:grid;'
                'grid-template-columns: repeat(3, 1fr);'
                'grid-template-rows: repeat(3, 1fr);'
                'gap:16px;'
                'margin:0 20px 20px 20px;'
                'flex:1;'
                'min-height:0;'
            )

    def set_center_view(view: str):
        state["center_view"] = view
        render_center_grid()

    def render_metrics_grid():
        """Полностью перестраивает сетку 3×3 с актуальными данными."""
        el = refs["metrics_grid"]
        if not el:
            return
        el.clear()
        eco = state["economy_data"]

        with el:
            # ── 1. TOTAL SPEND ──
            with ui.card().classes('dashboard-stat-card').style('overflow:hidden;'):
                ui.label('TOTAL SPEND').classes('dashboard-stat-label')
                ui.label(f'${eco.get("total", 0):.4f}').classes('dashboard-stat-value-total')
                ui.html('<div style="font-family:JetBrains Mono,monospace;font-size:0.55rem;'
                        'color:rgba(140,150,180,0.4);margin-top:4px;">за период</div>')

            # ── 2. BURN RATE ──
            with ui.card().classes('dashboard-stat-card').style('overflow:hidden;'):
                ui.label('BURN RATE').classes('dashboard-stat-label')
                burn_hr = eco.get("burn_rate", 0) * 60
                ui.label(f'${burn_hr:.4f}/hr').classes('dashboard-stat-value-burn')
                ui.html('<div style="font-family:JetBrains Mono,monospace;font-size:0.55rem;'
                        'color:rgba(140,150,180,0.4);margin-top:4px;">$/час</div>')

            # ── 3. RUNWAY ──
            with ui.card().classes('dashboard-stat-card').style('overflow:hidden;'):
                ui.label('RUNWAY').classes('dashboard-stat-label')
                _burn_day = eco.get("burn_rate", 0) * 60 * 24
                _budget   = eco.get("budget", 0)
                if _budget and _burn_day > 0:
                    _days = _budget / _burn_day
                    ui.label(f'{_days:.1f} дн').classes('dashboard-stat-value-total').style('color:#f87171;')
                    ui.html(f'<div style="font-family:JetBrains Mono,monospace;font-size:0.55rem;'
                            f'color:rgba(140,150,180,0.4);margin-top:4px;">бюджет ${_budget:.2f}</div>')
                elif _burn_day > 0:
                    ui.label(f'${_burn_day:.4f}/d').classes('dashboard-stat-value-burn')
                    ui.html('<div style="font-family:JetBrains Mono,monospace;font-size:0.55rem;'
                            'color:rgba(140,150,180,0.4);margin-top:4px;">бюджет не задан</div>')
                else:
                    ui.label('—').classes('dashboard-stat-value-total')

            # 4. COST OVER TIME
            with ui.card().classes('dashboard-stat-card').style('overflow:hidden; display:flex; flex-direction:column;'):
                ui.label('COST OVER TIME').classes('dashboard-stat-label')
                refs["ec_cost"] = ui.echart({
                    'backgroundColor': 'transparent', 'animation': False,
                    'grid': {'left': '12%', 'right': '4%', 'top': '6%', 'bottom': '18%'},
                    'xAxis': {'type': 'category', 'data': [], 'axisLabel': {'color': 'rgba(180,190,220,0.4)', 'fontSize': 9}},
                    'yAxis': {'type': 'value', 'axisLabel': {'color': 'rgba(180,190,220,0.4)', 'fontSize': 9},
                              'splitLine': {'lineStyle': {'color': 'rgba(99,130,255,0.07)'}}},
                    'series': [{'type': 'line', 'data': [], 'smooth': True, 'symbol': 'none',
                                'lineStyle': {'color': '#6c8cff', 'width': 1.5},
                                'areaStyle': {'color': 'rgba(108,140,255,0.1)'}}],
                }).style('flex:1; min-height:0;')
            # 5. CALLS VOLUME
            with ui.card().classes('dashboard-stat-card').style('overflow:hidden; display:flex; flex-direction:column;'):
                ui.label('CALLS VOLUME').classes('dashboard-stat-label')
                refs["ec_calls"] = ui.echart({
                    'backgroundColor': 'transparent', 'animation': False,
                    'grid': {'left': '12%', 'right': '4%', 'top': '6%', 'bottom': '18%'},
                    'xAxis': {'type': 'category', 'data': [], 'axisLabel': {'color': 'rgba(180,190,220,0.4)', 'fontSize': 9}},
                    'yAxis': {'type': 'value', 'axisLabel': {'color': 'rgba(180,190,220,0.4)', 'fontSize': 9},
                              'splitLine': {'lineStyle': {'color': 'rgba(99,130,255,0.07)'}}},
                    'series': [{'type': 'bar', 'data': [],
                                'itemStyle': {'color': '#c9a84c', 'borderRadius': 2}}],
                }).style('flex:1; min-height:0;')
            # 6. AVG COST / CALL
            with ui.card().classes('dashboard-stat-card').style('overflow:hidden; display:flex; flex-direction:column;'):
                ui.label('AVG COST / CALL').classes('dashboard-stat-label')
                refs["ec_avg"] = ui.echart({
                    'backgroundColor': 'transparent', 'animation': False,
                    'grid': {'left': '12%', 'right': '4%', 'top': '6%', 'bottom': '18%'},
                    'xAxis': {'type': 'category', 'data': [], 'axisLabel': {'color': 'rgba(180,190,220,0.4)', 'fontSize': 9}},
                    'yAxis': {'type': 'value', 'axisLabel': {'color': 'rgba(180,190,220,0.4)', 'fontSize': 9},
                              'splitLine': {'lineStyle': {'color': 'rgba(99,130,255,0.07)'}}},
                    'series': [{'type': 'line', 'data': [], 'smooth': True, 'symbol': 'none',
                                'lineStyle': {'color': '#50fa7b', 'width': 1.5},
                                'areaStyle': {'color': 'rgba(80,250,123,0.08)'}}],
                }).style('flex:1; min-height:0;')
            # 7. PROVIDER BREAKDOWN
            with ui.card().classes('dashboard-stat-card').style('overflow:hidden; display:flex; flex-direction:column;'):
                ui.label('PROVIDER BREAKDOWN').classes('dashboard-stat-label')
                refs["ec_provider"] = ui.echart({
                    'backgroundColor': 'transparent', 'animation': False,
                    'color': ['#6c8cff', '#c9a84c', '#a78bfa', '#f87171', '#50fa7b', '#38bdf8'],
                    'legend': {'orient': 'vertical', 'right': '5%', 'top': 'center',
                               'textStyle': {'color': 'rgba(180,190,220,0.55)', 'fontSize': 9}},
                    'series': [{'type': 'pie', 'radius': ['38%', '65%'], 'center': ['38%', '50%'],
                                'data': [], 'label': {'show': False}}],
                }).style('flex:1; min-height:0;')
            # ── 8. TOP SPENDERS ──
            with ui.card().classes('dashboard-stat-card').style('overflow:hidden;'):
                ui.label('TOP SPENDERS').classes('dashboard-stat-label')
                _agent_items = sorted(
                    eco.get("by_agent", {}).items(),
                    key=lambda x: x[1], reverse=True
                )[:5]
                for _aname, _aval in _agent_items:
                    _short = _aname[:14] + '…' if len(_aname) > 14 else _aname
                    ui.html(
                        f'<div style="display:flex;justify-content:space-between;align-items:center;'
                        f'font-family:JetBrains Mono,monospace;font-size:0.58rem;'
                        f'color:rgba(200,210,240,0.75);margin-top:5px;border-bottom:1px solid rgba(99,130,255,0.06);padding-bottom:4px;gap:8px;">'
                        f'<span style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{_short}</span>'
                        f'<span style="color:#c9a84c;flex-shrink:0;white-space:nowrap;">${_aval:.4f}</span></div>'
                    )
                if not _agent_items:
                    ui.html('<div style="font-size:0.6rem;color:rgba(180,190,220,0.3);margin-top:8px;">— нет данных —</div>')

            # ── 9. TRENDS ──
            with ui.card().classes('dashboard-stat-card').style('overflow:hidden;'):
                ui.label('TRENDS').classes('dashboard-stat-label')
                _curr = eco.get("total", 0)
                _prev = eco.get("prev_total", 0)
                if _prev and _prev > 0:
                    _dpct = ((_curr - _prev) / _prev) * 100
                    _arrow = '↑' if _dpct >= 0 else '↓'
                    _clr   = '#f87171' if _dpct >= 0 else '#50fa7b'
                    ui.label(f'{_arrow} {abs(_dpct):.1f}%').classes('dashboard-stat-value-total').style(f'color:{_clr};')
                    ui.html(
                        f'<div style="font-family:JetBrains Mono,monospace;font-size:0.55rem;'
                        f'color:rgba(140,150,180,0.4);margin-top:4px;">'
                        f'vs прошлый период ${_prev:.4f}</div>'
                    )
                else:
                    ui.label(f'${_curr:.4f}').classes('dashboard-stat-value-total').style('color:#6c8cff;')
                    ui.html('<div style="font-family:JetBrains Mono,monospace;font-size:0.52rem;'
                            'color:rgba(140,150,180,0.2);margin-top:6px;">нет данных за прошлый период</div>')

    # ── LEFT PANEL: слоты и агенты ──

    def toggle_slot(slot_id):
        if state.get("open_slot") == slot_id:
            state["open_slot"] = None
        else:
            state["open_slot"] = slot_id
        render_agent_list()

    def select_agent(agent_id, agent_dept=""):
        state["selected_agent"] = agent_id
        state["selected_dept"] = agent_dept
        state["agent_stats"] = get_agent_stats(agent_id, state["period"])
        render_agent_list()
        render_detail()

    def set_period(days):
        state["period"] = days
        state["selected_agent"] = None
        state["agent_stats"] = {}
        update_all()

    def render_agent_list():
        el = refs["agent_list"]
        if not el:
            return
        el.clear()

        eco = state["economy_data"]

        # Группируем агентов по слотам (slot_id из леджера)
        agents_by_slot = {}
        for dept_id, agents in state["all_agents"].items():
            slot = dept_id if dept_id else "unknown"
            if slot not in agents_by_slot:
                agents_by_slot[slot] = []
            agents_by_slot[slot].extend(agents)

        # Считаем сумму слота из by_slot леджера
        slot_costs = eco.get("by_slot", {})

        # Сортируем слоты по сумме
        sorted_slots = sorted(
            agents_by_slot.keys(),
            key=lambda s: slot_costs.get(s, 0),
            reverse=True
        )

        with el:
            for slot_id in sorted_slots:
                agents = agents_by_slot.get(slot_id, [])
                slot_total = slot_costs.get(slot_id, 0)

                if not agents and slot_total == 0:
                    continue

                with ui.element('div').classes('cab-dept-section'):
                    is_open = state.get("open_slot") == slot_id
                    header_cls = 'cab-dept-header open' if is_open else 'cab-dept-header'

                    hdr = ui.element('div').classes(header_cls)
                    hdr.on('click', lambda _, sid=slot_id: toggle_slot(sid))

                    with hdr:
                        with ui.element('div').classes('dashboard-slot-header-left'):
                            arrow_cls = 'dashboard-slot-arrow open' if is_open else 'dashboard-slot-arrow'
                            ui.html(f'<span class="{arrow_cls}">▶</span>')
                            ui.html(f'<span class="dashboard-slot-name">{slot_id}</span>')

                        ui.html(f'<span class="dashboard-slot-count">${slot_total:.3f} ({len(agents)})</span>')

                    body_cls = 'cab-dept-body open' if is_open else 'cab-dept-body'
                    with ui.element('div').classes(body_cls):
                        agents_sorted = sorted(
                            agents,
                            key=lambda a: eco.get("by_agent", {}).get(a["id"], 0),
                            reverse=True
                        )

                        for agent in agents_sorted:
                            aid = agent["id"]
                            cost = eco.get("by_agent", {}).get(aid, 0)
                            is_active = state["selected_agent"] == aid and state["selected_dept"] == slot_id

                            cls = 'cab-agent-card active' if is_active else 'cab-agent-card'

                            with ui.element('div').classes(cls).on('click', lambda _, _id=aid, _dept=slot_id: select_agent(_id, _dept)):
                                with ui.element('div').classes('dashboard-agent-top'):
                                    avatar_url = agent.get("avatar_url", "")
                                    # ВАЖНО: background-image остаётся инлайн, потому что URL динамический
                                    ui.html(f'<div class="dashboard-agent-avatar" style="background-image:url(\'{avatar_url}\')"></div>')
                                    ui.label(agent.get("label", aid)).classes('dashboard-agent-name')
                                    ui.label(f'${cost:.3f}').classes('dashboard-agent-cost')

                                if cost > 0:
                                    max_cost = max(eco.get("by_agent", {}).values()) if eco.get("by_agent") else 1
                                    pct = min(100, int((cost / max_cost) * 100))
                                    ui.html(f'<div class="cab-bar-track"><div class="cab-bar-fill" style="width:{pct}%;background:#6c8cff"></div></div>')

    # ── CENTER: чарты ──

    def render_charts():
        """Заливает данные в ECharts (встроены в NiceGUI, CDN не нужен)."""
        from studio.billing_ledger import get_timeseries
        eco = state["economy_data"]
        ts  = get_timeseries(state["period"])
        lbl = ts["labels"]

        if refs["ec_cost"]:
            refs["ec_cost"].options["xAxis"]["data"] = lbl
            refs["ec_cost"].options["series"][0]["data"] = ts["cost"]
            refs["ec_cost"].update()

        if refs["ec_calls"]:
            refs["ec_calls"].options["xAxis"]["data"] = lbl
            refs["ec_calls"].options["series"][0]["data"] = ts["calls"]
            refs["ec_calls"].update()

        if refs["ec_avg"]:
            refs["ec_avg"].options["xAxis"]["data"] = lbl
            refs["ec_avg"].options["series"][0]["data"] = ts["avg_cost"]
            refs["ec_avg"].update()

        if refs["ec_provider"]:
            items = [{"name": k, "value": round(v, 4)}
                     for k, v in eco.get("by_provider", {}).items()]
            refs["ec_provider"].options["series"][0]["data"] = items or [{"name": "нет данных", "value": 1}]
            refs["ec_provider"].update()
    # ── RIGHT PANEL: детали агента ──

    def render_detail():
        el = refs["detail_panel"]
        if not el:
            return
        el.clear()

        aid = state["selected_agent"]
        adept = state.get("selected_dept", "")

        if not aid:
            with el:
                ui.html('<div class="dashboard-empty-state">выбери агента слева</div>')
            return

        # Ищем агента: сначала по dept+id, потом по id (fallback)
        agent = None
        if adept:
            for a in state["all_agents"].get(adept, []):
                if a["id"] == aid:
                    agent = a
                    break
        if not agent:
            for dept_agents in state["all_agents"].values():
                for a in dept_agents:
                    if a["id"] == aid:
                        agent = a
                        break
                if agent:
                    break

        stats = state.get("agent_stats", {})

        with el:
            # Аватар — background-image инлайн, остальное в классе
            avatar_url = agent.get("avatar_url", "") if agent else ""
            ui.html(f'<div class="dashboard-detail-avatar" style="background-image:url(\'{avatar_url}\')"></div>')

            # Имя и ID
            ui.label(agent.get("label", aid) if agent else aid).classes('dashboard-detail-name')
            ui.label(f'ID: {aid}').classes('dashboard-detail-id')

            ui.html('<hr class="dashboard-detail-divider">')

            # ── ОСНОВНЫЕ МЕТРИКИ ──
            ui.html('<div class="dashboard-detail-section-title">💰 финансы агента</div>')

            total = stats.get("total", 0)
            burn = stats.get("burn_rate", 0)
            calls = stats.get("total_calls", 0)
            avg = stats.get("avg_cost", 0)

            ui.html(f'''
                <div class="dashboard-metric-row">
                    <span class="dashboard-metric-label">Total Spend</span>
                    <span class="dashboard-metric-value-total">${total:.4f}</span>
                </div>
            ''')
            ui.html(f'''
                <div class="dashboard-metric-row">
                    <span class="dashboard-metric-label">Burn Rate</span>
                    <span class="dashboard-metric-value-burn">${burn:.4f}/m</span>
                </div>
            ''')
            ui.html(f'''
                <div class="dashboard-metric-row">
                    <span class="dashboard-metric-label">Total Calls</span>
                    <span class="dashboard-metric-value-default">{calls}</span>
                </div>
            ''')
            ui.html(f'''
                <div class="dashboard-metric-row">
                    <span class="dashboard-metric-label">Avg Cost/Call</span>
                    <span class="dashboard-metric-value-gold">${avg:.4f}</span>
                </div>
            ''')

            # ── BY PROVIDER ──
            by_provider = stats.get("by_provider", {})
            ui.html('<hr class="dashboard-detail-divider">')
            ui.html('<div class="dashboard-detail-section-title">🔌 провайдеры</div>')
            if by_provider:
                for prov, val in by_provider.items():
                    ui.html(f'''
                        <div class="dashboard-provider-row">
                            <span class="dashboard-provider-label">{prov}</span>
                            <span class="dashboard-provider-value">${val:.4f}</span>
                        </div>
                    ''')
            else:
                ui.html('<div class="dashboard-no-data">— нет данных за период —</div>')

            # ── BY MODEL ──
            by_model = stats.get("by_model", {})
            ui.html('<hr class="dashboard-detail-divider">')
            ui.html('<div class="dashboard-detail-section-title">🤖 модели</div>')
            if by_model:
                for mod, val in by_model.items():
                    model_short = mod.split("/")[-1] if "/" in mod else mod
                    ui.html(f'''
                        <div class="dashboard-provider-row">
                            <span class="dashboard-provider-label">{model_short}</span>
                            <span class="dashboard-provider-value" style="color:#a78bfa">${val:.4f}</span>
                        </div>
                    ''')
            else:
                ui.html('<div class="dashboard-no-data">— нет данных за период —</div>')

            # ── ПОСЛЕДНИЕ ТРАНЗАКЦИИ ──
            recent = stats.get("recent", [])
            ui.html('<hr class="dashboard-detail-divider">')
            ui.html('<div class="dashboard-detail-section-title">📋 последние вызовы</div>')
            if recent:
                with ui.element('div').classes('dashboard-tx-list'):
                    for tx in recent[:10]:
                        ts = tx.get("ts", "")
                        try:
                            dt = datetime.fromisoformat(ts)
                            ts_str = dt.strftime("%d.%m %H:%M:%S")
                        except Exception:
                            ts_str = ts[:19] if ts else "??:??:??"

                        model = tx.get("model", "?")
                        model_short = model.split("/")[-1] if "/" in model else model
                        cost = tx.get("cost", 0)
                        tokens = tx.get("tokens", 0)

                        ui.html(f'''
                            <div class="dashboard-tx-row">
                                <span class="dashboard-tx-time">{ts_str}</span>
                                <span class="dashboard-tx-model">{model_short}</span>
                                <span class="dashboard-tx-tokens">{tokens}t</span>
                                <span class="dashboard-tx-cost">${cost:.4f}</span>
                            </div>
                        ''')
            else:
                ui.html('<div class="dashboard-no-data">— нет вызовов за период —</div>')

    # ── LAYOUT ──
    with ui.element('div').classes('cabinet-page'):
        with ui.element('div').classes('cab-grid'):

            # HEADER
            with ui.element('div').classes('cab-header'):
                ui.button('← в кабинет', on_click=lambda: ui.open('/cabinet')).props('flat dense').classes('dashboard-header-back-btn')
                ui.label('📊 ECONOMY DASHBOARD').classes('dashboard-header-title')
                ui.label('').classes('dashboard-header-spacer')

            # LEFT: AGENTS
            with ui.element('div').classes('cab-left'):
                with ui.element('div').classes('cab-panel-title'):
                    ui.html('<span class="dashboard-panel-title">👥 агенты / финансы</span>')

                with ui.row().classes('dashboard-period-row'):
                    for days, label in [(1, '1д'), (7, '7д'), (30, '30д')]:
                        is_active = state["period"] == days
                        btn_cls = 'dashboard-period-btn active' if is_active else 'dashboard-period-btn inactive'
                        ui.button(label, on_click=lambda d=days: set_period(d)).props('flat dense').classes(btn_cls)

                refs["agent_list"] = ui.element('div').classes('dashboard-agent-list-container')

            # CENTER: CHARTS
            with ui.element('div').classes('cab-center').style(
                'padding-left:0; margin-left:0; display:flex; flex-direction:column; height:100%;'
            ):
                # ── Верхняя полоса: статы (refs) + кнопки провайдеров — НЕ ТРОГАТЬ ──
                with ui.element('div').style(
                    'display:flex; align-items:stretch; gap:20px; margin:20px; width:calc(100% - 40px); flex-shrink:0;'
                ):
                    # Левая часть: Total Spend, Burn Rate, заглушка
                    with ui.element('div').style(
                        'display:grid; grid-template-columns:repeat(3, 1fr); gap:20px; flex:1;'
                    ):
                        with ui.card().classes('dashboard-stat-card'):
                            ui.label('').classes('dashboard-stat-label')
                        with ui.card().classes('dashboard-stat-card'):
                            ui.label('').classes('dashboard-stat-label')
                        # Заглушка — симметрия с кнопками
                        with ui.card().classes('dashboard-stat-card'):
                            ui.label('').classes('dashboard-stat-label')
                            ui.label('').classes('dashboard-stat-value-total')

                    # Правая часть: кнопки провайдеров 3×2
                    PROVIDERS = [
                        {"label": "ElevenLabs",  "url": "https://elevenlabs.io/subscription",           "key": "elevenlabs"},
                        {"label": "Tavily",      "url": "https://app.tavily.com/home",                  "key": "tavily"},
                        {"label": "OpenRouter",  "url": "https://openrouter.ai/credits",                "key": "openrouter"},
                        {"label": "Suno",        "url": "https://suno.com/account",                     "key": "suno"},
                        {"label": "SiliconFlow", "url": "https://cloud.siliconflow.cn/account/finance", "key": "siliconflow"},
                        {"label": "Fal.ai",      "url": "https://fal.ai/dashboard/billing",             "key": "fal"},
                    ]
                    with ui.element('div').style(
                        'display:grid; grid-template-columns:repeat(3, 1fr);'
                        'grid-template-rows:repeat(2, 1fr); gap:20px; flex:1;'
                    ):
                        for p in PROVIDERS:
                            spent = state.get("economy_data", {}).get("by_provider", {}).get(p["key"], 0)
                            spent_str = f"${spent:.4f}" if spent else ""
                            purl = p["url"]
                            plabel = p["label"]
                            with ui.element('a').props(
                                f'href="{purl}" target="_blank" rel="noopener"'
                            ).style(
                                'display:flex; flex-direction:column; align-items:center;'
                                'justify-content:center; padding:10px 8px;'
                                'background:rgba(99,130,255,0.05);'
                                'border:1px solid rgba(99,130,255,0.12);'
                                'border-radius:6px; text-decoration:none; cursor:pointer;'
                                'transition:background 0.15s, border-color 0.15s; height:100%;'
                            ):
                                ui.html(
                                    f'<span style="font-family:JetBrains Mono,monospace;font-size:0.58rem;'
                                    f'font-weight:600;letter-spacing:0.07em;'
                                    f'color:rgba(200,210,240,0.75);text-transform:uppercase;">{plabel}</span>'
                                    + (
                                        f'<span style="font-family:JetBrains Mono,monospace;'
                                        f'font-size:0.52rem;color:#6c8cff;margin-top:3px;">{spent_str}</span>'
                                        if spent_str else ''
                                    )
                                )

                # ── METRICS GRID 3×3 — динамический контейнер, перестраивается через render_metrics_grid() ──
                refs["metrics_grid"] = ui.element('div').style(
                    'display:grid;'
                    'grid-template-columns: repeat(3, 1fr);'
                    'grid-template-rows: repeat(3, 1fr);'
                    'gap:16px;'
                    'margin:0 20px 20px 20px;'
                    'flex:1;'
                    'min-height:0;'
                )



            # RIGHT: DETAIL
            with ui.element('div').classes('cab-right'):
                with ui.element('div').classes('cab-panel-title').style(
                    'display:flex; align-items:center; gap:0; justify-content:space-between;'
                ):
                    ui.html('<span class="dashboard-panel-title">🔍 детали агента</span>')
                    with ui.element('div').style(
                        'display:flex; gap:4px; margin-right:4px;'
                    ):
                        ui.button('Агент', on_click=lambda: set_center_view('economy')).props('flat dense').style(
                            'font-family:JetBrains Mono,monospace; font-size:0.55rem;'
                            'letter-spacing:0.06em; color:rgba(180,190,220,0.6);'
                            'padding:2px 8px; border-radius:4px;'
                            'background:rgba(99,130,255,0.08);'
                            'border:1px solid rgba(99,130,255,0.15);'
                        )
                        ui.button('Observability', on_click=lambda: set_center_view('observability')).props('flat dense').style(
                            'font-family:JetBrains Mono,monospace; font-size:0.55rem;'
                            'letter-spacing:0.06em; color:rgba(180,190,220,0.6);'
                            'padding:2px 8px; border-radius:4px;'
                            'background:rgba(99,130,255,0.08);'
                            'border:1px solid rgba(99,130,255,0.15);'
                        )
                refs["detail_panel"] = ui.element('div').classes('cab-tab-content')

    # ── INIT ──
    ui.timer(30, update_all)
    ui.timer(0.3, update_all, once=True)   # первый запуск после установки WS соединения
# patch_dashboard_2_applied

# patch_dashboard_3_applied

# patch_dashboard_final_applied
# patch_top_stubs_applied
