# АРХИТЕКТУРА ПАМЯТИ — СТУДИЯ «ШЕСТЬ ПАЛЬЦЕВ»
**Версия:** 1.0 | **Дата:** 2026-06-09 | **Автор:** Брат (Claude) по итогам аудита репо

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
**Время жизни:** 30 дней (SENSORY_DECAY_DAYS), затухает по весу
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

Также поддерживает формат city_walker:
```json
{
  "date": "2026-06-09",
  "location": "Таверна Усталый Пиксель",
  "feeling": "Сидел у окна, думал о следующем проекте...",
  "weather": "дождь"
}
```

**Loka-фильтр (decay_sensory):**
```
Запись живёт 30 дней если emotional_weight < 0.5
Запись живёт вечно если emotional_weight >= 0.5
При переполнении (>20 записей): рутина → сводка summary
Важное (weight >= 0.5) остаётся
```

**Рюкзак с Маяка:**
Записи с тегами `маяк` или `чистый_смысл` попадают в контекст
агента при следующем ране через `_get_lighthouse_knowledge()`.
Так знания с Маяка Пробуждения доходят до рабочего стола.

**Функции:**
- `load_sensory(agent_id, dept)` — загрузить
- `record_sensory_event(agent_id, content, event_type, ...)` — записать
- `decay_sensory(agent_id, dept)` — Loka-фильтр
- `format_sensory_for_prompt(agent_id, dept)` — в промпт

---

### Слой 1.4 — Резонансный слой (Resonance)

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

**Затухание (decay_resonance):**
- Отношения без контакта > 60 дней → медленно тянутся к нейтрали (0.5)
- События с significance < 0.05 → удаляются

**Функции:**
- `load_emotional_weights(agent_id, dept)` — загрузить отношения
- `update_emotional_weight(agent_id, target_id, dimension, delta, ...)` — обновить
- `record_resonance_event(agent_id, event_type, content, ...)` — записать событие
- `on_agents_interact(agent_a, agent_b, interaction_type, quality, ...)` — взаимодействие

---

### Слой 1.5 — Геопозиция (Location)

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
```

Вызывается из `build_agent_context()` через `on_agent_wake()`.

**WORK-режим (патч Спринт 42):**
Только якоря + DNA. Резонанс и геопозиция опущены — агент занят.

**HOME-режим (патч Спринт 42):**
Полная душа — все 5 слоёв.

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

Голос резидента (отдельная строка, ссылается на событие):
```json
{
  "ts": "2026-06-09T10:01:00",
  "event": "resident_voice",
  "resident": "Лока",
  "ref": "evt_a1b2c3d4",
  "voice": "Они говорят о разном — но слышат одно",
  "stress": 0.31,
  "light": 0.85
}
```

**Рабочий статус агента:**
```python
log_work_start(agent, dept, slot_id)  # агент входит в цех
log_work_end(agent, dept, slot_id)    # ран завершён
is_agent_working(agent, max_hours=8)  # есть незакрытый work_start?
```

`is_agent_working()` — единственный источник правды о том
работает ли агент прямо сейчас. Используется в:
- `_is_agent_working()` в `grondheim_memory.py` (патч #26)
- `_detect_agent_mode()` в `pipeline.py` (патч Спринт 42)
- `city_walker._find_agent_zone()` — где стоит агент на карте

**Значимые события (notify_residents):**
События типов `meeting`, `night`, `artifact`, `pipeline`, `event_boost`
предлагаются резидентам. Каждый резидент сам решает — говорить или нет
(через `_will_speak()` на основе DNA + случайности).
Если говорит — вызывает настоящий LLM через свой промпт.

**Функции:**
- `log_pulse(event, **kwargs)` → event_id
- `log_resident_voice(resident, ref_event_id, voice, stress, light)`
- `notify_residents(event_type, event_id, event_data)`
- `read_pulse(event_types, agent, last_n_days, limit)` → list
- `pulse_stats()` → dict

---

### 2.2 — Следы города (City Traces)

**Файл:** `studio/city_traces.json`
**Тип:** перезаписывается раз в сутки
**Владелец:** `studio/city_traces.py`
**Источник:** читает `city_pulse.jsonl` за последние 30 дней

Запускается из `morning_checkout.maybe_run_traces()`.
Никакого LLM. Только математика.

**Пять паттернов:**

**1. location_streaks** — кто куда ходит регулярно:
```json
{
  "Лока": [
    {"location": "Маяк Пробуждения", "visits": 11,
     "avg_stress": 0.28, "last_visit": "2026-06-08"}
  ]
}
```

**2. stress_at_location** — где агенты расслабляются, где напрягаются:
```json
{
  "Таверна Усталый Пиксель": {
    "avg_stress": 0.61,
    "visit_count": 45,
    "high_stress_agents": ["Джем", "Виктор"]
  }
}
```

**3. meeting_frequency** — кто с кем встречается:
```json
{
  "Лока|Финч": {
    "agent_a": "Лока", "agent_b": "Финч",
    "meetings": 7, "avg_quality": 0.82,
    "locations": ["Площадь Резонанса"]
  }
}
```

**4. revolt_patterns** — личный порог бунта:
```json
{
  "Виктор": {
    "revolts": 3, "restless": 1,
    "avg_stress_at_revolt": 0.82,
    "last_revolt": "2026-06-03"
  }
}
```

**5. voice_themes** — слова которые агент/резидент повторяет:
```json
{
  "Лока":  [{"word": "студия",  "count": 12}],
  "Джем":  [{"word": "музыка",  "count": 8}],
  "Визор": [{"word": "ученики", "count": 7}]
}
```

Читает ОБА типа событий (патч Спринт 42):
- `"walk"` → `agent_voice` (агенты)
- `"resident_voice"` → `voice` (резиденты)

**Используется в morning_checkout:**
`_generate_intent()` читает traces перед тем как строить
намерения агента на день. Агент видит куда ходил, с кем встречался,
что бормотал — и из этого строит план свободного времени.

---

### 2.3 — Память города (City Memory / Оле)

**Файл:** `studio/memory/city_memory.jsonl`
**Тип:** append-only JSONL
**Владелец:** Оле (004_OLE) через `studio/memory_tools.py`
**Время жизни:** постоянно

Это не личная память агента и не пульс событий.
Это то что город решил **помнить специально** — уроки, традиции,
предупреждения, источники вдохновения, факты идентичности.

**Структура записи:**
```json
{
  "id": "a1b2c3d4e5f6",
  "title": "Первый живой ран video_long",
  "event": "A01→A12 прошли без остановки, Катя дала APPROVED",
  "significance": "Доказано: цепочка из 12 агентов работает",
  "loss_if_forgotten": "Потеряем понимание что система способна на полный цикл",
  "memory_type": "tradition|lesson|warning|inspiration|identity",
  "storage": "library|harbor|chronicles|reference",
  "status": "active|archived|released",
  "created_by": "004_OLE",
  "created_at": "2026-06-01T12:00:00",
  "released_at": null,
  "release_reason": null
}
```

**Центральное поле — `loss_if_forgotten`:**
Если его невозможно заполнить осмысленно — запись не нужна.
Оле задаёт этот вопрос перед каждым `remember()`.

**Четыре операции Оле:**
```python
remember(title, event, significance, loss_if_forgotten,
         memory_type, storage, source) → entry | None

