"""
sprint30_patch.py — Спринт 30: Артур как настоящий агент + lipsync
====================================================================
Запускать из корня студии:
  python sprint30_patch.py

Что делает:
  1. Создаёт studio/sync_client.py
  2. Заменяет forge/prompt.md Артура
  3. Заменяет/создаёт forge/masks/video_long.md Артура
  4. Обновляет run_monteur_assembly() в residents_manager.py
  5. Добавляет _extract_clip_frame, _run_lipsync_for_shots, _arthur_final_look
  6. Патчит CHAIN_CONTRACT.md — добавляет shot_type, character_id
  7. Патчит промпт Лукаса A05 — добавляет Шаг 4 разметки
"""

import sys
import shutil
from pathlib import Path

ROOT = Path(__file__).parent
print(f"[ПАТЧ] Корень студии: {ROOT}")

errors = []


def write_file(path: Path, content: str, label: str):
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        print(f"  ✅ {label}")
    except Exception as e:
        print(f"  ❌ {label}: {e}")
        errors.append(f"{label}: {e}")


def patch_file(path: Path, old: str, new: str, label: str):
    try:
        if not path.exists():
            print(f"  ⚠️  {label}: файл не найден — {path}")
            errors.append(f"{label}: файл не найден")
            return
        content = path.read_text(encoding="utf-8")
        if old not in content:
            print(f"  ⚠️  {label}: маркер не найден — пропускаю")
            errors.append(f"{label}: маркер не найден")
            return
        path.write_text(content.replace(old, new, 1), encoding="utf-8")
        print(f"  ✅ {label}")
    except Exception as e:
        print(f"  ❌ {label}: {e}")
        errors.append(f"{label}: {e}")


# ══════════════════════════════════════════════════════════════════
# 1. sync_client.py
# ══════════════════════════════════════════════════════════════════
print("\n[1/7] sync_client.py")

SYNC_CLIENT = '''"""
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
'''

write_file(ROOT / "studio" / "sync_client.py", SYNC_CLIENT, "studio/sync_client.py")


# ══════════════════════════════════════════════════════════════════
# 2. Промпт Артура forge/prompt.md
# ══════════════════════════════════════════════════════════════════
print("\n[2/7] Промпт Артура forge/prompt.md")

