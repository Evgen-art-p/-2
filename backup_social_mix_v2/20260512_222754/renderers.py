"""
Assembly — renderers (grid, cards, preview, stats, progress, right panels, asset strip)
"""
import json
import time
from pathlib import Path
from nicegui import ui

from studio.assembly.constants import (
    RENDER_DIR, IMAGE_FORMATS, DEFAULT_FORMAT,
    get_asset_name, get_asset_category, lookup_asset_metadata,
)
from studio.assembly.helpers import to_url, asset_to_url


def render_grid(state, refs):
    """Render the main asset grid (covers / frames / clips / characters / badges / ui)."""
    if not refs["grid"] or not state["tasks"]:
        return
    refs["grid"].clear()
    tasks = state["tasks"]
    with refs["grid"]:
        if tasks["thumbnails"]:
            ui.html('<div class="sec-head">COVERS</div>')
            with ui.element("div").classes("assets-grid"):
                for t in tasks["thumbnails"]:
                    _card(f"thumb_{t['variant']}", t, "thumb", state, refs)
        if tasks["key_frames"]:
            ui.html('<div class="sec-head">KEY FRAMES</div>')
            with ui.element("div").classes("assets-grid"):
                for f in tasks["key_frames"]:
                    _card(f"frame_{f['index']}", f, "frame", state, refs)
        if tasks["videos"]:
            ui.html('<div class="sec-head">VIDEO CLIPS</div>')
            with ui.element("div").classes("assets-grid"):
                for v in tasks["videos"]:
                    _card(f"clip_{v['index']}", v, "video", state, refs)
        # ── НОВЫЕ СЕКЦИИ ──────────────────────────────────────
        if tasks.get("characters"):
            ui.html('<div class="sec-head">ПЕРСОНАЖИ</div>')
            with ui.element("div").classes("assets-grid"):
                for ch in tasks["characters"]:
                    _card(f"char_{ch['char_id']}", ch, "char", state, refs)
        if tasks.get("badges"):
            ui.html('<div class="sec-head">БЕЙДЖИ</div>')
            with ui.element("div").classes("assets-grid"):
                for b in tasks["badges"]:
                    _card(f"badge_{b['achievement_id']}", b, "badge", state, refs)
        if tasks.get("interaction_assets"):
            ui.html('<div class="sec-head">UI / ИНТЕРАКТИВ</div>')
            with ui.element("div").classes("assets-grid"):
                for ia in tasks["interaction_assets"]:
                    _card(f"ui_{ia['interaction_id']}_{ia['element_id']}", ia, "ui", state, refs)


