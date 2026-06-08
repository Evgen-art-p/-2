# КОНТРАКТ КЛЮЧЕЙ — CLIPMAKERS v1.0
## studio/modules/clipmakers/CHAIN_CONTRACT.md
##
## Это ЕДИНСТВЕННЫЙ источник правды по ключам chain_data.
## Если агент пишет ключ не из этого списка — ошибка.
## Если агент читает ключ не из этого списка — ошибка.
##
## v1.0 — первая живая версия, Спринт 40
## Цех: Музыкальный клип (предпродакшн-план, не реальная съёмка)
## 12 агентов · 3 фазы · hard_stop после A03 (Виктор)

---

## СВОДНАЯ ТАБЛИЦА

| Агент | Пишет | Читает |
|-------|-------|--------|
| A01 Вайб Винни | `vinnie_concept`, `history_dna` | `master_brief`, `history_dna` |
| A02 Ричи Ритм | `richi_sync` | `master_brief`, `vinnie_concept`, `history_dna` |
| A03 Стори Стив | `steve_storyboard` | `master_brief`, `vinnie_concept`, `richi_sync`, `history_dna` |
| **Виктор (резидент)** | `victor_critique` | `master_brief`, `vinnie_concept`, `richi_sync`, `steve_storyboard` |
| A04 Лока Лотти | `lottie_locations` | `master_brief`, `vinnie_concept`, `richi_sync`, `steve_storyboard` |
| A05 Стелла Стайл | `stella_artdir` | `master_brief`, `vinnie_concept`, `richi_sync`, `steve_storyboard`, `lottie_locations` |
| A06 Гимбал Гас | `gus_camera` | `master_brief`, `vinnie_concept`, `richi_sync`, `steve_storyboard`, `lottie_locations`, `stella_artdir` |
| A07 Люмен Люк | `luke_lighting` | `master_brief`, `vinnie_concept`, `stella_artdir`, `lottie_locations`, `gus_camera` |
| A08 Дрон Дэн | `dan_aerial` | `master_brief`, `vinnie_concept`, `richi_sync`, `steve_storyboard`, `lottie_locations`, `gus_camera`, `luke_lighting` |
| A09 Лютер Лут | `luther_color` | `master_brief`, `vinnie_concept`, `stella_artdir`, `luke_lighting`, `gus_camera`, `dan_aerial` |
| A10 Джиджи Глитч | `gigi_vfx` | `master_brief`, `vinnie_concept`, `richi_sync`, `steve_storyboard`, `stella_artdir`, `gus_camera`, `luther_color` |
| A11 Бьюти Белла | `bella_retouch` | `master_brief`, `vinnie_concept`, `stella_artdir`, `luther_color`, `gigi_vfx` |
| A12 Рендер Рекс | `rex_qa`, `deliverables`, `final_dna`, `history_dna` | ВСЁ |

**Сквозные ключи** (`{{inherit}}`): `master_brief`, `history_dna`

---

## СТРУКТУРЫ КЛЮЧЕЙ

### `vinnie_concept`
```json
{
  "track_analysis": {
    "bpm": "число или null",
    "structure": "intro → verse → chorus...",
    "key_moments": ["дроп 0:48", "бридж 2:12"],
    "mood_map": {
      "intro": "настроение",
      "verse": "настроение",
      "chorus": "настроение"
    }
  },
  "concept": {
    "clip_type": "performance | narrative | concept | hybrid | fashion_mood",
    "idea": "одно предложение",
    "visual_metaphor": "что символизирует",
    "emotional_arc": "от X к Y"
  },
  "world": {
    "locations": ["локация 1", "локация 2"],
    "palette": ["#hex1", "#hex2", "#hex3"],
    "era_style": "описание",
    "atmosphere": "одно слово"
  },
  "energy_map": {
    "intro":      { "level": 3, "visual": "что видим" },
    "verse_1":    { "level": 5, "visual": "что видим" },
    "pre_chorus": { "level": 7, "visual": "что видим" },
    "chorus":     { "level": 10, "visual": "что видим" },
    "verse_2":    { "level": 5, "visual": "что видим" },
    "bridge":     { "level": 6, "visual": "что видим" },
    "final":      { "level": 9, "visual": "что видим" },
    "outro":      { "level": 2, "visual": "что видим" }
  }
}
```
⚠️ `energy_map` — ОБЯЗАТЕЛЕН. Без него A02 (Ричи) не может построить таймкод-карту.
⚠️ `clip_type` — одно из пяти значений. Не придумывать новые.

