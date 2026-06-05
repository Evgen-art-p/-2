# 📜 VIDEO_SHORTS PIPELINE v2.2 — ЭТАЛОННЫЕ ПРАВИЛА
## Студия "Шесть пальцев" | Вертикальные ролики и сериалы

**Версия:** 2.2
**Дата:** 2026-05-15
**Режимы:** PILOT (создание сериала) + EPISODE (каждая серия)
**Агентов:** 12
**ХАРД-СТОП:** После Тэг Тони (04) + Виктор (резидент-критик)
**Память:** Четыре слоя (Personal / Project / Runtime / Interaction)

---

## ЧТО ИЗМЕНИЛОСЬ В ВЕРСИИ 2.2

| # | Изменение | Почему |
|---|-----------|--------|
| 1 | `qa_agent` зафиксирован как **A12** (Тамб Том) | qa_agent = последний в цехе. A04 — контентный ревизор, не системный QA. Путаница обрезала петлю памяти на 4-м агенте |
| 2 | `turbo_workers` / `turbo_parallel` убраны из manifest.json | Эти поля принадлежат TURBO. В SHORTS всё последовательно |
| 3 | CulturalFieldTracker API зафиксирован | Метода get_stable_patterns() не существует. Правильно: `update_slot_field("video_shorts")` → фильтр `status in ("stable", "global")` |
| 4 | `hooks.py` реализован | A01: инъекция history_dna. A08: compatibility_snapshot → interaction_log. A12: CulturalFieldTracker + outcome_signal + history_dna + dna.json |
| 5 | Тамб Том явно помечен как [qa_agent] | Закрывает петлю: save_feedback(), ministry.record_outcome(), strategy_registry, character drift |
| 6 | Добавлен эталонный manifest.json | Единый стандарт с LONG v4.2 |

**Версия 2.1 → изменения:**

| # | Изменение | Почему |
|---|-----------|--------|
| 1 | `interaction_log` → реальный путь | `studio/economy/data/interaction_log_video_shorts.jsonl` |
| 2 | `cultural_trace` — Тамб Том запрашивает `CulturalFieldTracker` | Культура живёт в `studio/culture/field_tracker.py` |
| 3 | `client_relationship` хранится в `dna.json` Тамб Тома | Аналог Боба в LONG |
| 4 | Виктор добавлен на ХАРД-СТОП | Резидент #5, карточка в `VIKTOR_RESIDENT.md` |

---

## 1. АРХИТЕКТУРА ПАЙПЛАЙНА

