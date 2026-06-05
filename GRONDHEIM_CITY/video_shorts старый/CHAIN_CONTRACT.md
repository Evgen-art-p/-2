# КОНТРАКТ КЛЮЧЕЙ — VIDEO_SHORTS v2.2
## studio/modules/video_shorts/CHAIN_CONTRACT.md
##
## Это ЕДИНСТВЕННЫЙ источник правды по ключам chain_data.
## Если агент пишет ключ не из этого списка — ошибка.
## Если агент читает ключ не из этого списка — ошибка.
##
## Редактировать только вместе с SHORTS_RULES.md раздел 10.
## Не копировать в другие цеха.

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
  "micro_script": [{ "segment", "action", "emotion", "visual_hint", "duration_sec" }],
  "series_map": { "series_id", "total_episodes", "current_episode", "arc", "cliffhanger" },
  "character_memory": { "protagonist": { "name", "fear", "trait", "visual_note" } },
  "narrative_entry": { "episode", "summary", "cliffhanger", "key_shot" }
}
```

### `julia_sound_code` / `julia_sound`
```json
{
  "sound_code": { "theme", "bpm_range", "emotional_peaks", "no_go", "jingle" },
  "episode_sound": [{ "segment", "track_mood", "sfx", "volume_note" }],
  "sound_notes": "строка"
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

### `vera_visual` ⚠️ hooks.py добавляет `path` после генерации
```json
{
  "format": "9:16",
  "platform": "строка",
  "frames": [{
    "frame_id", "segment", "banana_prompt", "ref_ids",
    "composition", "focus_point", "safe_zone_check", "timing",
    "path"  ← добавляет hooks.py после fal.ai
  }],
  "visual_notes": "строка"
}
```

### `stan_video`
```json
{
  "video_clips": [{ "frame_id", "segment", "veo_prompt_en", "ref_ids", "duration_sec", "camera_move" }],
  "compatibility_snapshot": { "technical", "creative", "rhythm" },
  "friction_note": "строка"
}
```

### `larry_edit`
```json
{
  "edit_plan": [{ "order", "frame_id", "timecode_in", "timecode_out", "transition_in", "sfx_accent" }],
  "pacing_note": "строка",
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
  "captions": [{ "timecode_in", "timecode_out", "text", "position", "style": { "color", "size", "animation" } }],
  "caption_notes": "строка"
}
```

### `tom_thumbnail` + `final_dna` ⚠️ hooks.py добавляет `path` к обложке
```json
{
  "thumbnail": {
    "variant_a": { "concept", "banana_prompt", "ref_ids", "text_overlay", "emotion", "path" },
    "variant_b": { "concept", "banana_prompt", "ref_ids", "text_overlay", "emotion", "path" }
  },
  "narrative_entry": { "episode", "summary", "cliffhanger", "key_shot" },
  "learnings_pack": { "viral_score", "best_practices", "avoid_next", "client_feedback" },
  "client_relationship": { "trust", "revision_pressure", "creative_freedom" },
  "outcome_signal": { "viral_score", "client_feedback", "retention_peak" },
  "qa_scores": { "A01"…"A11": { "score", "note" } }
}
"final_dna": { "project_id", "mode", "episode", "viral_score", "loop_score",
               "retention_peak", "key_frames_count", "veo3_clips_count",
               "platform", "duration_sec" }
```

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
| 7 | `interaction_log` пишет ТОЛЬКО A08 Стэн, заполняет outcome ТОЛЬКО A12 |
| 8 | `cultural_trace` генерирует ТОЛЬКО A12 через CulturalFieldTracker |
| 9 | Перед написанием нового промта — сверить INPUT и chain_data с этой таблицей |
| 10 | Скопировал промт из другого цеха — удали и напиши заново по этому контракту |

---

## КАК ПРОВЕРИТЬ СВОЙ ПРОМТ

Три вопроса перед сохранением:

1. **INPUT** — все ключи которые агент читает, есть в колонке "Читает" этой таблицы?
2. **my_output** — структура совпадает со структурой выше?
3. **chain_data** — агент пишет только свой ключ, остальное `{{inherit}}`?

Если хотя бы одно "нет" — промт не готов.

---

*VIDEO_SHORTS v2.2 | Контракт ключей | Спринт 19*
*Источник: SHORTS_RULES v2.2 раздел 10*
