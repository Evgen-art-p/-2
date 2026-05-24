"""
patch_pipeline_culture.py — Спринт 22
Точечный патч pipeline.py: инжект культурного поля в build_agent_context().

Что делает:
  - После блока Strategy Registry добавляет Cultural Field
  - CulturalFieldTracker.format_field_for_prompt() → контекст агента
  - Только stable/global паттерны, топ-5, формулировка мягкая
  - Не срабатывает если _slot_id не задан или нет stable паттернов
  - _CULTURE_ENABLED уже есть в pipeline.py — просто используем

Запуск: python patch_pipeline_culture.py
"""
import shutil
from pathlib import Path

TARGET = Path("studio/workshop/pipeline.py")

OLD_BLOCK = '    # ══ Strategy Registry — успешные стратегии по слоту ══\n    if _STRATEGY_ENABLED:\n        _slot_id_for_strat = state.get("_slot_id", "")\n        strategies = get_strategies(worker_id, slot_id=_slot_id_for_strat)\n        if strategies:\n            context += strategies + "\\n\\n"\n            print(f"[STRATEGY] 🏆 {worker_id}: стратегии загружены ({len(strategies)} симв.)")\n    # ══ end Strategy Registry ══'

NEW_BLOCK = '    # ══ Strategy Registry — успешные стратегии по слоту ══\n    if _STRATEGY_ENABLED:\n        _slot_id_for_strat = state.get("_slot_id", "")\n        strategies = get_strategies(worker_id, slot_id=_slot_id_for_strat)\n        if strategies:\n            context += strategies + "\\n\\n"\n            print(f"[STRATEGY] 🏆 {worker_id}: стратегии загружены ({len(strategies)} симв.)")\n    # ══ end Strategy Registry ══\n\n    # ══ Cultural Field — культура цеха из данных Демона (Этап 8 v2) ══\n    if _CULTURE_ENABLED:\n        try:\n            _culture_slot = state.get("_slot_id", "")\n            if _culture_slot:\n                _tracker = CulturalFieldTracker()\n                _culture_ctx = _tracker.format_field_for_prompt(_culture_slot)\n                if _culture_ctx:\n                    context += _culture_ctx + "\\n\\n"\n                    print(f"[CULTURE] 🧬 {worker_id}: культура цеха {_culture_slot} загружена")\n        except Exception as _cult_err:\n            print(f"[CULTURE] {worker_id}: {_cult_err}")\n    # ══ end Cultural Field ══'


def apply_patch():
    if not TARGET.exists():
        print(f"[PATCH] Файл не найден: {TARGET}")
        return False

    content = TARGET.read_text(encoding="utf-8")

    if OLD_BLOCK not in content:
        print("[PATCH] Блок для замены не найден — возможно уже применён?")
        return False

    bak = TARGET.with_suffix(".bak_sprint22")
    shutil.copy2(TARGET, bak)
    print(f"[PATCH] Бэкап: {bak}")

    new_content = content.replace(OLD_BLOCK, NEW_BLOCK, 1)
    TARGET.write_text(new_content, encoding="utf-8")
    print("[PATCH] pipeline.py обновлён — культура цеха в контексте агентов")

    import subprocess
    result = subprocess.run(
        ["python", "-m", "py_compile", str(TARGET)],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        print("[PATCH] Синтаксис OK")
        return True
    print(f"[PATCH] Синтаксис ERROR:\n{result.stderr}")
    shutil.copy2(bak, TARGET)
    return False


if __name__ == "__main__":
    apply_patch()