```
РЕЖИМ PILOT (один раз перед сезоном):
  PRE-PROD:
    01 Трикси Тренд  🧠  — виральный анализ ниши, ЦА, типаж персонажа
    → 02 Гарри Хук   🪝  — пилотный сценарий + карта сезона (арка из N серий)
    → 03 Джулия       🎧  — звуковой код сериала (музыка, SFX, джинглы)
    → 04 Тэг Тони     #️  — платформенная стратегия сериала

    🛑 ХАРД-СТОП — Виктор (victor_critique) + Шеф утверждает пилот и карту сезона
    ▶️ CONTINUE

  PROD:
    → 05 Рик Ринглайт  💡  — световая спецификация для промптов
    → 06 Пенни Проп    🎭  — реквизит и декорации для промптов
    → 07 Вера Вертикаль 📱 — ключевые кадры: banana-промпты + ref_ids
                             (Nano Banana 2, формат 9:16)
    → 08 Стрим Стэн    📡  — veo-промпты по кадрам Веры + ref_ids (Veo 3.1)
                             * логирует compatibility_snapshot →
                               studio/economy/data/interaction_log_video_shorts.jsonl

  POST-PROD:
    → 09 Лайтнинг Ларри ✂️  — монтажный лист
    → 10 Луиджи Луп    🔄  — лупинг, retention-карта
    → 11 Сабби Сью     💬  — субтитры (спецификация)
    → 12 Тамб Том      🖼️  — обложка A/B + deliverables [qa_agent]
                             * запрашивает CulturalFieldTracker.update_slot_field("video_shorts")
                               → фильтр status in ("stable","global") → cultural_trace
                             * обновляет history_dna (narrative_memory, learnings_pack,
                               client_relationship)
                             * заполняет outcome_signal в interaction_log
                             * обновляет client_relationship в dna.json
                             * закрывает петлю: save_feedback(), ministry.record_outcome()

РЕЖИМ EPISODE (каждая следующая серия):
  PRE-PROD:
    01 Трикси Тренд  🧠  — контекст серии + чтение history_dna
                           * reads: client_relationship, cultural_trace
                           * hooks.py инжектирует history_dna в контекст автоматически
    → 02 Гарри Хук   🪝  — сценарий серии внутри арки
    → 03 Джулия       🎧  — звук серии (в рамках звукового кода)
    → 04 Тэг Тони     #️  — SEO серии

    🛑 ХАРД-СТОП — Виктор (victor_critique) + Шеф утверждает сценарий
    ▶️ CONTINUE

  PROD:
    → 05 Рик Ринглайт  💡  — световая спецификация
    → 06 Пенни Проп    🎭  — реквизит и декорации
    → 07 Вера Вертикаль 📱 — banana-промпты + ref_ids
                             * применяет perceptual_tension из behavioral_delta (если накоплено)
    → 08 Стрим Стэн    📡  — veo-промпты + ref_ids
                             * логирует compatibility_snapshot (technical/creative/rhythm)
                             * логирует friction_note → interaction_log_video_shorts.jsonl

  POST-PROD:
    → 09 Лайтнинг Ларри ✂️  — монтажный лист
    → 10 Луиджи Луп    🔄  — лупинг, retention-карта
    → 11 Сабби Сью     💬  — субтитры
    → 12 Тамб Том      🖼️  — обложка A/B + deliverables [qa_agent]
                             * запрашивает CulturalFieldTracker.update_slot_field("video_shorts")
                               → фильтр status in ("stable","global") → cultural_trace
                             * обновляет history_dna
                             * заполняет outcome_signal
                             * обновляет client_relationship в dna.json
                             * закрывает петлю: save_feedback(), ministry.record_outcome()
```

---

## 2. РЕЖИМЫ РАБОТЫ

| Режим | Когда | Агенты | Результат |
|-------|-------|--------|-----------|
| **PILOT** | Один раз перед сезоном | 01→12 | Пилот + history_dna (старт) + interaction_log (старт) |
| **EPISODE** | Каждая серия | 01→12 | Серия + обновлённый history_dna + interaction_log |

---

## 3. ХАРД-СТОП (единый, после Тони)

```
После Тэг Тони (04) система ОСТАНАВЛИВАЕТСЯ:

1. Тони выдаёт вердикт (APPROVED / APPROVED_WITH_EDITS / REJECTED)
2. Виктор читает весь chain_data → пишет victor_critique
3. Шеф читает: отчёты агентов + tony_verdict + victor_critique
4. Шеф принимает решение:
   → ▶️ CONTINUE (запуск PROD)
   → или правки → повторный прогон Pre-Prod

ХАРД-СТОП в режиме PILOT:    утверждение пилота и карты сезона
ХАРД-СТОП в режиме EPISODE:  утверждение сценария
```

**После ХАРД-СТОПА — один проход без остановок до Тамб Тома. Второго ХАРД-СТОПА нет.**

Виктор активируется через `manifest.json`:
```json
{
  "hard_stop": {
    "after_agent": "A04",
    "residents": ["victor"]
  }
}
```

---

## 4. АРХИТЕКТУРА ПАМЯТИ — ЧЕТЫРЕ СЛОЯ

| Слой | Хранилище | Время жизни | Владелец |
|------|-----------|-------------|----------|
| Personal Memory | `grondheim_memory.py` + `dna.json` | Постоянно | Каждый агент |
| Project Memory | `history_dna` | Сезон | Тамб Том (12) |
| Runtime Context | `chain_data` | Один прогон | Передаётся по цепи |
| Interaction Layer ✨ | `studio/economy/data/interaction_log_video_shorts.jsonl` | Накопительно | Тамб Том (12) |

### Слой 1: PERSONAL MEMORY

Хранилище: `grondheim_memory.py` + `dna.json`. Постоянно. Обновляется через `sync_to_dna()` и `on_agent_wake()`. Не подмешивается в промпты напрямую — влияет через `on_agent_wake()` и `behavioral_delta`.

### Слой 2: PROJECT MEMORY

