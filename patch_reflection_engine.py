#!/usr/bin/env python3
"""
patch_reflection_engine.py
══════════════════════════
Студия «Шесть Пальцев» — Патч: Reflection Engine.

Что делает:
  1. Создаёт studio/reflection.py — движок рефлексии:
     • Читает global_feedback.json после каждых N ранов
     • Извлекает поведенческие паттерны по каждому агенту
     • Формирует человекочитаемый вывод (не сырые данные)
     • Определяет режим агента: GENIUS / NORMAL / SAFE / RECOVERY

  2. Подключает reflection.py в pipeline.py:
     • get_reflection() вызывается в build_agent_context()
     • Инжектируется в промпт рядом с feedback

  Reflection срабатывает каждые REFLECTION_EVERY_N_RUNS ранов (default: 5).
  Между ранами используется кешированный вывод.

Запуск из корня проекта:
  python patch_reflection_engine.py
"""

import shutil
from pathlib import Path

STUDIO = Path("studio")
PIPELINE = STUDIO / "workshop" / "pipeline.py"
REFLECTION = STUDIO / "reflection.py"


def backup(path: Path):
    bak = path.with_suffix(path.suffix + ".bak_reflection")
    shutil.copy2(path, bak)
    print(f"  📦 Бэкап: {bak.name}")


# ════════════════════════════════════════════════════════════
# reflection.py — полный файл
# ════════════════════════════════════════════════════════════

