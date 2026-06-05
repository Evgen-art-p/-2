"""
patch_video_shorts_contract.py
Студия «Шесть Пальцев» · Спринт 40

ЧТО ДЕЛАЕТ:
  1. Перезаписывает studio/modules/video_shorts/CHAIN_CONTRACT.md
     — добавляет в vera_visual.frames[]: negative_prompt, self_assessment
     — добавляет в stan_video.video_clips[]: video_path, clip_assessment
     — добавляет в julia_sound_code/julia_sound: music, sfx_list, vo_lines
     — обновляет версию до v3.0
  2. Обновляет studio/modules/video_shorts/manifest.json
     — version: "2.0" → "3.0"

ЗАПУСК из корня проекта:
  python patch_video_shorts_contract.py
"""

import sys
import json
import shutil
from pathlib import Path
from datetime import datetime

CONTRACT_PATH = Path("studio/modules/video_shorts/CHAIN_CONTRACT.md")
MANIFEST_PATH = Path("studio/modules/video_shorts/manifest.json")


def check():
    ok = True
    for p in [CONTRACT_PATH, MANIFEST_PATH]:
        if not p.exists():
            print(f"❌  Не найден: {p}")
            ok = False
        else:
            print(f"✅  Найден: {p}")
    if not ok:
        sys.exit(1)


def backup(path: Path) -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = path.with_suffix(path.suffix + f".bak_{stamp}")
    shutil.copy2(path, dest)
    print(f"📦  Бэкап: {dest}")
    return dest


# ─── Новый CHAIN_CONTRACT.md ─────────────────────────────────────────────────