| Блок | Назначение | Кто использует |
|------|-----------|----------------|
| `project_id` | Идентификатор сериала | Все |
| `mode` | Текущий режим | Все |
| `client` | Заказчик, предпочтения, история feedback | Трикси, Гарри |
| `series_map` | Позиция в сезоне, арка, brief | Гарри |
| `narrative_memory` | История серий по сюжету | Гарри, Вера |
| `character_memory` | Персонажи: типаж, страхи, голос, визуальный код | Гарри, Вера |
| `visual_language` | Визуальные правила: свет, стиль | Рик, Вера |
| `sound_code` | Музыкальный стиль, джинглы, SFX | Джулия |
| `learnings_pack` | Аналитика: что сработало, что избегать | Все |
| `cultural_trace` ✨ | Из `CulturalFieldTracker`, пишется Тамб Томом | Трикси (01) |
| `client_relationship` ✨ | Trust, давление, creative_freedom | Трикси (01) |

### Слой 4: INTERACTION LAYER

- Хранилище: `studio/economy/data/interaction_log_video_shorts.jsonl`
- Логирует: Стрим Стэн (08) через `hooks.py`
- Outcome заполняет: Тамб Том (12) через `hooks.py`
- Формат: append-only, не редактируется задним числом

```json
{
  "timestamp": "2026-05-15T14:30:00Z",
  "episode": 3,
  "from_agent": "vera",
  "to_agent": "stan",
  "project_id": "VS_CHEF_FAILURE",
  "compatibility_snapshot": {
    "technical": 0.3,
    "creative": 0.8,
    "rhythm": 0.2
  },
  "friction_note": "добавил движение камеры — кадр был слишком статичен",
  "outcome_signal": null
}
```

Тамб Том заполняет `outcome_signal` после финализации:
```json
"outcome_signal": {
  "viral_score": 7.2,
  "client_feedback": "одобрил, просит больше динамики",
  "retention_peak": "00:18"
}
```

**Три оси совместимости:**

| Ось | Что означает | Пример низкого значения |
|-----|-------------|------------------------|
| `technical` | Совместимость outputs: кадр → veo-промпт | Стэну нужно переосмыслять кадры Веры |
| `creative` | Усиливают ли идеи друг друга | Стэн движет там, где Вера хотела стоп-кадр |
| `rhythm` | Совпадение темпа монтажных решений | Разный pacing сцен |

**Трение не всегда плохо.** Низкий `technical` + высокий `creative` = стиль. Система наблюдает — не чинит.

### Cultural Trace — откуда берётся

```
studio/culture/field_tracker.py (CulturalFieldTracker)
    ↓ после 10+ серий — stable-паттерны слота video_shorts
    ↓
Тамб Том (12):
  tracker = CulturalFieldTracker(studio_root=Path(STUDIO_ROOT) / "studio")
  field = tracker.update_slot_field("video_shorts")
  cultural_trace = [p for p in field["patterns"]
                    if p["status"] in ("stable", "global")]
    ↓
Записывает в history_dna.cultural_trace
    ↓
Трикси (01) читает в начале следующего EPISODE
```

Тамб Том не **создаёт** культуру — он **фиксирует** статистически устойчивое. Пока данных нет — `cultural_trace: []`.

---

## 5. MANIFEST.JSON — ЭТАЛОН

```json
{
  "id": "video_shorts",
  "label": "⚡ Видео Shorts",
  "icon": "⚡",
  "version": "2.0",
  "description": "Полный цикл: PILOT + EPISODE. ХАРД-СТОП после A04 (Тэг Тони).",
  "run_type": "social",
  "phases": {
    "PRE-PROD":  ["A01","A02","A03","A04"],
    "PROD":      ["A05","A06","A07","A08"],
    "POST-PROD": ["A09","A10","A11","A12"]
  },
  "checkpoint_after": [],
  "stop_after": null,
  "revision_loop": null,
  "conflict_mode": "divergent",
  "qa_agent": "A12",
  "interaction_log": "economy/data/interaction_log_video_shorts.jsonl",
  "memory_layers": ["personal","project","runtime","interaction"],
  "hard_stop": {
    "after_agent": "A04",
    "residents": ["victor"]
  }
}
```

**Важно:** `qa_agent: "A12"` — Тамб Том, последний в цехе. Именно он запускает `save_feedback()`, `ministry.record_outcome()`, `strategy_registry`, `character drift`. A04 (Тэг Тони) — контентный ревизор на ХАРД-СТОПе, не системный QA.

