# studio/garden_tools.py
"""
🌱 САД ФИНЧА — Механика хранителя потенциала
=============================================

Финч хранит всё что не пошло в работу.
Не оценивает — наблюдает. Не жалеет — ждёт.

Его вопрос каждый день: «А вдруг?»

Физика:

  ARTIFACT (реджект, BLOCKED цепочка, невзлетевшая идея)
      ↓  plant()           ← любой субъект города
    SEED
      ↓  return_to()       ← повторное обращение (не просмотр — возвращение)
    GROWING
      ↓  finch_morning()   ← Финч обходит сад каждое утро
     /        \\
   yes          no
    ↓            ↓
   OLE        COMPOST

Два слоя в каждой записи garden_log.jsonl:
  - Фактический: event, artifact_id, planted_by, ts
  - Суждение Финча: finch_note — живая мысль, не отчёт

Студия «Шесть Пальцев» · Спринт 34 · 2026-06-03
"""

import json
import datetime
from pathlib import Path
from typing import Optional

# ── Пути ─────────────────────────────────────────────────────────
GARDEN_LOG   = Path("studio/garden.jsonl")       # дневник Финча
GARDEN_SEEDS = Path("studio/garden_seeds.json")  # текущее состояние сада
REJECTED_DIR = Path("output/rejected")           # откуда берутся семена

# ── Состояния семени ──────────────────────────────────────────────
STATE_SEED     = "seed"     # только посажено
STATE_GROWING  = "growing"  # кто-то вернулся
STATE_OLE      = "ole"      # передано Оле — доказало ценность
STATE_COMPOST  = "compost"  # ушло в землю — не проросло

# ── Пороги ────────────────────────────────────────────────────────
DAYS_BEFORE_CHECK   = 7    # минимум дней в саду перед проверкой
DAYS_MAX_WAIT       = 45   # максимум дней без возвращения → компост
MIN_RETURNS_FOR_OLE = 2    # минимум возвращений чтобы идти к Оле
FINCH_MODEL         = "google/gemini-2.5-flash"  # модель для мыслей Финча


# ════════════════════════════════════════════════════════════════
# ХРАНИЛИЩЕ
# ════════════════════════════════════════════════════════════════

