#!/usr/bin/env python3
"""
patch_music_decision.py
Студия «Шесть пальцев» | Спринт 40

Закрывает вопрос: "Что если музыки нет?"

Три изменения:
  1. Промт A01 Вайб Винни — добавляет раздел MUSIC_DECISION
  2. Промт A02 Ричи Ритм — добавляет режим APPROXIMATE
  3. hooks.py — хук on_after_agent A01 + обновление _call_monteur

Запуск:
  python patch_music_decision.py            # dry-run
  python patch_music_decision.py --apply
"""
import sys
import shutil
from pathlib import Path

DRY_RUN = "--apply" not in sys.argv

STUDIO_ROOT   = Path(__file__).parent / "studio"
CLIPMAKERS    = STUDIO_ROOT / "modules" / "clipmakers"
HOOKS_PATH    = CLIPMAKERS / "hooks.py"
A01_PROMPT    = CLIPMAKERS / "A01" / "forge" / "prompt.md"
A02_PROMPT    = CLIPMAKERS / "A02" / "forge" / "prompt.md"
BACKUP_SUFFIX = ".bak_sprint40_music"


def log(msg): print(f"  {msg}")
def log_action(label, detail=""):
    prefix = "○ DRY" if DRY_RUN else "▶ APP"
    print(f"[{prefix}] {label}")
    if detail:
        for line in detail.strip().splitlines():
            print(f"         {line}")

def backup(path):
    dst = path.with_suffix(path.suffix + BACKUP_SUFFIX)
    if not DRY_RUN:
        shutil.copy2(path, dst)
    log(f"бэкап → {dst.name}")


# ─── БЛОК ДЛЯ ДОБАВЛЕНИЯ В ПРОМТ A01 ────────────────────────────

A01_MUSIC_BLOCK = '''
---

# 🎵 MUSIC DECISION — ПЕРВОЕ ЧТО ДЕЛАЕШЬ

Смотришь в `master_brief.assets.audio_ref[]`.

## Если `audio_ref` НЕ ПУСТ → PATH: has_track

Файл трека передан. Работаешь в штатном режиме.
В `music_decision.path` пишешь `"has_track"`.

## Если `audio_ref` ПУСТ → выбери один из трёх путей:

### PATH A: needs_track — СТОП, нужен трек

**Когда:** `master_brief.music` слишком расплывчат для работы.
Нет BPM + нет структуры + нет ключевых моментов = нельзя строить sync-карту.

Пишешь в `music_decision`:
```json
{
  "path": "needs_track",
  "stop_reason": "Не могу построить sync-карту без BPM и структуры трека. Нужно: [список]",
  "what_is_needed": ["BPM или темп", "структура (intro→verse→chorus)", "ключевые моменты"]
}
```
**Цепочка останавливается.** Шеф докидывает трек или описание.

---

### PATH B: description_only — РАБОТАЮ ПО ОПИСАНИЮ

**Когда:** В брифе есть жанр + BPM + настроение + структура + key_moments.
Файла нет, но информации достаточно для концепта и примерной sync-карты.

Ричи (A02) будет работать в режиме APPROXIMATE — таймкоды примерные.
Монтажёр соберёт клип без аудиодорожки. Шеф подкладывает трек вручную потом.

Пишешь:
```json
{
  "path": "description_only",
  "music_warning": "Трек не загружен. Sync-карта будет примерной. Клип выйдет без музыки — подложишь трек вручную.",
  "music_brief": null
}
```

---

### PATH C: generate — ГЕНЕРИРУЮ ТРЕК ЧЕРЕЗ AI

**Когда:** В брифе явно указано `"generate_music": true` или Шеф написал "сгенерируй музыку".

Формируешь `music_brief` для ElevenLabs — это твоя работа как Creative Director:
- жанр (genre)
- BPM или темп (bpm)
- настроение (mood)
- длительность в секундах (duration_sec)
- инструменты (instruments) — 2-3 ключевых
- структура (structure) — в секундах: {"intro": 12, "verse": 24, ...}

Пишешь:
```json
{
  "path": "generate",
  "music_brief": {
    "genre": "dark trap",
    "bpm": 140,
    "mood": "aggressive, atmospheric",
    "duration_sec": 210,
    "instruments": ["808 bass", "hi-hats", "synth pad"],
    "structure": {"intro": 12, "verse_1": 24, "pre_chorus": 12, "chorus": 24}
  }
}
```
**Хук сгенерирует трек через ElevenLabs** и положит его в цепочку автоматически.

---

## В JSON output — ВСЕГДА добавляй поле `music_decision`

```json
"my_output": {
  "music_decision": {
    "path": "has_track | description_only | generate | needs_track",
    "music_warning": "текст или null",
    "music_brief": {...} или null,
    "stop_reason": "текст или null",
    "what_is_needed": [] или null
  },
  "track_analysis": {...},
  "concept": {...},
  ...
}
```

⚠️ Если `path == "needs_track"` — остальные поля (`track_analysis`, `concept`, `energy_map`) **не заполняешь**. Возвращаешь только `music_decision`.
'''

