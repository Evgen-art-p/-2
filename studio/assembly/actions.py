"""
Assembly — actions (export, folder, zip, picker)
"""
import os
import sys
import subprocess
import shutil
import zipfile
from pathlib import Path
from nicegui import ui

from studio.assembly.constants import (
    RENDER_DIR, OUTPUT_DIR,
    parse_final_md, extract_tasks, find_final_mds,
)
from studio.assembly.helpers import restore_paths
from studio.assembly.renderers import render_grid, render_stats, render_right_panels, render_social_post


def load_md(path, state, refs):
    """Load and parse a final .md file into state."""
    try:
        data = parse_final_md(path)
        tasks = extract_tasks(data)

        # Проверяем что есть хоть какие-то задачи для сборки
        has_content = (
            tasks.get("key_frames")
            or tasks.get("thumbnails")
            or tasks.get("characters")
            or tasks.get("badges")
            or tasks.get("sfx")
            or tasks.get("music")
        )
        if not has_content:
            ui.notify(
                "⚠️ Файл загружен, но промптов нет — chain_data пустой. "
                "Возможно A11 сломала chain. Перезапусти пайплайн.",
                type="warning", timeout=8000,
            )

        state["tasks"] = tasks
        state["selected"] = set()
        state["active_card"] = None
        state["active_item"] = None
        state["_slide_index"] = 0
        restore_paths(state)
        if tasks.get("social_post"):
            render_social_post(state, refs)
            render_stats(state, refs)
        else:
            render_grid(state, refs)
            render_stats(state, refs)
            render_right_panels(state, refs)
        ui.notify(f"Project: {tasks['project_id']}", type="positive")
    except Exception as e:
        ui.notify(f"Error: {e}", type="negative")
        import traceback
        traceback.print_exc()



def do_copy_post(state):
    """Копирует готовый пост в буфер обмена."""
    post = state.get("tasks", {}).get("social_post")
    if not post:
        ui.notify("Нет поста для копирования", type="warning")
        return
    parts = []
    if post.get("hook"):
        parts.append(post["hook"])
    if post.get("body"):
        parts.append(post["body"])
    if post.get("cta"):
        parts.append(post["cta"])
    if post.get("hashtags"):
        parts.append(" ".join(post["hashtags"]))
    if post.get("first_comment"):
        parts.append(f"\n💬 {post['first_comment']}")
    text = "\n\n".join(parts)
    import json as _json
    ui.run_javascript(f"navigator.clipboard.writeText({_json.dumps(text)})")
    ui.notify("📋 Пост скопирован!", type="positive")


def do_export(item, state):
    """Export a single item to RENDER folder."""
    if not item.get("path") or not Path(item["path"]).exists():
        ui.notify("Nothing to export — generate first!", type="warning")
        return
    tasks = state["tasks"]
    project_name = tasks.get("project_id", "unknown")
    export_dir = RENDER_DIR / project_name
    export_dir.mkdir(parents=True, exist_ok=True)
    src = Path(item["path"])
    if "variant" in item:
        nice_name = f"Cover_{item['variant'].upper()}{src.suffix}"
    elif "purpose" in item:
        idx = item.get("index", 0)
        scene = item.get("scene", 1)
        # scene может быть строкой (web_story) или числом (video)
        if isinstance(scene, int):
            scene_str = f"Sc{scene:02d}"
        else:
            scene_str = str(scene)[:30]
        if isinstance(idx, int):
            idx_str = f"Shot{idx:02d}"
        else:
            idx_str = f"Shot{idx}"
        nice_name = f"{scene_str}_{idx_str}{src.suffix}"
    else:
        idx = item.get("index", 0)
        nice_name = f"Clip_{idx:02d}{src.suffix}"
    dest = export_dir / nice_name
    shutil.copy2(str(src), str(dest))
    ui.notify(f"✅ Exported → RENDER/{project_name}/{nice_name}", type="positive")
    print(f"📦 EXPORT: {src} → {dest}")


def do_export_all(state, refs):
    """Export all generated items to RENDER folder."""
    if not state["tasks"]:
        ui.notify("Load project first!", type="warning")
        return
    tasks = state["tasks"]
    project_name = tasks.get("project_id", "unknown")
    export_dir = RENDER_DIR / project_name
    export_dir.mkdir(parents=True, exist_ok=True)
    count = 0
    for item in tasks["thumbnails"]:
        if item.get("path") and Path(item["path"]).exists():
            src = Path(item["path"])
            nice = f"Cover_{item['variant'].upper()}{src.suffix}"
            shutil.copy2(str(src), str(export_dir / nice))
            count += 1
    for item in tasks["key_frames"]:
        if item.get("path") and Path(item["path"]).exists():
            src = Path(item["path"])
            scene = item.get("scene", 1)
            idx = item.get("index", 0)
            scene_str = f"Sc{scene:02d}" if isinstance(scene, int) else str(scene)[:30]
            idx_str = f"Shot{idx:02d}" if isinstance(idx, int) else f"Shot{idx}"
            nice = f"{scene_str}_{idx_str}{src.suffix}"
            shutil.copy2(str(src), str(export_dir / nice))
            count += 1
    for item in tasks["videos"]:
        if item.get("path") and Path(item["path"]).exists():
            src = Path(item["path"])
            idx = item.get("index", 0)
            nice = f"Clip_{idx:02d}{src.suffix}"
            shutil.copy2(str(src), str(export_dir / nice))
            count += 1
    if count:
        ui.notify(f"✅ Exported {count} files → RENDER/{project_name}/", type="positive")
        render_stats(state, refs)
    else:
        ui.notify("Nothing to export — generate first!", type="warning")


