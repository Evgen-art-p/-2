# studio/modules/turbo/hooks.py
# Студия «Шесть Пальцев» · 2026
# v4.0 — Полный конвейер до mp4:
#         A03 → картинки (Banana) + анимация (Wan2.2 I2V)
#         A02 → озвучка (ElevenLabs музыка + SFX + CosyVoice VO)
#         A05 → обложки + deliverables + Монтажёр (ffmpeg → final.mp4)
#
# Три новых слоя по образцу video_long/hooks.py:
#   _a03_generate_clips()   ← Wan2.2 I2V по каждому кадру
#   _a02_generate_audio()   ← ElevenLabs + CosyVoice
#   _monteur_after_a05()    ← residents_manager.run_monteur_assembly

import json
import re
import shutil
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from studio.assembly.constants import generate_image, generate_with_refs, OUTPUT_DIR
from studio.llm import chat_with_images

# ОТК — vision_client по образцу video_long
try:
    from studio.vision_client import generate_with_vision_check as _vision_otk
    _VISION_OTK_ENABLED = True
    print("[TURBO OTK] 👁 vision_client подключён")
except ImportError:
    _VISION_OTK_ENABLED = False
    print("[TURBO OTK] ⚠️ vision_client не найден — работаем без ОТК")

# Монтажёр — финальная сборка после A05
try:
    from studio.residents_manager import run_monteur_assembly as _run_monteur
    _MONTEUR_ENABLED = True
    print("[TURBO MONTEUR] 🎬 Монтажёр подключён")
except ImportError:
    _MONTEUR_ENABLED = False
    def _run_monteur(deliverables, project_id="", slot_id="turbo"):
        print("[TURBO MONTEUR] ⚠️ residents_manager не найден — сборка пропущена")


# ============================================================
# НАСТРОЙКИ КАЧЕСТВА
# ============================================================

MAX_ATTEMPTS      = 5   # максимум попыток на одну картинку
QUALITY_THRESHOLD = 6   # score ниже этого → пробуем ещё раз
_FRAME_TIMEOUT    = 300 # таймаут на генерацию одного клипа (сек)
_RETRY_DELAYS     = [5, 10]


# ============================================================
# HOOKS API
# ============================================================

def on_before_agent(state: dict, worker_id: str, context: str) -> str:
    return context


def on_after_agent(state: dict, worker_id: str, human_text: str, meta: dict) -> dict:
    if worker_id == "A02":
        if state.get("_a02_audio_review_pending"):
            # Второй вызов A02 — Мими слушает результат
            _a02_apply_audio_review(state, human_text)
        else:
            # Первый вызов A02 — генерация промптов + аудио
            _a02_generate_audio(state, human_text)
            # audio_files уже положены в state → pipeline вызовет A02 снова
    elif worker_id == "A03":
        if state.get("_a03_clip_review_pending"):
            # Третий вызов A03 — смотрит на grid клипов
            _a03_apply_clip_review(state, human_text)
        elif state.get("_a03_self_review_pending"):
            # Второй вызов A03 — смотрит на картинки, потом анимация + grid
            _a03_apply_self_review(state, human_text)
            _a03_generate_clips(state)      # анимация → grid → clip_review_pending
        else:
            # Первый вызов A03 — генерация картинок
            _a03_generate_keyframes(state, human_text)
            # vision_images уже положены → pipeline вызовет A03 снова
    elif worker_id == "A05":
        _a05_generate_thumbnails_and_deliverables(state, human_text)
        _a05_record_ministry(state)
        if _MONTEUR_ENABLED:
            _monteur_after_a05(state)
    return {}


# ============================================================
# A02 AUDIO-REVIEW — Мими слушает результат (второй вызов)
# По образцу _sam_generate_audio Этап 2 из video_long
# ============================================================

def _a02_apply_audio_review(state: dict, human_text: str):
    """
    Второй вызов A02 — Мими получила аудиофайл и слушает его.
    Применяем audio_assessment: APPROVED или REJECTED.
    При REJECTED — перегенерируем с новым промптом.

    По образцу Сэма (A10) из video_long — тот же стандарт:
    посекундная разметка, один артефакт = REJECTED целиком.
    """
    # Убираем флаг и audio_files
    state.pop("audio_files", None)
    state.pop("_a02_audio_review_pending", None)
    mimi_sound = state.pop("_a02_mimi_sound_for_review", {})

    data = _parse_json(human_text)
    if not data:
        print("[A02 AUDIO-REVIEW] JSON не найден — принимаю как есть")
        return

    my_output  = data.get("my_output", data)
    review     = my_output.get("mimi_sound", my_output)
    music_rev  = review.get("music", {})
    assessment = music_rev.get("audio_assessment", {})

    if not assessment:
        print("[A02 AUDIO-REVIEW] audio_assessment отсутствует — принимаю как есть")
        _write_chain_key(state, "mimi_sound", mimi_sound)
        return

    verdict  = assessment.get("verdict", "APPROVED")
    score    = assessment.get("score", 7.0)
    note     = assessment.get("note", "")
    timeline = assessment.get("timeline", "")
    revised  = music_rev.get("revised_prompt") or assessment.get("revised_prompt")

    print(f"[A02 AUDIO-REVIEW] {verdict} (score={score}) — {note[:60]}")
    if timeline:
        print(f"[A02 AUDIO-REVIEW]   timeline: {timeline[:100]}")

    if verdict == "REJECTED" and revised:
        print(f"[A02 AUDIO-REVIEW] 🔄 Перегенерирую музыку: {revised[:80]}...")
        try:
            from studio.elevenlabs_client import generate_music
            project_id  = _get_project_id(state)
            project_dir = OUTPUT_DIR / project_id
            project_dir.mkdir(parents=True, exist_ok=True)
            slot_id     = state.get("_slot_id", "turbo")

            music       = mimi_sound.get("music", {})
            duration    = float(music.get("duration_sec", 30))
            filename    = f"music_{_slugify(project_id)}_revised.mp3"

            raw_path = generate_music(
                prompt=revised,
                duration_sec=duration,
                filename=filename,
                agent_id="A02",
                slot_id=slot_id,
            )
            dest = project_dir / filename
            Path(raw_path).replace(dest)
            music["audio_path"]        = str(dest)
            music["prompt"]            = revised
            music["audio_assessment"]  = assessment
            mimi_sound["music"]        = music
            print(f"[A02 AUDIO-REVIEW] ✅ Ревизия: {dest.name}")
        except Exception as e:
            print(f"[A02 AUDIO-REVIEW] ❌ Ревизия упала: {e} — оставляю оригинал")
    else:
        # APPROVED — просто сохраняем assessment
        music = mimi_sound.get("music", {})
        music["audio_assessment"] = assessment
        mimi_sound["music"] = music
        print(f"[A02 AUDIO-REVIEW] ✅ APPROVED — трек принят")

    _write_chain_key(state, "mimi_sound", mimi_sound)


