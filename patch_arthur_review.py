"""
patch_arthur_review.py
======================
Добавляет в studio/assembly/monteur.py функцию _arthur_review().

После того как final.mp4 собран — Артур его смотрит.

Два результата:
  assembly_assessment  — оценка своей работы, из данных сборки (без LLM)
                         влияет на DNA через sync_to_dna()
  arthur_notes         — взгляд как жителя города, через LLM с vision
                         пишется в хроники, не влияет на DNA

Запускать из корня проекта:
  python patch_arthur_review.py
"""

import re
from pathlib import Path

TARGET = Path("studio/assembly/monteur.py")

# ── Код который добавляем ─────────────────────────────────────────────────────

ARTHUR_REVIEW_CODE = '''

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

'''

# ── Патч: вставляем _arthur_review и вызываем его в assemble() ────────────────

def patch():
    if not TARGET.exists():
        print(f"❌ Файл не найден: {TARGET}")
        return

    src = TARGET.read_text(encoding="utf-8")

    # 1. Проверяем что патч не применён
    if "_arthur_review" in src:
        print("✅ Патч уже применён — пропускаю")
        return

    # 2. Добавляем код после последней функции (_db_to_factor)
    insert_after = "    return 10 ** (db / 20)"
    if insert_after not in src:
        print("❌ Якорь не найден — проверь версию monteur.py")
        return

    src = src.replace(insert_after, insert_after + ARTHUR_REVIEW_CODE)

    # 3. Вызываем _arthur_review() в assemble() после _write_manifest()
    # Находим строку после записи манифеста
    old_call = (
        "        result.status     = \"DONE\" if not result.errors else \"PARTIAL\"\n"
        "        result.final_path = str(final_path)"
    )
    new_call = (
        "        result.status     = \"DONE\" if not result.errors else \"PARTIAL\"\n"
        "        result.final_path = str(final_path)\n\n"
        "        # Этап 2 — Артур смотрит финал\n"
        "        _arthur_review(result, deliverables, slot_id)"
    )

    if old_call not in src:
        print("❌ Место вставки вызова не найдено — проверь monteur.py")
        return

    src = src.replace(old_call, new_call)

    # 4. Пишем результат
    TARGET.write_text(src, encoding="utf-8")
    print(f"✅ Патч применён → {TARGET}")
    print("   Добавлено:")
    print("   • _arthur_review() — два этапа после сборки")
    print("   • _sync_assembly_to_dna() — DNA от своей работы")
    print("   • _arthur_look() — LLM с vision, выбор модели")
    print("   • _choose_model() — сам выбирает Flash/Pro/Sonnet")
    print("   • _extract_frames() — кадры из final.mp4")
    print("   • _write_to_chronicles() — arthur_notes в хроники")


if __name__ == "__main__":
    patch()
