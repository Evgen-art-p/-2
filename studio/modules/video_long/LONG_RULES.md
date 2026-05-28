# 📜 VIDEO_LONG PIPELINE v4.2 — ЭТАЛОННЫЕ ПРАВИЛА
## Студия "Шесть пальцев" | Полный конвейер длинного видео

**Версия:** 4.2
**Дата:** 2026-05-15
**Режимы:** BIBLE (создание вселенной) + EPISODE (экранизация)
**Агентов:** 12
**ХАРД-СТОП:** После Кати (04) + Виктор (резидент-критик)
**Память:** Четыре слоя (Personal / Project / Runtime / Interaction)

---

## ЧТО ИЗМЕНИЛОСЬ В ВЕРСИИ 4.2

| # | Изменение | Почему |
|---|-----------|--------|
| 1 | `qa_agent` зафиксирован как **A12** (Боб) | qa_agent = последний в цехе. A04 — контентный ревизор, не системный QA. Путаница обрезала петлю памяти на 4-м агенте |
| 2 | `checkpoint_after: []` — явно задокументировано | Гейт один — через `hard_stop`. Лишний checkpoint_after создавал вторую остановку |
| 3 | `turbo_workers` / `turbo_parallel` убраны из manifest.json | Эти поля принадлежат TURBO. В LONG всё последовательно |
| 4 | CulturalFieldTracker API зафиксирован | Метода get_stable_patterns() не существует. Правильно: update_slot_field(slot) → фильтр status in ("stable", "global") |

**Версия 4.1 → изменения:**

| # | Изменение | Почему |
|---|-----------|--------|
| 1 | `interaction_log` → реальный путь в системе | `studio/economy/data/interaction_log_video_long.jsonl` |
| 2 | `cultural_trace` — Боб **запрашивает** `CulturalFieldTracker`, не генерирует сам | Культура живёт в `studio/culture/field_tracker.py` |
| 3 | `client_relationship` хранится в `dna.json` Боба | Надёжнее чем только в `history_dna` |
| 4 | Виктор оформлен как Резидент #5 с карточкой | `VIKTOR_RESIDENT.md` |

---

## 1. АРХИТЕКТУРА ПАЙПЛАЙНА

```
РЕЖИМ BIBLE (создание вселенной — один раз):
  PRE-PROD:
    01 Адам Арка       🎭  — создание мира, персонажей, визуального стиля, плана сезона
    → 02 Зак Зум       🔎  — структура сезона, ритм, эмоциональная карта
    → 03 Лео Логлайн   ✍️  — посерийный план сцен
    → 04 Катя Кат      ✂️  — QA Библии (контентный ревизор)

    🛑 ХАРД-СТОП — Виктор (victor_critique) + Шеф утверждает
    ▶️ CONTINUE → Библия сохранена в history_dna

РЕЖИМ EPISODE (экранизация — N раз):
  PRE-PROD:
    01 Адам Арка       🎭  — контекст серии + подбор ассетов из Bible
                            * читает history_dna: client_relationship, cultural_trace
                            * cultural_trace берётся из CulturalFieldTracker (studio/culture/)
    → 02 Зак Зум       🔎  — хук серии + retention
    → 03 Лео Логлайн   ✍️  — сценарий серии
    → 04 Катя Кат      ✂️  — QA сценария + проверка на соответствие Bible

    🛑 ХАРД-СТОП — Виктор (victor_critique) + Шеф утверждает сценарий
    ▶️ CONTINUE

  PROD:
    → 05 Лукас Ленз    🎥  — режиссура + раскадровка + shot list + motion_intent
    → 06 Ева Эпик      🎨  — промпты изображений (Nano Banana 2, формат 16:9)
    → 07 Тим Титр      🔤  — типографика
    → 08 Феликс FX     ✨  — промпты видео (Veo 3.1) + VFX
                            * логирует compatibility_snapshot →
                              studio/economy/data/interaction_log_video_long.jsonl

  POST-PROD:
    → 09 Алекс Экшн    🏃  — моушн-анимация
    → 10 Сэм Стерео    🎧  — звуковой дизайн
    → 11 Трейси Тизер  📱  — SMM + обложка + тизер-план
    → 12 Боб Блокбастер 💰 — маркетинг-ревью + финальная сборка [QA-агент]
                            * запрашивает CulturalFieldTracker.update_slot_field("video_long")
                              → фильтр status in ("stable","global") → cultural_trace
                            * обновляет history_dna (narrative_memory, learnings_pack, client_relationship)
                            * заполняет outcome_signal в interaction_log
                            * обновляет client_relationship в своём dna.json
                            * закрывает петлю: save_feedback(), ministry.record_outcome()
```