# ============================================================
# НОВОЕ: A02 МИМИ — ОЗВУЧКА
# ElevenLabs музыка + SFX batch + CosyVoice VO
# По образцу _sam_generate_audio из video_long/hooks.py
# ============================================================

def _a02_generate_audio(state: dict, human_text: str):
    """
    A02 Мими — генерация аудио. Точная копия _sam_generate_audio из video_long.

    Читает mimi_sound из ответа агента:
      music.prompt     → ElevenLabs generate_music()
      sfx_list[]       → ElevenLabs generate_sfx_batch()
      vo_lines[]       → CosyVoice generate_speech()

    Пишет обратно:
      mimi_sound.music.audio_path
      mimi_sound.sfx_list[*].sfx_path
      mimi_sound.vo_lines[*].vo_path
    """
    try:
        from studio.elevenlabs_client import generate_music, generate_sfx_batch
    except ImportError:
        print("[TURBO A02] ❌ elevenlabs_client не найден — аудио пропускаю")
        return

    data = _parse_json(human_text)
    if not data:
        print("[TURBO A02] JSON не найден — пропускаю")
        return

    my_output  = data.get("my_output", data)
    mimi_sound = my_output.get("mimi_sound", {})
    if not mimi_sound:
        print("[TURBO A02] mimi_sound пуст — пропускаю")
        return

    project_id  = _get_project_id(state)
    project_dir = OUTPUT_DIR / project_id
    project_dir.mkdir(parents=True, exist_ok=True)
    slot_id = state.get("_slot_id", "turbo")

    # ── 1. МУЗЫКА — точно как _sam_generate_audio ──────────────────
    # Мими пишет music.prompt и music.duration_sec
    # Fallback: suno_prompt на верхнем уровне mimi_sound
    music       = mimi_sound.get("music", {})
    if isinstance(music, str):
        music = {"prompt": music}
    music_prompt   = music.get("prompt", "") or mimi_sound.get("suno_prompt", "")
    music_duration = float(
        music.get("duration_sec", 0)
        or state.get("chain_data", {})
               .get("stella_strategy", {})
               .get("script", {})
               .get("total_duration_sec", 30)
    )

    if music_prompt:
        print(f"[TURBO A02] 🎵 Генерирую музыку ({music_duration:.0f}с)...")
        music_filename = f"music_{_slugify(project_id or 'track')}.mp3"
        try:
            raw_path = generate_music(
                prompt=music_prompt,
                duration_sec=music_duration,
                filename=music_filename,
                agent_id="A02",
                slot_id=slot_id,
            )
            dest = project_dir / music_filename
            Path(raw_path).replace(dest)
            music["audio_path"] = str(dest)
            print(f"[TURBO A02] ✅ Музыка: {dest.name}")
        except Exception as e:
            print(f"[TURBO A02] ❌ Музыка упала: {e}")
            music["audio_path"] = None
            music["error"] = str(e)
        mimi_sound["music"] = music
    else:
        print("[TURBO A02] ⚠️ music.prompt пуст — музыку не генерирую")

    # ── 2. SFX BATCH — точно как _sam_generate_audio ───────────────
    # Мими пишет sfx_list[] с sfx_prompt и timing_sec
    # Fallback: sfx_map[] → нормализуем в sfx_list
    sfx_list = mimi_sound.get("sfx_list", [])
    if not sfx_list:
        # Нормализуем sfx_map → sfx_list (старый формат Мими)
        sfx_map = mimi_sound.get("sfx_map", [])
        sfx_list = [
            {
                "sfx_prompt":   item.get("sfx", item.get("description", "")),
                "duration_sec": 2.0,
                "timing_sec":   0.0,
                "segment":      item.get("segment", ""),
                "purpose":      item.get("purpose", ""),
            }
            for item in sfx_map
            if item.get("sfx") or item.get("description")
        ]

    if sfx_list:
        print(f"[TURBO A02] 💥 Генерирую {len(sfx_list)} SFX эффектов...")
        sfx_list = generate_sfx_batch(
            sfx_list=sfx_list,
            project_dir=project_dir,
            agent_id="A02",
            slot_id=slot_id,
        )
        mimi_sound["sfx_list"] = sfx_list
        ok = sum(1 for s in sfx_list if s.get("sfx_path"))
        print(f"[TURBO A02] 💥 SFX итог: {ok}/{len(sfx_list)}")
    else:
        print("[TURBO A02] ℹ️ sfx_list пуст — SFX пропускаю")

    # ── 3. VO — CosyVoice — точно как _sam_generate_audio ──────────
    # Мими пишет vo_lines[] с text и timing_sec
    # Fallback: берём voiceover из micro_script Стеллы
    vo_lines = mimi_sound.get("vo_lines", [])
    if not vo_lines:
        voiceover = mimi_sound.get("voiceover", {})
        if voiceover.get("needed"):
            stella   = state.get("chain_data", {}).get("stella_strategy", {})
            segments = stella.get("script", {}).get("micro_script", [])
            vo_lines = [
                {"text": seg.get("voiceover", ""), "segment": seg.get("segment", ""),
                 "timing_sec": 0.0}
                for seg in segments if seg.get("voiceover")
            ]

    if vo_lines:
        try:
            from studio.siliconflow_client import generate_speech
            print(f"[TURBO A02] 🎙️ Генерирую {len(vo_lines)} VO линий...")
            for idx, vo in enumerate(vo_lines):
                text = vo.get("text", "")
                if not text:
                    vo["vo_path"] = None
                    continue
                vo_filename = f"vo_{_slugify(vo.get('segment', f'line_{idx:02d}'))}.mp3"
                dest = project_dir / vo_filename
                try:
                    raw = generate_speech(
                        text=text,
                        voice="alex",
                        filename=vo_filename,
                        agent_id="A02",
                        slot_id=slot_id,
                    )
                    Path(raw).replace(dest)
                    vo["vo_path"] = str(dest)
                    print(f"[TURBO A02] ✅ VO {vo.get('segment', idx)}: {dest.name}")
                except Exception as e:
                    print(f"[TURBO A02] ❌ VO {vo.get('segment', idx)}: {e}")
                    vo["vo_path"] = None
                    vo["error"] = str(e)
            mimi_sound["vo_lines"] = vo_lines
            ok_vo = sum(1 for v in vo_lines if v.get("vo_path"))
            print(f"[TURBO A02] 🎙️ VO итог: {ok_vo}/{len(vo_lines)}")
        except (ImportError, AttributeError):
            print("[TURBO A02] ⚠️ siliconflow_client.generate_speech не найден — VO пропускаю")
    else:
        print("[TURBO A02] ℹ️ vo_lines пуст — VO пропускаю")

    # Пишем обратно в chain_data
    my_output["mimi_sound"] = mimi_sound
    if "my_output" in data:
        data["my_output"] = my_output
    _update_state(state, data)
    _write_chain_key(state, "mimi_sound", mimi_sound)

    has_music = bool(mimi_sound.get("music", {}).get("audio_path"))
    n_sfx     = sum(1 for s in mimi_sound.get("sfx_list", []) if s.get("sfx_path"))
    n_vo      = sum(1 for v in mimi_sound.get("vo_lines",  []) if v.get("vo_path"))
    print(f"[TURBO A02] 🎧 Итог: музыка={'✅' if has_music else '❌'} SFX={n_sfx} VO={n_vo}")

    # ── Self-review: кладём аудио для второго вызова A02 ──────────
    # pipeline.call_agent увидит audio_files → вызовет A02 с chat_with_audio
    music_path = mimi_sound.get("music", {}).get("audio_path")
    if music_path and Path(music_path).exists():
        state["_a02_audio_review_pending"] = True
        state["_a02_mimi_sound_for_review"] = mimi_sound
        state["audio_files"] = [music_path]  # pipeline передаёт в chat_with_audio
        print(f"[A02 AUDIO-REVIEW] 🎧 Готовлю трек для прослуха Мими: {Path(music_path).name}")
    else:
        print("[A02 AUDIO-REVIEW] ⚠️ Нет аудиофайла — audio review пропускаю")


