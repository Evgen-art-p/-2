"""
studio/siliconflow_client.py
============================
Клиент для генерации видео через SiliconFlow API.
Модель: Wan-AI/Wan2.2-I2V-A14B (img2video)
Музыка: CosyVoice (TTS/пение персонажей)

Архитектура:
  • submit → polling → скачать mp4
  • Retry 3 попытки (паузы 5с / 10с / 20с)
  • Таймаут polling: 600с (10 минут)
  • Параллельная генерация через ThreadPoolExecutor
"""

import os
import re
import time
import json
import base64
import shutil
import datetime
import httpx
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from studio.config import SILICONFLOW_API_KEY

# ── Настройки ────────────────────────────────────────────────────────
API_BASE        = "https://api.siliconflow.com/v1"
MODEL_I2V       = "Wan-AI/Wan2.2-I2V-A14B"
MODEL_TTS       = "FunAudioLLM/CosyVoice2-0.5B"

OUTPUT_DIR      = Path("output/generated")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

POLL_INTERVAL   = 5.0     # секунд между опросами
POLL_MAX_WAIT   = 600     # максимум 10 минут на клип
_RETRY_DELAYS   = [5, 10, 20]
_MAX_WORKERS    = 3       # параллельных генераций


# ── HTTP хелпер ──────────────────────────────────────────────────────

def _headers() -> dict:
    return {
        "Authorization": f"Bearer {SILICONFLOW_API_KEY}",
        "Content-Type": "application/json",
    }


def _post(endpoint: str, payload: dict, timeout: int = 30) -> dict:
    url = f"{API_BASE}/{endpoint}"
    with httpx.Client(timeout=timeout) as client:
        r = client.post(url, json=payload, headers=_headers())
        r.raise_for_status()
        return r.json()


def _get(endpoint: str, timeout: int = 15) -> dict:
    url = f"{API_BASE}/{endpoint}"
    with httpx.Client(timeout=timeout) as client:
        r = client.get(url, headers=_headers())
        r.raise_for_status()
        return r.json()


# ── Скачивание ───────────────────────────────────────────────────────

def _download(url: str, filepath: Path, retries: int = 3):
    """Скачивает файл по URL. Поддерживает data:// и https://"""
    if url.startswith("data:"):
        _, b64 = url.split(",", 1)
        filepath.write_bytes(base64.b64decode(b64))
        return

    last_err = None
    for attempt in range(retries):
        try:
            with httpx.Client(timeout=httpx.Timeout(connect=15, read=180, write=15, pool=15)) as client:
                r = client.get(url, headers={"Authorization": f"Bearer {SILICONFLOW_API_KEY}"})
                r.raise_for_status()
                filepath.write_bytes(r.content)
                return
        except Exception as e:
            last_err = e
            wait = (attempt + 1) * 5
            print(f"  ⚠️  Скачивание попытка {attempt+1}: {e} — жду {wait}с...")
            time.sleep(wait)
    raise RuntimeError(f"Не удалось скачать {url}: {last_err}")


# ═══════════════════════════════════════════════════════════════════
# ИЗОБРАЖЕНИЕ → ВИДЕО (Wan2.2 I2V)
# ═══════════════════════════════════════════════════════════════════

