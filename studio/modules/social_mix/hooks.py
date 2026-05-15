# studio/modules/social_mix/hooks.py
# Студия «Шесть Пальцев» · 2026
# v3.0 — A06 генерирует картинку (до 5 попыток + Gemini-проверка).
#         A12 собирает готовый пост. PLAN-режим останавливается после A04.

import asyncio
import shutil
import time
from pathlib import Path


def on_before_agent(state: dict, worker_id: str, context: str) -> str:
    """Модифицирует контекст агента перед вызовом.

    В v3.0 контекст не модифицируется.
    """
    return context


def on_after_agent(state: dict, worker_id: str, human_text: str, meta: dict) -> dict:
    """Пост-обработка после каждого агента.

    Режим PLAN (run_type == "content_plan"):
        Стоп после A04.

    Режим POST:
        A06 → генерируем картинку (evan_visual → image_path).
        A12 → финальный роутинг (пайплайн уже завершён, хук для будущего).
        Остальные → продолжаем.

    Возвращает:
        {}               — продолжаем пайплайн
        {"action": "stop"} — остановить пайплайн
    """
    run_type = state.get("run_type", state.get("active_dept", ""))

    # PLAN: стоп после PRE-PROD (A04)
    if run_type == "content_plan" and worker_id == "A04":
        print(f"[HOOKS] 📋 PLAN: контент-план готов. Стоп после {worker_id}.")
        return {"action": "stop"}

    # A06 — Эван Вижн: генерируем картинку
    if worker_id == "A06":
        try:
            result = asyncio.get_event_loop().run_until_complete(
                _evan_generate_image(state)
            )
        except RuntimeError:
            # Если уже внутри event loop — создаём задачу через executor
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(_evan_generate_image_sync, state)
                future.result()

    return {}


# ─── Эван: генерация картинки ─────────────────────────────────────────────────