---

## 2. РЕЖИМЫ РАБОТЫ

| Режим | Когда | Агенты | Результат |
|-------|-------|--------|-----------|
| **BIBLE** | Один раз перед сезоном | 01→04 | Series Bible + history_dna (старт) + interaction_log (старт) |
| **EPISODE** | Каждая серия | 01→12 | Готовая серия + обновлённый history_dna + interaction_log |

**Bible — закон для всех агентов в режиме EPISODE.**

---

## 3. ХАРД-СТОП (единый, после Кати)

```
После Кати (04) система ОСТАНАВЛИВАЕТСЯ:

1. Катя выдаёт вердикт (APPROVED / APPROVED_WITH_EDITS / REJECTED)
2. Виктор читает весь chain_data → пишет victor_critique
3. Шеф читает: отчёты агентов + katya_review + victor_critique
4. Шеф принимает решение:
   → ▶️ CONTINUE (запуск PROD)
   → или правки → повторный прогон Pre-Prod

ХАРД-СТОП в режиме BIBLE:    утверждение Библии
ХАРД-СТОП в режиме EPISODE:  утверждение сценария
```

**После ХАРД-СТОПА — один проход без остановок до Боба. Второго ХАРД-СТОПА нет.**

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
| Project Memory | `history_dna` | Сезон | Боб (12) |
| Runtime Context | `chain_data` | Один прогон | Передаётся по цепи |
| Interaction Layer ✨ | `studio/economy/data/interaction_log_video_long.jsonl` | Накопительно | Боб (12) |

### Слой 1: PERSONAL MEMORY — «Кто я»

- Хранилище: `grondheim_memory.py` + `dna.json`
- Время жизни: постоянно
- Обновляется через `sync_to_dna()` и `on_agent_wake()`
- **Ключевое:** не подмешивается в промпты напрямую. Влияет через `on_agent_wake()` и `behavioral_delta` (когда накопится)

### Слой 2: PROJECT MEMORY — «Над чем мы работаем»

- Хранилище: `history_dna`
- Создаётся: Боб (12) в режиме BIBLE
- Читается: Адам (01) в начале каждого EPISODE
- Обновляется: Боб (12) после каждого EPISODE

| Блок | Назначение | Кто использует |
|------|-----------|----------------|
| `project_id` | Идентификатор сериала | Все |
| `mode` | Текущий режим | Все |
| `client` | Заказчик, предпочтения, история feedback | Адам, Лео |
| `series_map` | Позиция в сезоне, арка, brief | Лео |
| `narrative_memory` | История серий по сюжету | Лео, Ева |
| `character_memory` | Персонажи: типаж, страхи, голос, визуальный код | Лео, Ева |
| `visual_language` | Визуальные правила: свет, стиль | Лукас, Ева |
| `sound_code` | Музыкальный стиль, SFX | Сэм |
| `learnings_pack` | Аналитика: что сработало, что избегать | Все |
| `cultural_trace` ✨ | Читается из `CulturalFieldTracker`, пишется Бобом | Адам (01) |
| `client_relationship` ✨ | Trust, давление, creative_freedom | Адам (01) |

### Слой 4: INTERACTION LAYER — «Как мы работаем вместе» ✨