# ============================================================
# A03 SELF-REVIEW — применяем вердикты после второго вызова агента
# ============================================================

def _a03_apply_self_review(state: dict, human_text: str):
    """
    Вызывается из on_after_agent после ВТОРОГО вызова A03 (self-review фаза).
    Агент посмотрел на свои картинки и написал self_assessment по каждому кадру.
    Применяем: REJECTED кадры помечаем, APPROVED — оставляем.
    Чистим vision_images из state (чтобы следующие агенты не получили их).

    Структура self_assessment от агента:
    {
      "my_output": {
        "vizor_visual": {
          "key_frames": [
            {
              "segment": "0-1.5s",
              "self_assessment": {
                "verdict": "APPROVED" | "REJECTED",
                "score": 8.5,
                "note": "...",
                "revised_prompt": "новый промпт если REJECTED"
              }
            }
          ]
        }
      }
    }
    """
    # Убираем vision_images — больше не нужны
    state.pop("vision_images", None)
    state.pop("_a03_self_review_pending", None)

    data = _parse_json(human_text)
    if not data:
        print("[A03 SELF-REVIEW] JSON не найден — self_assessment не применяю")
        return

    my_output    = data.get("my_output", data)
    vizor_review = my_output.get("vizor_visual", my_output)
    review_frames = vizor_review.get("key_frames", [])

    if not review_frames:
        print("[A03 SELF-REVIEW] key_frames пуст в ответе — пропускаю")
        return

    # Применяем self_assessment к кадрам в chain_data
    chain        = state.get("chain_data", {})
    vizor_visual = chain.get("vizor_visual", {})
    frames       = vizor_visual.get("key_frames", []) if isinstance(vizor_visual, dict) else []

    # Маппинг по segment
    review_map = {rf.get("segment", ""): rf for rf in review_frames}

    rejected_count  = 0
    approved_count  = 0
    project_id      = _get_project_id(state)
    project_dir     = OUTPUT_DIR / project_id
    slot_id         = state.get("_slot_id", "turbo")

    for frame in frames:
        segment = frame.get("segment", "")
        review  = review_map.get(segment, {})
        sa      = review.get("self_assessment", {})

        if not sa:
            continue

        verdict = sa.get("verdict", "APPROVED")
        score   = sa.get("score", 7.0)
        note    = sa.get("note", "")
        revised = sa.get("revised_prompt", "")

        frame["self_assessment"] = sa

        if verdict == "REJECTED" and revised:
            rejected_count += 1
            print(f"[A03 SELF-REVIEW] ❌ {segment}: REJECTED (score={score}) — {note[:60]}")
            print(f"[A03 SELF-REVIEW]   Новый промпт: {revised[:80]}...")

            # Перегенерируем кадр с новым промптом
            ref_ids       = _norm_refs(frame.get("ref_ids", []))
            seg_slug      = re.sub(r'[^\w-]', '_', segment)[:20]
            purpose_slug  = re.sub(r'[^\w-]', '_', frame.get("purpose", "frame"))[:20]
            filename_base = f"frame_revised_{seg_slug}_{purpose_slug}"
            dest          = project_dir / f"{filename_base}.png"

            path, new_score, quality = _generate_with_retries(
                prompt=revised,
                ref_ids=ref_ids,
                filename_base=filename_base,
                dest=dest,
                agent_id="A03",
                slot_id=slot_id,
                vision_rules="TURBO кадр 9:16 — ревизия после self-review агента.",
                project_id=project_id,
            )

            if path:
                frame["path"]          = path
                frame["quality_score"] = new_score
                frame["quality"]       = quality
                frame["revised"]       = True
                print(f"[A03 SELF-REVIEW] ✅ Ревизия {segment}: {dest.name}")
            else:
                print(f"[A03 SELF-REVIEW] ⚠️ Ревизия {segment} не удалась — оставляю оригинал")
        else:
            approved_count += 1
            if verdict == "APPROVED":
                print(f"[A03 SELF-REVIEW] ✅ {segment}: APPROVED (score={score})")

    # Обновляем chain_data
    vizor_visual["key_frames"] = frames
    _write_chain_key(state, "vizor_visual", vizor_visual)

    print(f"[A03 SELF-REVIEW] Итог: {approved_count} APPROVED, {rejected_count} REJECTED→ревизия")


# ============================================================
# НОВОЕ: A03 ВИЗОР — АНИМАЦИЯ (Wan2.2 I2V)
# По образцу _felix_generate_clips из video_long/hooks.py
# Запускается ПОСЛЕ генерации картинок (_a03_generate_keyframes)
# ============================================================

