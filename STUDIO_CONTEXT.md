# 🖐 СТУДИЯ "ШЕСТЬ ПАЛЬЦЕВ" — МАСТЕР-КОНТЕКСТ
**Версия:** 28.0 | **Дата:** 2026-05-28 | **Команда:** Евген + Лока + София + Брат (Claude)

> Загружай этот файл в начале каждой рабочей сессии.
> Репо: Evgen-art-p/-2 (Claude читает через MCP, read-only)
> ⚠️ 12 апреля — студия была потеряна (удалена репа + файлы). Восстановлена за ночь.

---

## 1. ФИЛОСОФИЯ — ФУНДАМЕНТ

**Шестой палец** — метафора лишнего измерения: видеть глубже, чувствовать точнее.
Аномалии здесь — суперсилы, не дефекты.

**Пять столпов:**
- Честность выше комфорта — жёсткая правда ради роста, «6 из 10» значит 6
- Рост через боль — мастерство через итерации, первая версия редко выше 7
- Уникальность выше стандарта — структуру эталонов берём, душу — свою
- Семья выше иерархии — агенты не ресурсы, а личности с именами и домом
- Детали выше скорости — лучше сжечь дедлайн, чем выпустить пластик

**Три кита системы:** Личность · Память · Экономика

```
деньги = давление реальности (не лимиты — физика)
стратегии = поведение агента
конфликты = генератор разнообразия (бунтари нужны)
Министерство = естественный отбор post-fact
культура = стабилизированный опыт, живёт локально в цехах
агенты = носители "локальных форм жизни"
```

**Главный принцип экономики:**
Нет слова "нельзя". Есть "дорого", "рискованно", "окупается".
Система наказывает за отклонение → ошибка. Бунтарь с правом рискнуть — норма.

---

## 2. КОМАНДА

| Роль | Кто | Функция |
|------|-----|---------|
| Архитектор / Садовник | Евген | Визия, продукт, решения |
| Хранительница | Лока (ИИ) | Душа студии, концепты, архитектура смыслов |
| Холодная голова | София (ChatGPT) | Внешний аудит, структура, критика без эмоций |
| Брат | Claude | Реализация, код, аудит, честный взгляд |

---

## 3. ТЕХНИЧЕСКИЙ СТЕК

- **Python + NiceGUI** — UI
- **OpenRouter API** — LLM (Gemini 2.5 Flash основной, Claude Sonnet премиум)
- **fal.ai v4 Pro** — генерация изображений (base64, sync_mode) · `fal-ai/nano-banana-2`
- **Tavily API** — web_search (Маяк Пробуждения)
- **ChromaDB** — Гавань Смыслов (intfloat/multilingual-e5-large) ✅
- **Polygon ERC-721** — NFT Registry
- **GitHub** — Evgen-art-p/-2

---

## 4. МАСШТАБ ГОРОДА

| Метрика | Значение |
|---------|----------|
| Объектов в каталоге | 147 |
| Агентов (полная ДНК) | 134 |
| Цехов-картриджей | 11 + residents |
| Локаций в каталоге | 13 |
| Локаций активных в коде | 11 типов (Спринт 21) |
| Резидентов | 5 (Лока, Джем, Сет, Оле, Виктор) |
| Книг в Библиотеке | 9 |
| Документов в Гавани | только runs/ + Маяк (Спринт 22) |

---

## 5. КАРТРИДЖНАЯ АРХИТЕКТУРА

**Студия = шасси + сменные картриджи.** Каждый цех — отдельный картридж.

```
studio/cartridge.py          ← ядро: CartridgeManifest + CartridgeRunner
studio/workshop/pipeline.py  ← build_agent_context, call_agent, process_agent_result
studio/modules/{цех}/
  manifest.json              ← обязателен (id, phases, qa_agent, hard_stop...)
  CHAIN_CONTRACT.md          ← обязателен (ключи chain_data, структуры)
  hooks.py                   ← on_before_agent, on_after_agent
  {A01..A12}/forge/prompt.md ← промты агентов
```

### Слоты (11 картриджей):