def _image_to_base64(image_path: str) -> str:
    """Конвертирует картинку в base64 data URI для SiliconFlow."""
    src = Path(image_path)
    if not src.exists():
        raise FileNotFoundError(f"Картинка не найдена: {image_path}")

    # Сжимаем через Pillow если есть
    try:
        from PIL import Image
        import io
        img = Image.open(str(src))
        if img.mode in ("RGBA", "P", "LA"):
            bg = Image.new("RGB", img.size, (255, 255, 255))
            if img.mode == "P":
                img = img.convert("RGBA")
            if "A" in img.mode:
                bg.paste(img, mask=img.split()[-1])
            else:
                bg.paste(img)
            img = bg
        elif img.mode != "RGB":
            img = img.convert("RGB")

        # Resize до 720p если больше
        w, h = img.size
        if max(w, h) > 1280:
            ratio = 1280 / max(w, h)
            img = img.resize((int(w*ratio), int(h*ratio)), Image.LANCZOS)

        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85, optimize=True)
        data = buf.getvalue()
        print(f"  📐 Картинка: {w}x{h} → {img.size[0]}x{img.size[1]}, {len(data)//1024}Кб")
    except ImportError:
        data = src.read_bytes()

    ext = src.suffix.lower().replace(".", "") or "jpeg"
    mime = f"image/{ext}" if ext in ("png", "webp") else "image/jpeg"
    b64 = base64.b64encode(data).decode("ascii")
    return f"data:{mime};base64,{b64}"


def generate_video(
    image_path: str,
    motion_prompt: str,
    filename: str = None,
    duration: int = 5,
    resolution: str = "720p",
    agent_id: str = "A08",
    slot_id: str = "video_long",
) -> str:
    """
    Генерирует видео из картинки через Wan2.2-I2V-A14B.

    Args:
        image_path: путь к картинке (output от Евы)
        motion_prompt: текст движения (EN, из motion_intent Лукаса)
        filename: имя mp4 файла
        duration: длительность в секундах (4 или 8)
        resolution: "480p" или "720p"
        agent_id: для биллинга
        slot_id: для биллинга

    Returns:
        str: путь к скачанному mp4
    """
    if not filename:
        filename = f"clip_{int(time.time())}.mp4"

    # Приводим duration к допустимым значениям (4 или 8)
    duration = 8 if duration > 6 else 4

    print(f"🎬 [Wan2.2 I2V] Генерирую: {filename}")
    print(f"   Промт: {motion_prompt[:80]}...")
    print(f"   Длина: {duration}с | Разрешение: {resolution}")

    # Конвертируем картинку
    image_b64 = _image_to_base64(image_path)

    payload = {
        "model": MODEL_I2V,
        "prompt": motion_prompt,
        "image": image_b64,
        "duration": duration,
        "resolution": resolution,
    }

    # Submit
    last_err = None
    request_id = None
    for attempt in range(len(_RETRY_DELAYS) + 1):
        try:
            result = _post("video/submit", payload, timeout=60)
            request_id = result.get("requestId")
            if not request_id:
                raise ValueError(f"requestId не получен: {result}")
            print(f"  📤 Отправлено → {request_id}")
            break
        except Exception as e:
            last_err = e
            if attempt < len(_RETRY_DELAYS):
                wait = _RETRY_DELAYS[attempt]
                print(f"  ⚠️  Submit попытка {attempt+1}: {e} — жду {wait}с...")
                time.sleep(wait)
    else:
        raise RuntimeError(f"Submit не удался после {len(_RETRY_DELAYS)+1} попыток: {last_err}")

    # Polling
    start = time.time()
    while True:
        elapsed = time.time() - start
        if elapsed > POLL_MAX_WAIT:
            raise TimeoutError(f"Wan2.2 не ответил за {POLL_MAX_WAIT}с: {request_id}")

        try:
            status_data = _get(f"video/status/{request_id}")
            status = status_data.get("status", "")

            if status == "Succeed":
                video_url = (
                    status_data.get("results", {}).get("videos", [{}])[0].get("url")
                    or status_data.get("video", {}).get("url")
                    or status_data.get("url")
                )
                if not video_url:
                    raise ValueError(f"URL видео не найден в ответе: {status_data}")
                print(f"  ✅ Готово за {elapsed:.1f}с")
                break

            elif status == "Failed":
                reason = status_data.get("reason", "неизвестно")
                raise RuntimeError(f"Генерация упала: {reason}")

            else:
                # InQueue / InProgress
                print(f"  ⏳ {status}... ({elapsed:.0f}с)")

        except (RuntimeError, ValueError):
            raise
        except Exception as e:
            print(f"  ⚠️  Polling ошибка: {e} — жду...")

        time.sleep(POLL_INTERVAL)

    # Скачиваем
    filepath = OUTPUT_DIR / filename
    print(f"  📥 Скачиваю mp4...")
    _download(video_url, filepath)

    # Биллинг
    try:
        from studio import billing_ledger as _ledger
        _ledger.record(
            agent_id=agent_id,
            slot_id=slot_id,
            model=f"siliconflow/{MODEL_I2V}",
            prompt_tokens=0,
            completion_tokens=0,
            call_type="video_i2v",
        )
    except Exception:
        pass

    size_mb = filepath.stat().st_size / 1024 / 1024
    print(f"  ✅ {filepath} ({size_mb:.1f} МБ)")
    return str(filepath)


