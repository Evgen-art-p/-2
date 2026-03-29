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

# Feedback loop — оценки от Артура
try:
    from studio.agent_feedback import get_feedback, save_feedback
except ImportError:
    def get_feedback(client_slug, worker_id): return ""
    def save_feedback(client_slug, arthur_result): pass

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
    # ══ END ══

    context += settings_ctx

    if anchor_ctx:
        context += anchor_ctx + "\n"

    # Каталог ассетов
    catalog = _load_asset_catalog()
    if catalog:
        context += f"\n\n{catalog}\n\n"

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
    system_prompt = get_worker_prompt(worker_id)
    worker_knowledge = get_worker_knowledge(worker_id)
    vision_images = _collect_images_for_vision(state)
    dept = state.get("active_dept", "")

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
                    info = get_worker_info(worker_id)
                    label = info.get("label", worker_id) if info else worker_id
                    print(f"[DNA→T°] {worker_id} {label}: Stress={dynamic.get('Stress',0)} Light={dynamic.get('Internal_Light',0.8)} → temp={agent_temp}")
        except Exception as e:
            print(f"[DNA→T°] {worker_id}: не удалось — {e}")

    if vision_images:
        print(f"[PIPELINE] Vision для {worker_id}: {len(vision_images)} изображений")
        raw_result = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda sp=system_prompt, ctx=context, wk=worker_knowledge, vi=vision_images, t=agent_temp:
                chat_with_images(sp, ctx, images=vi, knowledge=wk, temperature=t)
        )
    else:
        raw_result = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda sp=system_prompt, ctx=context, wk=worker_knowledge, t=agent_temp:
                chat(sp, ctx, wk, temperature=t)
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
    info = get_worker_info(worker_id)
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

    # Feedback loop: если это Артур — сохраняем оценки для следующего рана
    print(f"[DEBUG FEEDBACK] worker={worker_id}, client='{client_slug}'") 
    if worker_id == "A12" and client_slug != "_sandbox":
        try:
            save_feedback(client_slug, raw_result)
        except Exception as _fb_err:
            print(f"[FEEDBACK] Ошибка сохранения: {_fb_err}")

        # ══ NEW: Артур оценивает коллег → влияет на их DNA ══
        if _GRONDHEIM_ENABLED:
            _apply_arthur_feedback(state, raw_result)
        # ══ END NEW ══

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


# ══ NEW: Артур (A12) → оценки коллегам ══
def _apply_arthur_feedback(state: dict, raw_result: str):
    """
    Парсит ответ Артура и транслирует оценки в DNA коллег.
    Артур упоминает агентов — ищем позитивные/негативные маркеры.
    """
    dept = state.get("active_dept", "")
    raw_lower = raw_result.lower()

    # Все рабочие агенты кроме Артура
    worker_ids = [k for k in state.get("results", {}).keys() if k != "A12"]

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
            on_agents_interact("A12", wid, "praise", 0.8, "Положительная оценка QA", dept)
        elif is_negative and not is_positive:
            on_agents_interact("A12", wid, "critique", 0.7, "Замечания QA", dept)
        elif is_positive and is_negative:
            # Смешанная оценка — лёгкая критика
            on_agents_interact("A12", wid, "critique", 0.3, "Смешанная оценка QA", dept)
# ══ END NEW ══


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
                ""
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