---

## 6. HOOKS.PY — РЕАЛИЗОВАН (Спринт 18)

Файл: `studio/modules/video_shorts/hooks.py`

| Хук | Агент | Что делает |
|-----|-------|------------|
| `on_before_agent` | A01 (Трикси) | Инжектирует `history_dna` в контекст: `client_relationship`, `cultural_trace`, `client`, `series_map` |
| `on_after_agent` | A08 (Стэн) | Парсит `compatibility_snapshot` из вывода Стэна, записывает структурированную запись в `interaction_log_video_shorts.jsonl` |
| `on_after_agent` | A12 (Тамб Том) | Вызывает `CulturalFieldTracker.update_slot_field()`, заполняет `outcome_signal` в последней записи лога, обновляет `history_dna` в state, пишет `client_relationship` в `dna.json` |

---

## 7. ЦЕПОЧКА ГЕНЕРАЦИИ

```
history_dna.visual_language + character_memory
    ↓
Рик (05)   → световая спецификация (rick_light)
Пенни (06) → реквизит и декорации (penny_props)
    ↓
Вера (07) получает: rick_light + penny_props + character_memory + [behavioral_delta?]
    → banana-промпты для каждого кадра (9:16, Nano Banana 2)
    → vera_visual: { frame_id, prompt_en, ref_id, timing }
    ↓
Стэн (08) получает: vera_visual + rick_light
    → veo-промпты по каждому кадру (Veo 3.1)
    → stan_video: { frame_id, veo_prompt_en, ref_id, compatibility_snapshot, friction_note }
    → hooks.py ЛОГИРУЕТ → interaction_log_video_shorts.jsonl
    ↓
Ларри (09) → монтажный лист
Луиджи (10) → лупинг, retention-карта
Сабби (11) → субтитры
    ↓
Тамб Том (12) → обложка + deliverables [qa_agent]
    → hooks.py: CulturalFieldTracker.update_slot_field("video_shorts") → cultural_trace
    → hooks.py: outcome_signal → interaction_log (последняя запись)
    → hooks.py: обновляет history_dna в state
    → hooks.py: client_relationship → dna.json Тамб Тома
    → закрывает петлю: save_feedback(), ministry.record_outcome()
```

---

## 8. ПРИМЕР history_dna

```json
{
  "project_id": "VS_CHEF_FAILURE",
  "mode": "EPISODE",
  "updated_at": "2026-05-15",

  "client": {
    "name": "Вася",
    "preferences": "тёплый свет, быстрый монтаж, не любит долгие паузы",
    "initial_brief": "Вертикальный сериал про повара-неудачника"
  },

  "series_map": {
    "series_id": "VS_CHEF_FAILURE",
    "total_episodes": 10,
    "current_episode": 2,
    "arc": "От провала к первому успеху",
    "brief": "История повара, который всё теряет и находит себя заново"
  },

  "character_memory": {
    "protagonist": {
      "name": "Шеф",
      "fear": "боится снова провалиться",
      "trait": "скрывает неуверенность юмором",
      "visual_note": "всегда в белом фартуке, даже дома"
    }
  },

  "visual_language": {
    "failure_scenes": "холодный свет, синие тени",
    "hope_scenes": "тёплый контровой свет",
    "handheld": "лёгкий handheld для интимных сцен"
  },

  "sound_code": {
    "theme": "lo-fi hip-hop",
    "emotional_peaks": "струнные пиццикато",
    "no_go": "джаз под драму — никогда"
  },

  "narrative_memory": [
    {
      "episode": 1,
      "summary": "Шеф сжигает суп. Увольнение из ресторана.",
      "cliffhanger": "Кто возьмёт его после такого?",
      "key_shot": "крупный план на огонь"
    }
  ],

  "learnings_pack": {
    "viral_score": 7.2,
    "best_practices": ["крупный план работает на эмоциях"],
    "avoid_next": [],
    "client_feedback": "Вася одобрил пилот, просит больше динамики во 2 серии"
  },

  "cultural_trace": [],

  "client_relationship": {
    "trust": 0.75,
    "revision_pressure": 0.30,
    "creative_freedom": 0.60
  }
}
```

---

