#!/usr/bin/env python3
"""
patch_fix_night_rest.py
════════════════════════════════════════════════════════════════
Фикс бага: двойной sync_to_dna в ночном цикле.

Проблема:
  _run_decay_for_agent() → sync_to_dna("night_rest")  для ВСЕХ
  _apply_night_decision() → sync_to_dna("night_sleep") для SLEEP
  Итог: каждый агент получает ДВА вызова SOUL вместо одного.

Фикс:
  _apply_night_decision() теперь добавляет ТОЛЬКО бонус сверх decay:
    SLEEP    → night_sleep (бонус за хороший день)
    RESTLESS → ничего     (decay достаточно)
    REVOLT   → night_rest x0.6 (частичный бонус за ночную работу)

Студия «Шесть Пальцев» · Спринт 23 · 2026
"""

import sys
from pathlib import Path
from datetime import datetime

NIGHT_CYCLE = Path("studio/night_cycle.py")

if not NIGHT_CYCLE.exists():
    print("❌ studio/night_cycle.py не найден — запусти сначала patch_daily_cycle.py")
    sys.exit(1)

OLD_FUNC = '''def _apply_night_decision(dna_path: Path, dna: dict, folder: str, dept: str, decision: str) -> dict:
    """
    Применяет последствия ночного решения через sync_to_dna().
    Возвращает обновлённые значения.
    """
    try:
        from studio.grondheim_memory import sync_to_dna

        if decision == "SLEEP":
            # Глубокий сон — лучшее восстановление
            sync_to_dna(folder, "night_sleep", intensity=1.0, dept=dept)

        elif decision == "RESTLESS":
            # Тревожный сон — почти ничего
            sync_to_dna(folder, "night_rest", intensity=0.3, dept=dept)

        elif decision == "REVOLT":
            # Бунт: сгорел в работе → частичный сброс стресса
            # (полное восстановление зависит от Stubbornness — см. morning_checkout)
            sync_to_dna(folder, "night_rest", intensity=0.6, dept=dept)

    except Exception:
        # Фоллбэк: прямая запись
        dynamic = dna.get("dynamic", {})
        if decision == "SLEEP":
            dynamic["Stress"]   = round(max(0.0, float(dynamic.get("Stress", 0)) - 0.05), 3)
            dynamic["Patience"] = round(min(1.0, float(dynamic.get("Patience", 1)) + 0.02), 3)
        elif decision == "RESTLESS":
            dynamic["Stress"]   = round(max(0.0, float(dynamic.get("Stress", 0)) - 0.01), 3)
        elif decision == "REVOLT":
            dynamic["Stress"]   = round(max(0.0, float(dynamic.get("Stress", 0)) - 0.03), 3)

        dna["dynamic"] = dynamic
        try:
            dna_path.write_text(
                json.dumps(dna, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
        except Exception:
            pass

    # Перечитываем актуальный dna
    try:
        return json.loads(dna_path.read_text(encoding="utf-8"))
    except Exception:
        return dna'''

NEW_FUNC = '''def _apply_night_decision(dna_path: Path, dna: dict, folder: str, dept: str, decision: str) -> dict:
    """
    Применяет последствия ночного решения через sync_to_dna().

    ВАЖНО: _run_decay_for_agent() уже вызвал night_rest для ВСЕХ агентов.
    Здесь добавляем ТОЛЬКО бонус сверх decay — иначе двойной SOUL вызов.

      SLEEP    → night_sleep (бонус за глубокий сон)
      RESTLESS → ничего     (decay достаточно, сон тревожный)
      REVOLT   → night_rest x0.6 (частичный бонус за ночную работу)
    """
    try:
        from studio.grondheim_memory import sync_to_dna

        if decision == "SLEEP":
            sync_to_dna(folder, "night_sleep", intensity=1.0, dept=dept)

        elif decision == "RESTLESS":
            pass  # decay уже отработал — тревожный сон бонуса не даёт

        elif decision == "REVOLT":
            sync_to_dna(folder, "night_rest", intensity=0.6, dept=dept)

    except Exception:
        # Фоллбэк: прямая запись только для SLEEP
        if decision == "SLEEP":
            dynamic = dna.get("dynamic", {})
            dynamic["Stress"]   = round(max(0.0, float(dynamic.get("Stress", 0)) - 0.05), 3)
            dynamic["Patience"] = round(min(1.0, float(dynamic.get("Patience", 1)) + 0.02), 3)
            dna["dynamic"] = dynamic
            try:
                dna_path.write_text(
                    json.dumps(dna, ensure_ascii=False, indent=2),
                    encoding="utf-8"
                )
            except Exception:
                pass

    try:
        return json.loads(dna_path.read_text(encoding="utf-8"))
    except Exception:
        return dna'''


def main():
    print("=" * 60)
    print("ПАТЧ: фикс двойного night_rest")
    print(f"Время: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)

    code = NIGHT_CYCLE.read_text(encoding="utf-8")

    if "decay уже отработал" in code:
        print("ℹ Патч уже применён — пропускаем")
        return

    if OLD_FUNC not in code:
        print("⚠ Точный якорь не найден — пробуем мягкий поиск")
        # Мягкий поиск по сигнатуре функции
        if "def _apply_night_decision" not in code:
            print("❌ Функция _apply_night_decision не найдена в файле")
            sys.exit(1)

        # Находим начало и конец функции вручную
        start = code.find("def _apply_night_decision")
        # Следующая def на том же уровне отступа
        next_def = code.find("\ndef ", start + 10)
        if next_def == -1:
            print("❌ Не удалось найти конец функции")
            sys.exit(1)

        old_block = code[start:next_def]
        new_code  = code[:start] + NEW_FUNC + code[next_def:]

        backup = NIGHT_CYCLE.with_suffix(".py.bak_fix_nightrest")
        backup.write_text(code, encoding="utf-8")
        print(f"  ✅ Бэкап: {backup.name}")

        NIGHT_CYCLE.write_text(new_code, encoding="utf-8")
        print("  ✅ Функция заменена (мягкий поиск)")
    else:
        backup = NIGHT_CYCLE.with_suffix(".py.bak_fix_nightrest")
        backup.write_text(code, encoding="utf-8")
        print(f"  ✅ Бэкап: {backup.name}")

        new_code = code.replace(OLD_FUNC, NEW_FUNC, 1)
        NIGHT_CYCLE.write_text(new_code, encoding="utf-8")
        print("  ✅ Функция заменена (точный поиск)")

    print()
    print("Результат: каждый агент получает ровно один [SOUL] вызов за ночь:")
    print("  SLEEP    → night_rest (decay) + night_sleep (бонус)")
    print("  RESTLESS → night_rest (decay) только")
    print("  REVOLT   → night_rest (decay) + night_rest x0.6 (бонус)")
    print("=" * 60)


if __name__ == "__main__":
    main()
