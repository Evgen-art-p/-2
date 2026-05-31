# КОНТРАКТ КЛЮЧЕЙ — VIDEO_LONG v1.3
## studio/modules/video_long/CHAIN_CONTRACT.md
##
## Это ЕДИНСТВЕННЫЙ источник правды по ключам chain_data.
## Если агент пишет ключ не из этого списка — ошибка.
## Если агент читает ключ не из этого списка — ошибка.
##
## v1.3 — синхронизирован с патчем Спринт 30:
##   - lucas_storyboard.shots: добавлены shot_type, character_id
##   - felix_vfx.video_clips: наследует shot_type, character_id от Лукаса
##   - deliverables.video_clips: Боб копирует shot_type, character_id от Феликса
##   - Правила 19–22: shot_type сквозь цепочку Лукас → Феликс → Боб → Монтажёр
##   - Добавлена lipsync логика в Монтажёре для dialog shots

---

## СВОДНАЯ ТАБЛИЦА

| Агент | Пишет (BIBLE) | Пишет (EPISODE) | Читает |
|-------|--------------|-----------------|--------|
| A01 Адам | `adam_bible` | `adam_episode` | `master_brief`, `history_dna` |
| A02 Зак | `zack_season_structure` | `zack_hook` | `adam_bible/episode`, `history_dna` |
| A03 Лео | `leo_season_breakdown` | `leo_script` | `adam_bible/episode`, `zack_season_structure/hook`, `history_dna` |
| A04 Катя | `katya_review` | `katya_review`, `katya_verdict` | `adam_bible/episode`, `zack_season_structure/hook`, `leo_season_breakdown/script` |
| Виктор | `victor_critique` | `victor_critique` | всё до A04 |
| A05 Лукас | — | `lucas_storyboard` | `leo_script`, `history_dna` |
| A06 Ева | — | `eva_visuals` | `lucas_storyboard`, `history_dna` |
| A07 Тим | — | `tim_typography` | `eva_visuals`, `lucas_storyboard` |
| A08 Феликс | — | `felix_vfx` | `eva_visuals`, `lucas_storyboard`, `history_dna` |
| A09 Алекс | — | `alex_motion` | `felix_vfx`, `eva_visuals`, `leo_script` |
| A10 Сэм | — | `sam_sound` | `leo_script`, `alex_motion`, `history_dna` |
| A11 Трейси | — | `tracy_smm` | `leo_script`, `eva_visuals`, `history_dna` |
| A12 Боб | — | `bob_marketing` + `final_dna` | ВСЁ |

**Сквозные ключи** (`{{inherit}}`): `master_brief`, `history_dna`, `mode`

---

## СТРУКТУРЫ КЛЮЧЕЙ

### `adam_bible` / `adam_episode`
```json
{
  "world": { "title", "genre", "tone", "setting", "premise" },
  "character_memory": {
    "protagonist": { "name", "fear", "trait", "visual_note" }
  },
  "visual_language": { "style", "color_mood", "lighting" },
  "sound_code": { "theme", "emotional_peaks", "no_go" },
  "series_map": { "series_id", "total_episodes", "arc" },
  "episode_brief": "строка",
  "selected_assets": ["asset_id из history_dna.character_memory — только EPISODE"],
  "client_read": "строка (только EPISODE)"
}
```

### `zack_season_structure` / `zack_hook`
```json
{
  "season_structure": {
    "arc_breakdown": [{ "episode", "emotional_beat", "retention_hook" }],
    "pacing_note": "строка"
  },
  "hook": { "text", "type", "why_it_works" },
  "retention_strategy": { "peak_moment", "loop_point", "open_loop" }
}
```

### `leo_season_breakdown` / `leo_script`
```json
{
  "episode_plan": [{ "episode", "title", "logline", "key_scene" }],
  "script": {
    "scenes": [{
      "scene_id", "description", "dialogue", "visual_note",
      "audio_note", "duration_sec", "emotional_beat"
    }]
  },
  "total_duration_sec": 0,
  "script_notes": "строка"
}
```

### `katya_review`
```json
{
  "content_check": { "passed", "issues" },
  "bible_compliance": { "passed", "deviations" },
  "safety_check": { "passed", "issues" }
}
"katya_verdict": "APPROVED | APPROVED_WITH_EDITS | REJECTED"
```

### `lucas_storyboard`
```json
{
  "shots": [{
    "shot_id",
    "scene_id",
    "framing",
    "camera_move",
    "motion_intent",
    "duration_sec",
    "composition_note",
    "shot_type",     ← "dialog" | "action" | "broll" — НОВОЕ Спринт 30
    "character_id"   ← имя персонажа или null — НОВОЕ Спринт 30
  }],
  "storyboard_notes": "строка"
}
```
⚠️ Плоский массив `shots[]` — не вложенный. Поле камеры — `camera_move` (не camera_movement).

