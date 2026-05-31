"""
studio/sync_client.py — клиент для sync.so lipsync API
Студия "Шесть пальцев" | Спринт 30

Основной вызов:
  run_lipsync(video_path, audio_path, output_path) → output_path

Переменные окружения:
  SYNC_API_KEY   — API ключ с sync.so dashboard
  SYNC_MODEL     — модель (default: lipsync-2)
  SYNC_POLL_SEC  — интервал поллинга в секундах (default: 5)
  SYNC_TIMEOUT   — максимум ожидания в секундах (default: 300)
"""

import os
import time
import requests
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

SYNC_API_BASE  = "https://api.sync.so/v2"
SYNC_API_KEY   = os.getenv("SYNC_API_KEY", "")
SYNC_MODEL     = os.getenv("SYNC_MODEL", "lipsync-2")
SYNC_POLL_SEC  = int(os.getenv("SYNC_POLL_SEC", "5"))
SYNC_TIMEOUT   = int(os.getenv("SYNC_TIMEOUT", "300"))


def _headers() -> dict:
    if not SYNC_API_KEY:
        raise RuntimeError("SYNC_API_KEY не задан в .env")
    return {
        "x-api-key": SYNC_API_KEY,
        "Content-Type": "application/json",
    }


def submit_lipsync(video_url: str, audio_url: str, model: str = None) -> str:
    """Отправляет задачу. Возвращает job_id."""
    model = model or SYNC_MODEL
    payload = {
        "model": model,
        "input": [
            {"type": "video", "url": video_url},
            {"type": "audio", "url": audio_url},
        ],
        "options": {
            "output_format": "mp4",
            "sync_mode": "bounce",
            "temperature": 0.5,
        }
    }
    resp = requests.post(
        f"{SYNC_API_BASE}/generate",
        headers=_headers(),
        json=payload,
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    job_id = data.get("id")
    if not job_id:
        raise RuntimeError(f"sync.so не вернул job_id: {data}")
    logger.info(f"[sync.so] job submitted: {job_id} | model: {model}")
    return job_id


def poll_lipsync(job_id: str, output_path: str) -> str:
    """Поллит статус. При COMPLETED скачивает mp4. Возвращает output_path."""
    deadline = time.time() + SYNC_TIMEOUT
    while time.time() < deadline:
        resp = requests.get(
            f"{SYNC_API_BASE}/generate/{job_id}",
            headers=_headers(),
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        status = data.get("status", "UNKNOWN")
        logger.debug(f"[sync.so] job {job_id} status: {status}")

        if status == "COMPLETED":
            video_url = (
                data.get("outputUrl")
                or data.get("output_url")
                or (data.get("output") or {}).get("url")
            )
            if not video_url:
                raise RuntimeError(f"sync.so COMPLETED но нет URL: {data}")
            _download(video_url, output_path)
            logger.info(f"[sync.so] готово → {output_path}")
            return output_path

        if status in ("FAILED", "REJECTED"):
            error = data.get("error") or data.get("message") or status
            raise RuntimeError(f"sync.so job {job_id} {status}: {error}")

        time.sleep(SYNC_POLL_SEC)

    raise TimeoutError(f"sync.so job {job_id} не завершился за {SYNC_TIMEOUT}с")


def _download(url: str, dest: str) -> None:
    Path(dest).parent.mkdir(parents=True, exist_ok=True)
    resp = requests.get(url, timeout=120, stream=True)
    resp.raise_for_status()
    with open(dest, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)


def _upload_to_fileio(local_path: str) -> str:
    """Временный хостинг через file.io (expire=1h). Для продакшна — заменить на S3/R2."""
    with open(local_path, "rb") as f:
        resp = requests.post(
            "https://file.io",
            files={"file": f},
            data={"expires": "1h"},
            timeout=60,
        )
    resp.raise_for_status()
    data = resp.json()
    url = data.get("link")
    if not url:
        raise RuntimeError(f"file.io не вернул ссылку: {data}")
    return url


def run_lipsync(
    video_path: str,
    audio_path: str,
    output_path: str,
    model: str = None,
) -> str:
    """
    Основной вызов из Монтажёра.
    video_path + audio_path (локальные файлы) → output_path (lipsync mp4).
    """
    logger.info(f"[sync.so] загружаю видео: {video_path}")
    video_url = _upload_to_fileio(video_path)
    logger.info(f"[sync.so] загружаю аудио: {audio_path}")
    audio_url = _upload_to_fileio(audio_path)

    job_id = submit_lipsync(video_url, audio_url, model=model)
    return poll_lipsync(job_id, output_path)


def estimate_cost(duration_sec: float, model: str = None) -> float:
    """Примерная стоимость в $."""
    rates = {
        "lipsync-2":     0.04,
        "lipsync-2-pro": 0.07,
        "sync-3":        0.133,
    }
    rate = rates.get(model or SYNC_MODEL, 0.05)
    return round(duration_sec * rate, 4)
