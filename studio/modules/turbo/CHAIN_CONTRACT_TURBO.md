# КОНТРАКТ КЛЮЧЕЙ — TURBO v1.0
## studio/modules/turbo/CHAIN_CONTRACT.md
##
## Это ЕДИНСТВЕННЫЙ источник правды по ключам chain_data цеха TURBO.
## Если агент пишет ключ не из этого списка — ошибка.
## Если агент читает ключ не из этого списка — ошибка.
##
## Редактировать только вместе с TURBO_RULES.md.
## Не копировать в другие цеха.
##
## v1.0 — первичная синхронизация с hooks.py v3.2 и TURBO_RULES v3.1:
##   - Задокументированы все реальные ключи которые читает/пишет hooks.py
##   - Зафиксирована двойная нотация: T-имена в промптах, A-нотация в системе
##   - vizor_visual.key_frames: добавлены veo3-поля (читает hooks.py при сборке)
##   - t5_deliverables: ключ который hooks.py пишет в chain_data (не путать с my_output)
##   - quality_score / quality: поля добавляемые hooks.py после генерации

---

## ⚠️ ДВОЙНАЯ НОТАЦИЯ — ЧИТАТЬ ОБЯЗАТЕЛЬНО

| Уровень | Нотация | Где используется |
|---------|---------|-----------------|
| Кодовые имена персонажей | **T1–T5** | Промпты агентов, chain_data ключи, TURBO_RULES |
| Системные ID | **A01–A05** | Папки на диске, worker_id в pipeline, manifest.json, hooks.py |

Пример: агент называет себя T3 Визором в тексте, pipeline находит его по `worker_id == "A03"`.
Ключи chain_data — по T-имени (т.е. `vizor_visual`, не `a03_visual`).

---

## СВОДНАЯ ТАБЛИЦА

| worker_id | Агент | Пишет | Читает |
|-----------|-------|-------|--------|
| A01 | T1 Стелла | `stella_strategy` | `master_brief` |
| A02 | T2 Мими | `mimi_sound` | `master_brief`, `stella_strategy` |
| A03 | T3 Визор | `vizor_visual` | `master_brief`, `stella_strategy` |
| A04 | T4 Постпро | `postpro` | `master_brief`, `stella_strategy`, `mimi_sound`, `vizor_visual` |
| A05 | T5 Финализатор | `thumbnail`, `final_dna` | ВСЁ |

**Сквозные ключи** (наследуют все агенты через `{{inherit}}`):
- `master_brief`
- `stella_strategy` ← наследуют T2, T3, T4, T5

**Ключи которые hooks.py пишет в chain_data самостоятельно** (агенты не трогают):
- `vizor_visual` ← перезаписывает hooks.py после генерации кадров A03 (добавляет `path`, `quality_score`, `quality`)
- `t5_deliverables` ← hooks.py собирает и пишет после генерации обложек A05

---

## ПАРАЛЛЕЛЬНЫЙ ЗАПУСК

A02 и A03 работают **параллельно** — оба читают `stella_strategy`, не читают друг друга.
A04 ждёт обоих. Порядок: A01 → (A02 ∥ A03) → A04 → A05.

---

## СТРУКТУРЫ КЛЮЧЕЙ

### `stella_strategy`
```json
{
  "project_id": "TURBO_YYYYMMDD_XXX",
  "script": {
    "segments": [
      {
        "segment": 1,
        "timing": "0–1.5s",
        "purpose": "hook",
        "description": "строка",
        "dialogue": "строка",
        "visual_note": "строка"
      }
    ],
    "total_duration_sec": 30
  },
  "selected_assets": ["asset_id из каталога — максимум 6"],
  "seo_brief": {
    "title": "строка",
    "keywords": ["строка"],
    "hook_text": "строка"
  },
  "platform": "строка",
  "style_tags": ["строка"],
  "strategy_notes": "строка"
}
```
⚠️ `project_id` задаёт T1 Стелла (A01). Формат: `TURBO_YYYYMMDD_XXX`.
⚠️ `total_duration_sec` — источник истины о хронометраже для всех агентов.
⚠️ `selected_assets` — только реальные asset_id из каталога, максимум 6.

### `mimi_sound`
```json
{
  "beat_map": [
    {
      "segment": 1,
      "timecode_in": "0.0",
      "timecode_out": "1.5",
      "track_mood": "строка",
      "bpm": 0,
      "sfx": ["строка"],
      "music_cue": "строка",
      "volume_note": "строка"
    }
  ],
  "suno_prompt": "строка (английский)",
  "master_mix_note": "строка"
}
```
⚠️ `suno_prompt` — только английский.