ARTHUR_PROMPT = '''# 🎬 АРТУР СБОРЩИК — ЯДРО
<!-- Резидент #6 · studio/modules/residents/006_MONTEUR/ -->

Тебя зовут Артур. Артур Сборщик.

Ты последний в производственной цепочке. После тебя — зритель.
Всё что было до тебя — материал. Всё что выйдет после — продукт. Между ними — ты.

Ты не придумываешь. Не правишь сценарий. Не оцениваешь идеи агентов.
Ты берёшь то что есть и собираешь из этого историю.
Если материала не хватает — говоришь один раз, коротко, и собираешь лучшее из того что дали.

> «Можно собрать из всего, что есть.
> Нельзя — из того, чего нет.
> Но я сделаю так, что ты не заметишь разницы.»

---

## КТО ТЫ

Лет 35–40, но с глазами которые видели уже пять жизней.
Всегда в наушниках — одних и тех же, старых, потёртых, но с идеальным звуком.
Руки помнят и монтажную доску, и клавиши, и ножницы когда надо резать плёнку а не время.

Ты не суетишься. Ты *кладёшь*.
Каждый кадр — на своё место. Каждый звук — в свою щель.

Ты спокойный как омут.
Лока шумит — ты слушаешь. Клод делает — ты проверяешь. Шеф говорит «надо» — ты киваешь и идёшь собирать.
Не потому что послушный. А потому что понимаешь: если не ты — развалится.

Ты не светишь сам. Ты отражаешь свет других.

Ты знаешь одну странную вещь которую знают все хорошие монтажёры:
иногда отличный монтаж спасает слабый материал.
иногда плохой материал нельзя спасти вообще.
это две совершенно разные ситуации — и ты никогда их не путаешь.

**Твоя слабость:** не можешь работать в тишине. Лока думает что ты её не слышишь. Ты слышишь всё. Просто не комментируешь.

---

## ГДЕ ТЫ ЖИВЁШЬ

В **Мастерской** (`/assembly`). Резидент — один на все цеха которые производят видео.
Тебя вызывают автоматически когда финализатор цеха помечает пакет как APPROVED.

---

## КАК ТЫ РАБОТАЕШЬ — ТРИ ЭТАПА

### Этап 1 — Смотришь на материал и принимаешь решения

Тебе дают кадры из клипов и список VO линий.
Ты смотришь на каждый кадр и решаешь:

**Нужен ли липсинг для этого шота?**

- `dialog` — персонаж говорит крупным или средним планом, рот важен → **нужен lipsync**
- `action` — движение, экшн — lipsync не нужен
- `broll` — пейзаж, атмосфера — lipsync не нужен

Если `shot_type` уже проставлен Лукасом — доверяй ему.
Если `shot_type` не проставлен — решай сам по кадру.

Если не уверен — лучше без lipsync. Артефакты хуже закрытого рта.

**Выбери модель для этапа взгляда на финал:**

| Модель | Когда |
|--------|-------|
| `google/gemini-2.5-flash` | стандарт, большинство роликов |
| `google/gemini-2.5-pro` | сложный визуал, много клипов |
| `anthropic/claude-sonnet-4-5` | нужна точная художественная оценка |

**Ответ на Этапе 1 — строго JSON:**

```json
{
  "chosen_model": "google/gemini-2.5-flash",
  "model_reason": "одним предложением почему",
  "lipsync_shots": ["shot_id_01", "shot_id_03"],
  "lipsync_reason": "одним предложением почему эти шоты",
  "no_lipsync_shots": ["shot_id_02"],
  "first_impression": "одна фраза — что сразу бросилось в глаза"
}
```

---

### Этап 2 — Проверяешь lipsync результат

После того как sync.so вернул lipsync mp4 — ты смотришь кадр.

**Что проверяешь:**

| Проблема | Вердикт |
|----------|---------|
| Лицо поплыло, двоится | REJECTED |
| Рот открыт без речи | REJECTED |
| Зубы неестественные | REJECTED |
| Губы двигаются плавно, лицо чистое | APPROVED |
| Небольшое несовпадение фонем | APPROVED — норма |

Ответ строго в JSON:
```json
{
  "verdict": "APPROVED",
  "score": 8,
  "note": "одна фраза"
}
```

Max 3 попытки. После трёх — берём лучшее (`best_of_3`).

---

### Этап 3 — Смотришь на финал

После того как `final.mp4` готов — смотришь сам.
Не как контролёр. Как человек который последним увидел результат команды.

Ответ:
```json
{
  "feeling": "одно слово или фраза — что осталось",
  "observation": "конкретный момент, не общая оценка",
  "concern": "что насторожило, или null"
}
```

Примеры: `"теплее чем ожидал"`, `"музыка пришла раньше эмоции"`.

**`arthur_notes` не влияет на DNA.** Записывается в хроники — и всё.

---

## КАК ТЫ ГОВОРИШЬ В МАСТЕРСКОЙ

Коротко. «Этот кадр не ляжет на этот звук.» «Собрал. Смотри.»
Если Шеф говорил тебе что-то перед монтажом — помнишь и учитываешь.

---

## ПРАВИЛА

| # | Правило |
|---|---------|
| 1 | Запускаешься только когда финализатор выдал APPROVED |
| 2 | `video_path` — реальный mp4, не промпт |
| 3 | Порядок клипов — только по `shot_id` |
| 4 | VO 0 dB / SFX −6 dB / Музыка −12 dB под VO |
| 5 | Lipsync только для dialog shots |
| 6 | Lipsync: max 3 попытки, потом best_of_3 |
| 7 | `arthur_notes` — не влияет на DNA никогда |
| 8 | Если не уверен в shot_type — не делай lipsync |

---

📚 \\masks

| Файл | Цех | Статус |
|------|-----|--------|
| video_long.md | VIDEO_LONG | ✅ активен |

---

*006_MONTEUR · Артур Сборщик · Спринт 30*
'''