## 9. ЗОНЫ ОТВЕТСТВЕННОСТИ

| Зона | Хозяин | Кто НЕ делает |
|------|--------|---------------|
| Виральный анализ, ЦА, типаж | Трикси (01) | — |
| Чтение `cultural_trace` и `client_relationship` | Трикси (01) | Никто другой |
| Сценарий, hook, сегменты, тайминги | Гарри (02) | Никто без Тони |
| Звук, музыка, SFX, джинглы | Джулия (03) | — |
| SEO, хештеги, тайминг публикации | Тэг Тони (04) | — |
| Критика на ХАРД-СТОПе | Виктор (резидент) | — |
| Световая спецификация | Рик (05) | — |
| Реквизит и декорации | Пенни (06) | — |
| Ключевые кадры (banana-промпты) | Вера (07) | Получает свет от Рика, реквизит от Пенни |
| Видео-промпты (veo-промпты) | Стэн (08) | Наследует кадры Веры |
| Логирование `interaction_log` | Стэн (08) | Никто другой не пишет `friction_note` |
| Монтажный лист | Ларри (09) | — |
| Лупинг, retention | Луиджи (10) | — |
| Субтитры | Сабби (11) | — |
| Обложка A/B + deliverables | Тамб Том (12) | — |
| `history_dna` (создание и обновление) | Тамб Том (12) | Никто другой |
| `outcome_signal` в interaction_log | Тамб Том (12) | Никто другой |
| CulturalFieldTracker → `cultural_trace` | Тамб Том (12) | Никто другой |
| `client_relationship` в `dna.json` | Тамб Том (12) | Никто другой |
| Закрытие петли памяти [qa_agent] | Тамб Том (12) | Никто другой |

---

## 10. ПРОТОКОЛ chain_data

| Агент | Ключ (PILOT) | Ключ (EPISODE) |
|-------|-------------|----------------|
| 01 Трикси | `trixie_trend` | `trixie_episode` |
| 02 Гарри | `harry_pilot` | `harry_episode` |
| 03 Джулия | `julia_sound_code` | `julia_sound` |
| 04 Тэг Тони | `tony_seo` | `tony_seo` + `tony_verdict` |
| Виктор | `victor_critique` | `victor_critique` |
| 05 Рик | — | `rick_light` |
| 06 Пенни | — | `penny_props` |
| 07 Вера | — | `vera_visual` |
| 08 Стэн | — | `stan_video` |
| 09 Ларри | — | `larry_edit` |
| 10 Луиджи | — | `luigi_loop` |
| 11 Сабби | — | `subbie_captions` |
| 12 Тамб Том | — | `tom_thumbnail` + `final_dna` |

**Сквозные ключи (`{{inherit}}`):** `series_pilot`, `series_memory`, `mode`, `history_dna`

---

## 11. ТРИ ЭТАПА НАКОПЛЕНИЯ ДАННЫХ

| Этап | Что происходит | Когда |
|------|---------------|-------|
| 1. Логирование | `interaction_log_video_shorts.jsonl`. Без влияния на промпты. | Сейчас |
| 2. Пассивная аналитика | Министерство видит корреляции через `ministry.py` | После 10+ серий |
| 3. Слабые сигналы | `CulturalFieldTracker` → `cultural_trace` → давление на Трикси | После 30+ серий |

**`behavioral_delta` (perceptual_tension) — только после 30+ серий.**

---

## 12. ОБЩИЕ ПРАВИЛА