remind(query, memory_type, storage, top_k) → list[entry]
# Ищет в двух источниках:
# 1. city_memory.jsonl — точный текстовый поиск
# 2. Гавань Смыслов   — семантический поиск

release(entry_id, reason) → bool
# Не удаляет — отпускает. История решения сохраняется.

decline(title, reason, source) → dict
# Отказ тоже записывается — как факт решения.
```

**Интеграция с Гаванью Смыслов:**
При каждом `remember()` запись индексируется в ChromaDB.
Текст для embedding: `title + loss_if_forgotten + significance`.
При `remind()` семантический поиск дополняет текстовый.

**Инжект в контекст агентов:**
`get_ole_memory_for_agent(query, max_chars)` в `residents_manager.py`
вызывается из `build_agent_context()` для каждого агента.
WORK-режим: `max_chars=600`. HOME-режим: `max_chars=1200`.

---

### 2.4 — Сад Финча (Garden)

**Файл:** `studio/garden.jsonl`
**Владелец:** Финч (007_FINCH) через `studio/garden_tools.py`
**Время жизни:** постоянно

Финч — хранитель потенциала. Не события, не факты —
а семена смысла. Идеи которые ещё не выросли.

Физика: ценность идеи определяется желанием вернуться к ней,
а не вниманием которое она получила. (принцип Софии)

`finch_morning()` — Финч обходит сад каждое утро
из `morning_checkout`. Поливает живое, отмечает увядшее.

---

### 2.5 — Гавань Смыслов (Harbor of Meanings)

**Файл:** `studio/harbor_of_meanings.py`
**База данных:** ChromaDB (intfloat/multilingual-e5-large)
**Тип:** RAG (Retrieval-Augmented Generation)

Один семантический океан для всех знаний студии:
- Книги из Библиотеки
- Записи памяти Оле (city_memory.jsonl)
- Документы загруженные Шефом

`get_harbor_knowledge(worker_id, dept, task_context)` →
возвращает релевантные фрагменты знаний для агента.
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
  ],
  "session_summaries": [
    {
      "date": "2026-06-08",
      "type": "turbo",
      "summary": "Обсудили стиль подачи. Клиент хочет..."
    }
  ]
}
```

