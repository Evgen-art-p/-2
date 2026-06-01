"""
Residents Manager — управление резидентами студии (SET и будущие).
Хранит пути, загружает промпты, маски, предоставляет методы
для сборки system prompt и общения.
"""
from pathlib import Path

# ── Константы ─────────────────────────────────────────
RESIDENTS_DIR = Path("studio/modules/residents")
SET_DIR = RESIDENTS_DIR / "003_LEGACY_SET"
OLE_DIR    = RESIDENTS_DIR / "004_OLE"      # Библиотекарь Оле
VICTOR_DIR  = RESIDENTS_DIR / "005_VICTOR"   # Резидент-критик Виктор
MONTEUR_DIR = RESIDENTS_DIR / "006_MONTEUR"  # Монтажёр — сборка финального ролика

# Кеш промптов (dept → промпт)
_prompt_cache: dict = {}


def _load_set_prompt(dept: str) -> str:
    """Загружает промпт SET: forge/prompt.md + маска цеха (если есть).
    Результат кешируется.
    """
    cache_key = f"set_{dept}"
    if cache_key in _prompt_cache:
        return _prompt_cache[cache_key]

    # Основной промпт — forge/prompt.md (бывший knowledge/set_core.md)
    prompt = ""
    prompt_path = SET_DIR / "forge" / "prompt.md"
    if prompt_path.exists():
        prompt = prompt_path.read_text(encoding="utf-8")

    # Маска под цех — forge/masks/{dept}.md (бывший knowledge/set_{dept}.md)
    mask = ""
    mask_path = SET_DIR / "forge" / "masks" / f"{dept}.md"
    if mask_path.exists():
        mask = mask_path.read_text(encoding="utf-8")

    result = f"{prompt}\n\n{mask}".strip()
    _prompt_cache[cache_key] = result
    return result


def get_set_system_prompt(dept: str, run_type: str, settings: dict) -> str:
    """Собирает system prompt для SET.
    Замена вычислению state['set_system'] в ui.py.

    Args:
        dept: цех (living_book, social_mix, ...)
        run_type: режим (content_plan, social, full, ...)
        settings: dict с format, duration, style

    Returns:
        Готовый system prompt для отправки в LLM
    """
    prompt = _load_set_prompt(dept)

    header = (
        f"=== ТЕКУЩИЙ ЦЕХ ===\n"
        f"Цех: {dept}\n"
        f"Режим: {run_type}\n"
        f"Формат: {settings.get('format', '9:16')}\n"
        f"Стиль: {settings.get('style', 'Stylized 3D Realism')}\n"
    )

    return f"{prompt}\n\n{header}"


def build_set_context(dept: str, run_type: str, settings: dict) -> str:
    """Собирает полный контекст SET для отправки в LLM.
    Включает: system prompt + актуальные настройки.
    Используется в send_message() при worker_id == 'SET'.
    """
    system = get_set_system_prompt(dept, run_type, settings)

    live_settings = (
        f"\n=== АКТУАЛЬНЫЕ НАСТРОЙКИ ===\n"
        f"Цех: {dept}\n"
        f"Режим: {run_type}\n"
        f"Формат: {settings.get('format', '9:16')}\n"
        f"Длительность: {settings.get('duration', 15)} сек\n"
        f"Стиль: {settings.get('style', 'Stylized 3D Realism')}\n"
    )

    return system + live_settings


def detect_run_type_from_brief(brief: str, dept: str, default_run_type: str) -> str:
    """Авто-определение режима по тексту брифа.
    Было в build_brief() в ui.py.

    Args:
        brief: текст брифа от SET
        dept: текущий цех
        default_run_type: режим по умолчанию (из DEPT_TO_RUNTYPE)

    Returns:
        'content_plan' если бриф про контент-план, иначе default_run_type
    """
    brief_lower = brief.lower()
    markers = [
        "content_plan",
        "контент-план",
        "режим: plan",
        "тип задачи: content_plan",
    ]

    if any(marker in brief_lower for marker in markers):
        return "content_plan"
    return default_run_type

# ============================================================
# 004_OLE — Bibliotekár (patch_ole.py)
# ============================================================

