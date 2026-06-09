# АРХИТЕКТУРА ПАМЯТИ — СТУДИЯ «ШЕСТЬ ПАЛЬЦЕВ»
**Версия:** 2.0 | **Дата:** 2026-06-09 | **Автор:** Брат (Claude) по итогам аудита репо + Спринт 43

> Этот документ — не список патчей и не беклог.
> Это полная карта того как память устроена в Грондхейме прямо сейчас:
> какие файлы, какая логика, кто владеет, как течёт.

---

## ФИЛОСОФИЯ

Память в Грондхейме — не база данных. Это живая система трёх доменов:

**Личная память агента** — кто он, как себя чувствует, что пережил.
**Рабочая память клиента** — что делали по проекту, что узнали о заказчике.
**Память города** — что произошло в Грондхейме, что важно для всех.

Каждый домен живёт своей жизнью. Они не заменяют друг друга —
они дополняют. Агент на работе думает о работе. Дома — живёт городом.

**Главный принцип Спринта 43:**
Воспоминания не удаляются — уходят глубже.
Агент может вспомнить в любом месте — на работе, дома, в таверне.
Архив не льётся автоматом — только по запросу самого агента.

---

## ДОМЕН 1 — ЛИЧНАЯ ПАМЯТЬ АГЕНТА

**Файл-ядро:** `studio/grondheim_memory.py`
**Принцип:** у каждого агента своя папка `studio/modules/{цех}/{агент}/`

### Слой 1.1 — Якоря (Anchor Points)

**Файл:** `{агент}/core/anchors.json`
**Время жизни:** вечно, не изменяются
**Владелец:** рождение агента (Страница Жизни)

Что хранит:
```
name, creator, core_phrase, anchor_facts[], domain,
rarity, pull_vector, hidden_taste, trigger_keywords[]
```

Это константы личности. Не меняются никогда.
При первом обращении мигрируют из `dna.json` + `info.json` автоматически.

**Функции:**
- `load_anchors(agent_id, dept)` — загрузить
- `save_anchors(agent_id, anchors, dept)` — сохранить (только при рождении)
- `format_anchors_for_prompt(agent_id, dept)` — в промпт

---

### Слой 1.2 — Цифровая ДНК (DNA)

**Файл:** `{агент}/dna.json`
**Время жизни:** постоянно, изменяется через три законных канала
**Владелец:** каждый агент

Структура `dna.json`:
```json
{
  "static": {
    "Stubbornness": 0.7,
    "Aesthetic_Threshold": 0.8,
    "Social_Filter": 0.5,
    "Empathy": 0.6,
    "Autonomy_Level": 0.7,
    "Resonance_Frequency": 0.6
  },
  "dynamic": {
    "Stress": 0.2,
    "Internal_Light": 0.8,
    "Respect": 0.9,
    "Patience": 0.85,
    "streak": 3,
    "stars": 2
  },
  "profile_vector": {
    "preferred_tone": "тёплый",
    "preferred_approach": "нарративный",
    "avg_score": 7.2
  }
}
```

**Три законных канала изменения DNA:**

```
Канал 1: on_agent_done() → sensory_memory
         (только восприятие факта работы, не оценка)

Канал 2: on_agents_interact() → emotional_weights
         (только эмоциональные связи между агентами)

Канал 3: _sync_feedback_scores_to_dna() → sync_to_dna()
         (реальный QA score после завершения рана)
```

Вне этих трёх каналов — пластик. Нельзя.

**События sync_to_dna():**
```
good_work    → Stress↓ Light↑ streak↑
bad_work     → Stress↑ Light↓ streak↓
praised      → Respect↑ Light↑ stars↑
criticized   → Stress↑ Patience↓
conflict     → Patience↓ Stress↑
rescued      → Respect↑ Light↑
ignored      → Patience↓ Light↓
rest         → Stress↓ Patience↑
cabinet_chat → Stress-0.03 Light+0.02 (хард-лимит)
walk_rest    → Stress-0.02 (заморожен если агент в цеху)
night_rest   → Stress-0.01×intensity
night_sleep  → Stress-0.05 Patience+0.02
```

