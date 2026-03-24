"""
Assembly — generators (image/video generation async tasks)
"""
import asyncio
from pathlib import Path
from nicegui import ui

from studio.assembly.constants import (
    OUTPUT_DIR, DEFAULT_FORMAT,
    generate_image, generate_with_refs,
)
from studio.assembly.helpers import save_manifest
from studio.assembly.renderers import render_grid, render_preview, render_stats, render_progress


async def do_regen_single(item, state, refs):
    """Regenerate a single item (image or video)."""
    if not state["tasks"] or state["generating"]:
        ui.notify("Wait, generation in progress", type="warning")
        return
    if not item.get("prompt"):
        ui.notify("No prompt!", type="negative")
        return
    tasks = state["tasks"]
    project_dir = OUTPUT_DIR / tasks["project_id"]
    project_dir.mkdir(parents=True, exist_ok=True)

    is_video = "camera" in item and "variant" not in item and "purpose" not in item
    if "variant" in item:
        fn = f"thumb_{item['variant']}.png"
        lbl = f"Cover {item['variant'].upper()}"
    elif "purpose" in item:
        fn = f"frame_{item['index']}_{item.get('purpose', 'x')}.png"
        lbl = f"Frame #{item.get('index', '?')}"
    else:
        fn = f"clip_{item['index']}_{item.get('segment', 'x').replace('-', '_')}.mp4"
        lbl = f"Clip #{item.get('index', '?')}"
        is_video = True

    state.update(generating=True, progress=0, progress_total=1, progress_label=lbl)
    render_progress(state, refs)
    try:
        if is_video:
            ui.notify(f"{lbl} — video manual mode", type="info")
            return
        _fmt = item.get("format", DEFAULT_FORMAT)
        _rids = item.get("ref_ids", [])
        if _rids:
            path = await asyncio.get_event_loop().run_in_executor(
                None, lambda p=item["prompt"], r=list(_rids), fm=_fmt, f=fn:
                    generate_with_refs(p, ref_ids=r, format=fm, filename=f))
        else:
            path = await asyncio.get_event_loop().run_in_executor(
                None, lambda p=item["prompt"], fm=_fmt, f=fn:
                    generate_image(p, format=fm, filename=f))
        final = project_dir / fn
        if item.get("path") and Path(item["path"]).exists():
            Path(item["path"]).unlink()
        Path(path).replace(final)
        item["path"] = str(final)
        state["progress"] = 1
        render_progress(state, refs)
        render_grid(state, refs)
        render_stats(state, refs)
        render_preview(item, state, refs)
        print(f"✅ {lbl} regenerated!")
    except Exception as e:
        print(f"❌ {lbl}: {e}")
    finally:
        state["generating"] = False
        render_progress(state, refs)


async def do_generate_images(state, refs):
    """Generate all pending images (thumbnails + key_frames)."""
    if not state["tasks"] or state["generating"]:
        return
    tasks = state["tasks"]
    project_dir = OUTPUT_DIR / tasks["project_id"]
    project_dir.mkdir(parents=True, exist_ok=True)
    items = tasks["thumbnails"] + tasks["key_frames"]
    state.update(generating=True, progress=0, progress_total=len(items))
    try:
        for item in items:
            if item.get("path"):
                state["progress"] += 1
                continue
            _raw_lbl = item.get("variant") or item.get("purpose") or f"#{item.get('index', '?')}"
            lbl = _raw_lbl.encode("ascii", "ignore").decode("ascii") if isinstance(_raw_lbl, str) else str(_raw_lbl)
            state["progress_label"] = lbl or f"#{item.get('index', '?')}"
            render_progress(state, refs)
            try:
                if "variant" in item:
                    fn = f"thumb_{item['variant']}.png"
                else:
                    _safe_purpose = (item.get('purpose') or 'x').encode('ascii', 'ignore').decode('ascii') or 'x'
                    fn = f"frame_{item['index']}_{_safe_purpose}.png"
                _fmt = item.get("format", DEFAULT_FORMAT)
                _rids = item.get("ref_ids", [])
                _prompt = item["prompt"]
                if _rids:
                    path = await asyncio.get_event_loop().run_in_executor(
                        None, lambda p=_prompt, r=list(_rids), fm=_fmt, f=fn:
                            generate_with_refs(p, ref_ids=r, format=fm, filename=f))
                else:
                    path = await asyncio.get_event_loop().run_in_executor(
                        None, lambda p=_prompt, fm=_fmt, f=fn:
                            generate_image(p, format=fm, filename=f))
                final = project_dir / fn
                Path(path).replace(final)
                item["path"] = str(final)
                save_manifest(state)
                render_grid(state, refs)
                if state.get("active_item") is item:
                    render_preview(item, state, refs)
            except Exception as e:
                ui.notify(f"Error: {e}", type="negative")
                print(f"❌ generate error: {e}")
            state["progress"] += 1
            render_progress(state, refs)
        render_grid(state, refs)
        render_stats(state, refs)
        ui.notify("Images generated!", type="positive")
    finally:
        state["generating"] = False
        render_progress(state, refs)
        render_stats(state, refs)


async def do_generate_all(state, refs):
    """Generate all pending items (images + videos)."""
    if not state["tasks"] or state["generating"]:
        return
    tasks = state["tasks"]
    project_dir = OUTPUT_DIR / tasks["project_id"]
    project_dir.mkdir(parents=True, exist_ok=True)
    all_items = ([("img", t) for t in tasks["thumbnails"]]
                 + [("img", f) for f in tasks["key_frames"]]
                 + [("vid", v) for v in tasks["videos"]])
    state.update(generating=True, progress=0, progress_total=len(all_items))
    try:
        for kind, item in all_items:
            if item.get("path"):
                state["progress"] += 1
                continue
            _raw_lbl = item.get("variant") or item.get("purpose") or f"#{item.get('index', '?')}"
            lbl = _raw_lbl.encode("ascii", "ignore").decode("ascii") if isinstance(_raw_lbl, str) else str(_raw_lbl)
            state["progress_label"] = lbl or f"#{item.get('index', '?')}"
            render_progress(state, refs)
            try:
                if kind == "img":
                    if "variant" in item:
                        fn = f"thumb_{item['variant']}.png"
                    else:
                        _safe_purpose = (item.get('purpose') or 'x').encode('ascii', 'ignore').decode('ascii') or 'x'
                        fn = f"frame_{item['index']}_{_safe_purpose}.png"
                    _fmt = item.get("format", DEFAULT_FORMAT)
                    _rids = item.get("ref_ids", [])
                    if _rids:
                        path = await asyncio.get_event_loop().run_in_executor(
                            None, lambda p=item["prompt"], r=list(_rids), fm=_fmt, f=fn:
                                generate_with_refs(p, ref_ids=r, format=fm, filename=f))
                    else:
                        path = await asyncio.get_event_loop().run_in_executor(
                            None, lambda p=item["prompt"], fm=_fmt, f=fn:
                                generate_image(p, format=fm, filename=f))
                else:
                    fn = f"clip_{item['index']}_{item['segment'].replace('-', '_')}.mp4"
                    ui.notify(f"Video {fn} — manual mode", type="info")
                    continue
                final = project_dir / fn
                Path(path).replace(final)
                item["path"] = str(final)
                save_manifest(state)
            except Exception as e:
                ui.notify(f"{lbl}: {e}", type="negative")
            state["progress"] += 1
            render_progress(state, refs)
            render_grid(state, refs)
        ui.notify("All generated!", type="positive")
    finally:
        state["generating"] = False
        render_progress(state, refs)
        render_stats(state, refs)