def do_open_folder(state):
    """Open project RENDER folder in OS file manager (cross-platform)."""
    if not state["tasks"]:
        ui.notify("Load project first!", type="warning")
        return
    tasks = state["tasks"]
    project_name = tasks.get("project_id", "unknown")
    export_dir = RENDER_DIR / project_name
    export_dir.mkdir(parents=True, exist_ok=True)
    folder = str(export_dir.resolve())
    # Cross-platform open
    if sys.platform == "win32":
        os.startfile(folder)
    elif sys.platform == "darwin":
        subprocess.Popen(["open", folder])
    else:
        subprocess.Popen(["xdg-open", folder])


def do_download_zip(state):
    """Create and download ZIP of exported files."""
    if not state["tasks"]:
        ui.notify("Load project first!", type="warning")
        return
    tasks = state["tasks"]
    project_name = tasks.get("project_id", "unknown")
    export_dir = RENDER_DIR / project_name
    if not export_dir.exists() or not any(export_dir.iterdir()):
        ui.notify("Export files first!", type="warning")
        return
    zip_path = RENDER_DIR / f"{project_name}.zip"
    with zipfile.ZipFile(str(zip_path), "w", zipfile.ZIP_DEFLATED) as zf:
        for f in export_dir.iterdir():
            if f.is_file() and f.suffix != ".zip":
                zf.write(str(f), f"{project_name}/{f.name}")
    ui.download(str(zip_path.resolve()))
    ui.notify(f"📦 Downloading {project_name}.zip", type="positive")


def do_extract_logic(state):
    """Извлекает логику из файла Артура → logic_map.json + PDF-отчёт."""
    if not state["tasks"]:
        ui.notify("Сначала загрузи проект!", type="warning")
        return

    project_id = state["tasks"].get("project_id", "unknown")

    # Ищем файл Артура в runs/ (.json и .md)
    import glob
    candidates = (
        glob.glob(f"runs/**/*{project_id}*.json", recursive=True) +
        glob.glob(f"runs/**/*{project_id}*.md", recursive=True) +
        glob.glob("runs/**/*A12*.json", recursive=True) +
        glob.glob("runs/**/*A12*.md", recursive=True) +
        glob.glob("runs/**/*arthur*.json", recursive=True) +
        glob.glob("runs/**/*Артур*.md", recursive=True) +
        glob.glob("runs/**/*артур*.md", recursive=True)
    )
    if not candidates:
        ui.notify("Файл Артура не найден в runs/ — убедись что .md или .json там есть", type="warning")
        return

    arthur_path = candidates[0]

    try:
        from studio.extract_logic import extract_logic
        output_dir = OUTPUT_DIR / project_id
        output_dir.mkdir(parents=True, exist_ok=True)

        # 1. Генерируем logic_map.json
        json_path = output_dir / "logic_map.json"
        logic_map = extract_logic(arthur_path, str(json_path))

        # 2. Извлекаем предупреждения QA из данных
        warnings = []
        try:
            from studio.extract_logic import _parse_file
            data = _parse_file(Path(arthur_path))
            for w in data.get("my_output", {}).get("warnings", []):
                if isinstance(w, dict):
                    warnings.append(w.get("description", str(w)))
                else:
                    warnings.append(str(w))
        except Exception:
            pass

        # 3. Генерируем PDF-отчёт
        pdf_path = output_dir / f"{project_id}_report.pdf"
        try:
            from studio.generate_report_pdf import generate_project_pdf
            generate_project_pdf(
                logic_map,
                str(pdf_path),
                project_title=f"Проект: {project_id}",
                warnings=warnings or None,
            )
            ui.notify(f"✅ PDF-отчёт готов → {pdf_path.name}", type="positive")
            print(f"📄 PDF: {pdf_path}")
        except ImportError:
            ui.notify("⚠️ reportlab не установлен — PDF не создан (pip install reportlab)", type="warning")
        except Exception as pdf_err:
            ui.notify(f"⚠️ PDF ошибка: {pdf_err}", type="warning")
            print(f"⚠️ PDF: {pdf_err}")

        ui.notify(f"🧠 Логика извлечена: {json_path.name}", type="positive")
        print(f"🧠 LOGIC: {arthur_path} → {json_path}")

    except Exception as e:
        ui.notify(f"Ошибка: {e}", type="negative")
        print(f"❌ extract_logic: {e}")


def show_picker(state, refs):
    """Show dialog to pick a final .md file."""
    files = find_final_mds(force=True)
    if not files:
        ui.notify("No final .md in runs/", type="warning")
        return
    with ui.dialog() as dlg, ui.card().style(
        "background:#0d1117; border:1px solid rgba(255,255,255,0.1);"
        "min-width:480px; max-width:600px; border-radius:20px;"):
        ui.label("Select project").style("color:white; font-weight:900; font-size:15px; margin-bottom:12px;")
        for f in files[:20]:
            with ui.element("div").style(
                "background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.08);"
                "border-radius:12px; padding:12px; margin-bottom:8px; cursor:pointer;"
            ).on("click", lambda e, fp=f["path"]: (load_md(fp, state, refs), dlg.close())):
                ui.label(f["project_id"]).style("color:#00ccff; font-weight:700; font-size:12px;")
                ui.label(f'{f["run"]} / {f["name"]}').style(
                    "color:rgba(255,255,255,0.35); font-size:10px; font-family:'JetBrains Mono', monospace;")
    dlg.open()
