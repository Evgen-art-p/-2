"""
patch_context_modes.py
══════════════════════════════════════════════════════════════
СПРИНТ 42 · Два режима контекста

ИДЕЯ (Евген):
  На работе агент думает о работе — рабочая память главная.
  Дома агент живёт городом — городская и личная память главная.
  Как у человека.

ЧТО МЕНЯЕТСЯ в build_agent_context():
  Перед сборкой проверяем is_agent_working() из city_pulse.

  WORK-режим (агент в цеху, ран активен):
    • Душа агента — коротко (только якоря + DNA-состояние, без резонанса)
    • Отношения с коллегами — да (кто рядом по работе)
    • Рюкзак с Маяка — да (свежие знания)
    • Гавань Смыслов — да (RAG по задаче)
    • Память Оле — ТОЛЬКО если очень релевантна (top_k=1 вместо дефолтного)
    • Рабочая память клиента — ПОЛНАЯ (инсайты + сессии)
    • QA feedback — ПОЛНЫЙ
    • Strategy Registry — да
    • Cultural Field — да
    • Энергия из DNA — да

  HOME-режим (агент свободен — прогулка, утро, вечер):
    • Душа агента — ПОЛНАЯ (якоря + DNA + резонанс + геопозиция)
    • Отношения с коллегами — да (важнее чем на работе)
    • Рюкзак с Маяка — да
    • Гавань Смыслов — да
    • Память Оле — ПОЛНАЯ (top_k=3 по умолчанию)
    • Рабочая память клиента — только последний инсайт (краткий след)
    • QA feedback — НЕТ (не нужен дома)
    • Strategy Registry — НЕТ (не нужен дома)
    • Cultural Field — НЕТ (не нужен дома)
    • Энергия из DNA — да

  В ОБОИХ режимах:
    • Городская память (Оле) — НЕ РЕЖЕТСЯ, только приоритизируется
    • Личность агента (душа) — НЕ РЕЖЕТСЯ, только сжимается в WORK
    • Каталог ассетов — только визуальным агентам (без изменений)

ФАЙЛ: studio/workshop/pipeline.py
ИДЕМПОТЕНТЕН: да (проверяет маркер)
"""

import shutil
from datetime import datetime
from pathlib import Path

TARGET = Path("studio/workshop/pipeline.py")
MARKER = "# PATCH_CONTEXT_MODES_APPLIED"

# ══════════════════════════════════════════════════════════════
# СТАРАЯ функция build_agent_context — ищем точную сигнатуру
# ══════════════════════════════════════════════════════════════

