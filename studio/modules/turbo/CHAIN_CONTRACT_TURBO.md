# КОНТРАКТ КЛЮЧЕЙ — TURBO v2.0
## studio/modules/turbo/CHAIN_CONTRACT_TURBO.md
##
## Это ЕДИНСТВЕННЫЙ источник правды по ключам chain_data цеха TURBO.
## Если агент пишет ключ не из этого списка — ошибка.
## Если агент читает ключ не из этого списка — ошибка.
##
## Редактировать только вместе с TURBO_RULES.md.
##
## v2.0 — синхронизация с hooks.py v4.0 и TURBO_RULES v4.0:
##   - veo3_* → wan_* (Veo3 устарел, используем Wan2.2 I2V)
##   - vizor_visual.key_frames: video_path, self_assessment (новые поля)
##   - mimi_sound: расширена структурой audio-путей
##   - t5_deliverables: veo3_prompts → wan_clips
##   - Добавлен self-review этап A03

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
| A05 | T5 Финализатор | `thumbnail`, `final_dna` | ВСЁ |

**Ключи которые hooks.py пишет самостоятельно** (агенты не трогают):
- `vizor_visual` ← hooks.py добавляет `path`, `video_path`, `quality_score`, `quality`, `self_assessment`
- `mimi_sound` ← hooks.py добавляет `music_path`, `sfx_list[*].sfx_path`, `vo_lines[*].vo_path`
- `t5_deliverables` ← hooks.py собирает после A05

---

## ПАРАЛЛЕЛЬНЫЙ ЗАПУСК

A02 и A03 работают **параллельно**.
A04 ждёт обоих. Порядок: A01 → (A02 ∥ A03) → A04 → A05.

⚠️ A03 вызывается **дважды**:
- Вызов 1: агент пишет промпты → hooks.py генерирует картинки → кладёт в `state["vision_images"]`
- Вызов 2: агент видит картинки → пишет `self_assessment` → hooks.py применяет вердикты → запускает Wan2.2

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

### `mimi_sound` ⚠️ hooks.py добавляет audio-пути после генерации
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
  "sfx_map": [
    {
      "segment": "0-1.5s",
      "sfx": "whoosh",
      "purpose": "строка"
    }
  ],
  "beat_map": [
    {
      "time_sec": 0.0,
      "beat": "DROP",
      "edit_note": "строка"
    }
  ],
  "voiceover": {
    "needed": true,
    "tone": "строка",
    "pace": "строка"
  },
  "suno_prompt": "ТОЛЬКО английский",
  "music_path": null,
  "sfx_list": [],
  "vo_lines": []
}
```
⚠️ `suno_prompt` — только английский. hooks.py передаёт в ElevenLabs.
⚠️ `music_path`, `sfx_list[*].sfx_path`, `vo_lines[*].vo_path` — агент ставит null/[]. hooks.py заполнит.
⚠️ `sfx_map` — hooks.py преобразует в `sfx_list` с реальными путями.

---

### `vizor_visual` ⚠️ hooks.py добавляет пути и self_assessment после генерации
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
      "shot_type": "close-up",
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
      "self_assessment": null
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
⚠️ `path`, `video_path`, `quality_score`, `quality`, `self_assessment` — агент ставит `null`. hooks.py заполнит.
⚠️ `ref_ids` — только asset_id из `stella_strategy.selected_assets`.

---

### `postpro`
```json
{
  "edit_plan": [
    {
      "segment": "0-1.5s",
      "timecode_in": "0.0",
      "timecode_out": "1.5",
      "transition": "строка",
      "retention_note": "строка",
      "loop_point": false,
      "beat_sync": "строка"
    }
  ],
  "captions": [
    {
      "segment": "0-1.5s",
      "timecode_in": "0.0",
      "timecode_out": "1.5",
      "text": "строка",
      "style": "строка",
      "animation": "строка",
      "accent_word": "строка"
    }
  ],
  "retention_strategy": {
    "peak_moment": "строка",
    "loop_point": "строка",
    "open_loop": "строка",
    "easter_egg": "строка"
  },
  "loop": {
    "last_frame": "строка",
    "first_frame": "строка",
    "connection": "строка",
    "seamless_score": "X/10"
  },
  "postpro_notes": "строка"
}
```

---

### `thumbnail` ⚠️ hooks.py добавляет `path`, `quality_score`, `quality`
```json
{
  "concept": "строка",
  "variant_a": {
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
⚠️ `concept` — на уровне `thumbnail`, не внутри вариантов.

---

### `final_dna`
```json
{
  "project_id": "строка",
  "platform": "строка",
  "duration_sec": 0,
  "key_frames_count": 0,
  "clips_count": 0,
  "format": "9:16",
  "viral_score": 0.0,
  "style_tags": ["строка"],
  "best_practices": ["строка"],
  "avoid_next": ["строка"],
  "client_feedback": "строка"
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
    "sfx_list": [{"prompt", "sfx_path", "segment", "timing_sec"}],
    "vo_lines": [{"text", "vo_path", "segment", "timing_sec"}]
  },
  "captions": {},
  "publication": {}
}
```
⚠️ ~~`veo3_prompts`~~ → `wan_clips`. Переименовано в v2.0.
⚠️ Агенты этот ключ не пишут.

---

## ПРАВИЛА КОТОРЫЕ НЕЛЬЗЯ НАРУШАТЬ

| # | Правило |
|---|---------|
| 1 | Ключ агента — строго из этой таблицы |
| 2 | `banana_prompt`, `wan_motion_prompt`, `suno_prompt` — ТОЛЬКО английский |
| 3 | Формат ВСЕГДА `9:16` |
| 4 | `ref_ids` — только реальные asset_id из `stella_strategy.selected_assets` |
| 5 | `path`, `video_path`, `quality_score`, `quality`, `self_assessment` — агент ставит `null` |
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
| 16 | A03 вызывается дважды: Этап 1 (промпты) → Этап 2 (self-review) |

---

## ИЗМЕНЕНИЯ v2.0 vs v1.0

| Что | v1.0 | v2.0 |
|-----|------|------|
| Анимационные поля | `veo3_prompt`, `veo3_camera_motion`, `veo3_duration_sec` | `wan_motion_prompt`, `wan_camera_move`, `wan_duration_sec` |
| `vizor_visual` новые поля | — | `video_path`, `self_assessment` |
| `mimi_sound` новые поля | — | `music_path`, `sfx_list`, `vo_lines` |
| `t5_deliverables` | `veo3_prompts[]` | `wan_clips[]`, `audio{}` |
| A03 вызовов | 1 | 2 (промпты + self-review) |
| ОТК картинок | Gemini score | vision_client PASS/REJECT |
| Выход | JSON-пакет | final.mp4 |

---

*TURBO v2.0 | Контракт ключей | 2026-06-02*
*Синхронизирован с: hooks.py v4.0, TURBO_RULES v4.0, A03 prompt v4.0*
