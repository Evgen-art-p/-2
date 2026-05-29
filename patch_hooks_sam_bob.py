#!/usr/bin/env python3
"""
patch_hooks_sam_bob.py
======================
Три патча в studio/modules/video_long/hooks.py

ПАТЧ 1: _bob_collect_media()
  - "veo3_prompts" → "video_clips"
  - добавляет "video_path" из felix_vfx.video_clips[].video_path

ПАТЧ 2: добавляет _sam_generate_audio()
  - по образцу _felix_generate_clips
  - music → ElevenLabs generate_music()
  - sfx_list → ElevenLabs generate_sfx_batch()
  - vo_lines → CosyVoice (через siliconflow_client)
  - пишет audio_path в sam_sound.music + sfx_path в sfx_list[]

ПАТЧ 3: on_after_agent()
  - подключает _sam_generate_audio() после A10 в EPISODE режиме

Запуск: python patch_hooks_sam_bob.py
Репо:   studio/modules/video_long/hooks.py
"""

import re
from pathlib import Path

HOOKS_PATH = Path("studio/modules/video_long/hooks.py")

# ─────────────────────────────────────────────────────────────────
# ПАТЧ 1 — _bob_collect_media: veo3_prompts → video_clips + video_path
# ─────────────────────────────────────────────────────────────────

OLD_FELIX_COLLECT = '''    # ── A08 Феликс: veo3_prompts ────────────────────────────────────────
    # FIX v2.1: поле "video_clips" согласно CHAIN_CONTRACT (было key_frames/veo3_prompts)
    #           поле промпта "motion_prompt" (было veo_prompt_en / veo3_prompt)
    #           поле камеры  "camera_move"   (было camera_movement)
    felix = chain.get("felix_vfx", {})
    if isinstance(felix, dict):
        felix_clips = felix.get("video_clips", [])
        if felix_clips:
            deliverables["veo3_prompts"] = [{
                "shot_id":  f.get("shot_id", ""),
                "camera":   f.get("camera_move", ""),
                "duration": f.get("duration_sec", 0),
                "prompt":   f.get("motion_prompt", ""),
                "ref_ids":  f.get("ref_ids", []),
                "vfx_layer": f.get("vfx_layer", ""),
            } for f in felix_clips]
            print(f"[EPISODE A12]   veo3_prompts: {len(deliverables['veo3_prompts'])} клипов")'''

NEW_FELIX_COLLECT = '''    # ── A08 Феликс: video_clips (реальные mp4) ──────────────────────
    # LONG_RULES v4.3 правило 16: video_clips[*].video_path — реальные mp4, не промпты
    # FIX patch_hooks_sam_bob: переименовали veo3_prompts → video_clips,
    #                          добавили video_path из felix_vfx.video_clips[].video_path
    felix = chain.get("felix_vfx", {})
    if isinstance(felix, dict):
        felix_clips = felix.get("video_clips", [])
        if felix_clips:
            deliverables["video_clips"] = [{
                "frame_id":     f.get("frame_id", ""),
                "shot_id":      f.get("shot_id", ""),
                "scene_id":     f.get("scene_id", ""),
                "motion_prompt": f.get("motion_prompt", ""),
                "camera_move":  f.get("camera_move", ""),
                "duration_sec": f.get("duration_sec", 0),
                "ref_ids":      f.get("ref_ids", []),
                "vfx_layer":    f.get("vfx_layer", "none"),
                "video_path":   f.get("video_path"),   # реальный mp4 от Wan2.2
                "clip_assessment": f.get("clip_assessment", {}),
            } for f in felix_clips]
            ok = sum(1 for c in deliverables["video_clips"] if c.get("video_path"))
            total = len(deliverables["video_clips"])
            print(f"[EPISODE A12]   video_clips : {ok}/{total} клипов с video_path")'''

# ─────────────────────────────────────────────────────────────────
# ПАТЧ 2 — новая функция _sam_generate_audio()
# Вставляется перед _bob_finalize
# ─────────────────────────────────────────────────────────────────

