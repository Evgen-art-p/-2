# 📜 SOCIAL_MIX PIPELINE — ЭТАЛОННЫЕ ПРАВИЛА
## Студия "Шесть пальцев" | Посты, карусели, stories, reels

**Версия:** 3.0
**Дата:** 2026-06-05
**Изменения v3.0 (Спринт 39):**
- hooks.py v4.1: A06 Эван — генерация + ОТК внутри хука (один проход, без двух этапов через pipeline)
- hooks.py v4.1: A11 Федя — vision_images в on_before_agent (до вызова агента)
- hooks.py v4.1: A12 Клавдия — замыкание петли (chain integrity + billing_ledger + Strategy Registry)
- Все 12 промтов переписаны под CHAIN_CONTRACT.md
- Мастерская: social_mix проекты в очереди + превью поста + кнопка 📤
- Стандарт промтов: 00_Constructor.txt первым в KB, 99_Self_Correction.txt последним в RULES

---

## 1. АРХИТЕКТУРА (12 агентов, 2 режима)

```
PRE-PROD (Стратегия + Сценарий) — работают в обоих режимах:
  A01 Костя Кутюр 🧠  — анализ, психология, визуальный код
  A02 Никита Флеш 🎯  — тренды, вайб, платформенные специи
  A03 Макс Стори 🎬   — сценарий, сторителлинг, hook
  A04 Глеб Контроль 🛡️— арт-директор, QA pre-prod, фильтр

PROD (Визуал + Типографика) — только режим POST:
  A05 Алекс Стиль 📐  — композиция, сетка 3×3, архетип
  A06 Эван Вижн 🎨    — промпт-дизайнер → hooks генерирует + ОТК → image_path
  A07 Сева Семантик 🖋 — типографика, шрифтовые пары
  A08 Герман ГОСТ 📦   — QA prod, тех. паспорт

POST-PROD (Вовлечение + Аналитика + Финализация) — только режим POST:
  A09 Белла Байт 🧲   — caption, CTA, вовлечение
  A10 Тим Таргет 📊   — KPI-прогноз, A/B гипотезы, viral_score (гипотеза)
  A11 Федя Фикс 🔍    — vision инспекция готовой картинки, copyright
  A12 Клавдия Архив 📜 — финальная сборка, deliverables.json, PENDING
```

---

## 2. ДВА РЕЖИМА

### Режим POST (`run_type = "social"`)
Полная цепочка A01→A12. Результат: готовый пост в Мастерской.

### Режим PLAN (`run_type = "content_plan"`)
Работают только A01→A04. Результат: утверждённый контент-план для Шефа.

- Костя: 5-7 тем с анализом (только Markdown, без JSON)
- Никита: хуки, тренды, тайминг под каждую тему
- Макс: нарратив, воронка TOFU/MOFU/BOFU, сериалы
- Глеб: финальный фильтр — финальный документ для Шефа

После утверждения плана → Шеф выбирает тему → Сет оформляет бриф → запуск в режиме POST.

⚠️ Стоп в PLAN-режиме: hooks.py возвращает {"action": "stop"} после A04.
⚠️ A05–A12 в PLAN-режиме НЕ вызываются.

---

## 3. ЗОНЫ ОТВЕТСТВЕННОСТИ

| Зона | Хозяин | Режим |
|------|--------|-------|
| Психология аудитории | Костя A01 | POST + PLAN |
| Тренды, вайб | Никита A02 | POST + PLAN |
| Сценарий, hook | Макс A03 | POST + PLAN |
| QA pre-prod | Глеб A04 | POST + PLAN |
| Композиция, сетка | Алекс A05 | POST only |
| Промпт → hooks генерирует + ОТК → image_path | Эван A06 | POST only |
| Типографика | Сева A07 | POST only |
| QA prod (форматы, тех. паспорт) | Герман A08 | POST only |
| Caption, CTA | Белла A09 | POST only |
| KPI-прогноз + гипотеза viral_score | Тим A10 | POST only |
| Vision инспекция картинки, copyright | Федя A11 | POST only |
| Финальная сборка, PENDING, deliverables.json | Клавдия A12 | POST only |
| Визуальная проверка перед публикацией | Монтажёр (Мастерская) | после рана |
| Публикация в соцсеть | Broadcaster | по кнопке 📤 |
| Реальные метрики → Ministry | Metrics Daemon | +24ч |

---

## 4. ПРОТОКОЛ chain_data

