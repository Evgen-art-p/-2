# КОНТРАКТ КЛЮЧЕЙ — VIDEO_LONG v1.1
## studio/modules/video_long/CHAIN_CONTRACT.md
##
## Это ЕДИНСТВЕННЫЙ источник правды по ключам chain_data.
## Если агент пишет ключ не из этого списка — ошибка.
## Если агент читает ключ не из этого списка — ошибка.
##
## Редактировать только вместе с LONG_RULES.md раздел 10.
## Не копировать в другие цеха.
##
## v1.1 — синхронизирован с hooks.py v2.1:
##   - eva_visuals: поле кадров → "frames" (единый стандарт)
##   - felix_vfx: поле клипов → "video_clips", промпт → "veo_prompt_en",
##                добавлен "compatibility_snapshot"
##   - lucas_storyboard: плоская структура shots[] (camera_move единый стандарт)
##   - tracy_smm.thumbnail: A/B варианты (variant_a / variant_b)
##   - Сквозные ключи: master_brief (единый стандарт студии)

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

**Сквозные ключи** (наследуют все агенты через `{{inherit}}`):
- `master_brief`
- `history_dna`
- `mode`

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
    "composition_note"
  }],
  "storyboard_notes": "строка"
}
```
⚠️ Плоский массив `shots[]` — не вложенный. Поле камеры — `camera_move` (не camera_movement).

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
    "path"  ← добавляет hooks.py после fal.ai
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

### `felix_vfx`
```json
{
  "video_clips": [{
    "frame_id",
    "shot_id",
    "veo_prompt_en",
    "ref_ids",
    "duration_sec",
    "camera_move",
    "vfx_layer"
  }],
  "compatibility_snapshot": {
    "technical": 0.0,
    "creative":  0.0,
    "rhythm":    0.0
  },
  "friction_note": "строка"
}
```
⚠️ Поле клипов — `video_clips`. Промпт — `veo_prompt_en` (ТОЛЬКО английский). Поле камеры — `camera_move`.
⚠️ `compatibility_snapshot` обязателен — hooks.py логирует его в interaction_log.

### `alex_motion`
```json
{
  "motion_plan": [{
    "clip_id", "frame_id", "animation_type",
    "easing", "duration_sec", "note"
  }],
  "motion_notes": "строка"
}
```

### `sam_sound`
```json
{
  "sound_design": [{
    "scene_id", "track_mood", "sfx", "music_cue",
    "volume_note", "timecode_in", "timecode_out"
  }],
  "master_mix_note": "строка"
}
```

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
      "path"  ← добавляет hooks.py после fal.ai
    },
    "variant_b": {
      "banana_prompt": "ТОЛЬКО английский",
      "ref_ids": [],
      "text_overlay": "строка",
      "emotion": "строка",
      "path"  ← добавляет hooks.py после fal.ai
    }
  },
  "teaser_plan": [{
    "platform", "format", "duration_sec", "hook_text", "posting_time"
  }],
  "seo": { "title", "description", "hashtags", "keywords" },
  "smm_notes": "строка"
}
```
⚠️ Thumbnail всегда в двух вариантах (A/B) — hooks.py генерирует оба параллельно.

### `bob_marketing` + `final_dna`
```json
{
  "marketing_review": {
    "viral_score": 0.0,
    "audience_fit": "строка",
    "distribution_strategy": "строка"
  },
  "deliverables": {
    "key_frames":   [{ собранные кадры от Евы }],
    "storyboard":   [{ shots от Лукаса }],
    "thumbnail":    { "variant_a": { "path" }, "variant_b": { "path" } },
    "veo3_prompts": [{ клипы от Феликса }],
    "audio":        { sam_sound },
    "motion":       { alex_motion },
    "typography":   { tim_typography }
  },
  "narrative_entry": { "episode", "summary", "cliffhanger", "key_shot" },
  "learnings_pack": { "viral_score", "best_practices", "avoid_next", "client_feedback" },
  "client_relationship": { "trust", "revision_pressure", "creative_freedom" },
  "outcome_signal": { "viral_score", "client_feedback", "retention_peak" }
}
"final_dna": {
  "project_id", "mode", "episode", "viral_score",
  "retention_peak", "key_frames_count", "veo3_clips_count",
  "platform", "duration_sec"
}
```

