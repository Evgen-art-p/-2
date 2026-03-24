"""
Assembly — helpers (URL converters, manifest persistence)
"""
import json
from pathlib import Path

from studio.assembly.constants import OUTPUT_DIR, ASSETS_DIR


def to_url(filepath):
    """Convert absolute path to /output/... URL for browser."""
    try:
        rel = Path(filepath).relative_to(OUTPUT_DIR)
        return '/output/' + str(rel).replace('\\', '/')
    except ValueError:
        return str(filepath)


def asset_to_url(filepath):
    """Convert asset path to /assets/... URL for browser.
    Поддерживает файлы из разных папок:
      - assets/ (корневая) → /assets/...
      - runs/.../assets/ → /run-assets/...
      - Абсолютный путь → /run-assets/filename
    """
    fp = Path(filepath)

    # 1. Корневая assets/
    try:
        rel = fp.relative_to(ASSETS_DIR)
        return '/assets/' + str(rel).replace('\\', '/')
    except ValueError:
        pass

    # 2. Любая папка assets внутри runs/
    parts = fp.parts
    for i, part in enumerate(parts):
        if part == "assets" and i > 0:
            rel = "/".join(parts[i:])
            # Регистрируем static route для этой конкретной assets папки
            base = Path(*parts[:i+1])
            route = '/run-assets'
            try:
                from nicegui import app as _app
                _app.add_static_files(route, str(base))
            except Exception:
                pass
            return route + '/' + "/".join(parts[i+1:])

    # 3. Фоллбэк: файл существует — отдаём через /run-assets/
    if fp.exists():
        try:
            from nicegui import app as _app
            _app.add_static_files('/run-assets', str(fp.parent))
        except Exception:
            pass
        return f'/run-assets/{fp.name}'

    return str(filepath)


def save_manifest(state):
    """Save current tasks to manifest.json so nothing is lost."""
    if not state["tasks"]:
        return
    tasks = state["tasks"]
    project_dir = OUTPUT_DIR / tasks["project_id"]
    project_dir.mkdir(parents=True, exist_ok=True)
    manifest = project_dir / "manifest.json"
    manifest.write_text(json.dumps(tasks, ensure_ascii=False, indent=2), encoding="utf-8")


def restore_paths(state):
    """After loading .md, check if images already exist on disk."""
    if not state["tasks"]:
        return
    tasks = state["tasks"]
    project_dir = OUTPUT_DIR / tasks["project_id"]
    if not project_dir.exists():
        return
    # Try loading manifest first
    manifest = project_dir / "manifest.json"
    if manifest.exists():
        try:
            saved = json.loads(manifest.read_text(encoding="utf-8"))
            _restore_list(tasks["thumbnails"], saved.get("thumbnails", []), "variant")
            _restore_list(tasks["key_frames"], saved.get("key_frames", []), "index")
            _restore_list(tasks["videos"], saved.get("videos", []), "index")
            return
        except Exception as e:
            print(f"⚠️ Manifest read error: {e}")
    # Fallback: scan files on disk
    for item in tasks["thumbnails"]:
        fn = f"thumb_{item['variant']}.png"
        fp = project_dir / fn
        if fp.exists():
            item["path"] = str(fp)
    for item in tasks["key_frames"]:
        fn = f"frame_{item['index']}_{item.get('purpose', 'x')}.png"
        fp = project_dir / fn
        if fp.exists():
            item["path"] = str(fp)
    for item in tasks["videos"]:
        fn = f"clip_{item['index']}_{item.get('segment', 'x').replace('-', '_')}.mp4"
        fp = project_dir / fn
        if fp.exists():
            item["path"] = str(fp)


def _restore_list(current, saved, key_field):
    """Match saved items to current by key field and restore paths."""
    saved_map = {}
    for s in saved:
        k = s.get(key_field)
        if k is not None and s.get("path"):
            saved_map[k] = s
    for item in current:
        k = item.get(key_field)
        if k in saved_map:
            saved_path = saved_map[k].get("path")
            if saved_path and Path(saved_path).exists():
                item["path"] = saved_path
            saved_prompt = saved_map[k].get("prompt")
            if saved_prompt:
                item["prompt"] = saved_prompt
            saved_fmt = saved_map[k].get("format")
            if saved_fmt:
                item["format"] = saved_fmt