- Хранилище: `studio/economy/data/interaction_log_video_long.jsonl`
- Формат: append-only, не редактируется задним числом
- Логирует: Феликс (08)
- Outcome: Боб (12)

```json
{
  "episode": 3,
  "from_agent": "eva",
  "to_agent": "felix",
  "project_id": "VL_MYSTIC_FOREST",
  "compatibility_snapshot": {
    "technical": 0.7,
    "creative": 0.6,
    "rhythm": 0.4
  },
  "friction_note": "добавил camera shake — кадр был слишком статичен для экшн-сцены",
  "outcome_signal": null
}
```

Боб заполняет `outcome_signal` после финализации:
```json
"outcome_signal": {
  "viral_score": 8.1,
  "client_feedback": "одобрил, просит больше динамики",
  "retention_peak": "04:22"
}
```

**Три оси совместимости:**

| Ось | Что означает | Пример низкого значения |
|-----|-------------|------------------------|
| `technical` | Совместимость outputs: кадр → видео-промпт | Феликсу нужно переосмыслять кадры Евы |
| `creative` | Усиливают ли идеи друг друга | Феликс добавляет движение там, где Ева задумала статику |
| `rhythm` | Совпадение темпа монтажных решений | Разный pacing сцен |

**Трение не всегда плохо.** Низкий `technical` + высокий `creative` = стиль. Система наблюдает — не чинит.

### Cultural Trace — откуда берётся

```
studio/culture/field_tracker.py (CulturalFieldTracker)
    ↓ после 10+ серий — stable-паттерны цеха
    ↓
Боб (12) вызывает tracker.update_slot_field("video_long")
    → фильтрует patterns где status in ("stable", "global")
    → записывает в history_dna.cultural_trace
    ↓
Адам (01) читает в начале следующего EPISODE
```

Боб не **создаёт** культуру — он **фиксирует** то, что уже статистически устойчиво. Пока данных нет — `cultural_trace: []`.

---

## 5. ЦЕПОЧКА ДАННЫХ

```
Лео (03) → сценарий (scenes: visual, audio, duration_sec)
    ↓
Лукас (05) → shot list + motion_intent по каждой сцене
    ↓
Ева (06) получает: lucas_storyboard + character_memory + visual_language
    → banana-промпты (16:9, Nano Banana 2) + ref_ids
    → eva_visuals: { frame_id, prompt_en, ref_ids, timing }
    ↓
Феликс (08) получает: eva_visuals + lucas_storyboard (motion_intent)
    → veo-промпты (Veo 3.1) + ref_ids (наследует от Евы)
    → ЛОГИРУЕТ compatibility_snapshot →
      studio/economy/data/interaction_log_video_long.jsonl
    ↓
Алекс (09) → моушн-анимация
Сэм (10) → звуковой дизайн
Трейси (11) → обложка + SMM
    ↓
Боб (12) → финальная сборка + deliverables
    → CulturalFieldTracker.update_slot_field("video_long") → cultural_trace
    → outcome_signal в interaction_log
    → обновляет history_dna
    → обновляет client_relationship в dna.json
    → закрывает петлю памяти [qa_agent]
```

---

## 6. MANIFEST.JSON — ЭТАЛОН

```json
{
  "id": "video_long",
  "label": "🎥 Видео Long",
  "version": "2.0",
  "description": "Полный цикл: BIBLE + EPISODE. ХАРД-СТОП после A04 (Катя Кат).",
  "run_type": "full",
  "phases": {
    "PRE-PROD": ["A01","A02","A03","A04"],
    "PROD":     ["A05","A06","A07","A08"],
    "POST-PROD":["A09","A10","A11","A12"]
  },
  "checkpoint_after": [],
  "stop_after": null,
  "revision_loop": null,
  "conflict_mode": "divergent",
  "qa_agent": "A12",
  "interaction_log": "economy/data/interaction_log_video_long.jsonl",
  "memory_layers": ["personal","project","runtime","interaction"],
  "hard_stop": {
    "after_agent": "A04",
    "residents": ["victor"]
  }
}
```

