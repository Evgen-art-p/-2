"""
studio/elevenlabs_client.py
============================
Клиент ElevenLabs для цехов video_long и video_shorts.

Три метода:
  generate_music(prompt, duration_sec, filename)  → фоновый трек MP3
  generate_sfx(prompt, duration_sec, filename)    → точечный звуковой эффект MP3
  generate_sfx_batch(sfx_list, project_dir)       → параллельная генерация SFX для всех сцен

Используется:
  A10 Сэм     → generate_music (фоновая музыка) + generate_sfx_batch (SFX по сценам)
  hooks.py    → _sam_generate_audio() после A10
  A12 Боб     → deliverables["audio"] содержит пути

Архитектура звука в ролике:
  1. VO/голос     — CosyVoice через siliconflow_client (хронометраж = база)
  2. SFX          — ElevenLabs sound-generation (точечно под ключевые действия)
  3. Музыка       — ElevenLabs music compose (фоновая подложка, ducking под VO)
  Сборка всех слоёв — ffmpeg в хуке A12 (Боб)
"""

import time
import json
import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

import httpx

from studio.config import ELEVENLABS_API_KEY

# ── Настройки ────────────────────────────────────────────────────────
API_BASE        = "https://api.elevenlabs.io/v1"
OUTPUT_DIR      = Path("output/generated")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

_RETRY_DELAYS   = [5, 10, 20]
_MAX_SFX_WORKERS = 4        # параллельных SFX генераций
_POLL_INTERVAL   = 5.0      # для потоковой музыки
_POLL_MAX_WAIT   = 300      # 5 минут на трек


# ═══════════════════════════════════════════════════════════════════
# МУЗЫКА — фоновый трек
# ═══════════════════════════════════════════════════════════════════

def generate_music(
    prompt: str,
    duration_sec: float = 60.0,
    filename: str = None,
    agent_id: str = "A10",
    slot_id: str = "video_long",
) -> str:
    """
    Генерирует фоновый музыкальный трек через ElevenLabs Music API.

    Args:
        prompt:       текстовый промпт (EN, описание настроения и стиля)
        duration_sec: длительность в секундах (3–600)
        filename:     имя MP3 файла
        agent_id:     для биллинга
        slot_id:      для биллинга

    Returns:
        str: путь к MP3 файлу

    Промпт-гайд для Сэма (A10):
        "Cinematic orchestral, warm and hopeful, slow build, no lyrics, 60 seconds"
        "Lo-fi ambient, minimal piano, soft pad, steady tempo, background music"
        "Corporate motivational, upbeat, light percussion, driving rhythm"
        НЕ упоминай: названия групп, артистов, копирайтные произведения
    """
    if not filename:
        filename = f"music_{int(time.time())}.mp3"

    # Клampим длительность в допустимый диапазон (3–600 сек)
    duration_ms = int(max(3000, min(600_000, duration_sec * 1000)))

    print(f"🎵 [ElevenLabs Music] Генерирую: {filename}")
    print(f"   Промт: {prompt[:80]}...")
    print(f"   Длина: {duration_sec:.0f}с")

    headers = _headers()
    payload = {
        "prompt":        prompt,
        "duration_ms":   duration_ms,
        "output_format": "mp3_44100_128",
    }

    filepath = OUTPUT_DIR / filename
    last_err = None

    for attempt in range(len(_RETRY_DELAYS) + 1):
        try:
            # ElevenLabs Music — потоковый endpoint, возвращает бинарный поток
            with httpx.Client(timeout=httpx.Timeout(connect=15, read=_POLL_MAX_WAIT,
                                                    write=15, pool=15)) as client:
                with client.stream("POST", f"{API_BASE}/music/compose",
                                   json=payload, headers=headers) as r:
                    r.raise_for_status()
                    with open(filepath, "wb") as f:
                        for chunk in r.iter_bytes(chunk_size=8192):
                            f.write(chunk)

            size_mb = filepath.stat().st_size / 1024 / 1024
            print(f"  ✅ {filepath} ({size_mb:.1f} МБ)")
            _record_billing(agent_id, slot_id, "elevenlabs_music")
            return str(filepath)

        except Exception as e:
            last_err = e
            if attempt < len(_RETRY_DELAYS):
                wait = _RETRY_DELAYS[attempt]
                print(f"  ⚠️  Попытка {attempt+1}: {e} — жду {wait}с...")
                time.sleep(wait)

    raise RuntimeError(f"ElevenLabs Music не удался за {len(_RETRY_DELAYS)+1} попытки: {last_err}")


# ═══════════════════════════════════════════════════════════════════
# SFX — один звуковой эффект
# ═══════════════════════════════════════════════════════════════════