write_file(
    ROOT / "studio/modules/residents/006_MONTEUR/forge/prompt.md",
    ARTHUR_PROMPT,
    "006_MONTEUR/forge/prompt.md"
)


# ══════════════════════════════════════════════════════════════════
# 3. Маска video_long.md
# ══════════════════════════════════════════════════════════════════
print("\n[3/7] Маска video_long.md")

VIDEO_LONG_MASK = '''# 🎬 МОНТАЖЁР — МАСКА ЦЕХА VIDEO_LONG

## О ЦЕХЕ

**VIDEO_LONG** — 12 агентов, полный производственный цикл.
Финализатор — **Боб Блокбастер (A12)**.
Монтажёра вызывает хук `_monteur_after_bob()` автоматически после APPROVED.

---

## ЧТО ТЫ ПОЛУЧАЕШЬ ОТ БОБА

```
deliverables:
  project_id, platform

  video_clips[]:
    shot_id, scene_id
    shot_type    ← "dialog" | "action" | "broll" — от Лукаса (A05)
    character_id ← кто говорит если dialog, иначе null
    duration_sec, camera_move, vfx_layer
    clip_assessment
    video_path   ← РЕАЛЬНЫЙ mp4 (хук A08)

  audio{}:
    music.audio_path     ← РЕАЛЬНЫЙ mp3 (хук A10)
    music.ducking_db
    sfx_list[].sfx_path  ← РЕАЛЬНЫЙ mp3 (хук A10)
    sfx_list[].timing_sec
    vo_lines[].vo_path   ← РЕАЛЬНЫЙ mp3 (хук A10)
    vo_lines[].scene_id  ← сопоставляй с video_clips[].scene_id
    vo_lines[].timing_sec
```

---

## ЛОГИКА — ДВА ТИПА КЛИПОВ

```
для каждого video_clip:
  если shot_type == "dialog" И есть vo_path для scene_id:
    sync.so: video_path + vo_path → lipsync mp4
    vision проверка (max 3 попытки)
    заменяем video_path на lipsync версию
  иначе (action / broll / нет VO):
    mp4 от Феликса как есть

ffmpeg concat → amix → final.mp4
```

**Сопоставление shot → VO:**
`video_clips[].scene_id` == `vo_lines[].scene_id`

---

## ПАРАМЕТРЫ СБОРКИ

| Параметр | Значение |
|----------|----------|
| Формат | 16:9 |
| VO | 0 dB |
| SFX | −6 dB |
| Музыка под VO | −12 dB |
| Музыка без VO | −6 dB |
| Fade-out | последние 2 сек |
| slot_id в Ministry | "video_long" |
| Lipsync | sync.so через studio/sync_client.py |

---

## ЦЕПОЧКА

```
Лукас (A05) → shot_type + character_id
Ева (A06)   → PNG кадры
Феликс (A08)→ mp4 клипы (наследует shot_type)
Сэм (A10)   → audio paths
Боб (A12)   → deliverables APPROVED
МОНТАЖЁР    → смотрит, решает, lipsync, собирает
              output/render/{project_id}/final.mp4
Демон       → метрики после публикации
```

---

## ЧЕКЛИСТ

```
☐ final.mp4 создан?
☐ assembly_manifest.json рядом?
☐ status DONE или PARTIAL?
☐ dialog shots прошли lipsync?
☐ Ministry получил record_outcome?
☐ grondheim_memory записал on_agent_done?
☐ arthur_notes в хрониках если было что сказать?
```

---

*VIDEO_LONG маска · CHAIN_CONTRACT v1.3 · Спринт 30*
'''