def _a03_generate_clips(state: dict):
    """
    После того как A03 сгенерировал картинки — анимируем каждую через Wan2.2 I2V.
    Читает vizor_visual.key_frames[*].path (картинка) и wan_motion_prompt (motion).
    Пишет video_path обратно в каждый кадр.
    """
    try:
        from studio.siliconflow_client import generate_video_with_retry
    except ImportError:
        print("[TURBO A03 CLIPS] ❌ siliconflow_client не найден — анимацию пропускаю")
        return

    chain        = state.get("chain_data", {})
    vizor_visual = chain.get("vizor_visual", {})
    frames       = vizor_visual.get("key_frames", []) if isinstance(vizor_visual, dict) else []

    if not frames:
        print("[TURBO A03 CLIPS] key_frames пуст — анимацию пропускаю")
        return

    project_id  = _get_project_id(state)
    project_dir = OUTPUT_DIR / project_id
    project_dir.mkdir(parents=True, exist_ok=True)
    slot_id = state.get("_slot_id", "turbo")
    total   = len(frames)

    print(f"[TURBO A03 CLIPS] 🎬 Анимирую {total} кадров через Wan2.2 I2V...")

    for idx, frame in enumerate(frames):
        img_path = frame.get("path")
        motion   = frame.get("wan_motion_prompt", "") or frame.get("veo3_prompt", "")
        duration = float(frame.get("wan_duration_sec", 0) or frame.get("veo3_duration_sec", 4))
        camera   = frame.get("wan_camera_move", "") or frame.get("veo3_camera_motion", "static")
        segment  = re.sub(r'[^\w-]', '_', str(frame.get("segment", f"{idx+1}")))[:20]
        purpose  = re.sub(r'[^\w-]', '_', str(frame.get("purpose",  f"clip_{idx+1}")))[:20]
        filename = f"clip_{idx+1:02d}_{segment}_{purpose}.mp4"
        dest     = project_dir / filename

        if not img_path or not Path(img_path).exists():
            print(f"[TURBO A03 CLIPS] ❌ Кадр {idx+1}: картинка не найдена — пропускаю")
            frame["video_path"] = None
            continue

        if not motion:
            print(f"[TURBO A03 CLIPS] ❌ Кадр {idx+1}: wan_motion_prompt пуст — пропускаю")
            frame["video_path"] = None
            continue

        print(f"[TURBO A03 CLIPS] → клип {idx+1}/{total}: {filename}")
        print(f"[TURBO A03 CLIPS]   motion: {motion[:80]}...")

        try:
            raw_path = generate_video_with_retry(
                image_path=img_path,
                motion_prompt=motion,
                filename=filename,
                duration=duration,
                resolution="720p",
                agent_id="A03",
                slot_id=slot_id,
            )
            shutil.move(raw_path, dest)
            frame["video_path"] = str(dest)
            print(f"[TURBO A03 CLIPS] ✅ {filename}")
        except Exception as e:
            print(f"[TURBO A03 CLIPS] ❌ Клип {idx+1} упал: {e}")
            frame["video_path"] = None
            frame["video_error"] = str(e)

    ok = sum(1 for f in frames if f.get("video_path"))
    print(f"[TURBO A03 CLIPS] 🎬 Итог: {ok}/{total} клипов готово")

    # Пишем обратно
    vizor_visual["key_frames"] = frames
    _write_chain_key(state, "vizor_visual", vizor_visual)

    # ── Grid-review: нарезаем клипы на кадры для self-review Визора ──
    # По образцу Феликса (A08) в video_long — grid матрица кадров
    grids = _build_clip_grids(frames, state.get("_slot_id", "turbo"))
    if grids:
        state["_a03_clip_review_pending"] = True
        state["_a03_frames_with_clips"]   = frames
        state["vision_images"]            = grids  # pipeline передаёт в chat_with_images
        print(f"[A03 CLIP-REVIEW] 🎞️ Grid готов для {len(grids)} клипов → Визор смотрит")
    else:
        print("[A03 CLIP-REVIEW] ⚠️ Grid не построен — clip review пропускаю")


# ============================================================
# A03 CLIP-REVIEW — grid анализ клипов (по образцу Феликса)
# ============================================================