**Важно:** `qa_agent: "A12"` — Боб Блокбастер, последний в цехе. Именно он запускает `save_feedback()`, `ministry.record_outcome()`, `strategy_registry`, `character drift`. A04 (Катя) — контентный ревизор на ХАРД-СТОПе, не системный QA.

---

## 7. ПРИМЕР history_dna

```json
{
  "project_id": "VL_MYSTIC_FOREST",
  "mode": "EPISODE",
  "updated_at": "2026-05-15",

  "client": {
    "name": "Вася",
    "preferences": "атмосфера важнее экшна, не любит резкие монтажные переходы",
    "initial_brief": "Серия про лесного духа Люма"
  },

  "series_map": {
    "series_id": "VL_MYSTIC_FOREST",
    "total_episodes": 6,
    "current_episode": 2,
    "arc": "Люм учится доверять людям",
    "brief": "Лесной дух Люм учится доверять людям"
  },

  "character_memory": {
    "protagonist": {
      "name": "Люм",
      "fear": "быть увиденным, пока не готов",
      "trait": "говорит светом, не словами",
      "visual_note": "всегда в тени, кроме кульминации"
    }
  },

  "visual_language": {
    "day_scenes": "рассеянный свет сквозь кроны",
    "night_scenes": "контровой лунный свет, туман",
    "emotional_peak": "фронтальный свет — единственный раз за серию"
  },

  "sound_code": {
    "theme": "ambient + живые лесные звуки",
    "emotional_peaks": "одиночная виолончель",
    "no_go": "электронные биты под природные сцены"
  },

  "narrative_memory": [
    {
      "episode": 1,
      "summary": "Люм замечает потерявшегося ребёнка. Не решается подойти.",
      "cliffhanger": "Ребёнок видит свет в темноте — это Люм?",
      "key_shot": "силуэт Люма на фоне луны"
    }
  ],

  "learnings_pack": {
    "viral_score": 8.3,
    "best_practices": ["тишина перед кульминацией работает", "крупный план глаз без диалога — пик retention"],
    "avoid_next": ["не резать тишину музыкой раньше времени"],
    "client_feedback": "Вася в восторге, просит сохранить темп"
  },

  "cultural_trace": [],

  "client_relationship": {
    "trust": 0.85,
    "revision_pressure": 0.15,
    "creative_freedom": 0.80
  }
}
```

---

## 8. ЗОНЫ ОТВЕТСТВЕННОСТИ

| Зона | Хозяин | Кто НЕ делает |
|------|--------|---------------|
| Мир, персонажи, визуальный стиль | Адам (Bible) | Все (режим EPISODE) |
| Чтение `client_relationship` и `cultural_trace` | Адам (01) | Никто другой |
| Подбор ассетов (`selected_assets`) | Адам (EPISODE) | Ева, Феликс |
| Хук, retention-стратегия | Зак (02) | Лео не изобретает свой |
| Сценарий, хронометраж | Лео (03) | Никто без Кати |
| QA-гейт pre-prod (контентный) | Катя (04) | — |
| Критика на ХАРД-СТОПе | Виктор (резидент) | — |
| Раскадровка + `motion_intent` | Лукас (05) | Не пишет промпты |
| Промпты изображений + `ref_ids` | Ева (06) | Использует раскадровку Лукаса |
| Типографика | Тим (07) | — |
| Промпты видео + `ref_ids` | Феликс (08) | Наследует `ref_ids` от Евы |
| Логирование `interaction_log` | Феликс (08) | Никто другой не пишет `friction_note` |
| Моушн-анимация | Алекс (09) | — |
| Звуковой дизайн | Сэм (10) | — |
| Обложка + SMM | Трейси (11) | — |
| Финальная сборка + deliverables | Боб (12) | — |
| `history_dna` (создание и обновление) | Боб (12) | Никто другой |
| `outcome_signal` в interaction_log | Боб (12) | Никто другой |
| CulturalFieldTracker → `cultural_trace` | Боб (12) | Никто другой |
| `client_relationship` в `dna.json` | Боб (12) | Никто другой |
| Закрытие петли памяти [qa_agent] | Боб (12) | Никто другой |