---

### `richi_sync`
```json
{
  "timecode_map": [
    {
      "time": "0:00-0:12",
      "part": "intro",
      "bars": 4,
      "energy": 3,
      "edit_pace": "slow | medium | fast",
      "transition_type": "fade | hard_cut | whip_pan | morph"
    }
  ],
  "sync_points": [
    {
      "time": "0:48",
      "type": "drop | breakdown | buildup | last_beat",
      "visual_action": "описание визуального события"
    }
  ],
  "lipsync_map": {
    "mandatory": ["verse_1", "verse_2"],
    "optional": ["chorus"],
    "cutaway": ["bridge"]
  }
}
```
⚠️ Если BPM не задан в `master_brief` — писать `"bpm_note": "определить на площадке"` в `vinnie_concept.track_analysis`.
⚠️ `lipsync_map` обязателен если в треке есть вокал. Если нет вокала — `"lipsync_map": null`.

---

### `steve_storyboard`
```json
{
  "scenes": [
    {
      "scene_id": 1,
      "time": "0:00—0:12",
      "part": "intro",
      "frames": [
        {
          "frame_id": 1,
          "timecode": "0:00",
          "shot_size": "EWS | WS | MS | CU | ECU",
          "angle": "описание",
          "camera_move": "tilt_down | dolly | steadicam | static | crane",
          "subject": "что в кадре",
          "action": "что происходит",
          "mood": "настроение"
        }
      ]
    }
  ],
  "hero_shots": [
    {
      "time": "0:48",
      "purpose": "youtube_cover | poster | reels_preview | emotional_peak | vfx_hero",
      "description": "описание кадра"
    }
  ],
  "transitions": [
    {
      "from": "intro",
      "to": "verse_1",
      "type": "hard_cut | match_cut | whip_pan | morph | fade",
      "sync_point": "0:12"
    }
  ]
}
```
⚠️ `hero_shots` — МИНИМУМ 3, МАКСИМУМ 5. Без них нет маркетинга клипа.
⚠️ `camera_move` у Стива — рекомендация режиссёра. Финальное слово за A06 (Гимбал Гас).

---

### `victor_critique` ⚠️ HARD-STOP — без APPROVED/APPROVED_WITH_CONCERNS A04+ не запускаются
```json
{
  "agent": "victor",
  "workshop": "clipmakers",
  "verdict": "APPROVED | APPROVED_WITH_CONCERNS | NEEDS_REWORK",
  "strong_points": ["что реально работает"],
  "blind_spots": ["где концепт предал потенциал", "где sync расходится со стори"],
  "sync_gap": "описание расхождения Ричи/Стива — или null",
  "critical_question": "один вопрос Шефу перед CONTINUE",
  "recommendation": "одна правка — самая важная"
}
```
⚠️ `verdict: "NEEDS_REWORK"` → хард-стоп. A04–A12 не запускаются.
⚠️ `verdict: "APPROVED" | "APPROVED_WITH_CONCERNS"` → Шеф нажимает ▶️ CONTINUE → A04 стартует.
⚠️ Виктор читает маску `clipmakers_hardstop.md` из `005_VICTOR/forge/masks/`.
⚠️ Виктор НЕ проверяет техническое — только концепт, sync, сториборд, метафору.

---

### `lottie_locations`
```json
{
  "locations": [
    {
      "scene": "intro",
      "type": "exterior | interior | studio",
      "place": "описание места",
      "light": "golden_hour | artificial | natural | practical",
      "time": "17:00-19:00 | любое",
      "plan_b": "запасная локация"
    }
  ],
  "logistics": {
    "total_locations": 3,
    "shooting_order": ["студия", "заброшка", "крыша"],
    "merge_scenes": { "verse_1": "bridge" }
  },
  "risks": [
    { "location": "крыша", "risk": "погода", "mitigation": "хромакей" }
  ]
}
```
⚠️ Для КАЖДОЙ сцены — основная локация + `plan_b`.
⚠️ `shooting_order` — по логистике (маршрут), не по хронологии клипа.

---

