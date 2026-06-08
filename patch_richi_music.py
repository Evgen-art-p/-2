#!/usr/bin/env python3
"""
patch_richi_music.py
Студия «Шесть пальцев» | Спринт 40

Ричи Ритм (A02) — ответственный за музыку:
  1. Промт A02: если трека нет → формирует music_generation brief
  2. hooks.py: on_after_agent A02 → ElevenLabs → анализ mp3 → обогащает chain_data

Применять ПОСЛЕ patch_clipmakers_launch.py --apply

Запуск:
  python patch_richi_music.py            # dry-run
  python patch_richi_music.py --apply
"""
import sys, shutil, re, json
from pathlib import Path

DRY_RUN       = "--apply" not in sys.argv
STUDIO_ROOT   = Path(__file__).parent / "studio"
CLIPMAKERS    = STUDIO_ROOT / "modules" / "clipmakers"
HOOKS_PATH    = CLIPMAKERS / "hooks.py"
A02_PROMPT    = CLIPMAKERS / "A02" / "forge" / "prompt.md"
BACKUP_SUFFIX = ".bak_sprint40_richi"

def log(msg):      print(f"  {msg}")
def log_action(l): print(f"  [{'DRY' if DRY_RUN else 'APP'}] {l}")
def backup(p):
    dst = p.with_suffix(p.suffix + BACKUP_SUFFIX)
    if not DRY_RUN: shutil.copy2(p, dst)
    log(f"бэкап → {dst.name}")


# ─── БЛОК ДЛЯ ПРОМТА A02 ─────────────────────────────────

A02_MUSIC_BLOCK = '''
---

# 🎵 ЕСЛИ ТРЕКА НЕТ — ТЫ РЕШАЕШЬ

Смотришь в `master_brief.assets.audio_ref`.

**Если `audio_ref` не пуст** → работаешь штатно по треку.

**Если `audio_ref` пуст** → ты единственный в цехе кто понимает музыку технически.
Твоя задача: сформировать точное ТЗ на трек.

Смотришь в `master_brief.music`:
- Есть жанр, BPM, настроение? → строишь ТЗ из них
- Данных нет? → выводишь BPM и структуру из `master_brief.music.genre` + `mood`
  (поп ~120 BPM, трэп ~140, R&B ~90, рок ~130, электро ~128)

Заполняешь `music_generation` в `my_output`:

```json
"music_generation": {
  "needed": true,
  "genre": "dark trap",
  "bpm": 140,
  "mood": "aggressive, atmospheric, cinematic",
  "duration_sec": 210,
  "instruments": ["808 bass", "hi-hats", "atmospheric synth pad"],
  "structure": {
    "intro_sec": 12,
    "verse_sec": 24,
    "pre_chorus_sec": 12,
    "chorus_sec": 24,
    "bridge_sec": 16,
    "outro_sec": 12
  },
  "elevenlabs_prompt": "dark trap instrumental, 140 BPM, heavy 808 bass, atmospheric synth pads, hi-hat rolls, cinematic and aggressive mood, no vocals, music video background"
}
```

**`elevenlabs_prompt`** — это твоя работа. Ты знаешь как описать музыку технически.
Один развёрнутый prompt на английском: жанр + BPM + инструменты + настроение + "no vocals".

После того как трек сгенерирован — система вернёт тебе анализ:
`track_analysis_result` в контексте:
```json
{
  "audio_path": "output/generated/...",
  "duration_sec": 213.4,
  "bpm_detected": 141.2,
  "sections": [
    {"start": 0, "end": 12.1, "label": "intro"},
    {"start": 12.1, "end": 36.3, "label": "verse_1"},
    ...
  ]
}
```

Используй эти данные для точного timecode_map.
Если анализ не пришёл — строй timecode_map по своему `music_generation.structure`.

**Если `needed: false`** — поле `music_generation` можно не писать или `{"needed": false}`.
'''

A02_RULE_OLD  = "Не придумывай BPM — если не дан, напиши \"определить на площадке\""
A02_RULE_NEW  = "Если BPM не дан — выведи его из жанра и mood сам. Площадки нет — у нас AI-генерация"


# ─── ХУКОВАЯ ФУНКЦИЯ _richi_generate_music ───────────────

