"""
patch_run_monteur.py — Спринт 30
================================
Заменяет run_monteur_assembly() в studio/residents_manager.py.

Артур теперь настоящий агент:
  1. Читает forge/prompt.md + маску цеха
  2. Читает sensory_memory.json — что Шеф говорил перед монтажом
  3. Читает ДНК → temperature
  4. Извлекает кадры из клипов → vision
  5. Вызывает LLM → решение: какие клипы dialog, что делать
  6. Для dialog shots: запускает sync.so (lipsync)
  7. Сам проверяет lipsync результат через vision
  8. Запускает ffmpeg → final.mp4
  9. Пишет в память, экономику, хроники

Как применить:
  Заменить функцию run_monteur_assembly() в studio/residents_manager.py
  на код ниже. Остальное в файле не трогать.
"""

# ══════════════════════════════════════════════════════════════════
# НОВАЯ run_monteur_assembly()
# Вставить вместо старой в studio/residents_manager.py
# ══════════════════════════════════════════════════════════════════

NEW_RUN_MONTEUR = '''
def run_monteur_assembly(
    deliverables: dict,
    project_id: str = "",
    slot_id: str = "video_long",
) -> "AssemblyResult":
    """
    Артур — настоящий агент.

    Этап 1: LLM смотрит на материал
      - читает промпт + маску цеха
      - читает sensory (что Шеф говорил перед монтажом)
      - получает кадры из клипов через vision
      - решает: какие клипы dialog, нужен ли lipsync
      - выбирает модель сам из ДНК

    Этап 2: Работа руками
      - для dialog shots: sync.so → lipsync mp4 → vision проверка
      - ffmpeg: concat + amix → final.mp4

    Этап 3: Взгляд после
      - смотрит на final.mp4
      - пишет arthur_notes в хроники
      - обновляет память и экономику
    """
    import json as _json
    import re as _re
    import base64 as _b64
    import subprocess
    import tempfile
    import datetime
    from pathlib import Path

    from studio.llm import chat_with_images, chat, stress_to_temperature
    from studio.grondheim_memory import (
        on_agent_wake, on_agent_done, sync_to_dna,
        load_sensory, record_resonance_event,
    )

    MONTEUR_ID  = "006_MONTEUR"
    MONTEUR_DIR = Path("studio/modules/residents/006_MONTEUR")
    project_id  = project_id or deliverables.get("project_id", "unknown")

    print(f"\\n[АРТУР] 🎬 Начинаю работу над: {project_id}")

    # ── Загружаем промпт ────────────────────────────────────────
    prompt_path = MONTEUR_DIR / "forge" / "prompt.md"
    mask_path   = MONTEUR_DIR / "forge" / "masks" / f"{slot_id}.md"

    system_prompt = ""
    if prompt_path.exists():
        system_prompt = prompt_path.read_text(encoding="utf-8")
    if mask_path.exists():
        system_prompt += "\\n\\n" + mask_path.read_text(encoding="utf-8")

    if not system_prompt.strip():
        print("[АРТУР] ⚠️  Промпт не найден — работаю как скрипт")
        from studio.assembly.monteur import assemble
        return assemble(deliverables=deliverables, project_id=project_id, slot_id=slot_id)

    # ── Пробуждение в городе ────────────────────────────────────
    on_agent_wake(MONTEUR_ID, dept="residents")

    # ── ДНК → temperature ───────────────────────────────────────
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
            print(f"[АРТУР] 🧬 temperature из ДНК: {agent_temp}")
    except Exception as e:
        print(f"[АРТУР] ⚠️  ДНК не загружена: {e}")

    # ── Читаем sensory — что Шеф говорил ────────────────────────
    chef_notes = ""
    try:
        sensory = load_sensory(MONTEUR_ID, "residents")
        entries = sensory.get("entries", [])
        # Берём последние 5 записей — свежий контекст
        recent = [e.get("feeling") or e.get("content", "") for e in entries[-5:] if e]
        recent = [r for r in recent if r]
        if recent:
            chef_notes = "=== ЧТО ШЕФ ГОВОРИЛ ПЕРЕД МОНТАЖОМ ===\\n"
            chef_notes += "\\n".join(f"  · {r}" for r in recent)
            chef_notes += "\\n=== КОНЕЦ ==="
            print(f"[АРТУР] 💬 Помню разговор с Шефом: {len(recent)} записей")
    except Exception as e:
        print(f"[АРТУР] ⚠️  Sensory не загружена: {e}")

    # ── Извлекаем кадры из клипов для vision ────────────────────
    clips = deliverables.get("video_clips", [])
    clip_frames = []  # [{clip_info, frames[]}]

    for clip in clips[:6]:  # max 6 клипов чтобы не перегружать контекст
        vpath = clip.get("video_path")
        if not vpath or not Path(vpath).exists():
            continue
        frames = _extract_clip_frame(vpath)
        if frames:
            clip_frames.append({
                "shot_id":    clip.get("shot_id", "?"),
                "scene_id":   clip.get("scene_id", "?"),
                "shot_type":  clip.get("shot_type"),   # может быть None — Артур сам решит
                "duration":   clip.get("duration_sec", 0),
                "video_path": vpath,
                "frames":     frames,
            })

    print(f"[АРТУР] 🎞  Кадры извлечены из {len(clip_frames)}/{len(clips)} клипов")

    # ── Собираем все изображения для vision ─────────────────────
    all_images = []
    clip_index_text = ""

    for i, cf in enumerate(clip_frames, 1):
        all_images.extend(cf["frames"])
        shot_type_hint = f"shot_type={cf['shot_type']}" if cf["shot_type"] else "shot_type=НЕИЗВЕСТЕН"
        clip_index_text += (
            f"  [{i}] shot_id={cf['shot_id']} scene={cf['scene_id']} "
            f"{shot_type_hint} dur={cf['duration']}s\\n"
        )

    # ── VO линии для сопоставления с dialog ─────────────────────
    vo_lines = deliverables.get("audio", {}).get("vo_lines", [])
    vo_index = ""
    for vo in vo_lines:
        vo_index += f"  scene_id={vo.get('scene_id')} → vo_path={vo.get('vo_path')}\\n"

    # ── Контекст для LLM ─────────────────────────────────────────
    context = f"""=== ПАКЕТ ОТ БОБА ===
project_id: {project_id}
platform: {deliverables.get("platform", "?")}
клипов всего: {len(clips)}
клипов с кадрами: {len(clip_frames)}

{clip_index_text}

=== VO ЛИНИИ ОТ СЭМА ===
{vo_index or "  (нет VO)"}

{chef_notes}

=== ТВОЯ ЗАДАЧА ===
Ты видишь кадры из клипов. Смотри внимательно.

1. Для каждого клипа определи: нужен ли липсинг?
   dialog = персонаж говорит крупным/средним планом, рот важен
   action/broll = рот не важен, Wan2.2 достаточно

2. Если shot_type уже проставлен Лукасом — доверяй ему.
   Если shot_type=None — решай сам по кадру.

3. Для dialog клипов: нужно запустить lipsync через sync.so
   (video_path + vo_path от Сэма по scene_id)

4. Выбери модель для этапа взгляда на финал.

Ответь строго в JSON. Ничего кроме JSON.
"""

    # ── Вызов LLM — Артур смотрит и решает ──────────────────────
    print(f"[АРТУР] 🤔 Смотрю на материал...")
    try:
        raw = chat_with_images(
            system=system_prompt,
            user_text=context,
            images=all_images if all_images else None,
            temperature=agent_temp,
            agent_id=MONTEUR_ID,
            slot_id=slot_id,
        )
    except Exception as e:
        print(f"[АРТУР] ❌ LLM ошибка: {e} — работаю без LLM решения")
        raw = "{}"

    # ── Парсим решение ───────────────────────────────────────────
    decision = {}
    m = _re.search(r"\\{.*\\}", raw, _re.DOTALL)
    if m:
        try:
            decision = _json.loads(m.group())
        except Exception:
            pass

    chosen_model   = decision.get("chosen_model", "google/gemini-2.5-flash")
    lipsync_shots  = decision.get("lipsync_shots", [])   # [shot_id, ...]
    arthur_thought = decision.get("first_impression", "")

    print(f"[АРТУР] 🎯 Решение: lipsync для {len(lipsync_shots)} шотов | модель: {chosen_model}")
    if arthur_thought:
        print(f"[АРТУР] 💭 {arthur_thought}")

    # ── Этап 2: Lipsync для dialog shots ────────────────────────
    if lipsync_shots:
        _run_lipsync_for_shots(
            lipsync_shots=lipsync_shots,
            clip_frames=clip_frames,
            deliverables=deliverables,
            project_id=project_id,
            system_prompt=system_prompt,
            chosen_model=chosen_model,
            agent_temp=agent_temp,
            slot_id=slot_id,
        )

    # ── Этап 3: Сборка ffmpeg ────────────────────────────────────
    from studio.assembly.monteur import assemble, AssemblyResult
    print(f"[АРТУР] 🔨 Запускаю сборку...")
    result = assemble(
        deliverables=deliverables,
        project_id=project_id,
        slot_id=slot_id,
    )

    # ── Этап 4: Взгляд на финал ─────────────────────────────────
    if result.final_path and Path(result.final_path).exists():
        _arthur_final_look(
            result=result,
            deliverables=deliverables,
            system_prompt=system_prompt,
            chosen_model=chosen_model,
            agent_temp=agent_temp,
            slot_id=slot_id,
        )

    # ── Память и экономика ───────────────────────────────────────
    verdict = "PASS" if result.status == "DONE" else (
        "PARTIAL" if result.status == "PARTIAL" else "FAIL"
    )
    summary = (
        f"Собрал {result.clips_used}/{result.clips_total} клипов, "
        f"{result.duration_sec:.1f}с, lipsync: {len(lipsync_shots)} шотов, "
        f"статус {result.status}"
    )
    quality = 1.0 if verdict == "PASS" else (0.6 if verdict == "PARTIAL" else 0.2)

    on_agent_done(MONTEUR_ID, result_summary=summary,
                  quality_score=quality, dept="residents")

    if verdict == "PASS":
        sync_to_dna(MONTEUR_ID, "good_work", intensity=quality, dept="residents")
    elif verdict == "FAIL":
        sync_to_dna(MONTEUR_ID, "bad_work", intensity=1.0, dept="residents")

    try:
        from studio.economy import ministry as _min
        score = 8.0 if verdict == "PASS" else (5.0 if verdict == "PARTIAL" else 0.0)
        _min.record_outcome(agent_id=MONTEUR_ID, slot_id=slot_id,
                            score=score, cost_usd=0.0)
    except Exception:
        pass

    return result


# ── Вспомогательные функции ──────────────────────────────────────────

def _extract_clip_frame(video_path: str) -> list:
    """Извлекает один кадр из середины клипа. Возвращает список для vision."""
    import subprocess, base64, json as _j, tempfile
    from pathlib import Path

    try:
        probe = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json",
             "-show_format", str(video_path)],
            capture_output=True, text=True, timeout=10,
        )
        dur = 5.0
        try:
            dur = float(_j.loads(probe.stdout).get("format", {}).get("duration", 5))
        except Exception:
            pass

        ts = dur * 0.5
        with tempfile.TemporaryDirectory() as tmp:
            fp = Path(tmp) / "frame.jpg"
            subprocess.run(
                ["ffmpeg", "-ss", str(ts), "-i", str(video_path),
                 "-vframes", "1", "-q:v", "4", str(fp), "-y"],
                capture_output=True, timeout=15,
            )
            if fp.exists() and fp.stat().st_size > 0:
                b64 = base64.b64encode(fp.read_bytes()).decode("ascii")
                name = Path(video_path).stem
                return [{"base64": b64, "mime_type": "image/jpeg",
                         "name": f"{name}_mid.jpg"}]
    except Exception as e:
        print(f"[АРТУР] ⚠️  Кадр не извлечь из {video_path}: {e}")
    return []


def _run_lipsync_for_shots(
    lipsync_shots, clip_frames, deliverables,
    project_id, system_prompt, chosen_model, agent_temp, slot_id,
):
    """Запускает lipsync для dialog shots через sync.so. Проверяет через vision."""
    import re as _re, json as _json, base64 as _b64
    from pathlib import Path
    from studio.llm import chat_with_images

    MONTEUR_ID = "006_MONTEUR"

    # Индекс VO по scene_id
    vo_by_scene = {
        v["scene_id"]: v["vo_path"]
        for v in deliverables.get("audio", {}).get("vo_lines", [])
        if v.get("scene_id") and v.get("vo_path") and Path(v["vo_path"]).exists()
    }

    # Индекс клипов по shot_id
    clip_by_shot = {cf["shot_id"]: cf for cf in clip_frames}

    render_dir = Path("output/render") / project_id / "lipsync"
    render_dir.mkdir(parents=True, exist_ok=True)

    for shot_id in lipsync_shots:
        cf = clip_by_shot.get(shot_id)
        if not cf:
            print(f"[АРТУР] ⚠️  shot {shot_id}: клип не найден — пропускаю")
            continue

        video_path = cf["video_path"]
        scene_id   = cf["scene_id"]
        vo_path    = vo_by_scene.get(scene_id)

        if not vo_path:
            print(f"[АРТУР] ⚠️  shot {shot_id}: нет VO для scene {scene_id} — пропускаю")
            continue

        output_path = str(render_dir / f"{shot_id}_lipsync.mp4")

        # max 3 попытки
        best_result = None
        for attempt in range(1, 4):
            try:
                print(f"[АРТУР] 💋 Lipsync {shot_id} попытка {attempt}/3...")
                from studio.sync_client import run_lipsync
                run_lipsync(video_path, vo_path, output_path)

                # Vision проверка результата
                frames = _extract_clip_frame(output_path)
                if not frames:
                    print(f"[АРТУР] ⚠️  {shot_id}: кадры не извлечь для проверки")
                    best_result = output_path
                    break

                check_prompt = (
                    "Ты смотришь на кадр из lipsync видео. "
                    "Проверь: лицо естественное? нет артефактов? рот в нормальном положении? "
                    "Ответь в JSON: {\\\"verdict\\\": \\\"APPROVED\\\" | \\\"REJECTED\\\", "
                    "\\\"score\\\": 0-10, \\\"note\\\": \\\"одна фраза\\\"}"
                )
                try:
                    raw_check = chat_with_images(
                        system=system_prompt,
                        user_text=check_prompt,
                        images=frames,
                        temperature=agent_temp,
                        agent_id=MONTEUR_ID,
                        slot_id=slot_id,
                    )
                    m = _re.search(r"\\{.*\\}", raw_check, _re.DOTALL)
                    if m:
                        check = _json.loads(m.group())
                        verdict = check.get("verdict", "APPROVED")
                        score   = check.get("score", 7)
                        note    = check.get("note", "")
                        print(f"[АРТУР] 👁  {shot_id} попытка {attempt}: {verdict} ({score}/10) — {note}")

                        if verdict == "APPROVED" or attempt == 3:
                            best_result = output_path
                            break
                    else:
                        best_result = output_path
                        break
                except Exception as e:
                    print(f"[АРТУР] ⚠️  Vision проверка упала: {e}")
                    best_result = output_path
                    break

            except Exception as e:
                print(f"[АРТУР] ❌ Lipsync {shot_id} попытка {attempt}: {e}")
                if attempt == 3:
                    print(f"[АРТУР] ⚠️  {shot_id}: все попытки провалились — оставляю оригинал")

        # Если lipsync получился — заменяем video_path в deliverables
        if best_result and Path(best_result).exists():
            for clip in deliverables.get("video_clips", []):
                if clip.get("shot_id") == shot_id:
                    clip["video_path"] = best_result
                    print(f"[АРТУР] ✅ {shot_id}: заменён на lipsync версию")
                    break


def _arthur_final_look(
    result, deliverables, system_prompt,
    chosen_model, agent_temp, slot_id,
):
    """Артур смотрит на финальный ролик. Пишет arthur_notes в хроники."""
    import re as _re, json as _json
    from pathlib import Path
    from studio.llm import chat_with_images
    from studio.grondheim_memory import record_resonance_event

    MONTEUR_ID = "006_MONTEUR"

    frames = _extract_clip_frame(result.final_path)
    # Дополнительно берём начало и конец
    try:
        import subprocess, base64 as _b64, tempfile as _tmp
        probe = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json",
             "-show_format", result.final_path],
            capture_output=True, text=True, timeout=10,
        )
        dur = float(_json.loads(probe.stdout).get("format", {}).get("duration", 10))
        for ts_factor, label in [(0.05, "начало"), (0.92, "конец")]:
            ts = max(0.5, dur * ts_factor)
            with _tmp.TemporaryDirectory() as tmp:
                fp = Path(tmp) / "f.jpg"
                subprocess.run(
                    ["ffmpeg", "-ss", str(ts), "-i", result.final_path,
                     "-vframes", "1", "-q:v", "4", str(fp), "-y"],
                    capture_output=True, timeout=15,
                )
                if fp.exists() and fp.stat().st_size > 0:
                    b64 = _b64.b64encode(fp.read_bytes()).decode("ascii")
                    frames.append({"base64": b64, "mime_type": "image/jpeg",
                                   "name": f"final_{label}.jpg"})
    except Exception:
        pass

    if not frames:
        return

    look_prompt = (
        f"Проект: {result.project_id}. "
        f"Клипов: {result.clips_used}/{result.clips_total}. "
        f"Длина: {result.duration_sec:.0f}с. "
        f"Платформа: {deliverables.get('platform', '?')}.\\n\\n"
        "Ты последний кто увидел что получилось. Три кадра: начало, середина, конец.\\n"
        "Не критикуй. Не оценивай коллег. Просто скажи что осталось.\\n"
        "JSON: {\\\"feeling\\\": \\\"строка или null\\\", "
        "\\\"observation\\\": \\\"строка или null\\\", "
        "\\\"concern\\\": \\\"строка или null\\\"}"
    )

    try:
        raw = chat_with_images(
            system=system_prompt,
            user_text=look_prompt,
            images=frames,
            temperature=agent_temp,
            agent_id=MONTEUR_ID,
            slot_id=slot_id,
        )
        m = _re.search(r"\\{.*\\}", raw, _re.DOTALL)
        if m:
            notes = _json.loads(m.group())
            feeling = notes.get("feeling") or ""
            obs     = notes.get("observation") or ""
            concern = notes.get("concern") or ""

            if feeling or obs:
                print(f"[АРТУР] 💭 {feeling}" + (f" · {obs[:60]}" if obs else ""))
                content_parts = []
                if feeling:
                    content_parts.append(f"Ощущение: {feeling}")
                if obs:
                    content_parts.append(f"Заметил: {obs}")
                if concern:
                    content_parts.append(f"Насторожило: {concern}")
                content = " / ".join(content_parts)
                record_resonance_event(
                    agent_id=MONTEUR_ID,
                    event_type="reflection",
                    content=f"[{result.project_id}] {content}",
                    significance=0.4,
                    tags=["assembly", "arthur_notes", result.project_id],
                    dept="residents",
                )
            else:
                print("[АРТУР] 🤫 Ничего не зацепило — молчу")
    except Exception as e:
        print(f"[АРТУР] ⚠️  Взгляд на финал упал: {e}")
'''

print("Код готов. Вставить в studio/residents_manager.py")
print("Заменить функцию run_monteur_assembly() и добавить")
print("вспомогательные функции _extract_clip_frame,")
print("_run_lipsync_for_shots, _arthur_final_look в конец файла.")