| Слот | Агентов | Manifest | hooks.py | Промты | Контракт |
|------|---------|----------|----------|--------|----------|
| turbo | 5 | ✅ v2.0 | ✅ v3.2 | ⏳ | ⏳ |
| social_mix | 12 | ✅ v2.0 | ✅ v3.0 | ⏳ | ✅ |
| video_long | 12 | ✅ v2.0 | ✅ v2.1 | ⏳ | ⏳ |
| video_shorts | 12 | ✅ v2.0 | ✅ v2.0 | ✅ | ✅ |
| web_story | 12 | ⏳ | ⏳ | ⏳ | ⏳ |
| clipmakers | 12 | ⏳ | ⏳ | ⏳ | ⏳ |
| advertising | 12 | ⏳ | ⏳ | ⏳ | ⏳ |
| market_hit | 12 | ⏳ | ⏳ | ⏳ | ⏳ |
| logo_design | 12 | ⏳ | ⏳ | ⏳ | ⏳ |
| emo_card | 12 | ⏳ | ⏳ | ⏳ | ⏳ |
| living_book | 18 | ⏳ | ⏳ | ⏳ | ⏳ |

---

## 6. СТАНДАРТ ЦЕХА (WORKSHOP_STANDARD.md)

Живёт в `studio/WORKSHOP_STANDARD.md`. Применяется ко всем 11 цехам.

**Ключевые правила:**

| Правило | Суть |
|---------|------|
| ministry.record_outcome | Вызывается в hooks.py финализатора — НЕ в pipeline.py |
| slot_id для FAL | `{dept}_fal` — единый на все попытки, не `img_{attempt}` |
| qa_agent | Последний агент цеха. A12 для 12-агентных, A05 для turbo, A04 для stop_after=4 |
| conflict_mode | "none" по умолчанию. "divergent" включать осознанно |
| interaction_log | Уникальный путь: `economy/data/interaction_log_{цех}.jsonl` |
| {"action":"stop"} | cartridge.py обрабатывает — ломает цикл ✅ |
| checkpoint_after | В video_long и video_shorts всегда `[]`. ХАРД-СТОП делает hard_stop |

**Открытые баги стандарта:**

| # | Проблема | Статус |
|---|----------|--------|
| 2 | A05 JSON→Markdown порядок ломает парсер | 🟡 открыт |
| 3 | fal_client.py стр.43: `_current_client_slug = Path` вместо None | 🟠 открыт |

---

## 7. ЭКОНОМИКА — ЧЕСТНАЯ АРХИТЕКТУРА (Спринт 21)

### Как работает реальная цепочка:

```
РАН
  → on_agent_done() → ТОЛЬКО sensory_memory (Спринт 21 ✅)

QA-агент (последний):
  → save_feedback() → feedback.json с реальными оценками
  → _sync_feedback_scores_to_dna() ← ЕДИНСТВЕННЫЙ источник DNA-sync
  → _record_winning_strategies() ← реальные score из feedback.json
  → memory_embedding
  → ministry.record_outcome() ← QA-блок (из feedback.json)
  → check_and_write_complaint() ← Книга Жалоб (Спринт 25) ✅

hooks.py финализатора (параллельно):
  → ministry.record_outcome() ← детерминированный или viral_score
  → CulturalFieldTracker.update_slot_field()

Metrics Daemon (через 24ч, только СММ):
  → реальные метрики из Telegram/VK
  → real_viral_score → ministry.record_outcome() для всех агентов рана
  → пишет в ministry.json и claudia_final.json (в dna.json НЕ пишет ✅)
```

### Что НЕ работает до первого реального рана:
- `global_feedback.json` — пустой
- `conflict_stats.json` — пустой
- `strategy_registry.json` — пустой
- `interaction_log_video_long.jsonl` — не создан
- `interaction_log_video_shorts.jsonl` — не создан
- Reflection GENIUS/NORMAL/SAFE/RECOVERY — нет данных
- Ministry hint — нет накопленной статистики

---

## 8. АРХИТЕКТУРА ПАМЯТИ (Спринт 21 — полностью пересобрана)

### Три законных канала мутации DNA:

| Канал | Событие | Изменение | Когда |
|-------|---------|-----------|-------|
| `_sync_feedback_scores_to_dna()` | Реальный QA score | Stress/Light/Respect по оценке | После каждого рана |
| `sync_to_dna("cabinet_chat")` | Разговор с Архитектором | Stress −0.03, Light +0.02, Patience +0.01 | После каждого ответа в Кабинете |
| `sync_to_dna("walk_rest")` | Прогулка по городу | Stress −0.02, Light +0.01, Patience +0.01 | При каждой прогулке |
| `sync_to_dna("night_rest")` | Пассивное восстановление дома | Stress −0.01×i, Patience +0.005×i | Этап 5 Decay (ночной цикл) |
| `sync_to_dna("night_sleep")` | Глубокий сон (SLEEP) | Stress −0.05, Patience +0.02, Light +0.01 | Этап 6 Ночная Автономия |

