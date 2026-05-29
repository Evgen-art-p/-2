"""
patch_vl_a01_a04_v2.py
======================
Патч промтов A01–A04 цеха video_long.
Работает с локальными файлами — никаких токенов.

Положи в корень репо (рядом с main.py) и запускай из VSCode терминала.

Dry-run (только показывает что изменится):
    python patch_vl_a01_a04_v2.py

Применить:
    python patch_vl_a01_a04_v2.py --apply

Один агент:
    python patch_vl_a01_a04_v2.py --apply --agent A03
"""

import sys
import re
import shutil
from pathlib import Path
from datetime import datetime

# ─── Пути к файлам ────────────────────────────────────────────────────────────
# Скрипт лежит в корне репо, промты — в studio/modules/video_long/
BASE = Path(__file__).parent

AGENT_PATHS = {
    "A01": BASE / "studio/modules/video_long/A01/forge/prompt.md",
    "A02": BASE / "studio/modules/video_long/A02/forge/prompt.md",
    "A03": BASE / "studio/modules/video_long/A03/forge/prompt.md",
    "A04": BASE / "studio/modules/video_long/A04/forge/prompt.md",
}

BACKUP_DIR = BASE / "_patch_backups" / f"vl_a01_a04_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

# ─── Diff helper ──────────────────────────────────────────────────────────────
def show_diff(agent, old, new):
    old_lines = old.splitlines()
    new_lines = new.splitlines()
    changes = []
    max_len = max(len(old_lines), len(new_lines))
    for i in range(max_len):
        a = old_lines[i] if i < len(old_lines) else None
        b = new_lines[i] if i < len(new_lines) else None
        if a != b:
            if a is not None:
                changes.append(f"  - {a.rstrip()}")
            if b is not None:
                changes.append(f"  + {b.rstrip()}")
    if changes:
        print(f"\n{'─'*55}")
        print(f"  {agent} — изменения ({len(changes)//2} строк):")
        print(f"{'─'*55}")
        for c in changes[:100]:
            print(c)
        if len(changes) > 100:
            print(f"  ... ещё {len(changes)-100} строк")
    else:
        print(f"  {agent}: без изменений")

# ─── ПАТЧ A01 — Адам ─────────────────────────────────────────────────────────
def patch_a01(text: str) -> str:

    # 1. agent key
    text = re.sub(r'"agent":\s*"01_adam_arc"', '"agent": "A01"', text)

    # 2. next_step
    text = re.sub(r'"next_step":\s*"02_zack_zoom"', '"next_step": "A02"', text)

    # 3. chain_data: project_memory → history_dna
    text = re.sub(
        r'("chain_data"[\s\S]{0,200}?)"project_memory":\s*"\{\{inherit\}\}"',
        r'\1"history_dna": "{{inherit}}"',
        text
    )

    # 4. chain_data: adam_analysis → adam_bible
    text = re.sub(
        r'"adam_analysis":\s*"\{\{my_output\}\}"',
        '"adam_bible": "{{my_output}}"',
        text
    )

    # 5. INPUT блок: "project_memory": {...}
    text = re.sub(r'"project_memory":\s*\{\.\.\.\}', '"history_dna": {...}', text)

    # 6. CONTEXTUAL MEMORY — убрать старый json пример, заменить ссылкой
    old_ctx_pattern = r'```json\n\{\n  "project_memory": \{[\s\S]*?\}\n\}\n```'
    if re.search(old_ctx_pattern, text):
        text = re.sub(
            old_ctx_pattern,
            '*(структура history_dna — см. LONG_RULES v4.2 раздел 7)*',
            text
        )

    # 7. ANTI-REPEAT CHECK
    text = text.replace(
        "- Проверь `project_memory.previous_videos`\n"
        "- Не повторяй тот же тип героя + конфликта\n"
        "- Предложи разнообразие в арке\n"
        "- Если первый проект — пропусти проверку",
        "- Проверь `history_dna.narrative_memory` — не повторяй сюжеты из истории\n"
        "- Проверь `history_dna.learnings_pack` — учитывай что уже сработало\n"
        "- Не повторяй тот же тип героя + конфликта\n"
        "- Предложи разнообразие в арке\n"
        "- Если `history_dna: null` — пропусти проверку"
    )
    # Короткий вариант если скрипт уже частично сработал
    text = text.replace(
        "- Проверь `project_memory.previous_videos`",
        "- Проверь `history_dna.narrative_memory` и `learnings_pack`\n"
        "- Не повторяй сюжеты из narrative_memory\n"
        "- Учитывай что сработало из learnings_pack"
    )

    # 8. RULES — добавить BIBLE/EPISODE если нет
    if "BIBLE режим" not in text and "adam_bible" not in text.split("# ⚠️ RULES")[-1]:
        bible_rule = (
            "- **Режим:** читай `master_brief.mode` или `state[\"mode\"]`\n"
            "  - BIBLE → пиши ключ `adam_bible` в chain_data\n"
            "  - EPISODE → пиши ключ `adam_episode` в chain_data\n"
        )
        text = text.replace(
            "- Проверь себя через 99_Self_Correction.txt",
            bible_rule + "- Проверь себя через 99_Self_Correction.txt"
        )

    return text