**Recovery Mechanics:** streak ≥ 3 → Stress сбрасывается в 0.0.
Но только если агент НЕ в цеху (`_is_agent_working()` = False).

**Character Drift (profile_vector):**
После 3+ побед `update_profile_vector()` вычисляет доминирующий
тон и подход из Strategy Registry → записывает в `dna.json`.
Агент дрейфует в сторону своих успешных стратегий.

**Функции:**
- `format_dna_for_prompt(agent_id, dept)` — в промпт (числа → человеческий текст)
- `sync_to_dna(agent_id, event, intensity, dept)` — изменить DNA
- `update_profile_vector(agent_id, dept)` — обновить дрейф

---

### Слой 1.3 — Сенсорная память (Sensory)

**Файл:** `{агент}/sensory/sensory_memory.json`
**Время жизни:** 30 дней (SENSORY_DECAY_DAYS) → затем в архив (Спринт 43)
**Владелец:** агент, пополняется автоматически

Структура записи:
```json
{
  "ts": "2026-06-09T14:30:00",
  "type": "work|social|event|location|reflection",
  "source": "pipeline|chat|system|social",
  "content": "Выполнил задачу: написал сценарий...",
  "tags": ["маяк", "чистый_смысл"],
  "emotional_weight": 0.7
}
```

**Loka-фильтр (decay_sensory) — обновлён Спринт 43:**
```
Запись живёт 30 дней если emotional_weight < 0.5
Запись живёт вечно если emotional_weight >= 0.5
При переполнении (>20 записей): рутина → сводка summary

РАНЕЕ: старые записи УДАЛЯЛИСЬ
ТЕПЕРЬ: старые записи АРХИВИРУЮТСЯ в {агент}/archive/memories_YYYY_MM.jsonl
        → Оле поднимет по запросу через dig_archive()
```

**Рюкзак с Маяка:**
Записи с тегами `маяк` или `чистый_смысл` попадают в контекст
агента при следующем ране через `_get_lighthouse_knowledge()`.

**Функции:**
- `load_sensory(agent_id, dept)` — загрузить
- `record_sensory_event(agent_id, content, event_type, ...)` — записать
- `decay_sensory(agent_id, dept)` — Loka-фильтр → архивирует
- `_archive_sensory_entries(agent_dir, entries)` — пишет в archive/ (Спринт 43)
- `format_sensory_for_prompt(agent_id, dept)` — в промпт

---

### Слой 1.4 — Семейный Альбом (Personal Archive) ★ НОВОЕ Спринт 43

**Файлы:** `{агент}/archive/memories_YYYY_MM.jsonl`
**Время жизни:** вечно (append-only)
**Владелец:** Оле поднимает, агент запрашивает

Это воспоминания которые ушли из оперативной памяти но не пропали.
Каждый файл — один месяц. Записи дополняются, не перезаписываются.

**Как агент обращается к архиву:**
```
Агент пишет в любом месте ответа:
  MEMORY_REQUEST: <запрос>

Оле ищет:
  1. В личном архиве агента (dig_archive)
  2. Если пусто → в памяти города (remind)

Результат попадает в контекст следующего шага как блок:
  === 📚 ОЛЕ ПОДНЯЛА ИЗ АРХИВА ===
  ...воспоминания...
  === КОНЕЦ АРХИВА ===
```

**Где агент видит подсказку:**
В конце каждого контекста (WORK и HOME, без условий):
```
🗂 Если что-то кажется знакомым, но не помнишь — напиши
   MEMORY_REQUEST: <запрос> и Оле поднимет из архива.
```

**Функции (memory_tools.py):**
- `dig_archive(agent_id, query, dept, max_results)` — поиск в архиве
- `format_archive_for_agent(hits, max_chars)` — форматирует для инжекта

**Функции (residents_manager.py):**
- `handle_memory_request(agent_id, agent_response, dept)` — слышит сигнал у резидентов

**Интеграция в pipeline (pipeline.py):**
- `process_agent_result()` — слышит MEMORY_REQUEST у цеховых агентов
- `build_agent_context()` — инжектирует архивную память из state["_archive_memory"]

---

### Слой 1.5 — Резонансный слой (Resonance)