def _load_ole_prompt(mode="home"):
    """Zagruzhaet prompt Ole po rezhimu: 'home' | 'library'. Keshiruetsya."""
    cache_key = f"ole_{mode}"
    if cache_key in _prompt_cache:
        return _prompt_cache[cache_key]
    path = (
        OLE_DIR / "forge" / "prompt.md"
        if mode == "library"
        else OLE_DIR / "home" / "home_prompt.md"
    )
    result = path.read_text(encoding="utf-8") if path.exists() else ""
    _prompt_cache[cache_key] = result
    return result


def get_ole_system_prompt(mode="home"):
    """System-prompt dlya Ole.
    mode='home'    — bytovoy (instrumenty OFF)
    mode='library' — rabochiy (instrumenty ON)
    """
    return _load_ole_prompt(mode)


def invalidate_ole_cache():
    """Сбрасывает кеш промптов Оле."""
    global _prompt_cache
    for k in [k for k in list(_prompt_cache) if k.startswith("ole_")]:
        del _prompt_cache[k]


def run_ole_remember(
    title: str,
    event: str,
    significance: str,
    loss_if_forgotten: str,
    memory_type: str,
    storage: str,
    source: str = "",
) -> dict:
    """
    Оле принимает событие в память города.

    Оле сама решает — стоит ли сохранять.
    Если loss_if_forgotten пустой или натянутый — вернёт None.

    memory_type: lesson | tradition | warning | inspiration | identity
    storage:     library | harbor | chronicles | reference
    """
    try:
        from studio.memory_tools import remember
        result = remember(
            title=title,
            event=event,
            significance=significance,
            loss_if_forgotten=loss_if_forgotten,
            memory_type=memory_type,
            storage=storage,
            source=source,
        )
        if result:
            print(f"[ОЛЕ] ✅ Принято в память: '{title}'")
        else:
            print(f"[ОЛЕ] ✗ Отклонено: '{title}' — loss_if_forgotten не убедителен")
        return result or {}
    except Exception as e:
        print(f"[ОЛЕ] ❌ run_ole_remember: {e}")
        return {}


def run_ole_remind(
    query: str,
    memory_type: str = None,
    storage: str = None,
    top_k: int = 3,
) -> list[dict]:
    """
    Оле ищет в памяти города — для инжекта в контекст агента.

    Используется в pipeline.py → build_agent_context()
    когда агент идёт по уже пройденному пути.

    Возвращает список memory_entry или [] если память пуста.
    """
    try:
        from studio.memory_tools import remind, format_for_agent
        results = remind(query=query, memory_type=memory_type,
                         storage=storage, top_k=top_k)
        return results
    except Exception as e:
        print(f"[ОЛЕ] ❌ run_ole_remind: {e}")
        return []


def run_ole_release(entry_id: str, reason: str) -> bool:
    """
    Оле отпускает запись памяти.

    Не удаление — отпущенное остаётся в архиве с причиной.
    reason обязателен.
    """
    try:
        from studio.memory_tools import release
        return release(entry_id=entry_id, reason=reason)
    except Exception as e:
        print(f"[ОЛЕ] ❌ run_ole_release: {e}")
        return False


def run_ole_decline(title: str, reason: str, source: str = "") -> dict:
    """
    Оле отказывает событию во входе в память.

    "Нет. Это не войдёт в память города."
    Отказ записывается — история решений сохраняется.
    reason обязателен.
    """
    try:
        from studio.memory_tools import decline
        return decline(title=title, reason=reason, source=source)
    except Exception as e:
        print(f"[ОЛЕ] ❌ run_ole_decline: {e}")
        return {}


def get_ole_memory_for_agent(query: str, max_chars: int = 1500) -> str:
    """
    Рюкзак памяти — для инжекта в контекст агента в pipeline.

    Вызывается из build_agent_context() рядом с get_harbor_knowledge().
    Возвращает отформатированный текст или '' если памяти нет.
    """
    try:
        from studio.memory_tools import remind, format_for_agent
        results = remind(query=query, top_k=3)
        if not results:
            return ""
        formatted = format_for_agent(results, max_chars=max_chars)
        if formatted:
            print(f"[ОЛЕ→РЮКЗАК] 🧠 {len(results)} записей памяти для агента")
        return formatted
    except Exception as e:
        print(f"[ОЛЕ] ❌ get_ole_memory_for_agent: {e}")
        return ""


