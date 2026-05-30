"""
studio/assembly/monteur.py
==========================
Монтажная — инструмент сборки финального ролика.

Берёт deliverables от Боба (A12):
  - video_clips[*].video_path   — mp4 клипы от Феликса (Wan2.2)
  - audio.music.audio_path      — фоновый трек от Сэма (ElevenLabs)
  - audio.sfx_list[*].sfx_path  — SFX точки от Сэма
  - audio.vo_lines[*].vo_path   — VO от Сэма (CosyVoice)
  - typography                  — титры от Тима

Выдаёт:
  output/render/{project_id}/final.mp4

Связи:
  - grondheim_memory: on_agent_wake / on_agent_done → Монтажёр живёт в городе
  - ministry.record_outcome → фиксирует факт сборки в экономике
  - billing_ledger → пишет стоимость рендера

Инструменты (публичный API):
  assemble(deliverables, project_id, slot_id) → AssemblyResult
  get_assembly_status(project_id) → dict
"""

import json
import shutil
import subprocess
import datetime
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

# ── Константы ────────────────────────────────────────────────────────
RENDER_DIR   = Path("output/render")
REJECTED_DIR = Path("output/rejected")
MONTEUR_ID   = "006_MONTEUR"
SLOT_ID      = "assembly"

RENDER_DIR.mkdir(parents=True, exist_ok=True)


# ── Результат сборки ─────────────────────────────────────────────────

@dataclass
class AssemblyResult:
    project_id:   str
    status:       str          # DONE | FAILED | PARTIAL
    final_path:   str | None   # путь к final.mp4
    duration_sec: float = 0.0
    clips_used:   int   = 0
    clips_total:  int   = 0
    has_audio:    bool  = False
    has_vo:       bool  = False
    has_sfx:      bool  = False
    errors:       list  = field(default_factory=list)
    assembled_at: str   = ""


# ═══════════════════════════════════════════════════════════════════
# ПУБЛИЧНЫЙ API
# ═══════════════════════════════════════════════════════════════════

