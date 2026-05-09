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
from studio.billing_ledger import get_economy_data, get_agent_stats

ui.add_head_html('<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>')

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
    }

    refs = {
        "agent_list": None,
        "detail_panel": None,
        "total_label": None,
        "burn_label": None,
        "provider_chart": None,
        "agent_chart": None,
    }

    # ── DATA SOURCE: billing_ledger ──

    def update_all():
        state["economy_data"] = get_economy_data(state["period"])
        state["all_agents"] = list_all_agents()
        update_header_stats()
        render_agent_list()
        render_charts()
        render_detail()

    def update_header_stats():
        eco = state["economy_data"]
        if refs["total_label"]:
            refs["total_label"].set_text(f'${eco["total"]:.4f}')
        if refs["burn_label"]:
            refs["burn_label"].set_text(f'${eco["burn_rate"]:.4f}/m')

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
        eco = state["economy_data"]

        p_labels = list(eco.get("by_provider", {}).keys())
        p_data = list(eco.get("by_provider", {}).values())

        top_agents = dict(list(eco.get("by_agent", {}).items())[:5])
        a_labels = list(top_agents.keys())
        a_data = list(top_agents.values())

        js = f"""
        try {{
            const pCtx = document.getElementById('providerChart');
            if (pCtx) {{
                if (window.myProviderChart) window.myProviderChart.destroy();
                window.myProviderChart = new Chart(pCtx, {{
                    type: 'bar',
                    data: {{
                        labels: {json.dumps(p_labels)},
                        datasets: [{{
                            label: 'USD',
                            data: {json.dumps(p_data)},
                            backgroundColor: '#6c8cff',
                            borderRadius: 4
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {{ legend: {{ display: false }} }},
                        scales: {{
                            y: {{ 
                                grid: {{ color: 'rgba(99,130,255,0.06)' }}, 
                                ticks: {{ color: 'rgba(180,190,220,0.5)', font: {{ size: 10 }} }} 
                            }},
                            x: {{ 
                                ticks: {{ color: 'rgba(180,190,220,0.5)', font: {{ size: 10 }} }} 
                            }}
                        }}
                    }}
                }});
            }}

            const aCtx = document.getElementById('agentChart');
            if (aCtx) {{
                if (window.myAgentChart) window.myAgentChart.destroy();
                window.myAgentChart = new Chart(aCtx, {{
                    type: 'doughnut',
                    data: {{
                        labels: {json.dumps(a_labels)},
                        datasets: [{{
                            data: {json.dumps(a_data)},
                            backgroundColor: ['#6c8cff', '#c9a84c', '#a78bfa', '#f87171', '#50fa7b'],
                            borderWidth: 0
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {{ 
                            legend: {{ 
                                position: 'right', 
                                labels: {{ 
                                    color: 'rgba(180,190,220,0.7)', 
                                    font: {{ size: 10 }},
                                    boxWidth: 10,
                                    padding: 8
                                }} 
                            }} 
                        }}
                    }}
                }});
            }}
        }} catch(e) {{ console.log('Chart error', e); }}
        """
        ui.run_javascript(js)

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
            with ui.element('div').classes('cab-center').style('padding-left: 0; margin-left: 0;'):
                # ── Верхняя полоса: статы + кнопки провайдеров ──
                with ui.element('div').style(
                    'display:flex; align-items:stretch; gap:20px; margin:20px; width:calc(100% - 40px);'
                ):
                    # Левая часть: Total Spend, Burn Rate, пустое пространство (три колонки внутри левой половины)
                    with ui.element('div').style(
                        'display:grid; grid-template-columns:repeat(3, 1fr); gap:20px; flex:1;'
                    ):
                        with ui.card().classes('dashboard-stat-card'):
                            ui.label('TOTAL SPEND').classes('dashboard-stat-label')
                            refs["total_label"] = ui.label('$0.0000').classes('dashboard-stat-value-total')
                        with ui.card().classes('dashboard-stat-card'):
                            ui.label('BURN RATE').classes('dashboard-stat-label')
                            refs["burn_label"] = ui.label('$0.0000/m').classes('dashboard-stat-value-burn')
                        # Пустая карточка-заглушка для симметрии с кнопками
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

                # ── Графики ──
                with ui.element('div').classes('dashboard-chart-row').style('gap: 20px;'):
                    with ui.element('div').classes('dashboard-chart-box'):
                        ui.label('PROVIDERS BREAKDOWN').classes('dashboard-chart-title')
                        ui.html('<canvas id="providerChart" style="width:100%;height:100%;"></canvas>')

                    with ui.element('div').classes('dashboard-chart-box'):
                        ui.label('TOP SPENDERS').classes('dashboard-chart-title')
                        ui.html('<canvas id="agentChart" style="width:100%;height:100%;"></canvas>')

            # RIGHT: DETAIL
            with ui.element('div').classes('cab-right'):
                with ui.element('div').classes('cab-panel-title'):
                    ui.html('<span class="dashboard-panel-title">🔍 детали агента</span>')
                refs["detail_panel"] = ui.element('div').classes('cab-tab-content')

    # ── INIT ──
    ui.timer(30, update_all)
    update_all()