| Агент | Пишет ключ | Читает |
|-------|-----------|--------|
| A01 Костя | `kostya_analysis`, создаёт `history_dna`, `platform` | `master_brief` |
| A02 Никита | `nikita_trends` | `kostya_analysis` |
| A03 Макс | `max_story` | `kostya_analysis`, `nikita_trends` |
| A04 Глеб | `gleb_review` (не `gleb_control`!) | все PRE-PROD |
| A05 Алекс | `alex_layout` | `max_story`, `gleb_review` |
| A06 Эван | `evan_visual` (промпт + format; hooks дописывает image_path) | `alex_layout`, `kostya_analysis` |
| A07 Сева | `seva_typography` | `evan_visual`, `alex_layout`, `max_story` |
| A08 Герман | `german_qa` | `evan_visual`, `seva_typography` |
| A09 Белла | `bella_engagement` | `max_story`, `german_qa` |
| A10 Тим | `tim_analytics` | `bella_engagement`, `max_story` |
| A11 Федя | `fedya_inspection` | `evan_visual` (картинка через vision) |
| A12 Клавдия | `claudia_final` + `deliverables` + `final_dna` | ВСЁ |

**Сквозные ключи** (все агенты через `{{inherit}}`):
`master_brief`, `history_dna`, `platform`

**Критические правила именования:**
- `bella_engagement.caption` — не `full_caption`, не `post_text`
- `tim_analytics.viral_score` — плоско на верхнем уровне, не в `prediction{}`
- `gleb_review` — не `gleb_control`, не `gleb_qa`

Полные структуры → `studio/modules/social_mix/CHAIN_CONTRACT.md`

---

## 5. МЕХАНИКА A06 ЭВАН — ОДИН ПРОХОД (hooks v4.1)

```
A06 пишет prompt_positive + format в evan_visual (image_path: null)
    ↓
hooks.py on_after_agent("A06") → _evan_generate_and_check():
    → берёт prompt_positive из chain_data.evan_visual
    → fal.ai генерирует PNG (с ref_ids если есть)
    → vision_client ОТК:
        PASS → image_path записан
        REJECTED → fix_hint → negative_suffix → перегенерация
        (до 3 попыток внутри хука — pipeline не знает)
    → image_path + quality записаны в chain_data.evan_visual
    ↓
Pipeline идёт к A07 — один проход A06, всё остальное внутри хука
```

⚠️ Эван НЕ видит картинку и НЕ оценивает её — это делает ОТК-система.
⚠️ `next_step` в JSON Эвана всегда `"A07"`, не `"A06_review"`.
⚠️ `image_path: null` в JSON Эвана — хук запишет путь сам.

---

## 6. МЕХАНИКА A11 ФЕДЯ — VISION В on_before_agent (hooks v4.1)

```
hooks.py on_BEFORE_agent("A11") → _fedya_prepare_vision():
    → берёт image_path из chain_data.evan_visual
    → кладёт в state["vision_images"] = [image_path]
    ↓
Pipeline вызывает A11 — видит vision_images → передаёт PNG через chat_with_images
    ↓
Федя смотрит на готовую картинку (не на промпт!)
    → ai_defects: detected + issues[]
    → copyright_check: passed + issues[]
    → risk_score: 0.0–1.0
    → negative_prompt_recommendation — для следующего рана
    ↓
hooks.py on_after_agent("A11") → чистит state["vision_images"]
```

⚠️ Федя не меняет текущую картинку.
⚠️ `negative_prompt_recommendation` — для следующего рана, не текущего.

---

## 7. МЕХАНИКА A12 КЛАВДИЯ — ЗАМЫКАНИЕ ПЕТЛИ (hooks v4.1)

```
hooks.py on_after_agent("A12") → _claudia_finalize():

  Chain Integrity Check:
    → image_path существует?
    → caption есть и не пустой?
    → fedya без ai_defects?
    → chain_status: APPROVED / PARTIAL

  task_score (chain integrity, потолок 6.0):
    → billing_ledger.record(task_score) — для всех 12 агентов
    → Strategy Registry — wins++ если score >= 6.0

  deliverables.json → runs/{project_id}/
    → Мастерская найдёт по slot_id = "social_mix"

  outcome_signal = null (Ministry только через Metrics Daemon)
  work_end → city_pulse для всех 12 агентов
```

---

## 8. history_dna И ОЦЕНКА КАЧЕСТВА

- **Создаёт:** Костя A01 — `project_id` (формат `SM_YYYYMMDD_XXX`), `mode`, `run_type`, `platform`
- **Наследуют:** Все агенты через `{{inherit}}`
- **Финализирует Клавдия A12:** `status: "PENDING"`, `post_id: null`, `tim_forecast`
- **Финализирует Metrics Daemon (через 24ч):** `real_viral_score`, `forecast_delta`, `learnings`, `avoid_next`