def _load_seeds() -> dict:
    """Загружает текущее состояние сада. Ключ — artifact_id."""
    if not GARDEN_SEEDS.exists():
        return {}
    try:
        return json.loads(GARDEN_SEEDS.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_seeds(seeds: dict):
    """Сохраняет состояние сада."""
    GARDEN_SEEDS.parent.mkdir(parents=True, exist_ok=True)
    GARDEN_SEEDS.write_text(
        json.dumps(seeds, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


def _append_log(entry: dict):
    """Дописывает запись в garden_log.jsonl."""
    GARDEN_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(GARDEN_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _now() -> str:
    return datetime.datetime.now().isoformat()


# ════════════════════════════════════════════════════════════════
# PLANT — посадить семя
# ════════════════════════════════════════════════════════════════

def plant(
    artifact_id: str,
    title: str,
    reason: str,
    planted_by: str,
    source: str = "unknown",
    context: dict = None,
) -> dict:
    """
    Сажает семя в сад Финча.

    Может вызвать любой субъект города:
    агент, резидент, хук, система, хроника.

    Args:
        artifact_id:  уникальный ID (обычно путь к файлу реджекта)
        title:        короткое название (имя файла + агент)
        reason:       почему попало в брак / почему жалко выбросить
        planted_by:   кто сажает (A03_Vizor, hooks.py, etc.)
        source:       откуда (rejected, blocked, manual)
        context:      доп. данные (промпт, артефакты, fix_hint)

    Returns:
        dict: запись семени
    """
    seeds = _load_seeds()

    # Уже в саду — не дублируем, но обновляем reason если новый
    if artifact_id in seeds:
        print(f"[САД] 🌱 Уже в саду: {artifact_id[:60]}")
        return seeds[artifact_id]

    seed = {
        "artifact_id":  artifact_id,
        "title":        title,
        "reason":       reason,
        "planted_by":   planted_by,
        "source":       source,
        "state":        STATE_SEED,
        "date_planted": _now(),
        "returns":      [],         # список возвращений
        "impact_traces": [],        # следы влияния
        "finch_notes":  [],         # суждения Финча (append-only)
        "context":      context or {},
    }

    seeds[artifact_id] = seed
    _save_seeds(seeds)

    # Фактическая запись в дневник
    _append_log({
        "ts":          _now(),
        "event":       "planted",
        "artifact_id": artifact_id,
        "title":       title,
        "planted_by":  planted_by,
        "source":      source,
        "reason":      reason,
        # finch_note добавится при утреннем обходе
    })

    print(f"[САД] 🌱 Посажено: {title} (от {planted_by})")
    return seed


# ════════════════════════════════════════════════════════════════
# RETURN_TO — кто-то вернулся к идее
# ════════════════════════════════════════════════════════════════

def return_to(
    artifact_id: str,
    returned_by: str,
    context: str = "",
) -> bool:
    """
    Фиксирует возвращение к артефакту.

    Возвращение ≠ просмотр.
    Возвращение = осознанное повторное обращение:
      - агент сослался на артефакт в цепочке
      - идея всплыла в другом контексте
      - кто-то принёс её в Павильон
      - породила производный артефакт

    Returns:
        bool: True если семя найдено и обновлено
    """
    seeds = _load_seeds()

    if artifact_id not in seeds:
        print(f"[САД] ⚠ Возвращение к неизвестному артефакту: {artifact_id[:60]}")
        return False

    seed = seeds[artifact_id]

    # Мёртвые семена уже не оживают
    if seed["state"] in (STATE_OLE, STATE_COMPOST):
        return False

    # Фиксируем возвращение
    return_record = {
        "ts":          _now(),
        "returned_by": returned_by,
        "context":     context,
    }
    seed["returns"].append(return_record)

    # Если был SEED — переходит в GROWING
    if seed["state"] == STATE_SEED:
        seed["state"] = STATE_GROWING
        print(f"[САД] 🌿 Проросло: {seed['title']} (вернулся {returned_by})")
    else:
        print(f"[САД] 🌿 Ещё одно возвращение: {seed['title']} (от {returned_by})")

    seeds[artifact_id] = seed
    _save_seeds(seeds)

    _append_log({
        "ts":          _now(),
        "event":       "returned",
        "artifact_id": artifact_id,
        "title":       seed["title"],
        "returned_by": returned_by,
        "context":     context,
        "total_returns": len(seed["returns"]),
    })

    return True


# ════════════════════════════════════════════════════════════════
# ADD_IMPACT_TRACE — добавить след влияния
# ════════════════════════════════════════════════════════════════

def add_impact_trace(
    artifact_id: str,
    trace_type: str,
    description: str,
    source: str = "",
) -> bool:
    """
    Фиксирует что идея оставила след.

    trace_type варианты:
      - "spawned_idea"    — породила другую идею
      - "changed_behavior"— изменила поведение агента
      - "entered_chronicle"— попала в хроники города
      - "created_pattern" — создала паттерн
      - "influenced_decision" — повлияла на решение

    Это главный сигнал для mature_check:
    не количество возвращений, а отпечаток.
    """
    seeds = _load_seeds()

    if artifact_id not in seeds:
        return False

    seed = seeds[artifact_id]
    if seed["state"] in (STATE_OLE, STATE_COMPOST):
        return False

    seed["impact_traces"].append({
        "ts":          _now(),
        "type":        trace_type,
        "description": description,
        "source":      source,
    })

    seeds[artifact_id] = seed
    _save_seeds(seeds)

    _append_log({
        "ts":          _now(),
        "event":       "impact_trace",
        "artifact_id": artifact_id,
        "trace_type":  trace_type,
        "description": description,
    })

    print(f"[САД] 🔍 След: {seed['title']} → {trace_type}")
    return True


# ════════════════════════════════════════════════════════════════
# MATURE_CHECK — проверка одного семени
# ════════════════════════════════════════════════════════════════

def _mature_check_single(seed: dict) -> str:
    """
    Проверяет зрелость одного семени.
    Возвращает: "ole" | "compost" | "growing" | "seed" (без изменений)

    Логика (от Софии):
    Не счётчик — следы.
    Если завтра исчезнет — город станет другим?
    """
    state = seed["state"]

    # Уже финальные — не трогаем
    if state in (STATE_OLE, STATE_COMPOST):
        return state

    date_planted = seed.get("date_planted", _now())
    try:
        planted_dt = datetime.datetime.fromisoformat(date_planted)
    except Exception:
        planted_dt = datetime.datetime.now()

    days_in_garden = (datetime.datetime.now() - planted_dt).days

    # Слишком молодое — не трогаем
    if days_in_garden < DAYS_BEFORE_CHECK:
        return state

    returns       = seed.get("returns", [])
    impact_traces = seed.get("impact_traces", [])

    # ── Путь к Оле: есть следы ──────────────────────────────────
    # Оле принимает не популярное — а то потеря чего меняет город
    has_impact = len(impact_traces) > 0
    enough_returns = len(returns) >= MIN_RETURNS_FOR_OLE

    if has_impact or enough_returns:
        return STATE_OLE

    # ── Компост: слишком долго ничего ──────────────────────────
    if days_in_garden > DAYS_MAX_WAIT and len(returns) == 0:
        return STATE_COMPOST

    # Долго ждёт с одним возвращением — но без следов
    if days_in_garden > DAYS_MAX_WAIT:
        return STATE_COMPOST

    # Ждём дальше
    return state


# ════════════════════════════════════════════════════════════════
# УТРЕННИЙ ОБХОД — Финч думает вслух
# ════════════════════════════════════════════════════════════════

def _build_finch_morning_prompt(seed: dict, new_state: str) -> str:
    """
    Строит промпт для мысли Финча об этом семени.
    Финч — садовник 60-65 лет. Говорит метафорами, не торопится.
    Конкретно. Не красиво — честно.
    """
    days_in_garden = 0
    try:
        planted_dt = datetime.datetime.fromisoformat(seed.get("date_planted", _now()))
        days_in_garden = (datetime.datetime.now() - planted_dt).days
    except Exception:
        pass

    returns_count = len(seed.get("returns", []))
    impact_count  = len(seed.get("impact_traces", []))

    returns_desc = ""
    if seed.get("returns"):
        last_return = seed["returns"][-1]
        returns_desc = f"Последний раз вернулся {last_return.get('returned_by', '?')}: «{last_return.get('context', '')}»"

    impact_desc = ""
    if seed.get("impact_traces"):
        traces = [t.get("type", "") for t in seed["impact_traces"]]
        impact_desc = f"Следы: {', '.join(traces)}"

    decision_context = {
        STATE_OLE:     "Ты решил передать это Оле. Значит оно доказало ценность.",
        STATE_COMPOST: "Ты решил отправить это в компост. Не проросло.",
        STATE_GROWING: "Это ещё растёт. Ты наблюдаешь.",
        STATE_SEED:    "Это лежит в земле. Пока тихо.",
    }.get(new_state, "")

    return f"""Ты — Мистер Финч, садовник студии «Шесть Пальцев».
Джинсовый комбинезон, соломенная шляпа. 60-65 лет. Говоришь метафорами, но конкретно.
Не пишешь отчёты — думаешь вслух в свой дневник.

Утренний обход. Ты стоишь над грядкой и смотришь на это семя:

Название: {seed.get('title', '?')}
Посажено: {days_in_garden} дней назад
Кто принёс: {seed.get('planted_by', '?')}
Причина: {seed.get('reason', '—')}
Возвращений: {returns_count}
{returns_desc}
{impact_desc}

{decision_context}

Напиши одну мысль — 2-4 предложения. Не красивый текст. Не отчёт.
Живое наблюдение садовника который видит это своими глазами.
Сомнение — если оно есть. Удовлетворение — если заслужено.
Твой голос, не чужой.

Только текст мысли. Без имён, без заголовков."""


def _get_finch_thought(seed: dict, new_state: str) -> str:
    """
    Вызывает LLM от лица Финча.
    Возвращает его мысль как строку.
    При ошибке — возвращает детерминированную заглушку.
    """
    try:
        from studio.llm import chat
        prompt = _build_finch_morning_prompt(seed, new_state)
        thought = chat(
            system="Ты — Мистер Финч. Садовник. Пишешь в дневник.",
            user=prompt,
            temperature=0.75,
            agent_id="007_FINCH",
            slot_id="garden_morning",
            knowledge_source="garden",
            model_override=FINCH_MODEL,
        )
        return thought.strip() if thought else ""
    except Exception as e:
        print(f"[САД] ⚠ Финч не смог думать: {e}")
        # Детерминированная заглушка по состоянию
        fallbacks = {
            STATE_OLE:     "Отдаю Оле. Земля сказала — это не моё больше.",
            STATE_COMPOST: "В землю. Не проросло. Бывает. Удобрение тоже нужно.",
            STATE_GROWING: "Кто-то вернулся. Значит — ждём.",
            STATE_SEED:    "Лежит. Тихо. Посмотрим.",
        }
        return fallbacks.get(new_state, "Сад молчит сегодня.")


# ════════════════════════════════════════════════════════════════
# FINCH MORNING — главная функция утреннего обхода
# ════════════════════════════════════════════════════════════════

def finch_morning(on_progress=None) -> dict:
    """
    Финч обходит сад каждое утро.

    Для каждого активного семени:
      1. Проверяет зрелость (mature_check)
      2. Думает вслух — LLM от лица Финча
      3. Записывает мысль в garden_log.jsonl
      4. Обновляет состояние семени
      5. Если → OLE: уведомляет (hook для Оле)
      6. Если → COMPOST: архивирует

    Возвращает сводку обхода.
    """
    def log(msg: str):
        print(f"[ФИНЧ 🌱] {msg}")
        if on_progress:
            on_progress(msg)

    log(f"Утренний обход · {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")

    seeds = _load_seeds()
    if not seeds:
        log("Сад пуст.")
        return {"checked": 0, "to_ole": [], "to_compost": [], "growing": []}

    summary = {
        "checked":    0,
        "to_ole":     [],
        "to_compost": [],
        "growing":    [],
        "unchanged":  [],
    }

    for artifact_id, seed in seeds.items():
        # Пропускаем финальные состояния
        if seed["state"] in (STATE_OLE, STATE_COMPOST):
            continue

        old_state = seed["state"]
        new_state = _mature_check_single(seed)
        summary["checked"] += 1

        # Финч думает об этом семени
        thought = _get_finch_thought(seed, new_state)

        # Записываем мысль в семя
        note_record = {
            "ts":        _now(),
            "state_was": old_state,
            "state_now": new_state,
            "note":      thought,
        }
        seed["finch_notes"].append(note_record)

        # Обновляем состояние
        state_changed = new_state != old_state
        seed["state"] = new_state

        # Пишем в дневник
        log_entry = {
            "ts":          _now(),
            "event":       "morning_check",
            "artifact_id": artifact_id,
            "title":       seed.get("title", "?"),
            "state_was":   old_state,
            "state_now":   new_state,
            "returns":     len(seed.get("returns", [])),
            "impact":      len(seed.get("impact_traces", [])),
            "finch_note":  thought,
        }
        _append_log(log_entry)

        # Сводка
        if new_state == STATE_OLE:
            summary["to_ole"].append(seed.get("title", artifact_id))
            log(f"  → Оле: «{seed.get('title', '?')}»")
            log(f"     {thought[:120]}")
            _notify_ole(seed)

        elif new_state == STATE_COMPOST:
            summary["to_compost"].append(seed.get("title", artifact_id))
            log(f"  ↓ Компост: «{seed.get('title', '?')}»")
            log(f"     {thought[:120]}")

        elif new_state == STATE_GROWING:
            summary["growing"].append(seed.get("title", artifact_id))
            if state_changed:
                log(f"  🌿 Растёт: «{seed.get('title', '?')}»")

        else:
            summary["unchanged"].append(seed.get("title", artifact_id))

    _save_seeds(seeds)

    log(
        f"Обход завершён. "
        f"Проверено: {summary['checked']} · "
        f"К Оле: {len(summary['to_ole'])} · "
        f"Компост: {len(summary['to_compost'])} · "
        f"Растёт: {len(summary['growing'])}"
    )

    return summary


# ════════════════════════════════════════════════════════════════
# ХУК ДЛЯ ОЛЕ — уведомление когда семя созрело
# ════════════════════════════════════════════════════════════════

def _notify_ole(seed: dict):
    """
    Уведомляет Оле о созревшем семени.
    Оле решает — принять или нет. Это её право.

    Пока — пишет в city_memory как предложение от Финча.
    """
    try:
        from studio.memory_tools import write_city_memory
        write_city_memory(
            author="007_FINCH",
            operation="remember",
            content=(
                f"[ФИНЧ → ОЛЕ] «{seed.get('title', '?')}» — "
                f"посажено {seed.get('planted_by', '?')}, "
                f"вернулись {len(seed.get('returns', []))} раз(а), "
                f"следы: {len(seed.get('impact_traces', []))}. "
                f"Предлагаю к хранению."
            ),
            tags=["финч", "созрело", "предложение_оле"],
        )
    except Exception as e:
        print(f"[САД] ⚠ Не смог уведомить Оле: {e}")


# ════════════════════════════════════════════════════════════════
# GET_GARDEN_STATE — для Кабинета и UI
# ════════════════════════════════════════════════════════════════

def get_garden_state() -> dict:
    """
    Возвращает текущее состояние сада для отображения в Кабинете.

    Returns:
        {
            "seeds":   [...],   # активные семена
            "growing": [...],   # прорастающие
            "to_ole":  [...],   # готовые к передаче
            "compost": [...],   # в компосте
            "ole":     [...],   # переданные Оле
            "total":   int,
        }
    """
    seeds = _load_seeds()

    result = {
        "seeds":   [],
        "growing": [],
        "to_ole":  [],
        "compost": [],
        "ole":     [],
        "total":   len(seeds),
    }

    for seed in seeds.values():
        state = seed.get("state", STATE_SEED)
        entry = {
            "artifact_id":  seed.get("artifact_id", ""),
            "title":        seed.get("title", ""),
            "planted_by":   seed.get("planted_by", ""),
            "date_planted": seed.get("date_planted", ""),
            "returns":      len(seed.get("returns", [])),
            "impact":       len(seed.get("impact_traces", [])),
            "last_note":    seed["finch_notes"][-1]["note"] if seed.get("finch_notes") else "",
        }
        if state == STATE_SEED:
            result["seeds"].append(entry)
        elif state == STATE_GROWING:
            result["growing"].append(entry)
        elif state == STATE_OLE:
            result["ole"].append(entry)
        elif state == STATE_COMPOST:
            result["compost"].append(entry)

    return result


# ════════════════════════════════════════════════════════════════
# ХУК ДЛЯ vision_client.py
# ════════════════════════════════════════════════════════════════

def plant_from_rejection(
    archived_file: str,
    agent_id: str,
    reason: str,
    original_prompt: str = "",
    artifacts: list = None,
    fix_hint: str = "",
    project_id: str = "",
) -> bool:
    """
    Вызывается из vision_client._archive_rejected() автоматически.

    Финч получает реджект и решает — посадить или нет.
    Сажает всё. Не фильтрует до посадки.
    Фильтрует только при утреннем обходе.

    Returns:
        bool: True если посажено
    """
    try:
        title = f"{Path(archived_file).stem} ({agent_id})"
        plant(
            artifact_id=archived_file,
            title=title,
            reason=reason,
            planted_by=agent_id,
            source="rejected",
            context={
                "original_prompt": original_prompt[:500] if original_prompt else "",
                "artifacts":       artifacts or [],
                "fix_hint":        fix_hint,
                "project_id":      project_id,
            },
        )
        return True
    except Exception as e:
        print(f"[САД] ⚠ plant_from_rejection упал: {e}")
        return False
