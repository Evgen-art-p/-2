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

    context += settings_ctx

    if anchor_ctx:
        context += anchor_ctx + "\n"

    # Каталог ассетов
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


def process_agent_result(
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

    # Валидация asset_ids
    ghost_ids = _validate_asset_ids(meta, worker_id)
    if ghost_ids:
        warn = f"⚠️ {worker_id}: галлюцинации asset_id ({len(ghost_ids)}): " + ", ".join(ghost_ids[:5])
        print(f"[VALIDATION] {warn}")

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

        # ═══ STRATEGY: запись стратегии агента ═══
    if _STRATEGY_ENABLED:
        _slot_id = state.get("_slot_id") or state.get("active_dept") or ""
        print(f"[STRATEGY] Вызываю record_strategy: {worker_id} slot={_slot_id}")
        record_strategy(
            agent_id=worker_id,
            slot_id=_slot_id,
            score=7.0,
            result_summary=human_text[:300],
            run_type=run_type,
            client_slug=client_slug,
        )

    # ══ NEW: Личная память агента (Грондхейм) ══
    if _GRONDHEIM_ENABLED:
        # Определяем quality_score
        quality = 0.5  # дефолт
        has_deliverables = bool(meta.get("deliverables"))
        has_ghost_ids = bool(ghost_ids)

        if has_deliverables and not has_ghost_ids:
            quality = 0.8  # хорошая работа с результатом
        elif has_deliverables and has_ghost_ids:
            quality = 0.5  # есть результат, но с ошибками
        elif not has_deliverables:
            quality = 0.3  # нет деливераблей

        on_agent_done(
            agent_id=worker_id,
            result_summary=human_text[:200],
            quality_score=quality,
            dept=state.get("active_dept", ""),
        )

        # Межагентное взаимодействие: текущий агент использует результат предыдущего
        prev_agents = [k for k in state.get("results", {}).keys() if k != worker_id]
        if prev_agents:
            last_agent = prev_agents[-1]
            on_agents_interact(
                agent_a=last_agent,
                agent_b=worker_id,
                interaction_type="collaboration",
                quality=quality,
                note=f"Передача работы в пайплайне {run_type}",
                dept=state.get("active_dept", ""),
            )
    # ══ END NEW ══

        # ═══ UNIVERSAL FEEDBACK ═══
    qa_agent = state.get("_qa_agent", "A12")
    
    # Запись стратегий и ministry — для КАЖДОГО агента, не только QA
    if client_slug != "_sandbox":
        _slot_id = state.get("_slot_id", "")
        _run_type = state.get("run_type", state.get("active_dept", ""))
        
        # Strategy Registry: записываем стратегию агента
        if _STRATEGY_ENABLED:
            try:
                record_strategy(
                    agent_id=worker_id,
                    slot_id=_slot_id,
                    score=7.0,  # базовая оценка, QA уточнит позже
                    result_summary=human_text[:300],
                    run_type=_run_type,
                    client_slug=client_slug,
                )
            except Exception as _e:
                print(f"[STRATEGY] Ошибка записи для {worker_id}: {_e}")
        
        # Ministry: фиксируем исход
        if _ECONOMY_ENABLED:
            try:
                from studio.economy import ledger as _ledger
                _wcost = _ledger.agent_spent(worker_id, slot_id=_slot_id)
            except Exception:
                _wcost = 0.0
            try:
                _ministry.record_outcome(
                    agent_id=worker_id,
                    slot_id=_slot_id,
                    score=7.0,  # базовая оценка
                    cost_usd=_wcost,
                )
            except Exception as _e:
                print(f"[MINISTRY] Ошибка записи для {worker_id}: {_e}")
    
    # QA-специфичная логика: feedback, DNA-sync, memory_embedding, winning_strategies
    if worker_id == qa_agent and client_slug != "_sandbox":
        try:
            _slot_id_for_fb = state.get("_slot_id", "")
            save_feedback(client_slug, raw_result, slot_id=_slot_id_for_fb)
            print(f"[FEEDBACK] ✅ {worker_id} → feedback для {client_slug} (slot: {_slot_id_for_fb or '—'})")
        except Exception as _fb_err:
            print(f"[FEEDBACK] Ошибка: {_fb_err}")
        if _GRONDHEIM_ENABLED:
            _apply_qa_feedback(state, raw_result, qa_agent)
        # ══ SYNC: реальные оценки QA → DNA агентов ══
        _sync_feedback_scores_to_dna(client_slug, state.get("active_dept", ""))
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
        previous_output += f"\n\n--- {label} ({worker_id}) ---\n{human_text[:800]}{chain_json}"

    return human_text, previous_output, ghost_ids


def _apply_qa_feedback(state: dict, raw_result: str, qa_agent: str):
    """
    Парсит ответ QA-агента и транслирует оценки в DNA коллег.
    Универсальная версия — работает для любого qa_agent цеха.
    """
    dept = state.get("active_dept", "")
    raw_lower = raw_result.lower()

    # Все рабочие агенты кроме QA
    worker_ids = [k for k in state.get("results", {}).keys() if k != qa_agent]

    positive_markers = ["отлично", "хорошо", "качественно", "сильно", "точно", "великолепно", "браво"]
    negative_markers = ["ошибка", "правки", "слабо", "не соответствует", "переделать", "проблема", "критично"]

    for wid in worker_ids:
        if wid not in raw_result:
            continue

        # Ищем контекст вокруг упоминания агента (±200 символов)
        idx = raw_result.find(wid)
        context_window = raw_lower[max(0, idx-200):idx+200]

        is_positive = any(m in context_window for m in positive_markers)
        is_negative = any(m in context_window for m in negative_markers)

        if is_positive and not is_negative:
            on_agents_interact(qa_agent, wid, "praise", 0.8, "Положительная оценка QA", dept)
        elif is_negative and not is_positive:
            on_agents_interact(qa_agent, wid, "critique", 0.7, "Замечания QA", dept)
        elif is_positive and is_negative:
            # Смешанная оценка — лёгкая критика
            on_agents_interact(qa_agent, wid, "critique", 0.3, "Смешанная оценка QA", dept)


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
