#!/usr/bin/env python3
"""
fix_prompts_vl_a01_a04.py
══════════════════════════
Патч промтов video_long A01–A04.
Запускать на КОПИИ — смотреть diff — потом на боевых.

Что правит:
  1. agent: "0X_имя"  →  "AXX"
  2. next_step: "0X_имя"  →  "AXX"
  3. project_memory  →  history_dna (в INPUT, chain_data, CONTEXTUAL MEMORY)
  4. Неверные ключи my_output (adam_analysis → режимные ключи)
  5. Добавляет BIBLE/EPISODE разделение в INPUT и chain_data
  6. A03: поля scenes[] приводит к контракту
  7. A04: добавляет katya_verdict, упоминание ХАРД-СТОПа

Что НЕ трогает:
  - IDENTITY, характер, коронные фразы
  - KNOWLEDGE BASE
  - TASK логику
  - home_prompt.md
  - Всё что не узнаётся на 100%

Безопасность:
  - Делает .bak копию каждого файла перед правкой
  - Добавляет маркер # Auto-patched в начало
  - Печатает diff построчно
  - dry_run=True по умолчанию — без --apply не пишет

Запуск:
  python fix_prompts_vl_a01_a04.py           # dry run, только diff
  python fix_prompts_vl_a01_a04.py --apply   # реальная запись
"""

import sys
import re
import shutil
from pathlib import Path
from datetime import date

DRY_RUN = "--apply" not in sys.argv
PATCH_MARKER = f"<!-- Auto-patched by fix_prompts_vl_a01_a04.py on {date.today()} -->"
MODULES = Path("studio/modules/video_long")

# ══════════════════════════════════════════════════════════
# ЗАМЕНЫ — простые строковые паттерны (100% безопасные)
# ══════════════════════════════════════════════════════════

# Применяются ко всем 4 агентам
COMMON_REPLACEMENTS = [
    # agent поле
    ('"agent": "01_adam_arc"',   '"agent": "A01"'),
    ('"agent": "02_zack_zoom"',  '"agent": "A02"'),
    ('"agent": "03_leo_logline"','"agent": "A03"'),
    ('"agent": "04_katya_cut"',  '"agent": "A04"'),

    # next_step поле
    ('"next_step": "02_zack_zoom"',  '"next_step": "A02"'),
    ('"next_step": "03_leo_logline"','"next_step": "A03"'),
    ('"next_step": "04_katya_cut"',  '"next_step": "A04"'),
    ('"next_step": "05_lucas_lens"', '"next_step": "A05"'),

    # project_memory → history_dna в chain_data
    ('"project_memory": "{{inherit}}"', '"history_dna": "{{inherit}}"'),

    # project_memory в INPUT блоке описания
    (
        '  "project_memory": {...},',
        '  "history_dna": {...},  // история клиента, серий, cultural_trace'
    ),

    # В CONTEXTUAL MEMORY заголовке
    (
        'Читаешь `project_memory.',
        'Читаешь `history_dna.'
    ),
]

# ══════════════════════════════════════════════════════════
# ИНДИВИДУАЛЬНЫЕ ПРАВКИ
# ══════════════════════════════════════════════════════════

# A01 — ключ my_output и chain_data
A01_REPLACEMENTS = [
    # my_output ключ
    ('"adam_analysis": "{{my_output}}"', '"adam_bible": "{{my_output}}"  // BIBLE режим\n    // В EPISODE режиме этот ключ: "adam_episode": "{{my_output}}"'),

    # chain_data пишет
    ('"adam_analysis": "{{my_output}}"',
     '"adam_bible": "{{my_output}}"'),

    # INPUT: что читает Адам — добавляем примечание о режимах
    (
        '  "master_brief": {\n    ...',
        '  // BIBLE: создаёт мир с нуля\n  // EPISODE: читает history_dna, подбирает ассеты\n  "master_brief": {\n    ...'
    ),
]

# A02 — ключ my_output, INPUT от Адама
A02_REPLACEMENTS = [
    # Читает adam_analysis → надо разделить по режимам
    # Добавляем примечание в INPUT
    (
        '"adam_analysis": {',
        '// BIBLE режим: "adam_bible", EPISODE режим: "adam_episode"\n  "adam_bible_or_episode": {'
    ),

    # my_output: zack_hook → добавляем примечание о BIBLE
    (
        '"zack_hook": "{{my_output}}"',
        '"zack_hook": "{{my_output}}"'
        '  // BIBLE режим: ключ "zack_season_structure"\n    // EPISODE режим: ключ "zack_hook"'
    ),

    # chain_data
    (
        '"zack_hook": "{{my_output}}"',
        '"zack_season_structure": "{{my_output}}"  // BIBLE\n    // "zack_hook": "{{my_output}}"  // EPISODE'
    ),
]

# A03 — поля scenes[], ключи
A03_REPLACEMENTS = [
    # Неверные поля сцены → правильные по контракту
    # visual → visual_note
    (
        '        "visual": "описание кадра",',
        '        "visual_note": "описание кадра (для Лукаса и Евы)",',
    ),
    # audio → audio_note
    (
        '        "audio": "VO / диалог / музыка / SFX",',
        '        "audio_note": "VO / диалог / музыка / SFX (для Сэма)",',
    ),
    # text_on_screen убираем (не в контракте)
    (
        '        "text_on_screen": "текст или null",\n',
        '',
    ),
    # emotion → emotional_beat
    (
        '        "emotion": "эмоция",',
        '        "emotional_beat": "эмоция сцены",',
    ),
    # Добавляем недостающее поле description и dialogue
    (
        '        "purpose": "hook / build / climax / resolve / CTA"',
        '        "description": "что происходит в сцене",\n'
        '        "dialogue": "реплики если есть, иначе null",\n'
        '        "purpose": "hook / build / climax / resolve / CTA"'
    ),
    # leo_script ключ — добавляем примечание о BIBLE
    (
        '"leo_script": "{{my_output}}"',
        '"leo_script": "{{my_output}}"'
        '  // BIBLE режим: ключ "leo_season_breakdown"\n    // EPISODE режим: ключ "leo_script"'
    ),
    # adam_analysis → примечание
    (
        '"adam_analysis": "{{inherit}}",',
        '"adam_bible": "{{inherit}}",  // или adam_episode в EPISODE'
    ),
    (
        '"zack_hook": "{{inherit}}",',
        '"zack_season_structure": "{{inherit}}",  // или zack_hook в EPISODE'
    ),
]