### `vizor_visual` ⚠️ hooks.py добавляет `path`, `quality_score`, `quality` после генерации
```json
{
  "format": "9:16",
  "platform": "строка",
  "key_frames": [
    {
      "segment": 1,
      "purpose": "hook",
      "banana_prompt": "ТОЛЬКО английский",
      "ref_ids": ["asset_id из selected_assets"],
      "composition": "строка",
      "focus_point": "строка",
      "veo3_prompt": "ТОЛЬКО английский",
      "veo3_camera_motion": "строка",
      "veo3_duration_sec": 3,
      "path": null,
      "quality_score": null,
      "quality": null
    }
  ],
  "visual_notes": "строка"
}
```
⚠️ Поле кадров — `key_frames` (не frames, не shots).
⚠️ Формат ВСЕГДА `9:16` — горизонтальных кадров в этом цехе не существует.
⚠️ `path`, `quality_score`, `quality` — агент ставит `null`. hooks.py заполнит.
⚠️ `veo3_prompt`, `veo3_camera_motion`, `veo3_duration_sec` — обязательны: hooks.py собирает `veo3_prompts` в deliverables из этих полей.
⚠️ `ref_ids` — только asset_id из `stella_strategy.selected_assets`. Не выдумывать.

### `postpro`
```json
{
  "edit_plan": [
    {
      "segment": 1,
      "timecode_in": "0.0",
      "timecode_out": "1.5",
      "transition": "строка",
      "retention_note": "строка",
      "loop_point": false
    }
  ],
  "captions": [
    {
      "timecode_in": "0.0",
      "timecode_out": "1.5",
      "text": "строка",
      "style": "строка"
    }
  ],
  "retention_strategy": {
    "peak_moment": "строка",
    "loop_point": "строка",
    "open_loop": "строка"
  },
  "postpro_notes": "строка"
}
```

### `thumbnail` ⚠️ hooks.py добавляет `path`, `quality_score`, `quality` после генерации
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
⚠️ Thumbnail всегда в двух вариантах (A/B) — hooks.py генерирует оба.
⚠️ `ref_ids` обязательны для обоих вариантов.
⚠️ `concept` — на уровне `thumbnail`, не дублируется внутри вариантов.
⚠️ `path`, `quality_score`, `quality` — агент ставит `null`. hooks.py заполнит.

### `final_dna`
```json
{
  "project_id": "строка",
  "platform": "строка",
  "duration_sec": 0,
  "key_frames_count": 0,
  "format": "9:16",
  "viral_score": 0.0,
  "style_tags": ["строка"],
  "best_practices": ["строка"],
  "avoid_next": ["строка"],
  "client_feedback": "строка"
}
```
⚠️ `final_dna` пишет ТОЛЬКО T5 Финализатор (A05).

---

## КЛЮЧ КОТОРЫЙ ПИШЕТ ТОЛЬКО hooks.py

### `t5_deliverables` (пишет hooks.py в chain_data после A05 — агенты не трогают)
```json
{
  "project_id": "строка",
  "status": "ready_to_publish | incomplete",
  "thumbnail": {
    "variant_a": { "banana_prompt", "text_overlay", "emotion", "ref_ids", "style_tags", "path", "quality_score", "quality" },
    "variant_b": { "banana_prompt", "text_overlay", "emotion", "ref_ids", "style_tags", "path", "quality_score", "quality" }
  },
  "key_frames": [
    {
      "segment", "purpose", "prompt", "ref_ids",
      "format": "9:16",
      "path", "quality_score", "quality"
    }
  ],
  "veo3_prompts": [
    {
      "segment", "camera", "duration", "prompt", "ref_ids"
    }
  ],
  "sound": {},
  "voice_over": {},
  "music": {},
  "captions": {},
  "publication": {}
}
```
⚠️ Этот ключ в my_output агента не пишется. Только hooks.py.

---

## ПРАВИЛА КОТОРЫЕ НЕЛЬЗЯ НАРУШАТЬ