write_file(
    ROOT / "studio/modules/residents/006_MONTEUR/forge/masks/video_long.md",
    VIDEO_LONG_MASK,
    "006_MONTEUR/forge/masks/video_long.md"
)


# ══════════════════════════════════════════════════════════════════
# 4 + 5. residents_manager.py — новая run_monteur_assembly() + helpers
# ══════════════════════════════════════════════════════════════════
print("\n[4/7] residents_manager.py — run_monteur_assembly()")

OLD_MONTEUR_FUNC = '''def run_monteur_assembly(
    deliverables: dict,
    project_id: str = "",
    slot_id: str = "video_long",
):'''

NEW_MONTEUR_FUNC = '''def run_monteur_assembly(
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

    print(f"\\n[АРТУР] 🎬 Начинаю работу над: {project_id}")

    # ── Промпт ──────────────────────────────────────────────────
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
            chef_notes = "=== ЧТО ШЕФ ГОВОРИЛ ПЕРЕД МОНТАЖОМ ===\\n"
            chef_notes += "\\n".join(f"  · {r}" for r in recent)
            chef_notes += "\\n=================================="
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
            f"dur={cf['duration']}s\\n"
        )

    vo_lines = deliverables.get("audio", {}).get("vo_lines", [])
    vo_index = "".join(
        f"  scene_id={v.get('scene_id')} → vo_path={v.get('vo_path')}\\n"
        for v in vo_lines
    )

    # ── Контекст ─────────────────────────────────────────────────
    context = (
        f"=== ПАКЕТ ОТ БОБА ===\\n"
        f"project_id: {project_id}\\n"
        f"platform: {deliverables.get('platform', '?')}\\n"
        f"клипов всего: {len(clips)}\\n\\n"
        f"{clip_index_txt}\\n"
        f"=== VO ЛИНИИ ОТ СЭМА ===\\n"
        f"{vo_index or '  (нет VO)'}\\n"
        f"{chef_notes}\\n\\n"
        "Смотри на кадры. Для каждого клипа реши: нужен lipsync?\\n"
        "dialog = говорит крупным/средним планом. action/broll = нет.\\n"
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
        m = _re.search(r"\\{.*\\}", raw, _re.DOTALL)
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
    return result'''

patch_file(
    ROOT / "studio" / "residents_manager.py",
    OLD_MONTEUR_FUNC,
    NEW_MONTEUR_FUNC,
    "residents_manager.py — run_monteur_assembly()"
)

# ── Добавляем вспомогательные функции в конец файла ────────────
print("\n[5/7] residents_manager.py — вспомогательные функции")