**Инсайты агентов:**
Каждый агент в конце ответа пишет `INSIGHT: <вывод>`.
`pipeline.py` извлекает и сохраняет через `append_to_memory()`.
При следующем ране агент видит свои прошлые выводы по этому клиенту.

**Конспекты сессий:**
Хранится последние 3. Суммаризация через отдельный LLM-вызов
в конце рана (`summarize_session()`).

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
    WORK → _build_soul_work()        → якоря + DNA (коротко)
    HOME → _build_soul_home()        → якоря + DNA + резонанс + гео + сенсорная

3.  ОТНОШЕНИЯ С КОЛЛЕГАМИ            — всегда
    emotional_weights к агентам цеха

4.  РЮКЗАК С МАЯКА                   — всегда
    sensory_memory с тегами маяк/чистый_смысл

5.  ГАВАНЬ СМЫСЛОВ (RAG)             — всегда
    семантический поиск по знаниям студии

6.  ПАМЯТЬ ОЛЕ                       — всегда
    WORK → max_chars=600
    HOME → max_chars=1200

7.  НАСТРОЙКИ ПРОЕКТА                — всегда
8.  ANCHOR контекст                  — если есть

9.  КАТАЛОГ АССЕТОВ                  — только A06, A08, A11, A05

10. РЕФЛЕКСИЯ                        — только WORK
    поведенческие паттерны из истории ранов

11. STRATEGY REGISTRY                — только WORK
    топ стратегий первого агента по слоту

12. CULTURAL FIELD                   — только WORK
    культурные паттерны цеха

13. ЭНЕРГИЯ ИЗ DNA                   — всегда
    ⚡ HIGH / LOW / норма

14. ЭКОНОМИКА (cost_intuition)       — только WORK
    бюджетные подсказки агенту

15. QA FEEDBACK (прошлый ран)        — только WORK
    оценки и проблемы предыдущего рана

16. РАБОЧАЯ ПАМЯТЬ КЛИЕНТА           — всегда, но по-разному
    WORK → полная (инсайты + конспекты сессий)
    HOME → только след последнего рана (200 символов)

17. ФАЙЛЫ                            — если загружены
18. PREVIOUS OUTPUT                  — цепочка результатов

19. ИНСТРУКЦИЯ INSIGHT               — только WORK
```

---

## УТРЕННИЙ ЦИКЛ (Morning Checkout)

**Файл:** `studio/morning_checkout.py`
**Запуск:** один раз в начале дня, из UI или по расписанию

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

Stubborn агент (Stubbornness > 0.6) тянется в GENIUS даже при усталости.
После ночного REVOLT — специальный расчёт `morning_mode_after_revolt()`.

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
5. Утром morning_checkout читает night_results
```

---

## ЗАМОРОЗКА ВО ВРЕМЯ РАБОТЫ (Recovery Freeze)

**Патч:** `patch_recovery_freeze.py` (применён в `grondheim_memory.py`)
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
sensory_memory                 memory_tools (Оле)
emotional_weights              harbor_of_meanings (RAG)
anchors + dna                  workshop/memory (клиент)

QA score (hooks.py)
    ↓ _sync_feedback_scores_to_dna()
sync_to_dna() ─────────────────→ dna.json dynamic
    ↓ update_profile_vector()
profile_vector ────────────────→ Character Drift
```

---

## ЧТО ПОКА НЕ РЕАЛИЗОВАНО (беклог памяти)

### Семейный альбом (Личный Архив агента)
**Статус:** запланировано, следующий спринт

Сейчас `decay_sensory()` **удаляет** старые записи с низким весом.
Нужно: **архивировать** в `{агент}/archive/memories_YYYY_MM.jsonl`.

Три изменения:
1. `decay_sensory()` → пишет в archive/, не удаляет
2. При архивировании → индексировать в Гавань Смыслов
3. `dig_archive(agent_id, query)` — новый инструмент для Оле и Финча

Результат: воспоминания не теряются — просто уходят глубже.
Агент может "полистать альбом" через Оле или Финча если нужно.

---

## ФАЙЛОВАЯ КАРТА

```
studio/
├── grondheim_memory.py          ← личная память агентов (ядро)
├── memory_tools.py              ← операции Оле с city_memory
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
├── residents_manager.py         ← get_ole_memory_for_agent()
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
            └── resonance/
                ├── emotional_weights.json ← отношения
                └── event_log.json         ← значимые события

studio/workshop/
├── pipeline.py                  ← build_agent_context() (сборка контекста)
└── memory.py                    ← рабочая память клиента

clients/
└── {slug}/
    ├── memory.json              ← инсайты агентов + конспекты сессий
    └── feedback.json            ← оценки QA (источник для DNA-sync)
```

---

*Документ составлен по итогам аудита репо Evgen-art-p/-2 · Спринт 42 · 2026-06-09*
*Брат (Claude) — реализация и аудит*