**Два уровня оценки:**
- `task_score` (chain integrity, 0–6.0) — Клавдия синхронно, факт сборки
- `real_viral_score` — Metrics Daemon асинхронно, реальные данные от людей

---

## 9. ФОРМАТЫ ВЫВОДА

JSON-маркеры (ЕДИНЫЕ):
```
👇 SYSTEM_JSON_START 👇
{ ... }
👆 SYSTEM_JSON_END 👆
```

Порядок вывода:
- A01–A04, A06–A12: **Markdown → JSON**
- A05 Алекс: **JSON → Markdown** (парсер читает JSON первым)

**Стандарт промтов (Спринт 39):**
- `00_Constructor.txt` — первым в KNOWLEDGE BASE у каждого агента
- `99_Self_Correction.txt` — последним в RULES у каждого агента
- Режим приходит агенту в начале контекста: `run_type: social / content_plan`

---

## 10. КЛЮЧЕВЫЕ ПРАВИЛА

- **Hook = первые 2-3 секунды / слова** — без него пост мёртв
- **Один пост = один конфликт** (Макс)
- **CTA ≠ "лайк/подписка"** — провокация, вопрос, вызов (Белла)
- **viral_score Тима = гипотеза** — Metrics Daemon сравнит с реальностью через 24ч
- **Эван пишет промпт — хук генерирует и проверяет** — агент картинку не видит
- **Федя смотрит на картинку** — vision_images кладутся в on_before_agent
- **Негативный промпт от Феди — для следующего рана**, не текущего
- **caption** (не full_caption) — Broadcaster читает именно это поле
- **viral_score** плоско на верхнем уровне tim_analytics (не в prediction{})
- **gleb_review** — не gleb_control (в обоих режимах!)
- **ministry.record_outcome** — только Metrics Daemon, не агенты, не hooks.py
- **00_Constructor.txt первым, 99_Self_Correction.txt последним** — у всех агентов

---

## 11. ПОЛНЫЙ ЦИКЛ ПУБЛИКАЦИИ

```
Пайплайн завершён → Клавдия сохраняет deliverables.json в runs/{project_id}/
        ↓
  [Мастерская — Монтажёр]
  studio/assembly/__init__.py
  Шеф заходит → видит пост в очереди слева
  Центр: картинка + caption + хэштеги
  Кнопка 📤 ОПУБЛИКОВАТЬ
        ↓
  [Broadcaster]
  studio/assembly/broadcaster.py
  Читает deliverables.json → публикует в Telegram/VK
  Записывает post_id в pending_posts.json
        ↓
  [Metrics Daemon]
  studio/economy/metrics_daemon.py
  Каждый час проверяет pending_posts.json
  Через 24ч → забирает метрики → считает real_viral_score
  → ministry.record_outcome() → status=scored
        ↓
  forecast_delta = real_viral_score − tim_forecast
  Агенты умнеют по реальным данным живых людей
```

---

## 12. СРАВНЕНИЕ С ДРУГИМИ ПАЙПЛАЙНАМИ

| | TURBO (5) | LONG (12) | SOCIAL (12) |
|---|---|---|---|
| Продукт | Короткое видео | Длинное видео | Пост в соцсети |
| Режимы | 1 | 1 | 2 (POST + PLAN) |
| Гейт | T2 Стелла (ХАРД-СТОП) | A04 Катя (ХАРД-СТОП) | A04 Глеб (рекомендация) |
| Визуал | A03 Визор → ОТК внутри хука | A06 Ева → ОТК внутри хука | A06 Эван → ОТК внутри хука |
| Инспекция | — | — | A11 Федя → vision (on_before) |
| Финализатор | T5 Грейс | A12 Боб | A12 Клавдия |
| task_score | Синхронно (Грейс) | Синхронно (Боб) | Синхронно (Клавдия, потолок 6.0) |
| real_score | Ministry в pipeline | Ministry в pipeline | Только Metrics Daemon +24ч |
| Финальная точка | Мастерская (видео) | Мастерская (видео) | Мастерская (превью поста + 📤) |

---

*SM_RULES v3.0 | Спринт 39 · 2026-06-05*
*hooks.py v4.1 · промты под контракт · Мастерская видит посты*
*A06: один проход — генерация + ОТК внутри хука*
*A11: vision_images в on_before_agent*