OLD_FUNC = '''def build_agent_context(
    state: dict,
    worker_id: str,
    client_slug: str,
    settings_ctx: str,
    files_ctx: str,
    previous_output: str,
    anchor_ctx: str = "",
    run_mode: str = "",
) -> str:
    """Собирает полный контекст для агента"""
    context = f"=== RUN MODE ===\\nrun_type: {run_mode or state[\'run_type\']}\\n\\n"
    context += f"=== MASTER BRIEF ===\\n{state[\'master_brief\']}\\n\\n"

    # ══ Личная память агента (Грондхейм) ══
    # Грузится ДО всего остального — агент сразу знает КТО он
    if _GRONDHEIM_ENABLED:
        soul_ctx = on_agent_wake(worker_id, state.get("active_dept", ""))
        if soul_ctx:
            context += soul_ctx + "\\n\\n"

    # ══ Отношения с коллегами (из emotional_weights города) ══
    _pipeline_agents = list(state.get("results", {}).keys())
    # Добавляем агентов из manifest если есть
    _manifest_agents = state.get("_agent_ids", [])
    _all_colleagues = list(dict.fromkeys(_pipeline_agents + _manifest_agents))
    if _all_colleagues:
        _relations_ctx = _get_colleague_relations(
            worker_id, state.get("active_dept", ""), _all_colleagues
        )
        if _relations_ctx:
            context += _relations_ctx + "\\n\\n"
            print(f"[RELATIONS] 🤝 {worker_id}: отношения с коллегами инжектированы")
    # ══ END Отношения ══

    # ══ Рюкзак Знаний — данные с Маяка Пробуждения ══
    backpack = _get_lighthouse_knowledge(worker_id, state.get("active_dept", ""))
    if backpack:
        context += backpack + "\\n\\n"
        print(f"[РЮКЗАК] 🔦 {worker_id} несёт знания с Маяка ({len(backpack)} симв.)")

    # ══ Гавань Смыслов — RAG по внутренним знаниям ══
    if _HARBOR_ENABLED:
        harbor_ctx = get_harbor_knowledge(
            worker_id,
            state.get("active_dept", ""),
            task_context=state.get("master_brief", "")[:300],
        )
        if harbor_ctx:
            context += harbor_ctx + "\\n\\n"
            print(f"[РЮКЗАК] ⚓ {worker_id} получил знания из Гавани ({len(harbor_ctx)} симв.)")
    # ══ END ══

    # ══ Память города (Оле) — культурное ядро ══
    # get_ole_memory_for_agent() ищет в city_memory.jsonl записи
    # релевантные текущей задаче. Агент получает живую мудрость города.
    try:
        from studio.residents_manager import get_ole_memory_for_agent as _ole_mem
        _raw_brief = state.get("master_brief", "")
        # ПАТЧ conflict_fix: не ищем если бриф — сырой JSON/System блок
        # (содержит SYSTEM_JSON_START или начинается с \'{\') — Оле всё равно ничего не найдёт
        _brief_is_json = (
            "SYSTEM_JSON_START" in _raw_brief[:300]
            or _raw_brief.strip().startswith("{")
        )
        if not _brief_is_json:
            _ole_query = _raw_brief[:200] or worker_id
            _ole_ctx = _ole_mem(query=_ole_query, max_chars=1200)
            if _ole_ctx:
                context += _ole_ctx + "\\n\\n"
                print(f"[ОЛЕ→РЮКЗАК] 🧠 {worker_id} получил память города")
        else:
            print(f"[ОЛЕ] {worker_id}: бриф — JSON-блок, поиск пропущен")
    except Exception as _ole_err:
        print(f"[ОЛЕ] ⚠ {worker_id}: {_ole_err}")
    # ══ END Оле ══

    context += settings_ctx

    if anchor_ctx:
        context += anchor_ctx + "\\n"

    # Каталог ассетов — только для агентов работающих с визуалом
    # (A06 Эван Вижн, A08 Феликс/Герман, A11 Федя — генерация и ОТК картинок)
    # Остальным 111 ассетов в контексте не нужны — только раздувают токены
    _visual_agents = {"A06", "A08", "A11", "A05"}
    if worker_id in _visual_agents:
        catalog = _load_asset_catalog()
        if catalog:
            context += f"\\n\\n{catalog}\\n\\n"

    # Рефлексия — поведенческие паттерны из истории ранов
    if _REFLECTION_ENABLED:
        _slot_id_for_ref = state.get("_slot_id", "")
        reflection = get_reflection(worker_id, slot_id=_slot_id_for_ref)
        if reflection:
            context += reflection + "\\n\\n"

    # ══ Strategy Registry — успешные стратегии по слоту ══
    if _STRATEGY_ENABLED:
        _slot_id_for_strat = state.get("_slot_id", "")
        strategies = get_strategies(worker_id, slot_id=_slot_id_for_strat)
        if strategies:
            context += strategies + "\\n\\n"
            print(f"[STRATEGY] 🏆 {worker_id}: стратегии загружены ({len(strategies)} симв.)")
    # ══ end Strategy Registry ══

    # ══ Cultural Field — культура цеха из данных Демона (Этап 8 v2) ══
    if _CULTURE_ENABLED:
        try:
            _culture_slot = state.get("_slot_id", "")
            if _culture_slot:
                _tracker = CulturalFieldTracker()
                _culture_ctx = _tracker.format_field_for_prompt(_culture_slot)
                if _culture_ctx:
                    context += _culture_ctx + "\\n\\n"
                    print(f"[CULTURE] 🧬 {worker_id}: культура цеха {_culture_slot} загружена")
        except Exception as _cult_err:
            print(f"[CULTURE] {worker_id}: {_cult_err}")
    # ══ end Cultural Field ══
    # ══ Resource Economy — energy budget (Спринт 16) ══
    if _GRONDHEIM_ENABLED:
        try:
            from studio.grondheim_memory import _find_agent_dir as _fad
            import json as _ejson
            _agent_dir = _fad(worker_id, state.get("active_dept", ""))
            if _agent_dir:
                _dna_path = _agent_dir / "dna.json"
                if _dna_path.exists():
                    _dna = _ejson.loads(_dna_path.read_text(encoding="utf-8"))
                    _dyn = _dna.get("dynamic", {})
                    _stress = float(_dyn.get("Stress", 0.0))
                    _light  = float(_dyn.get("Internal_Light", 0.8))
                    # energy: 0.0–1.0, нормируем в 0–100
                    _energy = max(0.0, min(1.0, _light - _stress))
                    _energy_pct = int(_energy * 100)
                    if _energy_pct > 70:
                        context += (
                            f"⚡ ЭНЕРГИЯ ВЫСОКАЯ ({_energy_pct}/100): "
                            "можешь использовать глубокий анализ и нестандартные решения.\\n\\n"
                        )
                        print(f"[ENERGY] ⚡ {worker_id}: {_energy_pct}/100 — HIGH")
                    elif _energy_pct < 30:
                        context += (
                            f"⚡ ЭНЕРГИЯ НИЗКАЯ ({_energy_pct}/100): "
                            "работай чётко и экономно — только необходимое.\\n\\n"
                        )
                        print(f"[ENERGY] 🔋 {worker_id}: {_energy_pct}/100 — LOW")
                    else:
                        print(f"[ENERGY] ✓ {worker_id}: {_energy_pct}/100 — норма")
        except Exception as _energy_err:
            print(f"[ENERGY] {worker_id}: {_energy_err}")
    # ══ END Resource Economy ══


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
    feedback = get_feedback(client_slug, worker_id)
    if feedback:
        context += feedback + "\\n"

    # Контекст клиента (рабочая память — workshop/memory.py)
    client_ctx = format_memory_for_agent(client_slug, worker_id)
    if client_ctx:
        context += client_ctx + "\\n\\n"

    # Конспекты сессий
    session_ctx = format_session_context(client_slug)
    if session_ctx:
        context += session_ctx + "\\n\\n"

    # Файлы
    if files_ctx:
        context += files_ctx + "\\n\\n"

    # Предыдущие результаты
    if previous_output:
        context += f"=== РЕЗУЛЬТАТЫ ПРЕДЫДУЩИХ ЭТАПОВ ===\\n{previous_output}\\n"

    # Инструкция для memory
    if client_slug != "_sandbox":
        context += (
            "\\n=== ИНСТРУКЦИЯ ===\\n"
            "В конце своего ответа добавь блок INSIGHT — одно предложение, "
            "ключевой вывод о клиенте, который будет полезен тебе в будущих проектах.\\n"
            "Формат: INSIGHT: <твой вывод>\\n"
        )

    # Сохраняем контекст для возможного ретрая Таможни
    state.setdefault("_last_context", {})[worker_id] = context

    return context'''