# ─── БЛОК ДЛЯ ДОБАВЛЕНИЯ В ПРОМТ A02 ────────────────────────────

A02_MUSIC_BLOCK = '''
---

# 🎵 РЕЖИМ РАБОТЫ БЕЗ ТРЕКА (APPROXIMATE)

Смотришь в `vinnie_concept.music_decision.path`.

## Если path == "has_track" или "generate"

Трек есть (реальный или сгенерированный). Работаешь в штатном режиме.
Таймкоды точные. Sync-точки реальные.

## Если path == "description_only"

Трека нет — работаешь в режиме **APPROXIMATE**.

**Что меняется:**
- Таймкоды — расчётные, на основе BPM и структуры из брифа
- Sync-точки — рекомендательные, не привязаны к реальному файлу
- Каждый элемент `timecode_map` добавляешь поле `"approximate": true`
- В начале вывода пишешь предупреждение: "⚡ APPROXIMATE MODE: трека нет, таймкоды расчётные"

**Что НЕ меняется:**
- Структура JSON остаётся той же
- Энергия и монтажная логика — по описанию из брифа
- lipsync_map — если вокал описан в брифе

## Если path == "needs_track"

Винни уже остановил цепочку. Ты не должен был запуститься.
Если запустился — напиши "Трек не определён, sync-карту построить невозможно" и верни пустой my_output.
'''

# ─── БЛОК ДЛЯ ДОБАВЛЕНИЯ В hooks.py ─────────────────────────────

HOOKS_MUSIC_ADDITION = '''

# ═══════════════════════════════════════════════════════════════════
# MUSIC DECISION — обработка решения Винни о музыке
# Вызывается из on_after_agent после A01
# ═══════════════════════════════════════════════════════════════════

def _handle_music_decision(state: dict, human_text: str):
    """
    Читает music_decision из ответа A01 Вайб Винни.

    has_track:         ничего не делаем — трек уже в master_brief.assets.audio_ref
    description_only:  пишем предупреждение в state, флоу идёт дальше
    generate:          генерируем трек через ElevenLabs, кладём в state
    needs_track:       бросаем StopIteration — Шеф должен добавить трек
    """
    data = _parse_json(human_text)
    if not data:
        return

    my_output = data.get("my_output", {})
    music_dec = my_output.get("music_decision", {})
    path = music_dec.get("path", "has_track")

    if path == "has_track":
        print("[CLIPMAKERS A01] 🎵 Трек есть — флоу штатный")
        return

    elif path == "needs_track":
        stop_reason = music_dec.get("stop_reason", "Нужен трек")
        what_needed = music_dec.get("what_is_needed", [])
        msg = (
            f"[clipmakers] СТОП: Вайб Винни не может начать без трека.\\n"
            f"Причина: {stop_reason}\\n"
            f"Нужно: {', '.join(what_needed) if what_needed else 'см. выше'}"
        )
        print(msg)
        raise StopIteration(msg)

    elif path == "description_only":
        warning = music_dec.get("music_warning", "Трек не загружен — sync-карта примерная")
        state["music_warning"] = warning
        state["music_mode"]    = "description_only"
        print(f"[CLIPMAKERS A01] ⚡ APPROXIMATE MODE: {warning}")

    elif path == "generate":
        music_brief = music_dec.get("music_brief")
        if not music_brief:
            print("[CLIPMAKERS A01] ⚠ generate: music_brief пуст — пропускаю генерацию")
            state["music_mode"] = "description_only"
            return

        print(f"[CLIPMAKERS A01] 🎵 Генерирую трек: {music_brief.get('genre')} "
              f"{music_brief.get('bpm')} BPM {music_brief.get('duration_sec')}с...")
        try:
            from studio.elevenlabs_client import generate_music
            slot_id = state.get("_slot_id", "clipmakers")
            duration = float(music_brief.get("duration_sec", 180))

            prompt_parts = [
                music_brief.get("genre", ""),
                music_brief.get("mood", ""),
                f"{music_brief.get('bpm', '')} BPM",
                ", ".join(music_brief.get("instruments", [])),
            ]
            music_prompt = ", ".join(p for p in prompt_parts if p)

            filename = f"generated_track_{_slugify(music_brief.get('genre','track'))}.mp3"
            raw_path = generate_music(
                prompt=music_prompt,
                duration_sec=duration,
                filename=filename,
                agent_id="A01",
                slot_id=slot_id,
            )

            output_dir = Path("output/generated") / state.get("project_id", "clip_unknown")
            output_dir.mkdir(parents=True, exist_ok=True)
            dest = output_dir / filename
            Path(raw_path).replace(dest)

            state["generated_music_path"] = str(dest)
            state["music_mode"]           = "generated"
            print(f"[CLIPMAKERS A01] ✅ Трек сгенерирован: {dest.name}")

        except Exception as e:
            print(f"[CLIPMAKERS A01] ❌ ElevenLabs: {e} — переход в description_only")
            state["music_mode"]    = "description_only"
            state["music_warning"] = f"Генерация трека упала ({e}). Sync-карта будет примерной."
'''

