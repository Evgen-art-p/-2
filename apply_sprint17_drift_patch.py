"""
apply_sprint17_drift_patch.py
═══════════════════════════════════════════════════════════
Спринт 17 — Этап 9: Character Drift
Патчит studio/grondheim_memory.py:
  1. Добавляет update_profile_vector() — вычисление дрейфа
  2. Добавляет вызов в on_agent_done()
  3. Добавляет чтение profile_vector в format_dna_for_prompt()

Механика:
  - После 3+ успешных ранов (score ≥ 8) агент накапливает вектор
  - profile_vector = усреднённые паттерны успешных стратегий
  - Агент видит свой дрейф в промпте → ведёт себя соответственно
  - Без новых файлов, без новой инфраструктуры

Запуск из корня проекта:
    python apply_sprint17_drift_patch.py

Создаёт бэкап: grondheim_memory.py.bak_sprint17_drift_<timestamp>
═══════════════════════════════════════════════════════════
"""

import ast
import shutil
import sys
from datetime import datetime
from pathlib import Path

TARGET = Path("studio/grondheim_memory.py")

# ── Бэкап ────────────────────────────────────────────────
def make_backup(path: Path) -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = path.with_suffix(f".py.bak_sprint17_drift_{ts}")
    shutil.copy2(path, backup)
    print(f"[BACKUP] {backup.name}")
    return backup


# ── Проверка синтаксиса ──────────────────────────────────
def check_syntax(code: str, label: str = "") -> bool:
    """Проверяет что код парсится без ошибок."""
    try:
        ast.parse(code)
        if label:
            print(f"[SYNTAX OK] {label}")
        return True
    except SyntaxError as e:
        print(f"[SYNTAX ERROR] {label}: {e}")
        return False


# ── Патч 1: функция update_profile_vector ─────────────────
# Вставляем перед функцией on_agent_wake
ANCHOR_FUNC = "def on_agent_wake(agent_id: str, dept: str = \"\"):"

NEW_FUNCTION = '''def update_profile_vector(agent_id: str, dept: str = ""):
    """
    Вычисляет profile_vector на основе истории стратегий из Strategy Registry.
    Агент дрейфует в сторону своих успешных подходов.

    Вызывается после record_strategy() когда накоплено ≥ 3 побед.
    Сохраняет вектор в dna.json["profile_vector"].
    """
    agent_dir = _find_agent_dir(agent_id, dept)
    if not agent_dir:
        return

    dna_path = agent_dir / "dna.json"
    dna = _load_json(dna_path)
    if not dna:
        return

    # Загружаем стратегии из strategy_registry.json
    registry_path = Path("studio/strategy_registry.json")
    if not registry_path.exists():
        return

    try:
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
    except Exception:
        return

    # Собираем все стратегии агента из всех слотов
    all_strategies = []
    for slot_id, agents in registry.get("slots", {}).items():
        if agent_id in agents:
            all_strategies.extend(agents[agent_id])

    # Добавляем глобальные
    all_strategies.extend(registry.get("global", {}).get(agent_id, []))

    # Нужно минимум 3 стратегии для дрейфа
    if len(all_strategies) < 3:
        return

    # Сортируем: wins важнее score
    all_strategies.sort(
        key=lambda s: (s.get("wins", 1), s.get("score", 0)),
        reverse=True,
    )

    # Берём топ-5 стратегий
    top = all_strategies[:5]

    # Извлекаем паттерны из summaries
    # Простой подход: считаем частоту ключевых слов (без внешних зависимостей)
    import re
    from collections import Counter

    tone_words = Counter()
    approach_words = Counter()
    all_scores = []

    # Ключевые слова для определения тона
    tone_patterns = {
        "ироничный": ["ирони", "шутк", "юмор", "сарказ", "остро"],
        "серьёзный": ["серьёз", "строгий", "академич", "формаль"],
        "тёплый": ["тёпл", "забот", "эмпат", "мягк", "добр"],
        "дерзкий": ["дерзк", "смел", "провокац", "резк"],
        "поэтичный": ["поэтич", "метафор", "образ", "лирич"],
    }
    approach_patterns = {
        "структурный": ["структур", "логич", "последовательн", "анализ", "схем"],
        "интуитивный": ["интуиц", "поток", "спонтан", "импровиз"],
        "визуальный": ["визуал", "образ", "картин", "цвет", "сцен"],
        "нарративный": ["истор", "повеств", "сюжет", "рассказ", "наррат"],
        "минималистичный": ["минимал", "простой", "ясный", "чист", "лаконич"],
    }

    for s in top:
        summary = s.get("summary", "").lower()
        score = s.get("score", 0)
        wins = s.get("wins", 1)
        weight = wins * score  # комбинированный вес

        all_scores.append(score)

        # Подсчёт тона
        for tone, keywords in tone_patterns.items():
            for kw in keywords:
                if kw in summary:
                    tone_words[tone] += weight

        # Подсчёт подхода
        for approach, keywords in approach_patterns.items():
            for kw in keywords:
                if kw in summary:
                    approach_words[approach] += weight

    if not all_scores:
        return

    # Определяем доминирующий тон и подход
    dominant_tone = tone_words.most_common(1)[0][0] if tone_words else "нейтральный"
    dominant_approach = approach_words.most_common(1)[0][0] if approach_words else "сбалансированный"
    avg_score = round(sum(all_scores) / len(all_scores), 1)

    # Формируем профиль
    profile_vector = {
        "preferred_tone": dominant_tone,
        "preferred_approach": dominant_approach,
        "avg_score": avg_score,
        "total_wins": sum(s.get("wins", 1) for s in top),
        "dominant_strategy": top[0].get("summary", "")[:200] if top else "",
        "tone_breakdown": dict(tone_words.most_common(3)),
        "approach_breakdown": dict(approach_words.most_common(3)),
        "last_updated": datetime.now().isoformat(),
        "strategies_analyzed": len(all_strategies),
    }

    # Сохраняем в dna.json
    dna["profile_vector"] = profile_vector
    _save_json(dna_path, dna)

    print(
        f"[DRIFT] 🧬 {agent_id}: tone={dominant_tone}, "
        f"approach={dominant_approach}, "
        f"avg_score={avg_score}, "
        f"strategies={len(all_strategies)}"
    )


'''

