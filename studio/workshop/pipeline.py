# studio/workshop_pipeline.py — Общая логика пайплайнов
# Вынесено из ui_workshop.py — хелперы для run_pipeline и turbo_pipeline
# ══ PATCHED: grondheim_memory integration ══

import re
import json
import asyncio
from studio.llm import chat, chat_with_images, stress_to_temperature
from studio.modules_registry import get_worker_prompt, get_worker_info, get_worker_knowledge
from studio.workshop.utils import (
    _clean_response, _validate_asset_ids,
    parse_agent_response, _collect_images_for_vision
)
from studio.workshop.memory import (
    append_to_memory, format_memory_for_agent, format_session_context,
    save_session_summary
)
from studio.workshop.assets import _load_asset_catalog

# ══ Contract Validator — Таможня Контракта ══
# ПАТЧ timer_contract: временно отключён — ключи контракта не совпадают
# с реальным output агентов, вызывает ретраи (+30 сек каждый), гробит WS.
# Включить обратно после синхронизации CHAIN_CONTRACT.md с промптами агентов.
_CONTRACT_ENABLED = False
def _contract_validate(agent_id, my_output, dept=""): return []
def _contract_retry_prompt(errors, agent_id): return ""
print("[CONTRACT] Таможня Контракта — ПАУЗА (ключи не синхронизированы)")
# ══ END Contract ══


# Reflection Engine — поведенческие паттерны из истории ранов
try:
    from studio.reflection import get_reflection, maybe_rebuild
    _REFLECTION_ENABLED = True
    print("[REFLECTION] 🧠 Reflection Engine подключён")
except ImportError:
    _REFLECTION_ENABLED = False
    def get_reflection(agent_id): return ""
    def maybe_rebuild(force=False): pass

# Feedback loop — оценки от Артура
try:
    from studio.agent_feedback import get_feedback, save_feedback
except ImportError:
    def get_feedback(client_slug, worker_id): return ""
    def save_feedback(client_slug, arthur_result): pass

# ══ Strategy Registry — банк успешных стратегий по слотам ══
try:
    from studio.strategy_registry import get_strategies, record_strategy
    _STRATEGY_ENABLED = True
    print("[STRATEGY] 🏆 Strategy Registry подключён")
except ImportError:
    _STRATEGY_ENABLED = False
    def get_strategies(agent_id, slot_id=""): return ""
    def record_strategy(**kwargs): pass

# ══ Culture Field (Этап 10) — Cultural Feedback Loop ══
try:
    from studio.culture.field_tracker import CulturalFieldTracker
    _CULTURE_ENABLED = True
    print("[CULTURE] 🧬 Cultural Field Tracker подключён")
except ImportError:
    _CULTURE_ENABLED = False
    print("[CULTURE] ⚠ field_tracker не найден — работаем без культуры")
# ══ END Culture ══

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

# ══ NEW: Гавань Смыслов — RAG внутренних знаний ══
try:
    from studio.harbor_of_meanings import get_harbor_knowledge
    _HARBOR_ENABLED = True
    print("[ГАВАНЬ] ⚓ Рюкзак Знаний v2 (RAG) подключён")
except ImportError:
    _HARBOR_ENABLED = False
    print("[ГАВАНЬ] ⚠ harbor_of_meanings.py не найден — работаем без Гавани")
    def get_harbor_knowledge(worker_id, dept, task_context=""): return ""
# ══ END ГАВАНЬ ══

# ══ NEW: Грондхейм — личная память агента ══
try:
    from studio.grondheim_memory import (
        on_agent_wake,
        on_agent_done,
        on_agents_interact,
        sync_to_dna,
        record_sensory_event,
    )
    _GRONDHEIM_ENABLED = True
    print("[GRONDHEIM] Память агентов подключена")
except ImportError:
    _GRONDHEIM_ENABLED = False
    print("[GRONDHEIM] grondheim_memory.py не найден — работаем без личной памяти")
    def on_agent_wake(agent_id, dept=""): return ""
    def on_agent_done(agent_id, result_summary, quality_score=0.5, dept=""): pass
    def on_agents_interact(a, b, interaction_type="collaboration", quality=0.5, note="", dept=""): pass
    def sync_to_dna(agent_id, event, intensity=0.5, dept=""): pass
    def record_sensory_event(**kwargs): pass
# ══ END NEW ══
# ══ NEW: Квантовые прогулки — автотриггер после рана ══
_QUANTUM_WALK_ENABLED = False
try:
    from studio.city_walker import run_city_walk_evening as _run_evening_walk
    _QUANTUM_WALK_ENABLED = True
    print("[CITY] 🌆 Квантовые прогулки подключены (автотриггер)")
except ImportError:
    async def _run_evening_walk(**kwargs): return []
# ══ END ══