def _build_clip_grids(frames: list, slot_id: str) -> list:
    """
    Нарезает mp4 клипы на кадры через ffmpeg и собирает grid.
    Возвращает список путей к grid-изображениям для chat_with_images.
    По образцу _monteur_get_frame из residents_manager.py.
    """
    import subprocess, base64, tempfile, json as _json
    grids = []

    for frame in frames:
        video_path = frame.get("video_path")
        if not video_path or not Path(video_path).exists():
            continue

        try:
            # Получаем длительность
            probe = subprocess.run(
                ["ffprobe", "-v", "quiet", "-print_format", "json",
                 "-show_format", str(video_path)],
                capture_output=True, text=True, timeout=10,
            )
            duration = float(_json.loads(probe.stdout).get("format", {}).get("duration", 4))

            # 4 кадра: начало, 33%, 66%, конец
            timestamps = [
                max(0.1, duration * 0.05),
                duration * 0.33,
                duration * 0.66,
                max(0.1, duration * 0.95),
            ]

            frames_b64 = []
            with tempfile.TemporaryDirectory() as tmp:
                for i, ts in enumerate(timestamps):
                    fp = Path(tmp) / f"frame_{i}.jpg"
                    subprocess.run(
                        ["ffmpeg", "-ss", str(ts), "-i", str(video_path),
                         "-vframes", "1", "-q:v", "5", str(fp), "-y"],
                        capture_output=True, timeout=15,
                    )
                    if fp.exists() and fp.stat().st_size > 0:
                        b64 = base64.b64encode(fp.read_bytes()).decode("ascii")
                        frames_b64.append(b64)

            if frames_b64:
                # Берём средний кадр как репрезентативный для grid
                # (в будущем можно собрать коллаж)
                mid = frames_b64[len(frames_b64) // 2]
                segment = frame.get("segment", "")
                grids.append({
                    "base64":    mid,
                    "mime_type": "image/jpeg",
                    "name":      f"clip_{segment}.jpg",
                    "segment":   segment,
                })
                print(f"[A03 CLIP-REVIEW] 🎞️ Grid: {segment} ({len(frames_b64)} кадров)")

        except FileNotFoundError:
            print("[A03 CLIP-REVIEW] ⚠️ ffmpeg не найден — grid пропускаю")
            break
        except Exception as e:
            print(f"[A03 CLIP-REVIEW] ⚠️ {video_path}: {e}")

    return grids


def _a03_apply_clip_review(state: dict, human_text: str):
    """
    Второй вызов A03 (clip-review фаза) — Визор смотрит на grid клипов.
    Применяем clip_assessment: APPROVED/REJECTED.
    При REJECTED — перегенерируем клип с новым wan_motion_prompt.
    """
    state.pop("vision_images", None)
    state.pop("_a03_clip_review_pending", None)
    frames = state.pop("_a03_frames_with_clips", [])

    data = _parse_json(human_text)
    if not data:
        print("[A03 CLIP-REVIEW] JSON не найден — принимаю клипы как есть")
        return

    my_output    = data.get("my_output", data)
    vizor_review = my_output.get("vizor_visual", my_output)
    review_frames = vizor_review.get("key_frames", [])

    if not review_frames:
        print("[A03 CLIP-REVIEW] key_frames пуст — пропускаю")
        _write_chain_key(state, "vizor_visual", {"key_frames": frames})
        return

    review_map = {rf.get("segment", ""): rf for rf in review_frames}
    project_id = _get_project_id(state)
    project_dir = OUTPUT_DIR / project_id
    slot_id     = state.get("_slot_id", "turbo")

    approved = rejected = 0

    for frame in frames:
        segment = frame.get("segment", "")
        review  = review_map.get(segment, {})
        ca      = review.get("clip_assessment", {})

        if not ca:
            continue

        verdict = ca.get("verdict", "APPROVED")
        score   = ca.get("score", 7.0)
        note    = ca.get("note", "")
        revised = ca.get("revised_prompt", "")

        frame["clip_assessment"] = ca

        if verdict == "REJECTED" and revised and frame.get("path"):
            rejected += 1
            print(f"[A03 CLIP-REVIEW] ❌ {segment}: REJECTED (score={score}) — {note[:60]}")
            print(f"[A03 CLIP-REVIEW]   Новый motion: {revised[:80]}...")

            try:
                from studio.siliconflow_client import generate_video_with_retry
                seg_slug  = re.sub(r'[^\w-]', '_', segment)[:20]
                filename  = f"clip_revised_{seg_slug}.mp4"
                dest      = project_dir / filename
                duration  = float(frame.get("wan_duration_sec", 0) or frame.get("veo3_duration_sec", 4))

                raw_path = generate_video_with_retry(
                    image_path=frame["path"],
                    motion_prompt=revised,
                    filename=filename,
                    duration=duration,
                    resolution="720p",
                    agent_id="A03",
                    slot_id=slot_id,
                )
                import shutil as _sh
                _sh.move(raw_path, dest)
                frame["video_path"] = str(dest)
                frame["wan_motion_prompt"] = revised
                print(f"[A03 CLIP-REVIEW] ✅ Ревизия {segment}: {dest.name}")
            except Exception as e:
                print(f"[A03 CLIP-REVIEW] ❌ Ревизия {segment} упала: {e}")
        else:
            approved += 1
            if verdict == "APPROVED":
                print(f"[A03 CLIP-REVIEW] ✅ {segment}: APPROVED (score={score})")

    chain        = state.get("chain_data", {})
    vizor_visual = chain.get("vizor_visual", {})
    if isinstance(vizor_visual, dict):
        vizor_visual["key_frames"] = frames
    else:
        vizor_visual = {"key_frames": frames}
    _write_chain_key(state, "vizor_visual", vizor_visual)

    print(f"[A03 CLIP-REVIEW] Итог: {approved} APPROVED, {rejected} REJECTED→ревизия")


# ============================================================
# НОВОЕ: МОНТАЖЁР — сборка mp4 после A05
# По образцу _monteur_after_bob из video_long/hooks.py
# ============================================================

def _monteur_after_a05(state: dict):
    """
    После A05 — запускаем Монтажёра если deliverables собраны.
    Монтажёр берёт клипы + аудио → ffmpeg → final.mp4

    АДАПТЕР для TURBO:
    monteur.py ожидает video_clips[*].shot_id для сортировки и lipsync.
    В TURBO вместо shot_id используется segment ("0-1.5s", "1.5-5s"...).
    Адаптируем segment → shot_id чтобы monteur._collect_clips
    мог правильно отсортировать клипы по порядку.
    """
    chain        = state.get("chain_data", {})
    deliverables = chain.get("t5_deliverables", {})

    if not deliverables:
        print("[TURBO MONTEUR] ⚠️ t5_deliverables пусты — сборку пропускаю")
        return

    # ── Chain Integrity Check — по образцу _monteur_after_bob из video_long ──
    # Монтажёр запускается только если Финализатор выдал chain_status APPROVED
    chain_check  = chain.get("chain_check", {})
    chain_status = chain_check.get("chain_status", "")

    if not chain_status:
        # A05 не писал chain_check — fallback на status из deliverables
        chain_status = "APPROVED" if deliverables.get("status") == "ready_to_publish" else "BLOCKED"
        print(f"[TURBO MONTEUR] ℹ️ chain_check не найден — fallback: {chain_status}")

    if chain_status != "APPROVED":
        failed = chain_check.get("failed_checks", [])
        print(f"[TURBO MONTEUR] ❌ chain_status={chain_status} — Монтажёра не запускаю")
        for f in failed:
            print(f"[TURBO MONTEUR]   ✗ {f}")
        state["_assembly_result"] = {
            "status": "BLOCKED",
            "chain_status": chain_status,
            "failed_checks": failed,
        }
        return

    print(f"[TURBO MONTEUR] ✅ APPROVED → запускаю сборку")

    status = deliverables.get("status", "")
    if status == "incomplete":
        print(f"[TURBO MONTEUR] ℹ️ status=incomplete — сборку не запускаю")
        return

    # ── Адаптируем клипы из vizor_visual в формат monteur ──
    # monteur._collect_clips сортирует по shot_id (shot_01, shot_02...)
    # Генерируем shot_id из порядкового номера кадра
    vizor_visual = chain.get("vizor_visual", {})
    frames       = vizor_visual.get("key_frames", []) if isinstance(vizor_visual, dict) else []

    video_clips = []
    for idx, f in enumerate(frames):
        if not f.get("video_path"):
            continue
        video_clips.append({
            "shot_id":      f"shot_{idx+1:02d}",   # shot_01, shot_02... — для сортировки
            "scene_id":     f.get("segment", f"scene_{idx+1}"),  # "0-1.5s" как scene_id
            "shot_type":    f.get("shot_type", "medium"),
            "video_path":   f.get("video_path"),
            "duration_sec": float(f.get("wan_duration_sec", 0) or f.get("veo3_duration_sec", 4)),
            "camera_move":  f.get("wan_camera_move", "") or f.get("veo3_camera_motion", "static"),
            "segment":      f.get("segment", ""),
            "purpose":      f.get("purpose", ""),
        })

    if video_clips:
        deliverables["video_clips"] = video_clips
        print(f"[TURBO MONTEUR] 🎬 Клипов для сборки: {len(video_clips)}")
    else:
        print("[TURBO MONTEUR] ⚠️ Нет клипов с video_path — только картинки")
        # Сборка всё равно запустится, monteur вернёт FAILED без клипов

    # ── Аудио: передаём в формат monteur._mix_audio ──────────────
    # monteur._mix_audio ожидает:
    #   audio.music.audio_path   ← dict с полем audio_path
    #   audio.sfx_list[*].sfx_path + timing_sec
    #   audio.vo_lines[*].vo_path + timing_sec
    mimi_sound = chain.get("mimi_sound", {})
    if mimi_sound:
        # Музыка — точно как у Боба в лонгах
        music      = mimi_sound.get("music", {})
        if isinstance(music, str):
            music = {"audio_path": music}
        sfx_list   = mimi_sound.get("sfx_list", [])
        vo_lines   = mimi_sound.get("vo_lines", [])

        # Привязка VO по времени из beat_map если нет timing_sec
        beat_map   = mimi_sound.get("beat_map", [])
        beat_times = [float(b.get("time_sec", 0)) for b in beat_map]
        for i, vo in enumerate(vo_lines):
            if not vo.get("timing_sec") and i < len(beat_times):
                vo["timing_sec"] = beat_times[i]

        deliverables["audio"] = {
            "music":    music,
            "sfx_list": sfx_list,
            "vo_lines": vo_lines,
        }
        has_music = bool(music.get("audio_path"))
        print(f"[TURBO MONTEUR] 🎧 Аудио: "
              f"музыка={'✅' if has_music else '—'} "
              f"SFX={len(sfx_list)} "
              f"VO={len(vo_lines)}")

    project_id = deliverables.get("project_id", _get_project_id(state))
    slot_id    = state.get("_slot_id", "turbo")

    print(f"[TURBO MONTEUR] 🎬 Запускаю сборку: {project_id}")

    try:
        result = _run_monteur(
            deliverables=deliverables,
            project_id=project_id,
            slot_id=slot_id,
        )
        state["_assembly_result"] = {
            "status":     result.status,
            "final_path": result.final_path,
            "duration":   result.duration_sec,
            "clips":      f"{result.clips_used}/{result.clips_total}",
        }
        emoji = "✅" if result.status == "DONE" else "⚠️"
        print(f"[TURBO MONTEUR] {emoji} {result.status}: {result.final_path}")
    except Exception as e:
        print(f"[TURBO MONTEUR] ❌ Сборка упала: {e}")
        state["_assembly_result"] = {"status": "FAILED", "error": str(e)}


# ============================================================
# MINISTRY — финальный score после A05
# ============================================================

def _a05_record_ministry(state: dict) -> None:
    """
    Финализатор TURBO сообщает Ministry о реальном результате рана.
    Score считается детерминированно по фактам: кадры + клипы + обложки + аудио.
    """
    try:
        from studio.economy import ministry as _min
        slot_id = state.get("_slot_id", "turbo")

        chain  = state.get("chain_data", {})
        deliv  = chain.get("t5_deliverables", {})

        frames       = deliv.get("key_frames", [])
        ready_frames = sum(1 for f in frames if f.get("path"))
        total_frames = len(frames) or 1

        # Учитываем клипы (новое)
        vizor  = chain.get("vizor_visual", {})
        vf     = vizor.get("key_frames", []) if isinstance(vizor, dict) else []
        ready_clips = sum(1 for f in vf if f.get("video_path"))

        thumb        = deliv.get("thumbnail", {})
        ready_thumbs = sum(
            1 for v in ("variant_a", "variant_b")
            if thumb.get(v, {}).get("path")
        )

        # Аудио (новое)
        mimi = chain.get("mimi_sound", {})
        has_music = bool(mimi.get("music_path"))

        qs_list = [f.get("quality_score", 5) for f in frames if f.get("path")]
        avg_qs  = sum(qs_list) / len(qs_list) if qs_list else 5.0

        # Формула: +2.0 кадры, +1.5 клипы, +1.0 обложки, +0.5 музыка, +0.5 качество
        score = 4.0
        score += 2.0 * (ready_frames / total_frames)
        score += 1.5 * (ready_clips  / total_frames)
        score += 1.0 * (ready_thumbs / 2)
        score += 0.5 * (1.0 if has_music else 0.0)
        score += 0.5 * (avg_qs / 10.0)
        score  = round(min(10.0, score), 2)

        agents = ["A01", "A02", "A03", "A04", "A05"]
        for agent_id in agents:
            try:
                from studio.economy import ledger as _led
                cost = _led.agent_spent(agent_id, slot_id=slot_id)
            except Exception:
                cost = 0.0
            _min.record_outcome(
                agent_id=agent_id,
                slot_id=slot_id,
                score=score,
                cost_usd=cost,
            )

        print(f"[TURBO A05] 🏛 Ministry: score={score} "
              f"frames={ready_frames}/{total_frames} "
              f"clips={ready_clips} "
              f"thumbs={ready_thumbs}/2 "
              f"music={'✅' if has_music else '❌'}")

        try:
            from studio.culture.field_tracker import CulturalFieldTracker
            CulturalFieldTracker().update_slot_field(slot_id)
            print("[TURBO A05] 🧬 CulturalFieldTracker обновлён")
        except Exception as _ce:
            print(f"[TURBO A05] ⚠ CulturalFieldTracker: {_ce}")

    except Exception as e:
        print(f"[TURBO A05] ⚠ ministry.record_outcome: {e}")


# ============================================================
# КАЧЕСТВО — GEMINI FLASH
# ============================================================

def _check_quality(image_path: str, prompt: str, agent_id: str, slot_id: str) -> tuple[int, str]:
    try:
        system = (
            "You are an art director. Rate how well the image matches the prompt and its visual quality. "
            "Reply STRICTLY as JSON: {\"score\": <1-10>, \"notes\": \"<issues in English>\"}\n"
            "1-5 = bad (artifacts, mismatch), 6-7 = acceptable, 8-10 = excellent."
        )
        user = f"Prompt: {prompt}\n\nRate this image."
        raw = chat_with_images(system, user, images=[image_path],
                               agent_id=agent_id, slot_id=slot_id)
        m = re.search(r'\{.*?\}', raw, re.DOTALL)
        if m:
            data = json.loads(m.group(0))
            return int(data.get("score", 7)), str(data.get("notes", ""))
    except Exception as e:
        print(f"[QUALITY] Проверка не удалась: {e}")
    return 7, "check unavailable"


# ============================================================
# ГЕНЕРАЦИЯ КАРТИНКИ С ОТК (vision_client)
# По образцу video_long/hooks.py _generate_with_vision_check
# ============================================================

def _generate_with_retries(
    prompt: str,
    ref_ids: list,
    filename_base: str,
    dest: Path,
    agent_id: str,
    slot_id: str,
    vision_rules: str = "",
    project_id: str = "",
) -> tuple[str | None, int, str]:
    """
    Генерирует картинку с полноценным ОТК через vision_client.

    Если vision_client доступен:
      → PASS/REJECT по стандарту video_long
      → брак архивируется в output/rejected/{project_id}/
      → fix_hint корректирует промпт через негатив
      → до MAX_ATTEMPTS попыток

    Если vision_client недоступен:
      → fallback на _check_quality (Gemini score 1-10)
    """
    if _VISION_OTK_ENABLED:
        return _generate_with_otk(
            prompt=prompt,
            ref_ids=ref_ids,
            filename_base=filename_base,
            dest=dest,
            agent_id=agent_id,
            slot_id=slot_id,
            vision_rules=vision_rules,
            project_id=project_id,
        )
    else:
        return _generate_with_score_check(
            prompt=prompt,
            ref_ids=ref_ids,
            filename_base=filename_base,
            dest=dest,
            agent_id=agent_id,
            slot_id=slot_id,
        )


def _generate_with_otk(
    prompt: str,
    ref_ids: list,
    filename_base: str,
    dest: Path,
    agent_id: str,
    slot_id: str,
    vision_rules: str = "",
    project_id: str = "",
) -> tuple[str | None, int, str]:
    """
    Генерация + ОТК через vision_client.generate_with_vision_check.
    Возвращает (path, score, quality_label) для совместимости с вызывающим кодом.
    """
    current_prompt   = [prompt]
    negative_suffix  = [""]

    def _gen():
        full = current_prompt[0]
        if negative_suffix[0]:
            full += f", --no {negative_suffix[0]}"
        filename = f"{filename_base}_attempt.png"
        if ref_ids:
            return generate_with_refs(
                prompt=full,
                ref_ids=ref_ids,
                format="9:16",
                filename=filename,
                agent_id=agent_id,
                slot_id=slot_id,
            )
        else:
            return generate_image(
                prompt=full,
                format="9:16",
                filename=filename,
                agent_id=agent_id,
                slot_id=slot_id,
            )

    def _on_retry(attempt: int, fix_hint: str):
        if fix_hint:
            negative_suffix[0] = (negative_suffix[0] + ", " + fix_hint).strip(", ")
            print(f"[TURBO OTK {agent_id}] Негатив обновлён: {fix_hint[:60]}")

    try:
        raw_path = _vision_otk(
            generate_fn=_gen,
            original_prompt=prompt,
            agent_id=agent_id,
            rules=vision_rules,
            max_visual_retries=MAX_ATTEMPTS,
            on_retry=_on_retry,
            project_id=project_id,
        )
        # Перемещаем в финальный dest
        if Path(raw_path).resolve() != dest.resolve():
            shutil.copy2(raw_path, dest)
            try:
                Path(raw_path).unlink()
            except Exception:
                pass
        return str(dest), 8, "ok"  # APPROVED → score 8 условно

    except Exception as e:
        print(f"[TURBO OTK {agent_id}] ❌ Все попытки в браке: {e}")
        return None, 0, "rejected"


def _generate_with_score_check(
    prompt: str,
    ref_ids: list,
    filename_base: str,
    dest: Path,
    agent_id: str,
    slot_id: str,
) -> tuple[str | None, int, str]:
    """
    Fallback: генерация + Gemini score 1-10 (без vision_client).
    Используется когда vision_client недоступен.
    """
    best_path      = None
    best_score     = 0
    current_prompt = prompt

    for attempt in range(1, MAX_ATTEMPTS + 1):
        filename = f"{filename_base}_attempt{attempt}.png"
        tmp_path = None

        try:
            if ref_ids:
                tmp_path = generate_with_refs(
                    prompt=current_prompt,
                    ref_ids=ref_ids,
                    format="9:16",
                    filename=filename,
                    agent_id=agent_id,
                    slot_id=slot_id,
                )
            else:
                tmp_path = generate_image(
                    prompt=current_prompt,
                    format="9:16",
                    filename=filename,
                    agent_id=agent_id,
                    slot_id=slot_id,
                )
        except Exception as e:
            print(f"  ❌ Попытка {attempt}: {e}")
            continue

        if not tmp_path or not Path(tmp_path).exists():
            continue

        score, notes = _check_quality(tmp_path, current_prompt, agent_id, slot_id)
        print(f"  Попытка {attempt}: score={score} | {notes[:80]}")

        if score > best_score:
            best_score = score
            best_path  = tmp_path

        if score >= QUALITY_THRESHOLD:
            print(f"  ✅ Принято на попытке {attempt}")
            break

        if notes and "unavailable" not in notes and attempt < MAX_ATTEMPTS:
            current_prompt = f"{prompt}. Fix: {notes[:120]}"

    quality_label = "ok" if best_score >= QUALITY_THRESHOLD else "fallback"

    if best_path and Path(best_path).exists():
        shutil.copy2(best_path, dest)
        try:
            Path(best_path).unlink()
        except Exception:
            pass
        return str(dest), best_score, quality_label

    return None, best_score, quality_label


# ============================================================
# T3 — КЛЮЧЕВЫЕ КАДРЫ (картинки)
# ============================================================

def _a03_generate_keyframes(state: dict, human_text: str):
    data = _parse_json(human_text)
    if not data:
        print("[A03] JSON не найден — пропускаю генерацию кадров")
        return

    my_output    = data.get("my_output", data)
    vizor_visual = my_output.get("vizor_visual", my_output)
    frames       = vizor_visual.get("key_frames", [])

    if not frames:
        print("[A03] key_frames пуст — пропускаю генерацию")
        return

    project_id  = _get_project_id(state)
    project_dir = OUTPUT_DIR / project_id
    project_dir.mkdir(parents=True, exist_ok=True)
    slot_id = state.get("_slot_id", "turbo")

    generated = 0
    total     = len(frames)

    for i, frame in enumerate(frames):
        prompt = frame.get("banana_prompt") or frame.get("prompt", "")
        if not prompt:
            print(f"[A03] Кадр {i+1}/{total}: нет banana_prompt — пропускаю")
            frame["path"] = None
            continue

        ref_ids       = _norm_refs(frame.get("ref_ids", []))
        segment       = re.sub(r'[^\w-]', '_', str(frame.get("segment", f"{i+1}")))[:20]
        purpose       = re.sub(r'[^\w-]', '_', str(frame.get("purpose",  f"frame_{i+1}")))[:20]
        filename_base = f"frame_{i+1:02d}_{segment}_{purpose}"
        dest          = project_dir / f"{filename_base}.png"

        print(f"\n[A03] 🎬 Кадр {i+1}/{total}: {filename_base}")
        print(f"[A03]   Промпт: {prompt[:80]}...")

        path, score, quality = _generate_with_retries(
            prompt=prompt, ref_ids=ref_ids,
            filename_base=filename_base, dest=dest,
            agent_id="A03", slot_id=slot_id,
            vision_rules="TURBO кадр 9:16. Строгая анатомия. Соответствие промпту и референсам.",
            project_id=project_id,
        )

        frame["path"]          = path
        frame["quality_score"] = score
        frame["quality"]       = quality

        if path:
            generated += 1
            print(f"[A03] 💾 {dest} | score={score} | {quality}")
        else:
            print(f"[A03] ⚠️ Кадр {i+1} не сгенерирован после {MAX_ATTEMPTS} попыток")

    print(f"\n[A03] Итого картинок: {generated}/{total}")

    vizor_visual["key_frames"] = frames
    _write_chain_key(state, "vizor_visual", vizor_visual)

    # ── Self-review: кладём пути картинок в state для второго вызова A03 ──
    # pipeline.call_agent увидит vision_images и вызовет chat_with_images
    # Агент получит свои картинки и напишет self_assessment по каждому кадру
    ready_paths = [f["path"] for f in frames if f.get("path")]
    if ready_paths:
        state["_a03_self_review_pending"] = True
        state["_a03_frames_for_review"]   = frames
        # vision_images — стандартный ключ pipeline для передачи картинок агенту
        state["vision_images"] = ready_paths
        print(f"[A03 SELF-REVIEW] 👁 Готовлю {len(ready_paths)} картинок для самооценки Визора")
    else:
        print("[A03 SELF-REVIEW] ⚠️ Нет готовых картинок — self-review пропускаю")


# ============================================================
# T5 — ОБЛОЖКИ + СБОРКА DELIVERABLES
# ============================================================

def _a05_generate_thumbnails_and_deliverables(state: dict, human_text: str):
    data = _parse_json(human_text)
    if not data:
        print("[A05] JSON не найден — пропускаю")
        return

    my_output = data.get("my_output", data)
    thumb     = my_output.get("thumbnail", {})

    project_id  = _get_project_id(state)
    project_dir = OUTPUT_DIR / project_id
    project_dir.mkdir(parents=True, exist_ok=True)
    slot_id = state.get("_slot_id", "turbo")

    generated = 0
    for variant_name in ["variant_a", "variant_b"]:
        variant = thumb.get(variant_name, {})
        if not variant:
            continue
        prompt = variant.get("banana_prompt") or variant.get("prompt", "")
        if not prompt:
            print(f"[A05] {variant_name}: нет banana_prompt — пропускаю")
            continue

        ref_ids = _norm_refs(variant.get("ref_ids", []))
        dest    = project_dir / f"thumb_{variant_name}.png"

        print(f"\n[A05] 🖼️ Обложка: {variant_name}")
        path, score, quality = _generate_with_retries(
            prompt=prompt, ref_ids=ref_ids,
            filename_base=f"thumb_{variant_name}", dest=dest,
            agent_id="A05", slot_id=slot_id,
            vision_rules="TURBO обложка 9:16. CTR-максимум. Лицо чёткое, текст читаем, нет артефактов.",
            project_id=project_id,
        )
        variant["path"]          = path
        variant["quality_score"] = score
        variant["quality"]       = quality
        if path:
            generated += 1
            print(f"[A05] 💾 {dest} | score={score} | {quality}")

    print(f"\n[A05] Обложки: {generated}/2")

    chain        = state.get("chain_data") or {}
    vizor_visual = chain.get("vizor_visual", {})
    vizor_frames = vizor_visual.get("key_frames", []) if isinstance(vizor_visual, dict) else []

    deliverables = {}

    deliverables["thumbnail"] = {
        "variant_a": _clean_variant(thumb.get("variant_a", {})),
        "variant_b": _clean_variant(thumb.get("variant_b", {})),
    }

    deliverables["key_frames"] = [
        {
            "segment":       vf.get("segment", ""),
            "purpose":       vf.get("purpose", ""),
            "prompt":        vf.get("banana_prompt", "") or vf.get("prompt", ""),
            "ref_ids":       vf.get("ref_ids", []),
            "format":        "9:16",
            "path":          vf.get("path"),
            "video_path":    vf.get("video_path"),   # ← НОВОЕ: путь к клипу
            "quality_score": vf.get("quality_score", 0),
            "quality":       vf.get("quality", "unknown"),
        }
        for vf in vizor_frames
    ]

    deliverables["wan_clips"] = [
        {
            "segment":            vf.get("segment", ""),
            "wan_camera_move":    vf.get("wan_camera_move", "") or vf.get("veo3_camera_motion", ""),
            "wan_duration_sec":   float(vf.get("wan_duration_sec", 0) or vf.get("veo3_duration_sec", 4)),
            "wan_motion_prompt":  vf.get("wan_motion_prompt", "") or vf.get("veo3_prompt", ""),
            "ref_ids":            vf.get("ref_ids", []),
        }
        for vf in vizor_frames
        if vf.get("wan_motion_prompt") or vf.get("veo3_prompt")
    ]

    # Аудио из mimi_sound — формат как у Боба в лонгах
    mimi_sound = chain.get("mimi_sound", {})
    if mimi_sound:
        music = mimi_sound.get("music", {})
        if isinstance(music, str):
            music = {"audio_path": music}
        deliverables["audio"] = {
            "music":    music,
            "sfx_list": mimi_sound.get("sfx_list", []),
            "vo_lines": mimi_sound.get("vo_lines", []),
        }

    # Остальные поля из T5
    for key in ("sound", "voice_over", "music", "captions", "publication"):
        if key in my_output:
            deliverables[key] = my_output[key]

    deliverables["project_id"] = project_id

    ready_frames = sum(1 for f in deliverables["key_frames"] if f.get("path"))
    ready_clips  = sum(1 for f in deliverables["key_frames"] if f.get("video_path"))
    ready_thumbs = sum(
        1 for v in ("variant_a", "variant_b")
        if deliverables["thumbnail"].get(v, {}).get("path")
    )
    has_audio = bool(mimi_sound.get("music_path"))

    deliverables["status"] = (
        "ready_to_publish"
        if (ready_frames and ready_thumbs)
        else "incomplete"
    )

    print(f"[A05] deliverables: "
          f"frames={ready_frames} clips={ready_clips} "
          f"thumbs={ready_thumbs}/2 audio={'✅' if has_audio else '❌'} "
          f"status={deliverables['status']}")

    # tasks[] для Assembly UI
    tasks = state.setdefault("tasks", {})
    tasks["project_id"] = project_id
    tasks["key_frames"] = deliverables["key_frames"]
    tasks["videos"]     = [
        {"segment": f.get("segment"), "video_path": f.get("video_path")}
        for f in deliverables["key_frames"]
        if f.get("video_path")
    ]
    if my_output.get("final_dna"):
        tasks["final_dna"] = my_output["final_dna"]

    _write_chain_key(state, "t5_deliverables", deliverables)

    # Прокидываем chain_check в chain_data чтобы _monteur_after_a05 мог его прочитать
    chain_check = my_output.get("chain_check", {})
    if chain_check:
        _write_chain_key(state, "chain_check", chain_check)
        status = chain_check.get("chain_status", "")
        print(f"[A05] 🔗 chain_check: {status}")


# ============================================================
# УТИЛИТЫ
# ============================================================

def _parse_json(text: str) -> dict | None:
    m = re.search(r'SYSTEM_JSON_START[^\n]*\n(.*?)\n[^\n]*SYSTEM_JSON_END', text, re.DOTALL)
    if m:
        raw = m.group(1)
    else:
        m2 = re.search(r'```json\s*\n(.*?)\n```', text, re.DOTALL)
        raw = m2.group(1) if m2 else None
    if not raw:
        print("[TURBO] JSON не найден")
        return None
    raw = raw.strip().strip("`").strip()
    if raw.startswith("json"):
        raw = raw[4:].strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"[TURBO] Ошибка парсинга JSON: {e}")
        return None


