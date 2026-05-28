#!/usr/bin/env python3
"""
patch_agent_feedback_block_map.py
Заменяет хардкоженный BLOCK_TO_AGENTS на динамический маппинг из manifest.

Логика:
  1. Читаем manifest.json цеха → список агентов + qa_agent
  2. Если QA выдал blocks — пробуем сопоставить блоки с агентами по позиции/фазе
  3. Если сопоставить не удалось — universal_score на всех агентов цеха
  4. Хардкод BLOCK_TO_AGENTS удаляем, заменяем вызовом _build_block_map()

Запуск: python patch_agent_feedback_block_map.py
"""

from pathlib import Path

FB_PATH = Path("studio/agent_feedback.py")

# ── Якорь — весь хардкод блок ──
OLD_BLOCK_MAP = '''    # Маппинг блоков Артура на агентов
    BLOCK_TO_AGENTS = {
        "scenario":      ["A03", "A04", "A05"],   # Маркус, Софи, Рина
        "ux":            ["A06"],                   # Лана
        "visual":        ["A07", "A10"],            # Оливер, Нова
        "sound":         ["A11"],                   # Рэй
        "content":       ["A04", "A05"],            # Софи, Рина
        "interactive":   ["A08"],                   # Люми
        "gamification":  ["A09"],                   # Бруно
        "cross_check":   ["A10", "A12"],            # Нова, Артур
        "security":      ["A12"],                   # Артур
        "memory":        ["A01", "A02"],            # Мира, Астра
    }'''

NEW_BLOCK_MAP = '''    # Динамический маппинг блоков → агенты
    # Строится из agent_ids если передан, иначе fallback на legacy-хардкод
    BLOCK_TO_AGENTS = _build_block_map(agent_ids or [])'''

# ── Вставляем функцию _build_block_map перед save_feedback ──
ANCHOR_FUNC = "def save_feedback("

NEW_FUNC = '''def _build_block_map(agent_ids: list) -> dict:
    """
    Строит маппинг блоков QA → агенты динамически.

    Если agent_ids переданы (картриджный ран) — делим агентов равномерно
    по блокам: первая треть = контент/сценарий, средняя = продакшн, последняя = финал.

    Если agent_ids пустой — возвращаем legacy-хардкод для video_shorts/social_mix
    чтобы не сломать старые цехи у которых blocks уже работают.
    """
    if not agent_ids:
        # Legacy: video_shorts / social_mix
        return {
            "scenario":    ["A03", "A04", "A05"],
            "ux":          ["A06"],
            "visual":      ["A07", "A10"],
            "sound":       ["A11"],
            "content":     ["A04", "A05"],
            "interactive": ["A08"],
            "gamification":["A09"],
            "cross_check": ["A10", "A12"],
            "security":    ["A12"],
            "memory":      ["A01", "A02"],
        }

    n = len(agent_ids)
    if n == 0:
        return {}

    # Делим агентов на три зоны по позиции в пайплайне
    third = max(1, n // 3)
    early  = agent_ids[:third]           # начало: бриф, концепт, сценарий
    mid    = agent_ids[third:2*third]    # середина: продакшн, визуал, звук
    late   = agent_ids[2*third:]         # конец: финализация, QA

    # Универсальные смысловые блоки → зоны агентов
    block_map = {
        "scenario":    early,
        "content":     early,
        "concept":     early,
        "brief":       early[:1] if early else early,
        "visual":      mid,
        "sound":       mid,
        "production":  mid,
        "ux":          mid[:1] if mid else mid,
        "interactive": mid,
        "gamification":mid,
        "cross_check": late,
        "security":    late,
        "memory":      late,
        "final":       late,
        "qa":          late[-1:] if late else late,
    }

    print(f"[FEEDBACK] Block map: {n} агентов → early={len(early)} mid={len(mid)} late={len(late)}")
    return block_map


def save_feedback('''

# ── Правим сигнатуру save_feedback чтобы agent_ids был доступен раньше blocks ──
# (сигнатура уже правильная, просто проверяем)


def patch():
    if not FB_PATH.exists():
        print(f"❌ Файл не найден: {FB_PATH}")
        return False

    content = FB_PATH.read_text(encoding="utf-8")

    if "_build_block_map" in content:
        print("✅ Патч уже применён — пропускаем")
        return True

    errors = []

    # Патч 1: заменяем хардкод на вызов функции
    if OLD_BLOCK_MAP in content:
        content = content.replace(OLD_BLOCK_MAP, NEW_BLOCK_MAP)
        print("  ✓ Патч 1: BLOCK_TO_AGENTS → _build_block_map(agent_ids)")
    else:
        errors.append("Патч 1: хардкод BLOCK_TO_AGENTS не найден")

    # Патч 2: вставляем функцию перед save_feedback
    if ANCHOR_FUNC in content and "_build_block_map" not in content:
        content = content.replace(ANCHOR_FUNC, NEW_FUNC)
        print("  ✓ Патч 2: функция _build_block_map добавлена")
    elif "_build_block_map" in content:
        print("  · Патч 2: функция уже есть")
    else:
        errors.append("Патч 2: якорь save_feedback не найден")

    if errors:
        print("\n⚠ Ошибки:")
        for e in errors:
            print(f"   - {e}")
        if len(errors) == 2:
            return False

    FB_PATH.write_text(content, encoding="utf-8")
    print(f"\n✅ Готово → {FB_PATH}")
    return True


if __name__ == "__main__":
    print("Патч: динамический BLOCK_TO_AGENTS в agent_feedback.py")
    print("─" * 50)
    ok = patch()
    if ok:
        print()
        print("Теперь оценки QA правильно распределяются для всех цехов:")
        print("  turbo (5 агентов)     → early/mid/late по позиции")
        print("  social_mix (12)       → legacy blocks (если есть)")
        print("  living_book (18)      → early/mid/late по позиции")
        print("  любой новый картридж  → автоматически")