### `stella_artdir`
```json
{
  "visual_language": {
    "style": "streetwear | haute_couture | vintage | minimal | grunge | editorial",
    "palette": ["#hex1", "#hex2", "#hex3", "#hex4", "#hex5"],
    "textures": ["бетон", "шёлк", "металл"],
    "keywords": "для AI-генерации, только английский"
  },
  "outfit_plan": [
    {
      "look": 1,
      "scene": "verse_1",
      "description": "описание образа",
      "colors": ["#hex"],
      "material": "материал",
      "mood": "настроение"
    }
  ],
  "props": [
    { "item": "предмет", "scene": "chorus", "purpose": "усиливает метафору" }
  ],
  "moodboard_prompt": "словесный мудборд для AI, только английский"
}
```
⚠️ Палитра — РОВНО 5 цветов с HEX.
⚠️ `moodboard_prompt` и `keywords` — ТОЛЬКО английский (для AI-генерации).
⚠️ Каждый outfit привязан к конкретной сцене, не абстрактно.

---

### `gus_camera`
```json
{
  "camera_map": [
    {
      "frame_id": 1,
      "timecode": "0:00",
      "equipment": "drone | gimbal | steadicam | handheld | tripod | crane",
      "movement": "tilt_down | dolly | tracking | static | crash_zoom | orbit",
      "speed": "slow | medium | fast",
      "fps": 24,
      "note": "описание"
    }
  ],
  "speed_ramps": [
    {
      "timecode": "0:48",
      "type": "crash_zoom | slow_motion | time_lapse | ramp",
      "from_fps": 60,
      "to_fps": 24
    }
  ],
  "ai_prompts": [
    { "frame_id": 1, "prompt": "только английский, движение + оборудование + атмосфера" }
  ]
}
```
⚠️ FPS обязателен для каждого кадра.
⚠️ `ai_prompts` — ТОЛЬКО английский.
⚠️ Speed-ramp только на `sync_points` из `richi_sync` — не случайно.

---

### `luke_lighting`
```json
{
  "light_map": [
    {
      "scene": "intro",
      "location": "крыша",
      "scheme": "backlight | rembrandt | split | butterfly | rim | ring | low_key | high_key",
      "color": "golden | cold_white | neon_blue | warm | neutral",
      "mood": "настроение",
      "practical": "городские огни | фонарь | свеча | LED"
    }
  ],
  "artist_schemes": [
    {
      "scene": "verse_1",
      "scheme": "rembrandt",
      "key": "45° справа, холодный",
      "fill": "минимальный",
      "rim": "контровой сзади",
      "practical": "фонарь в кадре"
    }
  ],
  "effects": [
    { "timecode": "0:48", "type": "strobe | flicker | fade_to_black | pulse", "detail": "описание" }
  ],
  "ai_prompts": [
    { "scene": "verse_1", "prompt": "только английский, схема + температура + настроение" }
  ]
}
```
⚠️ Световая карта обязательна для КАЖДОЙ сцены.
⚠️ Световые эффекты (`strobe`, `fade_to_black`) — ТОЛЬКО на `sync_points`.
⚠️ Схема света для артиста привязана к `outfit_plan` Стеллы.

---

### `dan_aerial`
```json
{
  "drone_needed": {
    "mandatory": ["intro", "outro"],
    "optional": ["chorus"],
    "not_needed": ["verse", "bridge"]
  },
  "drone_map": [
    {
      "shot_id": "D1",
      "timecode": "0:00",
      "flight_type": "reveal | orbit | tracking | pull_away | dive | top_down | fly_through",
      "altitude": "50m → 10m",
      "speed": "slow | medium | fast",
      "direction": "descending | ascending | lateral | circular",
      "purpose": "описание цели"
    }
  ],
  "ai_prompts": [
    { "shot_id": "D1", "prompt": "только английский, высота + направление + атмосфера" }
  ],
  "constraints": [
    { "type": "no_fly_zone | weather | safety | battery", "detail": "описание" }
  ]
}
```
⚠️ Если дрон не нужен ни в одной сцене — писать `"drone_map": []` и объяснять в `drone_needed`.
⚠️ Каждый дрон-шот привязан к таймкоду и sync-point.

---