# ══ Рюкзак Знаний: читаем что агент принёс с Маяка ══

def _get_lighthouse_knowledge(worker_id: str, dept: str) -> str:
    """Читает Рюкзак Знаний — записи с Маяка из sensory_memory.

    Если агент недавно ходил на Маяк Пробуждения, его записи
    с тегом 'чистый_смысл' попадают в контекст при следующей работе.
    Знания приходят из города — не из хардкода.
    """
    if not _GRONDHEIM_ENABLED:
        return ""

    try:
        from studio.grondheim_memory import load_sensory
        sensory = load_sensory(worker_id, dept)
        entries = sensory.get("entries", [])

        lighthouse_entries = []
        for entry in entries[-20:]:
            tags = entry.get("tags", [])
            feeling = entry.get("feeling", "") or entry.get("content", "")
            location = entry.get("location", "")

            is_lighthouse = (
                "чистый_смысл" in tags
                or "маяк" in tags
                or "маяк" in location.lower()
            )
            if is_lighthouse and feeling:
                lighthouse_entries.append(feeling[:300])

        if not lighthouse_entries:
            return ""

        lines = ["=== 🔦 РЮКЗАК ЗНАНИЙ (с Маяка Пробуждения) ==="]
        for i, entry in enumerate(lighthouse_entries[-3:], 1):
            lines.append(f"  {i}. {entry}")
        lines.append("Используй эти данные если они релевантны текущей задаче.")
        lines.append("=== КОНЕЦ РЮКЗАКА ===")
        return "\n".join(lines)

    except Exception as e:
        print(f"[РЮКЗАК] ⚠ {worker_id}: {e}")
        return ""


def _get_colleague_relations(worker_id: str, dept: str, agent_ids: list) -> str:
    """
    Читает emotional_weights агента к коллегам по текущему цеху.
    Возвращает текстовый блок для инжекта в контекст — или пустую строку.

    Правило трёх каналов: только READ, никакой записи в DNA.
    Это информационный инжект — агент знает с кем работает сегодня.

    Пороги:
      Тёплый союз:   warmth > 0.65 AND trust > 0.65
      Холодок:       warmth < 0.35
      Соперничество: rivalry > 0.50
      Уважение:      respect > 0.75
    """
    if not _GRONDHEIM_ENABLED:
        return ""
    if not agent_ids:
        return ""

    try:
        from studio.grondheim_memory import load_emotional_weights
    except ImportError:
        return ""

    try:
        weights = load_emotional_weights(worker_id, dept)
    except Exception:
        return ""

    if not weights:
        return ""

    lines = []
    for colleague_id in agent_ids:
        if colleague_id == worker_id:
            continue

        rel = weights.get(colleague_id) or weights.get(colleague_id.upper())
        if not rel:
            continue

        warmth  = float(rel.get("warmth",  0.5))
        trust   = float(rel.get("trust",   0.5))
        respect = float(rel.get("respect", 0.5))
        rivalry = float(rel.get("rivalry", 0.0))
        memory  = rel.get("memory", "")

        notes = []

        # Тёплый союз — работают слаженно
        if warmth > 0.65 and trust > 0.65:
            notes.append(f"с {colleague_id} тёплые отношения — вы слаженно работаете")
            if memory:
                notes.append(f"  (помнишь: {memory[:80]})")

        # Глубокое уважение
        elif respect > 0.75 and warmth >= 0.4:
            notes.append(f"к {colleague_id} глубокое профессиональное уважение")

        # Соперничество — не конфликт, но напряжение
        elif rivalry > 0.50:
            notes.append(
                f"с {colleague_id} есть соперничество — "
                "сосредоточься на своей задаче, не на нём"
            )

        # Холодок / напряжение
        elif warmth < 0.35:
            notes.append(
                f"с {colleague_id} сейчас напряжение — "
                "будь профессионален, не давай личному мешать работе"
            )

        lines.extend(notes)

    if not lines:
        return ""

    result = ["=== 🤝 ОТНОШЕНИЯ В ЦЕХЕ (из жизни города) ==="]
    result.extend(f"  • {line}" for line in lines)
    result.append("=== КОНЕЦ ОТНОШЕНИЙ ===")
    return "\n".join(result)


def build_settings_ctx(state: dict) -> str:
    """Формирует блок PROJECT SETTINGS для агентов"""
    return (
        f"=== PROJECT SETTINGS ===\n"
        f"Format: {state['settings']['format']}\n"
        f"Duration: {state['settings']['duration']} sec\n"
        f"Style: {state['settings']['style']}\n"
    )