def assemble(
    deliverables: dict,
    project_id:   str  = "",
    slot_id:      str  = "video_long",
) -> AssemblyResult:
    """
    Главная функция — собирает финальный ролик из deliverables Боба.

    Args:
        deliverables: dict из state["_last_output"]["deliverables"]
        project_id:   ID проекта (для папки render)
        slot_id:      цех-источник (для памяти и экономики)

    Returns:
        AssemblyResult с путём к final.mp4 и статистикой
    """
    project_id = project_id or deliverables.get("project_id", "unknown")
    render_dir = RENDER_DIR / project_id
    render_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n[МОНТАЖЁР] 🎬 Начинаю сборку: {project_id}")

    # Пробуждение в городе
    _wake(slot_id)

    result = AssemblyResult(
        project_id=project_id,
        status="FAILED",
        final_path=None,
        assembled_at=datetime.datetime.utcnow().isoformat(),
    )

    try:
        # ── 1. Собираем клипы ──────────────────────────────────────
        clips = _collect_clips(deliverables)
        result.clips_total = len(clips)

        if not clips:
            result.errors.append("Нет клипов с video_path — нечего склеивать")
            print(f"[МОНТАЖЁР] ❌ {result.errors[-1]}")
            _done(slot_id, result)
            return result

        valid_clips = [c for c in clips if c.get("video_path") and
                       Path(c["video_path"]).exists()]
        result.clips_used = len(valid_clips)

        if not valid_clips:
            result.errors.append(
                f"Все {result.clips_total} клипов имеют video_path но файлы не найдены"
            )
            print(f"[МОНТАЖЁР] ❌ {result.errors[-1]}")
            _done(slot_id, result)
            return result

        missing = result.clips_total - result.clips_used
        if missing:
            print(f"[МОНТАЖЁР] ⚠️  Пропущено {missing} клипов (нет файла) — собираю что есть")
            result.errors.append(f"Пропущено {missing}/{result.clips_total} клипов")

        # ── 2. Сырая склейка клипов ───────────────────────────────
        raw_video = render_dir / "raw_concat.mp4"
        duration  = _concat_clips(valid_clips, raw_video)
        result.duration_sec = duration
        print(f"[МОНТАЖЁР] ✅ Склейка: {result.clips_used} клипов → {duration:.1f}с")

        # ── 3. Аудио-слои ─────────────────────────────────────────
        audio_data = deliverables.get("audio", {})
        audio_mix  = None

        if audio_data:
            audio_mix = _mix_audio(audio_data, duration, render_dir)
            result.has_audio = audio_mix is not None and audio_mix.get("music") is not None
            result.has_vo    = audio_mix is not None and bool(audio_mix.get("vo_lines"))
            result.has_sfx   = audio_mix is not None and bool(audio_mix.get("sfx_points"))

        # ── 4. Финальная компиляция ────────────────────────────────
        final_path = render_dir / "final.mp4"

        if audio_mix and audio_mix.get("mixed_path"):
            _merge_video_audio(raw_video, audio_mix["mixed_path"], final_path)
            print(f"[МОНТАЖЁР] ✅ Видео + аудио → {final_path.name}")
        else:
            # Без аудио — просто переименовываем raw
            shutil.copy2(str(raw_video), str(final_path))
            print(f"[МОНТАЖЁР] ℹ️  Аудио нет — финал без звука")

        # Удаляем промежуточный файл
        if raw_video.exists() and raw_video != final_path:
            raw_video.unlink()

        # ── 5. Пишем манифест сборки ──────────────────────────────
        _write_manifest(result, deliverables, render_dir)

        result.status     = "DONE" if not result.errors else "PARTIAL"
        result.final_path = str(final_path)

        # Этап 2 — Артур смотрит финал
        _arthur_review(result, deliverables, slot_id)

        size_mb = final_path.stat().st_size / 1024 / 1024
        print(f"\n[МОНТАЖЁР] 🎉 {result.status}: {final_path}")
        print(f"           {size_mb:.1f} МБ · {duration:.1f}с · "
              f"клипов {result.clips_used}/{result.clips_total} · "
              f"аудио={'✅' if result.has_audio else '—'} "
              f"vo={'✅' if result.has_vo else '—'} "
              f"sfx={'✅' if result.has_sfx else '—'}")

    except Exception as e:
        result.status = "FAILED"
        result.errors.append(str(e))
        print(f"[МОНТАЖЁР] ❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()

    finally:
        _done(slot_id, result)

    return result


def get_assembly_status(project_id: str) -> dict:
    """
    Возвращает статус последней сборки проекта из манифеста.

    Returns:
        {
          "status": "DONE|PARTIAL|FAILED|NOT_ASSEMBLED",
          "final_path": str | None,
          "assembled_at": str | None,
          "duration_sec": float,
          "clips_used": int,
          "clips_total": int,
          "has_audio": bool,
          "errors": list,
        }
    """
    manifest_path = RENDER_DIR / project_id / "assembly_manifest.json"
    if not manifest_path.exists():
        return {
            "status": "NOT_ASSEMBLED",
            "final_path": None,
            "assembled_at": None,
            "duration_sec": 0.0,
            "clips_used": 0,
            "clips_total": 0,
            "has_audio": False,
            "errors": [],
        }
    try:
        return json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as e:
        return {"status": "ERROR", "error": str(e)}


# ═══════════════════════════════════════════════════════════════════
# СБОРКА КЛИПОВ
# ═══════════════════════════════════════════════════════════════════

def _collect_clips(deliverables: dict) -> list[dict]:
    """Собирает список клипов из deliverables в порядке shot_id."""
    clips = deliverables.get("video_clips", [])
    if not clips:
        return []

    # Сортируем по shot_id если есть (shot_01, shot_02, ...)
    def _sort_key(c):
        sid = c.get("shot_id", "")
        # Извлекаем числовую часть: shot_03 → 3
        import re
        m = re.search(r"(\d+)", sid)
        return int(m.group(1)) if m else 999

    return sorted(clips, key=_sort_key)


def _concat_clips(clips: list[dict], output_path: Path) -> float:
    """
    Склеивает mp4-клипы в один через ffmpeg concat demuxer.
    Возвращает итоговую длительность в секундах.
    """
    if not _ffmpeg_available():
        raise RuntimeError(
            "ffmpeg не найден. Установи ffmpeg и добавь в PATH.\n"
            "Windows: https://ffmpeg.org/download.html"
        )

    # Создаём временный concat-лист
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False, encoding="utf-8"
    ) as f:
        concat_file = Path(f.name)
        for clip in clips:
            path = Path(clip["video_path"]).resolve()
            # ffmpeg требует экранирования обратных слешей на Windows
            f.write(f"file '{str(path).replace(chr(92), '/')}'\n")

    try:
        cmd = [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_file),
            "-c", "copy",              # без перекодирования — быстро
            "-movflags", "+faststart", # для стриминга
            str(output_path),
        ]
        _run_ffmpeg(cmd, "concat")

        # Получаем длительность результата
        return _get_duration(output_path)

    finally:
        concat_file.unlink(missing_ok=True)


