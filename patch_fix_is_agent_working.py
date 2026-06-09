"""
patch_fix_is_agent_working.py
══════════════════════════════════════════════════════
СПРИНТ 42 · Баг #26

ПРОБЛЕМА:
  В grondheim_memory.py есть своя _is_agent_working(agent_id),
  которая читает city_pulse.jsonl и ищет:
      entry.get("status") in ("work_start", "working")
  Но в city_pulse.py событие называется event="work_start",
  а поля "status" в записи нет.
  → функция НИКОГДА не возвращала True → walk_rest и Recovery
    не замораживались несмотря на патч recovery_freeze.

РЕШЕНИЕ:
  Заменяем самодельную _is_agent_working() на делегат к
  city_pulse.is_agent_working() — единственный источник правды.
  Сигнатура публичного API сохраняется.

ФАЙЛ: studio/grondheim_memory.py
ИДЕМПОТЕНТЕН: да (проверяет маркер перед заменой)
"""

import shutil
from datetime import datetime
from pathlib import Path

TARGET = Path("studio/grondheim_memory.py")

# ── Маркер что патч уже применён ─────────────────────────────
MARKER = "# PATCH_FIX_IS_AGENT_WORKING_APPLIED"

# ── Старый код (точная строка из репо) ───────────────────────
OLD = '''def _is_agent_working(agent_id: str) -> bool:
    """Проверяет находится ли агент в рабочем статусе по city_pulse.
    Если да — walk_rest и RECOVERY не должны сбрасывать стресс.
    """
    try:
        pulse_path = Path("studio/city_pulse.jsonl")
        if not pulse_path.exists():
            return False
        lines = pulse_path.read_text(encoding="utf-8").splitlines()[-500:]
        for line in reversed(lines):
            try:
                entry = json.loads(line)
                if entry.get("agent") == agent_id:
                    return entry.get("status") in ("work_start", "working")
            except Exception:
                continue
    except Exception:
        pass
    return False'''

# ── Новый код ─────────────────────────────────────────────────
NEW = '''def _is_agent_working(agent_id: str) -> bool:
    """Проверяет находится ли агент в рабочем статусе по city_pulse.
    Если да — walk_rest и RECOVERY не должны сбрасывать стресс.

    PATCH_FIX_IS_AGENT_WORKING_APPLIED · Спринт 42
    Делегируем в city_pulse.is_agent_working() — единственный источник правды.
    Старая реализация искала entry.get("status") in ("work_start", "working"),
    но в city_pulse.py поле называется event="work_start", а "status" отсутствует
    → функция всегда возвращала False → walk_rest и Recovery не замораживались.
    """
    try:
        from studio.city_pulse import is_agent_working as _cp_working
        result = _cp_working(agent_id, max_hours=8.0)
        return result is not None
    except Exception:
        pass
    return False'''


def main():
    # Проверяем файл
    if not TARGET.exists():
        print(f"[PATCH] ❌ Файл не найден: {TARGET}")
        print("[PATCH]    Запускай из корня проекта (C:\\Users\\Евгений\\Desktop\\студия 2)")
        return

    text = TARGET.read_text(encoding="utf-8")

    # Идемпотентность
    if MARKER in text:
        print("[PATCH] ✅ Патч уже применён — пропускаю")
        return

    # Проверяем что старый код на месте
    if OLD not in text:
        print("[PATCH] ⚠️  Старый код _is_agent_working не найден точно.")
        print("[PATCH]    Возможно файл уже изменён локально.")
        print("[PATCH]    Проверь grondheim_memory.py вручную:")
        print()
        print("  Должно быть (убрать):")
        print("    return entry.get(\"status\") in (\"work_start\", \"working\")")
        print()
        print("  Заменить на:")
        print("    from studio.city_pulse import is_agent_working as _cp_working")
        print("    result = _cp_working(agent_id, max_hours=8.0)")
        print("    return result is not None")
        return

    # Бэкап
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = TARGET.with_suffix(f".bak_{ts}")
    shutil.copy2(TARGET, bak)
    print(f"[PATCH] 📦 Бэкап: {bak.name}")

    # Замена
    new_text = text.replace(OLD, NEW, 1)

    # Записываем
    TARGET.write_text(new_text, encoding="utf-8")
    print(f"[PATCH] ✅ Применён: {TARGET}")
    print()
    print("[PATCH] Что изменилось:")
    print("  _is_agent_working() теперь делегирует в city_pulse.is_agent_working()")
    print("  Единый источник правды — больше нет дублирующейся логики")
    print("  walk_rest и Recovery теперь корректно замораживаются во время рана")
    print()
    print("[PATCH] Проверь:")
    print("  python -c \"from studio.grondheim_memory import _is_agent_working; print('OK')\"")


if __name__ == "__main__":
    main()