# ─── ПАТЧ A02 — Зак ──────────────────────────────────────────────────────────
def patch_a02(text: str) -> str:

    # 1. agent key
    text = re.sub(r'"agent":\s*"02_zack_zoom"', '"agent": "A02"', text)

    # 2. next_step
    text = re.sub(r'"next_step":\s*"03_leo_logline"', '"next_step": "A03"', text)

    # 3. chain_data: project_memory → history_dna
    text = re.sub(
        r'("chain_data"[\s\S]{0,300}?)"project_memory":\s*"\{\{inherit\}\}"',
        r'\1"history_dna": "{{inherit}}"',
        text
    )

    # 4. chain_data: adam_analysis → adam_bible (inherit)
    text = re.sub(
        r'"adam_analysis":\s*"\{\{inherit\}\}"',
        '"adam_bible": "{{inherit}}"',
        text
    )

    # 5. chain_data: zack_hook my_output → zack_season_structure (BIBLE default)
    text = re.sub(
        r'"zack_hook":\s*"\{\{my_output\}\}"',
        '"zack_season_structure": "{{my_output}}"',
        text
    )

    # 6. INPUT блок
    text = re.sub(r'"project_memory":\s*\{\.\.\.\}', '"history_dna": {...}', text)
    # adam_analysis → adam_bible в INPUT примере
    text = re.sub(
        r'("adam_analysis":\s*\{[\s\S]{0,50}?"hero_analysis")',
        lambda m: m.group(0).replace('"adam_analysis"', '"adam_bible"'),
        text
    )

    # 7. CONTEXTUAL MEMORY: project_memory.engagement_data → history_dna
    text = text.replace(
        "Читаешь `project_memory.engagement_data`",
        "Читаешь `history_dna.engagement_data`"
    )

    # 8. Добавить "Определи режим" в начало TASK если нет
    if "Определи режим" not in text:
        mode_block = (
            "### Определи режим\n"
            "Читай из `master_brief.mode` или `history_dna.mode`:\n"
            "- **BIBLE** → создаёшь структуру сезона (`season_structure`, `arc_breakdown`, `pacing_note`)\n"
            "- **EPISODE** → создаёшь хук и retention-стратегию (`hook`, `retention_strategy`, `tonal_vector`)\n\n"
        )
        text = text.replace(
            "Твоя задача — найти **угол атаки**",
            mode_block + "Твоя задача — найти **угол атаки**"
        )

    # 9. RULES: BIBLE/EPISODE ключи
    if "zack_season_structure" not in text.split("# ⚠️ RULES")[-1]:
        bible_rule = (
            "- **Режим:** читай `master_brief.mode` или `state[\"mode\"]`\n"
            "  - BIBLE → пиши ключ `zack_season_structure` в chain_data\n"
            "  - EPISODE → пиши ключ `zack_hook` в chain_data\n"
        )
        text = text.replace(
            "- Проверь себя через 99_Self_Correction.txt",
            bible_rule + "- Проверь себя через 99_Self_Correction.txt"
        )

    return text