REFLECTION_PY = '''# studio/reflection.py — Reflection Engine
# Студия «Шесть Пальцев» · 2026
#
# Читает global_feedback.json → извлекает паттерны → инжектирует в промпт.
# Агент видит не сырые цифры, а осмысленный вывод о себе.
#
# Три режима агента (определяются по avg_score + streak):
#   GENIUS MODE   — avg ≥ 8.5, streak ≥ 3  → температура вверх, свобода
#   NORMAL MODE   — avg 6–8.5               → стандартный режим
#   SAFE MODE     — avg 4–6                 → строгий формат, меньше импровизации
#   RECOVERY MODE — avg < 4 или streak ≤ -3 → минимальный вывод, самопроверка

import json
from pathlib import Path
from datetime import datetime

GLOBAL_FEEDBACK_PATH = Path("studio") / "global_feedback.json"
REFLECTION_CACHE_PATH = Path("studio") / "reflection_cache.json"

# Каждые N ранов пересчитываем рефлексию
REFLECTION_EVERY_N_RUNS = 5

# Минимум ранов чтобы делать выводы
MIN_RUNS_FOR_REFLECTION = 3


def _load_global() -> dict:
    """Загружает global_feedback.json."""
    if GLOBAL_FEEDBACK_PATH.exists():
        try:
            return json.loads(GLOBAL_FEEDBACK_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"agents": {}, "total_runs": 0}


def _load_cache() -> dict:
    """Загружает кеш рефлексии."""
    if REFLECTION_CACHE_PATH.exists():
        try:
            return json.loads(REFLECTION_CACHE_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"last_run": 0, "agents": {}}


def _save_cache(cache: dict):
    """Сохраняет кеш рефлексии."""
    REFLECTION_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    REFLECTION_CACHE_PATH.write_text(
        json.dumps(cache, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


def _get_mode(avg_score: float, streak: int, stars: int) -> str:
    """Определяет режим агента по его истории."""
    if avg_score >= 8.5 and streak >= 3:
        return "GENIUS"
    elif avg_score >= 8.0 or stars >= 3:
        return "GENIUS"
    elif avg_score >= 6.0:
        return "NORMAL"
    elif avg_score >= 4.0:
        return "SAFE"
    else:
        return "RECOVERY"


def _mode_instruction(mode: str) -> str:
    """Инструкция для промпта в зависимости от режима."""
    instructions = {
        "GENIUS": (
            "🔥 GENIUS MODE активен.\\n"
            "Ты на пике — серия побед и высокий средний балл.\\n"
            "Разрешена нестандартная структура, смелые решения, творческий риск.\\n"
            "Доверяй своей интуиции."
        ),
        "NORMAL": (
            "✅ NORMAL MODE.\\n"
            "Стабильная работа. Балансируй между структурой и творчеством."
        ),
        "SAFE": (
            "⚠️ SAFE MODE.\\n"
            "Средний балл ниже нормы. Работай строго по формату.\\n"
            "Никакой импровизации. Проверяй каждый шаг."
        ),
        "RECOVERY": (
            "🔴 RECOVERY MODE.\\n"
            "Серия неудач или низкий балл. Режим восстановления.\\n"
            "Только чёткая структура. Краткие ответы. Обязательная самопроверка перед выводом.\\n"
            "Не пытайся быть креативным — сначала восстанови доверие."
        ),
    }
    return instructions.get(mode, "")


def _extract_patterns(agent_data: dict) -> dict:
    """
    Извлекает поведенческие паттерны из данных агента.
    Возвращает структурированный вывод.
    """
    runs = agent_data.get("runs", 0)
    avg_score = agent_data.get("avg_score", 5.0)
    streak = agent_data.get("streak", 0)
    stars = agent_data.get("stars", 0)
    recurring = agent_data.get("recurring_problems", [])
    last_problems = agent_data.get("last_problems", [])

    mode = _get_mode(avg_score, streak, stars)

    # Повторяющиеся проблемы (встречались 2+ раз)
    chronic = [p for p in recurring if p.get("count", 0) >= 2]

    # Тренд: улучшение или деградация
    if streak >= 3:
        trend = "улучшение"
    elif streak <= -2:
        trend = "деградация"
    else:
        trend = "стабильно"

    return {
        "runs": runs,
        "avg_score": avg_score,
        "streak": streak,
        "stars": stars,
        "mode": mode,
        "trend": trend,
        "chronic_problems": chronic,
        "last_problems": last_problems,
        "mode_instruction": _mode_instruction(mode),
    }


def rebuild_reflection_cache():
    """
    Пересчитывает рефлексию для всех агентов.
    Вызывается каждые REFLECTION_EVERY_N_RUNS ранов.
    """
    gf = _load_global()
    total_runs = gf.get("total_runs", 0)
    agents_data = gf.get("agents", {})

    cache = {
        "last_run": total_runs,
        "updated_at": datetime.now().isoformat(),
        "agents": {},
    }

    for agent_id, data in agents_data.items():
        if data.get("runs", 0) < MIN_RUNS_FOR_REFLECTION:
            continue  # Мало данных — пропускаем

        patterns = _extract_patterns(data)
        cache["agents"][agent_id] = patterns

    _save_cache(cache)
    print(f"[REFLECTION] 🧠 Кеш пересчитан: {len(cache[\'agents\'])} агентов, {total_runs} ранов")
    return cache


def maybe_rebuild(force: bool = False):
    """
    Пересчитывает кеш если пришло время.
    Вызывается при каждом старте рана — быстро если не пора.
    """
    gf = _load_global()
    total_runs = gf.get("total_runs", 0)

    cache = _load_cache()
    last_run = cache.get("last_run", 0)

    if force or (total_runs - last_run) >= REFLECTION_EVERY_N_RUNS:
        return rebuild_reflection_cache()

    return cache


def get_reflection(agent_id: str) -> str:
    """
    Возвращает текст рефлексии для агента — для инжекта в промпт.
    Вызывается из build_agent_context() в pipeline.py.

    Если данных мало или агент новый — возвращает пустую строку.
    """
    cache = _load_cache()
    agent_data = cache.get("agents", {}).get(agent_id)

    if not agent_data:
        return ""

    runs = agent_data.get("runs", 0)
    avg = agent_data.get("avg_score", 5.0)
    streak = agent_data.get("streak", 0)
    stars = agent_data.get("stars", 0)
    mode = agent_data.get("mode", "NORMAL")
    trend = agent_data.get("trend", "стабильно")
    chronic = agent_data.get("chronic_problems", [])
    mode_instruction = agent_data.get("mode_instruction", "")

    lines = [f"=== 🧠 РЕФЛЕКСИЯ (на основе {runs} ранов) ==="]

    # Статистика
    stars_str = "⭐" * min(stars, 5) if stars > 0 else "нет"
    streak_str = f"🔥 +{streak}" if streak > 0 else f"💀 {streak}" if streak < 0 else "0"
    lines.append(f"Средний балл: {avg:.1f}/10 | Серия: {streak_str} | Звёзды: {stars_str}")
    lines.append(f"Тренд: {trend}")

    # Режим
    lines.append("")
    lines.append(mode_instruction)

    # Хронические проблемы
    if chronic:
        lines.append("")
        lines.append("⚠️ ХРОНИЧЕСКИЕ ПРОБЛЕМЫ (повторяются из раза в раз — ОБЯЗАТЕЛЬНО исправь):")
        for p in chronic[:3]:
            count = p.get("count", 0)
            text = p.get("text", "")
            lines.append(f"  [{count}x] {text}")

    lines.append("=== КОНЕЦ РЕФЛЕКСИИ ===")
    return "\\n".join(lines)


def get_reflection_summary() -> str:
    """
    Краткая сводка по всей студии — для логов и мониторинга.
    """
    cache = _load_cache()
    agents = cache.get("agents", {})

    if not agents:
        return "[REFLECTION] Кеш пуст — нужно больше ранов"

    lines = [f"[REFLECTION] Студия: {len(agents)} агентов проанализировано"]

    genius = [a for a, d in agents.items() if d.get("mode") == "GENIUS"]
    recovery = [a for a, d in agents.items() if d.get("mode") == "RECOVERY"]
    safe = [a for a, d in agents.items() if d.get("mode") == "SAFE"]

    if genius:
        lines.append(f"  🔥 GENIUS: {\', \'.join(genius)}")
    if recovery:
        lines.append(f"  🔴 RECOVERY: {\', \'.join(recovery)}")
    if safe:
        lines.append(f"  ⚠️ SAFE: {\', \'.join(safe)}")

    return "\\n".join(lines)
'''