def generate_video_with_retry(
    image_path: str,
    motion_prompt: str,
    filename: str,
    duration: int = 5,
    resolution: str = "720p",
    agent_id: str = "A08",
    slot_id: str = "video_long",
) -> str:
    """Обёртка с ретраями для использования в хуках."""
    last_exc = None
    for attempt in range(3):
        try:
            return generate_video(
                image_path=image_path,
                motion_prompt=motion_prompt,
                filename=filename,
                duration=duration,
                resolution=resolution,
                agent_id=agent_id,
                slot_id=slot_id,
            )
        except Exception as e:
            last_exc = e
            if attempt < 2:
                wait = _RETRY_DELAYS[attempt]
                print(f"  ⚠️  Попытка {attempt+1}/3 упала: {e} — жду {wait}с...")
                time.sleep(wait)
    raise last_exc


# ═══════════════════════════════════════════════════════════════════
# ПАРАЛЛЕЛЬНАЯ ГЕНЕРАЦИЯ КЛИПОВ (для хука A08)
# ═══════════════════════════════════════════════════════════════════

def generate_clips_parallel(
    clips: list[dict],
    project_dir: Path,
    slot_id: str = "video_long",
) -> list[dict]:
    """
    Параллельная генерация клипов из списка.

    Каждый элемент clips[]:
      {
        "shot_id": "shot_01",
        "scene_id": "scene_01",
        "image_path": "/path/to/frame.png",   ← из eva_visuals.frames[].path
        "motion_prompt": "...",                ← из video_clips[].motion_prompt
        "duration_sec": 5,
        "camera_move": "dolly_in",
      }

    Returns: тот же список с добавленным "video_path" (или None если упало)
    """
    total = len(clips)
    print(f"\n🎬 [Wan2.2 I2V] Параллельная генерация {total} клипов "
          f"(до {_MAX_WORKERS} потоков)...")

    def _gen_one(args):
        idx, clip = args
        shot_id  = clip.get("shot_id",  f"shot_{idx+1:02d}")
        scene_id = clip.get("scene_id", f"scene_{idx+1}")
        img_path = clip.get("image_path", "")
        prompt   = clip.get("motion_prompt", "")
        duration = clip.get("duration_sec", 5)

        if not img_path or not Path(img_path).exists():
            print(f"  ❌ {shot_id}: картинка не найдена ({img_path})")
            clip["video_path"] = None
            return idx, clip

        if not prompt:
            print(f"  ❌ {shot_id}: motion_prompt пуст")
            clip["video_path"] = None
            return idx, clip

        filename = f"{_slugify(scene_id)[:20]}_{_slugify(shot_id)[:15]}.mp4"
        print(f"  → клип {idx+1}/{total}: {filename}")

        try:
            path = generate_video_with_retry(
                image_path=img_path,
                motion_prompt=prompt,
                filename=filename,
                duration=duration,
                agent_id="A08",
                slot_id=slot_id,
            )
            # Переносим в папку проекта
            dest = project_dir / filename
            shutil.move(path, dest)
            clip["video_path"] = str(dest)
            print(f"  ✅ {shot_id}: {dest}")
        except Exception as e:
            print(f"  ❌ {shot_id}: {e}")
            clip["video_path"] = None
            clip["error"] = str(e)

        return idx, clip

    results = list(clips)
    with ThreadPoolExecutor(max_workers=_MAX_WORKERS) as pool:
        future_map = {pool.submit(_gen_one, (i, c)): i for i, c in enumerate(clips)}
        for future in as_completed(future_map, timeout=POLL_MAX_WAIT * total):
            try:
                idx, clip = future.result()
                results[idx] = clip
            except Exception as e:
                idx = future_map[future]
                print(f"  ❌ Поток {idx} упал: {e}")
                results[idx]["video_path"] = None

    ok = sum(1 for c in results if c.get("video_path"))
    print(f"\n[Wan2.2 I2V] Итог: {ok}/{total} клипов успешно\n")
    return results