# ─── ПАТЧ A03 — Лео ──────────────────────────────────────────────────────────
def patch_a03(text: str) -> str:

    # 1. agent key
    text = re.sub(r'"agent":\s*"03_leo_logline"', '"agent": "A03"', text)

    # 2. next_step
    text = re.sub(r'"next_step":\s*"04_katya_cut"', '"next_step": "A04"', text)

    # 3. chain_data: project_memory → history_dna
    text = re.sub(
        r'("chain_data"[\s\S]{0,300}?)"project_memory":\s*"\{\{inherit\}\}"',
        r'\1"history_dna": "{{inherit}}"',
        text
    )

    # 4. chain_data: adam_analysis → adam_bible
    text = re.sub(r'"adam_analysis":\s*"\{\{inherit\}\}"', '"adam_bible": "{{inherit}}"', text)

    # 5. chain_data: leo_script my_output → leo_season_breakdown (BIBLE default)
    text = re.sub(
        r'"leo_script":\s*"\{\{my_output\}\}"',
        '"leo_season_breakdown": "{{my_output}}"',
        text
    )

    # 6. INPUT блок
    text = re.sub(r'"project_memory":\s*\{\.\.\.\}', '"history_dna": {...}', text)
    text = re.sub(
        r'("adam_analysis":\s*\{[\s\S]{0,50}?"hero_analysis")',
        lambda m: m.group(0).replace('"adam_analysis"', '"adam_bible"'),
        text
    )

    # 7. Поля scenes[] — заменяем структуру одной сцены в JSON примере
    old_scene = (
        '        "scene_id": "scene_01",\n'
        '        "scene_name": "название",\n'
        '        "duration_sec": 5,\n'
        '        "visual": "описание кадра",\n'
        '        "audio": "VO / диалог / музыка / SFX",\n'
        '        "text_on_screen": "текст или null",\n'
        '        "emotion": "эмоция",\n'
        '        "purpose": "hook / build / climax / resolve / CTA"'
    )
    new_scene = (
        '        "scene_id": "scene_01",\n'
        '        "description": "что происходит в сцене",\n'
        '        "dialogue": "реплики или null",\n'
        '        "visual_note": "описание кадра для Лукаса и Евы",\n'
        '        "audio_note": "VO / музыка / SFX для Сэма",\n'
        '        "duration_sec": 5,\n'
        '        "emotional_beat": "эмоция сцены"'
    )
    if old_scene in text:
        text = text.replace(old_scene, new_scene)

    # 8. Таблица полей сцен в TASK (Шаг 3)
    field_fixes = [
        ("| visual | Что на экране (описание кадра) |",
         "| visual_note | Описание кадра для Лукаса и Евы |"),
        ("| audio | Что звучит (VO / диалог / музыка / SFX) |",
         "| audio_note | Что звучит (VO / музыка / SFX) для Сэма |"),
        ("| emotion | Какую эмоцию вызывает |",
         "| emotional_beat | Эмоция сцены |"),
        ("| scene_name | Короткое название |", ""),
        ("| text_on_screen | Текст на экране (если есть) |", ""),
    ]
    for old, new in field_fixes:
        text = text.replace(old, new)

    # Добавить description и dialogue в таблицу если нет
    if "| description |" not in text and "| scene_id |" in text:
        text = text.replace(
            "| scene_id | scene_01, scene_02... |",
            "| scene_id | scene_01, scene_02... |\n"
            "| description | Что происходит в сцене |\n"
            "| dialogue | Реплики если есть, иначе null |"
        )

    # 9. Добавить "Определи режим" в TASK
    if "Определи режим" not in text:
        mode_block = (
            "### Определи режим\n"
            "Читай из `master_brief.mode` или `history_dna.mode`:\n"
            "- **BIBLE** → пишешь план сезона → `leo_season_breakdown` (episode, title, logline, key_scene)\n"
            "- **EPISODE** → пишешь полный сценарий серии → `leo_script` (script.scenes[])\n\n"
        )
        text = text.replace(
            "Твоя задача — написать **полный сценарий**",
            mode_block + "Твоя задача — написать **полный сценарий**"
        )

    # 10. RULES: BIBLE/EPISODE ключи
    if "leo_season_breakdown" not in text.split("# ⚠️ RULES")[-1]:
        bible_rule = (
            "- **Режим:** читай `master_brief.mode` или `state[\"mode\"]`\n"
            "  - BIBLE → пиши ключ `leo_season_breakdown` в chain_data (план серий)\n"
            "  - EPISODE → пиши ключ `leo_script` в chain_data (сценарий серии)\n"
        )
        text = text.replace(
            "- Проверь себя через 99_Self_Correction.txt",
            bible_rule + "- Проверь себя через 99_Self_Correction.txt"
        )

    return text