NEW_CONTRACT = """# КОНТРАКТ КЛЮЧЕЙ — VIDEO_SHORTS v3.0
## studio/modules/video_shorts/CHAIN_CONTRACT.md
##
## Это ЕДИНСТВЕННЫЙ источник правды по ключам chain_data.
## Если агент пишет ключ не из этого списка — ошибка.
## Если агент читает ключ не из этого списка — ошибка.
##
## Редактировать только вместе с SHORTS_RULES.md раздел 10.
## Не копировать в другие цеха.
##
## v3.0 (Спринт 40):
##   vera_visual.frames[]: +negative_prompt, +self_assessment
##   stan_video.video_clips[]: +video_path, +clip_assessment
##   julia_sound_code/julia_sound: +music, +sfx_list, +vo_lines
##   harry_episode.micro_script[]: +dialogue
##   hooks.py: генерация реальная — fal.ai (A07), Wan2.2 (A08), ElevenLabs+CosyVoice (A03)

---

## СВОДНАЯ ТАБЛИЦА

| Агент | Пишет (PILOT) | Пишет (EPISODE) | Читает |
|-------|--------------|-----------------|--------|
| A01 Трикси | `trixie_trend` | `trixie_episode` | `master_brief`, `history_dna` |
| A02 Гарри | `harry_pilot` | `harry_episode` | `trixie_trend/episode`, `history_dna` |
| A03 Джулия | `julia_sound_code` | `julia_sound` | `harry_pilot/episode`, `trixie_trend/episode`, `history_dna` |
| A04 Тэг Тони | `tony_seo`, `tony_verdict` | `tony_seo`, `tony_verdict` | `harry_pilot/episode`, `julia_sound_code/sound`, `trixie_trend/episode` |
| Виктор | `victor_critique` | `victor_critique` | всё до A04 |
| A05 Рик | — | `rick_light` | `harry_episode`, `tony_seo`, `history_dna` |
| A06 Пенни | — | `penny_props` | `harry_episode`, `rick_light`, `history_dna` |
| A07 Вера | — | `vera_visual` | `rick_light`, `penny_props`, `harry_episode`, `history_dna` |
| A08 Стэн | — | `stan_video` | `vera_visual`, `rick_light`, `harry_episode` |
| A09 Ларри | — | `larry_edit` | `stan_video`, `vera_visual`, `harry_episode`, `julia_sound` |
| A10 Луиджи | — | `luigi_loop` | `larry_edit`, `harry_episode`, `julia_sound`, `history_dna` |
| A11 Сабби | — | `subbie_captions` | `harry_episode`, `larry_edit`, `tony_seo`, `vera_visual` |
| A12 Тамб Том | — | `tom_thumbnail`, `final_dna` | ВСЁ |

**Сквозные ключи** (наследуют все агенты через `{{inherit}}`):
- `master_brief`
- `history_dna`
- `mode`

---

## СТРУКТУРЫ КЛЮЧЕЙ

### `trixie_trend` / `trixie_episode`
```json
{
  "series_concept": { "title", "niche", "viral_angle", "target_audience", "pain_point", "hook_strategy" },
  "character_concept": { "name", "archetype", "trait", "visual_note" },
  "visual_language": { "style", "color_mood", "lighting" },
  "sound_code": { "theme", "emotional_peaks", "no_go" },
  "episode_brief": "строка",
  "client_read": "строка (только EPISODE)"
}
```

### `harry_pilot` / `harry_episode`
```json
{
  "hook": { "text", "type", "why_it_works" },
  "micro_script": [{
    "segment",
    "action",
    "emotion",
    "visual_hint",
    "dialogue",        ← v3.0: текст реплики или null. Джулия берёт для VO
    "duration_sec"
  }],
  "series_map": { "series_id", "total_episodes", "current_episode", "arc", "cliffhanger" },
  "character_memory": { "protagonist": { "name", "fear", "trait", "visual_note" } },
  "narrative_entry": { "episode", "summary", "cliffhanger", "key_shot" }
}
```

### `julia_sound_code` / `julia_sound`
```json
{
  "sound_code": { "theme", "bpm_range", "emotional_peaks", "no_go", "jingle" },

  "music": {                          ← v3.0: реальная генерация через ElevenLabs
    "prompt":      "English. One line. Genre + tempo + instruments + mood.",
    "duration_sec": 60,
    "mood":        "одно слово",
    "ducking_db":  -12,
    "audio_path":  "путь к mp3 — добавляет hooks.py после генерации"
  },

  "sfx_list": [{                      ← v3.0: SFX пачкой через ElevenLabs
    "segment":      "0-1.5s",
    "sfx_prompt":   "English 3-8 words, specific sound",
    "duration_sec": 1.5,
    "timing_sec":   0.0,
    "purpose":      "хук / акцент / атмосфера",
    "sfx_path":     "путь к mp3 — добавляет hooks.py"
  }],

  "vo_lines": [{                      ← v3.0: VO через CosyVoice
    "segment":      "0-1.5s",
    "text":         "текст из harry_episode.micro_script[].dialogue",
    "timing_sec":   0.0,
    "voice_style":  "warm | energetic | whisper | authoritative",
    "vo_path":      "путь к mp3 — добавляет hooks.py"
  }],

  "sound_notes": "строка",

  "music.audio_assessment": {         ← v3.0: Джулия слушает и оценивает
    "verdict":           "APPROVED | REJECTED",
    "score":             0.0,
    "timeline":          "посекундные замечания",
    "note":              "главный вывод",
    "corrected_prompt":  "если REJECTED — улучшенный промпт EN"
  }
}
```

### `tony_seo` + `tony_verdict`
```json
{
  "platform_strategy": { "platform", "format", "optimal_duration_sec", "posting_time", "posting_frequency" },
  "seo": { "title", "description", "hashtags", "keywords" },
  "safety_check": { "passed", "issues" }
}
"tony_verdict": "APPROVED | APPROVED_WITH_EDITS | REJECTED"
```

### `rick_light`
```json
{
  "light_specs": [{ "segment", "light_type", "color_temp", "direction", "mood", "prompt_en" }],
  "global_light_note": "строка"
}
```

### `penny_props`
```json
{
  "props_specs": [{ "segment", "location", "props", "costume", "background", "prompt_en" }],
  "global_props_note": "строка"
}
```

### `vera_visual` ⚠️ hooks.py добавляет `path` и `self_assessment` после генерации
```json
{
  "format": "9:16",
  "platform": "строка",
  "frames": [{
    "frame_id":        "frame_01",
    "segment":         "0-1.5s",
    "banana_prompt":   "English. Vertical 9:16. Nano Banana 2.",
    "negative_prompt": "extra fingers, 6 fingers, ...",  ← v3.0: обязателен
    "ref_ids":         ["asset_id из history_dna.character_memory"],
    "composition":     "rule_of_thirds | center | edge",
    "focus_point":     "строка",
    "safe_zone_check": true,
    "timing":          "0-1.5s",
    "path":            "путь к PNG — добавляет hooks.py после fal.ai",

    "self_assessment": {               ← v3.0: Вера смотрит на PNG сама
      "verdict":          "APPROVED | REJECTED",
      "score":            0.0,
      "note":             "строка",
      "corrected_prompt": "если REJECTED — новый промпт EN"
    }
  }],
  "color_palette":  ["#hex1", "#hex2", "#hex3"],
  "visual_notes":   "строка"
}
```

### `stan_video` ⚠️ hooks.py добавляет `video_path` и `clip_assessment` после генерации
```json
{
  "video_clips": [{
    "frame_id":     "frame_01",
    "segment":      "0-1.5s",
    "veo_prompt_en": "English. ≤80 words. [subject + action], [camera], [atmosphere]. Wan2.2.",
    "ref_ids":      ["наследуй от vera_visual.frames[].ref_ids"],
    "duration_sec": 1.5,
    "camera_move":  "static | pan | tilt | zoom | track | handheld | dolly",
    "video_path":   "путь к mp4 — добавляет hooks.py после Wan2.2",  ← v3.0

    "clip_assessment": {               ← v3.0: Стэн смотрит на клип сам
      "verdict":                "APPROVED | REJECTED",
      "score":                  0.0,
      "note":                   "строка",
      "grid_observations":      "строки grid слева→право сверху→вниз",
      "corrected_motion_prompt": "если REJECTED — новый промпт EN ≤80 слов"
    }
  }],
  "compatibility_snapshot": { "technical", "creative", "rhythm" },
  "friction_note": "строка"
}
```

### `larry_edit`
```json
{
  "edit_plan": [{
    "order":         1,
    "frame_id":      "frame_01",
    "video_path":    "из stan_video.video_clips[].video_path",  ← v3.0: реальный путь
    "timecode_in":   "00:00:00",
    "timecode_out":  "00:00:01.5",
    "transition_in": "cut | swipe | zoom | whip | match | morph",
    "sfx_accent":    "из julia_sound.sfx_list или null"
  }],
  "pacing_note":       "строка",
  "total_duration_sec": 0
}
```

### `luigi_loop`
```json
{
  "retention_map": [{ "timecode", "retention_pct", "note" }],
  "retention_peak": "ТТ:СС",
  "loop": { "loop_score", "loop_point", "loop_note" },
  "retention_advice": "строка"
}
```

### `subbie_captions`
```json
{
  "captions": [{
    "timecode_in":  "00:00:00",
    "timecode_out": "00:00:01.5",
    "text":         "строка (макс 5-7 слов)",
    "position":     "top | center | bottom",
    "frame_id":     "frame_01",
    "style": { "color", "size", "animation" }
  }],
  "caption_notes": "строка"
}
```

### `tom_thumbnail` + `final_dna` ⚠️ hooks.py генерирует thumbnail через fal.ai
```json
{
  "thumbnail": {
    "variant_a": { "concept", "banana_prompt", "ref_ids", "text_overlay", "emotion", "path" },
    "variant_b": { "concept", "banana_prompt", "ref_ids", "text_overlay", "emotion", "path" }
  },
  "narrative_entry": { "episode", "summary", "cliffhanger", "key_shot" },
  "learnings_pack":  { "viral_score", "best_practices", "avoid_next", "client_feedback" },
  "client_relationship": { "trust", "revision_pressure", "creative_freedom" },
  "outcome_signal":  { "viral_score", "client_feedback", "retention_peak" },
  "qa_scores":       { "A01"…"A11": { "score", "note" } }
}
"final_dna": {
  "project_id", "mode", "episode", "viral_score", "loop_score",
  "retention_peak", "key_frames_count", "video_clips_count",
  "platform", "duration_sec"
}
```

---

## ЧТО ДОБАВЛЯЕТ hooks.py v3.0 (не агент)

| Поле | Кто добавляет | Когда |
|------|---------------|-------|
| `vera_visual.frames[].path` | hooks.py после A07 | fal.ai генерирует PNG |
| `vera_visual.frames[].self_assessment` | hooks.py после A07 | vision_client проверяет |
| `stan_video.video_clips[].video_path` | hooks.py после A08 | Wan2.2 генерирует mp4 |
| `stan_video.video_clips[].clip_assessment` | hooks.py после A08 | vision_client проверяет |
| `julia_sound.music.audio_path` | hooks.py после A03 | ElevenLabs генерирует mp3 |
| `julia_sound.sfx_list[].sfx_path` | hooks.py после A03 | ElevenLabs генерирует mp3 |
| `julia_sound.vo_lines[].vo_path` | hooks.py после A03 | CosyVoice генерирует mp3 |
| `julia_sound.music.audio_assessment` | hooks.py после A03 | Джулия слушает |
| `tom_thumbnail.thumbnail.variant_a.path` | hooks.py после A12 | fal.ai thumbnail |
| `tom_thumbnail.thumbnail.variant_b.path` | hooks.py после A12 | fal.ai thumbnail |

---

## ПРАВИЛА КОТОРЫЕ НЕЛЬЗЯ НАРУШАТЬ

| # | Правило |
|---|---------|
| 1 | Ключ агента — строго из этой таблицы. Никаких `vizor_visual`, `stella_strategy`, `turbo_*` |
| 2 | `banana_prompt` и `veo_prompt_en` — ТОЛЬКО английский |
| 3 | Формат ВСЕГДА `9:16` — горизонтальных не существует |
| 4 | `ref_ids` — только реальные asset_id из `history_dna.character_memory` |
| 5 | `history_dna` обновляет ТОЛЬКО A12 Тамб Том |
| 6 | `client_relationship` обновляет ТОЛЬКО A12 Тамб Том |
| 7 | `interaction_log` пишет ТОЛЬКО A08 Стэн (snapshot), outcome патчит ТОЛЬКО A12 |
| 8 | `cultural_trace` генерирует ТОЛЬКО A12 через CulturalFieldTracker |
| 9 | `path` / `video_path` / `audio_path` / `sfx_path` / `vo_path` — ТОЛЬКО hooks.py |
| 10 | `self_assessment` / `clip_assessment` — ТОЛЬКО hooks.py через vision_client |
| 11 | `negative_prompt` — обязателен в каждом frame у Веры |
| 12 | `dialogue` в micro_script — null если нет реплики, не пустая строка |
| 13 | Перед написанием нового промта — сверить INPUT и chain_data с этой таблицей |
| 14 | Скопировал промт из другого цеха — удали и напиши заново по этому контракту |

---

## КАК ПРОВЕРИТЬ СВОЙ ПРОМТ

Три вопроса перед сохранением:

1. **INPUT** — все ключи которые агент читает, есть в колонке "Читает" этой таблицы?
2. **my_output** — структура совпадает со структурой выше?
3. **chain_data** — агент пишет только свой ключ, остальное `{{inherit}}`?

Если хотя бы одно "нет" — промт не готов.

---

*VIDEO_SHORTS v3.0 | Контракт ключей | Спринт 40*
*Источник: SHORTS_RULES v2.2 раздел 10 + hooks.py v3.0*
*Изменения: vera_visual +negative_prompt +self_assessment | stan_video +video_path +clip_assessment | julia_sound +music +sfx_list +vo_lines | harry_episode.micro_script +dialogue*
"""