SAM_GENERATE_FUNC = '''

# ═══════════════════════════════════════════════════════════════════
# EPISODE: A10 СЭМ — генерация аудио (музыка + SFX + VO)
# По образцу _felix_generate_clips.
# Хук ЖДЁТ всего → конвейер идёт к A11 только после возврата.
#
# Три слоя:
#   1. Музыка  → ElevenLabs generate_music()
#   2. SFX     → ElevenLabs generate_sfx_batch()
#   3. VO      → CosyVoice (siliconflow_client.generate_voice_over)
#
# Пишет обратно в state:
#   sam_sound.music.audio_path    ← mp3 путь
#   sam_sound.sfx_list[*].sfx_path ← mp3 пути
#   sam_sound.vo_lines[*].vo_path  ← mp3 пути
# ═══════════════════════════════════════════════════════════════════

def _sam_generate_audio(state: dict, human_text: str):
    """
    A10 СЭМ — генерация аудио через ElevenLabs и CosyVoice.
    Вызывается хуком on_after_agent сразу после A10 в EPISODE режиме.
    """
    try:
        from studio.elevenlabs_client import generate_music, generate_sfx_batch
        has_elevenlabs = True
    except ImportError:
        print("[A10 Сэм] ❌ elevenlabs_client не найден — аудио пропускаю")
        return

    data = _parse_json(human_text)
    if not data:
        print("[A10 Сэм] JSON не найден — пропускаю")
        return

    my_output = data.get("my_output", data)
    sam_sound = my_output.get("sam_sound", {})
    if not sam_sound:
        print("[A10 Сэм] sam_sound пуст — пропускаю")
        return

    project_id  = state.get("project_id", "")
    project_dir = OUTPUT_DIR / (project_id or "vl_episode_unknown")
    project_dir.mkdir(parents=True, exist_ok=True)
    slot_id = state.get("_slot_id", "video_long")

    # ── 1. МУЗЫКА ──────────────────────────────────────────────────
    music = sam_sound.get("music", {})
    music_prompt   = music.get("prompt", "")
    music_duration = float(music.get("duration_sec", 60))

    if music_prompt:
        print(f"[A10 Сэм] 🎵 Генерирую музыку ({music_duration:.0f}с)...")
        music_filename = f"music_{_slugify(project_id or 'track')}.mp3"
        try:
            raw_path = generate_music(
                prompt=music_prompt,
                duration_sec=music_duration,
                filename=music_filename,
                agent_id="A10",
                slot_id=slot_id,
            )
            dest = project_dir / music_filename
            Path(raw_path).replace(dest)
            music["audio_path"] = str(dest)
            print(f"[A10 Сэм] ✅ Музыка: {dest.name}")
        except Exception as e:
            print(f"[A10 Сэм] ❌ Музыка упала: {e}")
            music["audio_path"] = None
            music["error"] = str(e)
        sam_sound["music"] = music
    else:
        print("[A10 Сэм] ⚠️  music.prompt пуст — музыку не генерирую")

    # ── 2. SFX BATCH ───────────────────────────────────────────────
    sfx_list = sam_sound.get("sfx_list", [])
    if sfx_list:
        print(f"[A10 Сэм] 💥 Генерирую {len(sfx_list)} SFX эффектов...")
        sfx_list = generate_sfx_batch(
            sfx_list=sfx_list,
            project_dir=project_dir,
            agent_id="A10",
            slot_id=slot_id,
        )
        sam_sound["sfx_list"] = sfx_list
        ok = sum(1 for s in sfx_list if s.get("sfx_path"))
        print(f"[A10 Сэм] 💥 SFX итог: {ok}/{len(sfx_list)}")
    else:
        print("[A10 Сэм] ℹ️  sfx_list пуст — SFX пропускаю")

    # ── 3. VO — CosyVoice ──────────────────────────────────────────
    vo_lines = sam_sound.get("vo_lines", [])
    if vo_lines:
        try:
            from studio.siliconflow_client import generate_speech
            has_cosyvoice = True  # generate_speech()
        except (ImportError, AttributeError):
            print("[A10 Сэм] ⚠️  siliconflow_client.generate_speech не найден — VO пропускаю")
            has_cosyvoice = False

        if has_cosyvoice:
            print(f"[A10 Сэм] 🎙️  Генерирую {len(vo_lines)} VO линий...")
            for idx, vo in enumerate(vo_lines):
                text = vo.get("text", "")
                # voice_style Сэма ("warm/authoritative/energetic/whisper") →
                # CosyVoice не принимает стиль как параметр, управляется промптом.
                # Используем дефолтный голос "alex". При необходимости расширить
                # через маппинг voice_style → голос CosyVoice.
                if not text:
                    vo["vo_path"] = None
                    continue
                vo_filename = f"vo_{_slugify(vo.get('scene_id', f'line_{idx:02d}'))}.mp3"
                dest = project_dir / vo_filename
                try:
                    raw = generate_speech(
                        text=text,
                        voice="alex",
                        filename=vo_filename,
                        agent_id="A10",
                        slot_id=slot_id,
                    )
                    Path(raw).replace(dest)
                    vo["vo_path"] = str(dest)
                    print(f"[A10 Сэм] ✅ VO {vo.get('scene_id', idx)}: {dest.name}")
                except Exception as e:
                    print(f"[A10 Сэм] ❌ VO {vo.get('scene_id', idx)}: {e}")
                    vo["vo_path"] = None
                    vo["error"] = str(e)
            sam_sound["vo_lines"] = vo_lines
            ok_vo = sum(1 for v in vo_lines if v.get("vo_path"))
            print(f"[A10 Сэм] 🎙️  VO итог: {ok_vo}/{len(vo_lines)}")
    else:
        print("[A10 Сэм] ℹ️  vo_lines пуст — VO пропускаю")

    # ── Пишем обратно в state ──────────────────────────────────────
    my_output["sam_sound"] = sam_sound
    if "my_output" in data:
        data["my_output"] = my_output
    _update_state(state, data)

    # Итоговый отчёт
    has_music = bool(sam_sound.get("music", {}).get("audio_path"))
    n_sfx     = sum(1 for s in sam_sound.get("sfx_list", []) if s.get("sfx_path"))
    n_vo      = sum(1 for v in sam_sound.get("vo_lines",  []) if v.get("vo_path"))
    print(f"[A10 Сэм] 🎧 Итог: музыка={'✅' if has_music else '❌'}  "
          f"SFX={n_sfx}  VO={n_vo}")

'''