# ─── ПАТЧ A04 — Катя ─────────────────────────────────────────────────────────
def patch_a04(text: str) -> str:

    # 1. agent key
    text = re.sub(r'"agent":\s*"04_katya_cut"', '"agent": "A04"', text)

    # 2. next_step
    text = re.sub(r'"next_step":\s*"05_lucas_lens"', '"next_step": "A05"', text)

    # 3. chain_data — полная замена блока
    old_chain = (
        '  "chain_data": {\n'
        '    "master_brief": "{{inherit}}",\n'
        '    "project_memory": "{{inherit}}",\n'
        '    "adam_analysis": "{{inherit}}",\n'
        '    "zack_hook": "{{inherit}}",\n'
        '    "leo_script": "{{inherit}}",\n'
        '    "katya_review": "{{my_output}}"\n'
        '  }'
    )
    new_chain = (
        '  "chain_data": {\n'
        '    "master_brief": "{{inherit}}",\n'
        '    "history_dna": "{{inherit}}",\n'
        '    "adam_bible": "{{inherit}}",\n'
        '    "zack_season_structure": "{{inherit}}",\n'
        '    "leo_season_breakdown": "{{inherit}}",\n'
        '    "katya_review": "{{my_output}}"\n'
        '  },\n'
        '  "katya_verdict": "APPROVED | APPROVED_WITH_EDITS | REJECTED"'
    )
    if old_chain in text:
        text = text.replace(old_chain, new_chain)
    else:
        # Fallback — точечные замены
        text = re.sub(
            r'("chain_data"[\s\S]{0,300}?)"project_memory":\s*"\{\{inherit\}\}"',
            r'\1"history_dna": "{{inherit}}"',
            text
        )
        text = re.sub(r'"adam_analysis":\s*"\{\{inherit\}\}"', '"adam_bible": "{{inherit}}"', text)
        # Добавить zack_season_structure и leo_season_breakdown если нет
        if '"zack_season_structure"' not in text:
            text = text.replace(
                '"adam_bible": "{{inherit}}",\n    "zack_hook"',
                '"adam_bible": "{{inherit}}",\n'
                '    "zack_season_structure": "{{inherit}}",\n'
                '    "leo_season_breakdown": "{{inherit}}",\n'
                '    "zack_hook"'
            )
        # katya_verdict отдельным ключом
        if '"katya_verdict"' not in text:
            text = text.replace(
                '"katya_review": "{{my_output}}"\n  }',
                '"katya_review": "{{my_output}}"\n  },\n'
                '  "katya_verdict": "APPROVED | APPROVED_WITH_EDITS | REJECTED"'
            )

    # 4. INPUT блок
    text = re.sub(r'"project_memory":\s*\{\.\.\.\}', '"history_dna": {...}', text)
    text = re.sub(
        r'("adam_analysis":\s*\{[\s\S]{0,50}?"hero_analysis")',
        lambda m: m.group(0).replace('"adam_analysis"', '"adam_bible"'),
        text
    )

    # 5. CONTEXTUAL MEMORY
    text = text.replace(
        "Читаешь `project_memory.quality_issues`",
        "Читаешь `history_dna.quality_issues`"
    )

    # 6. RULES: ХАРД-СТОП + Виктор + BIBLE/EPISODE
    if "ХАРД-СТОП" not in text:
        hardsop = (
            "- **ХАРД-СТОП:** `katya_verdict` = REJECTED → PROD не запускается\n"
            "  - Пайплайн уходит к Виктору (`victor_critique`) на разбор\n"
            "  - Виктор возвращает с правками или снимает проект\n"
            "- **Режим:** читай `master_brief.mode` или `state[\"mode\"]`\n"
            "  - BIBLE → проверяешь план сезона (`leo_season_breakdown`)\n"
            "  - EPISODE → проверяешь сценарий серии (`leo_script`)\n"
        )
        text = text.replace(
            "- REJECTED только если: нет конфликта / хронометраж ±30% / запрещённый контент",
            "- REJECTED только если: нет конфликта / хронометраж ±30% / запрещённый контент\n" + hardsop
        )

    return text