# ═══════════════════════════════════════════════════════════════════
# TTS / ПЕНИЕ ПЕРСОНАЖЕЙ (CosyVoice через SiliconFlow)
# ═══════════════════════════════════════════════════════════════════

def generate_speech(
    text: str,
    voice: str = "alex",
    filename: str = None,
    agent_id: str = "A10",
    slot_id: str = "video_long",
) -> str:
    """
    Генерирует речь/озвучку через CosyVoice2-0.5B.

    Args:
        text: текст для озвучки
        voice: голос (alex, anna, и др. доступные в CosyVoice)
        filename: имя аудио файла

    Returns:
        str: путь к mp3/wav файлу
    """
    if not filename:
        filename = f"speech_{int(time.time())}.mp3"

    print(f"🎙️ [CosyVoice] TTS: {text[:60]}...")

    payload = {
        "model": MODEL_TTS,
        "input": text,
        "voice": voice,
        "response_format": "mp3",
    }

    for attempt in range(len(_RETRY_DELAYS) + 1):
        try:
            with httpx.Client(timeout=60) as client:
                r = client.post(
                    f"{API_BASE}/audio/speech",
                    json=payload,
                    headers=_headers(),
                )
                r.raise_for_status()
                filepath = OUTPUT_DIR / filename
                filepath.write_bytes(r.content)
                print(f"  ✅ {filepath}")
                return str(filepath)
        except Exception as e:
            if attempt < len(_RETRY_DELAYS):
                wait = _RETRY_DELAYS[attempt]
                print(f"  ⚠️  TTS попытка {attempt+1}: {e} — жду {wait}с...")
                time.sleep(wait)
            else:
                raise RuntimeError(f"TTS не удался: {e}")


# ═══════════════════════════════════════════════════════════════════
# УТИЛИТЫ
# ═══════════════════════════════════════════════════════════════════

def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9а-яА-ЯёЁ_-]", "_", str(name).lower().strip())
    slug = re.sub(r"_+", "_", slug).strip("_")
    return slug or "unknown"


def check_api() -> bool:
    """Проверяет доступность SiliconFlow API."""
    try:
        with httpx.Client(timeout=10) as client:
            r = client.get(
                f"{API_BASE}/models",
                headers=_headers(),
            )
            r.raise_for_status()
            print("✅ SiliconFlow API доступен")
            return True
    except Exception as e:
        print(f"❌ SiliconFlow API недоступен: {e}")
        return False


def test_single_clip(image_path: str, prompt: str = None) -> str:
    """
    Быстрый тест: одна картинка → один mp4.
    Запускать из корня репо:
        python -c "from studio.siliconflow_client import test_single_clip; test_single_clip('path/to/frame.png')"
    """
    if not prompt:
        prompt = "Camera slowly pushes in. Cinematic motion, smooth and steady."
    print(f"\n🧪 ТЕСТ: {image_path}")
    path = generate_video(
        image_path=image_path,
        motion_prompt=prompt,
        filename=f"test_{int(time.time())}.mp4",
        duration=4,
        resolution="480p",  # 480p для теста — дешевле и быстрее
    )
    print(f"\n✅ Тест прошёл: {path}")
    return path