def generate_sfx(
    prompt: str,
    duration_sec: float = None,
    filename: str = None,
    agent_id: str = "A10",
    slot_id: str = "video_long",
    prompt_influence: float = 0.5,
) -> str:
    """
    Генерирует звуковой эффект через ElevenLabs Sound Generation API.

    Args:
        prompt:           текстовый промпт (EN, лаконично)
        duration_sec:     длительность 0.5–30с. None = модель выберет сама
        filename:         имя MP3 файла
        prompt_influence: 0.0–1.0, насколько строго следовать промпту (0.5 рекомендуется)

    Returns:
        str: путь к MP3 файлу

    Промпт-гайд для Сэма (A10):
        "low cinematic boom"
        "cyberpunk door sliding open"
        "footsteps on gravel, slow pace"
        "distant thunder rumble"
        "paper rustling, quiet office"
        Правило: короткий, конкретный, без лирики
    """
    if not filename:
        filename = f"sfx_{int(time.time())}.mp3"

    print(f"🔊 [ElevenLabs SFX] {prompt[:60]}...")

    headers = _headers()
    payload = {
        "text":              prompt,
        "output_format":     "mp3_44100_128",
        "prompt_influence":  prompt_influence,
    }
    if duration_sec is not None:
        payload["duration_seconds"] = max(0.5, min(30.0, duration_sec))

    filepath = OUTPUT_DIR / filename
    last_err = None

    for attempt in range(len(_RETRY_DELAYS) + 1):
        try:
            with httpx.Client(timeout=60) as client:
                r = client.post(
                    f"{API_BASE}/sound-generation",
                    json=payload,
                    headers=headers,
                )
                r.raise_for_status()
                filepath.write_bytes(r.content)

            size_kb = filepath.stat().st_size // 1024
            print(f"  ✅ {filename} ({size_kb} Кб)")
            _record_billing(agent_id, slot_id, "elevenlabs_sfx")
            return str(filepath)

        except Exception as e:
            last_err = e
            if attempt < len(_RETRY_DELAYS):
                wait = _RETRY_DELAYS[attempt]
                print(f"  ⚠️  Попытка {attempt+1}: {e} — жду {wait}с...")
                time.sleep(wait)

    raise RuntimeError(f"ElevenLabs SFX не удался: {last_err}")


# ═══════════════════════════════════════════════════════════════════
# SFX BATCH — параллельная генерация для всех сцен
# ═══════════════════════════════════════════════════════════════════

def generate_sfx_batch(
    sfx_list: list[dict],
    project_dir: Path,
    agent_id: str = "A10",
    slot_id: str = "video_long",
) -> list[dict]:
    """
    Параллельная генерация SFX для всех сцен.

    sfx_list — список из промта Сэма (A10):
    [
      {
        "scene_id":    "scene_01",
        "sfx_prompt":  "low cinematic boom",
        "duration_sec": 2.0,        # опционально
        "timing_sec":   0.0,        # когда в ролике (для ffmpeg)
      },
      ...
    ]

    Returns:
        тот же список с добавленным "sfx_path" (str или None)
    """
    total = len(sfx_list)
    if total == 0:
        return sfx_list

    project_dir.mkdir(parents=True, exist_ok=True)
    print(f"\n🔊 [ElevenLabs SFX batch] {total} эффектов "
          f"(до {_MAX_SFX_WORKERS} потоков)...")

    def _gen_one(args):
        idx, item = args
        scene_id = item.get("scene_id", f"scene_{idx+1:02d}")
        prompt   = item.get("sfx_prompt", item.get("prompt", ""))
        duration = item.get("duration_sec")

        if not prompt:
            print(f"  ⚠️  {scene_id}: sfx_prompt пуст — пропускаю")
            item["sfx_path"] = None
            return idx, item

        filename = f"sfx_{_slugify(scene_id)}.mp3"
        dest     = project_dir / filename

        try:
            path = generate_sfx(
                prompt=prompt,
                duration_sec=duration,
                filename=filename,
                agent_id=agent_id,
                slot_id=slot_id,
            )
            import shutil as _sh
            _sh.move(path, dest)
            item["sfx_path"] = str(dest)
            print(f"  ✅ {scene_id}: {dest.name}")
        except Exception as e:
            print(f"  ❌ {scene_id}: {e}")
            item["sfx_path"] = None
            item["error"]    = str(e)

        return idx, item

    results = list(sfx_list)
    with ThreadPoolExecutor(max_workers=_MAX_SFX_WORKERS) as pool:
        future_map = {pool.submit(_gen_one, (i, item)): i
                      for i, item in enumerate(sfx_list)}
        for future in as_completed(future_map, timeout=120 * total):
            try:
                idx, item = future.result()
                results[idx] = item
            except Exception as e:
                idx = future_map[future]
                print(f"  ❌ Поток {idx} упал: {e}")
                results[idx]["sfx_path"] = None

    ok = sum(1 for r in results if r.get("sfx_path"))
    print(f"[ElevenLabs SFX batch] Итог: {ok}/{total} эффектов готово\n")
    return results


# ═══════════════════════════════════════════════════════════════════
# ВСПОМОГАТЕЛЬНЫЕ
# ═══════════════════════════════════════════════════════════════════

def _headers() -> dict:
    if not ELEVENLABS_API_KEY:
        raise RuntimeError("ELEVENLABS_API_KEY не найден в .env")
    return {
        "xi-api-key":   ELEVENLABS_API_KEY,
        "Content-Type": "application/json",
    }


def _slugify(name: str) -> str:
    import re
    slug = re.sub(r"[^a-zA-Z0-9_-]", "_", str(name).lower().strip())
    slug = re.sub(r"_+", "_", slug).strip("_")
    return slug or "unknown"


def _record_billing(agent_id: str, slot_id: str, call_type: str):
    try:
        from studio import billing_ledger as _ledger
        _ledger.record(
            agent_id=agent_id,
            slot_id=slot_id,
            model="elevenlabs",
            prompt_tokens=0,
            completion_tokens=0,
            call_type=call_type,
        )
    except Exception:
        pass


def check_api() -> bool:
    """Проверяет доступность ElevenLabs API."""
    try:
        with httpx.Client(timeout=10) as client:
            r = client.get(f"{API_BASE}/user", headers=_headers())
            r.raise_for_status()
            print("✅ ElevenLabs API доступен")
            return True
    except Exception as e:
        print(f"❌ ElevenLabs API недоступен: {e}")
        return False