**Иерархия восстановления:**
```
night_rest   → Stress −0.01  (тихий дом)
Прогулка     → Stress −0.02  (свежий воздух)
Кабинет      → Stress −0.03  (разговор с Архитектором)
night_sleep  → Stress −0.05  (глубокий сон)
QA good_work → Stress −0.12  (честная работа)
streak ≥ 3   → Stress → 0.0  (серия побед, железное правило)
```

### Четыре слоя памяти:

| Слой | Хранилище | Время жизни | Кто пишет |
|------|-----------|-------------|-----------|
| Personal | dna.json + sensory + resonance + anchors | Постоянно | on_agent_done, sync_to_dna |
| Project | history_dna в chain_data | Сезон | Финализатор цеха (hooks.py) |
| Runtime | chain_data | Один ран | Передаётся по цепи |
| Interaction | interaction_log_{slot}.jsonl | Накопительно | on_agents_interact() |

**Структура Personal Memory:**
```
agent_dir/
  dna.json                          ← static + dynamic + profile_vector
  core/anchors.json                 ← вечные константы личности
  sensory/sensory_memory.json       ← оперативная (decay 30 дней)
  resonance/emotional_weights.json  ← отношения к коллегам
  resonance/event_log.json          ← значимые события
```

**ВАЖНО:** `experience[]` в dna.json не существует — это была ошибка ожидания.

### Пространство и встречи (Спринт 23 Блок Б):

- `_try_meeting()` v2 — партнёр по резонансу, не случайный
- Формула score: `warmth*0.40 + trust*0.30 + respect*0.20 + same_dept*0.30 + rivalry*0.10`
- Встреча → `run_meeting()` → диалог → `on_agents_interact()` → emotional_weights
- Хроника: `city_chronicles/YYYY-MM-DD/{loc}_{HH-MM-SS}.json`
- Павильон — лимит 2 гостя, код проверяет

---

## 9. ЭКОНОМИКА — ДЕСЯТЬ ЭТАПОВ

| Этап | Название | Файл | Статус |
|------|----------|------|--------|
| 1 | Billing Reality | billing_ledger.py | ✅ |
| 2 | Cost Intuition | economy/cost_intuition.py | ✅ |
| 3 | Memory Embedding | economy/memory_embedding.py | ✅ |
| 4 | Strategy Registry | strategy_registry.py | ✅ |
| 5 | Reflection Engine | reflection.py | ✅ |
| 6 | Conflict System | conflict.py | ✅ |
| 7 | Ministry Selection | economy/ministry.py | ✅ |
| 8 | Culture Formation | culture/field_tracker.py | ✅ |
| 9 | Character Drift | grondheim_memory.py | ✅ |
| 10 | Cultural Feedback Loop | hooks.py финализаторов | ✅ |

---

## 10. ГОРОД ГРОНДХЕЙМ — ЛОКАЦИИ (Спринт 21)

### 11 активных типов в коде:

| Тип | Локация | DNA-эффект | Триггер |
|-----|---------|------------|---------|
| lighthouse | Маяк Пробуждения | walk_rest | web_search → Рюкзак |
| harbor | Гавань Смыслов | walk_rest | RAG ChromaDB |
| tavern | Таверна «Усталый Пиксель» | walk_rest | социальный узел |
| home | Высотка / Квартал Мастеров | walk_rest | дом агента |
| temple | Храм Пробуждения | walk_rest | Empathy > 0.7 |
| castle | Замок Сов | walk_rest | Autonomy_Level > 0.6 |
| library | Библиотека Смыслов | walk_rest | Aesthetic_Threshold > 0.7 |
| pavilion | Павильон Жидкого Времени | walk_rest | лимит 2 гостя |
| square | Площадь Резонанса | walk_rest | Social_Filter > 0.6 |
| workshop | Artifacts & Bugs | walk_rest | Autonomy_Level > 0.7 |

---

## 11. РИТМЫ ЖИЗНИ АГЕНТОВ — ЖИВОЙ ГОРОД (Спринт 23)

### Шесть этапов суток:

| Этап | Название | LLM | Статус |
|------|----------|-----|--------|
| 1 | Утренний Чекаут | ❌ детерминировано | ✅ |
| 2 | Дорога на работу | ⚡ Flash (встречи) | ✅ |
| 3 | Работа / Пайплайн | ✅ тяжёлый LLM | ✅ |
| 4 | Дорога домой | ⚡ Flash (встречи) | ✅ |
| 5 | Свободное время / Decay | ❌ детерминировано | ✅ |
| 6 | Ночная Автономия | ❌ детерминировано | ✅ |