def _get_project_id(state: dict) -> str:
    pid = state.get("project_id", "")
    if pid:
        return pid
    pid = state.get("history_dna", {}).get("project_id", "")
    if pid:
        return pid
    chain = state.get("chain_data") or {}
    return (
        chain.get("project_id")
        or chain.get("stella_strategy", {}).get("project_id", "")
        or chain.get("a01_strategy",    {}).get("project_id", "")
        or "turbo_unknown"
    )


def _norm_refs(ref_ids) -> list:
    if isinstance(ref_ids, str):
        ref_ids = [ref_ids]
    return [r for r in (ref_ids or []) if r]


def _write_chain_key(state: dict, key: str, value):
    chain = state.setdefault("chain_data", {})
    chain[key] = value


def _clean_variant(variant: dict) -> dict:
    return {
        "concept":       variant.get("concept", ""),
        "banana_prompt": variant.get("banana_prompt") or variant.get("prompt", ""),
        "text_overlay":  variant.get("text_overlay", ""),
        "emotion":       variant.get("emotion", ""),
        "ref_ids":       variant.get("ref_ids", []),
        "style_tags":    variant.get("style_tags", []),
        "quality_check": variant.get("quality_check", ""),
        "quality_score": variant.get("quality_score", 0),
        "quality":       variant.get("quality", "unknown"),
        "path":          variant.get("path"),
    }


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9а-яА-ЯёЁ_-]", "_", str(name).lower().strip())
    slug = re.sub(r"_+", "_", slug).strip("_")
    return slug or "unknown"
