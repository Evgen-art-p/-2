# debug_deep.py
import re, json, glob
from pathlib import Path
from studio.fal_client import parse_final_md

mds = sorted(glob.glob('runs/**/A12*.md', recursive=True), key=lambda f: Path(f).stat().st_mtime, reverse=True)
data = parse_final_md(mds[0])
print(f"Файл: {mds[0]}")

dlv = data.get("my_output", {}).get("deliverables", {})
scenes = dlv.get("nova_scene_prompts", [])
chain = (data.get("chain_data") or {})
nova = chain.get("nova_prompts")

print(f"chain_data.nova_prompts type: {type(nova)}")
print(f"deliverables.nova_scene_prompts: {len(scenes) if isinstance(scenes,list) else type(scenes)}")

if isinstance(scenes, list) and scenes:
    sp = scenes[0]
    txt = json.dumps(sp, ensure_ascii=False)
    locs = re.findall(r'loc_[\w]+', txt)
    print(f"\nСцена 1 JSON (первые 300 символов):")
    print(txt[:300])
    print(f"\nloc_ найдено: {locs}")
else:
    print("nova_scene_prompts ПУСТО!")
    # Может парсер берёт из chain?
    if isinstance(nova, dict):
        sp2 = nova.get("scene_prompts", [])
        print(f"chain scene_prompts: {len(sp2)}")