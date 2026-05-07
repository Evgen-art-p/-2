#!/usr/bin/env python3
# patch_strategy_registry.py — Интеграция Strategy Registry
# Студия «Шесть Пальцев» · 2026
#
# ШАГ 1: Положи strategy_registry.py в папку studio/
# ШАГ 2: Запусти этот скрипт из корня проекта:
#         python patch_strategy_registry.py
#
# Затрагивает 1 файл:
#   studio/workshop/pipeline.py — подключает стратегии в контекст агента
#                                 и записывает победы после QA

import shutil
from pathlib import Path
from datetime import datetime

SUFFIX = ".bak_strategy"
DRY_RUN = False


def backup(path: Path):
    bak = path.with_suffix(path.suffix + SUFFIX)
    shutil.copy2(path, bak)
    print(f"  📦 Бэкап: {bak.name}")


def patch_file(path: Path, old: str, new: str, description: str) -> bool:
    if not path.exists():
        print(f"  ❌ Файл не найден: {path}")
        return False

    content = path.read_text(encoding="utf-8")

    if old not in content:
        print(f"  ⚠️  Паттерн не найден ({description}) — возможно уже запатчено")
        return False

    if DRY_RUN:
        print(f"  🔍 [DRY RUN] Нашёл паттерн: {description}")
        return True

    backup(path)
    new_content = content.replace(old, new, 1)
    path.write_text(new_content, encoding="utf-8")
    print(f"  ✅ {description}")
    return True


def check_strategy_registry_exists():
    """Проверяем что strategy_registry.py уже скопирован в studio/"""
    path = Path("studio/strategy_registry.py")
    if not path.exists():
        print("\n❌ СТОП! Файл studio/strategy_registry.py не найден.")
        print("   Сначала скопируй strategy_registry.py в папку studio/")
        print("   Потом запускай этот патч снова.")
        return False
    print("  ✅ studio/strategy_registry.py найден")
    return True