### `luther_color`
```json
{
  "grade_style": {
    "type": "teal_and_orange | desaturated | crushed_blacks | film_emulation | high_sat | monochrome",
    "contrast": "high | medium | low",
    "saturation": "oversaturated | normal | muted",
    "shadows": "crushed_to_blue | lifted | clean_black",
    "highlights": "warm_golden | blown | clean_white",
    "film_grain": true
  },
  "scene_grades": [
    {
      "scene": "intro",
      "temperature": "5500K",
      "shadows": "deep_blue",
      "midtones": "golden",
      "highlights": "soft",
      "saturation": "low",
      "mood": "описание"
    }
  ],
  "skin_tone": {
    "base": "warm_neutral | cool | neutral",
    "per_scene": {},
    "forbidden": ["green", "grey", "dead"]
  },
  "color_transitions": [
    { "timecode": "0:48", "type": "hard | gradual", "from": "cold", "to": "warm" }
  ],
  "ai_prompts": [
    { "scope": "general | verse | chorus | bridge", "prompt": "только английский" }
  ]
}
```
⚠️ Тон кожи СВЯЩЕНЕН — не жертвовать ради стиля ни при каких обстоятельствах.
⚠️ Один стиль грейда на весь клип (единство).
⚠️ Цветовые переходы привязаны к `sync_points`.

---

### `gigi_vfx`
```json
{
  "vfx_audit": {
    "mandatory": ["intro", "chorus"],
    "enhance": ["bridge", "verse_2"],
    "not_needed": ["verse_1", "outro"]
  },
  "vfx_map": [
    {
      "scene": "chorus",
      "timecode": "0:48",
      "effect": "particles | double_exposure | glitch | fog | light_leak | morph",
      "type": "digital | practical | cgi",
      "purpose": "зачем этот эффект",
      "complexity": "low | medium | high",
      "sync_point": true
    }
  ],
  "tech_specs": [
    {
      "effect": "double_exposure",
      "method": "screen blend, чёрный фон",
      "duration": "8 тактов",
      "sync": "замедление бриджа"
    }
  ],
  "ai_prompts": [
    { "effect": "particles", "prompt": "только английский, технически точный" }
  ],
  "forbidden": ["fire_effects", "3d_titles"]
}
```
⚠️ Каждый VFX требует обоснования (`purpose`). Без обоснования — не ставить.
⚠️ VFX синхронизируется с `sync_points` из `richi_sync`.
⚠️ `forbidden` — список ЗАПРЕЩЁННЫХ эффектов для этого клипа обязателен.

---

### `bella_retouch`
```json
{
  "retouch_style": {
    "approach": "natural | glamour | grunge | editorial",
    "skin": "preserve_texture | light_smoothing | dodge_burn",
    "eyes": "enhance_catchlight | as_is",
    "rule": "если видно ретушь — переделывать"
  },
  "retouch_map": [
    {
      "scene": "verse_1",
      "shot_size": "CU | ECU | MS",
      "priority": "high | medium | low",
      "actions": ["skin_texture", "eyes", "lips"],
      "forbidden": ["remove_moles", "plastic_skin"]
    }
  ],
  "hero_frames": [
    {
      "timecode": "0:48",
      "purpose": "youtube_cover | poster | reels_preview",
      "retouch_level": "full",
      "actions": ["dodge_burn", "eye_enhance", "hair_cleanup"]
    }
  ],
  "formats": [
    { "platform": "youtube", "aspect": "16:9", "resolution": "3840x2160" },
    { "platform": "reels", "aspect": "9:16", "resolution": "1080x1920" },
    { "platform": "thumbnail", "aspect": "16:9", "resolution": "1280x720" }
  ],
  "ai_prompts": [
    { "scope": "skin | hero", "prompt": "только английский" }
  ]
}
```
⚠️ Ретушь НЕВИДИМАЯ — принцип для всего цеха.
⚠️ Список форматов — ОБЯЗАТЕЛЕН (минимум: youtube + reels + thumbnail).
⚠️ `hero_frames` совпадают с `hero_shots` Стива (A03) по таймкодам.

---

### `rex_qa` + `deliverables` + `final_dna`