# ─── ПАТЧ ПРОМТА A01 ─────────────────────────────────────────────

def patch_a01_prompt():
    print("\\n[1/3] A01/forge/prompt.md — добавляем MUSIC_DECISION")

    if not A01_PROMPT.exists():
        log(f"❌ файл не найден: {A01_PROMPT}")
        return

    content = A01_PROMPT.read_text(encoding="utf-8")

    if "MUSIC_DECISION" in content:
        log("✓ MUSIC_DECISION уже есть — пропускаю")
        return

    # Вставляем перед ⚠️ RULES
    insert_before = "⚠️ RULES"
    if insert_before not in content:
        insert_before = "Проверь себя через"

    log_action(
        "Добавить раздел MUSIC_DECISION в A01",
        "has_track / description_only / generate / needs_track"
    )

    if not DRY_RUN:
        backup(A01_PROMPT)
        idx = content.index(insert_before)
        new_content = content[:idx] + A01_MUSIC_BLOCK + "\\n" + content[idx:]
        A01_PROMPT.write_text(new_content, encoding="utf-8")
        log("✅ A01 промт обновлён")
    else:
        log("○ dry-run: не записан")


# ─── ПАТЧ ПРОМТА A02 ─────────────────────────────────────────────

def patch_a02_prompt():
    print("\\n[2/3] A02/forge/prompt.md — добавляем APPROXIMATE режим")

    if not A02_PROMPT.exists():
        log(f"❌ файл не найден: {A02_PROMPT}")
        return

    content = A02_PROMPT.read_text(encoding="utf-8")

    if "APPROXIMATE" in content:
        log("✓ APPROXIMATE уже есть — пропускаю")
        return

    insert_before = "⚠️ RULES"
    if insert_before not in content:
        insert_before = "Проверь себя через"

    log_action("Добавить раздел APPROXIMATE в A02")

    if not DRY_RUN:
        backup(A02_PROMPT)
        idx = content.index(insert_before)
        new_content = content[:idx] + A02_MUSIC_BLOCK + "\\n" + content[idx:]
        A02_PROMPT.write_text(new_content, encoding="utf-8")
        log("✅ A02 промт обновлён")
    else:
        log("○ dry-run: не записан")


# ─── ПАТЧ hooks.py ────────────────────────────────────────────────