# ─── Новый manifest.json ─────────────────────────────────────────────────────

NEW_MANIFEST = {
    "id": "video_shorts",
    "label": "⚡ Видео Shorts",
    "icon": "⚡",
    "version": "3.0",
    "description": "Полный цикл: от идеи до постинга. Реальная генерация: fal.ai (кадры 9:16) + Wan2.2 I2V (видео) + ElevenLabs + CosyVoice (звук).",
    "run_type": "social",
    "phases": {
        "PRE-PROD": ["A01", "A02", "A03", "A04"],
        "PROD":     ["A05", "A06", "A07", "A08"],
        "POST-PROD":["A09", "A10", "A11", "A12"]
    },
    "checkpoint_after": ["A04"],
    "stop_after": None,
    "revision_loop": None,
    "conflict_mode": "divergent",
    "qa_agent": "A12",
    "interaction_log": "economy/data/interaction_log_video_shorts.jsonl",
    "memory_layers": ["personal", "project", "runtime", "interaction"],
    "hard_stop": {
        "after_agent": "A04",
        "residents": ["victor"]
    },
    "generation": {
        "image": {
            "agent": "A07",
            "client": "fal_client",
            "model": "nano-banana-2",
            "format": "9:16",
            "vision_check": True,
            "max_retries": 3
        },
        "video": {
            "agent": "A08",
            "client": "siliconflow_client",
            "model": "wan2.2-i2v",
            "resolution": "720p",
            "vision_check": True,
            "max_retries": 3
        },
        "audio": {
            "agent": "A03",
            "music_client": "elevenlabs_client",
            "sfx_client": "elevenlabs_client",
            "vo_client": "siliconflow_client",
            "audio_check": True,
            "max_retries": 1
        }
    }
}