# A04 — katya_verdict, ХАРД-СТОП, chain_data
A04_REPLACEMENTS = [
    # Добавляем katya_verdict в my_output (после verdict строки)
    (
        '    "verdict": "APPROVED / APPROVED_WITH_EDITS / REJECTED",',
        '    "verdict": "APPROVED / APPROVED_WITH_EDITS / REJECTED",'
        '\n    "katya_verdict": "APPROVED / APPROVED_WITH_EDITS / REJECTED",'
        '  // отдельный ключ для таможни и Виктора'
    ),
    # adam_analysis → режимные ключи в INPUT
    (
        '"adam_analysis": {',
        '// BIBLE: "adam_bible", EPISODE: "adam_episode"\n  "adam_bible_or_episode": {'
    ),
    # chain_data: leo_script inherit + добавляем katya_verdict
    (
        '    "katya_review": "{{my_output}}"',
        '    "katya_review": "{{my_output}}",\n'
        '    "katya_verdict": "{{my_output.katya_verdict}}"'
    ),
    # Добавляем в RULES упоминание ХАРД-СТОПа
    (
        '- Проверь себя через 99_Self_Correction.txt',
        '- Проверь себя через 99_Self_Correction.txt\n'
        '- После тебя — ХАРД-СТОП. Виктор (резидент) читает весь chain_data и твой вердикт\n'
        '- Шеф принимает финальное решение: продолжать PROD или возвращать на доработку\n'
        '- Твой katya_verdict — сигнал системе. REJECTED = PROD не запускается'
    ),
]

# ══════════════════════════════════════════════════════════
# ДВИЖОК
# ══════════════════════════════════════════════════════════

AGENT_PATCHES = {
    "A01": A01_REPLACEMENTS,
    "A02": A02_REPLACEMENTS,
    "A03": A03_REPLACEMENTS,
    "A04": A04_REPLACEMENTS,
}


def patch_file(path: Path, replacements: list) -> tuple[str, str, int]:
    """Применяет замены. Возвращает (original, patched, count_changes)."""
    original = path.read_text(encoding="utf-8")
    patched = original
    count = 0

    for old, new in replacements:
        if old in patched:
            patched = patched.replace(old, new)
            count += 1

    return original, patched, count


def print_diff(agent: str, original: str, patched: str):
    """Простой построчный diff."""
    orig_lines = original.splitlines()
    new_lines = patched.splitlines()

    changes = 0
    print(f"\n{'='*60}")
    print(f"  DIFF: {agent}/forge/prompt.md")
    print(f"{'='*60}")

    max_lines = max(len(orig_lines), len(new_lines))
    for i in range(max_lines):
        o = orig_lines[i] if i < len(orig_lines) else None
        n = new_lines[i] if i < len(new_lines) else None
        if o != n:
            if o is not None:
                print(f"  - {o[:100]}")
            if n is not None:
                print(f"  + {n[:100]}")
            changes += 1

    print(f"\n  Изменено строк: {changes}")


def main():
    mode = "DRY RUN" if DRY_RUN else "APPLY"
    print(f"\n{'='*60}")
    print(f"  fix_prompts_vl_a01_a04.py — {mode}")
    print(f"  Дата: {date.today()}")
    print(f"{'='*60}")

    if DRY_RUN:
        print("\n  ⚠  DRY RUN — файлы НЕ изменяются")
        print("  Запусти с --apply чтобы применить\n")

    total_changed = 0

    for agent_id, individual in AGENT_PATCHES.items():
        prompt_path = MODULES / agent_id / "forge" / "prompt.md"

        if not prompt_path.exists():
            print(f"\n⚠  {agent_id}/forge/prompt.md не найден — пропускаю")
            continue

        all_replacements = COMMON_REPLACEMENTS + individual
        original, patched, count = patch_file(prompt_path, all_replacements)

        # Добавляем маркер если ещё нет
        if PATCH_MARKER not in patched:
            patched = PATCH_MARKER + "\n" + patched
            count += 1

        if count == 0:
            print(f"\n✓  {agent_id}: уже в порядке, ничего не изменилось")
            continue

        print_diff(agent_id, original, patched)
        total_changed += count

        if not DRY_RUN:
            # Бэкап
            bak = prompt_path.with_suffix(".md.bak_fix_a01_a04")
            shutil.copy2(prompt_path, bak)
            print(f"  💾 Бэкап: {bak.name}")

            # Запись
            prompt_path.write_text(patched, encoding="utf-8")
            print(f"  ✅ {agent_id}: записано ({count} замен)")

    print(f"\n{'='*60}")
    if DRY_RUN:
        print(f"  DRY RUN завершён. Всего замен: {total_changed}")
        print(f"  Запусти с --apply если diff выглядит правильно")
    else:
        print(f"  APPLY завершён. Всего замен: {total_changed}")
        print(f"  Проверь каждый промт глазами перед первым раном")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