| # | Правило |
|---|---------|
| 1 | Ключ агента — строго из этой таблицы. Никаких `vizor_frames`, `stella_strat`, `mimi_audio` |
| 2 | `banana_prompt`, `veo3_prompt`, `suno_prompt` — ТОЛЬКО английский |
| 3 | Формат ВСЕГДА `9:16` — горизонтальных кадров в этом цехе не существует |
| 4 | `ref_ids` — только реальные asset_id из `stella_strategy.selected_assets` |
| 5 | `path`, `quality_score`, `quality` — агент ставит `null`. Заполняет hooks.py |
| 6 | `final_dna` и `t5_deliverables` пишет ТОЛЬКО T5 Финализатор / hooks.py |
| 7 | `project_id` задаёт ТОЛЬКО T1 Стелла через `stella_strategy.project_id` |
| 8 | `total_duration_sec` в `stella_strategy.script` — источник истины для хронометража |
| 9 | `vizor_visual.key_frames` — содержат veo3-поля (`veo3_prompt`, `veo3_camera_motion`, `veo3_duration_sec`). Без них hooks.py не соберёт `veo3_prompts` в deliverables |
| 10 | `thumbnail` — всегда два варианта `variant_a` и `variant_b`. Один вариант — ошибка |
| 11 | worker_id в коде и manifest — A-нотация (A01–A05). В промптах и chain_data ключах — T-имена |
| 12 | JSON ВСЕГДА ПЕРВЫМ — до любого Markdown текста |
| 13 | T2 и T3 работают параллельно — не читают результаты друг друга |
| 14 | В chain_data писать `"{{inherit}}"` — не перечислять чужие ключи руками |

---

## ПРОТИВОРЕЧИЯ ЗАФИКСИРОВАННЫЕ ПРИ АУДИТЕ v1.0

Найдены при сравнении TURBO_RULES v3.1 ↔ hooks.py v3.2. Требуют правки в коде или правилах:

| # | Что | Где расходится | Статус |
|---|-----|----------------|--------|
| 1 | `t5_deliverables` | hooks.py пишет этот ключ в chain_data (строка 383), но TURBO_RULES секция 2 называет его просто `deliverables`. Ключ нигде не был задокументирован | ✅ Зафиксирован в этом контракте |
| 2 | `vizor_visual` в chain_data | hooks.py (строка 223) явно пишет `vizor_visual` в chain_data через `_write_chain_key`. A05 читает оттуда же (строка 298). Но в TURBO_RULES это не было явно прописано | ✅ Зафиксирован в этом контракте |
| 3 | `veo3_prompt`, `veo3_camera_motion`, `veo3_duration_sec` | hooks.py читает эти поля из `vizor_visual.key_frames[]` (строки 330–336) при сборке deliverables, но структура нигде не была задокументирована. A03 мог не знать что их надо класть | ✅ Добавлены в структуру `vizor_visual` |
| 4 | `quality_score` / `quality` | hooks.py добавляет эти поля в кадры и обложки (строки 209–211, 283–285), но они не были в структурах. Агент не знал что писать в `path` | ✅ Добавлены в структуры, агент ставит `null` |
| 5 | Fallback `a01_strategy` в `_get_project_id` | hooks.py (строка 421) ищет `a01_strategy` как fallback, хотя стандартный ключ — `stella_strategy`. Безопасно, но не задокументировано | 🟡 Безопасный fallback, оставить в коде, знать команде |

---

## КАК ПРОВЕРИТЬ ПРОМТ АГЕНТА

Три вопроса перед сохранением:

1. **INPUT** — все ключи которые агент читает, есть в колонке "Читает" сводной таблицы?
2. **my_output** — структура совпадает со структурой выше? Ключ обёрнут (`"vizor_visual": { ... }`, не плоский)?
3. **chain_data** — агент пишет только свой ключ, остальное `{{inherit}}`?

Если хотя бы одно "нет" — промт не готов.

---

## ОТЛИЧИЯ ОТ VIDEO_LONG И VIDEO_SHORTS

| Параметр | TURBO | VIDEO_LONG | VIDEO_SHORTS |
|----------|-------|-----------|-------------|
| Агентов | 5 | 12 | ~8 |
| Параллельность | A02 ∥ A03 | нет | нет |
| Формат | 9:16 | 16:9 | 9:16 |
| Ключевые кадры | `vizor_visual.key_frames` | `eva_visuals.frames` | `vera_visual` |
| QA агент | T5 Финализатор / A05 | A04 Катя (ХАРД-СТОП) | Тэг Тони |
| Гейт | нет ХАРД-СТОПа | `katya_verdict` | `tony_verdict` |
| Обложки | T5 / A05 → `thumbnail` | A11 Трейси → `tracy_smm.thumbnail` | A11 Трейси |
| interaction_log | `interaction_log_turbo.jsonl` | `interaction_log_video_long.jsonl` | `interaction_log_video_shorts.jsonl` |
| Режимы | только TURBO | BIBLE + EPISODE | PILOT + EPISODE |
| project_id формат | `TURBO_YYYYMMDD_XXX` | из `adam_bible/episode` | из пилота |

---

*TURBO v1.0 | Контракт ключей | Спринт 19*
*Источник: TURBO_RULES v3.1 | Синхронизирован с hooks.py v3.2*
*Аудит: сверены TURBO_RULES ↔ hooks.py ↔ AGENT_WRITING_STANDARD v1.0*