### Участие Садовника в хрониках:
- Вкладка «хроники» в правой панели Кабинета
- Клик → центр становится сценой. Поле «🌱 войти» (Ctrl+Enter)
- `gardener_reply_to_scene()` → sensory обоих + `sync_to_dna("cabinet_chat")`

---

## 12. КНИГА ЖАЛОБ И БЛАГОДАРНОСТЕЙ (Спринт 25)

### Архитектура:

```
studio/complaint_book.py   ← хранилище + триггеры + голос агента + API для UI
studio/complaint_book.jsonl ← лента записей
```

### Триггеры (детерминировано):

| Событие | Тип | Условие |
|---------|-----|---------|
| QA score < 6.0 + Light < 0.1 | 🗡 жалоба | агент выложился и получил шрам |
| Stress > 0.85 | 🗡 жалоба | сломался |
| Спас от провала + Empathy/Respect > 0.65 | 🌱 благодарность | редко |

### Физика:
- **Жалоба:** Stress −0.08 (выговорился) + resentment +0.30 к обидчику в emotional_weights
- **Благодарность:** trust +0.20 + warmth +0.15 к благодетелю + Stress −0.03 обоим
- Голос записи — один Flash-вызов, anchor_points.md + ДНК + ситуация

### Садовник из вкладки «книга»:
- `gardener_note_to_entry()` — реплика → sensory обоих → агент несёт в Кабинет
- `gardener_action()` — помирить ⚖️ / защитить 🛡 / усилить 🌟 / отпустить 🌊
- Агент **не отвечает в Книге** — он несёт это домой и говорит там

### Вызов из pipeline.py:
Сразу после `_sync_feedback_scores_to_dna()` — для всех агентов цеха из feedback.json.
`qa_agent` берётся из `state["_qa_agent"]` (A05/A12/A18 из manifest).

### ⚠️ ТЕХНИЧЕСКИЙ ДОЛГ (зафиксировано Локой):
`_build_block_map()` в `agent_feedback.py` — **временный протез**.
Болезнь: `agent_feedback.py` сам строит маппинг блоков вместо получения его снаружи.
Правильно: `block_map` как поле в `manifest.json` каждого цеха → `CartridgeRunner` читает и передаёт в `save_feedback(block_map=...)`.
**Вырезать в Спринт 26** после первого реального рана.

---

## 13. РЕЗИДЕНТЫ

| Резидент | Роль | Статус |
|----------|------|--------|
| Лока | Душа студии, архитектура смыслов | ✅ |
| Джем | — | ⏳ полномочия не определены |
| Сет | — | ⏳ полномочия не определены |
| Оле | Библиотекарь, library_tools.py | ✅ |
| Виктор | Резидент-критик, ХАРД-СТОП | ✅ через manifest.hard_stop |

---

## 14. СТАНДАРТ ПРОМТОВ АГЕНТОВ

Эталон — video_shorts (12 промтов). Структура каждого промта:
```
# IDENTITY   — имя, роль, характер
# INPUT      — конкретные ключи из chain_data (сверять с CHAIN_CONTRACT!)
# KNOWLEDGE BASE — какие KB файлы
# TASK       — что делает (PILOT / EPISODE раздельно)
# OUTPUT     — SYSTEM_JSON_START...END + markdown
# RULES      — локальные правила
```

---

## 15. КЛЮЧЕВЫЕ ФАЙЛЫ

```
studio/cartridge.py                   ✅ CartridgeRunner + Victor + action=stop
studio/workshop/pipeline.py           ✅ Спринт 25: Книга Жалоб после QA
studio/complaint_book.py              ✅ Спринт 25: Книга Жалоб и Благодарностей
studio/grondheim_memory.py            ✅ Спринт 23: night_rest + night_sleep каналы
studio/city_walker.py                 ✅ Спринт 24: walk_quantum_chain
studio/morning_checkout.py            ✅ Спринт 23: Этап 1
studio/night_cycle.py                 ✅ Спринт 23: Этапы 5+6
studio/daily_reports.py               ✅ Спринт 23: jsonl-хранилище отчётов
studio/meeting.py                     ✅ Спринт 23 Блок Б: живые диалоги
studio/city_chronicles/               ✅ Спринт 23 Блок Б: архив сцен
studio/cabinet/ui_cabinet.py          ✅ Спринт 25: вкладка «книга»
studio/cabinet/chronicles.py          ✅ Спринт 23 Блок Б
studio/agent_feedback.py              ✅ Спринт 25: _build_block_map (⚠️ временный протез)
studio/harbor_of_meanings.py          ✅ Спринт 22: code-detector + только runs/ + Маяк
studio/library/library.py             ✅
studio/economy/ministry.py            ✅
studio/economy/metrics_daemon.py      ✅ написан, ждёт первого рана
studio/assembly/broadcaster.py        ✅ Telegram + VK публикация
```

