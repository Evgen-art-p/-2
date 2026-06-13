# studio/cartridge_manager/ui.py — Менеджер картриджей
# Студия «Шесть Пальцев» · 2026
#
# Визуальное управление слотами:
# - Карточки активных картриджей
# - Включить/выключить
# - Клонировать / удалить
# - Добавить новый из доступных модулей
# - Сводка по городу

from nicegui import ui
from pathlib import Path

from studio.slot_manager import SlotManager, Slot, MODULES_DIR
from studio.cartridge import CartridgeManifest


# ═══════════════════════════════════════════════════════════
# CSS
# ═══════════════════════════════════════════════════════════

MANAGER_CSS = """
<style>
  .cm-page {
    min-height: 100vh;
    background: #0a0a0e;
    color: rgba(226,232,240,.9);
    padding: 24px;
    font-family: 'Inter', 'Segoe UI', system-ui, sans-serif;
  }
  .cm-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 24px;
  }
  .cm-title {
    font-size: 22px;
    font-weight: 700;
    letter-spacing: .02em;
  }
  .cm-stats {
    display: flex;
    gap: 24px;
    font-size: 13px;
    color: rgba(226,232,240,.55);
  }
  .cm-stat-num {
    font-weight: 700;
    font-size: 18px;
    color: rgba(226,232,240,.85);
    margin-right: 4px;
  }
  .cm-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 14px;
    margin-bottom: 24px;
  }
  .cm-card {
    background: rgba(20,20,28,.45);
    border: 1px solid rgba(255,255,255,.10);
    border-radius: 16px;
    padding: 16px 18px;
    backdrop-filter: blur(8px);
    transition: border-color .2s ease, box-shadow .2s ease;
  }
  .cm-card:hover {
    border-color: rgba(255,255,255,.18);
  }
  .cm-card-disabled {
    opacity: .45;
  }
  .cm-card-top {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 10px;
  }
  .cm-card-icon {
    font-size: 24px;
    margin-right: 10px;
  }
  .cm-card-label {
    font-weight: 700;
    font-size: 14px;
    letter-spacing: .02em;
  }
  .cm-card-id {
    font-size: 11px;
    color: rgba(226,232,240,.4);
    font-family: monospace;
  }
  .cm-card-agents {
    font-size: 12px;
    color: rgba(226,232,240,.5);
    margin-bottom: 12px;
  }
  .cm-card-actions {
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
  }
  .cm-btn {
    font-size: 11px;
    padding: 4px 12px;
    border-radius: 8px;
    border: 1px solid rgba(255,255,255,.12);
    background: rgba(0,0,0,.25);
    color: rgba(226,232,240,.7);
    cursor: pointer;
    transition: all .15s ease;
    font-family: inherit;
  }
  .cm-btn:hover {
    background: rgba(255,255,255,.08);
    border-color: rgba(255,255,255,.22);
    color: rgba(226,232,240,.95);
  }
  .cm-btn-danger:hover {
    background: rgba(220,50,50,.15);
    border-color: rgba(220,50,50,.35);
    color: #f87171;
  }
  .cm-btn-clone:hover {
    background: rgba(80,200,120,.12);
    border-color: rgba(80,200,120,.30);
    color: #6ee7b7;
  }
  .cm-add-section {
    margin-top: 8px;
    padding: 18px;
    background: rgba(20,20,28,.3);
    border: 1px dashed rgba(255,255,255,.12);
    border-radius: 16px;
  }
  .cm-add-title {
    font-size: 14px;
    font-weight: 600;
    margin-bottom: 12px;
    color: rgba(226,232,240,.6);
  }
  .cm-module-grid {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
  }
  .cm-module-btn {
    font-size: 12px;
    padding: 6px 14px;
    border-radius: 10px;
    border: 1px solid rgba(255,255,255,.10);
    background: rgba(0,0,0,.2);
    color: rgba(226,232,240,.65);
    cursor: pointer;
    transition: all .15s ease;
    font-family: inherit;
  }
  .cm-module-btn:hover {
    background: rgba(108,140,255,.12);
    border-color: rgba(108,140,255,.30);
    color: rgba(226,232,240,.95);
  }
  .cm-back {
    font-size: 13px;
    color: rgba(226,232,240,.45);
    cursor: pointer;
    transition: color .15s;
    text-decoration: none;
    display: inline-flex;
    align-items: center;
    gap: 4px;
  }
  .cm-back:hover { color: rgba(226,232,240,.8); }
  .cm-dot {
    width: 8px; height: 8px;
    border-radius: 50%;
    display: inline-block;
    margin-right: 6px;
  }
  .cm-dot-on { background: #34d399; }
  .cm-dot-off { background: rgba(255,255,255,.2); }
</style>
"""