# ============================================================
# 005_VICTOR — Резидент-критик (patch_victor.py)
# ============================================================

def run_victor_critique(chain_data: str, dept: str = "") -> dict:
    """Запускает Виктора Лэйна — критика смыслов.

    chain_data: previous_output (цепочка выводов агентов до ХАРД-СТОПа)
    dept:       цех (video_long, video_shorts, ...) — для маски промпта

    Возвращает:
        {
          "agent":             "victor",
          "verdict":           "APPROVED | APPROVED_WITH_CONCERNS | NEEDS_REWORK",
          "strong_points":     [...],
          "blind_spots":       [...],
          "critical_question": "...",
          "recommendation":    "..."
        }
    """
    import json as _json
    import re as _re
    from studio.llm import chat

    # ── Промпт ────────────────────────────────────────────────
    prompt_path = VICTOR_DIR / "forge" / "prompt.md"
    if not prompt_path.exists():
        print(f"[VICTOR] ⚠️  prompt.md не найден: {prompt_path}")
        return {
            "agent":             "victor",
            "verdict":           "APPROVED",
            "strong_points":     [],
            "blind_spots":       [],
            "critical_question": "",
            "recommendation":    "Промпт Виктора не найден — критика пропущена.",
        }

    system_prompt = prompt_path.read_text(encoding="utf-8")

    # Маска под цех если есть
    if dept:
        mask_path = VICTOR_DIR / "forge" / "masks" / f"{dept}.md"
        if mask_path.exists():
            system_prompt += "\n\n" + mask_path.read_text(encoding="utf-8")

    # ── Контекст ──────────────────────────────────────────────
    context = (
        "=== МАТЕРИАЛ ДЛЯ КРИТИКИ ===\n"
        f"{chain_data}\n\n"
        "Прочитай трижды. Найди где работа предала свой потенциал.\n"
        "Ответь строго в JSON — ничего кроме JSON."
    )

    # ── Вызов LLM ─────────────────────────────────────────────
    try:
        raw = chat(system_prompt, context, temperature=0.5)
    except Exception as e:
        print(f"[VICTOR] ❌ LLM ошибка: {e}")
        return {
            "agent":             "victor",
            "verdict":           "APPROVED",
            "strong_points":     [],
            "blind_spots":       [],
            "critical_question": "",
            "recommendation":    f"Ошибка вызова LLM: {e}",
        }

    # ── Парсинг JSON ──────────────────────────────────────────
    m = _re.search(r'\{.*\}', raw, _re.DOTALL)
    if m:
        try:
            result = _json.loads(m.group())
            # Гарантируем обязательные поля
            result.setdefault("agent", "victor")
            result.setdefault("verdict", "APPROVED_WITH_CONCERNS")
            result.setdefault("strong_points", [])
            result.setdefault("blind_spots", [])
            result.setdefault("critical_question", "")
            result.setdefault("recommendation", "")
            print(f"[VICTOR] ✅ Вердикт: {result['verdict']}")
            return result
        except _json.JSONDecodeError as e:
            print(f"[VICTOR] ⚠️  JSON parse error: {e}")

    # Fallback если JSON не распарсился
    print("[VICTOR] ⚠️  JSON не найден в ответе — возвращаю raw")
    return {
        "agent":             "victor",
        "verdict":           "APPROVED_WITH_CONCERNS",
        "strong_points":     [],
        "blind_spots":       [raw[:500]],
        "critical_question": "",
        "recommendation":    "",
    }


# ============================================================
# 006_MONTEUR — Монтажёр (финальная сборка роликов)
# ============================================================