```json
{
  "rex_qa": {
    "chain_audit": {
      "A01": "complete | missing",
      "A02": "complete | missing",
      "A03": "complete | missing",
      "A04": "complete | missing",
      "A05": "complete | missing",
      "A06": "complete | missing",
      "A07": "complete | missing",
      "A08": "complete | missing",
      "A09": "complete | missing",
      "A10": "complete | missing",
      "A11": "complete | missing"
    },
    "tech_checklist": {
      "lipsync_plan": "pass | fail | na",
      "sync_points_covered": "pass | fail",
      "hero_shots_ready": "pass | fail",
      "formats_complete": "pass | fail",
      "color_unity": "pass | fail",
      "vfx_justified": "pass | fail",
      "retouch_style_consistent": "pass | fail"
    },
    "issues": [
      {
        "id": 1,
        "issue": "описание",
        "severity": "critical | medium | minor",
        "assigned_to": "A01_vinnie | A02_richi | ... | A11_bella",
        "status": "open | fixed"
      }
    ],
    "verdict": "APPROVED | CONDITIONAL | REJECTED",
    "chain_status": "APPROVED | FAILED"
  },

  "deliverables": {
    "project_id": "строка",
    "clip_type": "тип из vinnie_concept",
    "concept_summary": "одно предложение из Винни",
    "storyboard_frames_count": 0,
    "hero_shots": [ ],
    "locations": [ ],
    "outfit_looks_count": 0,
    "vfx_effects": [ ],
    "delivery_package": [
      "SHOOTING_PLAN.pdf",
      "STORYBOARD.pdf",
      "MOODBOARD.pdf",
      "LOCATION_BRIEF.pdf",
      "TECH_SPEC.pdf",
      "PROJECT_METADATA.json"
    ]
  },

  "final_dna": {
    "project_id": "строка",
    "clip_type": "тип",
    "genre": "жанр",
    "style": "стиль арт-дирекшна",
    "locations_used": [],
    "vfx_used": [],
    "grade_style": "тип грейда",
    "verdict": "APPROVED | CONDITIONAL | REJECTED",
    "date": "дата"
  }
}
```
⚠️ `chain_status` — ОБЯЗАТЕЛЬНОЕ поле. Движок читает его.
⚠️ `history_dna` обновляет ТОЛЬКО A12 Рендер Рекс.
⚠️ A12 вызывает `billing_ledger.record()` и обновляет `strategy_registry.json` после каждого рана (Закон замыкания петли, Спринт 38).
⚠️ `outcome_signal` = null — реальные метрики после публикации заполняет Демон.

---

## ПРАВИЛА КОТОРЫЕ НЕЛЬЗЯ НАРУШАТЬ

| # | Правило |
|---|---------|
| 1 | Ключ агента — строго из этой таблицы. Самодеятельность = ошибка контракта |
| 2 | `moodboard_prompt`, `keywords`, все `ai_prompts` — ТОЛЬКО английский |
| 3 | `hero_shots` у Стива и `hero_frames` у Беллы — одни и те же таймкоды |
| 4 | `palette` у Стеллы — РОВНО 5 цветов с HEX |
| 5 | `history_dna` обновляет ТОЛЬКО A12 Рекс |
| 6 | `energy_map` обязателен у Винни — без него цепочка встаёт |
| 7 | `lipsync_map` обязателен если вокал есть; null если нет |
| 8 | VFX у Джиджи — ТОЛЬКО с полем `purpose`. Без обоснования — не ставить |
| 9 | Speed-ramp и световые эффекты — ТОЛЬКО на `sync_points` из Ричи |
| 10 | Тон кожи у Лютера — не жертвовать ради стиля ни при каких обстоятельствах |
| 11 | `victor_critique` — ХАРД-СТОП. `NEEDS_REWORK` блокирует A04–A12 полностью |
| 12 | Виктор читает маску `clipmakers_hardstop.md` — без неё он работает вслепую |
| 12 | `forbidden` у Джиджи — список запретов для клипа обязателен |
| 13 | `formats` у Беллы — минимум три: youtube + reels + thumbnail |
| 14 | Ретушь Беллы — НЕВИДИМАЯ. Видно = переделывать |
| 15 | Дрон у Дэна — только когда масштаб добавляет смысл, не "для красоты" |
| 16 | `shooting_order` у Лотти — по логистике (маршрут), не по хронологии клипа |
| 17 | A12 вызывает `billing_ledger.record()` и `strategy_registry` после рана |
| 18 | `outcome_signal` = null от A12. Демон заполняет после публикации |

---

## КАК ПРОВЕРИТЬ СВОЙ ПРОМТ

1. **INPUT** — все ключи которые агент читает, есть в колонке "Читает"?
2. **my_output** — структура совпадает со структурой выше?
3. **chain_data** — агент пишет только свой ключ, остальное `{{inherit}}`?
4. **ai_prompts** — все промпты на английском?
5. **sync привязка** — эффекты и speed-ramp привязаны к `sync_points` Ричи?

---

*CLIPMAKERS v1.0 | Контракт ключей | Спринт 40 | 2026-06-05*
*12 агентов — предпродакшн-план музыкального клипа. Не реальная съёмка в пайплайне.*
*Синхронизирован с: WORKSHOP_STANDARD.md, cartridge.py, billing_ledger.py, ministry.py*