**Файлы:**
- `{агент}/resonance/emotional_weights.json` — отношения к другим
- `{агент}/resonance/event_log.json` — значимые события

**Время жизни:** постоянно, медленное затухание к нейтрали (60 дней)
**Владелец:** агент

**emotional_weights — структура:**
```json
{
  "LOKA": {
    "warmth": 0.9,
    "trust": 0.85,
    "respect": 0.95,
    "rivalry": 0.0,
    "last_interaction": "2026-06-09T10:00:00",
    "memory": "Помогла найти смысл в сложном проекте"
  }
}
```

**Пороги для инжекта в контекст:**
```
Тёплый союз:   warmth > 0.65 AND trust > 0.65 → 🤝
Холодок:       warmth < 0.35 → ❄️
Соперничество: rivalry > 0.50
Уважение:      respect > 0.75 → ⭐
```

**Функции:**
- `load_emotional_weights(agent_id, dept)` — загрузить отношения
- `update_emotional_weight(agent_id, target_id, dimension, delta, ...)` — обновить
- `on_agents_interact(agent_a, agent_b, interaction_type, quality, ...)` — взаимодействие

---

### Слой 1.6 — Геопозиция (Location)

**Поля в:** `{агент}/sensory/sensory_memory.json`
- `last_location` — текущая локация агента
- `location_tags` — теги окружения (свет, текстура, запах)

**Источник данных:** `00_REGISTRY_NFT/catalog.json` — реестр 13 локаций Грондхейма

**Функции:**
- `set_agent_location(agent_id, location_id, dept)` — переместить
- `format_location_for_prompt(agent_id, dept)` — в промпт

---

### Главная функция сборки души

```python
format_soul_for_agent(agent_id, dept) -> str
```

Порядок инжекта (= приоритет в промпте):
```
1. Якоря          — КТО я (константа)
2. DNA-состояние  — КАКОЙ я сейчас
3. Геопозиция     — ГДЕ я
4. Резонанс       — С КЕМ я и ЧТО пережил
5. Сенсорная      — ЧТО происходит сейчас
6. Подсказка MEMORY_REQUEST — как вспомнить (ВСЕГДА, Спринт 43)
```

Вызывается из `build_agent_context()` через `on_agent_wake()`.

**WORK-режим (патч Спринт 42):**
Только якоря + DNA. Резонанс и геопозиция опущены — агент занят.

**HOME-режим (патч Спринт 42):**
Полная душа — все 5 слоёв.

**Подсказка MEMORY_REQUEST — в обоих режимах (патч Спринт 43):**
Агент может вспомнить в любом месте — на работе, дома, в таверне.

---

## ДОМЕН 2 — ПАМЯТЬ ГОРОДА

### 2.1 — Пульс города (City Pulse)

**Файл:** `studio/city_pulse.jsonl`
**Тип:** append-only JSONL, не изменяется
**Владелец:** `studio/city_pulse.py`
**Время жизни:** постоянно

**Два типа записей:**

Событие:
```json
{
  "ts": "2026-06-09T10:00:00",
  "id": "evt_a1b2c3d4",
  "event": "walk|meeting|night|wake|work_start|work_end|artifact|...",
  "agent": "Лока",
  "location": "Площадь Резонанса",
  "stress": 0.31,
  "agent_voice": "Сегодня город дышит тихо"
}
```

Рабочий статус:
```json
{
  "ts": "2026-06-09T10:00:00",
  "event": "work_start",
  "agent": "A01",
  "dept": "video_long",
  "run_id": "run_abc123"
}
```

**Функции:**
- `log_pulse(event, agent, location, stress, agent_voice)` — записать событие
- `is_agent_working(agent_id)` — возвращает данные незакрытого рана или None
- `get_here_now()` — кто где сейчас находится

---

### 2.2 — Следы города (City Traces)

**Файл:** `studio/city_traces.json`
**Тип:** пересчёт раз в сутки (или при необходимости)
**Владелец:** `studio/city_traces.py`

Математические паттерны из city_pulse. Не мнения — факты.