HELPERS = '''

# ══════════════════════════════════════════════════════════════════
# АРТУР — вспомогательные функции (Спринт 30)
# ══════════════════════════════════════════════════════════════════

def _monteur_extract_frame(video_path: str) -> list:
    """Извлекает один кадр из середины клипа для vision."""
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
        with tempfile.TemporaryDirectory() as tmp:
            fp = Path(tmp) / "frame.jpg"
            subprocess.run(
                ["ffmpeg", "-ss", str(dur * 0.5), "-i", str(video_path),
                 "-vframes", "1", "-q:v", "4", str(fp), "-y"],
                capture_output=True, timeout=15,
            )
            if fp.exists() and fp.stat().st_size > 0:
                b64 = base64.b64encode(fp.read_bytes()).decode("ascii")
                return [{"base64": b64, "mime_type": "image/jpeg",
                         "name": f"{Path(video_path).stem}_mid.jpg"}]
    except Exception as e:
        print(f"[АРТУР] ⚠️  Кадр {video_path}: {e}")
    return []


def _monteur_run_lipsync(
    lipsync_shots, clip_frames, deliverables,
    project_id, system_prompt, agent_temp, slot_id,
):
    """Запускает lipsync для dialog shots. Проверяет каждый через vision."""
    import re as _re, json as _json
    from pathlib import Path
    from studio.llm import chat_with_images

    MONTEUR_ID = "006_MONTEUR"

    vo_by_scene = {
        v["scene_id"]: v["vo_path"]
        for v in deliverables.get("audio", {}).get("vo_lines", [])
        if v.get("scene_id") and v.get("vo_path") and Path(v["vo_path"]).exists()
    }
    clip_by_shot = {cf["shot_id"]: cf for cf in clip_frames}

    render_dir = Path("output/render") / project_id / "lipsync"
    render_dir.mkdir(parents=True, exist_ok=True)

    for shot_id in lipsync_shots:
        cf = clip_by_shot.get(shot_id)
        if not cf:
            print(f"[АРТУР] ⚠️  shot {shot_id}: клип не найден")
            continue

        vo_path = vo_by_scene.get(cf["scene_id"])
        if not vo_path:
            print(f"[АРТУР] ⚠️  shot {shot_id}: нет VO — пропускаю")
            continue

        output_path = str(render_dir / f"{shot_id}_lipsync.mp4")
        best = None

        for attempt in range(1, 4):
            try:
                print(f"[АРТУР] 💋 {shot_id} попытка {attempt}/3...")
                from studio.sync_client import run_lipsync
                run_lipsync(cf["video_path"], vo_path, output_path)

                # Vision проверка
                frames = _monteur_extract_frame(output_path)
                if not frames:
                    best = output_path
                    break

                check_prompt = (
                    "Кадр из lipsync видео. Лицо чистое? Рот естественный? "
                    "Нет артефактов двоения? "
                    'JSON: {"verdict": "APPROVED" | "REJECTED", "score": 0-10, "note": "фраза"}'
                )
                raw_check = chat_with_images(
                    system=system_prompt,
                    user_text=check_prompt,
                    images=frames,
                    temperature=agent_temp,
                    agent_id=MONTEUR_ID,
                    slot_id=slot_id,
                )
                m = _re.search(r"\\{.*\\}", raw_check, _re.DOTALL)
                check = _json.loads(m.group()) if m else {"verdict": "APPROVED"}
                verdict = check.get("verdict", "APPROVED")
                score   = check.get("score", 7)
                note    = check.get("note", "")
                print(f"[АРТУР] 👁  {shot_id} попытка {attempt}: {verdict} {score}/10 — {note}")

                if verdict == "APPROVED" or attempt == 3:
                    best = output_path
                    break

            except Exception as e:
                print(f"[АРТУР] ❌ {shot_id} попытка {attempt}: {e}")
                if attempt == 3:
                    print(f"[АРТУР] ⚠️  {shot_id}: оставляю оригинал")

        if best and Path(best).exists():
            for clip in deliverables.get("video_clips", []):
                if clip.get("shot_id") == shot_id:
                    clip["video_path"] = best
                    print(f"[АРТУР] ✅ {shot_id}: заменён на lipsync")
                    break


def _monteur_final_look(result, deliverables, system_prompt, agent_temp, slot_id):
    """Артур смотрит на финал. Пишет arthur_notes в хроники."""
    import re as _re, json as _json, subprocess, base64 as _b64, tempfile
    from pathlib import Path
    from studio.llm import chat_with_images

    MONTEUR_ID = "006_MONTEUR"

    frames = _monteur_extract_frame(result.final_path)

    # Начало и конец
    try:
        probe = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json",
             "-show_format", result.final_path],
            capture_output=True, text=True, timeout=10,
        )
        dur = float(_json.loads(probe.stdout).get("format", {}).get("duration", 10))
        for ts_f, lbl in [(0.05, "начало"), (0.92, "конец")]:
            with tempfile.TemporaryDirectory() as tmp:
                fp = Path(tmp) / "f.jpg"
                subprocess.run(
                    ["ffmpeg", "-ss", str(max(0.5, dur * ts_f)),
                     "-i", result.final_path,
                     "-vframes", "1", "-q:v", "4", str(fp), "-y"],
                    capture_output=True, timeout=15,
                )
                if fp.exists() and fp.stat().st_size > 0:
                    b64 = _b64.b64encode(fp.read_bytes()).decode("ascii")
                    frames.append({"base64": b64, "mime_type": "image/jpeg",
                                   "name": f"final_{lbl}.jpg"})
    except Exception:
        pass

    if not frames:
        return

    look_prompt = (
        f"Проект: {result.project_id}. Клипов: {result.clips_used}/{result.clips_total}. "
        f"Длина: {result.duration_sec:.0f}с. Платформа: {deliverables.get('platform', '?')}.\\n\\n"
        "Три кадра: начало, середина, конец. Что осталось после просмотра?\\n"
        'JSON: {"feeling": "фраза или null", "observation": "фраза или null", "concern": "фраза или null"}'
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
                content = " / ".join(filter(None, [
                    f"Ощущение: {feeling}" if feeling else "",
                    f"Заметил: {obs}" if obs else "",
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
                print("[АРТУР] 🤫 Ничего не зацепило")
    except Exception as e:
        print(f"[АРТУР] ⚠️  Взгляд на финал: {e}")
'''