def patch_pipeline():
    """
    Патчим pipeline.py в двух местах:

    1. Подключение модуля (импорт) — в блоке try/except в начале файла
    2. build_agent_context() — инжект стратегий в контекст агента
    3. process_agent_result() — запись победы после QA
    """
    path = Path("studio/workshop/pipeline.py")
    print(f"\n[1/1] Патчим {path}")

    # ── ПАТЧ A: импорт Strategy Registry ──
    patch_file(
        path,
        old=(
            '# Feedback loop — оценки от Артура\n'
            'try:\n'
            '    from studio.agent_feedback import get_feedback, save_feedback\n'
            'except ImportError:\n'
            '    def get_feedback(client_slug, worker_id): return ""\n'
            '    def save_feedback(client_slug, arthur_result): pass'
        ),
        new=(
            '# Feedback loop — оценки от Артура\n'
            'try:\n'
            '    from studio.agent_feedback import get_feedback, save_feedback\n'
            'except ImportError:\n'
            '    def get_feedback(client_slug, worker_id): return ""\n'
            '    def save_feedback(client_slug, arthur_result): pass\n'
            '\n'
            '# ══ Strategy Registry — банк успешных стратегий по слотам ══\n'
            'try:\n'
            '    from studio.strategy_registry import get_strategies, record_strategy\n'
            '    _STRATEGY_ENABLED = True\n'
            '    print("[STRATEGY] 🏆 Strategy Registry подключён")\n'
            'except ImportError:\n'
            '    _STRATEGY_ENABLED = False\n'
            '    def get_strategies(agent_id, slot_id=""): return ""\n'
            '    def record_strategy(**kwargs): pass'
        ),
        description='Импорт Strategy Registry добавлен',
    )

    # ── ПАТЧ B: инжект стратегий в build_agent_context() ──
    # Вставляем ПОСЛЕ блока рефлексии — стратегии идут следующим слоем
    patch_file(
        path,
        old=(
            '    # Рефлексия — поведенческие паттерны из истории ранов\n'
            '    if _REFLECTION_ENABLED:\n'
            '        _slot_id_for_ref = state.get("_slot_id", "")\n'
            '        reflection = get_reflection(worker_id, slot_id=_slot_id_for_ref)\n'
            '        if reflection:\n'
            '            context += reflection + "\\n\\n"'
        ),
        new=(
            '    # Рефлексия — поведенческие паттерны из истории ранов\n'
            '    if _REFLECTION_ENABLED:\n'
            '        _slot_id_for_ref = state.get("_slot_id", "")\n'
            '        reflection = get_reflection(worker_id, slot_id=_slot_id_for_ref)\n'
            '        if reflection:\n'
            '            context += reflection + "\\n\\n"\n'
            '\n'
            '    # ══ Strategy Registry — успешные стратегии по слоту ══\n'
            '    if _STRATEGY_ENABLED:\n'
            '        _slot_id_for_strat = state.get("_slot_id", "")\n'
            '        strategies = get_strategies(worker_id, slot_id=_slot_id_for_strat)\n'
            '        if strategies:\n'
            '            context += strategies + "\\n\\n"\n'
            '            print(f"[STRATEGY] 🏆 {worker_id}: стратегии загружены ({len(strategies)} симв.)")\n'
            '    # ══ end Strategy Registry ══'
        ),
        description='Инжект стратегий добавлен в build_agent_context()',
    )

    # ── ПАТЧ C: запись стратегии после QA-рана ──
    # Вставляем ПОСЛЕ _sync_feedback_scores_to_dna — когда уже знаем оценки
    patch_file(
        path,
        old=(
            '        # ══ SYNC: реальные оценки QA → DNA агентов ══\n'
            '        _sync_feedback_scores_to_dna(client_slug, state.get("active_dept", ""))\n'
            '        # ══ REFLECTION: пересчитываем паттерны если пришло время ══\n'
            '        if _REFLECTION_ENABLED:\n'
            '            maybe_rebuild()'
        ),
        new=(
            '        # ══ SYNC: реальные оценки QA → DNA агентов ══\n'
            '        _sync_feedback_scores_to_dna(client_slug, state.get("active_dept", ""))\n'
            '        # ══ STRATEGY REGISTRY: записываем победы по слотам ══\n'
            '        if _STRATEGY_ENABLED:\n'
            '            _record_winning_strategies(state, client_slug)\n'
            '        # ══ REFLECTION: пересчитываем паттерны если пришло время ══\n'
            '        if _REFLECTION_ENABLED:\n'
            '            maybe_rebuild()'
        ),
        description='Вызов _record_winning_strategies() добавлен после QA',
    )

    # ── ПАТЧ D: добавляем функцию _record_winning_strategies() ──
    # Вставляем после _sync_feedback_scores_to_dna()
    patch_file(
        path,
        old='async def summarize_session(',
        new=(
            'def _record_winning_strategies(state: dict, client_slug: str):\n'
            '    """\n'
            '    Читает feedback.json и записывает стратегии победивших агентов\n'
            '    в Strategy Registry.\n'
            '    Вызывается один раз в конце рана после QA.\n'
            '    """\n'
            '    from pathlib import Path as _Path\n'
            '    import json as _json\n'
            '\n'
            '    slot_id = state.get("_slot_id", "")\n'
            '    run_type = state.get("run_type", "")\n'
            '\n'
            '    feedback_path = _Path("clients") / client_slug / "feedback.json"\n'
            '    if not feedback_path.exists():\n'
            '        return\n'
            '\n'
            '    try:\n'
            '        feedback = _json.loads(feedback_path.read_text(encoding="utf-8"))\n'
            '    except Exception as e:\n'
            '        print(f"[STRATEGY] Не удалось прочитать feedback: {e}")\n'
            '        return\n'
            '\n'
            '    agents_data = feedback.get("agents", {})\n'
            '    results = state.get("results", {})\n'
            '\n'
            '    for agent_id, fb_data in agents_data.items():\n'
            '        score = fb_data.get("score", 0.0)\n'
            '        problems = fb_data.get("problems", [])\n'
            '\n'
            '        # Берём краткое резюме из результата агента\n'
            '        result_data = results.get(agent_id, {})\n'
            '        if isinstance(result_data, dict):\n'
            '            summary = result_data.get("text", "")[:300]\n'
            '        else:\n'
            '            summary = str(result_data)[:300]\n'
            '\n'
            '        if not summary:\n'
            '            continue\n'
            '\n'
            '        record_strategy(\n'
            '            agent_id=agent_id,\n'
            '            slot_id=slot_id,\n'
            '            score=score,\n'
            '            result_summary=summary,\n'
            '            run_type=run_type,\n'
            '            client_slug=client_slug,\n'
            '            problems=problems,\n'
            '        )\n'
            '\n'
            '\n'
            'async def summarize_session('
        ),
        description='Функция _record_winning_strategies() добавлена в pipeline.py',
    )


def main():
    print("=" * 55)
    print("  ПАТЧ: Strategy Registry интеграция")
    print(f"  Режим: {'DRY RUN (файлы не меняются)' if DRY_RUN else 'БОЕВОЙ'}")
    print(f"  Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 55)

    if not Path("studio").exists():
        print("\n❌ Папка 'studio' не найдена.")
        print("   Запускай из корневой папки проекта!")
        return

    # Проверяем что strategy_registry.py на месте
    if not check_strategy_registry_exists():
        return

    patch_pipeline()

    print("\n" + "=" * 55)
    if DRY_RUN:
        print("  ✅ DRY RUN завершён — файлы НЕ изменены")
    else:
        print("  ✅ ПАТЧ ПРИМЕНЁН")
        print()
        print("  Бэкапы:")
        print("    studio/workshop/pipeline.py.bak_strategy")
        print()
        print("  Что работает теперь:")
        print("  • После рана с оценкой >= 8 → стратегия записывается")
        print("  • В следующем ране в том же слоте → агент получает подсказку")
        print("  • После 3 побед в разных слотах → стратегия становится глобальной")
        print()
        print("  Файл данных: studio/strategy_registry.json")
        print("  (создастся автоматически после первого успешного рана)")
    print("=" * 55)


if __name__ == "__main__":
    main()