**Правило разметки `shot_type` для Лукаса:**

| shot_type | Когда | character_id |
|-----------|-------|-------------|
| `"dialog"` | персонаж говорит, framing `close_up`/`medium`, `dialogue` в сцене не null | имя персонажа из `history_dna.character_memory` |
| `"action"` | движение, реакция, рот не важен | `null` |
| `"broll"` | пейзаж, объект, атмосфера | `null` |

ПРАВИЛО: если сцена с `dialogue` и `framing == close_up` или `medium` → `dialog`.
Если `dialogue null` или `framing == wide/aerial` → `broll` или `action`.
Не ставь `dialog` на групповые планы где рот не виден.

### `eva_visuals` ⚠️ hooks.py добавляет `path` после генерации
```json
{
  "format": "16:9",
  "platform": "строка",
  "frames": [{
    "frame_id",
    "shot_id",
    "banana_prompt",
    "ref_ids",
    "composition",
    "focus_point",
    "timing",
    "self_assessment": { "verdict", "score", "note" },
    "path"  ← добавляет hooks.py после fal.ai + ОТК
  }],
  "color_palette": ["hex_1", "hex_2", "hex_3"],
  "visual_notes": "строка"
}
```
⚠️ Поле кадров — `frames` (не key_frames, не key_shots).

### `tim_typography`
```json
{
  "titles": [{
    "frame_id", "text", "font", "size", "color",
    "position", "animation", "duration_sec"
  }],
  "lower_thirds": [{ "timecode", "text", "style" }],
  "typography_notes": "строка"
}
```

### `felix_vfx` ⚠️ hooks.py добавляет `video_path` после генерации Wan2.2
```json
{
  "video_clips": [{
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
  }],
  "compatibility_snapshot": {
    "technical": 0.0,
    "creative":  0.0,
    "rhythm":    0.0
  },
  "friction_note": "строка"
}
```
⚠️ Поле клипов — `video_clips`. Промпт — `motion_prompt` (ТОЛЬКО английский). Поле камеры — `camera_move`.
⚠️ `compatibility_snapshot` обязателен — hooks.py логирует в interaction_log.
⚠️ `video_path` — реальный mp4, не промпт. Добавляет хук после Wan2.2.

### `alex_motion`
```json
{
  "motion_plan": [{
    "clip_id", "frame_id", "animation_type",
    "easing", "duration_sec", "note"
  }],
  "edit_rhythm": {
    "pattern": "steady | rising | pulsing",
    "sync_to": "music | vo | action",
    "cut_note": "строка"
  },
  "motion_notes": "строка"
}
```

### `sam_sound` ⚠️ hooks.py добавляет audio_path, sfx_path, vo_path после генерации
```json
{
  "sound_design": [{
    "scene_id", "track_mood", "sfx", "music_cue",
    "volume_note", "timecode_in", "timecode_out"
  }],
  "music": {
    "prompt": "ТОЛЬКО английский",
    "duration_sec": 0,
    "mood": "строка",
    "ducking_db": -12,
    "audio_path": "строка ← добавляет hooks.py после ElevenLabs",
    "audio_assessment": { "verdict", "score", "timeline", "note" }
  },
  "sfx_list": [{
    "scene_id",
    "sfx_prompt": "ТОЛЬКО английский",
    "duration_sec": 0,
    "timing_sec": 0,
    "purpose": "строка",
    "sfx_path": "строка ← добавляет hooks.py после ElevenLabs"
  }],
  "vo_lines": [{
    "scene_id",
    "text": "из leo_script.scenes[].dialogue",
    "timing_sec": 0,
    "voice_style": "warm | authoritative | energetic | whisper",
    "vo_path": "строка ← добавляет hooks.py после CosyVoice"
  }],
  "master_mix_note": "строка",
  "mutations": [],
  "self_reflection": { "mood_match", "would_reuse_fragment", "tension_point" }
}
```
⚠️ `audio_path`, `sfx_path`, `vo_path` — реальные mp3. Добавляет хук A10 после ElevenLabs/CosyVoice.

### `tracy_smm` ⚠️ hooks.py добавляет `path` к обложкам после генерации
```json
{
  "thumbnail": {
    "concept": "строка",
    "variant_a": {
      "banana_prompt": "ТОЛЬКО английский",
      "ref_ids": [],
      "text_overlay": "строка",
      "emotion": "строка",
      "thumbnail_assessment": { "verdict", "score", "note" },
      "path"  ← добавляет hooks.py после fal.ai
    },
    "variant_b": {
      "banana_prompt": "ТОЛЬКО английский",
      "ref_ids": [],
      "text_overlay": "строка",
      "emotion": "строка",
      "thumbnail_assessment": { "verdict", "score", "note" },
      "path"  ← добавляет hooks.py после fal.ai
    }
  },
  "teaser_plan": [{ "platform", "format", "duration_sec", "hook_text", "posting_time" }],
  "seo": { "title", "description", "hashtags", "keywords" },
  "smm_notes": "строка"
}
```