HOOKS_RICHI_ADDITION = r'''

# ═══════════════════════════════════════════════════════════════════
# A02 РИЧИ РИТМ — генерация трека и анализ
# Вызывается из on_after_agent после A02
# ═══════════════════════════════════════════════════════════════════

def _richi_generate_music(state: dict, human_text: str) -> str | None:
    """
    Читает music_generation из ответа Ричи.
    Если needed: true → генерирует трек через ElevenLabs.
    Анализирует mp3 через ffprobe (BPM, длительность, секции).
    Возвращает путь к mp3 или None.
    Результат пишет в state и chain_data для следующих агентов.
    """
    data = _parse_json(human_text)
    if not data:
        return None

    my_output   = data.get("my_output", {})
    music_gen   = my_output.get("music_generation", {})
    if not music_gen or not music_gen.get("needed"):
        print("[CLIPMAKERS A02] 🎵 Трек предоставлен — генерация не нужна")
        return None

    slot_id    = state.get("_slot_id", "clipmakers")
    project_id = state.get("project_id", "clip_unknown")
    output_dir = Path("output/generated") / project_id
    output_dir.mkdir(parents=True, exist_ok=True)

    genre    = music_gen.get("genre", "cinematic")
    bpm      = music_gen.get("bpm", 120)
    duration = float(music_gen.get("duration_sec", 180))
    prompt   = music_gen.get(
        "elevenlabs_prompt",
        f"{genre} instrumental, {bpm} BPM, cinematic, no vocals"
    )

    print(f"[CLIPMAKERS A02] 🎵 Генерирую трек: {genre} {bpm}BPM {duration}с...")
    print(f"[CLIPMAKERS A02]   Промпт: {prompt[:80]}...")

    # ── Генерация через ElevenLabs ────────────────────────
    filename = f"track_{_slugify(genre)}_{bpm}bpm.mp3"
    dest     = output_dir / filename
    try:
        from studio.elevenlabs_client import generate_music as _el_music
        raw_path = _el_music(
            prompt=prompt,
            duration_sec=duration,
            filename=filename,
            agent_id="A02",
            slot_id=slot_id,
        )
        Path(raw_path).replace(dest)
        print(f"[CLIPMAKERS A02] ✅ Трек готов: {dest.name} ({duration}с)")
    except Exception as e:
        print(f"[CLIPMAKERS A02] ❌ ElevenLabs: {e}")
        return None

    # ── Анализ mp3 через ffprobe ──────────────────────────
    track_analysis = _analyze_track(str(dest), music_gen)

    # ── Пишем в state и chain_data ────────────────────────
    # audio_ref: теперь трек есть
    chain = state.get("chain_data", {})
    mb    = chain.get("master_brief", state.get("master_brief", {}))
    if isinstance(mb, dict):
        mb.setdefault("assets", {})["audio_ref"] = [str(dest)]
        chain["master_brief"] = mb

    # track_analysis_result — Ричи "слышит" что получилось
    chain["track_analysis_result"] = track_analysis
    state["chain_data"]            = chain
    state["generated_track_path"]  = str(dest)

    print(f"[CLIPMAKERS A02] 🎧 Анализ: {track_analysis.get('duration_sec')}с "
          f"BPM≈{track_analysis.get('bpm_detected')} "
          f"секций: {len(track_analysis.get('sections', []))}")

    return str(dest)


def _analyze_track(audio_path: str, music_gen: dict) -> dict:
    """
    Анализирует mp3 через ffprobe.
    Возвращает duration_sec, bpm_detected, sections[].
    Если ffprobe недоступен — возвращает данные из music_gen.structure.
    """
    import subprocess, json as _j

    result = {
        "audio_path":    audio_path,
        "duration_sec":  music_gen.get("duration_sec", 180),
        "bpm_detected":  music_gen.get("bpm", 120),
        "sections":      [],
    }

    # Длительность через ffprobe
    try:
        probe = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json",
             "-show_format", audio_path],
            capture_output=True, text=True, timeout=15,
        )
        fmt_data = _j.loads(probe.stdout).get("format", {})
        result["duration_sec"] = float(fmt_data.get("duration", result["duration_sec"]))
    except Exception as e:
        print(f"[A02 ANALYZE] ffprobe duration: {e}")

    # Секции из structure (approximation без librosa)
    structure = music_gen.get("structure", {})
    if structure:
        t = 0.0
        for part, dur in structure.items():
            part_name = part.replace("_sec", "").replace("_", " ")
            result["sections"].append({
                "start": round(t, 1),
                "end":   round(t + float(dur), 1),
                "label": part_name,
            })
            t += float(dur)

    # Пробуем librosa для реального BPM (необязательно)
    try:
        import librosa
        y, sr = librosa.load(audio_path, sr=None, duration=60)
        tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
        result["bpm_detected"] = round(float(tempo), 1)
        print(f"[A02 ANALYZE] librosa BPM: {result['bpm_detected']}")
    except Exception:
        pass  # librosa не установлена — используем bpm из music_gen

    return result
'''


# ─── ПАТЧ ПРОМТА A02 ─────────────────────────────────────

def patch_a02_prompt():
    print("\n[1/2] A02/forge/prompt.md — добавляем логику генерации трека")
    if not A02_PROMPT.exists():
        log(f"❌ не найден: {A02_PROMPT}"); return

    content = A02_PROMPT.read_text(encoding="utf-8")

    if "music_generation" in content:
        log("✓ music_generation уже есть — пропускаю"); return

    log_action("Добавить раздел ЕСЛИ ТРЕКА НЕТ + elevenlabs_prompt")

    if not DRY_RUN:
        backup(A02_PROMPT)
        # Исправляем устаревшее правило
        new_content = content.replace(A02_RULE_OLD, A02_RULE_NEW)
        # Вставляем перед ⚠️ RULES
        marker = "⚠️ RULES"
        if marker in new_content:
            idx = new_content.index(marker)
            new_content = new_content[:idx] + A02_MUSIC_BLOCK + "\n" + new_content[idx:]
        else:
            new_content += "\n" + A02_MUSIC_BLOCK
        A02_PROMPT.write_text(new_content, encoding="utf-8")
        log("✅ A02 промт обновлён")
    else:
        log("○ dry-run: не записан")