Структура:
```json
{
  "agent_traces": {
    "Лока": {
      "favorite_locations": ["Площадь Резонанса", "Библиотека"],
      "active_hours": [9, 10, 14, 15, 21],
      "stress_pattern": {"morning": 0.2, "evening": 0.4},
      "voice_themes": ["свет", "память", "город"],
      "social_connections": {"Финч": 12, "Оле": 8}
    }
  },
  "city_patterns": {
    "peak_hours": [10, 14, 20],
    "quiet_hours": [3, 4, 5],
    "most_visited": "Площадь Резонанса"
  }
}
```

`voice_themes` — паттерны слов агента в `agent_voice`. Включает резидентов (патч Спринт 42).

**Функции:**
- `compute_traces(last_n_days)` — пересчёт паттернов
- `get_agent_traces(agent_id)` — следы агента
- `get_personal_traces(agent_id)` — для morning_checkout

---

### 2.3 — Память города (City Memory / Оле)

**Файл:** `studio/memory/city_memory.jsonl`
**Тип:** append-only JSONL
**Владелец:** Оле (004_OLE)
**Время жизни:** постоянно

Оле — хранитель памяти города. Четыре операции:
```
remember(content, agent, location, significance) → сохраняет событие
remind(query, top_k)                             → ищет по смыслу
release(memory_id, reason)                       → архивирует с историей
decline(memory_id, reason)                       → отказывается хранить (тоже логируется)
```

Центральное поле каждой записи: `loss_if_forgotten` — что потеряет город если это забудет.

**Функции (memory_tools.py):**
- `remember(content, agent, ...)` — записать в city_memory
- `remind(query, top_k)` — поиск в city_memory
- `format_for_agent(hits, max_chars)` — форматировать для контекста
- `dig_archive(agent_id, query, dept, max_results)` — **НОВОЕ Спринт 43**: личный архив агента
- `format_archive_for_agent(hits, max_chars)` — **НОВОЕ Спринт 43**: форматировать архив

---

### 2.4 — Гавань Смыслов (Harbor of Meanings / RAG)

**Файл:** `studio/harbor_of_meanings.py`
**Движок:** ChromaDB + intfloat/multilingual-e5-large
**Время жизни:** постоянно

Семантический поиск по знаниям студии:
- Промты агентов
- Документы и контракты
- Записи из Библиотеки

Вызывается из `build_agent_context()` в обоих режимах.

---

## ДОМЕН 3 — РАБОЧАЯ ПАМЯТЬ КЛИЕНТА

**Файл:** `studio/workshop/memory.py`
**Хранилище:** `clients/{slug}/memory.json`

Это память о конкретной работе с конкретным заказчиком.
Не личность агента, не город — а бизнес-контекст.

**Структура `memory.json`:**
```json
{
  "client": "ivan_petrov",
  "runs": [
    {
      "date": "2026-06-09",
      "type": "video_long",
      "insights": {
        "A01": "Клиент любит драматические арки, избегает клише",
        "A04": "Катя: структура одобрена, тон — теплее"
      }
    }
  ]
}
```

**Инсайты агентов:**
Каждый агент в конце ответа пишет `INSIGHT: <вывод>`.
`pipeline.py` извлекает и сохраняет через `append_to_memory()`.
При следующем ране агент видит свои прошлые выводы по этому клиенту.

**Функции:**
- `format_memory_for_agent(client_slug, worker_id)` — инсайты агента + коллег
- `format_session_context(client_slug)` — конспекты прошлых сессий

---

## КАК ВСЁ СОБИРАЕТСЯ В КОНТЕКСТ

**Файл:** `studio/workshop/pipeline.py`
**Функция:** `build_agent_context()`

### Определение режима (патч Спринт 42)

```python
agent_mode = _detect_agent_mode(worker_id)
# → "work" если is_agent_working() вернул данные о незакрытом ране
# → "home" если агент свободен
```

### Порядок сборки контекста