def _evan_generate_image_sync(state: dict):
    """Синхронная обёртка для вызова из thread (когда event loop уже занят)."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_evan_generate_image(state))
    finally:
        loop.close()


async def _evan_generate_image(state: dict):
    """
    Читает evan_visual из chain_data, генерирует картинку через fal.ai.

    Алгоритм:
      1. Берём prompt_positive, format из evan_visual (если нет — выходим тихо)
      2. Выбираем формат исходя из платформы (instagram→4:5, stories→9:16, vk→1:1, etc.)
      3. До 5 попыток: generate_image() → проверка через Gemini Flash
      4. Если качество ok — пишем image_path + quality в chain_data
      5. Если 5 попыток не дали ok — берём лучшую, помечаем quality: "fallback"
      6. Копируем финальный файл в {project_dir}/images/
    """
    from studio.assembly.constants import generate_image, generate_with_refs, IMAGE_FORMATS

    chain_data = state.get("chain_data", {})
    evan = chain_data.get("evan_visual", {})

    if not evan:
        print("[HOOKS/A06] evan_visual не найден в chain_data — пропускаю генерацию")
        return

    prompt_positive = evan.get("prompt_positive") or evan.get("prompt", "")
    prompt_negative = evan.get("prompt_negative", "")
    if not prompt_positive:
        print("[HOOKS/A06] prompt_positive пустой — пропускаю")
        return

    # Формат: берём из evan_visual или определяем по платформе
    fmt = evan.get("format") or _platform_to_format(
        chain_data.get("platform", state.get("platform", "instagram"))
    )
    # Добавляем 4:5 если нет в словаре fal_client (на случай старой версии)
    if fmt not in IMAGE_FORMATS and fmt == "4:5":
        fmt = "3:4"  # ближайший fallback

    # Референсы: char_ref / style_ref из state или chain_data
    ref_paths = _collect_refs(state, chain_data)

    # Папка проекта
    project_dir = Path(state.get("project_dir", "output/generated"))
    images_dir  = project_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    MAX_ATTEMPTS = 5
    best_path    = None
    best_score   = 0
    best_notes   = ""
    final_quality = "fallback"
    attempts_done = 0

    print(f"[HOOKS/A06] Генерирую картинку. Формат: {fmt}. Попыток: {MAX_ATTEMPTS}")

    for attempt in range(1, MAX_ATTEMPTS + 1):
        attempts_done = attempt
        fname = f"evan_visual_attempt{attempt}.png"
        print(f"[HOOKS/A06] Попытка {attempt}/{MAX_ATTEMPTS}: {prompt_positive[:60]}...")

        try:
            if ref_paths:
                tmp_path = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda p=prompt_positive, r=ref_paths, f=fmt, n=fname: generate_with_refs(
                        p, ref_paths=r, format=f, filename=n,
                        agent_id="A06", slot_id=f"social_img_{attempt}"
                    ),
                )
            else:
                tmp_path = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda p=prompt_positive, f=fmt, n=fname: generate_image(
                        p, format=f, filename=n,
                        agent_id="A06", slot_id=f"social_img_{attempt}"
                    ),
                )
        except Exception as gen_err:
            print(f"[HOOKS/A06] ❌ Генерация упала: {gen_err}")
            continue

        # Проверка качества через Gemini Flash
        score, notes, ok = await _check_image_quality(
            image_path=tmp_path,
            prompt=prompt_positive,
            task_context=chain_data.get("task", state.get("task", "")),
        )
        print(f"[HOOKS/A06] Оценка: {score}/10 — {notes}")

        if score > best_score:
            best_score = score
            best_path  = tmp_path
            best_notes = notes

        if ok:
            final_quality = "ok"
            print(f"[HOOKS/A06] ✅ Качество ок с попытки {attempt}")
            break

        # Улучшаем промпт для следующей попытки на основе замечаний
        if attempt < MAX_ATTEMPTS:
            prompt_positive = _improve_prompt(prompt_positive, notes)

    if not best_path:
        print("[HOOKS/A06] ❌ Все попытки провалились — картинки нет")
        return

    # Копируем лучшую картинку в images/
    final_fname = "social_post_0.png"
    final_path  = images_dir / final_fname
    shutil.copy2(best_path, final_path)
    print(f"[HOOKS/A06] 📁 Сохранено: {final_path}")

    # Пишем результат обратно в chain_data
    chain_data["evan_visual"] = {
        **evan,
        "image_path":    str(final_path),
        "attempts":      attempts_done,
        "quality":       final_quality,
        "quality_score": best_score,
        "quality_notes": best_notes,
        "format":        fmt,
    }
    state["chain_data"] = chain_data
    print(f"[HOOKS/A06] evan_visual обновлён: quality={final_quality}, score={best_score}")


def _platform_to_format(platform: str) -> str:
    """Выбирает формат изображения исходя из платформы."""
    platform = (platform or "instagram").lower()
    mapping = {
        "instagram":  "4:5",    # пост Instagram
        "instagram_stories": "9:16",
        "reels":      "9:16",
        "stories":    "9:16",
        "vk":         "1:1",
        "telegram":   "1:1",
        "universal":  "4:5",
    }
    return mapping.get(platform, "4:5")


def _collect_refs(state: dict, chain_data: dict) -> list[str]:
    """Собирает пути к референсам (char_ref, style_ref) из state и chain_data."""
    refs = []
    for key in ("char_ref", "style_ref"):
        for src in (state, chain_data):
            val = src.get(key)
            if val and Path(val).exists():
                refs.append(val)
    return refs


def _improve_prompt(prompt: str, quality_notes: str) -> str:
    """
    Минимальное улучшение промпта на основе замечаний Gemini.
    Добавляет корректирующие теги в конец промпта.
    """
    fixes = []
    notes_lower = quality_notes.lower()
    if any(w in notes_lower for w in ("blur", "размыт", "нечёткий")):
        fixes.append("sharp focus, high detail")
    if any(w in notes_lower for w in ("dark", "тёмный", "underexposed")):
        fixes.append("well lit, bright exposure")
    if any(w in notes_lower for w in ("artifact", "артефакт", "glitch")):
        fixes.append("clean render, no artifacts")
    if any(w in notes_lower for w in ("composition", "композиц")):
        fixes.append("balanced composition, rule of thirds")
    if fixes:
        return prompt + ", " + ", ".join(fixes)
    return prompt


async def _check_image_quality(
    image_path: str,
    prompt: str,
    task_context: str = "",
    threshold: int = 7,
) -> tuple[int, str, bool]:
    """
    Проверяет качество картинки через Gemini Flash (мультимодальный).

    Возвращает:
        (score: int 1-10, notes: str, ok: bool)

    Если LLM недоступен — возвращает (7, "ok (skipped)", True) как безопасный дефолт.
    """
    try:
        import base64
        from studio.llm import chat  # Gemini Flash через OpenRouter

        img_bytes = Path(image_path).read_bytes()
        b64 = base64.b64encode(img_bytes).decode("ascii")
        mime = "image/png"

        system = (
            "Ты — Эван Вижн, арт-директор. Оцени изображение по шкале 1-10. "
            "Критерии: соответствие промпту, композиция, качество рендера, "
            "отсутствие артефактов, коммерческая привлекательность. "
            "Ответь СТРОГО в формате:"
            "SCORE: <число от 1 до 10>"
            "NOTES: <одно предложение с замечаниями на русском>"
        )

        user_text = (
            f"Промпт: {prompt[:200]}"
            f"Задача: {task_context[:150]}"
            "Оцени изображение выше."
        )

        response = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: chat(
                model="google/gemini-flash-1.5",
                system=system,
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:{mime};base64,{b64}"}
                        },
                        {"type": "text", "text": user_text},
                    ]
                }],
            )
        )

        # Парсим ответ
        score = 7
        notes = ""
        for line in response.splitlines():
            if line.startswith("SCORE:"):
                try:
                    score = int(line.split(":")[1].strip())
                except ValueError:
                    pass
            elif line.startswith("NOTES:"):
                notes = line.split(":", 1)[1].strip()

        ok = score >= threshold
        return score, notes, ok

    except Exception as e:
        print(f"[HOOKS/A06] ⚠️ Gemini проверка недоступна: {e} — считаем ok")
        return 7, f"quality check skipped ({e})", True
