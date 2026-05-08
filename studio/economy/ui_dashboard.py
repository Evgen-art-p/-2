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
from nicegui import ui
from studio.cabinet.css import CABINET_CSS
from studio.cabinet.agents import list_all_agents
from studio.billing_ledger import get_economy_data, get_agent_stats

ui.add_head_html('<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>')

@ui.page('/dashboard')
def dashboard_page():
    ui.add_head_html(f'<style>{CABINET_CSS}</style>')
    
    # ── STATE ──
    state = {
        "selected_agent": None,
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
    
    def select_agent(agent_id):
        state["selected_agent"] = agent_id
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
                        with ui.element('div').classes('cab-dept-header-left'):
                            arrow_style = 'transform: rotate(90deg)' if is_open else ''
                            ui.html(f'<span class="cab-dept-arrow" style="{arrow_style}">▶</span>')
                            ui.html(f'<span class="cab-dept-name">{slot_id}</span>')
                        
                        ui.html(f'<span class="cab-dept-count">${slot_total:.3f} ({len(agents)})</span>')
                    
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
                            is_active = state["selected_agent"] == aid
                            
                            cls = 'cab-agent-card active' if is_active else 'cab-agent-card'
                            
                            with ui.element('div').classes(cls).on('click', lambda _, _id=aid: select_agent(_id)):
                                with ui.element('div').classes('cab-agent-top'):
                                    avatar_url = agent.get("avatar", "")
                                    ui.html(f'<div class="cab-agent-avatar" style="background-image:url(\'{avatar_url}\')"></div>')
                                    ui.label(agent.get("label", aid)).classes('cab-agent-name')
                                    ui.label(f'${cost:.3f}').style('font-family:JetBrains Mono;font-size:0.75rem;color:#6c8cff;')
                                
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
        
        if not aid:
            with el:
                ui.html('<div style="text-align:center;padding:40px;color:rgba(140,150,180,0.3);font-family:JetBrains Mono;font-size:0.7rem;">выбери агента слева</div>')
            return
        
        # Ищем агента в all_agents
        agent = None
        for dept_agents in state["all_agents"].values():
            for a in dept_agents:
                if a["id"] == aid:
                    agent = a
                    break
            if agent:
                break
        
        stats = state.get("agent_stats", {})
        
        with el:
            # Аватар
            avatar_url = agent.get("avatar", "") if agent else ""
            ui.html(f'<div class="cab-detail-avatar" style="background-image:url(\'{avatar_url}\');margin:20px auto;"></div>')
            
            # Имя и ID
            ui.label(agent.get("label", aid) if agent else aid).style(
                'text-align:center;font-family:JetBrains Mono;font-size:1.1rem;color:rgba(220,225,240,0.95);'
            )
            ui.label(f'ID: {aid}').style(
                'text-align:center;font-family:JetBrains Mono;font-size:0.65rem;color:rgba(140,150,180,0.4);margin-bottom:12px;'
            )
            
            ui.html('<hr style="border-color:rgba(99,130,255,0.08);margin:12px 0;">')
            
            # ── ОСНОВНЫЕ МЕТРИКИ ──
            ui.html('<div class="cab-detail-header">💰 финансы агента</div>')
            
            total = stats.get("total", 0)
            burn = stats.get("burn_rate", 0)
            calls = stats.get("total_calls", 0)
            avg = stats.get("avg_cost", 0)
            
            ui.html(f'<div class="cab-dna-row"><span class="cab-dna-label">Total Spend</span><span class="cab-dna-val" style="color:#6c8cff">${total:.4f}</span></div>')
            ui.html(f'<div class="cab-dna-row"><span class="cab-dna-label">Burn Rate</span><span class="cab-dna-val" style="color:#f87171">${burn:.4f}/m</span></div>')
            ui.html(f'<div class="cab-dna-row"><span class="cab-dna-label">Total Calls</span><span class="cab-dna-val" style="color:rgba(220,225,240,0.8)">{calls}</span></div>')
            ui.html(f'<div class="cab-dna-row"><span class="cab-dna-label">Avg Cost/Call</span><span class="cab-dna-val" style="color:#c9a84c">${avg:.4f}</span></div>')
            
            # ── BY PROVIDER ──
            by_provider = stats.get("by_provider", {})
            ui.html('<hr style="border-color:rgba(99,130,255,0.08);margin:12px 0;">')
            ui.html('<div class="cab-detail-header">🔌 провайдеры</div>')
            if by_provider:
                for prov, val in by_provider.items():
                    ui.html(f'<div class="cab-dna-row"><span class="cab-dna-label">{prov}</span><span class="cab-dna-val" style="color:#6c8cff">${val:.4f}</span></div>')
            else:
                ui.html('<div style="font-family:JetBrains Mono;font-size:0.6rem;color:rgba(140,150,180,0.25);padding:4px 0;">— нет данных за период —</div>')
            
            # ── BY MODEL ──
            by_model = stats.get("by_model", {})
            ui.html('<hr style="border-color:rgba(99,130,255,0.08);margin:12px 0;">')
            ui.html('<div class="cab-detail-header">🤖 модели</div>')
            if by_model:
                for mod, val in by_model.items():
                    model_short = mod.split("/")[-1] if "/" in mod else mod
                    ui.html(f'<div class="cab-dna-row"><span class="cab-dna-label">{model_short}</span><span class="cab-dna-val" style="color:#a78bfa">${val:.4f}</span></div>')
            else:
                ui.html('<div style="font-family:JetBrains Mono;font-size:0.6rem;color:rgba(140,150,180,0.25);padding:4px 0;">— нет данных за период —</div>')
            
            # ── ПОСЛЕДНИЕ ТРАНЗАКЦИИ ──
            recent = stats.get("recent", [])
            ui.html('<hr style="border-color:rgba(99,130,255,0.08);margin:12px 0;">')
            ui.html('<div class="cab-detail-header">📋 последние вызовы</div>')
            if recent:
                with ui.element('div').style('max-height:260px;overflow-y:auto;scrollbar-width:thin;padding-right:4px;'):
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
                        
                        ui.html(
                            f'<div style="padding:5px 0;border-bottom:1px solid rgba(99,130,255,0.06);'
                            f'font-family:JetBrains Mono;font-size:0.58rem;display:flex;justify-content:space-between;gap:8px;">'
                            f'<span style="color:rgba(140,150,180,0.45);flex-shrink:0;">{ts_str}</span>'
                            f'<span style="color:rgba(180,190,220,0.65);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{model_short}</span>'
                            f'<span style="color:rgba(140,150,180,0.4);flex-shrink:0;">{tokens}t</span>'
                            f'<span style="color:#6c8cff;flex-shrink:0;">${cost:.4f}</span>'
                            f'</div>'
                        )
            else:
                ui.html('<div style="font-family:JetBrains Mono;font-size:0.6rem;color:rgba(140,150,180,0.25);padding:4px 0;">— нет вызовов за период —</div>')
    
    # ── LAYOUT ──
    with ui.element('div').classes('cabinet-page'):
        with ui.element('div').classes('cab-grid'):
            
            # HEADER
            with ui.element('div').classes('cab-header'):
                ui.button('← в кабинет', on_click=lambda: ui.open('/cabinet')).props('flat dense').style(
                    'font-family:JetBrains Mono;font-size:0.65rem;color:#6c8cff;'
                )
                ui.label('📊 ECONOMY DASHBOARD').style(
                    'flex:1;text-align:center;font-family:JetBrains Mono;font-size:0.7rem;color:rgba(180,190,220,0.6);'
                )
                ui.label('').style('width:80px;')
            
            # LEFT: AGENTS
            with ui.element('div').classes('cab-left'):
                with ui.element('div').classes('cab-panel-title'):
                    ui.html("👥 агенты / финансы")
                
                with ui.row().style('padding:6px 10px;gap:6px;'):
                    for days, label in [(1, '1д'), (7, '7д'), (30, '30д')]:
                        is_active = state["period"] == days
                        btn_style = (
                            'font-family:JetBrains Mono;font-size:0.6rem;'
                            'color:#6c8cff;border-color:#6c8cff;'
                            if is_active else
                            'font-family:JetBrains Mono;font-size:0.6rem;'
                        )
                        ui.button(label, on_click=lambda d=days: set_period(d)).props('flat dense').style(btn_style)
                
                refs["agent_list"] = ui.element('div').style('padding:6px 0;overflow-y:auto;')
            
            # CENTER: CHARTS
            with ui.element('div').classes('cab-center'):
                with ui.element('div').style('padding:20px;display:flex;gap:20px;align-items:center;'):
                    with ui.card().style('background:#0e1018;border:1px solid rgba(99,130,255,0.08);padding:16px;min-width:150px;'):
                        ui.label('TOTAL SPEND').style('font-family:JetBrains Mono;font-size:0.6rem;color:rgba(140,150,180,0.5);')
                        refs["total_label"] = ui.label('$0.0000').style('font-family:JetBrains Mono;font-size:1.5rem;color:#6c8cff;font-weight:bold;')
                    
                    with ui.card().style('background:#0e1018;border:1px solid rgba(99,130,255,0.08);padding:16px;min-width:150px;'):
                        ui.label('BURN RATE').style('font-family:JetBrains Mono;font-size:0.6rem;color:rgba(140,150,180,0.5);')
                        refs["burn_label"] = ui.label('$0.0000/m').style('font-family:JetBrains Mono;font-size:1.5rem;color:#f87171;font-weight:bold;')
                
                with ui.element('div').style('flex:1;padding:0 20px 20px;overflow-y:auto;display:flex;gap:20px;'):
                    with ui.element('div').style('flex:1;background:#0e1018;border:1px solid rgba(99,130,255,0.08);padding:16px;'):
                        ui.label('PROVIDERS BREAKDOWN').style('font-family:JetBrains Mono;font-size:0.7rem;color:rgba(180,190,220,0.7);margin-bottom:12px;')
                        ui.html('<canvas id="providerChart" style="width:100%;height:300px;"></canvas>')
                    
                    with ui.element('div').style('flex:1;background:#0e1018;border:1px solid rgba(99,130,255,0.08);padding:16px;'):
                        ui.label('TOP SPENDERS').style('font-family:JetBrains Mono;font-size:0.7rem;color:rgba(180,190,220,0.7);margin-bottom:12px;')
                        ui.html('<canvas id="agentChart" style="width:100%;height:300px;"></canvas>')
            
            # RIGHT: DETAIL
            with ui.element('div').classes('cab-right'):
                with ui.element('div').classes('cab-panel-title'):
                    ui.html("🔍 детали агента")
                refs["detail_panel"] = ui.element('div').classes('cab-tab-content')
    
    # ── INIT ──
    ui.timer(30, update_all)
    update_all()