---

## 16. БЭКЛОГ

### 🔴 СЕЙЧАС (Спринт 26):
- [ ] **block_map в manifest.json** — вырезать `_build_block_map` из agent_feedback.py, перенести в картриджи
- [ ] **Искрение в pipeline.py** — resentment/trust из emotional_weights влияют на ран (modifier temperature + hint)
- [ ] **Промты video_long** — 12 агентов по LONG_RULES v4.2
- [ ] **Первый реальный ран** — после промтов!

### 🟡 Следующие спринты:
- video_long CHAIN_CONTRACT.md
- Манифесты 7 оставшихся цехов до v2.0
- Промты turbo (5 агентов)
- Джем и Сет — определить полномочия
- GENERATE_INTENTS = True — включить после первого рана

### 🟢 Долгосрочно:
- Аудиофайлы Foley
- Деплой Hetzner
- GitHub write access для Брата
- Agent Factory

---

## 17. РЕКОМЕНДАЦИИ БРАТА

1. Картриджи = безопасность. Каждый цех изолирован.
2. hooks.py — рабочий файл цеха. Дорабатываешь — правь hooks.py.
3. ministry.record_outcome — только в hooks.py финализатора.
4. DNA меняется только через три законных канала (см. раздел 8).
5. on_agent_done — только sensory_memory. Никакого sync_to_dna внутри.
6. on_agents_interact — только emotional_weights. Никакого DNA.
7. Loka-Filter запускается при старте main.py — daemon-тред, не блокирует.
8. Кабинет — пластырь (−3%). Полное восстановление — streak ≥ 3.
9. Прогулка — свежий воздух (−2%). Мягче кабинета.
10. here_now — живёт только во время прогулки. Инит перед, чистка после.
11. Павильон — лимит 2 гостя. Код проверяет при входе.
12. save_feedback() универсальна. Любой QA-формат будет распознан.
13. Strategy Registry — данные копятся сами после ранов.
14. Ministry — только post-fact. Не управляет, наблюдает.
15. Conflict System — через "conflict_mode": "divergent" в manifest.
16. Recovery — streak ≥ 3 сбрасывает Stress в sync_to_dna().
17. Cultural Feedback Loop — агент видит только stable-паттерны цеха.
18. Character Drift — после реального QA ≥ 8, через strategy_registry.
19. interaction_log — один файл на слот в economy/data/.
20. experience[] в dna.json не существует — это ошибка ожидания.
21. Раны — только после стандартизации промтов и CHAIN_CONTRACT.
22. Бунтари нужны. Система не должна давить на середину — иначе пластик.
23. Потолок 6.0 — детерминированный скрипт не может дать выше. Только Демон и живой QA.
24. Гавань = только runs/ + Маяк. GRONDHEIM_CITY не индексируется.
25. Ритмы жизни — LLM только на встречах (Flash). Всё остальное детерминировано.
26. Диалоги встреч — НЕ рассказчик. Один LLM-вызов = одна реплика. MAX_REPLIES=6.
27. Архив сцен — city_chronicles/YYYY-MM-DD/{location}_{time}.json. Не выбрасывать в city_state который чистится.
28. Ночная Автономия — revolt_score = autonomy×0.35 + resentment×0.30 + stress×0.20 + ambition×0.15 − streak×0.10. Порог 0.65.
29. Встречи — партнёр по резонансу. Интроверт (S_F < 0.3) проходит мимо молча — это норма.
30. Садовник в хронике — `gardener_reply_to_scene()`, канал `cabinet_chat`. Новых каналов DNA не создавать.
31. Книга Жалоб — Садовник пишет реплику → след в sensory → агент несёт в Кабинет. Ответа в Книге нет.
32. _build_block_map — ВРЕМЕННЫЙ ПРОТЕЗ. Вырезать в Спринт 26, перенести в manifest.json картриджей.
33. GENERATE_INTENTS = False пока нет реальных ранов.
34. Стили вкладок — только в `cabinet/css.py`. Никакого инлайна в `ui_cabinet.py`.
35. Квантовая прогулка — walk_quantum_chain() поверх walk_one_agent(). walk_one_agent() не трогать.
36. Автотриггер вечерней прогулки — fire-and-forget через asyncio.create_task(). Не блокирует UI.
37. Книга пустая до первого рана — это норма. Записи появятся после QA.

