"""
Assembly — main entry point
Modular refactor: 973 → ~70 lines (layout only)
"""
from nicegui import ui

from studio.assembly.css import ASSEMBLY_CSS
from studio.assembly.actions import (
    do_export_all, do_open_folder, do_download_zip, show_picker,
    load_md,
)
from studio.assembly.generators import do_generate_images, do_generate_all
# constants import triggers catalog load + static routes
import studio.assembly.constants  # noqa: F401

from studio.assembly.actions import (
    do_export_all, do_open_folder, do_download_zip, show_picker,
    load_md, do_extract_logic  # ← ДОБАВЬ ЭТО
)

def page_assembly():

    state = {
        "tasks": None, "selected": set(), "generating": False,
        "progress": 0, "progress_total": 0, "progress_label": "",
        "active_card": None, "active_item": None,
    }

    refs = {
        "grid": None, "stats": None, "preview": None, "progress": None,
        "audio_panel": None, "captions_panel": None, "pub_panel": None,
    }

    ui.add_head_html(f'<style>{ASSEMBLY_CSS}</style>')
    ui.html('<div id="bg-asm"></div>')

    # ===== LAYOUT =====

    with ui.element('div').classes('asm-app'):

        # ── HEADER ──
        with ui.element('div').classes('area-header glass'):
            with ui.row().style('width:100%;height:100%;align-items:center;padding:0 20px;gap:0;'):
                ui.button('\u2190 BACK', on_click=lambda: ui.navigate.to('/workshop')).props('flat dense').style(
                    'height:36px;padding:0 14px;border-radius:10px;'
                    'border:1px solid rgba(255,255,255,0.2);background:rgba(255,255,255,0.06);'
                    'color:white;font-weight:800;font-size:11px;')
                ui.element('div').style('flex:1;')
                ui.button('EXPORT ALL', on_click=lambda: do_export_all(state, refs)).props('flat dense').style(
                    'height:36px;padding:0 14px;border-radius:10px;margin-right:8px;'
                    'border:1px solid rgba(0,255,136,0.3);background:rgba(0,255,136,0.08);'
                    'color:rgba(0,255,136,0.9);font-weight:800;font-size:11px;letter-spacing:0.05em;')
                ui.button('\U0001f4c2 FOLDER', on_click=lambda: do_open_folder(state)).props('flat dense').style(
                    'height:36px;padding:0 14px;border-radius:10px;margin-right:8px;'
                    'border:1px solid rgba(0,204,255,0.3);background:rgba(0,204,255,0.08);'
                    'color:rgba(0,204,255,0.9);font-weight:800;font-size:11px;')
                ui.button('\U0001f4e6 ZIP', on_click=lambda: do_download_zip(state)).props('flat dense').style(
                    'height:36px;padding:0 14px;border-radius:10px;margin-right:12px;'
                    'border:1px solid rgba(255,149,0,0.3);background:rgba(255,149,0,0.08);'
                    'color:rgba(255,149,0,0.9);font-weight:800;font-size:11px;')
                ui.button('LOAD .MD', on_click=lambda: show_picker(state, refs)).props('flat dense').style(
                    'height:36px;padding:0 14px;border-radius:10px;'
                    'border:1px solid rgba(255,255,255,0.2);background:rgba(255,255,255,0.06);'
                    'color:white;font-weight:800;font-size:11px;')
                 # Кнопка извлечения логики (ставим перед FOLDER)
                ui.button('🧠 LOGIC', on_click=lambda: do_extract_logic(state)).props('flat dense').style(
                    'height:36px;padding:0 14px;border-radius:10px;margin-right:8px;'
                    'border:1px solid rgba(255,0,255,0.3);background:rgba(255,0,255,0.08);'
                    'color:rgba(255,0,255,0.9);font-weight:800;font-size:11px;')   
                    

        # ── LEFT PANEL ──
        with ui.element('div').classes('area-left glass'):
            with ui.element('div').classes('left-col'):
                ui.html('<div class="panel-title">PROJECT</div>')
                with ui.element('div').classes('panel-body'):
                    refs["stats"] = ui.element('div')
                    with refs["stats"]:
                        ui.html('<span class="info-placeholder">Load .md first</span>')
                ui.html('<div class="panel-title">PROMPT</div>')
                with ui.element('div').classes('prompt-area'):
                    refs["preview"] = ui.element('div')
                    with refs["preview"]:
                        ui.html('<span class="info-placeholder">Click a card</span>')
                refs["progress"] = ui.element('div').style('padding:0 16px;')
                ui.button('IMAGES', on_click=lambda: do_generate_images(state, refs)).classes('neon-btn o').props('flat').style('margin:4px 0;')
                ui.button('ALL (IMG+VID)', on_click=lambda: do_generate_all(state, refs)).classes('neon-btn g').props('flat')

        # ── STAGE (center grid) ──
        with ui.element('div').classes('area-stage glass'):
            with ui.element('div').style('height:100%; padding:16px; overflow-y:auto;'):
                refs["grid"] = ui.element('div')
                with refs["grid"]:
                    ui.html('<div style="display:grid; place-items:center; height:300px; color:rgba(255,255,255,0.2);">Load final .md to see assets</div>')

        # ── RIGHT PANEL ──
        with ui.element('div').classes('area-right glass'):
            with ui.element('div').classes('right-col'):
                ui.html('<div class="panel-title">AUDIO / SUNO</div>')
                with ui.element('div').classes('panel-body').style('overflow-y:auto;'):
                    refs["audio_panel"] = ui.element('div')
                    with refs["audio_panel"]:
                        ui.html('<span class="info-placeholder">After loading .md</span>')
                ui.html('<div class="panel-title">CAPTIONS</div>')
                with ui.element('div').classes('panel-body').style('overflow-y:auto;'):
                    refs["captions_panel"] = ui.element('div')
                    with refs["captions_panel"]:
                        ui.html('<span class="info-placeholder">After loading .md</span>')
                ui.html('<div class="panel-title">PUBLICATION</div>')
                with ui.element('div').classes('pub-area'):
                    refs["pub_panel"] = ui.element('div')
                    with refs["pub_panel"]:
                        ui.html('<span class="info-placeholder">After loading .md</span>')