# ════════════════════════════════════════════════════════════
# Что вставляем в pipeline.py
# ════════════════════════════════════════════════════════════

# Импорт в начало файла
IMPORT_MARKER = "# Feedback loop — оценки от QA-агента цеха"
IMPORT_OLD_MARKER = "# Feedback loop — оценки от Артура"

NEW_IMPORT = """# Reflection Engine — поведенческие паттерны из истории ранов
try:
    from studio.reflection import get_reflection, maybe_rebuild
    _REFLECTION_ENABLED = True
    print("[REFLECTION] 🧠 Reflection Engine подключён")
except ImportError:
    _REFLECTION_ENABLED = False
    def get_reflection(agent_id): return ""
    def maybe_rebuild(force=False): pass

"""

# Вызов maybe_rebuild в начале рана (в CartridgeRunner.run → pipeline начало)
# Вставляем в build_agent_context — перед get_feedback

OLD_FEEDBACK_LINE = "    # Обратная связь от QA (прошлый ран)\n    feedback = get_feedback(client_slug, worker_id)"

NEW_FEEDBACK_LINE = """    # Рефлексия — поведенческие паттерны из истории ранов
    if _REFLECTION_ENABLED:
        reflection = get_reflection(worker_id)
        if reflection:
            context += reflection + "\\n\\n"

    # Обратная связь от QA (прошлый ран)
    feedback = get_feedback(client_slug, worker_id)"""

# maybe_rebuild вызываем после save_feedback — данные уже обновлены
OLD_SYNC_CALL = "        # ══ SYNC: реальные оценки QA → DNA агентов ══\n        _sync_feedback_scores_to_dna(client_slug, state.get(\"active_dept\", \"\"))"

NEW_SYNC_CALL = """        # ══ SYNC: реальные оценки QA → DNA агентов ══
        _sync_feedback_scores_to_dna(client_slug, state.get("active_dept", ""))
        # ══ REFLECTION: пересчитываем паттерны если пришло время ══
        if _REFLECTION_ENABLED:
            maybe_rebuild()"""


def create_reflection_py():
    print("\n── reflection.py ──")

    if REFLECTION.exists():
        print("  ✅ Уже существует, пропускаем")
        return True

    REFLECTION.write_text(REFLECTION_PY, encoding="utf-8")
    print("  ✅ studio/reflection.py создан")
    return True


