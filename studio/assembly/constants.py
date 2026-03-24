"""
Assembly — constants, imports, discovery
"""
import json
import time
import shutil
import os
import sys
import zipfile
import asyncio
import subprocess
from pathlib import Path
from nicegui import ui, app
from studio.config import BASE_DIR

# ============================================================
# CONSTANTS
# ============================================================

RUNS_DIR    = BASE_DIR / "runs"
RENDER_DIR  = BASE_DIR / "output" / "render"
THUMB_SIZE  = "52px"
PLACEHOLDER_ICON = "?"

CATEGORY_EMOJI = {
    "character": "👤",
    "location":  "🏞️",
    "prop":      "📦",
    "unknown":   "❓",
}

COLOR_GREEN  = "#00ff88"
COLOR_BLUE   = "#00ccff"
COLOR_ORANGE = "#ff9500"
COLOR_GLASS  = "rgba(13, 17, 23, 0.60)"

from studio.fal_client import (
    parse_final_md, extract_tasks,
    generate_image, generate_with_refs,
    get_asset_name, get_asset_category,
    lookup_asset_metadata,
    load_catalog,
    OUTPUT_DIR, ASSETS_DIR, IMAGE_FORMATS, DEFAULT_FORMAT,
)

# ============================================================
# MD DISCOVERY
# ============================================================

_md_cache = None


def find_final_mds(force=False):
    """Scan runs/ for final .md files (A05 / final_dna / Финализатор)."""
    global _md_cache
    if _md_cache is not None and not force:
        return _md_cache
    results = []
    if not RUNS_DIR.exists():
        return results
    for run_dir in sorted(RUNS_DIR.iterdir(), reverse=True):
        if not run_dir.is_dir() or run_dir.name.startswith("_"):
            continue
        md_files = sorted(run_dir.glob("*.md"), key=lambda p: p.name, reverse=True)
        for md in md_files:
            try:
                text = md.read_text(encoding="utf-8")
                is_final = (
                    md.name.startswith("A05")
                    or "final_dna" in text
                    or ("Финализатор" in md.name and ('"thumbnails"' in text or '"key_frames"' in text))
                )
                if is_final:
                    results.append({
                        "path": str(md),
                        "name": md.name,
                        "run": run_dir.name,
                        "project_id": md.stem,
                    })
            except Exception:
                pass
    _md_cache = results
    return results


# ============================================================
# INIT: catalog + static routes
# ============================================================

# Каталог загружается при смене клиента в workshop
# Фоллбэк: если ничего не загружено — грузим дефолт
try:
    from studio.fal_client import _asset_catalog
    if not _asset_catalog.get('assets'):
        load_catalog()
except Exception as _e:
    print(f'⚠️ Каталог: {_e}')

app.add_static_files('/output', str(OUTPUT_DIR))
app.add_static_files('/assets', str(ASSETS_DIR))
