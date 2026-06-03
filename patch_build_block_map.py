"""
patch_build_block_map.py — фикс бага #7

_build_block_map() вызывается в save_feedback() но нигде не определена.
Каждый вызов save_feedback() с blocks падает с NameError.

Решение: добавить функцию в agent_feedback.py перед save_feedback().

Запуск из корня: python patch_build_block_map.py
"""

import sys
from pathlib import Path

FEEDBACK_PY = Path("studio") / "agent_feedback.py"
errors = []


def patch(path, old, new, label):
    text = path.read_text(encoding="utf-8")
    if old not in text:
        errors.append(f"MISS [{label}]")
        return False
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    print(f"  OK {label}")
    return True


OLD_ANCHOR = 'def save_feedback(client_slug: str, arthur_result: str | dict, slot_id: str = "", agent_ids: list = None):'

NEW_BLOCK = '''\
def _build_block_map(agent_ids: list) -> dict:
    """
    Строит маппинг блоков QA-агента на агентов цеха.

    Возвращает: {block_name: [agent_ids]}

    Работает для всех цехов без хардкода:
      turbo        A01..A05 — QA A05, chain_check 7 пунктов
      video_long   A01..A12 — QA A12 Боб, named blocks
      video_shorts A01..A12 — QA A12 Тамб Том, named blocks
      social_mix   A01..A12 — QA A12 Клавдия, named blocks

    Стратегия:
    1. Каждый агент получает block = его ID (A01, A02 ...) — всегда работает.
    2. Именованные блоки из контрактов маппятся на реальных агентов цеха.
       Если агента нет в agent_ids (например A06 в turbo) — берётся ближайший.
    3. chain_check пункты turbo маппятся с fallback: A06->A03, A10->A02.
    """
    if not agent_ids:
        return {}

    result = {}

    # Схема 1: block_name = agent_id (универсально для всех цехов)
    for aid in agent_ids:
        result[aid] = [aid]
        result[aid.lower()] = [aid]

    # Схема 2: именованные блоки с fallback для коротких цехов (turbo = A01..A05)
    # Порядок в списке = приоритет. Берётся первый who in agent_set.
    _named = {
        # визуал / кадры
        "visual":       ["A06", "A03"],
        "visuals":      ["A06", "A03"],
        "frames":       ["A06", "A03"],
        "image":        ["A06", "A03"],
        # видео / клипы
        "video":        ["A08", "A03"],
        "vfx":          ["A08", "A03"],
        "clips":        ["A08", "A03"],
        # звук / аудио
        "sound":        ["A10", "A02"],
        "audio":        ["A10", "A02"],
        "music":        ["A10", "A02"],
        # монтаж
        "motion":       ["A09", "A04"],
        "edit":         ["A09", "A04"],
        "montage":      ["A09", "A04"],
        # шрифты / субтитры
        "typography":   ["A07", "A04"],
        "captions":     ["A07", "A04"],
        "subtitles":    ["A07", "A04"],
        # раскадровка
        "storyboard":   ["A05", "A03"],
        "storyboards":  ["A05", "A03"],
        # стратегия / сценарий
        "strategy":     ["A01"],
        "concept":      ["A01"],
        "hook":         ["A02", "A01"],
        "script":       ["A03", "A02"],
        "narrative":    ["A03", "A02"],
        # thumbnail / smm / seo
        "thumbnail":    ["A11", "A04"],
        "smm":          ["A11", "A04"],
        "seo":          ["A04"],
        # turbo chain_check пункты (с fallback для 5-агентного цеха)
        "frames_have_path":      ["A06", "A03"],
        "frames_self_review":    ["A06", "A03"],
        "clips_have_video_path": ["A08", "A03"],
        "clips_clip_review":     ["A08", "A03"],
        "audio_has_path":        ["A10", "A02"],
        "audio_review":          ["A10", "A02"],
        "timings_match":         ["A04", "A09"],
        # social_mix специфичные
        "layout":        ["A05"],
        "engagement":    ["A09", "A04"],
        "analytics":     ["A10", "A04"],
        "inspection":    ["A11", "A04"],
    }

    agent_set = set(agent_ids)
    for block_name, priority_agents in _named.items():
        # Берём первого кто есть в agent_set
        valid = [a for a in priority_agents if a in agent_set]
        if valid:
            result[block_name] = [valid[0]]

    return result


''' + OLD_ANCHOR


print("=== patch_build_block_map.py ===\n")
print("studio/agent_feedback.py:")
patch(
    FEEDBACK_PY,
    OLD_ANCHOR,
    NEW_BLOCK,
    "_build_block_map() добавлена перед save_feedback()"
)

print()
if errors:
    print("ОШИБКИ:")
    for e in errors:
        print(f"  {e}")
    sys.exit(1)

print("Готово.")
print()
print("Что исправлено:")
print("  - NameError при save_feedback() с blocks устранён")
print("  - _build_block_map() работает для всех 4 цехов")
print("  - turbo chain_check пункты маппятся с fallback (A06->A03, A10->A02)")
print("  - Нет хардкода по именам цехов — всё через agent_ids")
print()
print("Commit:")
print("  fix: _build_block_map() — NameError в save_feedback() (баг #7)")