# ═══════════════════════════════════════════════════════════════════
# АУДИО МИКС
# ═══════════════════════════════════════════════════════════════════

def _mix_audio(audio_data: dict, video_duration: float, render_dir: Path) -> dict | None:
    """
    Микширует аудио-слои: музыка + SFX + VO.

    Приоритет громкости (стандарт Сэма):
      VO:    0 dB  (главный)
      SFX:  -6 dB
      Music: -12 dB (под VO) / -6 dB (без VO)

    Возвращает dict с mixed_path или None если нечего микшировать.
    """
    music_data = audio_data.get("music", {})
    sfx_list   = audio_data.get("sfx_list", [])
    vo_lines   = audio_data.get("vo_lines", [])

    music_path = music_data.get("audio_path") if isinstance(music_data, dict) else None
    ducking_db = music_data.get("ducking_db", -12) if isinstance(music_data, dict) else -12

    # Собираем доступные дорожки
    has_music = music_path and Path(music_path).exists()
    sfx_points = [s for s in sfx_list
                  if s.get("sfx_path") and Path(s["sfx_path"]).exists()]
    vo_points  = [v for v in vo_lines
                  if v.get("vo_path") and Path(v["vo_path"]).exists()]

    if not has_music and not sfx_points and not vo_points:
        print("[МОНТАЖЁР] ℹ️  Нет аудиофайлов — пропускаю микш")
        return None

    print(f"[МОНТАЖЁР] 🎧 Микш: "
          f"музыка={'✅' if has_music else '—'} "
          f"sfx={len(sfx_points)} "
          f"vo={len(vo_points)}")

    mixed_path = render_dir / "audio_mix.mp3"

    # ── Простой случай: только музыка, нет SFX и VO ──────────────
    if has_music and not sfx_points and not vo_points:
        # Обрезаем/дополняем до длины видео
        _trim_audio_to_duration(
            Path(music_path), mixed_path,
            duration=video_duration,
            volume_db=ducking_db,
        )
        return {"mixed_path": str(mixed_path), "music": music_path,
                "vo_lines": [], "sfx_points": []}

    # ── Полный микш через ffmpeg amix ────────────────────────────
    inputs  = []
    filters = []
    stream  = 0

    if has_music:
        inputs += ["-i", str(music_path)]
        # Обрезаем музыку до длины видео + фейд-аут последние 2с
        fade_start = max(0, video_duration - 2)
        filters.append(
            f"[{stream}:a]"
            f"atrim=duration={video_duration:.2f},"
            f"volume={_db_to_factor(ducking_db):.3f},"
            f"afade=t=out:st={fade_start:.2f}:d=2"
            f"[music]"
        )
        stream += 1

    # VO дорожки — склеиваем последовательно по timing_sec
    if vo_points:
        for i, vo in enumerate(vo_points):
            inputs += ["-i", str(vo["vo_path"])]
            delay_ms = int(float(vo.get("timing_sec", 0)) * 1000)
            filters.append(
                f"[{stream}:a]adelay={delay_ms}|{delay_ms}[vo{i}]"
            )
            stream += 1

    # SFX точки — каждый в свой момент
    if sfx_points:
        for i, sfx in enumerate(sfx_points):
            inputs += ["-i", str(sfx["sfx_path"])]
            delay_ms = int(float(sfx.get("timing_sec", 0)) * 1000)
            vol = _db_to_factor(-6)
            filters.append(
                f"[{stream}:a]adelay={delay_ms}|{delay_ms},"
                f"volume={vol:.3f}[sfx{i}]"
            )
            stream += 1

    # Собираем все дорожки в amix
    mix_inputs = ""
    n = 0
    if has_music:
        mix_inputs += "[music]"
        n += 1
    for i in range(len(vo_points)):
        mix_inputs += f"[vo{i}]"
        n += 1
    for i in range(len(sfx_points)):
        mix_inputs += f"[sfx{i}]"
        n += 1

    if n == 0:
        return None

    if n == 1:
        # Только одна дорожка — без amix
        filters.append(f"{mix_inputs}acopy[out]")
    else:
        filters.append(
            f"{mix_inputs}amix=inputs={n}:duration=longest:normalize=0[out]"
        )

    filter_complex = ";".join(filters)

    cmd = [
        "ffmpeg", "-y",
        *inputs,
        "-filter_complex", filter_complex,
        "-map", "[out]",
        "-c:a", "libmp3lame", "-q:a", "2",
        "-t", str(video_duration),
        str(mixed_path),
    ]

    try:
        _run_ffmpeg(cmd, "audio_mix")
        print(f"[МОНТАЖЁР] ✅ Аудио микш готов: {mixed_path.name}")
        return {
            "mixed_path": str(mixed_path),
            "music":      music_path,
            "vo_lines":   vo_points,
            "sfx_points": sfx_points,
        }
    except Exception as e:
        print(f"[МОНТАЖЁР] ❌ Аудио микш упал: {e}")
        # Fallback: только музыка если есть
        if has_music:
            print("[МОНТАЖЁР] ℹ️  Fallback → только музыка")
            _trim_audio_to_duration(
                Path(music_path), mixed_path,
                duration=video_duration,
                volume_db=ducking_db,
            )
            return {"mixed_path": str(mixed_path), "music": music_path,
                    "vo_lines": [], "sfx_points": []}
        return None