# ─────────────────────────────────────────────────────────────────
# ПАТЧ 3 — on_after_agent: подключить A10 хук
# ─────────────────────────────────────────────────────────────────

OLD_DISPATCHER = '''    if mode == "bible" and worker_id == "A06":
        _bible_eva_sync(state, human_text)
    elif mode == "episode" and worker_id == "A06":
        _episode_eva_parallel(state, human_text)
    elif worker_id == "A08":
        _felix_log_interaction(state, human_text)
        if mode == "episode":
            _felix_generate_clips(state, human_text)
    elif mode == "episode" and worker_id == "A11":
        _episode_tracy_parallel(state, human_text)
    elif mode == "episode" and worker_id == "A12":
        _bob_finalize(state, human_text)'''

NEW_DISPATCHER = '''    if mode == "bible" and worker_id == "A06":
        _bible_eva_sync(state, human_text)
    elif mode == "episode" and worker_id == "A06":
        _episode_eva_parallel(state, human_text)
    elif worker_id == "A08":
        _felix_log_interaction(state, human_text)
        if mode == "episode":
            _felix_generate_clips(state, human_text)
    elif mode == "episode" and worker_id == "A10":
        _sam_generate_audio(state, human_text)
    elif mode == "episode" and worker_id == "A11":
        _episode_tracy_parallel(state, human_text)
    elif mode == "episode" and worker_id == "A12":
        _bob_finalize(state, human_text)'''


# ─────────────────────────────────────────────────────────────────
# ПРИМЕНЯЕМ ПАТЧИ
# ─────────────────────────────────────────────────────────────────

def apply():
    if not HOOKS_PATH.exists():
        print(f"❌ Файл не найден: {HOOKS_PATH}")
        print("   Запусти скрипт из корня репо (рядом со studio/)")
        return False

    text = HOOKS_PATH.read_text(encoding="utf-8")
    original = text
    errors = []

    # ── ПАТЧ 1: veo3_prompts → video_clips + video_path ──
    if OLD_FELIX_COLLECT in text:
        text = text.replace(OLD_FELIX_COLLECT, NEW_FELIX_COLLECT)
        print("✅ ПАТЧ 1: _bob_collect_media — video_clips + video_path")
    else:
        errors.append("ПАТЧ 1: блок veo3_prompts не найден (уже пропатчен?)")

    # ── ПАТЧ 2: вставляем _sam_generate_audio() перед _bob_finalize ──
    SAM_ANCHOR = "\ndef _bob_finalize"
    if "_sam_generate_audio" not in text:
        if SAM_ANCHOR in text:
            text = text.replace(SAM_ANCHOR, SAM_GENERATE_FUNC + "\ndef _bob_finalize")
            print("✅ ПАТЧ 2: _sam_generate_audio() добавлена")
        else:
            errors.append("ПАТЧ 2: якорь '_bob_finalize' не найден")
    else:
        print("ℹ️  ПАТЧ 2: _sam_generate_audio уже есть — пропускаю")

    # ── ПАТЧ 3: on_after_agent — A10 хук ──
    if OLD_DISPATCHER in text:
        text = text.replace(OLD_DISPATCHER, NEW_DISPATCHER)
        print("✅ ПАТЧ 3: on_after_agent — A10 хук подключён")
    else:
        if "worker_id == \"A10\"" in text:
            print("ℹ️  ПАТЧ 3: A10 хук уже подключён — пропускаю")
        else:
            errors.append("ПАТЧ 3: диспетчер on_after_agent не найден точно")

    if errors:
        print("\n⚠️  Предупреждения:")
        for e in errors:
            print(f"   - {e}")

    if text == original and not errors:
        print("\nℹ️  Файл не изменился — все патчи уже применены.")
        return True

    if text != original:
        # Бэкап
        backup = HOOKS_PATH.with_suffix(".py.bak_sam")
        backup.write_text(original, encoding="utf-8")
        print(f"\n💾 Бэкап: {backup}")

        HOOKS_PATH.write_text(text, encoding="utf-8")
        print(f"✅ Записано: {HOOKS_PATH}")

    if errors:
        print("\n⚠️  Некоторые патчи не применились — проверь вручную:")
        for e in errors:
            print(f"   {e}")
        return False

    print("\n🎉 Все три патча применены успешно!")
    print("\nЧто изменилось:")
    print("  1. deliverables['video_clips'] — реальные mp4 с video_path (не промпты)")
    print("  2. _sam_generate_audio() — ElevenLabs music + SFX batch + CosyVoice VO")
    print("  3. on_after_agent A10 → запускает _sam_generate_audio()")
    print("\nПроверь что работает:")
    print("  - ELEVENLABS_API_KEY в .env")
    print("  - siliconflow_client.generate_speech() — есть ✅")
    print("    Если нет — VO пропустится с предупреждением, остальное работает")
    return True


if __name__ == "__main__":
    apply()
