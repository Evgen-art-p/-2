# КОНТРАКТ КЛЮЧЕЙ — TURBO v2.1
## studio/modules/turbo/CHAIN_CONTRACT_TURBO.md
##
## Это ЕДИНСТВЕННЫЙ источник правды по ключам chain_data цеха TURBO.
## Если агент пишет ключ не из этого списка — ошибка.
## Если агент читает ключ не из этого списка — ошибка.
##
## Редактировать только вместе с TURBO_RULES.md.
##
## v2.1 — уточнение механики вызовов:
##   - A02 вызывается ДВАЖДЫ (промпты → audio review)
##   - A03 вызывается ТРИЖДЫ (промпты → self-review → clip-review)
##   - chain_check добавлен в таблицу (пишет A05)
##   - clip_assessment добавлен в vizor_visual.key_frames
##   - mimi_sound.music теперь dict с prompt, audio_path, audio_assessment

---

## ⚠️ ДВОЙНАЯ НОТАЦИЯ — ЧИТАТЬ ОБЯЗАТЕЛЬНО

| Уровень | Нотация | Где используется |
|---------|---------|-----------------|
| Кодовые имена персонажей | **T1–T5** | Промпты агентов, chain_data ключи, TURBO_RULES |
| Системные ID | **A01–A05** | Папки на диске, worker_id в pipeline, manifest.json, hooks.py |

---

## СВОДНАЯ ТАБЛИЦА

| worker_id | Агент | Пишет | Читает |
|-----------|-------|-------|--------|
| A01 | T1 Стелла | `stella_strategy` | `master_brief` |
| A02 | T2 Мими | `mimi_sound` | `master_brief`, `stella_strategy` |
| A03 | T3 Визор | `vizor_visual` | `master_brief`, `stella_strategy` |
| A04 | T4 Постпро | `postpro` | `master_brief`, `stella_strategy`, `mimi_sound`, `vizor_visual` |
| A05 | T5 Финализатор | `thumbnail`, `chain_check`, `final_dna` | ВСЁ |

**Ключи которые hooks.py пишет самостоятельно** (агенты не трогают):
- `vizor_visual` ← hooks.py добавляет `path`, `video_path`, `quality_score`, `quality`, `self_assessment`, `clip_assessment`
- `mimi_sound` ← hooks.py добавляет `music.audio_path`, `music.audio_assessment`, `sfx_list[*].sfx_path`, `vo_lines[*].vo_path`
- `chain_check` ← hooks.py читает из my_output A05 и прокидывает в chain_data
- `t5_deliverables` ← hooks.py собирает после A05

---

## ПОРЯДОК ВЫЗОВОВ АГЕНТОВ

```
A01 → один вызов

A02 → ДВАЖДЫ:
  Вызов 1: агент пишет промпты
           hooks.py → ElevenLabs музыка + SFX + CosyVoice VO
           state["audio_files"] = [music_path]
  Вызов 2: агент слушает трек через chat_with_audio()
           пишет audio_assessment (APPROVED/REJECTED)
           REJECTED → hooks.py перегенерирует с revised_prompt

A03 → ТРИЖДЫ:
  Вызов 1: агент пишет промпты (banana + wan)
           hooks.py → Nano Banana PNG + vision OTK
           state["vision_images"] = [png_paths]
  Вызов 2: агент смотрит на PNG через chat_with_images()
           пишет self_assessment (APPROVED/REJECTED)
           REJECTED → hooks.py перегенерирует кадр
           hooks.py → Wan2.2 I2V → mp4 клипы + ffmpeg grid
           state["vision_images"] = [grid_frames]
  Вызов 3: агент смотрит на grid клипов через chat_with_images()
           пишет clip_assessment (APPROVED/REJECTED)
           REJECTED → hooks.py перегенерирует клип

A04 → один вызов

A05 → один вызов
  Chain Integrity Check → chain_status APPROVED/BLOCKED
  hooks.py читает chain_status из my_output → кладёт в chain_data
  APPROVED → hooks.py запускает 006_MONTEUR → final.mp4
  BLOCKED  → Монтажёр не запускается
```

---

## СТРУКТУРЫ КЛЮЧЕЙ

