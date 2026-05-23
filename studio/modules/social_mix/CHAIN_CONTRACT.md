# КОНТРАКТ КЛЮЧЕЙ — SOCIAL_MIX v1.0
## studio/modules/social_mix/CHAIN_CONTRACT.md
##
## Это ЕДИНСТВЕННЫЙ источник правды по ключам chain_data SMM-цеха.
## Если агент пишет ключ не из этого списка — ошибка.
## Если агент читает ключ не из этого списка — ошибка.
##
## Редактировать только вместе с SM_RULES.md.
## Не копировать в другие цеха.
##
## v1.0 — первичный контракт, выведен из SM_RULES.md + hooks.py v3.0

---

## СВОДНАЯ ТАБЛИЦА

| Агент | Пишет (POST) | Пишет (PLAN) | Читает |
|-------|-------------|-------------|--------|
| A01 Костя | `kostya_analysis`, `history_dna` | то же | `master_brief` |
| A02 Никита | `nikita_trends` | то же | `kostya_analysis`, `history_dna` |
| A03 Макс | `max_story` | то же | `kostya_analysis`, `nikita_trends`, `history_dna` |
| A04 Глеб | `gleb_review` | то же | `kostya_analysis`, `nikita_trends`, `max_story` |
| A05 Алекс | `alex_layout` | — | `max_story`, `gleb_review` |
| A06 Эван | `evan_visual` | — | `alex_layout`, `max_story`, `history_dna` |
| A07 Сева | `seva_typography` | — | `evan_visual`, `alex_layout` |
| A08 Герман | `german_qa` | — | `evan_visual`, `seva_typography`, `alex_layout` |
| A09 Белла | `bella_engagement` | — | `max_story`, `evan_visual`, `german_qa` |
| A10 Тим | `tim_analytics` | — | `max_story`, `bella_engagement`, `history_dna` |
| A11 Федя | `fedya_inspection` | — | `evan_visual`, `bella_engagement`, `tim_analytics` |
| A12 Клавдия | `claudia_final`, `deliverables`, `final_dna`, `history_dna` | — | ВСЁ |

**Сквозные ключи** (наследуют все агенты через `{{inherit}}`):
- `master_brief`
- `history_dna`
- `run_type`

**Два режима:**
- `run_type: "social"` — полная цепочка A01→A12 (дефолт из manifest.json)
- `run_type: "content_plan"` — цепочка A01→A04, hooks.py останавливает после A04

⚠️ Значение `"social"` берётся из `manifest.run_type` если state не переопределил.
⚠️ PLAN-режим: UI обязан писать `state["run_type"] = "content_plan"` до запуска.
⚠️ SM_RULES называет режимы «POST» и «PLAN» — в коде это `"social"` и `"content_plan"`.

---

## СТРУКТУРЫ КЛЮЧЕЙ

### `history_dna` ← создаёт A01 Костя, финализирует A12 Клавдия

```json
{
  "project_id": "SM_YYYYMMDD_XXX",
  "mode": "post | content_plan",
  "run_type": "post | content_plan",
  "platform": "instagram | vk | telegram | universal",
  "viral_score": null,  ← заполняет Metrics Daemon после реального рана
  "learnings": "строка — заполняет Metrics Daemon через 24ч",
  "avoid_next": "строка — что не повторять"
}
```
A01 пишет `history_dna` целиком (начальная версия): `project_id`, `mode`, `run_type`, `platform`.
A12 перезаписывает `history_dna` с финальными данными: `status: PENDING`, `post_id: null`. Metrics Daemon дописывает `real_viral_score` позже.
Остальные агенты — только `{{inherit}}`, не трогают.

⚠️ Оба ключа `history_dna` должны быть в allowed keys своих агентов — иначе Таможня заблокирует.
   Контракт разрешает `history_dna` для A01 (WRITE) и A12 (WRITE) — см. сводную таблицу.

---

### `kostya_analysis`

```json
{
  "audience": {
    "archetype": "строка",
    "pain_points": ["строка"],
    "desires": ["строка"]
  },
  "visual_code": {
    "palette_hint": "строка",
    "style_hint": "строка"
  },
  "platform": "instagram | vk | telegram | universal",
  "psychology_notes": "строка"
}
```

---

### `nikita_trends`