def _card(key, item, kind, state, refs):
    """Single asset card in the grid."""
    cls = "asset-card"
    if key in state["selected"]:
        cls += " selected"
    if state["active_card"] == key:
        cls += " active-card"
    has = item.get("path") is not None

    def _click(e, k=key, it=item):
        state["active_card"] = k
        state["active_item"] = it
        render_grid(state, refs)
        render_preview(it, state, refs)

    def _toggle(e, k=key):
        if k in state["selected"]:
            state["selected"].discard(k)
        else:
            state["selected"].add(k)
        render_grid(state, refs)
        render_stats(state, refs)

    with ui.element("div").classes(cls).on("click", _click).on("contextmenu.prevent", _toggle):
        if has:
            ui.image(f'{to_url(item["path"])}?t={int(time.time()*1000)}').classes("asset-thumb")
        else:
            icon = {"thumb": "IMG", "frame": "PIC", "video": "VID",
                    "char": "👤", "badge": "🏆", "ui": "🖱️"}.get(kind, "?")
            ui.html(f'<div class="asset-ph">{icon}</div>')
        ui.html('<div class="asset-chk">V</div>')
        with ui.element("div").classes("asset-info"):
            if kind == "thumb":
                ui.html(f'<div class="asset-lbl">Cover {item["variant"].upper()}</div>')
            elif kind == "frame":
                ui.html(f'<div class="asset-lbl">Frame #{item["index"]}</div>')
            elif kind == "video":
                ui.html(f'<div class="asset-lbl">Clip #{item["index"]}</div>')
            elif kind == "char":
                lbl = item.get("char_name") or item.get("char_id", "?")
                ui.html(f'<div class="asset-lbl">👤 {lbl}</div>')
            elif kind == "badge":
                lbl = item.get("achievement_id", "badge")
                ui.html(f'<div class="asset-lbl">🏆 {lbl}</div>')
            elif kind == "ui":
                lbl = f'{item.get("interaction_id","?")} / {item.get("element_id","?")}'
                ui.html(f'<div class="asset-lbl">🖱️ {lbl}</div>')
            sc = "#00ff88" if has else "rgba(255,255,255,0.3)"
            st = "Ready" if has else "Pending"
            with ui.row().style("align-items:center;gap:6px;margin-top:4px;"):
                ui.html(f'<span style="color:{sc};font-size:10px;">{st}</span>')
                if has:
                    from studio.assembly.actions import do_export
                    ui.button("EXPORT", on_click=lambda e, it=item, s=state: do_export(it, s)).props("flat dense").style(
                        "height:18px;padding:0 6px;border-radius:6px;font-size:9px;font-weight:800;"
                        "border:1px solid rgba(0,255,136,0.3);background:rgba(0,255,136,0.10);"
                        "color:rgba(0,255,136,0.9);min-width:0;")
            # Ref badges
            _ref_ids = item.get("ref_ids", [])
            if _ref_ids:
                _badges = ""
                for _rid in _ref_ids[:3]:
                    _cat = get_asset_category(_rid)
                    _ico = {"character": "🧑", "location": "📍", "prop": "🔧"}.get(_cat, "📎")
                    _nm = get_asset_name(_rid)
                    if len(_nm) > 12:
                        _nm = _nm[:11] + "…"
                    _badges += (
                        f'<span style="display:inline-block;padding:1px 5px;'
                        f'margin:1px;border-radius:6px;font-size:9px;'
                        f'background:rgba(0,204,255,0.12);color:rgba(0,204,255,0.85);'
                        f'border:1px solid rgba(0,204,255,0.2);">'
                        f'{_ico}{_nm}</span>'
                    )
                if len(_ref_ids) > 3:
                    _badges += f'<span style="font-size:9px;color:rgba(255,255,255,0.3);">+{len(_ref_ids)-3}</span>'
                ui.html(f'<div style="margin-top:3px;line-height:1.6;">{_badges}</div>')


