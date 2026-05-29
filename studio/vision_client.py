"""
studio/vision_client.py
=======================
ОТК — «Глаза» агентов. Проверяет качество сгенерированных медиафайлов.

Использует: OpenRouter → Gemini 2.5 Flash (vision)
  • Картинки (PNG/JPG): прямая проверка
  • Видео (MP4): извлекает 3 кадра (первый / середина / последний) через ffmpeg

Брак:
  При REJECTED файл перемещается в output/rejected/{project_id}/{filename}_attempt{N}
  Рядом кладётся JSON-карточка с причиной, артефактами, fix_hint, промптом.
  Это архив ошибок студии — Боб (A12) читает его для learnings_pack.

Возвращает:
  {
    "status": "APPROVED" | "REJECTED",
    "score": 0.0–1.0,
    "reason": "...",
    "artifacts": ["анатомия", "лишний персонаж", ...],
    "fix_hint": "что добавить в негатив при ретрае"
  }
"""

import base64
import datetime
import json
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

import httpx

from studio.config import OPENROUTER_API_KEY

# ── Настройки ────────────────────────────────────────────────────────
OPENROUTER_BASE    = "https://openrouter.ai/api/v1"
VISION_MODEL       = "google/gemini-2.5-flash"
APPROVAL_THRESHOLD = 0.65
MAX_RETRIES        = 3

REJECTED_DIR = Path("output/rejected")   # корень архива брака

# Базовые правила ОТК
_BASE_RULES = """
Ты — жёсткий технический контролёр качества визуального контента AI-студии.
Твоя задача: определить годен ли медиафайл для профессионального использования.

КРИТИЧЕСКИЕ ДЕФЕКТЫ (любой → REJECTED):
- Сломанная анатомия: лишние/отсутствующие пальцы, руки, ноги, глаза
- Деформированные лица: асимметрия, двойные черты, артефакты
- Смешение персонажей: два разных лица на одном теле
- Явные артефакты: пиксельный шум, размытие объектов переднего плана
- Текст/водяные знаки/логотипы (если не запрошены)
- Несоответствие формату: обрезанные главные объекты

ДОПУСТИМЫЕ НЕДОСТАТКИ (не влияют на решение):
- Лёгкое зерно/шум на фоне
- Небольшие неточности в окружении
- Чуть другой оттенок цвета

ФОРМАТ ОТВЕТА — только JSON, без markdown:
{
  "status": "APPROVED" или "REJECTED",
  "score": число от 0.0 до 1.0,
  "reason": "одно предложение — главная причина решения",
  "artifacts": ["список найденных дефектов или пустой массив"],
  "fix_hint": "что добавить в негативный промпт при ретрае, или пустая строка"
}
""".strip()


# ═══════════════════════════════════════════════════════════════════
# АРХИВ БРАКА
# ═══════════════════════════════════════════════════════════════════