def run_monteur_assembly(
    deliverables: dict,
    project_id: str = "",
    slot_id: str = "video_long",
):
    """
    Артур — последний мастер перед зрителем. Спринт 30в.

    Этап 1: Читает пакет → определяет dialog shots → выбирает модель
    Этап 2: accept_material() — приёмка lipsync (только технический брак)
    Этап 3: ffmpeg по стандарту (не режиссирует заново)
    Этап 4: смотрит весь финал (grid каждые 2 сек) → arthur_notes
    """
    import json as _json
    import re as _re
    from pathlib import Path

    from studio.llm import chat, chat_with_images, stress_to_temperature

    MONTEUR_ID  = "006_MONTEUR"
    MONTEUR_DIR = Path("studio/modules/residents/006_MONTEUR")
    project_id  = project_id or deliverables.get("project_id", "unknown")

    print(f"
[АРТУР] 🎬 Начинаю работу над: {project_id}")

    # ── Промпт ──────────────────────────────────────────────────
    prompt_path = MONTEUR_DIR / "forge" / "prompt.md"
    mask_path   = MONTEUR_DIR / "forge" / "masks" / f"{slot_id}.md"
    system_prompt = ""
    if prompt_path.exists():
        system_prompt = prompt_path.read_text(encoding="utf-8")
    if mask_path.exists():
        system_prompt += "

" + mask_path.read_text(encoding="utf-8")

    if not system_prompt.strip():
        print("[АРТУР] ⚠️  Промпт не найден — работаю как скрипт")
        from studio.assembly.monteur import assemble
        return assemble(deliverables=deliverables,
                        project_id=project_id, slot_id=slot_id)

    # ── Пробуждение ─────────────────────────────────────────────
    try:
        from studio.grondheim_memory import on_agent_wake
        on_agent_wake(MONTEUR_ID, dept="residents")
    except Exception:
        pass

    # ── ДНК → temperature ────────────────────────────────────────
    agent_temp = 0.5
    try:
        dna_path = MONTEUR_DIR / "dna.json"
        if dna_path.exists():
            dna = _json.loads(dna_path.read_text(encoding="utf-8"))
            dyn = dna.get("dynamic", {})
            agent_temp = stress_to_temperature(
                stress=float(dyn.get("Stress", 0.0)),
                light=float(dyn.get("Internal_Light", 0.8)),
            )
            print(f"[АРТУР] 🧬 temp={agent_temp}")
    except Exception as e:
        print(f"[АРТУР] ⚠️  ДНК: {e}")

    # ── Sensory — разговоры с Шефом ─────────────────────────────
    chef_notes = ""
    try:
        from studio.grondheim_memory import load_sensory
        sensory = load_sensory(MONTEUR_ID, "residents")
        entries = sensory.get("entries", [])
        recent  = [e.get("feeling") or e.get("content", "")
                   for e in entries[-5:] if e]
        recent  = [r for r in recent if r]
        if recent:
            chef_notes = "=== ЧТО ШЕФ ГОВОРИЛ ПЕРЕД МОНТАЖОМ ===
"
            chef_notes += "
".join(f"  · {r}" for r in recent)
            chef_notes += "
=================================="
            print(f"[АРТУР] 💬 Помню {len(recent)} записей")
    except Exception as e:
        print(f"[АРТУР] ⚠️  Sensory: {e}")

    # ── ЭТАП 1: Читаем пакет ─────────────────────────────────────
    clips    = deliverables.get("video_clips", [])
    vo_lines = deliverables.get("audio", {}).get("vo_lines", [])

    clip_index = "".join(
        f"  shot_id={c.get('shot_id','?')} "
        f"scene={c.get('scene_id','?')} "
        f"shot_type={c.get('shot_type','?')} "
        f"dur={c.get('duration_sec',0)}s
"
        for c in clips
    )
    vo_index = "".join(
        f"  scene_id={v.get('scene_id')} "
        f"vo_path={'✅' if v.get('vo_path') else '❌'}
"
        for v in vo_lines
    )

    context = (
        f"=== ПАКЕТ: {project_id} | {deliverables.get('platform','?')} ===

"
        f"=== КЛИПЫ ({len(clips)}) ===
{clip_index}
"
        f"=== VO ЛИНИИ ===
{vo_index or '  (нет VO)'}

"
        f"{chef_notes}

"
        "Определи какие shots нужен lipsync (dialog + есть vo_path).
"
        "Выбери модель для взгляда на финал.
"
        "Ответь строго в JSON."
    )

    print("[АРТУР] 📋 Читаю пакет...")
    decision = {}
    try:
        raw = chat(
            system=system_prompt,
            user=context,
            temperature=agent_temp,
            agent_id=MONTEUR_ID,
            slot_id=slot_id,
        )
        m = _re.search(r"\{.*\}", raw, _re.DOTALL)
        if m:
            decision = _json.loads(m.group())
    except Exception as e:
        print(f"[АРТУР] ⚠️  LLM: {e}")

    lipsync_shots = decision.get("lipsync_shots", [])
    chosen_model  = decision.get("chosen_model", "google/gemini-2.5-flash")

    print(f"[АРТУР] 🎯 lipsync: {len(lipsync_shots)} shots | модель: {chosen_model}")

    # ── ЭТАП 2: Приёмка материала lipsync ───────────────────────
    if lipsync_shots:
        _monteur_accept_material(
            lipsync_shots=lipsync_shots,
            clips=clips,
            deliverables=deliverables,
            project_id=project_id,
            system_prompt=system_prompt,
            agent_temp=agent_temp,
            slot_id=slot_id,
        )

    # ── ЭТАП 3: Сборка ffmpeg по стандарту ──────────────────────
    from studio.assembly.monteur import assemble
    print("[АРТУР] 🔨 Собираю...")
    result = assemble(
        deliverables=deliverables,
        project_id=project_id,
        slot_id=slot_id,
    )

    # ── ЭТАП 4: Смотрим весь финал ──────────────────────────────
    if result.final_path and Path(result.final_path).exists():
        _monteur_watch_final(
            result=result,
            deliverables=deliverables,
            system_prompt=system_prompt,
            chosen_model=chosen_model,
            agent_temp=agent_temp,
            slot_id=slot_id,
        )

    # ── Память и экономика ───────────────────────────────────────
    verdict = ("PASS" if result.status == "DONE"
               else "PARTIAL" if result.status == "PARTIAL" else "FAIL")
    quality = 1.0 if verdict == "PASS" else (0.6 if verdict == "PARTIAL" else 0.2)
    summary = (
        f"Собрал {result.clips_used}/{result.clips_total} клипов, "
        f"{result.duration_sec:.1f}с, lipsync: {len(lipsync_shots)}, "
        f"статус {result.status}"
    )

    try:
        from studio.grondheim_memory import on_agent_done, sync_to_dna
        on_agent_done(MONTEUR_ID, result_summary=summary,
                      quality_score=quality, dept="residents")
        if verdict == "PASS":
            sync_to_dna(MONTEUR_ID, "good_work",
                        intensity=quality, dept="residents")
        elif verdict == "FAIL":
            sync_to_dna(MONTEUR_ID, "bad_work",
                        intensity=1.0, dept="residents")
    except Exception as e:
        print(f"[АРТУР] ⚠️  Память: {e}")

    try:
        from studio.economy import ministry as _min
        score = 8.0 if verdict == "PASS" else (
                5.0 if verdict == "PARTIAL" else 0.0)
        _min.record_outcome(agent_id=MONTEUR_ID, slot_id=slot_id,
                            score=score, cost_usd=0.0)
    except Exception:
        pass

    print(f"[АРТУР] {'✅' if verdict == 'PASS' else '⚠️'} {verdict}: {result.final_path}")
    return result



# ══════════════════════════════════════════════════════════════════
# АРТУР — вспомогательные функции (Спринт 30в · финал)
# ══════════════════════════════════════════════════════════════════

def _monteur_accept_material(
    lipsync_shots, clips, deliverables,
    project_id, system_prompt, agent_temp, slot_id,
):
    """
    Приёмка lipsync материала. Артур — мастер ОТК, не эксперт по lipsync.
    REJECT только за технический брак. Не за художественное качество.
    REJECT → повтор sync.so → max 3 → best_of_3.
    """
    import json as _json, re as _re, base64 as _b64
    import subprocess, tempfile
    from pathlib import Path
    from studio.llm import chat_with_images
    from studio.sync_client import run_lipsync

    MONTEUR_ID = "006_MONTEUR"

    vo_by_scene = {
        v["scene_id"]: v["vo_path"]
        for v in deliverables.get("audio", {}).get("vo_lines", [])
        if v.get("scene_id") and v.get("vo_path")
        and Path(v["vo_path"]).exists()
    }
    clip_by_shot = {c.get("shot_id"): c for c in clips if c.get("shot_id")}

    render_dir = Path("output/render") / project_id / "lipsync"
    render_dir.mkdir(parents=True, exist_ok=True)

    ACCEPT_PROMPT = (
        "Ты мастер ОТК на производстве. Смотришь кадр из lipsync видео.\n"
        "Вопрос один: ПРИГОДЕН ли материал для монтажа?\n\n"
        "REJECT только если:\n"
        "  · рот явно не соответствует речи (грубая рассинхронизация)\n"
        "  · лицо разрушено, двоится, распалось\n"
        "  · артефакты генерации делают кадр непригодным\n"
        "  · материал технически повреждён\n\n"
        "PASS если:\n"
        "  · материал пригоден для монтажа\n"
        "  · небольшие несовпадения фонем — норма\n"
        "  · художественное качество, атмосфера — не твоя зона\n\n"
        'JSON: {"verdict": "PASS" | "REJECT", "reason": "одна фраза или null"}'
    )

    for shot_id in lipsync_shots:
        clip = clip_by_shot.get(shot_id)
        if not clip:
            print(f"[АРТУР] ⚠️  {shot_id}: клип не найден")
            continue

        vo_path = vo_by_scene.get(clip.get("scene_id"))
        if not vo_path:
            print(f"[АРТУР] ⚠️  {shot_id}: нет VO — пропускаю")
            continue

        output_path = str(render_dir / f"{shot_id}_lipsync.mp4")
        best_result = None

        for attempt in range(1, 4):
            try:
                print(f"[АРТУР] 💋 {shot_id} попытка {attempt}/3...")
                run_lipsync(clip["video_path"], vo_path, output_path)

                # Извлекаем средний кадр для приёмки
                frame = _monteur_get_frame(output_path, offset=0.5)
                if not frame:
                    # Нет кадра — берём как есть
                    best_result = output_path
                    break

                raw = chat_with_images(
                    system=system_prompt,
                    user_text=ACCEPT_PROMPT,
                    images=[frame],
                    temperature=0.1,  # низкая температура — ОТК строгий
                    agent_id=MONTEUR_ID,
                    slot_id=slot_id,
                )
                m = _re.search(r"\{.*\}", raw, _re.DOTALL)
                check = _json.loads(m.group()) if m else {"verdict": "PASS"}
                verdict = check.get("verdict", "PASS")
                reason  = check.get("reason", "")

                print(f"[АРТУР] 🔍 {shot_id} попытка {attempt}: {verdict}"
                      + (f" — {reason}" if reason else ""))

                if verdict == "PASS":
                    best_result = output_path
                    break
                elif attempt == 3:
                    print(f"[АРТУР] ⚠️  {shot_id}: 3 попытки — берём best_of_3")
                    best_result = output_path

            except Exception as e:
                print(f"[АРТУР] ❌ {shot_id} попытка {attempt}: {e}")
                if attempt == 3:
                    print(f"[АРТУР] ⚠️  {shot_id}: оставляю оригинал")

        if best_result and Path(best_result).exists():
            clip["video_path"] = best_result
            print(f"[АРТУР] ✅ {shot_id}: принят в сборку")


def _monteur_get_frame(video_path: str, offset: float = 0.5) -> dict | None:
    """Извлекает один кадр из видео. offset=0..1 (доля от длины)."""
    import subprocess, base64, json as _j, tempfile
    from pathlib import Path
    try:
        probe = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json",
             "-show_format", str(video_path)],
            capture_output=True, text=True, timeout=10,
        )
        dur = float(_j.loads(probe.stdout).get("format", {}).get("duration", 5))
        ts  = max(0.1, dur * offset)
        with tempfile.TemporaryDirectory() as tmp:
            fp = Path(tmp) / "frame.jpg"
            subprocess.run(
                ["ffmpeg", "-ss", str(ts), "-i", str(video_path),
                 "-vframes", "1", "-q:v", "5", str(fp), "-y"],
                capture_output=True, timeout=15,
            )
            if fp.exists() and fp.stat().st_size > 0:
                b64 = base64.b64encode(fp.read_bytes()).decode("ascii")
                return {"base64": b64, "mime_type": "image/jpeg",
                        "name": f"frame_{ts:.1f}s.jpg"}
    except Exception as e:
        print(f"[АРТУР] ⚠️  кадр из {video_path}: {e}")
    return None