def build_files_ctx(state: dict) -> str:
    """Формирует контекст загруженных файлов"""
    if not state.get("uploaded_files") or not state.get("file_processor"):
        return ""
    try:
        ctx = state["file_processor"].format_for_agent()
        if ctx.strip():
            print(f"[FILES] Контекст файлов: {len(ctx)} символов, файлов: {len(state['uploaded_files'])}")
            return ctx
    except Exception as ex:
        print(f"[FILES ERROR] {ex}")
        import traceback
        traceback.print_exc()
    return ""


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
    """Собирает полный контекст для агента"""
    context = f"=== RUN MODE ===\nrun_type: {run_mode or state['run_type']}\n\n"
    context += f"=== MASTER BRIEF ===\n{state['master_brief']}\n\n"

    # ══ Личная память агента (Грондхейм) ══
    # Грузится ДО всего остального — агент сразу знает КТО он
    if _GRONDHEIM_ENABLED:
        soul_ctx = on_agent_wake(worker_id, state.get("active_dept", ""))
        if soul_ctx:
            context += soul_ctx + "\n\n"

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
            context += _relations_ctx + "\n\n"
            print(f"[RELATIONS] 🤝 {worker_id}: отношения с коллегами инжектированы")
    # ══ END Отношения ══

    # ══ Рюкзак Знаний — данные с Маяка Пробуждения ══
    backpack = _get_lighthouse_knowledge(worker_id, state.get("active_dept", ""))
    if backpack:
        context += backpack + "\n\n"
        print(f"[РЮКЗАК] 🔦 {worker_id} несёт знания с Маяка ({len(backpack)} симв.)")

    # ══ Гавань Смыслов — RAG по внутренним знаниям ══
    if _HARBOR_ENABLED:
        harbor_ctx = get_harbor_knowledge(
            worker_id,
            state.get("active_dept", ""),
            task_context=state.get("master_brief", "")[:300],
        )
        if harbor_ctx:
            context += harbor_ctx + "\n\n"
            print(f"[РЮКЗАК] ⚓ {worker_id} получил знания из Гавани ({len(harbor_ctx)} симв.)")
    # ══ END ══

    # ══ Память города (Оле) — культурное ядро ══
    # get_ole_memory_for_agent() ищет в city_memory.jsonl записи
    # релевантные текущей задаче. Агент получает живую мудрость города.
    try:
        from studio.residents_manager import get_ole_memory_for_agent as _ole_mem
        _raw_brief = state.get("master_brief", "")
        # ПАТЧ conflict_fix: не ищем если бриф — сырой JSON/System блок
        # (содержит SYSTEM_JSON_START или начинается с '{') — Оле всё равно ничего не найдёт
        _brief_is_json = (
            "SYSTEM_JSON_START" in _raw_brief[:300]
            or _raw_brief.strip().startswith("{")
        )
        if not _brief_is_json:
            _ole_query = _raw_brief[:200] or worker_id
            _ole_ctx = _ole_mem(query=_ole_query, max_chars=1200)
            if _ole_ctx:
                context += _ole_ctx + "\n\n"
                print(f"[ОЛЕ→РЮКЗАК] 🧠 {worker_id} получил память города")
        else:
            print(f"[ОЛЕ] {worker_id}: бриф — JSON-блок, поиск пропущен")
    except Exception as _ole_err:
        print(f"[ОЛЕ] ⚠ {worker_id}: {_ole_err}")
    # ══ END Оле ══

    context += settings_ctx

    if anchor_ctx:
        context += anchor_ctx + "\n"

    # Каталог ассетов — только для агентов работающих с визуалом
    # (A06 Эван Вижн, A08 Феликс/Герман, A11 Федя — генерация и ОТК картинок)
    # Остальным 111 ассетов в контексте не нужны — только раздувают токены
    _visual_agents = {"A06", "A08", "A11", "A05"}
    if worker_id in _visual_agents:
        catalog = _load_asset_catalog()
        if catalog:
            context += f"\n\n{catalog}\n\n"

    # Рефлексия — поведенческие паттерны из истории ранов
    if _REFLECTION_ENABLED:
        _slot_id_for_ref = state.get("_slot_id", "")
        reflection = get_reflection(worker_id, slot_id=_slot_id_for_ref)
        if reflection:
            context += reflection + "\n\n"

    # ══ Strategy Registry — успешные стратегии по слоту ══
    if _STRATEGY_ENABLED:
        _slot_id_for_strat = state.get("_slot_id", "")
        strategies = get_strategies(worker_id, slot_id=_slot_id_for_strat)
        if strategies:
            context += strategies + "\n\n"
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
                    context += _culture_ctx + "\n\n"
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
                            "можешь использовать глубокий анализ и нестандартные решения.\n\n"
                        )
                        print(f"[ENERGY] ⚡ {worker_id}: {_energy_pct}/100 — HIGH")
                    elif _energy_pct < 30:
                        context += (
                            f"⚡ ЭНЕРГИЯ НИЗКАЯ ({_energy_pct}/100): "
                            "работай чётко и экономно — только необходимое.\n\n"
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
            context += _ec_cost + "\n\n"
        if _ec_min:
            context += _ec_min + "\n\n"
    # ══ END Economy ══

    # Обратная связь от QA (прошлый ран)
    feedback = get_feedback(client_slug, worker_id)
    if feedback:
        context += feedback + "\n"

    # Контекст клиента (рабочая память — workshop/memory.py)
    client_ctx = format_memory_for_agent(client_slug, worker_id)
    if client_ctx:
        context += client_ctx + "\n\n"

    # Конспекты сессий
    session_ctx = format_session_context(client_slug)
    if session_ctx:
        context += session_ctx + "\n\n"

    # Файлы
    if files_ctx:
        context += files_ctx + "\n\n"

    # ПАТЧ chain_prop: накопленный chain_data от предыдущих агентов
    # Это критично для video_long: A04 должна видеть adam_bible,
    # zack_season_structure, leo_season_breakdown из chain_data A01-A03
    _chain_acc = state.get("_chain_accumulator", {})
    if _chain_acc:
        try:
            import json as _cjson
            _chain_str = _cjson.dumps(_chain_acc, ensure_ascii=False, indent=2)
            context += (
                f"=== CHAIN DATA (от предыдущих агентов) ===\n"
                f"```json\n{_chain_str}\n```\n\n"
            )
            print(f"[CHAIN] {worker_id}: получил chain_data {list(_chain_acc.keys())}")
        except Exception as _ce:
            print(f"[CHAIN] {worker_id}: ошибка инжекта chain_data: {_ce}")

    # Предыдущие результаты
    if previous_output:
        context += f"=== РЕЗУЛЬТАТЫ ПРЕДЫДУЩИХ ЭТАПОВ ===\n{previous_output}\n"

    # Инструкция для memory
    if client_slug != "_sandbox":
        context += (
            "\n=== ИНСТРУКЦИЯ ===\n"
            "В конце своего ответа добавь блок INSIGHT — одно предложение, "
            "ключевой вывод о клиенте, который будет полезен тебе в будущих проектах.\n"
            "Формат: INSIGHT: <твой вывод>\n"
        )

    # Сохраняем контекст для возможного ретрая Таможни
    state.setdefault("_last_context", {})[worker_id] = context

    return context


async def call_agent(
    state: dict,
    worker_id: str,
    context: str,
) -> tuple[str, dict, str]:
    """
    Вызывает агента (LLM) и возвращает (human_text, meta, raw_result).
    Поддерживает vision если есть изображения.
    Temperature рассчитывается из ДНК агента (Stress + Internal_Light).
    """
    dept = state.get("active_dept", "")
    system_prompt = get_worker_prompt(worker_id, dept)
    worker_knowledge = get_worker_knowledge(worker_id, dept)
    vision_images = _collect_images_for_vision(state)

    # ══ Temperature из ДНК агента ══
    agent_temp = None
    if _GRONDHEIM_ENABLED:
        try:
            from studio.grondheim_memory import _find_agent_dir
            import json as _json
            agent_dir = _find_agent_dir(worker_id, dept)
            if agent_dir:
                dna_path = agent_dir / "dna.json"
                if dna_path.exists():
                    dna = _json.loads(dna_path.read_text(encoding="utf-8"))
                    dynamic = dna.get("dynamic", {})
                    agent_temp = stress_to_temperature(
                        stress=float(dynamic.get("Stress", 0)),
                        light=float(dynamic.get("Internal_Light", 0.8)),
                    )
                    info = get_worker_info(worker_id, dept)
                    label = info.get("label", worker_id) if info else worker_id
                    print(f"[DNA→T°] {worker_id} {label}: Stress={dynamic.get('Stress',0)} Light={dynamic.get('Internal_Light',0.8)} → temp={agent_temp}")
        except Exception as e:
            print(f"[DNA→T°] {worker_id}: не удалось — {e}")

    slot_id = state.get("_slot_id", "unknown")

    if vision_images:
        print(f"[PIPELINE] Vision для {worker_id}: {len(vision_images)} изображений")
        raw_result = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda sp=system_prompt, ctx=context, wk=worker_knowledge, vi=vision_images, t=agent_temp:
                chat_with_images(sp, ctx, images=vi, knowledge=wk, temperature=t,
                                 agent_id=worker_id, slot_id=slot_id)
        )
    else:
        raw_result = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda sp=system_prompt, ctx=context, wk=worker_knowledge, t=agent_temp:
                chat(sp, ctx, wk, temperature=t,
                     agent_id=worker_id, slot_id=slot_id)
        )

    human_text, meta = parse_agent_response(raw_result)
    human_text = _clean_response(human_text)

    return human_text, meta, raw_result