def _trim_audio_to_duration(
    src: Path, dest: Path,
    duration: float,
    volume_db: float = -12,
) -> None:
    """Обрезает аудио до нужной длины с фейд-аутом."""
    fade_start = max(0, duration - 2)
    vol = _db_to_factor(volume_db)
    cmd = [
        "ffmpeg", "-y",
        "-i", str(src),
        "-af",
        f"volume={vol:.3f},afade=t=out:st={fade_start:.2f}:d=2",
        "-t", str(duration),
        "-c:a", "libmp3lame", "-q:a", "2",
        str(dest),
    ]
    _run_ffmpeg(cmd, "trim_audio")


# ═══════════════════════════════════════════════════════════════════
# ФИНАЛЬНАЯ КОМПИЛЯЦИЯ
# ═══════════════════════════════════════════════════════════════════

def _merge_video_audio(
    video_path: Path,
    audio_path: str,
    output_path: Path,
) -> None:
    """
    Склеивает видео и аудио в финальный mp4.
    Аудио имеет приоритет по длине (shortest=0 → берём длину видео).
    """
    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-i", str(audio_path),
        "-c:v", "copy",           # видео без перекодирования
        "-c:a", "aac",            # аудио → AAC для mp4
        "-b:a", "192k",
        "-shortest",              # обрезаем по короткой дорожке
        "-movflags", "+faststart",
        str(output_path),
    ]
    _run_ffmpeg(cmd, "merge_video_audio")


# ═══════════════════════════════════════════════════════════════════
# МАНИФЕСТ СБОРКИ
# ═══════════════════════════════════════════════════════════════════

def _write_manifest(
    result: AssemblyResult,
    deliverables: dict,
    render_dir: Path,
) -> None:
    """Пишет assembly_manifest.json рядом с final.mp4."""
    manifest = {
        "project_id":   result.project_id,
        "status":       result.status,
        "final_path":   result.final_path,
        "assembled_at": result.assembled_at,
        "duration_sec": result.duration_sec,
        "clips_used":   result.clips_used,
        "clips_total":  result.clips_total,
        "has_audio":    result.has_audio,
        "has_vo":       result.has_vo,
        "has_sfx":      result.has_sfx,
        "errors":       result.errors,
        "platform":     deliverables.get("platform", ""),
        "assembler":    MONTEUR_ID,
    }
    path = render_dir / "assembly_manifest.json"
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[МОНТАЖЁР] 📋 Манифест: {path.name}")


# ═══════════════════════════════════════════════════════════════════
# ПАМЯТЬ И ЭКОНОМИКА
# ═══════════════════════════════════════════════════════════════════

def _wake(slot_id: str) -> None:
    """Монтажёр просыпается — пишет в grondheim_memory."""
    try:
        from studio.grondheim_memory import on_agent_wake
        on_agent_wake(MONTEUR_ID, dept="residents")
    except Exception:
        pass