# ═══════════════════════════════════════════════════════════
# PAGE
# ═══════════════════════════════════════════════════════════

def page_cartridge_manager() -> None:
    """Страница менеджера картриджей."""

    ui.add_head_html(MANAGER_CSS)

    sm = SlotManager()

    # Список всех доступных модулей (для кнопки «добавить»)
    available_modules = []
    if MODULES_DIR.exists():
        for d in sorted(MODULES_DIR.iterdir()):
            if d.is_dir() and d.name != "residents" and (d / "info.json").exists():
                available_modules.append(d.name)

    # ═══ Рендер ═══════════════════════════════════════════

    @ui.refreshable
    def render_manager():
        sm_fresh = SlotManager()
        summary = sm_fresh.summary()
        slots = sm_fresh.slots

        with ui.element('div').classes('cm-page'):

            # ── Header ──
            with ui.element('div').classes('cm-header'):
                with ui.row().style('align-items: center; gap: 16px;'):
                    ui.html('<a class="cm-back" href="/">← рецепция</a>')
                    ui.html(f'<div class="cm-title">🔌 Картриджи</div>')

                ui.html(f'''
                    <div class="cm-stats">
                        <div><span class="cm-stat-num">{summary["total_slots"]}</span>слотов</div>
                        <div><span class="cm-stat-num">{summary["total_agents"]}</span>агентов</div>
                        <div><span class="cm-stat-num">{summary["total_residents"]}</span>резидентов</div>
                        <div><span class="cm-stat-num">{summary["total_citizens"]}</span>граждан</div>
                    </div>
                ''')

            # ── Карточки слотов ──
            with ui.element('div').classes('cm-grid'):
                for slot in sorted(slots, key=lambda s: s.order):
                    try:
                        manifest = CartridgeManifest.load(slot.module)
                        agent_count = len(manifest.get_all_agents())
                        phases = list(manifest.phases.keys())
                    except Exception:
                        agent_count = 0
                        phases = []

                    card_cls = 'cm-card' + ('' if slot.enabled else ' cm-card-disabled')

                    with ui.element('div').classes(card_cls):
                        # Top row: icon + name + dot
                        with ui.element('div').classes('cm-card-top'):
                            with ui.row().style('align-items: center; gap: 8px;'):
                                dot_cls = 'cm-dot cm-dot-on' if slot.enabled else 'cm-dot cm-dot-off'
                                ui.html(f'<span class="{dot_cls}"></span>')
                                ui.html(f'<span class="cm-card-icon">{manifest.icon if manifest else "🔧"}</span>')
                                ui.html(f'<span class="cm-card-label">{slot.label}</span>')
                            ui.html(f'<span class="cm-card-id">{slot.slot_id}</span>')

                        # Info
                        phases_str = " → ".join(phases) if phases else "—"
                        ui.html(f'''
                            <div class="cm-card-agents">
                                {agent_count} агентов · модуль: {slot.module}<br>
                                фазы: {phases_str}
                            </div>
                        ''')

                        # Actions
                        with ui.element('div').classes('cm-card-actions'):
                            # Toggle
                            if slot.enabled:
                                def make_toggle_off(sid=slot.slot_id):
                                    def do():
                                        SlotManager().toggle_slot(sid, False)
                                        ui.notify(f'⏸ {sid} выключен', type='warning')
                                        render_manager.refresh()
                                    return do
                                ui.button('выключить', on_click=make_toggle_off()).props(
                                    'flat dense no-caps size=xs'
                                ).style(
                                    'font-size:11px; color: rgba(226,232,240,.5); border: 1px solid rgba(255,255,255,.08); border-radius: 8px; padding: 2px 10px;'
                                )
                            else:
                                def make_toggle_on(sid=slot.slot_id):
                                    def do():
                                        SlotManager().toggle_slot(sid, True)
                                        ui.notify(f'▶ {sid} включён', type='positive')
                                        render_manager.refresh()
                                    return do
                                ui.button('включить', on_click=make_toggle_on()).props(
                                    'flat dense no-caps size=xs'
                                ).style(
                                    'font-size:11px; color: #6ee7b7; border: 1px solid rgba(80,200,120,.25); border-radius: 8px; padding: 2px 10px;'
                                )

                            # Clone
                            def make_clone(sid=slot.slot_id, mod=slot.module):
                                def do():
                                    try:
                                        new_slot = SlotManager().add_slot(mod)
                                        ui.notify(f'✅ Клон создан: {new_slot.slot_id}', type='positive')
                                        render_manager.refresh()
                                    except Exception as e:
                                        ui.notify(f'❌ {e}', type='negative')
                                return do
                            ui.button('клонировать', on_click=make_clone()).props(
                                'flat dense no-caps size=xs'
                            ).style(
                                'font-size:11px; color: rgba(226,232,240,.5); border: 1px solid rgba(255,255,255,.08); border-radius: 8px; padding: 2px 10px;'
                            )

                            # Remove (only for clones — not original slots)
                            is_clone = slot.slot_id != slot.module
                            if is_clone:
                                def make_remove(sid=slot.slot_id):
                                    def do():
                                        SlotManager().remove_slot(sid, delete_memory=False)
                                        ui.notify(f'🗑 {sid} удалён (память сохранена)', type='warning')
                                        render_manager.refresh()
                                    return do
                                ui.button('удалить', on_click=make_remove()).props(
                                    'flat dense no-caps size=xs'
                                ).style(
                                    'font-size:11px; color: rgba(248,113,113,.6); border: 1px solid rgba(220,50,50,.2); border-radius: 8px; padding: 2px 10px;'
                                )

                            # Open workshop
                            def make_open(mod=slot.module):
                                def do():
                                    ui.navigate.to(f'/workshop?dept={mod}')
                                return do
                            ui.button('открыть цех', on_click=make_open()).props(
                                'flat dense no-caps size=xs'
                            ).style(
                                'font-size:11px; color: rgba(108,140,255,.8); border: 1px solid rgba(108,140,255,.2); border-radius: 8px; padding: 2px 10px;'
                            )

            # ── Добавить картридж ──
            with ui.element('div').classes('cm-add-section'):
                ui.html('<div class="cm-add-title">+ Добавить картридж</div>')

                with ui.element('div').classes('cm-module-grid'):
                    for mod_id in available_modules:
                        try:
                            m = CartridgeManifest.load(mod_id)
                            btn_label = f'{m.icon} {m.label}'
                        except Exception:
                            btn_label = mod_id

                        def make_add(mid=mod_id):
                            def do():
                                try:
                                    new_slot = SlotManager().add_slot(mid)
                                    ui.notify(f'✅ Добавлен: {new_slot.slot_id} ({new_slot.label})', type='positive')
                                    render_manager.refresh()
                                except Exception as e:
                                    ui.notify(f'❌ {e}', type='negative')
                            return do

                        ui.button(btn_label, on_click=make_add()).props(
                            'flat dense no-caps'
                        ).style(
                            'font-size:12px; color: rgba(226,232,240,.65); border: 1px solid rgba(255,255,255,.10); '
                            'border-radius: 10px; padding: 5px 14px; background: rgba(0,0,0,.2);'
                        )

    render_manager()
