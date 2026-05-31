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
    """Sbrosit' kesh promptov Ole."""
    global _prompt_cache
    for k in [k for k in list(_prompt_cache) if k.startswith("ole_")]:
        del _prompt_cache[k]


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
    Артур — настоящий агент. Спринт 30.

    Этап 1: LLM смотрит кадры клипов через vision
      - читает промпт + маску цеха + sensory (разговоры с Шефом)
      - решает: какие shots нужен lipsync
      - выбирает модель из ДНК

    Этап 2: Работа
      - dialog shots → sync.so → lipsync mp4 → vision проверка
      - ffmpeg: concat + amix → final.mp4

    Этап 3: Взгляд на финал
      - arthur_notes в хроники города
    """
    import json as _json
    import re as _re
    import base64 as _b64
    import subprocess
    import tempfile
    from pathlib import Path

    from studio.llm import chat_with_images, stress_to_temperature

    MONTEUR_ID  = "006_MONTEUR"
    MONTEUR_DIR = Path("studio/modules/residents/006_MONTEUR")
    project_id  = project_id or deliverables.get("project_id", "unknown")

    print(f"\n[АРТУР] 🎬 Начинаю работу над: {project_id}")

    # ── Промпт ──────────────────────────────────────────────────
    prompt_path = MONTEUR_DIR / "forge" / "prompt.md"
    mask_path   = MONTEUR_DIR / "forge" / "masks" / f"{slot_id}.md"
    system_prompt = ""
    if prompt_path.exists():
        system_prompt = prompt_path.read_text(encoding="utf-8")
    if mask_path.exists():
        system_prompt += "\n\n" + mask_path.read_text(encoding="utf-8")

    if not system_prompt.strip():
        print("[АРТУР] ⚠️  Промпт не найден — работаю как скрипт")
        from studio.assembly.monteur import assemble
        return assemble(deliverables=deliverables, project_id=project_id, slot_id=slot_id)

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
        recent  = [e.get("feeling") or e.get("content", "") for e in entries[-5:] if e]
        recent  = [r for r in recent if r]
        if recent:
            chef_notes = "=== ЧТО ШЕФ ГОВОРИЛ ПЕРЕД МОНТАЖОМ ===\n"
            chef_notes += "\n".join(f"  · {r}" for r in recent)
            chef_notes += "\n=================================="
            print(f"[АРТУР] 💬 Помню {len(recent)} записей из разговора с Шефом")
    except Exception as e:
        print(f"[АРТУР] ⚠️  Sensory: {e}")

    # ── Кадры из клипов для vision ───────────────────────────────
    clips       = deliverables.get("video_clips", [])
    clip_frames = []

    for clip in clips[:6]:
        vpath = clip.get("video_path")
        if not vpath or not Path(vpath).exists():
            continue
        frames = _monteur_extract_frame(vpath)
        if frames:
            clip_frames.append({
                "shot_id":    clip.get("shot_id", "?"),
                "scene_id":   clip.get("scene_id", "?"),
                "shot_type":  clip.get("shot_type"),
                "duration":   clip.get("duration_sec", 0),
                "video_path": vpath,
                "frames":     frames,
            })

    print(f"[АРТУР] 🎞  Кадры: {len(clip_frames)}/{len(clips)} клипов")

    # ── Собираем изображения и индекс ────────────────────────────
    all_images     = []
    clip_index_txt = ""
    for i, cf in enumerate(clip_frames, 1):
        all_images.extend(cf["frames"])
        stype = f"shot_type={cf['shot_type']}" if cf["shot_type"] else "shot_type=НЕИЗВЕСТЕН"
        clip_index_txt += (
            f"  [{i}] shot_id={cf['shot_id']} "
            f"scene={cf['scene_id']} {stype} "
            f"dur={cf['duration']}s\n"
        )

    vo_lines = deliverables.get("audio", {}).get("vo_lines", [])
    vo_index = "".join(
        f"  scene_id={v.get('scene_id')} → vo_path={v.get('vo_path')}\n"
        for v in vo_lines
    )

    # ── Контекст ─────────────────────────────────────────────────
    context = (
        f"=== ПАКЕТ ОТ БОБА ===\n"
        f"project_id: {project_id}\n"
        f"platform: {deliverables.get('platform', '?')}\n"
        f"клипов всего: {len(clips)}\n\n"
        f"{clip_index_txt}\n"
        f"=== VO ЛИНИИ ОТ СЭМА ===\n"
        f"{vo_index or '  (нет VO)'}\n"
        f"{chef_notes}\n\n"
        "Смотри на кадры. Для каждого клипа реши: нужен lipsync?\n"
        "dialog = говорит крупным/средним планом. action/broll = нет.\n"
        "Ответь строго в JSON."
    )

    # ── LLM решение ─────────────────────────────────────────────
    print("[АРТУР] 🤔 Смотрю на материал...")
    decision = {}
    try:
        raw = chat_with_images(
            system=system_prompt,
            user_text=context,
            images=all_images if all_images else None,
            temperature=agent_temp,
            agent_id=MONTEUR_ID,
            slot_id=slot_id,
        )
        m = _re.search(r"\{.*\}", raw, _re.DOTALL)
        if m:
            decision = _json.loads(m.group())
    except Exception as e:
        print(f"[АРТУР] ⚠️  LLM: {e}")

    lipsync_shots  = decision.get("lipsync_shots", [])
    chosen_model   = decision.get("chosen_model", "google/gemini-2.5-flash")
    first_thought  = decision.get("first_impression", "")

    print(f"[АРТУР] 🎯 lipsync для {len(lipsync_shots)} шотов | модель: {chosen_model}")
    if first_thought:
        print(f"[АРТУР] 💭 {first_thought}")

    # ── Lipsync ─────────────────────────────────────────────────
    if lipsync_shots:
        _monteur_run_lipsync(
            lipsync_shots=lipsync_shots,
            clip_frames=clip_frames,
            deliverables=deliverables,
            project_id=project_id,
            system_prompt=system_prompt,
            agent_temp=agent_temp,
            slot_id=slot_id,
        )

    # ── Сборка ffmpeg ────────────────────────────────────────────
    from studio.assembly.monteur import assemble
    print("[АРТУР] 🔨 Собираю...")
    result = assemble(
        deliverables=deliverables,
        project_id=project_id,
        slot_id=slot_id,
    )

    # ── Взгляд на финал ─────────────────────────────────────────
    from pathlib import Path as _Path
    if result.final_path and _Path(result.final_path).exists():
        _monteur_final_look(
            result=result,
            deliverables=deliverables,
            system_prompt=system_prompt,
            agent_temp=agent_temp,
            slot_id=slot_id,
        )

    # ── Память и экономика ───────────────────────────────────────
    verdict = "PASS" if result.status == "DONE" else (
              "PARTIAL" if result.status == "PARTIAL" else "FAIL")
    summary = (
        f"Собрал {result.clips_used}/{result.clips_total} клипов, "
        f"{result.duration_sec:.1f}с, lipsync: {len(lipsync_shots)} шотов, "
        f"статус {result.status}"
    )
    quality = 1.0 if verdict == "PASS" else (0.6 if verdict == "PARTIAL" else 0.2)

    try:
        from studio.grondheim_memory import on_agent_done, sync_to_dna
        on_agent_done(MONTEUR_ID, result_summary=summary,
                      quality_score=quality, dept="residents")
        if verdict == "PASS":
            sync_to_dna(MONTEUR_ID, "good_work", intensity=quality, dept="residents")
        elif verdict == "FAIL":
            sync_to_dna(MONTEUR_ID, "bad_work", intensity=1.0, dept="residents")
    except Exception as e:
        print(f"[АРТУР] ⚠️  Память: {e}")

    try:
        from studio.economy import ministry as _min
        score = 8.0 if verdict == "PASS" else (5.0 if verdict == "PARTIAL" else 0.0)
        _min.record_outcome(agent_id=MONTEUR_ID, slot_id=slot_id,
                            score=score, cost_usd=0.0)
    except Exception:
        pass

    print(f"[АРТУР] {'✅' if verdict == 'PASS' else '⚠️'} {verdict}: {result.final_path}")
    return result
    """Запускает Монтажёра — собирает финальный ролик из deliverables Боба.

    Вызывается из hooks.py после _bob_finalize когда chain_status APPROVED.
    Один Монтажёр работает со всеми цехами которые производят видео.

    Args:
        deliverables: dict из state["_last_output"]["deliverables"]
        project_id:   ID проекта (для папки output/render/)
        slot_id:      цех-источник (video_long, video_shorts, ...)

    Returns:
        AssemblyResult с полями:
            status      — "DONE" | "PARTIAL" | "FAILED"
            final_path  — путь к final.mp4 или None
            duration_sec, clips_used, clips_total, has_audio, errors
    """
    try:
        from studio.assembly.monteur import assemble
    except ImportError as e:
        print(f"[MONTEUR] ❌ monteur.py не найден: {e}")
        # Возвращаем заглушку с нужными полями
        class _FailResult:
            status = "FAILED"
            final_path = None
            duration_sec = 0.0
            clips_used = 0
            clips_total = 0
            has_audio = False
            has_vo = False
            has_sfx = False
            errors = [str(e)]
            assembled_at = ""
        return _FailResult()

    project_id = project_id or deliverables.get("project_id", "unknown")

    print(f"[MONTEUR] 🎬 Запуск сборки: {project_id} (цех: {slot_id})")

    result = assemble(
        deliverables=deliverables,
        project_id=project_id,
        slot_id=slot_id,
    )

    # Логируем итог
    if result.status == "DONE":
        print(
            f"[MONTEUR] ✅ {project_id} → {result.final_path} "
            f"({result.clips_used}/{result.clips_total} клипов, "
            f"{result.duration_sec:.1f}с)"
        )
    elif result.status == "PARTIAL":
        print(
            f"[MONTEUR] ⚠️  {project_id} — частично. "
            f"Ошибки: {result.errors[:2]}"
        )
    else:
        print(
            f"[MONTEUR] ❌ {project_id} — сборка упала. "
            f"Ошибки: {result.errors[:2]}"
        )

    return result