---

## ПРАВИЛА КОТОРЫЕ НЕЛЬЗЯ НАРУШАТЬ

| # | Правило |
|---|---------|
| 1 | Ключ агента — строго из этой таблицы. Никаких `adam_arc`, `zack_structure`, `lucas_shots` и других вариаций |
| 2 | `banana_prompt` и `veo_prompt_en` — ТОЛЬКО английский |
| 3 | Формат ВСЕГДА `16:9` — вертикальных в этом цехе не существует |
| 4 | `ref_ids` — только реальные asset_id из `history_dna.character_memory` |
| 5 | `history_dna` обновляет ТОЛЬКО A12 Боб |
| 6 | `client_relationship` обновляет ТОЛЬКО A12 Боб |
| 7 | `interaction_log` пишет ТОЛЬКО A08 Феликс, заполняет outcome ТОЛЬКО A12 |
| 8 | `cultural_trace` генерирует ТОЛЬКО A12 через CulturalFieldTracker |
| 9 | Перед написанием нового промта — сверить INPUT и chain_data с этой таблицей |
| 10 | Скопировал промт из другого цеха — удали и напиши заново по этому контракту |
| 11 | `motion_intent` — рекомендация Лукаса, не директива. Феликс может отступить — логирует в `friction_note` |
| 12 | `katya_verdict` и `victor_critique` — гейт ХАРД-СТОП. Без APPROVED/APPROVED_WITH_EDITS PROD не запускается |
| 13 | `lucas_storyboard.shots` — плоский массив, не вложенный. Не путать со структурой `storyboard→scenes→shots` |
| 14 | `tracy_smm.thumbnail` — всегда `variant_a` и `variant_b`. Промт A11 генерирует оба варианта |
| 15 | `felix_vfx.video_clips` — поле клипов только так. `veo_prompt_en` — поле промпта |
| 16 | `eva_visuals.frames` — поле кадров только так |

---

## КАК ПРОВЕРИТЬ СВОЙ ПРОМТ

Три вопроса перед сохранением:

1. **INPUT** — все ключи которые агент читает, есть в колонке "Читает" этой таблицы?
2. **my_output** — структура совпадает со структурой выше?
3. **chain_data** — агент пишет только свой ключ, остальное `{{inherit}}`?

Если хотя бы одно "нет" — промт не готов.

---

## ОТЛИЧИЯ ОТ VIDEO_SHORTS

| Параметр | VIDEO_LONG | VIDEO_SHORTS |
|----------|-----------|-------------|
| Режимы | BIBLE + EPISODE | PILOT + EPISODE |
| Формат | 16:9 | 9:16 |
| Гейт A04 | Катя → `katya_review` / `katya_verdict` | Тэг Тони → `tony_seo` / `tony_verdict` |
| qa_agent A12 | Боб Блокбастер → `bob_marketing` + `final_dna` | Тамб Том → `tom_thumbnail` + `final_dna` |
| Кадры A06 | Ева → `eva_visuals` (16:9, Nano Banana 2, поле `frames`) | Вера A07 → `vera_visual` (9:16) |
| Видео A08 | Феликс → `felix_vfx` + `video_clips` | Стэн A08 → `stan_video` |
| Между кадрами и видео | A07 Тим → `tim_typography` | нет |
| Сквозные ключи | `master_brief`, `history_dna`, `mode` | `master_brief`, `history_dna`, `mode` |
| interaction_log | `interaction_log_video_long.jsonl` | `interaction_log_video_shorts.jsonl` |

---

*VIDEO_LONG v1.1 | Контракт ключей | Спринт 19*
*Источник: LONG_RULES v4.2 раздел 10 | Синхронизирован с hooks.py v2.1*