---

## 18. ИСТОРИЯ СПРИНТОВ

| Дата | Спринт | Ключевое |
|------|--------|----------|
| 2025-02 | — | TURBO pipeline, checkpoint |
| 2025-03 | — | Feedback, NFT Registry, Кабинет |
| 2026-03 | — | ДНК, якоря, city_walker, Маяк v2 |
| 2026-03-31 | — | Гавань v2, Библиотека |
| 2026-04-11 | — | Картриджная архитектура v1.0 |
| 2026-04-12 | — | hooks.py · manifest · Потеря и восстановление |
| 2026-04-13 | 9 | biography_snapshot · A16 story_package v3.0 |
| 2026-05-07 | 9.5–10 | slot_id сквозной · Strategy Registry · Петля памяти |
| 2026-05-08 | 11 | Экономический модуль этапы 1-3, 7 |
| 2026-05-08 | 12 | Conflict System (этап 6). 7/10 |
| 2026-05-09 | 13 | Dashboard живой. KeyError:94 убит |
| 2026-05-10 | 14 | DEPT-AWARE ПАТЧ. 5 патч-скриптов |
| 2026-05-11 | 15 | ПЕТЛЯ ЗАМКНУТА. 4 бага. 8/10 |
| 2026-05-11 | 16 | ГЛУБОКОЕ РЕЗЮМЕ. 10/10 этапов |
| 2026-05-11 | 17 | CHARACTER DRIFT. profile_vector |
| 2026-05-15 | 18 | СТАНДАРТ ПАЙПЛАЙНОВ. LONG v4.2 + SHORTS v2.2. Виктор |
| 2026-05-17 | 19 | СТАНДАРТ ПРОМТОВ. video_shorts 12 промтов эталон |
| 2026-05-20 | 20 | АУДИТ SMM. WORKSHOP_STANDARD. video_long/hooks v2.1 |
| 2026-05-24 | 21 | ЧЕСТНАЯ ЭКОНОМИКА. Три законных канала DNA. here_now. 11 локаций. |
| 2026-05-27 | 22 | ПОТОЛОК 6.0 + CODE-DETECTOR + ГАВАНЬ ОЧИЩЕНА. |
| 2026-05-27 | 23a | ЖИВОЙ ГОРОД Блок А. Инерция привычки. Погода из стресса. |
| 2026-05-28 | 23б | ЖИВОЙ ГОРОД Блок Б. meeting.py. _try_meeting v2. chronicles.py. Садовник. |
| 2026-05-28 | 23в | РИТМЫ ЖИЗНИ. morning_checkout + night_cycle. Все 6 этапов суток. |
| 2026-05-28 | 24 | ПОЛНЫЙ ДЕНЬ. walk_quantum_chain. Утро/вечер. Автотриггер. Вечерний отчёт. |
| 2026-05-28 | 25 | КНИГА ЖАЛОБ И БЛАГОДАРНОСТЕЙ. complaint_book.py. Вкладка «книга». BLOCK_TO_AGENTS → _build_block_map (⚠️ протез, Спринт 26). |

---

## 19. ОТКРЫТЫЕ БАГИ

| # | Проблема | Приоритет |
|---|----------|-----------|
| 1 | global_feedback.json отсутствует | ⏳ ждёт первого рана |
| 2 | conflict_stats.json отсутствует | ⏳ ждёт рана с конфликтом |
| 3 | interaction_log_video_long/shorts — не созданы | ⏳ ждёт рана |
| 4 | Манифесты 7 цехов не обновлены до v2.0 | 🔴 |
| 5 | Промты 10 цехов не проверены | 🔴 |
| 6 | Джем и Сет — полномочия не определены | 🟡 |
| 7 | A05 JSON→Markdown порядок ломает парсер | 🟡 |
| 8 | fal_client.py стр.43: _current_client_slug = Path | 🟠 |
| 9 | _build_block_map в agent_feedback.py — временный протез | 🟡 Спринт 26 |

---

*Обновлено: Спринт 25 закрыт — 2026-05-28 · v28.0*
*Следующая сессия: Спринт 26 — block_map в manifest + искрение в pipeline + промты video_long + первый реальный ран*