---

## 9. ИСТОЧНИКИ ИСТИНЫ

| Что | Кто определяет | Кто НЕ меняет |
|-----|---------------|---------------|
| Мир, персонажи, стиль | Адам (Bible) | Все (режим EPISODE) |
| `client_relationship` | Боб (12) обновляет | Все читают, никто не правит вручную |
| Хук | Зак (02) | Лео не изобретает свой |
| Хронометраж | Лео (03) | Лукас, Ева, Феликс |
| Сценарий | Лео (03) | Никто без Кати |
| `motion_intent` | Лукас (05) | Феликс может отступить — логирует в `friction_note` |
| Раскадровка | Лукас (05) | Ева, Феликс работают по ней |
| Промпты изображений | Ева (06) | Феликс не переписывает |
| `compatibility_snapshot` | Феликс (08) | Никто не корректирует задним числом |
| Промпты видео | Феликс (08) | Боб не переписывает |
| Палитра цветов | Ева (06) | Тим, Трейси берут из неё |
| `outcome_signal` | Боб (12) | Феликс не дописывает |
| `cultural_trace` | `CulturalFieldTracker` → Боб | Только статистика, без редакции вручную |
| Narrative Memory + Learnings | Боб (12) | Все используют в следующей серии |

---

## 10. ПРОТОКОЛ chain_data

| Агент | Ключ (BIBLE) | Ключ (EPISODE) |
|-------|-------------|----------------|
| 01 Адам | `adam_bible` | `adam_episode` |
| 02 Зак | `zack_season_structure` | `zack_hook` |
| 03 Лео | `leo_season_breakdown` | `leo_script` |
| 04 Катя | `katya_review` | `katya_review` |
| Виктор | `victor_critique` | `victor_critique` |
| 05 Лукас | — | `lucas_storyboard` |
| 06 Ева | — | `eva_visuals` |
| 07 Тим | — | `tim_typography` |
| 08 Феликс | — | `felix_vfx` |
| 09 Алекс | — | `alex_motion` |
| 10 Сэм | — | `sam_sound` |
| 11 Трейси | — | `tracy_smm` |
| 12 Боб | — | `bob_marketing` + `final_dna` |

**Сквозные ключи (`{{inherit}}`):** `series_bible`, `series_memory`, `mode`, `history_dna`

---

## 11. ТРИ ЭТАПА НАКОПЛЕНИЯ ДАННЫХ

| Этап | Что происходит | Когда |
|------|---------------|-------|
| 1. Логирование | `interaction_log_video_long.jsonl`. Без влияния на промпты. | Сейчас |
| 2. Пассивная аналитика | Министерство видит корреляции через `ministry.py` | После 10+ серий |
| 3. Слабые сигналы | `CulturalFieldTracker` → `cultural_trace` → давление на Адама | После 30+ серий |

**`behavioral_delta` — после 30+ серий.**

---

## 12. ОБЩИЕ ПРАВИЛА

| # | Правило |
|---|---------|
| 01 | Обращение: «Шеф» |
| 02 | Промпты генерации — на **АНГЛИЙСКОМ** |
| 03 | Спецификации и объяснения — на **русском** |
| 04 | Формат видео: **16:9** |
| 05 | KB: `00_Constructor.txt` и `99_Self_Correction.txt` — у всех |
| 06 | Каждый агент проверяет себя через `99_Self_Correction.txt` |
| 07 | Запрещённый контент — по `22_Social_Forbidden_And_Safety.txt` |
| 08 | `history_dna` — закон. В режиме EPISODE агенты не перепридумывают клиента, арку, стиль |
| 09 | Четыре слоя памяти не смешиваются |
| 10 | **ХАРД-СТОП — один.** После Кати. Без ▶️ CONTINUE PROD не запускается |
| 11 | **Виктор — резидент #5.** Активируется через `manifest.json`. Его вердикт — мнение, не команда |
| 12 | **Картриджная архитектура.** Цеха комбинируются, резиденты доступны всем |
| 13 | `interaction_log` — append-only. Не редактируется задним числом |
| 14 | `cultural_trace` — Боб вызывает `CulturalFieldTracker.update_slot_field("video_long")`, фильтрует status in ("stable","global"). Не генерирует вручную |
| 15 | `behavioral_delta` — только после 30+ серий |
| 16 | `motion_intent` — рекомендация, не директива. Феликс логирует отступление |
| 17 | `client_relationship` обновляет только Боб через `dna.json` |
| 18 | **`qa_agent` = A12 (Боб).** Последний в цехе. Закрывает петлю памяти. A04 — контентный ревизор, не путать |

