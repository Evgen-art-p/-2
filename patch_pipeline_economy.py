#!/usr/bin/env python3
"""
ПАТЧ: Интеграция economy/ в pipeline.py
Глубокое Резюме Системы — Этапы 1, 2, 6-7 замыкаются в пайплайне

Запускать из корня проекта:
    python patch_pipeline_economy.py

Что делает:
  1. Бэкапит studio/workshop/pipeline.py → pipeline.py.bak_economy
  2. Добавляет импорт economy в начало файла
  3. В build_agent_context() — вставляет cost_intuition + ministry hint
  4. В process_agent_result() — вызывает ministry.record_outcome() post-fact
     после QA (рядом с _sync_feedback_scores_to_dna)

Принцип: Министерство работает ТОЛЬКО post-fact. Никогда в runtime.
"""

import shutil
from pathlib import Path

ROOT     = Path(__file__).resolve().parent
PIPELINE = ROOT / "studio" / "workshop" / "pipeline.py"
BAK      = ROOT / "studio" / "workshop" / "pipeline.py.bak_economy"


# ─── 1. ИМПОРТ — добавляем после блока strategy_registry ───────────────────

OLD_IMPORT = "# ══ NEW: Гавань Смыслов — RAG внутренних знаний ══"

NEW_IMPORT = """\
# ══ Economy — экономический модуль (Глубокое Резюме Системы) ══
try:
    from studio.economy import cost_intuition as _cost_intuition
    from studio.economy import ministry as _ministry
    _ECONOMY_ENABLED = True
    print("[ECONOMY] 💰 Экономический модуль подключён")
except ImportError:
    _ECONOMY_ENABLED = False
    class _cost_intuition:
        @staticmethod
        def get_prompt_hint(agent_id, slot_id=None): return ""
    class _ministry:
        @staticmethod
        def get_prompt_hint(agent_id, slot_id): return ""
        @staticmethod
        def record_outcome(agent_id, slot_id, score, cost_usd): pass
# ══ END Economy ══

# ══ NEW: Гавань Смыслов — RAG внутренних знаний ══"""


# ─── 2. BUILD_AGENT_CONTEXT — вставляем ощущение после Стратегий ───────────

OLD_CONTEXT = """\
    # Обратная связь от QA (прошлый ран)
    feedback = get_feedback(client_slug, worker_id)"""

NEW_CONTEXT = """\
    # ══ Economy: Cost Intuition + Ministry (Этапы 2, 6-7) ══
    if _ECONOMY_ENABLED:
        _ec_slot = state.get("_slot_id", "")
        _ec_cost  = _cost_intuition.get_prompt_hint(worker_id, slot_id=_ec_slot)
        _ec_min   = _ministry.get_prompt_hint(worker_id, _ec_slot)
        if _ec_cost:
            context += _ec_cost + "\\n\\n"
        if _ec_min:
            context += _ec_min + "\\n\\n"
    # ══ END Economy ══

    # Обратная связь от QA (прошлый ран)
    feedback = get_feedback(client_slug, worker_id)"""


# ─── 3. PROCESS_AGENT_RESULT — ministry.record_outcome() post-fact ──────────

OLD_OUTCOME = """\
        # ══ REFLECTION: пересчитываем паттерны если пришло время ══
        if _REFLECTION_ENABLED:
            maybe_rebuild()
    # ══ END UNIVERSAL FEEDBACK ══"""

NEW_OUTCOME = """\
        # ══ REFLECTION: пересчитываем паттерны если пришло время ══
        if _REFLECTION_ENABLED:
            maybe_rebuild()
        # ══ Ministry: фиксируем исходы post-fact (Этапы 6-7) ══
        if _ECONOMY_ENABLED:
            _results_data = state.get("results", {})
            _agents_fb    = {}
            try:
                from pathlib import Path as _Path
                import json as _json
                _fb_path = _Path("clients") / client_slug / "feedback.json"
                if _fb_path.exists():
                    _agents_fb = _json.loads(_fb_path.read_text(encoding="utf-8")).get("agents", {})
            except Exception:
                pass
            _ec_slot = state.get("_slot_id", "")
            for _wid, _wdata in _agents_fb.items():
                _wscore = float(_wdata.get("score", 5.0))
                try:
                    from studio.economy import ledger as _ledger
                    _wcost = _ledger.agent_spent(_wid, slot_id=_ec_slot)
                except Exception:
                    _wcost = 0.0
                try:
                    _ministry.record_outcome(
                        agent_id=_wid,
                        slot_id=_ec_slot,
                        score=_wscore,
                        cost_usd=_wcost,
                    )
                except Exception as _me:
                    print(f"[MINISTRY] record_outcome ошибка: {_me}")
        # ══ END Ministry ══
    # ══ END UNIVERSAL FEEDBACK ══"""


# ─── ПРИМЕНЯЕМ ──────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("ПАТЧ: pipeline.py ← economy integration")
    print("=" * 60)
    print()

    if not PIPELINE.exists():
        print(f"[ERR] {PIPELINE} не найден")
        return

    src = PIPELINE.read_text(encoding="utf-8")

    # Проверяем идемпотентность
    if "_ECONOMY_ENABLED" in src:
        print("[SKIP] Патч уже применён — economy уже в pipeline.py")
        return

    errors = []

    if OLD_IMPORT not in src:
        errors.append("Не найдена точка вставки ИМПОРТА (блок Гавань)")
    if OLD_CONTEXT not in src:
        errors.append("Не найдена точка вставки в build_agent_context (feedback)")
    if OLD_OUTCOME not in src:
        errors.append("Не найдена точка вставки в process_agent_result (REFLECTION)")

    if errors:
        print("[ERR] Патч не может быть применён:")
        for e in errors:
            print(f"  • {e}")
        print()
        print("Вероятно pipeline.py изменился. Проверь вручную.")
        return

    # Бэкап
    shutil.copy2(PIPELINE, BAK)
    print(f"[BAK] pipeline.py → {BAK.name}")

    # Применяем три замены
    src = src.replace(OLD_IMPORT,   NEW_IMPORT,   1)
    src = src.replace(OLD_CONTEXT,  NEW_CONTEXT,  1)
    src = src.replace(OLD_OUTCOME,  NEW_OUTCOME,  1)

    PIPELINE.write_text(src, encoding="utf-8")
    print(f"[OK]  pipeline.py — патч применён")
    print()
    print("Что добавлено:")
    print("  build_agent_context()   ← cost_intuition + ministry hint в промпт")
    print("  process_agent_result()  ← ministry.record_outcome() post-fact после QA")
    print()
    print("Цепочка замкнута:")
    print("  ран → ledger → QA score → ministry → ощущение → промпт → ран")


if __name__ == "__main__":
    main()
