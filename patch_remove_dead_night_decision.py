# -*- coding: utf-8 -*-
"""
ПАТЧ city_yellow №12 (часть 1) — удаление мёртвого дубля _compute_night_decision.

Что делает:
  В studio/night_cycle.py есть ДВЕ функции:
    - _compute_night_decision(dna)              ← МЁРТВАЯ. resentment в ней
                                                    захардкожен в 0.0, никогда
                                                    не используется, нигде не
                                                    вызывается.
    - _compute_night_decision_with_ew(dna, ...)  ← РАБОЧАЯ. Реально вызывается
                                                    в run_night_cycle().

Патч удаляет мёртвую _compute_night_decision целиком (включая её докстринг
и пустые строки до начала рабочей функции).

Безопасность:
  - Скрипт ищет ТОЧНОЕ совпадение блока кода. Если night_cycle.py уже был
    изменён и блок не найден — скрипт ничего не делает и сообщает об этом.
  - Перед заменой создаётся резервная копия night_cycle.py.bak

Запуск:
  python patch_remove_dead_night_decision.py
  (запускать из корня репо — там где лежит studio/night_cycle.py)
"""

import shutil
from pathlib import Path

TARGET = Path("studio/night_cycle.py")

OLD_BLOCK = '''def _compute_night_decision(dna: dict) -> dict:
    """
    Детерминированное решение агента: бунт или сон.

    revolt_score = (autonomy*0.35 + resentment*0.30 + stress*0.20 + ambition*0.15)
                   - streak*0.10

    Возвращает:
    {
        "decision": "REVOLT" | "RESTLESS" | "SLEEP",
        "revolt_score": float,
        "reason": str
    }
    """
    static  = dna.get("static",  {})
    dynamic = dna.get("dynamic", {})

    autonomy  = float(static.get("Autonomy_Level", 0.5))
    stress    = float(dynamic.get("Stress",         0.0))
    streak    = int(dynamic.get("streak", 0))

    # Ambition — не все агенты имеют, дефолт 0.5
    ambition = float(static.get("Ambition", dynamic.get("Ambition", 0.5)))

    # Максимальный resentment из emotional_weights — обида давит
    # Читаем напрямую из файла чтобы не зависеть от grondheim_memory
    resentment = 0.0

    return_dict = {}
    # Будет вызван ниже после загрузки ew
    return_dict["autonomy"]  = autonomy
    return_dict["stress"]    = stress
    return_dict["streak"]    = streak
    return_dict["ambition"]  = ambition
    return_dict["resentment"] = resentment  # обновится ниже

    revolt_score = (
        autonomy   * 0.35 +
        resentment * 0.30 +
        stress     * 0.20 +
        ambition   * 0.15
    ) - (max(0, streak) * 0.10)  # только серия ПОБЕД снимает давление

    revolt_score = round(revolt_score, 3)

    if revolt_score > REVOLT_THRESHOLD:
        decision = "REVOLT"
        reason   = f"revolt_score={revolt_score:.2f} (autonomy={autonomy:.2f}, resentment={resentment:.2f})"
    elif stress > RESTLESS_STRESS:
        decision = "RESTLESS"
        reason   = f"stress={stress:.2f} — не спит, тревожный сон"
    else:
        decision = "SLEEP"
        reason   = f"revolt_score={revolt_score:.2f} — сон"

    return {
        "decision":    decision,
        "revolt_score": revolt_score,
        "reason":       reason,
    }


def _compute_night_decision_with_ew(dna: dict, agent_dir: Path) -> dict:'''

NEW_BLOCK = '''def _compute_night_decision_with_ew(dna: dict, agent_dir: Path) -> dict:'''


def main():
    if not TARGET.exists():
        print(f"❌ Файл не найден: {TARGET}")
        print("   Запускай скрипт из корня репо.")
        return

    text = TARGET.read_text(encoding="utf-8")

    if NEW_BLOCK in text and OLD_BLOCK not in text:
        print("✅ Уже применено — мёртвая функция не найдена, рабочая на месте.")
        return

    if OLD_BLOCK not in text:
        print("⚠️  Точный блок не найден — файл уже отличается от ожидаемого.")
        print("    Ничего не изменено. Патч пропущен.")
        return

    # Резервная копия
    backup = TARGET.with_suffix(".py.bak")
    shutil.copy2(TARGET, backup)
    print(f"📋 Резервная копия: {backup}")

    new_text = text.replace(OLD_BLOCK, NEW_BLOCK, 1)
    TARGET.write_text(new_text, encoding="utf-8")

    removed_lines = text.count("\n") - new_text.count("\n")
    print(f"✅ Удалена мёртвая функция _compute_night_decision (~{removed_lines} строк).")
    print("   Рабочая _compute_night_decision_with_ew осталась без изменений.")


if __name__ == "__main__":
    main()