def _done(slot_id: str, result: AssemblyResult) -> None:
    """
    Монтажёр завершил работу:
    - grondheim_memory: on_agent_done (сенсорная память)
    - ministry.record_outcome (факт транзакции)
    - billing_ledger (стоимость рендера — пока 0, ffmpeg бесплатный)
    """
    # ── Грондхейм ────────────────────────────────────────────────
    try:
        from studio.grondheim_memory import on_agent_done
        summary = (
            f"Собрал {result.clips_used}/{result.clips_total} клипов, "
            f"{result.duration_sec:.1f}с, статус {result.status}"
        )
        quality = 1.0 if result.status == "DONE" else (
            0.6 if result.status == "PARTIAL" else 0.2
        )
        on_agent_done(
            agent_id=MONTEUR_ID,
            result_summary=summary,
            quality_score=quality,
            dept="residents",
        )
    except Exception:
        pass

    # ── Экономика — Ministry ──────────────────────────────────────
    try:
        from studio.economy import ministry as _min
        score = 8.0 if result.status == "DONE" else (
            5.0 if result.status == "PARTIAL" else 0.0
        )
        _min.record_outcome(
            agent_id=MONTEUR_ID,
            slot_id=slot_id,
            score=score,
            cost_usd=0.0,  # ffmpeg бесплатный
        )
    except Exception:
        pass

    # ── Биллинг ──────────────────────────────────────────────────
    try:
        from studio import billing_ledger as _ledger
        _ledger.record(
            agent_id=MONTEUR_ID,
            slot_id=slot_id,
            model="ffmpeg",
            prompt_tokens=0,
            completion_tokens=0,
            call_type="video_assembly",
        )
    except Exception:
        pass


# ═══════════════════════════════════════════════════════════════════
# УТИЛИТЫ
# ═══════════════════════════════════════════════════════════════════

def _ffmpeg_available() -> bool:
    try:
        subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True, timeout=5,
        )
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _run_ffmpeg(cmd: list, step: str) -> None:
    """Запускает ffmpeg команду. При ошибке бросает RuntimeError с логом."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600,  # 10 минут максимум
        )
        if result.returncode != 0:
            # Последние 20 строк stderr — достаточно для диагностики
            log_tail = "\n".join(result.stderr.strip().splitlines()[-20:])
            raise RuntimeError(f"ffmpeg [{step}] вернул код {result.returncode}:\n{log_tail}")
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"ffmpeg [{step}] не завершился за 10 минут")


def _get_duration(path: Path) -> float:
    """Получает длительность медиафайла через ffprobe."""
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                str(path),
            ],
            capture_output=True, text=True, timeout=15,
        )
        data = json.loads(result.stdout)
        return float(data.get("format", {}).get("duration", 0))
    except Exception:
        return 0.0


def _db_to_factor(db: float) -> float:
    """Конвертирует dB в линейный множитель громкости."""
    import math
    return 10 ** (db / 20)

# ═══════════════════════════════════════════════════════════════════
# ЭТАП 2 — АРТУР СМОТРИТ ФИНАЛ
# ═══════════════════════════════════════════════════════════════════

def _arthur_review(result: AssemblyResult, deliverables: dict, slot_id: str) -> dict:
    """
    Артур смотрит на final.mp4 после сборки.

    Два отдельных результата:

    assembly_assessment — оценка своей работы (без LLM):
        clips_assembled, audio_layers, duration_sec, errors, verdict
        verdict: PASS / PARTIAL / FAIL — только из данных сборки
        → влияет на DNA через sync_to_dna()

    arthur_notes — взгляд жителя города (LLM + vision):
        feeling, observation, concern
        → пишется в хроники города
        → НЕ влияет на DNA никогда

    Returns:
        dict с ключами "assembly_assessment" и "arthur_notes"
    """

    # ── 1. assembly_assessment — из данных, без LLM ──────────────────────────

    if result.status == "DONE" and not result.errors:
        verdict = "PASS"
    elif result.status == "PARTIAL" or (result.status == "DONE" and result.errors):
        verdict = "PARTIAL"
    else:
        verdict = "FAIL"

    audio_layers = "нет"
    if result.has_audio or result.has_vo or result.has_sfx:
        parts = []
        if result.has_audio:
            parts.append("музыка")
        if result.has_vo:
            parts.append("VO")
        if result.has_sfx:
            parts.append("SFX")
        audio_layers = " + ".join(parts)

    assembly_assessment = {
        "clips_assembled": f"{result.clips_used} из {result.clips_total}",
        "audio_layers":    audio_layers,
        "duration_sec":    round(result.duration_sec, 1),
        "errors":          result.errors[:3],  # не более 3 — остальное в манифесте
        "verdict":         verdict,
    }

    print(f"[АРТУР] 📋 Сборка: {assembly_assessment['clips_assembled']} клипов · "
          f"{assembly_assessment['duration_sec']}с · {audio_layers} · {verdict}")

    # DNA только от assembly_assessment
    _sync_assembly_to_dna(verdict, slot_id)

    # ── 2. arthur_notes — LLM смотрит final.mp4 ─────────────────────────────

    arthur_notes = _arthur_look(result, deliverables)

    # Записываем в хроники города (не в DNA)
    if arthur_notes.get("feeling") or arthur_notes.get("observation"):
        _write_to_chronicles(arthur_notes, result.project_id)

    return {
        "assembly_assessment": assembly_assessment,
        "arthur_notes":        arthur_notes,
    }


def _sync_assembly_to_dna(verdict: str, slot_id: str):
    """DNA меняется только от качества сборки — не от качества контента."""
    try:
        from studio.grondheim_memory import sync_to_dna
        if verdict == "PASS":
            sync_to_dna(MONTEUR_ID, "good_work", intensity=1.0, dept="residents")
        elif verdict == "FAIL":
            sync_to_dna(MONTEUR_ID, "bad_work", intensity=1.0, dept="residents")
        # PARTIAL — нейтрально, не трогаем DNA
    except Exception as e:
        print(f"[АРТУР] ⚠️  sync_to_dna: {e}")


def _arthur_look(result: AssemblyResult, deliverables: dict) -> dict:
    """
    Артур смотрит на final.mp4 — как человек, не как критик.

    Появляется только когда что-то зацепило.
    Большинство сборок — null. Это нормально.
    """
    if not result.final_path or not Path(result.final_path).exists():
        print("[АРТУР] ℹ️  final.mp4 нет — взгляд пропускаю")
        return {}

    frames = _extract_frames(result.final_path)
    if not frames:
        print("[АРТУР] ⚠️  Кадры не извлечь — взгляд пропускаю")
        return {}

    timeline_ctx = (
        f"Клипов: {result.clips_used}. "
        f"Длина: {result.duration_sec:.0f} сек. "
        f"Платформа: {deliverables.get('platform', '?')}."
    )

    model = _choose_model(result, deliverables)
    print(f"[АРТУР] 👁  Смотрю финал · модель: {model}")

    system = """Ты — Артур. Монтажёр. Только что досмотрел финальный ролик.