```json
{
  "trend_hooks": ["строка"],
  "platform_spices": {
    "format_rec": "post | carousel | stories | reels",
    "timing": "строка",
    "vibe": "строка"
  },
  "trend_notes": "строка"
}
```

---

### `max_story`

```json
{
  "hook": {
    "text": "строка — первые 2-3 слова/секунды",
    "type": "вопрос | провокация | факт | боль",
    "why_it_works": "строка"
  },
  "conflict": "строка — один конфликт поста",
  "narrative": {
    "opening": "строка",
    "body": "строка",
    "resolution": "строка"
  },
  "content_format": "post | carousel | stories | reels",
  "funnel_stage": "TOFU | MOFU | BOFU",
  "script_notes": "строка"
}
```

---

### `gleb_review`

```json
{
  "content_check": {
    "passed": true,
    "issues": ["строка"]
  },
  "balance_check": {
    "passed": true,
    "notes": "строка"
  },
  "feasibility": {
    "passed": true,
    "notes": "строка"
  },
  "overall": "APPROVED | NEEDS_REVISION",
  "qa_notes": "строка"
}
```

⚠️ Нет `gleb_verdict` как отдельного ключа — нет гейта с ХАРД-СТОПом в этом цехе.
`overall` — рекомендация, не директива. Пайплайн продолжается в любом случае.
В PLAN-режиме остановка происходит через hooks.py по `worker_id == "A04"`, не по значению `overall`.

---

### `alex_layout`

```json
{
  "content_format": "post | carousel | stories | reels",
  "grid": "single | 3x3 | carousel_N",
  "archetype": "строка",
  "composition": {
    "type": "строка",
    "focal_point": "строка",
    "elements": ["строка"]
  },
  "slides": [
    {
      "slide_id": "s1",
      "layout_type": "строка",
      "content_zone": "строка",
      "visual_zone": "строка"
    }
  ],
  "layout_notes": "строка"
}
```

⚠️ A05 (Алекс) — единственный агент с нестандартным порядком вывода (JSON→Markdown по SM_RULES §7).
Парсер (`parse_agent_response`) игнорирует всё после закрывающего маркера — Markdown-комментарий
после JSON будет утерян. Рекомендуется привести к стандарту Markdown→JSON в следующей версии.

---

### `evan_visual` ⚠️ hooks.py добавляет поля после генерации

```json
{
  "prompt_positive": "ТОЛЬКО английский, 2-3 предложения",
  "prompt_negative": "ТОЛЬКО английский (обязателен если fedya_inspection.risk_score > 0.3)",
  "format": "4:5 | 9:16 | 1:1",
  "char_ref": "путь к файлу (опционально)",
  "style_ref": "путь к файлу (опционально)",
  "visual_notes": "строка",

  "← hooks.py добавляет после fal.ai генерации:": "",
  "image_path": "строка",
  "attempts": 0,
  "quality": "ok | fallback",
  "quality_score": 0,
  "quality_notes": "строка"
}
```

⚠️ Поле промпта — `prompt_positive` (не `prompt`, не `banana_prompt`).
⚠️ hooks.py: fallback `evan.get("prompt_positive") or evan.get("prompt", "")` — на переходный период.
⚠️ Формат выбирается по платформе из `kostya_analysis.platform`:

| Платформа | Формат |
|-----------|--------|
| `instagram` | `4:5` |
| `instagram_stories`, `stories`, `reels` | `9:16` |
| `vk` | `1:1` |
| `telegram` | `1:1` |
| `universal` | `4:5` |

Если поле `format` задано явно в `evan_visual` — hooks.py использует его, платформу игнорирует.

---

### `seva_typography`

```json
{
  "overlays": [
    {
      "slide_id": "s1",
      "text": "строка",
      "font": "строка",
      "size": "строка",
      "color": "#hex",
      "position": "строка",
      "animation": "строка (опционально)"
    }
  ],
  "font_pair": {
    "heading": "строка",
    "body": "строка"
  },
  "typography_notes": "строка"
}
```

---

### `german_qa`

```json
{
  "format_check": {
    "passed": true,
    "issues": ["строка"]
  },
  "visual_check": {
    "passed": true,
    "issues": ["строка"]
  },
  "platform_compliance": {
    "passed": true,
    "issues": ["строка"]
  },
  "tech_passport": {
    "dimensions": "строка",
    "file_format": "строка",
    "color_profile": "строка"
  },
  "qa_notes": "строка"
}
```