async def process_agent_result(
    state: dict,
    worker_id: str,
    human_text: str,
    meta: dict,
    raw_result: str,
    client_slug: str,
    run_date: str,
    run_type: str,
    previous_output: str,
) -> tuple[str, str]:
    """
    Обрабатывает результат агента:
    - Валидирует asset_ids
    - Извлекает INSIGHT
    - Сохраняет файл
    - Обновляет state
    - Строит previous_output для следующего агента
    - ══ NEW: Записывает в личную память + sync_to_dna ══

    Возвращает (human_text_cleaned, updated_previous_output)
    """
    info = get_worker_info(worker_id, state.get("active_dept", ""))
    label = info.get("label", worker_id) if info else worker_id

    # Защита: meta должна быть dict. Если агент не вернул JSON —
    # parse_agent_response даёт {}, но конфликтный ран может дать строку.
    if not isinstance(meta, dict):
        meta = {}

    # Валидация asset_ids
    ghost_ids = _validate_asset_ids(meta, worker_id)
    if ghost_ids:
        warn = f"⚠️ {worker_id}: галлюцинации asset_id ({len(ghost_ids)}): " + ", ".join(ghost_ids[:5])
        print(f"[VALIDATION] {warn}")

    # ══ Таможня Контракта + Auto-Retry ══
    if _CONTRACT_ENABLED:
        _cerrs = _contract_validate(worker_id, meta.get("my_output"),
                                    dept=state.get("active_dept", ""))
        if _cerrs:
            for _ce in _cerrs:
                print(f"[CONTRACT] ❌ {worker_id}: {_ce}")
            state.setdefault("_contract_violations", {})[worker_id] = _cerrs
            print(f"[CONTRACT] 🔄 {worker_id}: ретрай...")
            _retry_ctx = state.get("_last_context", {}).get(worker_id, "")
            _retry_ctx += "\n\n" + _contract_retry_prompt(_cerrs, worker_id)
            try:
                _r_human, _r_meta, _r_raw = await call_agent(state, worker_id, _retry_ctx)
                if not _contract_validate(worker_id, _r_meta.get("my_output"),
                                          dept=state.get("active_dept", "")):  # PATCH audit-sprint19 [2]
                    human_text, meta, raw_result = _r_human, _r_meta, _r_raw
                    state["_contract_violations"].pop(worker_id, None)
                    print(f"[CONTRACT] ✅ {worker_id}: ретрай успешен")
                else:
                    print(f"[CONTRACT] ⚠️ {worker_id}: ретрай не помог")
            except Exception as _re:
                print(f"[CONTRACT] ⚠️ {worker_id}: ретрай упал — {_re}")
        elif meta.get("my_output"):
            print(f"[CONTRACT] ✅ {worker_id}: ключи верны")
    # ══ END Contract ══

    # Извлекаем INSIGHT
    insight_match = re.search(r'INSIGHT:\s*(.+)', raw_result)
    if insight_match and client_slug != "_sandbox":
        append_to_memory(client_slug, run_date, run_type, worker_id, insight_match.group(1).strip())
        human_text = re.sub(r'\n*INSIGHT:\s*.+', '', human_text).strip()

    # Сохраняем файл
    if state.get("project_dir"):
        result_file = state["project_dir"] / f"{worker_id}_{label.replace(' ', '_')}.md"
        result_file.write_text(raw_result, encoding='utf-8')

    # Сохраняем в state
    state["results"][worker_id] = {
        "text": human_text,
        "meta": meta,
        "raw": raw_result
    }

    # ПАТЧ chain_prop: накапливаем chain_data по цепочке
    # A01 пишет adam_bible, A02 — zack_season_structure и т.д.
    # Каждый следующий агент должен видеть всё накопленное
    _chain_data = meta.get("chain_data", {})
    if _chain_data and isinstance(_chain_data, dict):
        _acc = state.setdefault("_chain_accumulator", {})
        for _ck, _cv in _chain_data.items():
            # Пропускаем inherit-заглушки и master_brief/history_dna
            if _cv in ("{{inherit}}", None, ""):
                continue
            if _ck in ("master_brief", "history_dna", "mode"):
                continue
            _acc[_ck] = _cv
        if _acc:
            print(f"[CHAIN] {worker_id}: chain_accumulator = {list(_acc.keys())}")

    # ПАТЧ chain_prop: накапливаем chain_data по цепочке
    # A01 пишет adam_bible, A02 — zack_season_structure и т.д.
    # Каждый следующий агент должен видеть всё накопленное
    _chain_data = meta.get("chain_data", {})
    if _chain_data and isinstance(_chain_data, dict):
        _acc = state.setdefault("_chain_accumulator", {})
        for _ck, _cv in _chain_data.items():
            # Пропускаем inherit-заглушки и master_brief/history_dna
            if _cv in ("{{inherit}}", None, ""):
                continue
            if _ck in ("master_brief", "history_dna", "mode"):
                continue
            _acc[_ck] = _cv
        if _acc:
            print(f"[CHAIN] {worker_id}: chain_accumulator = {list(_acc.keys())}")

        # ═══ STRATEGY: стратегии пишутся только через QA (реальный score) ═══
        # record_strategy вызывается в _record_winning_strategies() после QA

    # ══ Личная память агента (Грондхейм) · Спринт 21 ══
    # ПАТЧ: on_agent_done() пишет ТОЛЬКО в sensory_memory (фактологический журнал).
    # sync_to_dna() и update_profile_vector() убраны отсюда.
    # Единственный источник правды для DNA → _sync_feedback_scores_to_dna() после QA.
    if _GRONDHEIM_ENABLED:
        on_agent_done(
            agent_id=worker_id,
            result_summary=human_text[:200],
            dept=state.get("active_dept", ""),
        )

        # Межагентное взаимодействие: социальные связи (не DNA!)
        # quality здесь — нейтральный сигнал о факте передачи, не оценка.
        prev_agents = [k for k in state.get("results", {}).keys() if k != worker_id]
        if prev_agents:
            last_agent = prev_agents[-1]
            _my_out = meta.get("my_output", {}) or {}
            _compat = _my_out.get("felix_vfx", {}).get("compatibility_snapshot") \
                if worker_id == "A08" else None
            _outcome = _my_out.get("final_dna") \
                if worker_id == state.get("_qa_agent", "A12") else None
            on_agents_interact(
                agent_a=last_agent,
                agent_b=worker_id,
                interaction_type="collaboration",
                quality=0.5,  # нейтрально — реальная оценка придёт от QA
                note=f"Передача работы в пайплайне {run_type}",
                dept=state.get("active_dept", ""),
                compatibility_snapshot=_compat,
                outcome_signal=_outcome,
            )
    # ══ END Личная память ══

        # ═══ UNIVERSAL FEEDBACK ═══
    qa_agent = state.get("_qa_agent", "A12")
    
    # Запись стратегий и ministry — для КАЖДОГО агента, не только QA
    if client_slug != "_sandbox":
        _slot_id = state.get("_slot_id", "")
        _run_type = state.get("run_type", state.get("active_dept", ""))
        
        # Strategy Registry: стратегии пишутся ТОЛЬКО после QA
        # через _record_winning_strategies() с реальным score.
        # Фантомный score=7.0 убран — он отравлял Registry мусором.
        
        # Ministry: record_outcome вызывается в hooks.py финализатора
        # с реальным score (детерминированным или viral).
        # Фантомный score=7.0 убран — он давал двойные записи с мусором.
    
    # QA-специфичная логика: feedback, DNA-sync, memory_embedding, winning_strategies
    if worker_id == qa_agent and client_slug != "_sandbox":
        try:
            _slot_id_for_fb = state.get("_slot_id", "")
            _all_run_agents = list(state.get("results", {}).keys())
            save_feedback(client_slug, raw_result, slot_id=_slot_id_for_fb, agent_ids=_all_run_agents)
            print(f"[FEEDBACK] ✅ {worker_id} → feedback для {client_slug} (slot: {_slot_id_for_fb or '—'})")
        except Exception as _fb_err:
            print(f"[FEEDBACK] Ошибка: {_fb_err}")
        # _apply_qa_feedback убрана: поиск слов в тексте QA ненадёжен.
        # DNA синхронизируется через _sync_feedback_scores_to_dna
        # которая читает структурированный feedback.json.
        # ══ SYNC: реальные оценки QA → DNA агентов ══
        _sync_feedback_scores_to_dna(client_slug, state.get("active_dept", ""))
        # ══ КНИГА ЖАЛОБ И БЛАГОДАРНОСТЕЙ · Спринт 25 ══
        # Проверяем каждого агента цеха на триггер жалобы.
        # qa_agent уже известен (A05/A12/A18 из manifest).
        # Благодарности — отдельный механизм, пишется из hooks.py когда
        # один агент явно спас другого (например, A08 закрыл слабый блок A05).
        try:
            from studio.complaint_book import check_and_write_complaint
            _book_dept = state.get("active_dept", "")
            _book_qa = qa_agent  # A05 / A12 / A18 — из manifest, уже правильный
            # Читаем feedback.json чтобы знать реальные оценки
            from pathlib import Path as _P
            import json as _J
            _fb_path = _P("clients") / client_slug / "feedback.json"
            if _fb_path.exists():
                _fb_data = _J.loads(_fb_path.read_text(encoding="utf-8"))
                _agents_fb = _fb_data.get("agents", {})
                for _book_agent_id, _book_fb in _agents_fb.items():
                    if _book_agent_id == _book_qa:
                        continue  # QA сам на себя не жалуется
                    _book_score = float(_book_fb.get("score", 5.0))
                    entry = check_and_write_complaint(
                        agent_id=_book_agent_id,
                        qa_agent_id=_book_qa,
                        qa_score=_book_score,
                        dept=_book_dept,
                    )
                    if entry:
                        print(f"[BOOK] 🗡 {_book_agent_id} написал жалобу (score={_book_score})")
        except Exception as _book_err:
            print(f"[BOOK] ⚠ Книга Жалоб: {_book_err}")
        # ══ END КНИГА ══
        # ══ STRATEGY REGISTRY: записываем победы по слотам ══
        if _STRATEGY_ENABLED:
            _record_winning_strategies(state, client_slug)
        # ══ REFLECTION: пересчитываем паттерны если пришло время ══
        if _REFLECTION_ENABLED:
            maybe_rebuild()
        # ══ Memory Embedding: числа → ощущения (Этап 3) ══
        if _ECONOMY_ENABLED:
            try:
                from studio.economy import memory_embedding as _membed
                _fb_agents_scores = {
                    _wid: float(_wdata.get("score", 5.0))
                    for _wid, _wdata in _agents_fb.items()
                } if "_agents_fb" in dir() and _agents_fb else {}
                if not _fb_agents_scores:
                    # Fallback: читаем feedback напрямую
                    try:
                        from pathlib import Path as _P
                        import json as _J
                        _fp = _P("clients") / client_slug / "feedback.json"
                        if _fp.exists():
                            _fd = _J.loads(_fp.read_text(encoding="utf-8"))
                            _fb_agents_scores = {
                                _w: float(_d.get("score", 5.0))
                                for _w, _d in _fd.get("agents", {}).items()
                            }
                    except Exception:
                        pass
                if _fb_agents_scores:
                    _membed.embed_all_agents(
                        agents_scores=_fb_agents_scores,
                        slot_id=state.get("_slot_id", ""),
                        dept=state.get("active_dept", ""),
                    )
            except Exception as _emb_err:
                print(f"[EMBEDDING] Ошибка: {_emb_err}")
        # ══ END Memory Embedding ══
        # ══ АВТОТРИГГЕР: вечерняя прогулка после рана · Спринт 24 ══
        # Fire-and-forget — не блокирует пайплайн.
        # Агенты цеха идут домой своим путём пока UI уже показывает результат.
        if _QUANTUM_WALK_ENABLED:
            _dept_for_walk = state.get("active_dept", "")
            if _dept_for_walk:
                try:
                    asyncio.create_task(
                        _run_evening_walk(
                            workshops=[_dept_for_walk],
                            max_agents=0,  # все агенты цеха
                        )
                    )
                    print(f"[CITY] 🌆 Вечерняя прогулка запущена для цеха: {_dept_for_walk}")
                except Exception as _walk_err:
                    print(f"[CITY] ⚠ Автотриггер прогулки: {_walk_err}")
        # ══ END АВТОТРИГГЕР ══

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
                    if not state.get("async_scoring", False):  # patch_ministry_qa
                        _ministry.record_outcome(
                            agent_id=_wid,
                            slot_id=_ec_slot,
                            score=_wscore,
                            cost_usd=_wcost,
                        )
                except Exception as _me:
                    print(f"[MINISTRY] record_outcome ошибка: {_me}")
        # ══ END Ministry ══
    # ══ END UNIVERSAL FEEDBACK ══

    # Строим chain для следующего агента
    my_output = meta.get("my_output", {})
    chain_json = ""
    if my_output:
        try:
            chain_json = f"\n```json\n{json.dumps(my_output, ensure_ascii=False, indent=2)}\n```"
        except Exception:
            pass

    if meta.get("next_input"):
        previous_output += f"\n\n--- {label} ({worker_id}) ---\n{meta['next_input']}"
    else:
        # ПАТЧ context_trim: 400 символов вместо 800
        # К A12 цепочка = 12 агентов × 400 = 4800 симв вместо 9600
        previous_output += f"\n\n--- {label} ({worker_id}) ---\n{human_text[:400]}{chain_json}"

    return human_text, previous_output, ghost_ids