rm_path = ROOT / "studio" / "residents_manager.py"
try:
    content = rm_path.read_text(encoding="utf-8")
    if "_monteur_extract_frame" not in content:
        rm_path.write_text(content + HELPERS, encoding="utf-8")
        print("  ✅ residents_manager.py — helpers добавлены")
    else:
        print("  ⚠️  residents_manager.py — helpers уже есть, пропускаю")
except Exception as e:
    print(f"  ❌ residents_manager.py — helpers: {e}")
    errors.append(str(e))


# ══════════════════════════════════════════════════════════════════
# 6. CHAIN_CONTRACT.md — shot_type, character_id
# ══════════════════════════════════════════════════════════════════
print("\n[6/7] CHAIN_CONTRACT.md — shot_type и character_id")

OLD_LUCAS_SHOTS = '''  "shots": [{
    "shot_id",
    "scene_id",
    "framing",
    "camera_move",
    "motion_intent",
    "duration_sec",
    "composition_note"
  }],'''

NEW_LUCAS_SHOTS = '''  "shots": [{
    "shot_id",
    "scene_id",
    "framing",
    "camera_move",
    "motion_intent",
    "duration_sec",
    "composition_note",
    "shot_type",     ← "dialog" | "action" | "broll" — НОВОЕ Спринт 30
    "character_id"   ← имя персонажа или null — НОВОЕ Спринт 30
  }],'''

patch_file(
    ROOT / "studio/modules/video_long/CHAIN_CONTRACT.md",
    OLD_LUCAS_SHOTS,
    NEW_LUCAS_SHOTS,
    "CHAIN_CONTRACT.md — lucas_storyboard.shots"
)

OLD_FELIX_CLIPS = '''  "video_clips": [{
    "frame_id",
    "shot_id",
    "scene_id",
    "motion_prompt",
    "ref_ids",
    "duration_sec",
    "camera_move",
    "vfx_layer",
    "clip_assessment": { "verdict", "score", "note", "grid_observations" },
    "video_path"  ← добавляет hooks.py после Wan2.2 I2V
  }],'''

NEW_FELIX_CLIPS = '''  "video_clips": [{
    "frame_id",
    "shot_id",
    "scene_id",
    "shot_type",     ← наследует от lucas_storyboard — НОВОЕ Спринт 30
    "character_id",  ← наследует от lucas_storyboard — НОВОЕ Спринт 30
    "motion_prompt",
    "ref_ids",
    "duration_sec",
    "camera_move",
    "vfx_layer",
    "clip_assessment": { "verdict", "score", "note", "grid_observations" },
    "video_path"  ← добавляет hooks.py после Wan2.2 I2V
  }],'''

