# debug_frames.py
from studio.fal_client import load_catalog, parse_final_md, extract_tasks

load_catalog(client_slug="сайт_окна")

import glob
from pathlib import Path
mds = sorted(glob.glob('runs/**/A12*.md', recursive=True), key=lambda f: Path(f).stat().st_mtime, reverse=True)
data = parse_final_md(mds[0])
tasks = extract_tasks(data)

print(f"key_frames: {len(tasks['key_frames'])}")
for i, kf in enumerate(tasks["key_frames"][:3]):
    print(f"\n  Frame {i+1}: {kf.get('scene','?')}")
    print(f"    ref_ids: {kf.get('ref_ids', [])}")
    print(f"    preview_paths: {kf.get('preview_paths', [])}")