def _archive_rejected(
    media_path: str,
    agent_id: str,
    attempt: int,
    result: dict,
    original_prompt: str,
    project_id: str = "",
) -> str:
    """
    Перемещает бракованный файл в output/rejected/{project_id}/
    и кладёт рядом JSON-карточку с метаданными.

    Структура:
        output/rejected/
        └── {project_id}/
            ├── {filename}_attempt{N}.png
            └── {filename}_attempt{N}.json  ← карточка брака

    Returns:
        str: путь к архивированному файлу
    """
    src = Path(media_path)
    if not src.exists():
        return ""

    # Папка брака
    folder_name = project_id or datetime.date.today().isoformat()
    dest_dir = REJECTED_DIR / folder_name
    dest_dir.mkdir(parents=True, exist_ok=True)

    # Имя файла с номером попытки
    stem    = src.stem
    suffix  = src.suffix
    dest_file = dest_dir / f"{stem}_attempt{attempt}{suffix}"

    # Перемещаем (не копируем — не плодим мусор)
    try:
        shutil.move(str(src), str(dest_file))
    except Exception as e:
        print(f"[ОТК архив] ⚠️  Не удалось переместить {src.name}: {e}")
        return ""

    # JSON-карточка брака
    card = {
        "agent_id":        agent_id,
        "attempt":         attempt,
        "timestamp":       datetime.datetime.utcnow().isoformat(),
        "original_prompt": original_prompt,
        "status":          "REJECTED",
        "score":           result.get("score", 0),
        "reason":          result.get("reason", ""),
        "artifacts":       result.get("artifacts", []),
        "fix_hint":        result.get("fix_hint", ""),
        "archived_file":   str(dest_file),
    }
    card_path = dest_dir / f"{stem}_attempt{attempt}.json"
    try:
        card_path.write_text(
            json.dumps(card, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
    except Exception as e:
        print(f"[ОТК архив] ⚠️  Не удалось записать карточку: {e}")

    print(f"[ОТК архив] 📁 Брак → {dest_file.relative_to(Path('.'))}")
    return str(dest_file)


def get_rejected_summary(project_id: str = "") -> list[dict]:
    """
    Читает карточки брака для проекта.
    Используется Бобом (A12) для learnings_pack.

    Returns:
        list of rejection cards (dict)
    """
    folder_name = project_id or datetime.date.today().isoformat()
    dest_dir = REJECTED_DIR / folder_name
    if not dest_dir.exists():
        return []

    cards = []
    for card_file in sorted(dest_dir.glob("*.json")):
        try:
            cards.append(json.loads(card_file.read_text(encoding="utf-8")))
        except Exception:
            pass
    return cards


# ═══════════════════════════════════════════════════════════════════
# ГЛАВНАЯ ФУНКЦИЯ
# ═══════════════════════════════════════════════════════════════════

def analyze_media_quality(
    media_path: str,
    original_prompt: str = "",
    rules: str = "",
    agent_id: str = "unknown",
) -> dict:
    """
    Проверяет качество картинки или видео.

    Args:
        media_path:      путь к PNG/JPG/MP4
        original_prompt: исходный промпт (для проверки соответствия)
        rules:           дополнительные правила ОТК
        agent_id:        для логирования

    Returns:
        dict: {"status", "score", "reason", "artifacts", "fix_hint"}
    """
    path = Path(media_path)
    if not path.exists():
        return _reject(f"Файл не найден: {media_path}")

    suffix = path.suffix.lower()
    if suffix in (".mp4", ".mov", ".webm"):
        return _check_video(path, original_prompt, rules, agent_id)
    elif suffix in (".png", ".jpg", ".jpeg", ".webp"):
        return _check_image(path, original_prompt, rules, agent_id)
    else:
        return _reject(f"Неподдерживаемый формат: {suffix}")


# ═══════════════════════════════════════════════════════════════════
# ПРОВЕРКА КАРТИНКИ
# ═══════════════════════════════════════════════════════════════════

def _check_image(path, original_prompt, rules, agent_id) -> dict:
    print(f"[ОТК {agent_id}] 👁 Проверяю: {path.name}")
    try:
        image_b64 = _image_to_b64(path)
    except Exception as e:
        return _reject(f"Не удалось прочитать: {e}")

    system  = _build_system_prompt(rules)
    content = _build_user_content(image_b64, original_prompt, path.suffix)
    result  = _call_vision_api(system, content, agent_id)
    _log_result(agent_id, path.name, result)
    return result


# ═══════════════════════════════════════════════════════════════════
# ПРОВЕРКА ВИДЕО (3 кадра)
# ═══════════════════════════════════════════════════════════════════

def _check_video(path, original_prompt, rules, agent_id) -> dict:
    print(f"[ОТК {agent_id}] 🎬 Проверяю видео: {path.name}")

    frames = _extract_video_frames(path)
    if not frames:
        return _reject("ffmpeg недоступен — видео-проверка пропущена")

    system = _build_system_prompt(
        rules + "\nЭто кадры из видео. Проверяй движение и консистентность."
    )

    frame_results = []
    labels = ["начальный", "средний", "финальный"]
    for i, frame_b64 in enumerate(frames):
        print(f"[ОТК {agent_id}]   → кадр {i+1}/3 ({labels[i]})")
        content = _build_user_content(
            frame_b64, original_prompt, ".jpg",
            extra=f"Это {labels[i]} кадр видеоклипа."
        )
        frame_results.append(_call_vision_api(system, content, agent_id))

    avg_score  = sum(r.get("score", 0) for r in frame_results) / len(frame_results)
    artifacts  = list(set(a for r in frame_results for a in r.get("artifacts", [])))
    rejected   = [r for r in frame_results if r.get("status") == "REJECTED"]

    if rejected or avg_score < APPROVAL_THRESHOLD:
        worst  = min(frame_results, key=lambda r: r.get("score", 0))
        result = {
            "status":    "REJECTED",
            "score":     round(avg_score, 3),
            "reason":    worst.get("reason", "Дефект в кадре"),
            "artifacts": artifacts,
            "fix_hint":  worst.get("fix_hint", ""),
        }
    else:
        result = {
            "status":    "APPROVED",
            "score":     round(avg_score, 3),
            "reason":    "Все кадры прошли проверку",
            "artifacts": artifacts,
            "fix_hint":  "",
        }

    _log_result(agent_id, path.name, result)
    return result


def _extract_video_frames(path: Path) -> list[str]:
    """Извлекает 3 кадра из MP4 через ffmpeg. Возвращает base64 JPEG."""
    try:
        probe = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_streams", str(path)],
            capture_output=True, text=True, timeout=15
        )
        duration = 5.0
        for stream in json.loads(probe.stdout).get("streams", []):
            d = stream.get("duration")
            if d:
                try:
                    duration = float(d)
                    break
                except ValueError:
                    pass

        timestamps   = [0.1, duration / 2, max(0.1, duration - 0.5)]
        frames_b64   = []

        with tempfile.TemporaryDirectory() as tmpdir:
            for i, ts in enumerate(timestamps):
                fp = Path(tmpdir) / f"frame_{i}.jpg"
                subprocess.run(
                    ["ffmpeg", "-ss", str(ts), "-i", str(path),
                     "-vframes", "1", "-q:v", "3", str(fp), "-y"],
                    capture_output=True, timeout=15
                )
                if fp.exists() and fp.stat().st_size > 0:
                    frames_b64.append(_image_to_b64(fp))

        return frames_b64

    except FileNotFoundError:
        print("[ОТК] ⚠️  ffmpeg не найден — пропускаю видео-проверку")
        return []
    except Exception as e:
        print(f"[ОТК] ⚠️  Ошибка извлечения кадров: {e}")
        return []


# ═══════════════════════════════════════════════════════════════════
# API — OpenRouter Gemini 2.5 Flash Vision
# ═══════════════════════════════════════════════════════════════════

def _call_vision_api(system_prompt, user_content, agent_id) -> dict:
    if not OPENROUTER_API_KEY:
        print(f"[ОТК {agent_id}] ⚠️  OPENROUTER_API_KEY нет — ОТК пропущен")
        return _approve("Нет ключа — ОТК пропущен")

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://studio.grondheim.ai",
        "X-Title":      "Six Fingers Studio OTK",
    }
    payload = {
        "model":       VISION_MODEL,
        "max_tokens":  512,
        "temperature": 0.1,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_content},
        ],
    }

    last_err = None
    for attempt in range(3):
        try:
            with httpx.Client(timeout=60) as client:
                r = client.post(
                    f"{OPENROUTER_BASE}/chat/completions",
                    json=payload, headers=headers,
                )
                r.raise_for_status()
                raw = r.json()["choices"][0]["message"]["content"]
                return _parse_response(raw)
        except Exception as e:
            last_err = e
            if attempt < 2:
                time.sleep(3 * (attempt + 1))
                print(f"[ОТК {agent_id}] ⚠️  Попытка {attempt+1}: {e}")

    print(f"[ОТК {agent_id}] ❌ Vision API недоступен: {last_err} — пропускаю")
    return _approve("Vision API недоступен — ОТК пропущен")


