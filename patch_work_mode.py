# patch_work_mode.py
# Запускать из корня проекта:
#   python patch_work_mode.py
#
# Два патча:
#   1. studio/workshop/pipeline.py
#      _detect_agent_mode() получает state и проверяет _force_work_mode
#   2. run_council.py
#      В state добавляется "_force_work_mode": True

from pathlib import Path
import shutil
from datetime import datetime

# ════════════════════════════════════════════════════════════

PIPELINE = Path("studio/workshop/pipeline.py")
COUNCIL  = Path("run_council.py")

# ── Патч 1: pipeline.py ─────────────────────────────────────

OLD_DETECT = '''\
def _detect_agent_mode(worker_id: str) -> str:
    """
    Определяет режим агента: 'work' или 'home'.

    'work' → is_agent_working() вернул данные о незакрытом ране.
    'home' → агент свободен (прогулка, утро, вечер).

    Использует city_pulse.is_agent_working() — единственный источник правды.
    Тот же вызов что и в grondheim_memory._is_agent_working() после патча #26.
    """
    try:
        from studio.city_pulse import is_agent_working as _cp_working
        result = _cp_working(worker_id, max_hours=8.0)
        mode = "work" if result is not None else "home"
        print(f"[MODE] {worker_id}: {mode.upper()}" +
              (f" (slot={result.get('slot_id','?')})" if result else ""))
        return mode
    except Exception as _e:
        # Безопасный fallback — если city_pulse недоступен,
        # считаем что агент работает (build_agent_context вызывается из пайплайна)
        print(f"[MODE] {worker_id}: fallback → work ({_e})")
        return "work"'''

NEW_DETECT = '''\
def _detect_agent_mode(worker_id: str, state: dict = None) -> str:
    """
    Определяет режим агента: 'work' или 'home'.

    'work' → is_agent_working() вернул данные о незакрытом ране.
    'home' → агент свободен (прогулка, утро, вечер).

    Если state содержит _force_work_mode=True (CLI-запуски, run_council и т.п.)
    — сразу возвращаем 'work' без обращения к city_pulse.

    Использует city_pulse.is_agent_working() — единственный источник правды.
    Тот же вызов что и в grondheim_memory._is_agent_working() после патча #26.
    """
    # CLI-ран или любой запуск без UI — явный флаг в state
    if state and state.get("_force_work_mode"):
        print(f"[MODE] {worker_id}: WORK (force)")
        return "work"
    try:
        from studio.city_pulse import is_agent_working as _cp_working
        result = _cp_working(worker_id, max_hours=8.0)
        mode = "work" if result is not None else "home"
        print(f"[MODE] {worker_id}: {mode.upper()}" +
              (f" (slot={result.get('slot_id','?')})" if result else ""))
        return mode
    except Exception as _e:
        # Безопасный fallback — если city_pulse недоступен,
        # считаем что агент работает (build_agent_context вызывается из пайплайна)
        print(f"[MODE] {worker_id}: fallback → work ({_e})")
        return "work"'''

# Вызов _detect_agent_mode в build_agent_context — передаём state
OLD_CALL = "    agent_mode = _detect_agent_mode(worker_id)"
NEW_CALL = "    agent_mode = _detect_agent_mode(worker_id, state)"

# ── Патч 2: run_council.py ───────────────────────────────────

OLD_STATE = '''\
        "chain_data":    {},
        "results":       {},
        "_agent_ids":    [],
    }'''

NEW_STATE = '''\
        "chain_data":    {},
        "results":       {},
        "_agent_ids":    [],
        "_force_work_mode": True,   # CLI-ран: агенты всегда в WORK-режиме
    }'''


# ════════════════════════════════════════════════════════════

def patch_file(path: Path, old: str, new: str, label: str) -> bool:
    if not path.exists():
        print(f"❌ Не найден: {path}")
        return False
    text = path.read_text(encoding="utf-8")
    if old not in text:
        print(f"⚠️  Якорь не найден в {path} ({label}) — уже пропатчен?")
        return False
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = path.with_suffix(f".py.bak_{ts}")
    shutil.copy2(path, backup)
    print(f"💾 Бэкап: {backup}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    print(f"✅ {label}: {path}")
    return True


def main():
    ok1 = patch_file(PIPELINE, OLD_DETECT, NEW_DETECT,
                     "_detect_agent_mode получает state")
    ok2 = patch_file(PIPELINE, OLD_CALL,   NEW_CALL,
                     "_detect_agent_mode вызов с state")
    ok3 = patch_file(COUNCIL,  OLD_STATE,  NEW_STATE,
                     "_force_work_mode в run_council state")

    if ok1 and ok2 and ok3:
        print()
        print("Все три патча применены. Запускай:")
        print("  python run_council.py EURUSDDaily.csv EURUSDDaily D1 --bars 50")
        print()
        print("В логе должно появиться:")
        print("  [MODE] A01: WORK (force)")
        print("  [MODE] A02: WORK (force)")
    else:
        print()
        print("Не все патчи применены — проверь вывод выше.")


if __name__ == "__main__":
    main()