# ─── Применяем ──────────────────────────────────────────────────────────────

def apply():
    check()

    # Бэкапы
    backup(CONTRACT_PATH)
    backup(MANIFEST_PATH)

    # Пишем CHAIN_CONTRACT.md
    CONTRACT_PATH.write_text(NEW_CONTRACT, encoding="utf-8")
    lines = NEW_CONTRACT.count('\n')
    print(f"✅  CHAIN_CONTRACT.md записан ({lines} строк)")

    # Пишем manifest.json
    MANIFEST_PATH.write_text(
        json.dumps(NEW_MANIFEST, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print(f"✅  manifest.json записан (version 3.0)")


def report():
    print()
    print("=" * 60)
    print("ПАТЧ ПРИМЕНЁН — video_shorts контракт v3.0")
    print("=" * 60)
    print()
    print("CHAIN_CONTRACT.md — что добавлено:")
    print()
    print("  harry_episode.micro_script[]:")
    print("    + dialogue  (текст реплики или null → Джулия → VO)")
    print()
    print("  julia_sound_code / julia_sound:")
    print("    + music        { prompt, duration_sec, mood, ducking_db, audio_path }")
    print("    + sfx_list[]   { sfx_prompt, timing_sec, sfx_path, ... }")
    print("    + vo_lines[]   { text, timing_sec, voice_style, vo_path }")
    print("    + music.audio_assessment  { verdict, score, timeline, note }")
    print()
    print("  vera_visual.frames[]:")
    print("    + negative_prompt   (обязателен, hooks.py учитывает)")
    print("    + self_assessment   { verdict, score, note, corrected_prompt }")
    print()
    print("  stan_video.video_clips[]:")
    print("    + video_path        (добавляет hooks.py после Wan2.2)")
    print("    + clip_assessment   { verdict, score, note, grid_observations,")
    print("                          corrected_motion_prompt }")
    print()
    print("  Правило 9 добавлено: path/video_path/audio_path — ТОЛЬКО hooks.py")
    print("  Правило 10: self_assessment/clip_assessment — ТОЛЬКО hooks.py")
    print("  Правило 11: negative_prompt обязателен у Веры")
    print("  Правило 12: dialogue null если нет реплики")
    print()
    print("manifest.json — что изменилось:")
    print("  version: '2.0' → '3.0'")
    print("  description: добавлено описание генерации")
    print("  + секция generation: image/video/audio конфиг")
    print()
    print("Следующий шаг:")
    print("  Разложи промты по папкам A01-A12")
    print("  Запусти patch_video_shorts_generation.py")


if __name__ == "__main__":
    apply()
    report()