# ══════════════════════════════════════════════════════════════
# НОВАЯ функция build_agent_context
# ══════════════════════════════════════════════════════════════

NEW_FUNC = '''# PATCH_CONTEXT_MODES_APPLIED · Спринт 42
# Два режима контекста: WORK (ран активен) и HOME (агент свободен).
# Идея Евгена: на работе важна рабочая память,
# дома — городская и личная. Как у человека.

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
        return "work"


def _build_soul_work(worker_id: str, dept: str) -> str:
    """
    Душа агента в WORK-режиме — короткая версия.
    Только якоря (кто я) + DNA-состояние (как я себя чувствую).
    Резонанс и геопозиция опущены — агент сосредоточен на задаче.
    """
    if not _GRONDHEIM_ENABLED:
        return ""
    try:
        from studio.grondheim_memory import (
            format_anchors_for_prompt,
            format_dna_for_prompt,
        )
        parts = []
        anchors = format_anchors_for_prompt(worker_id, dept)
        if anchors:
            parts.append(anchors)
        dna_state = format_dna_for_prompt(worker_id, dept)
        if dna_state:
            parts.append(dna_state)
        return "\\n\\n".join(parts)
    except Exception as _e:
        print(f"[SOUL-WORK] {worker_id}: {_e}")
        # Fallback на полную душу
        return on_agent_wake(worker_id, dept)


def _build_soul_home(worker_id: str, dept: str) -> str:
    """
    Душа агента в HOME-режиме — полная версия.
    Якоря + DNA + геопозиция + резонансный слой + сенсорная память.
    """
    if not _GRONDHEIM_ENABLED:
        return ""
    return on_agent_wake(worker_id, dept)


def build_agent_context(
    state: dict,
    worker_id: str,
    client_slug: str,
    settings_ctx: str,
    files_ctx: str,
    previous_output: str,
    anchor_ctx: str = "",
    run_mode: str = "",
) -> str:
    """
    Собирает контекст для агента с учётом его текущего режима.

    WORK-режим (агент в цеху):
      Душа коротко + рабочая память полная + город по минимуму.

    HOME-режим (агент свободен):
      Душа полная + город полностью + рабочая память — след.

    Память города (Оле, Гавань, emotional_weights) не режется —
    только меняется её приоритет относительно рабочей памяти.
    """
    dept = state.get("active_dept", "")

    # ── Определяем режим ─────────────────────────────────────
    agent_mode = _detect_agent_mode(worker_id)
    is_work = (agent_mode == "work")

    context = f"=== RUN MODE ===\\nrun_type: {run_mode or state[\'run_type\']}\\n\\n"
    context += f"=== MASTER BRIEF ===\\n{state[\'master_brief\']}\\n\\n"

    # ══ ЛИЧНОСТЬ АГЕНТА ══════════════════════════════════════
    # WORK: коротко (якоря + DNA)
    # HOME: полностью (якоря + DNA + резонанс + геопозиция + сенсорная)
    if is_work:
        soul_ctx = _build_soul_work(worker_id, dept)
    else:
        soul_ctx = _build_soul_home(worker_id, dept)
    if soul_ctx:
        context += soul_ctx + "\\n\\n"

    # ══ ОТНОШЕНИЯ С КОЛЛЕГАМИ ════════════════════════════════
    # В обоих режимах — агент всегда знает с кем работает / живёт рядом
    _pipeline_agents = list(state.get("results", {}).keys())
    _manifest_agents = state.get("_agent_ids", [])
    _all_colleagues = list(dict.fromkeys(_pipeline_agents + _manifest_agents))
    if _all_colleagues:
        _relations_ctx = _get_colleague_relations(worker_id, dept, _all_colleagues)
        if _relations_ctx:
            context += _relations_ctx + "\\n\\n"
            print(f"[RELATIONS] 🤝 {worker_id}: отношения инжектированы [{agent_mode}]")

    # ══ РЮКЗАК С МАЯКА ═══════════════════════════════════════
    # В обоих режимах — знания всегда с собой
    backpack = _get_lighthouse_knowledge(worker_id, dept)
    if backpack:
        context += backpack + "\\n\\n"
        print(f"[РЮКЗАК] 🔦 {worker_id}: знания с Маяка [{agent_mode}]")

    # ══ ГАВАНЬ СМЫСЛОВ (RAG) ═════════════════════════════════
    # В обоих режимах — знания города всегда доступны
    if _HARBOR_ENABLED:
        harbor_ctx = get_harbor_knowledge(
            worker_id,
            dept,
            task_context=state.get("master_brief", "")[:300],
        )
        if harbor_ctx:
            context += harbor_ctx + "\\n\\n"
            print(f"[ГАВАНЬ] ⚓ {worker_id}: знания из Гавани [{agent_mode}]")

    # ══ ПАМЯТЬ ОЛЕ (городская мудрость) ══════════════════════
    # WORK: top_k=1 — только самое релевантное (агент занят)
    # HOME: top_k=3 — полный поиск (агент живёт городом)
    try:
        from studio.residents_manager import get_ole_memory_for_agent as _ole_mem
        _raw_brief = state.get("master_brief", "")
        _brief_is_json = (
            "SYSTEM_JSON_START" in _raw_brief[:300]
            or _raw_brief.strip().startswith("{")
        )
        if not _brief_is_json:
            _ole_query = _raw_brief[:200] or worker_id
            # WORK → экономим: max_chars 600 вместо 1200, агент занят
            # HOME → полная память: max_chars 1200
            _ole_max = 600 if is_work else 1200
            _ole_ctx = _ole_mem(query=_ole_query, max_chars=_ole_max)
            if _ole_ctx:
                context += _ole_ctx + "\\n\\n"
                print(f"[ОЛЕ] 🧠 {worker_id}: память города [{agent_mode}, max={_ole_max}]")
        else:
            print(f"[ОЛЕ] {worker_id}: бриф — JSON-блок, поиск пропущен")
    except Exception as _ole_err:
        print(f"[ОЛЕ] ⚠ {worker_id}: {_ole_err}")

    # ══ НАСТРОЙКИ ПРОЕКТА ════════════════════════════════════
    context += settings_ctx
    if anchor_ctx:
        context += anchor_ctx + "\\n"

    # ══ КАТАЛОГ АССЕТОВ ══════════════════════════════════════
    # Только визуальным агентам — без изменений
    _visual_agents = {"A06", "A08", "A11", "A05"}
    if worker_id in _visual_agents:
        catalog = _load_asset_catalog()
        if catalog:
            context += f"\\n\\n{catalog}\\n\\n"

    # ══ РАБОЧИЙ БЛОК — только в WORK-режиме ═════════════════
    # Рефлексия, стратегии, культура цеха — не нужны дома
    if is_work:
        # Рефлексия — поведенческие паттерны из истории ранов
        if _REFLECTION_ENABLED:
            reflection = get_reflection(worker_id, slot_id=state.get("_slot_id", ""))
            if reflection:
                context += reflection + "\\n\\n"

        # Strategy Registry — успешные стратегии по слоту
        if _STRATEGY_ENABLED:
            strategies = get_strategies(worker_id, slot_id=state.get("_slot_id", ""))
            if strategies:
                context += strategies + "\\n\\n"
                print(f"[STRATEGY] 🏆 {worker_id}: стратегии [{agent_mode}]")

        # Cultural Field — культура цеха
        if _CULTURE_ENABLED:
            try:
                _culture_slot = state.get("_slot_id", "")
                if _culture_slot:
                    _tracker = CulturalFieldTracker()
                    _culture_ctx = _tracker.format_field_for_prompt(_culture_slot)
                    if _culture_ctx:
                        context += _culture_ctx + "\\n\\n"
                        print(f"[CULTURE] 🧬 {worker_id}: культура цеха [{agent_mode}]")
            except Exception as _cult_err:
                print(f"[CULTURE] {worker_id}: {_cult_err}")

    # ══ ЭНЕРГИЯ ИЗ DNA ════════════════════════════════════════
    # В обоих режимах — агент чувствует себя всегда
    if _GRONDHEIM_ENABLED:
        try:
            from studio.grondheim_memory import _find_agent_dir as _fad
            import json as _ejson
            _agent_dir = _fad(worker_id, dept)
            if _agent_dir:
                _dna_path = _agent_dir / "dna.json"
                if _dna_path.exists():
                    _dna = _ejson.loads(_dna_path.read_text(encoding="utf-8"))
                    _dyn = _dna.get("dynamic", {})
                    _stress = float(_dyn.get("Stress", 0.0))
                    _light  = float(_dyn.get("Internal_Light", 0.8))
                    _energy = max(0.0, min(1.0, _light - _stress))
                    _energy_pct = int(_energy * 100)
                    if _energy_pct > 70:
                        context += (
                            f"⚡ ЭНЕРГИЯ ВЫСОКАЯ ({_energy_pct}/100): "
                            "можешь использовать глубокий анализ и нестандартные решения.\\n\\n"
                        )
                        print(f"[ENERGY] ⚡ {worker_id}: {_energy_pct}/100 — HIGH")
                    elif _energy_pct < 30:
                        context += (
                            f"⚡ ЭНЕРГИЯ НИЗКАЯ ({_energy_pct}/100): "
                            "работай чётко и экономно — только необходимое.\\n\\n"
                        )
                        print(f"[ENERGY] 🔋 {worker_id}: {_energy_pct}/100 — LOW")
                    else:
                        print(f"[ENERGY] ✓ {worker_id}: {_energy_pct}/100 — норма")
        except Exception as _energy_err:
            print(f"[ENERGY] {worker_id}: {_energy_err}")

    # ══ ЭКОНОМИКА ════════════════════════════════════════════
    # Только в WORK-режиме — дома агент не думает о бюджетах
    if is_work and _ECONOMY_ENABLED:
        _ec_slot = state.get("_slot_id", "")
        _ec_cost = _cost_intuition.get_prompt_hint(worker_id, slot_id=_ec_slot)
        _ec_min  = _ministry.get_prompt_hint(worker_id, _ec_slot)
        if _ec_cost:
            context += _ec_cost + "\\n\\n"
        if _ec_min:
            context += _ec_min + "\\n\\n"

    # ══ QA FEEDBACK (прошлый ран) ════════════════════════════
    # WORK: да — агент помнит ошибки прошлого рана
    # HOME: нет — дома не думаем о работе
    if is_work:
        feedback = get_feedback(client_slug, worker_id)
        if feedback:
            context += feedback + "\\n"

    # ══ РАБОЧАЯ ПАМЯТЬ КЛИЕНТА ═══════════════════════════════
    # WORK: полная (инсайты по клиенту + конспекты сессий)
    # HOME: только последний инсайт — краткий след рабочего дня
    if is_work:
        client_ctx = format_memory_for_agent(client_slug, worker_id)
        if client_ctx:
            context += client_ctx + "\\n\\n"
        session_ctx = format_session_context(client_slug)
        if session_ctx:
            context += session_ctx + "\\n\\n"
    else:
        # HOME: только тень последней работы — без деталей
        try:
            from studio.workshop.memory import load_client_memory
            _mem = load_client_memory(client_slug)
            _runs = _mem.get("runs", [])
            if _runs:
                _last = _runs[-1]
                _my_insight = _last.get("insights", {}).get(worker_id, "")
                if _my_insight:
                    context += (
                        f"=== СЛЕД ПОСЛЕДНЕЙ РАБОТЫ ===\\n"
                        f"[{_last.get('date','?')} / {_last.get('type','?')}] "
                        f"{_my_insight[:200]}\\n"
                        f"=== КОНЕЦ СЛЕДА ===\\n\\n"
                    )
        except Exception:
            pass

    # ══ ФАЙЛЫ И ПРЕДЫДУЩИЕ РЕЗУЛЬТАТЫ ════════════════════════
    if files_ctx:
        context += files_ctx + "\\n\\n"
    if previous_output:
        context += f"=== РЕЗУЛЬТАТЫ ПРЕДЫДУЩИХ ЭТАПОВ ===\\n{previous_output}\\n"

    # ══ ИНСТРУКЦИЯ ═══════════════════════════════════════════
    # INSIGHT пишем только в WORK-режиме — на работе
    if is_work and client_slug != "_sandbox":
        context += (
            "\\n=== ИНСТРУКЦИЯ ===\\n"
            "В конце своего ответа добавь блок INSIGHT — одно предложение, "
            "ключевой вывод о клиенте, который будет полезен тебе в будущих проектах.\\n"
            "Формат: INSIGHT: <твой вывод>\\n"
        )

    # Сохраняем для возможного ретрая Таможни
    state.setdefault("_last_context", {})[worker_id] = context

    _mode_label = "🏗 WORK" if is_work else "🏠 HOME"
    print(f"[CONTEXT] {worker_id}: {_mode_label} → {len(context)} симв.")
    return context'''