### `stella_strategy`
```json
{
  "project_id": "TURBO_YYYYMMDD_XXX",
  "script": {
    "micro_script": [
      {
        "segment": "0-1.5s",
        "timing": "0–1.5s",
        "purpose": "hook",
        "description": "строка",
        "voiceover": "строка или null",
        "visual_note": "строка"
      }
    ],
    "total_duration_sec": 30
  },
  "selected_assets": {
    "characters": [{"id": "char_xxx", "name": "строка", "role": "строка"}],
    "locations":  [{"id": "loc_xxx",  "name": "строка", "role": "строка"}],
    "props": [],
    "notes": "строка"
  },
  "seo": {
    "hashtags": {"niche": [], "medium": [], "broad": []},
    "description": "строка",
    "posting_time": {"best_time": "строка", "timezone": "MSK"}
  },
  "platform": "строка",
  "style_tags": ["строка"]
}
```
⚠️ `project_id` — формат `TURBO_YYYYMMDD_XXX`, задаёт только T1.
⚠️ `total_duration_sec` — источник истины для всех агентов.
⚠️ `micro_script[*].voiceover` — hooks.py читает для генерации VO через CosyVoice.

---

### `mimi_sound` ⚠️ hooks.py добавляет audio-пути и assessment после вызовов
```json
{
  "audio_match": {
    "type": "trending | original | hybrid",
    "track": "строка",
    "rationale": "строка"
  },
  "mood": {
    "bpm": 128,
    "emotion": "energetic | chill | dramatic | funny | dark",
    "instruments": ["bass", "synth", "clap"]
  },
  "music": {
    "prompt": "ТОЛЬКО английский — для ElevenLabs",
    "duration_sec": 35,
    "ducking_db": -12,
    "audio_path": null,
    "audio_assessment": null
  },
  "sfx_list": [
    {
      "sfx_prompt": "whoosh cinematic",
      "duration_sec": 1.5,
      "timing_sec": 0.0,
      "segment": "0-1.5s",
      "purpose": "строка",
      "sfx_path": null
    }
  ],
  "vo_lines": [
    {
      "text": "из micro_script.voiceover",
      "timing_sec": 1.5,
      "segment": "1.5-5s",
      "voice_style": "строка",
      "vo_path": null
    }
  ],
  "beat_map": [
    {"time_sec": 0.0, "beat": "DROP", "edit_note": "строка"}
  ],
  "suno_prompt": "то же что music.prompt — для совместимости"
}
```
⚠️ `music.prompt` — только английский. hooks.py передаёт в ElevenLabs.
⚠️ `music.audio_path`, `music.audio_assessment` — агент ставит null. hooks.py заполнит.
⚠️ `sfx_list[*].sfx_path`, `vo_lines[*].vo_path` — агент ставит null. hooks.py заполнит.
⚠️ Fallback: если агент написал `suno_prompt` вместо `music.prompt` — hooks.py подхватит.

---

### `vizor_visual` ⚠️ hooks.py добавляет пути и assessments после вызовов
```json
{
  "style": "строка из 10_Style_Matrix",
  "palette": {
    "primary": "#hex",
    "secondary": "#hex",
    "accent": "#hex"
  },
  "platform_specs": {
    "resolution": "1080x1920",
    "fps": 30,
    "safe_zone": "строка"
  },
  "key_frames": [
    {
      "segment": "0-1.5s",
      "purpose": "hook",
      "shot_type": "close-up | medium | wide | dialog",
      "composition": "rule_of_thirds",
      "camera_move": "zoom-in",
      "focus_point": "строка",
      "transition_out": "cut",
      "lighting": {
        "source": "строка",
        "direction": "строка",
        "mood": "строка",
        "color_temp": "строка"
      },
      "props": ["строка"],
      "texture": "строка",
      "banana_prompt": "ТОЛЬКО английский",
      "ref_ids": ["asset_id из selected_assets"],
      "style_tags": ["из 10_Style_Matrix"],
      "wan_motion_prompt": "ТОЛЬКО английский",
      "wan_camera_move": "static | zoom_in | zoom_out | pan_left | pan_right | tilt_up | tilt_down",
      "wan_duration_sec": 4,
      "path": null,
      "video_path": null,
      "quality_score": null,
      "quality": null,
      "self_assessment": null,
      "clip_assessment": null
    }
  ],
  "tech_checklist": {
    "safe_zone": "pass | fail",
    "palette_consistent": "pass | fail",
    "banana_formula": "pass | fail",
    "wan_prompts": "pass | fail",
    "style_tags": "pass | fail",
    "anatomy_fix": "pass | fail",
    "ref_ids_filled": "pass | fail",
    "verdict": "READY | NEEDS_FIX"
  }
}
```
⚠️ Поле кадров — `key_frames`. Не `frames`, не `shots`.
⚠️ Формат ВСЕГДА `9:16`.
⚠️ `wan_motion_prompt`, `wan_camera_move`, `wan_duration_sec` — обязательны. hooks.py читает для Wan2.2 I2V.
⚠️ ~~`veo3_prompt`, `veo3_camera_motion`, `veo3_duration_sec`~~ — УСТАРЕЛИ. Не использовать.
⚠️ `path`, `video_path`, `quality_score`, `quality`, `self_assessment`, `clip_assessment` — агент ставит `null`. hooks.py заполнит.
⚠️ `ref_ids` — только asset_id из `stella_strategy.selected_assets`.
⚠️ `shot_type` несёт сквозь цепочку до Монтажёра — `dialog` → lipsync.