### `bob_marketing` + `final_dna`
```json
{
  "chain_status": "APPROVED | FAILED",
  "failed_checks": [],
  "marketing_notes": "личный взгляд продюсера — не для системы",
  "viral_score": null,
  "audience_fit": "строка",
  "distribution_strategy": "строка"
}

"deliverables": {
  "project_id": "строка",
  "platform": "строка",
  "key_frames": [{
    "frame_id", "shot_id", "scene_id",
    "banana_prompt", "ref_ids", "format", "path"
  }],
  "video_clips": [{
    "frame_id", "shot_id", "scene_id",
    "shot_type",     ← НОВОЕ Спринт 30 (копирует от Феликса)
    "character_id",  ← НОВОЕ Спринт 30 (копирует от Феликса)
    "motion_prompt", "camera_move", "duration_sec",
    "ref_ids", "vfx_layer",
    "video_path"  ← реальный mp4 от Феликса
  }],
  "thumbnail": {
    "concept": "строка",
    "variant_a": { "banana_prompt", "ref_ids", "text_overlay", "path" },
    "variant_b": { "banana_prompt", "ref_ids", "text_overlay", "path" }
  },
  "audio": { sam_sound целиком — с audio_path, sfx_path, vo_path },
  "typography": { tim_typography },
  "motion": { alex_motion },
  "description": "строка",
  "hashtags": [],
  "posting_time": "строка"
}

"final_dna": {
  "project_id", "mode", "episode",
  "key_frames_count", "video_clips_count",
  "platform", "duration_sec"
}
```
⚠️ `deliverables.video_clips` — не `veo3_prompts`. Содержат `video_path` (реальные mp4).
⚠️ `chain_status` — обязательное поле. Хук `_monteur_after_bob` проверяет его.

---

## ПРАВИЛА КОТОРЫЕ НЕЛЬЗЯ НАРУШАТЬ

| # | Правило |
|---|---------|
| 1 | Ключ агента — строго из этой таблицы |
| 2 | `banana_prompt` и `motion_prompt` — ТОЛЬКО английский |
| 3 | Формат ВСЕГДА `16:9` |
| 4 | `ref_ids` — только реальные asset_id из `history_dna.character_memory` |
| 5 | `history_dna` обновляет ТОЛЬКО A12 Боб |
| 6 | `client_relationship` обновляет ТОЛЬКО A12 Боб |
| 7 | `interaction_log` пишет ТОЛЬКО A08 Феликс, outcome_signal заполняет ТОЛЬКО A12 |
| 8 | `cultural_trace` генерирует ТОЛЬКО A12 через CulturalFieldTracker |
| 9 | Перед написанием нового промта — сверить INPUT и chain_data с этой таблицей |
| 10 | `motion_intent` — рекомендация Лукаса, не директива |
| 11 | `katya_verdict` и `victor_critique` — гейт ХАРД-СТОП |
| 12 | `lucas_storyboard.shots` — плоский массив, не вложенный |
| 13 | `tracy_smm.thumbnail` — всегда `variant_a` и `variant_b` |
| 14 | `felix_vfx.video_clips[*].video_path` — реальный mp4, не промпт |
| 15 | `eva_visuals.frames` — поле кадров только так |
| 16 | `sam_sound.music.audio_path` — реальный mp3, добавляет хук A10 |
| 17 | `deliverables.video_clips` — не `veo3_prompts`. Монтажёр читает именно это |
| 18 | `bob_marketing.chain_status` = APPROVED → хук запускает Монтажёра автоматически |
| 19 | `lucas_storyboard.shots[*].shot_type` — обязательное поле. Лукас размечает каждый шот |
| 20 | `shot_type` передаётся сквозь цепочку: Лукас → Феликс → Боб → Монтажёр |
| 21 | `character_id` — только для dialog shots. Для action/broll = null |
| 22 | Монтажёр читает `shot_type` из `deliverables.video_clips` — не угадывает |

---

## КАК ПРОВЕРИТЬ СВОЙ ПРОМТ

1. **INPUT** — все ключи которые агент читает, есть в колонке "Читает"?
2. **my_output** — структура совпадает со структурой выше?
3. **chain_data** — агент пишет только свой ключ, остальное `{{inherit}}`?

---

*VIDEO_LONG v1.3 | Контракт ключей | Спринт 30 | 2026-05-31*
*Синхронизирован с патчем Спринт 30: shot_type, character_id (Лукас → Феликс → Боб → Монтажёр), lipsync логика*