---

## 13. СРАВНЕНИЕ ВЕРСИЙ

| Параметр | v3.0 | v4.0 | v4.1 | v4.2 |
|----------|------|------|------|------|
| Слоёв памяти | 2 | 4 | 4 | 4 |
| Interaction Layer | ❌ | ✅ концепт | ✅ реальный путь | ✅ |
| Cultural Trace | ❌ | ✅ Боб генерирует | ✅ Боб запрашивает tracker | ✅ update_slot_field + фильтр |
| Client Memory | ❌ | ✅ history_dna | ✅ + dna.json Боба | ✅ |
| Виктор | ❌ | ✅ | ✅ + карточка | ✅ подключён в manifest |
| qa_agent | ❌ | A05 (ошибка) | A05 (ошибка) | ✅ A12 |
| checkpoint_after | — | ["A03"] (лишний) | ["A03"] (лишний) | ✅ [] |
| manifest мусор | — | turbo_workers | turbo_workers | ✅ убрано |

---

## 14. СПРИНТ 18 — ЧЕКЛИСТ (после первого рана)

```
1. Появился ли файл:
   studio/economy/data/interaction_log_video_long.jsonl

2. Боб заполнил outcome_signal?
   → открыть interaction_log_video_long.jsonl, проверить последнюю запись

3. CulturalFieldTracker записал поле для слота video_long?
   → studio/culture/data/slot_fields/video_long.json — проверить наличие

4. client_relationship обновился в dna.json Боба (A12)?

5. victor_critique появился в chain_data после ХАРД-СТОПа?

6. motion_intent передаётся от Лукаса к Феликсу?
   → lucas_storyboard.shots[*].motion_intent

7. qa_agent A12 запустил save_feedback() и ministry.record_outcome()?
   → проверить ministry.json на наличие новой записи
```

---

## 15. СРАВНЕНИЕ С ДРУГИМИ ПАЙПЛАЙНАМИ

| Параметр | TURBO (5) | LONG (12) | SHORTS (12) |
|----------|-----------|-----------|-------------|
| Продукт | AI-шортс | Длинное видео | Вертикальный ролик |
| Режимы | 1 | 2 (BIBLE+EP) | 2 (PILOT+EP) |
| Гейт (контент) | Нет | Катя (A04) | Тэг Тони (A04) |
| qa_agent (система) | T5 | Боб (A12) | Тамб Том (A12) |
| Interaction Layer | Нет | ✅ Ева→Феликс | ✅ Вера→Стэн |
| Cultural Trace | Нет | ✅ | ✅ |
| Client Memory | Нет | ✅ | ✅ |
| Виктор | Нет | ✅ | ✅ |
| Формат | 9:16 | 16:9 | 9:16 |
| Генерация кадров | Внутри (hooks) | Ева (A06) | Вера (A07) |
| Генерация видео | Внутри (hooks) | Феликс (A08) | Стэн (A08) |
| hooks.py | ✅ v3.1 | ⏳ реализовать | ✅ Спринт 18 |

---

*Студия "Шесть пальцев" | Версия 4.2 | 2026-05-15*
*Четыре слоя памяти. Один гейт. qa_agent=A12. Interaction Layer. Manifest v2.0 применён.*