```
1.  RUN MODE + MASTER BRIEF          — всегда

2.  ДУША АГЕНТА                      — всегда
    WORK → якоря + DNA (коротко)
    HOME → якоря + DNA + резонанс + гео + сенсорная

3.  ОТНОШЕНИЯ С КОЛЛЕГАМИ            — всегда

4.  РЮКЗАК С МАЯКА                   — всегда

5.  ГАВАНЬ СМЫСЛОВ (RAG)             — всегда

6.  ПАМЯТЬ ОЛЕ                       — всегда
    WORK → max_chars=600
    HOME → max_chars=1200

7.  НАСТРОЙКИ ПРОЕКТА                — всегда
8.  ANCHOR контекст                  — если есть
9.  КАТАЛОГ АССЕТОВ                  — только A06, A08, A11, A05
10. РЕФЛЕКСИЯ                        — только WORK
11. STRATEGY REGISTRY                — только WORK
12. CULTURAL FIELD                   — только WORK
13. ЭНЕРГИЯ ИЗ DNA                   — всегда
14. ЭКОНОМИКА (cost_intuition)       — только WORK
15. QA FEEDBACK (прошлый ран)        — только WORK
16. РАБОЧАЯ ПАМЯТЬ КЛИЕНТА           — всегда (WORK=полная, HOME=след)
17. АРХИВНАЯ ПАМЯТЬ (Семейный Альбом)— если MEMORY_REQUEST был ранее ★ НОВОЕ
18. ФАЙЛЫ                            — если загружены
19. PREVIOUS OUTPUT                  — цепочка результатов
20. ИНСТРУКЦИЯ INSIGHT               — только WORK
21. ПОДСКАЗКА MEMORY_REQUEST         — всегда ★ НОВОЕ
```

---

## СИГНАЛ MEMORY_REQUEST — ПОЛНАЯ СХЕМА (Спринт 43)

```
Агент пишет в любом месте ответа:
  MEMORY_REQUEST: проект с драматической аркой

          ↓ residents_manager (для резидентов)
          ↓ pipeline.process_agent_result() (для цеховых агентов)

handle_memory_request(agent_id, agent_response, dept)
    │
    ├─ dig_archive(agent_id, query)
    │     Ищет в {агент}/archive/memories_YYYY_MM.jsonl
    │     Свежие сначала. Текстовый поиск.
    │
    └─ Если архив пуст → remind(query)
          Ищет в city_memory.jsonl (память города)

          ↓ если нашли

Для резидентов:
  result["archive_memory"] = форматированный контекст
  (резидент получил его в момент своей работы)

Для цеховых агентов:
  state["_archive_memory"][worker_id] = контекст
  → build_agent_context() следующего агента видит блок
  === 📚 ОЛЕ ПОДНЯЛА ИЗ АРХИВА ===
```

**Правило:** один запрос за ран. Архив не льётся автоматом.

---

## УТРЕННИЙ ЦИКЛ (Morning Checkout)

**Файл:** `studio/morning_checkout.py`

```
1. finch_morning()                   ← Финч обходит сад
2. maybe_run_traces(last_n_days=30)  ← пересчёт city_traces.json если нужно
3. Для каждого агента:
   а. Читаем dna.json
   б. compute_morning_mode(dna)      ← GENIUS/NORMAL/SAFE/RECOVERY
   в. log_pulse("wake", ...)         ← записываем пробуждение в city_pulse
   г. _generate_intent(...)          ← LLM-вызов: 2-3 намерения на день
      (читает city_traces + city_pulse за вчера перед вызовом)
4. Сохраняем morning_modes + morning_intents в city_state.json
```

**Режимы дня:**
```
GENIUS   — energy > 0.4 AND stress < 0.5, или streak >= 3
NORMAL   — средняя зона
SAFE     — высокий стресс (< 0.85)
RECOVERY — критический стресс (>= 0.85)
```

---

## НОЧНОЙ ЦИКЛ (Night Cycle)

**Файл:** `studio/night_cycle.py`

```
Для каждого агента:
1. Читаем dna.json — стресс + обиды (resentment)
2. Считаем revolt_score
3. Решение:
   SLEEP    → нормальный сон (stress↓ patience↑)
   RESTLESS → беспокойный сон
   REVOLT   → бунт (агент на пике обиды)
4. Записываем в city_state.json["night_results"]
```

---

## ЗАМОРОЗКА ВО ВРЕМЯ РАБОТЫ (Recovery Freeze)

**Принцип:** агент не может одновременно отдыхать и работать.