# ─── ПАТЧ hooks.py ────────────────────────────────────────

def patch_hooks():
    print("\n[2/2] hooks.py — _richi_generate_music + вызов в on_after_agent")
    if not HOOKS_PATH.exists():
        log(f"❌ hooks.py не найден — сначала patch_clipmakers_launch.py --apply")
        return

    content = HOOKS_PATH.read_text(encoding="utf-8")

    # 1. Добавляем функцию
    if "_richi_generate_music" not in content:
        log_action("Добавить _richi_generate_music + _analyze_track в конец hooks.py")
        if not DRY_RUN:
            backup(HOOKS_PATH)
            content = content + HOOKS_RICHI_ADDITION
            HOOKS_PATH.write_text(content, encoding="utf-8")
            content = HOOKS_PATH.read_text(encoding="utf-8")
            log("✅ функции добавлены")

    # 2. Добавляем вызов в on_after_agent после A01 блока
    if "_richi_generate_music(state, human_text)" not in content:
        # Ищем блок elif worker_id == "A06"
        old = '    elif worker_id == "A06":\n        _gus_generate_frames(state, human_text)'
        new = (
            '    elif worker_id == "A02":\n'
            '        _richi_generate_music(state, human_text)\n\n'
            '    elif worker_id == "A06":\n'
            '        _gus_generate_frames(state, human_text)'
        )
        if old in content:
            log_action("Добавить вызов _richi_generate_music в on_after_agent A02")
            if not DRY_RUN:
                content = content.replace(old, new, 1)
                HOOKS_PATH.write_text(content, encoding="utf-8")
                content = HOOKS_PATH.read_text(encoding="utf-8")
                log("✅ вызов добавлен")
        else:
            log("⚠ не нашёл точку вставки в on_after_agent — добавь вручную после блока A01")

    # 3. _call_monteur: добавить проверку generated_track_path
    if "generated_track_path" not in content:
        old = (
            '            else:\n'
            '                print("[CLIPMAKERS A12] ℹ️  audio_ref пуст — клип без музыки")\n'
            '                if state.get("music_warning"):\n'
            '                    print(f"[CLIPMAKERS A12] ⚡ {state[\'music_warning\']}")'
        )
        new = (
            '            else:\n'
            '                # Ричи мог сгенерировать трек в on_after_agent A02\n'
            '                gen_path = state.get("generated_track_path", "")\n'
            '                if gen_path and Path(gen_path).exists():\n'
            '                    audio_layer = {"music": {"audio_path": gen_path, "ducking_db": -6}}\n'
            '                    print(f"[CLIPMAKERS A12] 🎵 AI-трек от Ричи: {Path(gen_path).name}")\n'
            '                else:\n'
            '                    print("[CLIPMAKERS A12] ℹ️  audio_ref пуст — клип без музыки")'
        )
        if old in content:
            log_action("Добавить проверку generated_track_path в _call_monteur")
            if not DRY_RUN:
                content = content.replace(old, new, 1)
                HOOKS_PATH.write_text(content, encoding="utf-8")
                log("✅ _call_monteur обновлён")
        else:
            log("⚠ не нашёл точку вставки в _call_monteur — проверь вручную")


# ─── Финальная проверка ───────────────────────────────────

def final_check():
    print("\n[Проверка]")
    checks = {
        "A02: music_generation":         (A02_PROMPT,  "music_generation"),
        "A02: elevenlabs_prompt":        (A02_PROMPT,  "elevenlabs_prompt"),
        "A02: rule исправлено":          (A02_PROMPT,  "Площадки нет — у нас AI"),
        "hooks: _richi_generate_music":  (HOOKS_PATH,  "_richi_generate_music"),
        "hooks: _analyze_track":         (HOOKS_PATH,  "_analyze_track"),
        "hooks: A02 вызов":              (HOOKS_PATH,  '_richi_generate_music(state'),
        "hooks: generated_track_path":   (HOOKS_PATH,  "generated_track_path"),
    }
    for label, (path, needle) in checks.items():
        found = path.exists() and needle in path.read_text(encoding="utf-8")
        print(f"  {'✅' if found else '❌'} {label}")


def main():
    mode = "DRY-RUN" if DRY_RUN else "APPLY"
    print(f"\n{'='*60}")
    print(f"  patch_richi_music.py  [{mode}]")
    print(f"{'='*60}")
    patch_a02_prompt()
    patch_hooks()
    final_check()
    print(f"\n{'='*60}")
    if DRY_RUN:
        print("  Dry-run. Применить: python patch_richi_music.py --apply")
    else:
        print("  ✅ Ричи Ритм теперь решает вопрос с музыкой.")
        print("  Нет трека → формирует ТЗ → хук генерирует → анализирует → chain_data обновлён.")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    main()