def patch_hooks():
    print("\\n[3/3] hooks.py — _handle_music_decision + on_after_agent A01 + _call_monteur")

    if not HOOKS_PATH.exists():
        log(f"❌ hooks.py не найден: {HOOKS_PATH}")
        log("   Сначала примени patch_clipmakers_launch.py --apply")
        return

    content = HOOKS_PATH.read_text(encoding="utf-8")

    if "_handle_music_decision" in content:
        log("✓ _handle_music_decision уже есть — пропускаю добавление функции")
    else:
        log_action("Добавить _handle_music_decision в конец hooks.py")
        if not DRY_RUN:
            backup(HOOKS_PATH)
            content = content + HOOKS_MUSIC_ADDITION
            HOOKS_PATH.write_text(content, encoding="utf-8")
            log("✅ функция добавлена")
            # Перечитываем для следующих правок
            content = HOOKS_PATH.read_text(encoding="utf-8")

    # Добавляем вызов в on_after_agent после A01
    if "_handle_music_decision(state, human_text)" not in content:
        old = '    if worker_id == "A06":\n        _gus_generate_frames(state, human_text)'
        new = (
            '    if worker_id == "A01":\n'
            '        _handle_music_decision(state, human_text)\n\n'
            '    elif worker_id == "A06":\n'
            '        _gus_generate_frames(state, human_text)'
        )
        if old in content:
            log_action("Добавить вызов _handle_music_decision в on_after_agent A01")
            if not DRY_RUN:
                content = content.replace(old, new, 1)
                HOOKS_PATH.write_text(content, encoding="utf-8")
                log("✅ вызов добавлен в on_after_agent")
        else:
            log("⚠ не нашёл точку вставки в on_after_agent — проверь вручную")

    # Добавляем проверку generated_music_path в _call_monteur
    if "generated_music_path" not in content:
        old = (
            '    if audio_refs:\n'
            '            audio_path = audio_refs[0] if isinstance(audio_refs[0], str) else ""\n'
            '            if audio_path and Path(audio_path).exists():\n'
            '                audio_layer = {"music": {"audio_path": audio_path, "ducking_db": -6}}\n'
            '                print(f"[CLIPMAKERS A12] 🎵 Трек артиста: {Path(audio_path).name}")\n'
            '            else:\n'
            '                print(f"[CLIPMAKERS A12] ℹ️  audio_ref задан но файл не найден: {audio_refs[0]}")\n'
            '        else:\n'
            '            print("[CLIPMAKERS A12] ℹ️  audio_ref пуст — клип без музыки")'
        )
        new = (
            '    if audio_refs:\n'
            '            audio_path = audio_refs[0] if isinstance(audio_refs[0], str) else ""\n'
            '            if audio_path and Path(audio_path).exists():\n'
            '                audio_layer = {"music": {"audio_path": audio_path, "ducking_db": -6}}\n'
            '                print(f"[CLIPMAKERS A12] 🎵 Трек артиста: {Path(audio_path).name}")\n'
            '            else:\n'
            '                print(f"[CLIPMAKERS A12] ℹ️  audio_ref задан но файл не найден: {audio_refs[0]}")\n'
            '        else:\n'
            '            # Проверяем сгенерированный трек (PATH C: generate)\n'
            '            gen_path = state.get("generated_music_path", "")\n'
            '            if gen_path and Path(gen_path).exists():\n'
            '                audio_layer = {"music": {"audio_path": gen_path, "ducking_db": -6}}\n'
            '                print(f"[CLIPMAKERS A12] 🎵 AI-трек: {Path(gen_path).name}")\n'
            '            else:\n'
            '                print("[CLIPMAKERS A12] ℹ️  audio_ref пуст — клип без музыки")\n'
            '                if state.get("music_warning"):\n'
            '                    print(f"[CLIPMAKERS A12] ⚡ {state[\'music_warning\']}")'
        )
        if old in content:
            log_action("Добавить проверку generated_music_path в _call_monteur")
            if not DRY_RUN:
                content = content.replace(old, new, 1)
                HOOKS_PATH.write_text(content, encoding="utf-8")
                log("✅ _call_monteur обновлён")
        else:
            log("⚠ не нашёл точку вставки в _call_monteur — проверь вручную")


# ─── Финальная проверка ───────────────────────────────────────────

def final_check():
    print("\\n[Проверка]")
    checks = {
        "A01 MUSIC_DECISION":   (A01_PROMPT, "MUSIC_DECISION"),
        "A02 APPROXIMATE":      (A02_PROMPT, "APPROXIMATE"),
        "hooks _handle_music":  (HOOKS_PATH, "_handle_music_decision"),
        "hooks A01 call":       (HOOKS_PATH, "_handle_music_decision(state"),
        "hooks generated_path": (HOOKS_PATH, "generated_music_path"),
        "hooks needs_track":    (HOOKS_PATH, "needs_track"),
        "hooks StopIteration":  (HOOKS_PATH, "StopIteration"),
    }
    for label, (path, needle) in checks.items():
        if path.exists():
            found = needle in path.read_text(encoding="utf-8")
        else:
            found = False
        print(f"  {'✅' if found else '❌'} {label}")


# ─── main ─────────────────────────────────────────────────────────

def main():
    mode = "DRY-RUN" if DRY_RUN else "APPLY"
    print(f"\\n{'='*60}")
    print(f"  patch_music_decision.py  [{mode}]")
    print(f"{'='*60}")

    patch_a01_prompt()
    patch_a02_prompt()
    patch_hooks()
    final_check()

    print(f"\\n{'='*60}")
    if DRY_RUN:
        print("  Dry-run. Применить: python patch_music_decision.py --apply")
    else:
        print("  ✅ Патч применён.")
        print("  Теперь Вайб Винни решает судьбу трека в начале каждого рана.")
    print(f"{'='*60}\\n")


if __name__ == "__main__":
    main()