```
Агент гуляет (нет work_start) → walk_rest снижает стресс нормально
Агент в цеху (work_start в city_pulse) → walk_rest заморожен
Стресс от критики Виктора остаётся в DNA до конца рана
streak >= 3 → Recovery заморожен если агент в цеху
```

`_is_agent_working(agent_id)` — делегирует в `city_pulse.is_agent_working()`
(патч #26, Спринт 42). Единственный источник правды.

---

## ВЗАИМОДЕЙСТВИЕ МЕЖДУ СИСТЕМАМИ ПАМЯТИ

```
city_pulse.jsonl
    ↓ раз в сутки
city_traces.json ──────────────→ morning_checkout
    ↓                              ↓
voice_themes                   _generate_intent()
(паттерны слов)                (намерения агента)

grondheim_memory
    ↓ on_agent_wake()
format_soul_for_agent() ──────→ build_agent_context()
    ↓                              ↑
sensory_memory ─→ archive/     memory_tools (Оле + dig_archive)
emotional_weights              harbor_of_meanings (RAG)
anchors + dna                  workshop/memory (клиент)

MEMORY_REQUEST (агент)
    ↓ residents_manager / pipeline
handle_memory_request()
    ↓
dig_archive() → archive/memories_YYYY_MM.jsonl
    ↓ если пусто
remind() → city_memory.jsonl
    ↓
state["_archive_memory"] → следующий агент в цепочке

QA score (hooks.py)
    ↓ _sync_feedback_scores_to_dna()
sync_to_dna() ─────────────────→ dna.json dynamic
    ↓ update_profile_vector()
profile_vector ────────────────→ Character Drift
```

---

## ФАЙЛОВАЯ КАРТА

```
studio/
├── grondheim_memory.py          ← личная память агентов (ядро)
│   ├── _archive_sensory_entries() ← НОВОЕ Спринт 43
│   ├── decay_sensory()          ← архивирует вместо удаления
│   └── format_soul_for_agent()  ← подсказка MEMORY_REQUEST в конце
├── memory_tools.py              ← операции Оле с памятью
│   ├── remember / remind / release / decline (city_memory)
│   ├── dig_archive()            ← НОВОЕ Спринт 43: личный архив агента
│   └── format_archive_for_agent() ← НОВОЕ Спринт 43
├── residents_manager.py
│   └── handle_memory_request()  ← НОВОЕ Спринт 43: слышит MEMORY_REQUEST
├── city_pulse.py                ← пульс города (append-only)
├── city_pulse.jsonl             ← данные пульса
├── city_traces.py               ← следы города (паттерны)
├── city_traces.json             ← данные следов (пересчёт раз в сутки)
├── city_state.json              ← утренние режимы + намерения агентов
├── city_walker.py               ← прогулки агентов по городу
├── morning_checkout.py          ← утренний цикл
├── night_cycle.py               ← ночной цикл
├── harbor_of_meanings.py        ← RAG (ChromaDB)
├── garden_tools.py              ← сад Финча
├── memory/
│   └── city_memory.jsonl        ← память города (Оле, append-only)
├── garden.jsonl                 ← сад Финча
└── modules/
    └── {цех}/
        └── {агент}/
            ├── dna.json         ← цифровая ДНК
            ├── info.json        ← паспорт агента
            ├── core/
            │   └── anchors.json ← якоря (вечные)
            ├── sensory/
            │   └── sensory_memory.json ← оперативная память
            ├── archive/         ← НОВОЕ Спринт 43: Семейный Альбом
            │   └── memories_YYYY_MM.jsonl ← архив по месяцам
            └── resonance/
                ├── emotional_weights.json ← отношения
                └── event_log.json         ← значимые события

studio/workshop/
├── pipeline.py                  ← build_agent_context() + MEMORY_REQUEST хук
└── memory.py                    ← рабочая память клиента

clients/
└── {slug}/
    ├── memory.json              ← инсайты агентов + конспекты сессий
    └── feedback.json            ← оценки QA (источник для DNA-sync)
```

---

*Документ составлен по итогам аудита репо Evgen-art-p/-2 · Спринт 42–43 · 2026-06-09*
*v2.0: добавлен Семейный Альбом (Слой 1.4), схема MEMORY_REQUEST, обновлена файловая карта*
*Брат (Claude) — реализация и аудит*