---

### `postpro`
```json
{
  "edit_plan": [
    {
      "segment": "0-1.5s",
      "cuts": 0,
      "transition_out": "cut",
      "speed": "1x",
      "beat_sync": "DROP at 0.0s"
    }
  ],
  "rhythm": {
    "source_bpm": "из mimi_sound.mood.bpm",
    "avg_cut_sec": 2,
    "total_cuts": 12,
    "sync_to": "beat_map"
  },
  "loop": {
    "last_frame": "строка",
    "first_frame": "строка",
    "connection": "строка",
    "seamless_score": "X/10",
    "wan_correction": {
      "last_clip_segment": "25-30s",
      "last_clip_note": "строка или null",
      "first_clip_segment": "0-1.5s",
      "first_clip_note": "строка или null"
    }
  },
  "retention_map": [
    {"time": "0-5s", "attention": "high", "risk": "low", "solution": "строка"}
  ],
  "easter_egg": "строка",
  "captions": {
    "style": {"font": "строка", "size": "large", "color": "#FFFFFF"},
    "segments": [
      {"segment": "0-1.5s", "text": "строка", "position": "center", "animation": "pop", "accent_word": "строка"}
    ]
  }
}
```

---

### `chain_check` — пишет A05, читает hooks.py
```json
{
  "chain_status": "APPROVED | BLOCKED",
  "failed_checks": [],
  "assigned_to": "строка или null",
  "checks": {
    "frames_have_path":      "PASS | FAIL",
    "frames_self_review":    "PASS | FAIL",
    "clips_have_video_path": "PASS | FAIL",
    "clips_clip_review":     "PASS | FAIL",
    "audio_has_path":        "PASS | FAIL",
    "audio_review":          "PASS | FAIL",
    "timings_match":         "PASS | FAIL"
  }
}
```
⚠️ A05 пишет в `my_output.chain_check`. hooks.py читает и кладёт в `chain_data`.
⚠️ `APPROVED` → Монтажёр запускается. `BLOCKED` → не запускается.

---

### `thumbnail` ⚠️ hooks.py добавляет `path`, `quality_score`, `quality`
```json
{
  "variant_a": {
    "concept": "строка",
    "banana_prompt": "ТОЛЬКО английский",
    "ref_ids": ["asset_id"],
    "text_overlay": "строка",
    "emotion": "строка",
    "style_tags": ["строка"],
    "quality_check": "строка",
    "path": null,
    "quality_score": null,
    "quality": null
  },
  "variant_b": {
    "concept": "строка",
    "banana_prompt": "ТОЛЬКО английский",
    "ref_ids": ["asset_id"],
    "text_overlay": "строка",
    "emotion": "строка",
    "style_tags": ["строка"],
    "quality_check": "строка",
    "path": null,
    "quality_score": null,
    "quality": null
  }
}
```
⚠️ Всегда два варианта A/B.

---

### `final_dna`
```json
{
  "project_id": "строка",
  "mode": "TURBO",
  "chain_status": "APPROVED | BLOCKED",
  "platform": "строка",
  "duration_sec": 30,
  "key_frames_count": 5,
  "clips_count": 5,
  "has_audio": true,
  "has_vo": false,
  "what_worked": "строка",
  "improve_next": "строка"
}
```
⚠️ Пишет ТОЛЬКО T5 Финализатор (A05).