def render_preview(item, state, refs):
    """Render prompt editor + preview for active item."""
    if not refs["preview"]:
        return
    refs["preview"].clear()
    with refs["preview"]:
        if item and item.get("prompt"):
            # Label
            kind_lbl = ""
            if "variant" in item:
                kind_lbl = f"Cover {item['variant'].upper()}"
            elif "purpose" in item:
                kind_lbl = f"Frame #{item.get('index', '?')}"
            elif "segment" in item:
                kind_lbl = f"Clip #{item.get('index', '?')}"
            if kind_lbl:
                ui.html(f'<div class="editor-label">{kind_lbl}</div>')

            # Preview image
            if item.get("path") and Path(item["path"]).exists():
                _img_url = f'{to_url(item["path"])}?t={int(time.time()*1000)}'
                ui.image(_img_url).style(
                    'width:100%;max-height:200px;object-fit:contain;'
                    'border-radius:12px;margin-bottom:6px;'
                    'border:1px solid rgba(255,255,255,0.08);')

            # Asset strip
            _render_asset_strip(refs["preview"], item)

            # Prompt textarea
            prompt_input = ui.textarea(value=item["prompt"]).props(
                "autogrow borderless input-style='color: white !important'"
            ).style(
                "width:100%; min-height:60px; max-height:140px; padding:8px 12px;"
                "background:rgba(0,204,255,0.08); border:1px solid rgba(0,204,255,0.30);"
                "border-radius:12px; color:white !important; overflow-y:auto;"
                "font-size:11px; font-family:JetBrains Mono, monospace; line-height:1.5;")
            def on_prompt_change(e, it=item):
                it["prompt"] = e.value
            prompt_input.on("change", on_prompt_change)

            # Format selector
            ui.html('<div style="color:rgba(255,255,255,0.4);font-size:10px;font-weight:600;'
                    'text-transform:uppercase;letter-spacing:0.08em;margin:8px 0 4px;">FORMAT</div>')
            _fmt_opts = list(IMAGE_FORMATS.keys())
            _cur_fmt = item.get("format", DEFAULT_FORMAT)
            if _cur_fmt not in _fmt_opts:
                _cur_fmt = DEFAULT_FORMAT
            _fmt_sel = ui.select(options=_fmt_opts, value=_cur_fmt).props("dense borderless").style(
                "width:100%;height:32px;padding:0 8px;"
                "background:rgba(0,204,255,0.08);border:1px solid rgba(0,204,255,0.25);"
                "border-radius:8px;color:white;font-size:11px;")
            def _on_fmt_change(e, it=item):
                val = e.args.get('label', DEFAULT_FORMAT) if isinstance(e.args, dict) else str(e.args)
                it["format"] = val
            _fmt_sel.on("update:model-value", _on_fmt_change)

            # Ref badges
            _p_refs = item.get("ref_ids", [])
            if _p_refs:
                ui.html('<div style="color:rgba(255,255,255,0.4);font-size:10px;font-weight:600;'
                        'text-transform:uppercase;letter-spacing:0.08em;margin:8px 0 4px;">REFERENCES</div>')
                _rhtml = ""
                for _rid in _p_refs:
                    _rcat = get_asset_category(_rid)
                    _rico = {"character": "🧑", "location": "📍", "prop": "🔧"}.get(_rcat, "📎")
                    _rnm = get_asset_name(_rid)
                    _rhtml += (
                        f'<span style="display:inline-block;padding:2px 7px;'
                        f'margin:2px;border-radius:8px;font-size:10px;'
                        f'background:rgba(0,255,136,0.10);color:rgba(0,255,136,0.85);'
                        f'border:1px solid rgba(0,255,136,0.2);">'
                        f'{_rico} {_rnm}</span>'
                    )
                ui.html(f'<div style="line-height:1.8;">{_rhtml}</div>')

            # JSON inspector
            def _show_json(it=item):
                _jdata = {k: v for k, v in it.items() if k != "path"}
                with ui.dialog() as _jdlg, ui.card().style(
                    "background:#0d1117;border:1px solid rgba(255,255,255,0.1);"
                    "min-width:500px;max-width:700px;max-height:80vh;border-radius:16px;"):
                    ui.label("SHOT JSON").style("color:white;font-weight:900;font-size:13px;margin-bottom:8px;")
                    ui.html(
                        f'<pre style="color:rgba(255,255,255,0.7);font-size:10px;'
                        f'font-family:JetBrains Mono,monospace;white-space:pre-wrap;'
                        f'max-height:60vh;overflow-y:auto;">'
                        f'{json.dumps(_jdata, ensure_ascii=False, indent=2)}</pre>')
                    ui.button("CLOSE", on_click=_jdlg.close).props("flat dense").style(
                        "color:rgba(255,255,255,0.6);margin-top:8px;")
                _jdlg.open()

            # Buttons row
            import asyncio
            from studio.assembly.generators import do_regen_single
            with ui.row().style("width:100%;gap:4px;margin-top:6px;"):
                ui.button("REGEN", on_click=lambda e, it=item: asyncio.ensure_future(
                    do_regen_single(it, state, refs)
                )).props("flat dense").style(
                    "height:28px;flex:1;border-radius:8px;"
                    "border:1px solid rgba(255,204,0,0.35);"
                    "background:linear-gradient(135deg,rgba(255,204,0,0.12),rgba(255,149,0,0.08));"
                    "color:rgba(255,255,255,0.9);font-weight:800;font-size:10px;")
                ui.button("JSON", on_click=_show_json).props("flat dense").style(
                    "height:28px;width:56px;border-radius:8px;"
                    "border:1px solid rgba(0,204,255,0.3);"
                    "background:rgba(0,204,255,0.08);"
                    "color:rgba(0,204,255,0.9);font-weight:800;font-size:10px;")
        else:
            ui.html('<span class="info-placeholder">Click a card to edit prompt</span>')