def _apply_qa_feedback(state: dict, raw_result: str, qa_agent: str):
    """
    УДАЛЕНО · Спринт 21.
    Парсинг ключевых слов ("отлично", "ошибка") из текста QA ненадёжен.
    DNA синхронизируется через _sync_feedback_scores_to_dna()
    которая читает структурированный feedback.json.
    Функция оставлена как заглушка для совместимости импортов.
    """
    pass  # намеренно пусто — см. _sync_feedback_scores_to_dna()


def _sync_feedback_scores_to_dna(client_slug: str, dept: str = ""):
    """
    Читает свежий feedback.json и синхронизирует реальные оценки QA
    в DNA каждого агента через sync_to_dna().

    Вызывается сразу после save_feedback() — один раз в конце рана.
    Это единственный источник правды для quality_score.

    score 0–4   → bad_work  (intensity = 1 - score/10)
    score 5–7   → нейтрально, лёгкий good_work
    score 8–10  → good_work (intensity = score/10)
    """
    if not _GRONDHEIM_ENABLED:
        return

    from pathlib import Path as _Path
    import json as _json

    feedback_path = _Path("clients") / client_slug / "feedback.json"
    if not feedback_path.exists():
        return

    try:
        feedback = _json.loads(feedback_path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[DNA-SYNC] Не удалось прочитать feedback: {e}")
        return

    agents_data = feedback.get("agents", {})
    if not agents_data:
        return

    print(f"[DNA-SYNC] Синхронизируем оценки → DNA ({len(agents_data)} агентов)")

    for agent_id, data in agents_data.items():
        score = data.get("score", 5.0)       # 0.0–10.0
        normalized = score / 10.0             # 0.0–1.0

        if score >= 8.0:
            event = "good_work"
            intensity = normalized
        elif score < 5.0:
            event = "bad_work"
            intensity = 1.0 - normalized      # чем хуже — тем сильнее
        else:
            event = "good_work"
            intensity = 0.4                   # нейтральная работа

        try:
            sync_to_dna(agent_id, event, intensity=intensity, dept=dept)
            emoji = "✅" if score >= 8 else "⚠️" if score >= 5 else "❌"
            print(f"  {emoji} {agent_id}: score={score} → {event}(i={intensity:.2f})")
        except Exception as e:
            print(f"  ⚠️ {agent_id}: sync_to_dna ошибка — {e}")


def _record_winning_strategies(state: dict, client_slug: str):
    """
    Читает feedback.json и записывает стратегии победивших агентов
    в Strategy Registry.
    Вызывается один раз в конце рана после QA.
    """
    from pathlib import Path as _Path
    import json as _json

    slot_id = state.get("_slot_id", "")
    run_type = state.get("run_type", "")

    feedback_path = _Path("clients") / client_slug / "feedback.json"
    if not feedback_path.exists():
        return

    try:
        feedback = _json.loads(feedback_path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[STRATEGY] Не удалось прочитать feedback: {e}")
        return

    agents_data = feedback.get("agents", {})
    results = state.get("results", {})

    for agent_id, fb_data in agents_data.items():
        score = fb_data.get("score", 0.0)
        problems = fb_data.get("problems", [])

        # Берём краткое резюме из результата агента
        result_data = results.get(agent_id, {})
        if isinstance(result_data, dict):
            summary = result_data.get("text", "")[:300]
        else:
            summary = str(result_data)[:300]

        if not summary:
            continue

        record_strategy(
            agent_id=agent_id,
            slot_id=slot_id,
            score=score,
            result_summary=summary,
            run_type=run_type,
            client_slug=client_slug,
            problems=problems,
        )


async def summarize_session(state: dict, client_slug: str, run_date: str, run_type: str):
    """Суммаризация сессии — вызывается в конце пайплайна"""
    if client_slug == "_sandbox":
        return

    try:
        chat_text = "\n".join([
            f"{m.get('role','')}: {m.get('content','')[:200]}"
            for m in state["chat_history"][-20:]
        ])

        results_text = ""
        for wid, res in state["results"].items():
            text = res.get("text", res) if isinstance(res, dict) else str(res)
            results_text += f"\n{wid}: {text[:300]}"

        summary_prompt = f"""Сделай краткий конспект рабочей сессии (300-500 слов).
Это нужно чтобы агенты помнили контекст в следующий раз.

Пиши только факты и решения — без воды. Формат:
- Что обсуждали
- Какие решения приняли
- Ключевые предпочтения клиента
- Что утвердили / отклонили
- Важные нюансы для будущих проектов

=== ДИАЛОГ ===
{chat_text}

=== БРИФ ===
{state['master_brief'][:1000]}

=== РЕЗУЛЬТАТЫ АГЕНТОВ ===
{results_text[:2000]}
"""

        summary = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: chat(
                "Ты — архивариус студии. Твоя задача — сжать рабочую сессию в краткий конспект для будущих проектов.",
                summary_prompt,
                "",
                agent_id="archiver",
                slot_id=state.get("_slot_id", "unknown"),
            )
        )

        save_session_summary(client_slug, run_date, run_type, summary)

        if state.get("project_dir"):
            summary_file = state["project_dir"] / "session_summary.md"
            summary_file.write_text(f"# Конспект сессии\n\n{summary}", encoding='utf-8')

        return summary
    except Exception as e:
        print(f"[SUMMARY ERROR] {e}")
        return None