# ─── Main ─────────────────────────────────────────────────────────────────────
PATCH_FUNCS = {
    "A01": patch_a01,
    "A02": patch_a02,
    "A03": patch_a03,
    "A04": patch_a04,
}

def main():
    apply  = "--apply" in sys.argv
    only   = None
    args   = sys.argv[1:]
    for i, a in enumerate(args):
        if a == "--agent" and i + 1 < len(args):
            only = args[i + 1].upper()
        elif a.startswith("--agent="):
            only = a.split("=", 1)[1].upper()

    targets = [only] if only else list(AGENT_PATHS.keys())

    print(f"\n🔧 patch_vl_a01_a04_v2.py  |  Sprint 26")
    print(f"   Режим : {'APPLY — пишем файлы' if apply else 'DRY-RUN — только diff'}")
    print(f"   Агенты: {', '.join(targets)}")

    # Проверяем что файлы существуют
    for agent in targets:
        p = AGENT_PATHS[agent]
        if not p.exists():
            print(f"\n❌ Файл не найден: {p}")
            print(f"   Убедись что скрипт лежит в корне репо (рядом с main.py)")
            sys.exit(1)

    if apply:
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        print(f"   Бэкап: {BACKUP_DIR}")

    errors = []
    changed = []

    for agent in targets:
        path = AGENT_PATHS[agent]
        patch_fn = PATCH_FUNCS[agent]

        print(f"\n📄 {agent}: {path.relative_to(BASE)}")

        original = path.read_text(encoding="utf-8")
        patched  = patch_fn(original)

        if patched == original:
            print(f"   ✅ Без изменений")
            continue

        show_diff(agent, original, patched)
        changed.append(agent)

        if apply:
            try:
                # Бэкап
                shutil.copy2(path, BACKUP_DIR / f"{agent}_prompt.md.bak")
                # Записываем
                path.write_text(patched, encoding="utf-8")
                print(f"   ✅ Записано")
            except Exception as e:
                errors.append((agent, str(e)))
                print(f"   ❌ Ошибка записи: {e}")

    print(f"\n{'='*55}")
    if not changed:
        print("✅ Все файлы уже чистые — изменений нет")
    elif apply:
        if errors:
            print(f"⚠️  Применено с ошибками. Упали: {[a for a,_ in errors]}")
            for a, e in errors:
                print(f"   {a}: {e}")
        else:
            print(f"✅ Применено: {', '.join(changed)}")
            print(f"   Бэкапы: {BACKUP_DIR}")
            print(f"\n   Теперь в VSCode: Stage All → Commit → Push 🚀")
    else:
        print(f"   Изменятся: {', '.join(changed)}")
        print(f"   Запусти с --apply чтобы применить")
    print(f"{'='*55}\n")

if __name__ == "__main__":
    main()