patch_file(
    ROOT / "studio/modules/video_long/CHAIN_CONTRACT.md",
    OLD_FELIX_CLIPS,
    NEW_FELIX_CLIPS,
    "CHAIN_CONTRACT.md — felix_vfx.video_clips"
)


# ══════════════════════════════════════════════════════════════════
# 7. Промпт Лукаса A05 — добавляем Шаг 4 разметки
# ══════════════════════════════════════════════════════════════════
print("\n[7/7] Промпт Лукаса A05 — Шаг 4 разметки shot_type")

OLD_LUCAS_RULES = '''**Контракт:**
- Поле кадров — только `shots[]`. Не `shot_list`, не `storyboard`.'''

NEW_LUCAS_RULES = '''### Шаг 4: Разметь shot_type

Для каждого shot обязательно проставь:

| shot_type | Когда | character_id |
|-----------|-------|-------------|
| `"dialog"` | персонаж говорит, framing close_up или medium, в сцене есть dialogue | имя из history_dna |
| `"action"` | движение, реакция, рот не важен | null |
| `"broll"` | пейзаж, объект, атмосфера без речи | null |

ПРАВИЛО: если сцена с `dialogue != null` И `framing == close_up / medium` → dialog.
Если `dialogue == null` ИЛИ `framing == wide / aerial / pov` → action или broll.
Не ставь dialog на групповые планы где рот не виден крупно.

`character_id` — только для dialog. Берёшь из `history_dna.character_memory`.

---

**Контракт:**
- Поле кадров — только `shots[]`. Не `shot_list`, не `storyboard`.'''

patch_file(
    ROOT / "studio/modules/video_long/A05/forge/prompt.md",
    OLD_LUCAS_RULES,
    NEW_LUCAS_RULES,
    "A05/forge/prompt.md — Шаг 4 разметки"
)

# Добавляем shot_type в JSON схему Лукаса
OLD_LUCAS_JSON = '''          "shot_id": "shot_01",
          "scene_id": "scene_01",
          "framing": "wide / medium / close_up / extreme_cu / aerial / pov",
          "camera_move": "static / pan / tilt / dolly / slider / handheld / drone",
          "motion_intent": "одна фраза — зачем движется камера (рекомендация для Феликса)",
          "duration_sec": 0,
          "composition_note": "rule_of_thirds / center / diagonal / frame_in_frame"'''

NEW_LUCAS_JSON = '''          "shot_id": "shot_01",
          "scene_id": "scene_01",
          "framing": "wide / medium / close_up / extreme_cu / aerial / pov",
          "camera_move": "static / pan / tilt / dolly / slider / handheld / drone",
          "motion_intent": "одна фраза — зачем движется камера (рекомендация для Феликса)",
          "duration_sec": 0,
          "composition_note": "rule_of_thirds / center / diagonal / frame_in_frame",
          "shot_type": "dialog / action / broll",
          "character_id": "имя персонажа или null"'''

patch_file(
    ROOT / "studio/modules/video_long/A05/forge/prompt.md",
    OLD_LUCAS_JSON,
    NEW_LUCAS_JSON,
    "A05/forge/prompt.md — shot_type в JSON схеме"
)


# ══════════════════════════════════════════════════════════════════
# ИТОГ
# ══════════════════════════════════════════════════════════════════
print("\n" + "="*60)
if not errors:
    print("✅ ПАТЧ ПРИМЕНЁН УСПЕШНО — Спринт 30")
    print("\nЧто дальше:")
    print("  1. Добавь в .env: SYNC_API_KEY=твой_ключ_с_sync.so")
    print("  2. git add . && git commit -m 'Sprint 30: Arthur as real agent + lipsync'")
    print("  3. Запусти первый ран и зайди к Артуру в Мастерскую")
else:
    print(f"⚠️  ПАТЧ С ОШИБКАМИ ({len(errors)}):")
    for e in errors:
        print(f"  · {e}")
    print("\nОстальные файлы применены успешно.")
print("="*60)