def patch_pipeline():
    print("\n── pipeline.py ──")

    if not PIPELINE.exists():
        print("  ❌ Файл не найден")
        return False

    text = PIPELINE.read_text(encoding="utf-8")

    if "_REFLECTION_ENABLED" in text:
        print("  ✅ Уже пропатчен, пропускаем")
        return True

    backup(PIPELINE)
    changed = False

    # 1. Добавляем импорт
    marker = IMPORT_MARKER if IMPORT_MARKER in text else IMPORT_OLD_MARKER
    if marker in text:
        text = text.replace(marker, NEW_IMPORT + marker)
        print("  ✅ Импорт reflection добавлен")
        changed = True
    else:
        # Вставляем после первых импортов
        text = NEW_IMPORT + text
        print("  ⚠️ Импорт добавлен в начало файла")
        changed = True

    # 2. Добавляем инжект рефлексии в build_agent_context
    if OLD_FEEDBACK_LINE in text:
        text = text.replace(OLD_FEEDBACK_LINE, NEW_FEEDBACK_LINE)
        print("  ✅ Инжект рефлексии в build_agent_context добавлен")
        changed = True
    else:
        print("  ⚠️ Место для инжекта не найдено — добавь вручную в build_agent_context():")
        print("     reflection = get_reflection(worker_id)")
        print("     if reflection: context += reflection + '\\n\\n'")

    # 3. Добавляем maybe_rebuild после sync
    if OLD_SYNC_CALL in text:
        text = text.replace(OLD_SYNC_CALL, NEW_SYNC_CALL)
        print("  ✅ maybe_rebuild() добавлен после sync_feedback")
        changed = True
    else:
        # Мягкий вариант — после save_feedback
        if "_sync_feedback_scores_to_dna" in text:
            text = text.replace(
                "_sync_feedback_scores_to_dna(client_slug, state.get(\"active_dept\", \"\"))",
                "_sync_feedback_scores_to_dna(client_slug, state.get(\"active_dept\", \"\"))\n        if _REFLECTION_ENABLED:\n            maybe_rebuild()"
            )
            print("  ⚠️ maybe_rebuild добавлен (мягкий вариант)")
            changed = True
        else:
            print("  ⚠️ Добавь вручную после save_feedback(): maybe_rebuild()")

    if changed:
        PIPELINE.write_text(text, encoding="utf-8")
        print("  ✅ pipeline.py сохранён")

    return changed


def verify():
    print("\n── Проверка ──")
    ok = True

    # reflection.py
    if REFLECTION.exists():
        text = REFLECTION.read_text(encoding="utf-8")
        if "get_reflection" in text and "GENIUS" in text and "RECOVERY" in text:
            print("  ✅ reflection.py: все режимы на месте")
        else:
            print("  ❌ reflection.py: что-то не так")
            ok = False
    else:
        print("  ❌ reflection.py не найден")
        ok = False

    # pipeline.py
    if PIPELINE.exists():
        text = PIPELINE.read_text(encoding="utf-8")
        checks = [
            ("_REFLECTION_ENABLED", "импорт"),
            ("get_reflection(worker_id)", "инжект в контекст"),
            ("maybe_rebuild()", "пересчёт кеша"),
        ]
        for marker, label in checks:
            if marker in text:
                print(f"  ✅ pipeline.py: {label}")
            else:
                print(f"  ❌ pipeline.py: {label} не найден")
                ok = False

    return ok


def main():
    print("=" * 55)
    print("  Патч: Reflection Engine")
    print("  Студия «Шесть Пальцев»")
    print("=" * 55)

    if not STUDIO.exists():
        print("\n❌ Папка studio/ не найдена")
        print("   Запусти из корня проекта!")
        return

    create_reflection_py()
    patch_pipeline()

    print("\n" + "=" * 55)
    if verify():
        print("  🎉 Патч применён успешно!")
        print("\n  Как работает:")
        print("  • Каждые 5 ранов система анализирует global_feedback.json")
        print("  • Для каждого агента определяется режим:")
        print("    🔥 GENIUS  — avg ≥ 8.5, streak ≥ 3")
        print("    ✅ NORMAL  — avg 6–8.5")
        print("    ⚠️ SAFE    — avg 4–6")
        print("    🔴 RECOVERY — avg < 4 или streak ≤ -3")
        print("  • Режим + хронические проблемы инжектируются в промпт")
        print("  • Агент видит осмысленный вывод, а не сырые цифры")
        print("  • Кеш: studio/reflection_cache.json")
        print("\n  Бэкап: pipeline.py.bak_reflection")
    else:
        print("  ⚠️  Проверь файлы вручную")
    print("=" * 55)


if __name__ == "__main__":
    main()