Ты не кинокритик. Не пиши рецензию.
Ты человек который последним выключил монитор после рендера.

ЗАПРЕЩЕНО использовать слова:
нарратив, композиция, эмоциональная арка, динамика, визуальный,
контент, концепция, референс, качество, уровень, демонстрирует,
поддерживается, реализован, выстроен.

ЗАПРЕЩЕНО:
- ставить оценки и рейтинги
- анализировать работу коллег
- писать экспертные формулировки

Отвечай как человек который только что досмотрел фильм и ещё не решил понравился он ему или нет.

Если ничего не зацепило — верни null во все поля.
Не придумывай впечатление которого нет.

Если что-то осталось — одна-две живые фразы. Не больше.

Примеры как это звучит:
"Странно. Я думал сцена с Ашотом пройдёт мимо. А её почему-то помню."
"Музыка осталась в голове дольше кадров."
"Не уверен что понял историю. Но мальчишку жалко."
"Концовка будто торопится."
"Ничего особенного."

Отвечай строго в JSON:
{
  "feeling": "одна фраза или null",
  "observation": "одна фраза или null",
  "concern": "одна фраза или null"
}

Все три могут быть null. Это нормально."""

    user = (
        f"{timeline_ctx}\n\n"
        "Три кадра: начало, середина, конец.\n"
        "Что осталось?"
    )

    try:
        from studio.llm import chat_with_images
        import json as _json
        import re as _re

        raw = chat_with_images(
            system=system,
            user_text=user,
            images=frames,
            agent_id=MONTEUR_ID,
            slot_id="assembly",
        )

        m = _re.search(r'\{.*\}', raw, _re.DOTALL)
        if m:
            notes = _json.loads(m.group())

            # Если всё null — молчим. Это нормально.
            if not any([notes.get("feeling"), notes.get("observation"), notes.get("concern")]):
                print("[АРТУР] 🤫 Ничего не зацепило — молчу")
                return {}

            feeling = notes.get("feeling") or ""
            obs = notes.get("observation") or ""
            print(f"[АРТУР] 💭 {feeling}" + (f" · {obs[:60]}" if obs else ""))
            return notes

    except Exception as e:
        print(f"[АРТУР] ⚠️  LLM взгляд упал: {e}")

    return {}


def _choose_model(result: AssemblyResult, deliverables: dict) -> str:
    """
    Артур сам выбирает модель для взгляда.

    Flash — стандарт.
    Pro — если ролик длинный (> 120с) или много клипов (> 8).
    Sonnet — если платформа требует художественной точности.
    """
    duration = result.duration_sec
    clips    = result.clips_used
    platform = deliverables.get("platform", "")

    if platform in ("youtube", "website") and duration > 180:
        # Длинный ролик для серьёзной платформы — Pro
        model = "google/gemini-2.5-pro"
        reason = "длинный ролик для YouTube/сайта — нужна глубина"
    elif clips > 8:
        # Много клипов — сложный таймлайн
        model = "google/gemini-2.5-pro"
        reason = f"{clips} клипов — сложный таймлайн"
    else:
        model = "google/gemini-2.5-flash"
        reason = "стандартный ролик — Flash справится"

    print(f"[АРТУР] 🧠 Модель: {model} ({reason})")
    return model


def _extract_frames(video_path: str) -> list:
    """
    Извлекает 3 кадра из final.mp4 через ffprobe/ffmpeg.
    Возвращает список dict для chat_with_images().
    """
    import subprocess
    import tempfile
    import base64
    import json as _json

    path = Path(video_path)

    try:
        # Узнаём длительность
        probe = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json",
             "-show_format", str(path)],
            capture_output=True, text=True, timeout=15,
        )
        duration = 10.0
        try:
            data = _json.loads(probe.stdout)
            duration = float(data.get("format", {}).get("duration", 10))
        except Exception:
            pass

        # Три момента: начало, середина, конец
        timestamps = [
            max(0.5, duration * 0.05),
            duration * 0.5,
            max(0.5, duration * 0.92),
        ]
        labels = ["начало", "середина", "конец"]
        frames = []

        with tempfile.TemporaryDirectory() as tmpdir:
            for i, (ts, label) in enumerate(zip(timestamps, labels)):
                fp = Path(tmpdir) / f"frame_{i}.jpg"
                subprocess.run(
                    ["ffmpeg", "-ss", str(ts), "-i", str(path),
                     "-vframes", "1", "-q:v", "4", str(fp), "-y"],
                    capture_output=True, timeout=20,
                )
                if fp.exists() and fp.stat().st_size > 0:
                    b64 = base64.b64encode(fp.read_bytes()).decode("ascii")
                    frames.append({
                        "base64":    b64,
                        "mime_type": "image/jpeg",
                        "name":      f"кадр_{label}_{ts:.0f}с.jpg",
                    })

        print(f"[АРТУР] 🎞  Кадров извлечено: {len(frames)}/3")
        return frames

    except FileNotFoundError:
        print("[АРТУР] ⚠️  ffmpeg не найден — кадры не извлечь")
        return []
    except Exception as e:
        print(f"[АРТУР] ⚠️  Ошибка извлечения кадров: {e}")
        return []


def _write_to_chronicles(notes: dict, project_id: str):
    """Записывает arthur_notes в хроники города."""
    try:
        from studio.grondheim_memory import record_resonance_event
        feeling = notes.get("feeling", "")
        observation = notes.get("observation", "")
        concern = notes.get("concern", "")

        content_parts = []
        if feeling:
            content_parts.append(f"Ощущение: {feeling}")
        if observation:
            content_parts.append(f"Заметил: {observation}")
        if concern:
            content_parts.append(f"Насторожило: {concern}")

        content = " / ".join(content_parts)
        if content:
            record_resonance_event(
                agent_id=MONTEUR_ID,
                event_type="reflection",
                content=f"[{project_id}] {content}",
                significance=0.4,
                tags=["assembly", "arthur_notes", project_id],
                dept="residents",
            )
            print(f"[АРТУР] 📖 В хроники: {content[:80]}")
    except Exception as e:
        print(f"[АРТУР] ⚠️  Хроники: {e}")


