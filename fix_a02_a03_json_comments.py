"""
fix_a02_a03_json_comments.py
Убирает // комментарии из JSON блоков в A02 и A03.
Кладёт в корень репо, запускать оттуда.
"""
from pathlib import Path

BASE = Path(__file__).parent

fixes = {
    "studio/modules/video_long/A02/forge/prompt.md": [
        # chain_data блок — убрать комментарии, оставить правильный ключ
        (
            '  "chain_data": {\n'
            '    "master_brief": "{{inherit}}",\n'
            '    "history_dna": "{{inherit}}",\n'
            '    "adam_bible": "{{inherit}}",\n'
            '    "zack_season_structure": "{{my_output}}"  // BIBLE\n'
            '    // "zack_season_structure": "{{my_output}}"  // EPISODE  // BIBLE режим: ключ "zack_season_structure"\n'
            '    // EPISODE режим: ключ "zack_hook"\n'
            '  },',
            '  "chain_data": {\n'
            '    "master_brief": "{{inherit}}",\n'
            '    "history_dna": "{{inherit}}",\n'
            '    "adam_bible": "{{inherit}}",\n'
            '    "zack_season_structure": "{{my_output}}"\n'
            '  },'
        ),
    ],
    "studio/modules/video_long/A03/forge/prompt.md": [
        # убрать scene_name из JSON примера сцены
        (
            '        "scene_id": "scene_01",\n'
            '        "scene_name": "название",\n'
            '        "duration_sec": 5,\n',
            '        "scene_id": "scene_01",\n'
            '        "duration_sec": 5,\n'
        ),
        # chain_data блок — убрать комментарии
        (
            '  "chain_data": {\n'
            '    "master_brief": "{{inherit}}",\n'
            '    "history_dna": "{{inherit}}",\n'
            '    "adam_bible": "{{inherit}}",  // или adam_episode в EPISODE\n'
            '    "zack_season_structure": "{{inherit}}",  // или zack_hook в EPISODE\n'
            '    "leo_season_breakdown": "{{my_output}}"  // BIBLE режим: ключ "leo_season_breakdown"\n'
            '    // EPISODE режим: ключ "leo_script"\n'
            '  },',
            '  "chain_data": {\n'
            '    "master_brief": "{{inherit}}",\n'
            '    "history_dna": "{{inherit}}",\n'
            '    "adam_bible": "{{inherit}}",\n'
            '    "zack_season_structure": "{{inherit}}",\n'
            '    "leo_season_breakdown": "{{my_output}}"\n'
            '  },'
        ),
    ],
}

for rel_path, replacements in fixes.items():
    path = BASE / rel_path
    if not path.exists():
        print(f"❌ Не найден: {path}")
        continue
    text = path.read_text(encoding="utf-8")
    changed = False
    for old, new in replacements:
        if old in text:
            text = text.replace(old, new)
            changed = True
            print(f"✅ Пофиксил в {rel_path}")
        else:
            print(f"⚠️  Паттерн не найден в {rel_path} — возможно уже чисто")
    if changed:
        path.write_text(text, encoding="utf-8")

print("\nГотово. Коммить через VSCode.")