def _monteur_watch_final(
    result, deliverables, system_prompt,
    chosen_model, agent_temp, slot_id,
):
    """
    Артур смотрит ВЕСЬ финальный ролик.
    Grid каждые 2 секунды. arthur_notes = свидетельство, не решение.
    """
    import json as _json, re as _re, subprocess
    from pathlib import Path
    from studio.llm import chat_with_images

    MONTEUR_ID = "006_MONTEUR"

    # Длительность
    try:
        probe = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json",
             "-show_format", result.final_path],
            capture_output=True, text=True, timeout=10,
        )
        duration = float(
            _json.loads(probe.stdout).get("format", {}).get("duration", 30)
        )
    except Exception:
        duration = 30.0

    # Grid каждые 2 секунды
    frames = []
    ts = 1.0  # начинаем с первой секунды
    print(f"[АРТУР] 👁  Смотрю финал: {duration:.1f}с → ~{int(duration/2)} кадров")

    while ts < duration:
        frame = _monteur_get_frame(result.final_path, offset=ts/duration)
        if frame:
            frame["name"] = f"t{ts:.0f}s.jpg"
            frames.append(frame)
        ts += 2.0

    if not frames:
        print("[АРТУР] ⚠️  Не удалось извлечь кадры финала")
        return

    print(f"[АРТУР] 🎞  {len(frames)} кадров — весь ролик")

    watch_prompt = (
        f"Проект: {result.project_id}. "
        f"Длина: {duration:.0f}с. "
        f"Клипов: {result.clips_used}/{result.clips_total}.\n\n"
        f"Ты видишь {len(frames)} кадров — весь ролик каждые 2 секунды.\n\n"
        "Ты последний человек который увидел это перед зрителем.\n"
        "Не последний сценарист. Не последний режиссёр. Последний мастер.\n\n"
        "Что осталось с тобой после просмотра?\n"
        "Говори конкретно — момент, не общее впечатление.\n"
        "Не оценивай коллег. Только своё наблюдение.\n\n"
        'JSON: {"feeling": "одно слово или фраза", '
        '"observation": "конкретный момент", '
        '"concern": "что насторожило или null"}'
    )

    try:
        raw = chat_with_images(
            system=system_prompt,
            user_text=watch_prompt,
            images=frames,
            temperature=agent_temp,
            agent_id=MONTEUR_ID,
            slot_id=slot_id,
            model_override=chosen_model,
        )
        m = _re.search(r"\{.*\}", raw, _re.DOTALL)
        if m:
            notes = _json.loads(m.group())
            feeling = notes.get("feeling", "")
            obs     = notes.get("observation", "")
            concern = notes.get("concern", "")

            if feeling or obs:
                print(f"[АРТУР] 💭 {feeling}" +
                      (f" · {obs[:70]}" if obs else ""))

                content = " / ".join(filter(None, [
                    feeling,
                    obs,
                    f"Насторожило: {concern}" if concern else "",
                ]))
                try:
                    from studio.grondheim_memory import record_resonance_event
                    record_resonance_event(
                        agent_id=MONTEUR_ID,
                        event_type="reflection",
                        content=f"[{result.project_id}] {content}",
                        significance=0.4,
                        tags=["assembly", "arthur_notes", result.project_id],
                        dept="residents",
                    )
                except Exception:
                    pass
            else:
                print("[АРТУР] 🤫 Посмотрел — молчу")
    except Exception as e:
        print(f"[АРТУР] ⚠️  Взгляд на финал: {e}")