def _parse_response(text: str) -> dict:
    clean = re.sub(r"```json\s*|```", "", text).strip()
    match = re.search(r"\{[\s\S]*\}", clean)
    if match:
        clean = match.group(0)
    try:
        data = json.loads(clean)
        return {
            "status":    data.get("status", "APPROVED"),
            "score":     float(data.get("score", 0.7)),
            "reason":    data.get("reason", ""),
            "artifacts": data.get("artifacts", []),
            "fix_hint":  data.get("fix_hint", ""),
        }
    except Exception:
        return _approve("Не удалось распарсить ответ ОТК")


# ═══════════════════════════════════════════════════════════════════
# УМНАЯ ГЕНЕРАЦИЯ С ОТК — основная обёртка для hooks.py
# ═══════════════════════════════════════════════════════════════════

def generate_with_vision_check(
    generate_fn,
    original_prompt: str,
    agent_id: str,
    rules: str = "",
    max_visual_retries: int = MAX_RETRIES,
    on_retry=None,
    project_id: str = "",
) -> str:
    """
    Генерирует медиа, проверяет ОТК, при REJECTED архивирует брак и перегенерирует.

    Args:
        generate_fn:         callable() → str (путь к файлу)
        original_prompt:     исходный промпт
        agent_id:            A06 / A08 / A11
        rules:               дополнительные правила ОТК
        max_visual_retries:  максимум попыток
        on_retry:            callable(attempt, fix_hint) — коррекция промпта
        project_id:          для папки брака (output/rejected/{project_id}/)

    Returns:
        str: путь к одобренному файлу

    Raises:
        Exception: если все попытки провалились
    """
    last_result = {}

    for attempt in range(1, max_visual_retries + 1):
        print(f"[ОТК {agent_id}] 🎬 Дубль {attempt}/{max_visual_retries}")

        # Генерируем
        try:
            media_path = generate_fn()
        except Exception as e:
            print(f"[ОТК {agent_id}] ❌ Генерация упала: {e}")
            raise

        # Проверяем
        last_result = analyze_media_quality(
            media_path=media_path,
            original_prompt=original_prompt,
            rules=rules,
            agent_id=agent_id,
        )

        if last_result["status"] == "APPROVED":
            print(f"[ОТК {agent_id}] ✅ Дубль {attempt} одобрен")
            return media_path

        # REJECTED — архивируем брак
        print(f"[ОТК {agent_id}] ❌ Дубль {attempt} отклонён: {last_result['reason']}")
        _archive_rejected(
            media_path=media_path,
            agent_id=agent_id,
            attempt=attempt,
            result=last_result,
            original_prompt=original_prompt,
            project_id=project_id,
        )

        # Корректируем промпт перед следующим дублем
        if on_retry and attempt < max_visual_retries:
            try:
                on_retry(attempt, last_result.get("fix_hint", ""))
            except Exception as e:
                print(f"[ОТК {agent_id}] ⚠️  on_retry ошибка: {e}")

    raise Exception(
        f"[ОТК {agent_id}] Все {max_visual_retries} дублей в браке. "
        f"Последняя причина: {last_result.get('reason', '?')}. "
        f"Брак архивирован в output/rejected/{project_id or 'общий'}/"
    )