# ── Патч 2: вызов в on_agent_done ─────────────────────────
ANCHOR_ON_DONE = "    # Значимое — в резонансный лог"

DRIFT_CALL = """    # ══ Character Drift (Спринт 17) ══
    if quality_score >= 0.8:
        update_profile_vector(agent_id, dept)
    # ══ END Drift ══

"""

# ── Патч 3: чтение profile_vector в format_dna_for_prompt ─
ANCHOR_DNA_END = '    lines.append("Если ты на пике — твоя энергия заразительна.")'

DRIFT_DISPLAY = """    # ══ Character Drift — показываем агенту его дрейф ══
    profile = dna.get("profile_vector", {})
    if profile:
        tone = profile.get("preferred_tone", "")
        approach = profile.get("preferred_approach", "")
        avg = profile.get("avg_score", 0)
        if tone or approach:
            lines.append("")
            lines.append("Твой характер дрейфует в сторону успешных стратегий:")
            if tone:
                lines.append(f"  • Тон: {tone}")
            if approach:
                lines.append(f"  • Подход: {approach}")
            if avg:
                lines.append(f"  • Средняя оценка успешных работ: {avg}/10")
            lines.append("Ты стал таким потому что это работало — продолжай.")
    # ══ END Drift Display ══
"""


# ─────────────────────────────────────────────────────────

def patch():
    if not TARGET.exists():
        print(f"[ERROR] Файл не найден: {TARGET}")
        print("        Запускай из корня проекта.")
        sys.exit(1)

    original = TARGET.read_text(encoding="utf-8")
    patched = original
    changes = 0

    # ── Патч 1: функция update_profile_vector ─────────────
    if "def update_profile_vector" in patched:
        print("[SKIP] update_profile_vector уже существует")
    elif ANCHOR_FUNC not in patched:
        print(f"[ERROR] Якорь не найден: {ANCHOR_FUNC}")
        sys.exit(1)
    else:
        patched = patched.replace(
            ANCHOR_FUNC,
            NEW_FUNCTION + ANCHOR_FUNC,
        )
        changes += 1
        print("[OK] Патч 1: update_profile_vector() добавлена")

    # ── Патч 2: вызов в on_agent_done ─────────────────────
    if "# ══ END Drift ══" in patched:
        print("[SKIP] Вызов update_profile_vector уже есть")
    elif ANCHOR_ON_DONE not in patched:
        print(f"[ERROR] Якорь on_agent_done не найден: {ANCHOR_ON_DONE}")
        sys.exit(1)
    else:
        # Вставляем ПЕРЕД "Значимое — в резонансный лог"
        patched = patched.replace(
            ANCHOR_ON_DONE,
            DRIFT_CALL + ANCHOR_ON_DONE,
        )
        changes += 1
        print("[OK] Патч 2: вызов в on_agent_done() добавлен")

    # ── Патч 3: отображение в промпте ─────────────────────
    if "# ══ END Drift Display ══" in patched:
        print("[SKIP] Отображение profile_vector уже есть")
    elif ANCHOR_DNA_END not in patched:
        print(f"[ERROR] Якорь format_dna_for_prompt не найден: {ANCHOR_DNA_END}")
        sys.exit(1)
    else:
        patched = patched.replace(
            ANCHOR_DNA_END,
            ANCHOR_DNA_END + "\n" + DRIFT_DISPLAY,
        )
        changes += 1
        print("[OK] Патч 3: отображение дрейфа в format_dna_for_prompt() добавлено")

    # ── Проверка синтаксиса ───────────────────────────────
    if patched == original:
        print("[INFO] Файл не изменён — все патчи уже применены ранее.")
        return

    if not check_syntax(patched, "grondheim_memory.py (итоговый)"):
        print("[ABORT] Синтаксическая ошибка в итоговом коде. Бэкап НЕ тронут.")
        sys.exit(1)

    # ── Сохраняем ─────────────────────────────────────────
    make_backup(TARGET)
    TARGET.write_text(patched, encoding="utf-8")
    print(f"\n✅ Готово! {TARGET} обновлён ({changes} изменений).")
    print("\nЧто сделано:")
    print("  · update_profile_vector() — вычисляет дрейф из Strategy Registry")
    print("  · Вызов в on_agent_done() при quality_score ≥ 0.8")
    print("  · Отображение в format_dna_for_prompt() — агент видит свой дрейф")
    print("  · profile_vector сохраняется в dna.json")
    print("\nКогда сработает:")
    print("  · Нужно ≥ 3 успешных стратегий в strategy_registry.json")
    print("  · После каждого рана с score ≥ 8 — профиль обновляется")
    print("  · Агент начинает осознавать свой стиль в промпте")
    print("\nБэкап создан. Синтаксис проверен. Можно запускать студию.")


if __name__ == "__main__":
    patch()