def render_stats(state, refs):
    """Render project stats in left panel."""
    if not refs["stats"] or not state["tasks"]:
        return
    refs["stats"].clear()
    t = state["tasks"]
    total = len(t["thumbnails"]) + len(t["key_frames"]) + len(t["videos"])
    done = sum(1 for x in t["thumbnails"] if x.get("path"))
    done += sum(1 for x in t["key_frames"] if x.get("path"))
    done += sum(1 for x in t["videos"] if x.get("path"))
    sel = len(state["selected"])
    project_name = t.get("project_id", "unknown")
    exp_dir = RENDER_DIR / project_name
    exported = len(list(exp_dir.glob("*"))) if exp_dir.exists() else 0
    with refs["stats"]:
        ui.html(f'''<div class="stats-box">
            <div class="st-row"><span class="st-l">Total</span><span class="st-v">{total}</span></div>
            <div class="st-row"><span class="st-l">Generated</span><span class="st-v g">{done}</span></div>
            <div class="st-row"><span class="st-l">Selected</span><span class="st-v b">{sel}</span></div>
            <div class="st-row"><span class="st-l">Exported</span><span class="st-v" style="color:#ff9500;">{exported}</span></div>
        </div>''')


def render_progress(state, refs):
    """Render generation progress bar."""
    if not refs["progress"]:
        return
    refs["progress"].clear()
    if state["generating"]:
        pct = int(state["progress"] / max(state["progress_total"], 1) * 100)
        with refs["progress"]:
            ui.html(f'''<div class="prog-box">
                <div class="prog-lbl">{state["progress_label"]} ({state["progress"]}/{state["progress_total"]})</div>
                <div class="prog-track"><div class="prog-fill" style="width:{pct}%"></div></div>
            </div>''')


def render_right_panels(state, refs):
    """Render audio / captions / publication panels."""
    tasks = state["tasks"]
    if refs["audio_panel"]:
        refs["audio_panel"].clear()
        with refs["audio_panel"]:
            if tasks and tasks.get("audio"):
                audio = tasks["audio"]
                lines = []
                if audio.get("style"):
                    lines.append(f"Style: {audio['style']}")
                if audio.get("suno_prompt"):
                    lines.append(f"Prompt: {audio['suno_prompt']}")
                ui.html(f'<div class="info-block">{"<br>".join(lines)}</div>')
            else:
                ui.html('<span class="info-placeholder">After loading .md</span>')
    if refs["captions_panel"]:
        refs["captions_panel"].clear()
        with refs["captions_panel"]:
            ui.html('<span class="info-placeholder">After loading .md</span>')
    if refs["pub_panel"]:
        refs["pub_panel"].clear()
        with refs["pub_panel"]:
            if tasks and tasks.get("publication"):
                pub = tasks["publication"]
                desc = pub.get("description", "")[:200]
                ui.html(f'<div class="info-block">{desc}</div>')
            else:
                ui.html('<span class="info-placeholder">After loading .md</span>')


def _render_asset_strip(container, item: dict):
    """Draw asset preview strip for one element."""
    ref_ids = item.get("ref_ids", [])
    if isinstance(ref_ids, str):
        ref_ids = [ref_ids]
    if not ref_ids:
        return
    with container:
        ui.html('<div class="asset-strip-label">🎨 Ассеты</div>')
        with ui.element("div").classes("asset-strip"):
            for rid in ref_ids:
                meta = lookup_asset_metadata(rid)
                name = meta["name"] if meta else rid
                preview = meta.get("preview_path") if meta else None
                with ui.element("div").classes("asset-thumb-wrap"):
                    if preview and Path(preview).exists():
                        src = asset_to_url(preview)
                        ui.html(
                            f'<img class="asset-thumb" src="{src}" alt="{name}">'
                            f'<div class="asset-tooltip">{name}</div>')
                    else:
                        ui.html(
                            f'<div class="asset-ph-small" title="{name}">?</div>'
                            f'<div class="asset-tooltip">{name}</div>')