---

### `bella_engagement`

```json
{
  "caption": "строка",
  "cta": {
    "type": "вопрос | провокация | вызов",
    "text": "строка"
  },
  "hashtags": ["строка"],
  "first_comment": "строка (опционально)",
  "engagement_notes": "строка"
}
```

⚠️ CTA ≠ «лайк/подписка». Типы: `"вопрос"`, `"провокация"`, `"вызов"`. (SM_RULES §8)

---

### `tim_analytics`

```json
{
  "viral_score": 0.0,
  "kpi_forecast": {
    "reach": "строка",
    "engagement_rate": "строка",
    "saves": "строка"
  },
  "ab_hypotheses": [
    {
      "variable": "строка",
      "variant_a": "строка",
      "variant_b": "строка",
      "hypothesis": "строка"
    }
  ],
  "strategy_notes": "строка",
  "analytics_notes": "строка"
}
```

⚠️ `viral_score` Тима — это его ГИПОТЕЗА, не реальная оценка. Хранится для сравнения.
⚠️ Metrics Daemon через 24ч посчитает `real_viral_score` и запишет `forecast_delta = real - tim`.
⚠️ ministry.record_outcome вызывает ТОЛЬКО Metrics Daemon. Тим и Клавдия — не вызывают.

---

### `fedya_inspection`

```json
{
  "ai_defects": {
    "detected": false,
    "issues": ["строка"]
  },
  "copyright_check": {
    "passed": true,
    "issues": ["строка"]
  },
  "risk_score": 0.0,
  "negative_prompt_required": false,
  "negative_prompt_recommendation": "ТОЛЬКО английский (заполнять если risk_score > 0.3)",
  "inspection_notes": "строка"
}
```

⚠️ `risk_score > 0.3` → `negative_prompt_required: true` + заполнить `negative_prompt_recommendation`.
⚠️ A11 идёт после A06 — `negative_prompt_recommendation` предназначен для следующего рана,
не для текущей картинки. Клавдия сохраняет его в deliverables для использования при ретрае.

---

### `claudia_final` + `deliverables` + `final_dna`

```json
{
  "claudia_final": {
    "post_ready": true,
    "status": "PENDING",
    "editorial_note": "строка"
  },
  "deliverables": {
    "image_path": "из evan_visual.image_path",
    "caption": "из bella_engagement.caption",
    "cta": "из bella_engagement.cta",
    "hashtags": ["из bella_engagement.hashtags"],
    "typography": "из seva_typography",
    "kpi_forecast": "из tim_analytics.kpi_forecast",
    "negative_prompt_next": "из fedya_inspection.negative_prompt_recommendation (если есть)"
  },
  "final_dna": {
    "project_id": "SM_YYYYMMDD_XXX",
    "mode": "post | content_plan",
    "platform": "строка",
    "format": "строка",
    "status": "PENDING",
    "post_id": null,
    "tim_forecast": 0.0,
    "real_viral_score": null,
    "forecast_delta": null,
    "learnings": "строка",
    "avoid_next": "строка"
  }
}
```

⚠️ A12 пишет `history_dna` с `status: PENDING`. Metrics Daemon дописывает `real_viral_score`, `learnings`, `avoid_next` через 24ч.
⚠️ Три ключа в `my_output` верхнего уровня: `claudia_final`, `deliverables`, `final_dna`.

---

## ПРАВИЛА КОТОРЫЕ НЕЛЬЗЯ НАРУШАТЬ