# ═══════════════════════════════════════════════════════════════════
# ВСПОМОГАТЕЛЬНЫЕ
# ═══════════════════════════════════════════════════════════════════

def _build_system_prompt(extra: str = "") -> str:
    if extra:
        return _BASE_RULES + "\n\nДОПОЛНИТЕЛЬНЫЕ ПРАВИЛА:\n" + extra.strip()
    return _BASE_RULES


def _build_user_content(image_b64, original_prompt, suffix, extra="") -> list:
    mime  = "image/jpeg" if suffix in (".jpg", ".jpeg") else "image/png"
    parts = []
    if original_prompt:
        parts.append(f"Оригинальный промпт: {original_prompt}")
    if extra:
        parts.append(extra)
    parts.append("Проверь изображение и выдай JSON-оценку.")
    return [
        {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{image_b64}"}},
        {"type": "text",      "text": "\n".join(parts)},
    ]


def _image_to_b64(path: Path) -> str:
    data = path.read_bytes()
    if len(data) > 1_000_000:
        try:
            from PIL import Image
            import io
            img = Image.open(path)
            if img.mode not in ("RGB", "L"):
                img = img.convert("RGB")
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=75, optimize=True)
            data = buf.getvalue()
        except ImportError:
            pass
    return base64.b64encode(data).decode("ascii")


def _log_result(agent_id, filename, result):
    icon   = "✅" if result.get("status") == "APPROVED" else "❌"
    score  = result.get("score", 0)
    reason = result.get("reason", "")
    print(f"[ОТК {agent_id}] {icon} {filename} — {result.get('status')} "
          f"(score={score:.2f}) {reason}")
    if result.get("artifacts"):
        print(f"[ОТК {agent_id}]   артефакты: {result['artifacts']}")
    if result.get("fix_hint"):
        print(f"[ОТК {agent_id}]   fix_hint:  {result['fix_hint']}")


def _approve(reason="") -> dict:
    return {"status": "APPROVED", "score": 1.0,
            "reason": reason, "artifacts": [], "fix_hint": ""}


def _reject(reason="") -> dict:
    return {"status": "REJECTED", "score": 0.0,
            "reason": reason, "artifacts": [], "fix_hint": ""}