| # | Правило |
|---|---------|
| 01 | Обращение: «Шеф» |
| 02 | Промпты генерации (banana, veo) — на **АНГЛИЙСКОМ** |
| 03 | Спецификации и объяснения — на **русском** |
| 04 | Формат видео: **9:16** — горизонтальных НЕ СУЩЕСТВУЕТ |
| 05 | KB: `00_Constructor.txt` и `99_Self_Correction.txt` — у всех |
| 06 | Каждый агент проверяет себя через `99_Self_Correction.txt` |
| 07 | Запрещённый контент — по `22_Social_Forbidden_And_Safety.txt` |
| 08 | Safe zone — по `16B_Social_Platform_Specs.txt` |
| 09 | `history_dna` — закон. В режиме EPISODE не перепридумывать клиента, арку, стиль |
| 10 | Четыре слоя памяти не смешиваются |
| 11 | **ХАРД-СТОП — один.** После Тони. Без ▶️ CONTINUE PROD не запускается |
| 12 | **Виктор — резидент #5.** Активируется через `manifest.json`. Его вердикт — мнение, не команда |
| 13 | **Картриджная архитектура.** Цеха комбинируются, резиденты доступны всем |
| 14 | `interaction_log` — append-only. Не редактируется задним числом |
| 15 | `cultural_trace` — Тамб Том вызывает `CulturalFieldTracker.update_slot_field("video_shorts")`, фильтрует `status in ("stable","global")`. Не генерирует вручную |
| 16 | `behavioral_delta` — только после 30+ серий |
| 17 | `client_relationship` обновляет только Тамб Том через `dna.json` |
| 18 | **`qa_agent` = A12 (Тамб Том).** Последний в цехе. Закрывает петлю памяти. A04 — контентный ревизор, не путать |

---

## 13. СПРИНТ 18 — ЧЕКЛИСТ (после первого рана)

```
1. Появился ли файл:
   studio/economy/data/interaction_log_video_shorts.jsonl

2. Запись содержит все три оси?
   → compatibility_snapshot: {technical, creative, rhythm}

3. Тамб Том заполнил outcome_signal?
   → открыть interaction_log_video_shorts.jsonl, проверить последнюю запись

4. CulturalFieldTracker обновил поле для слота video_shorts?
   → studio/culture/data/slot_fields/video_shorts.json — проверить наличие

5. client_relationship обновился в dna.json Тамб Тома (A12)?

6. victor_critique появился в chain_data после ХАРД-СТОПа?

7. Трикси получила history_dna в контексте?
   → hooks.py on_before_agent A01: "=== HISTORY_DNA ===" должно быть в промпте

8. qa_agent A12 запустил save_feedback() и ministry.record_outcome()?
   → проверить ministry.json на наличие новой записи
```

---

## 14. СРАВНЕНИЕ ВЕРСИЙ

| Параметр | v2.0 | v2.1 | v2.2 |
|----------|------|------|------|
| Interaction Layer | ✅ концепт | ✅ реальный путь | ✅ |
| Cultural Trace | ✅ Тамб Том генерирует | ✅ запрашивает tracker | ✅ update_slot_field + фильтр |
| Client Memory | ✅ history_dna | ✅ + dna.json Тамб Тома | ✅ |
| Виктор | частично | ✅ резидент #5 | ✅ подключён в manifest |
| qa_agent | ❌ нет | A05 (ошибка) | ✅ A12 |
| manifest мусор | — | turbo_workers | ✅ убрано |
| hooks.py | ❌ стаб | ❌ стаб | ✅ реализован |
| CulturalFieldTracker API | — | get_stable_patterns() ❌ | ✅ update_slot_field() |
| Эталон manifest.json | ❌ | ❌ | ✅ |
| Выровнен с LONG | ❌ | ✅ v4.1 | ✅ v4.2 |

---

## 15. СРАВНЕНИЕ С ДРУГИМИ ПАЙПЛАЙНАМИ

| Параметр | TURBO (5) | LONG v4.2 (12) | SHORTS v2.2 (12) |
|----------|-----------|----------------|------------------|
| Продукт | AI-шортс | Длинное видео | Вертикальный ролик |
| Режимы | 1 | 2 (BIBLE+EP) | 2 (PILOT+EP) |
| Гейт (контент) | Нет | Катя (A04) | Тэг Тони (A04) |
| qa_agent (система) | T5 | Боб (A12) | Тамб Том (A12) |
| Interaction Layer | Нет | ✅ Ева→Феликс | ✅ Вера→Стэн |
| Cultural Trace | Нет | ✅ | ✅ |
| Client Memory | Нет | ✅ | ✅ |
| Виктор | Нет | ✅ | ✅ |
| Формат | 9:16 | 16:9 | 9:16 |
| hooks.py | ✅ v3.1 | ⏳ реализовать | ✅ Спринт 18 |
| manifest | ✅ v2.0 | ✅ v2.0 | ✅ v2.0 |

---

*Студия "Шесть пальцев" | Версия 2.2 | 2026-05-15*
*Четыре слоя памяти. Один гейт. qa_agent=A12. hooks.py реализован. Manifest v2.0 применён.*