| # | Правило |
|---|---------|
| 1 | Ключ агента — строго из этой таблицы. Никаких `kostya_analysis_v2`, `max_hook`, `evan_prompt` и других вариаций |
| 2 | `prompt_positive` и `prompt_negative` в `evan_visual` — ТОЛЬКО английский |
| 3 | Формат изображения зависит от платформы — нет единого формата как в VIDEO_LONG |
| 4 | `history_dna` создаёт ТОЛЬКО A01, финализирует ТОЛЬКО A12, остальные — `{{inherit}}` |
| 5 | `gleb_review.overall` — рекомендация, не ХАРД-СТОП. Пайплайн не блокируется |
| 6 | PLAN-режим (`run_type: "content_plan"`) — работают только A01–A04 |
| 7 | В state и промтах писать `"content_plan"`, не `"PLAN"` — это реальное значение в hooks.py |
| 8 | CTA в `bella_engagement` — тип только `"вопрос"`, `"провокация"`, `"вызов"` |
| 9 | `viral_score` у Тима — гипотеза, не директива. `recommendation: REWORK` удалён. Реальная оценка — `real_viral_score` от Metrics Daemon |
| 10 | `negative_prompt_recommendation` — на следующий ран, не для текущей генерации |
| 11 | A12 пишет три ключа верхнего уровня: `claudia_final`, `deliverables`, `final_dna` |
| 12 | Порядок вывода A05 (JSON→Markdown) — известная проблема. До фикса Markdown-часть теряется |

---

## АСИНХРОННАЯ ПЕТЛЯ ОБРАТНОЙ СВЯЗИ

Клавдия (A12) завершает пост со статусом `PENDING`. Дальше работают внешние скрипты:

```
A12 → готовый пост + status: PENDING
  ↓
courier.py (Курьер) — публикует пост в Telegram/VK → сохраняет post_id
  ↓  (через 24 часа)
Metrics Daemon — забирает реальные метрики → вычисляет real_viral_score → ministry.record_outcome()
  ↓
Агенты умнеют по реальным данным, а не по предсказаниям нейросети
```

`real_viral_score` в `history_dna` и `final_dna` заполняет **только Metrics Daemon**.
Тим (A10) и Клавдия (A12) его не генерируют.

---

## КАК ПРОВЕРИТЬ СВОЙ ПРОМТ

Три вопроса перед сохранением:

1. **INPUT** — все ключи которые агент читает, есть в колонке «Читает» этой таблицы?
2. **my_output** — структура совпадает со структурой выше?
3. **chain_data** — агент пишет только свой ключ, остальное `{{inherit}}`?

Если хотя бы одно «нет» — промт не готов.

---

## ОТЛИЧИЯ ОТ VIDEO_LONG

| Параметр | VIDEO_LONG | SOCIAL_MIX |
|----------|-----------|------------|
| Режимы | BIBLE + EPISODE | POST (`"post"`) + PLAN (`"content_plan"`) |
| Форматы | всегда `16:9` | `4:5 / 9:16 / 1:1` по платформе |
| Гейт A04 | Катя → `katya_verdict` (ХАРД-СТОП) | Глеб → `gleb_review.overall` (рекомендация) |
| Финализатор A12 | Боб → `bob_marketing` + `final_dna` | Клавдия → `claudia_final` + `deliverables` + `final_dna` |
| Кадры A06 | Ева → `eva_visuals` (поле `frames[]`) | Эван → `evan_visual` (один кадр, поле `prompt_positive`) |
| Видео/VFX | A08 Феликс → `felix_vfx` + `video_clips` | нет |
| Motion | A09 Алекс → `alex_motion` | нет |
| Звук | A10 Сэм → `sam_sound` | нет |
| SMM/thumbnail | A11 Трейси → `tracy_smm` (A/B варианты) | A11 Федя → `fedya_inspection` (инспекция) |
| history_dna создаёт | A12 Боб | A01 Костя |
| interaction_log | `interaction_log_video_long.jsonl` | не определён (добавить в v1.1) |
| project_id | `VL_YYYYMMDD_XXX` | `SM_YYYYMMDD_XXX` |

---

## ПАРАМЕТРЫ MANIFEST.JSON

| Параметр | Значение |
|----------|----------|
| `id` | `social_mix` |
| `run_type` | `social` (POST) / `content_plan` (PLAN) |
| `qa_agent` | `A12` |
| `conflict_mode` | `divergent` ⚠️ — запускает conflict system на каждом агенте |
| `interaction_log` | `economy/data/interaction_log_social_mix.jsonl` |
| `checkpoint_after` | `[]` — нет паузы, нет ХАРД-СТОПа |
| `stop_after` | `null` — стоп только через hooks.py action |
| `revision_loop` | отсутствует — ревизии отключены |

---

*SOCIAL_MIX v1.4 | Контракт ключей — Асинхронная петля*
*Источник: SM_RULES.md v1.0 + hooks.py v3.0 + manifest.json v2.0 + замечания Спринт 20 + уточнение Лока*