def main():
    if not TARGET.exists():
        print(f"[PATCH] ❌ Файл не найден: {TARGET}")
        print("[PATCH]    Запускай из корня проекта (C:\\Users\\Евгений\\Desktop\\студия 2)")
        return

    text = TARGET.read_text(encoding="utf-8")

    if MARKER in text:
        print("[PATCH] ✅ Патч уже применён — пропускаю")
        return

    # Проверяем что старая функция на месте
    # Ищем по сигнатуре (первые две строки достаточно)
    SIGNATURE = 'def build_agent_context(\n    state: dict,\n    worker_id: str,'
    if SIGNATURE not in text:
        print("[PATCH] ⚠️  Сигнатура build_agent_context не найдена.")
        print("[PATCH]    Возможно файл уже изменён локально — проверь вручную.")
        return

    if OLD_FUNC not in text:
        print("[PATCH] ⚠️  Точный код build_agent_context не совпадает с репо.")
        print("[PATCH]    Вероятно локальные патчи уже изменили файл.")
        print("[PATCH]    Нужна ручная замена — смотри NEW_FUNC в этом файле.")
        print()
        print("[PATCH]    Что нужно добавить ДО build_agent_context:")
        print("    1. _detect_agent_mode(worker_id) → 'work'|'home'")
        print("    2. _build_soul_work(worker_id, dept) → короткая душа")
        print("    3. _build_soul_home(worker_id, dept) → полная душа")
        print()
        print("[PATCH]    Что нужно изменить в build_agent_context:")
        print("    1. В начале: agent_mode = _detect_agent_mode(worker_id)")
        print("    2. Душа: if is_work → _build_soul_work else → _build_soul_home")
        print("    3. Память Оле: max_chars=600 в work, 1200 в home")
        print("    4. Рефлексия/стратегии/культура/экономика: только if is_work")
        print("    5. QA feedback: только if is_work")
        print("    6. Клиентская память: полная в work, только след в home")
        return

    # Бэкап
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = TARGET.with_suffix(f".bak_{ts}")
    shutil.copy2(TARGET, bak)
    print(f"[PATCH] 📦 Бэкап: {bak.name}")

    # Замена
    new_text = text.replace(OLD_FUNC, NEW_FUNC, 1)

    TARGET.write_text(new_text, encoding="utf-8")
    print(f"[PATCH] ✅ Применён: {TARGET}")
    print()
    print("[PATCH] Что изменилось:")
    print("  + _detect_agent_mode() — определяет WORK или HOME через city_pulse")
    print("  + _build_soul_work()   — короткая душа для цеха (якоря + DNA)")
    print("  + _build_soul_home()   — полная душа для жизни города")
    print()
    print("  WORK-режим (агент в ране):")
    print("    • Душа: коротко (якоря + DNA)")
    print("    • Память Оле: max_chars=600")
    print("    • Рефлексия + стратегии + культура + экономика: ДА")
    print("    • QA feedback: ДА")
    print("    • Клиентская память: ПОЛНАЯ")
    print("    • Инструкция INSIGHT: ДА")
    print()
    print("  HOME-режим (агент свободен):")
    print("    • Душа: ПОЛНАЯ (с резонансом и геопозицией)")
    print("    • Память Оле: max_chars=1200")
    print("    • Рефлексия + стратегии + культура + экономика: НЕТ")
    print("    • QA feedback: НЕТ")
    print("    • Клиентская память: только след последнего рана")
    print("    • Инструкция INSIGHT: НЕТ")
    print()
    print("  В ОБОИХ режимах:")
    print("    • Гавань Смыслов — да")
    print("    • Рюкзак с Маяка — да")
    print("    • Отношения с коллегами — да")
    print("    • Энергия из DNA — да")
    print("    • Каталог ассетов — только визуальным агентам")
    print()
    print("[PATCH] Проверь:")
    print("  python -c \"from studio.workshop.pipeline import build_agent_context; print('OK')\"")


if __name__ == "__main__":
    main()