---

### `t5_deliverables` — пишет ТОЛЬКО hooks.py
```json
{
  "project_id": "строка",
  "status": "ready_to_publish | incomplete",
  "thumbnail": {
    "variant_a": {"banana_prompt", "text_overlay", "emotion", "ref_ids", "style_tags", "path", "quality_score", "quality"},
    "variant_b": {"banana_prompt", "text_overlay", "emotion", "ref_ids", "style_tags", "path", "quality_score", "quality"}
  },
  "key_frames": [
    {"segment", "purpose", "prompt", "ref_ids", "format": "9:16", "path", "video_path", "quality_score", "quality"}
  ],
  "wan_clips": [
    {"segment", "wan_camera_move", "wan_duration_sec", "wan_motion_prompt", "ref_ids"}
  ],
  "audio": {
    "music": {"audio_path": "строка или null", "ducking_db": -12},
    "sfx_list": [{"sfx_prompt", "sfx_path", "segment", "timing_sec"}],
    "vo_lines": [{"text", "vo_path", "segment", "timing_sec"}]
  },
  "captions": {},
  "publication": {}
}
```
⚠️ `wan_clips` вместо ~~`veo3_prompts`~~.
⚠️ Агенты этот ключ не пишут.

---

## ПРАВИЛА КОТОРЫЕ НЕЛЬЗЯ НАРУШАТЬ

| # | Правило |
|---|---------|
| 1 | Ключ агента — строго из этой таблицы |
| 2 | `banana_prompt`, `wan_motion_prompt`, `music.prompt` — ТОЛЬКО английский |
| 3 | Формат ВСЕГДА `9:16` |
| 4 | `ref_ids` — только реальные asset_id из `stella_strategy.selected_assets` |
| 5 | `path`, `video_path`, `quality_score`, `quality`, `self_assessment`, `clip_assessment`, `audio_assessment` — агент ставит `null` |
| 6 | `final_dna` и `t5_deliverables` пишет ТОЛЬКО T5 / hooks.py |
| 7 | `project_id` задаёт ТОЛЬКО T1 Стелла |
| 8 | `total_duration_sec` — источник истины для хронометража |
| 9 | `vizor_visual.key_frames` содержат `wan_motion_prompt`, `wan_camera_move`, `wan_duration_sec` — без них нет анимации |
| 10 | `thumbnail` — всегда два варианта A/B |
| 11 | worker_id в коде — A-нотация. В промптах — T-имена |
| 12 | JSON ВСЕГДА ПЕРВЫМ |
| 13 | T2 и T3 работают параллельно — не читают друг друга |
| 14 | В chain_data писать `"{{inherit}}"` |
| 15 | **🔴 `veo3_*` поля — УСТАРЕЛИ. Не использовать. Только `wan_*`** |
| 16 | **🔴 A02 вызывается ДВАЖДЫ: Вызов 1 (промпты + генерация) → Вызов 2 (audio review)** |
| 17 | **🔴 A03 вызывается ТРИЖДЫ: Вызов 1 (промпты) → Вызов 2 (self-review картинок) → Вызов 3 (clip-review клипов)** |
| 18 | **🔴 `chain_status: BLOCKED` → Монтажёр не запускается. Цепочка возвращается.** |
| 19 | `shot_type = "dialog"` + `vo_path` → lipsync в Монтажёре |

---

## ИЗМЕНЕНИЯ v2.1 vs v2.0

| Что | v2.0 | v2.1 |
|-----|------|------|
| A02 вызовов | 1 | **2** (промпты → audio review) |
| A03 вызовов | 2 | **3** (промпты → self-review → clip-review) |
| `chain_check` в таблице | ❌ | ✅ A05 пишет, hooks.py прокидывает |
| `clip_assessment` в key_frames | ❌ | ✅ |
| `mimi_sound.music` | строка `suno_prompt` | dict `{prompt, audio_path, audio_assessment}` |
| ОТК таблица | неполная | ✅ все 5 слоёв |

---

*TURBO v2.1 | Контракт ключей | 2026-06-02*
*Синхронизирован с: hooks.py v4.0, TURBO_RULES v4.1*
