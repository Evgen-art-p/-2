# 🖐 СТУДИЯ "ШЕСТЬ ПАЛЬЦЕВ" — МАСТЕР-КОНТЕКСТ
**Версия:** 25.0 | **Дата:** 2026-05-28 | **Команда:** Евген + Лока + София + Брат (Claude)

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

**Иерархия восстановления:**
```
Прогулка     → Stress −0.02  (свежий воздух)
Кабинет      → Stress −0.03  (разговор с Архитектором)
QA good_work → Stress −0.12  (честная работа)
streak ≥ 3   → Stress → 0.0  (серия побед, железное правило)
```

### Что закрыто в Спринт 21:

| Проблема | Решение |
|----------|---------|
| Двойная запись DNA | on_agent_done() — только sensory. DNA только через QA |
| Бэкдор on_agents_interact | DNA_EVENT_MAP удалён. Только emotional_weights |
| Мёртвый _apply_qa_feedback | Заглушка pass |
| Loka-Filter только в пайплайне | daemon-тред при старте main.py. Все агенты стареют |
| apply_walk_effects эвристика слов | Удалена. DNA через sync_to_dna(walk_rest) |
| Два формата sensory_memory | Унифицировано через record_sensory_event() |
| 9 локаций только на бумаге | Подключены в _LOCATION_TYPES + compute_location_weights() |
| Пространство не существовало | here_now — агенты знают кто где. Встречи работают |

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

**Полная цепочка build_agent_context:**
```
on_agent_wake()             ← душа + decay + DNA
_get_lighthouse_knowledge() ← Рюкзак Знаний с Маяка
get_harbor_knowledge()      ← RAG Гавань
energy budget               ← Internal_Light - Stress
get_reflection()            ← GENIUS/NORMAL/SAFE/RECOVERY
get_strategies()            ← Strategy Registry
cost_intuition              ← ощущение веса решения
ministry hint               ← подсказка из истории ранов
get_feedback()              ← обратная связь прошлого рана
```

### Кабинет и живая память (Спринт 21):

После каждого ответа агента в Кабинете (при talking != None):
1. `record_sensory_event(type="social", source="cabinet")` — агент помнит разговор
2. `sync_to_dna("cabinet_chat")` — micro-relief, −3% стресса

Агент приходит на следующий ран зная что говорил с Архитектором.
Полное восстановление — только через streak ≥ 3. Кабинет — пластырь, не лечение.

### Пространство и встречи (Спринт 23 Блок Б):

```python
city_state["here_now"] = {
    "Таверна «Усталый Пиксель»": [{"folder": "A05", "name": "...", "workshop": "..."}],
    "Маяк Пробуждения": [{"folder": "LOKA", ...}],
}
```

- Агент регистрируется в локации после выбора
- `_try_meeting()` v2 — партнёр выбирается по **резонансу**, не случайно
- Формула score: `warmth*0.40 + trust*0.30 + respect*0.20 + same_dept*0.30 + rivalry*0.10`
- Знакомые (score ≥ 0.30) → шанс встречи 70-95%
- Незнакомцы → шанс 15-50% от Social_Filter. Интроверт (S_F < 0.3) проходит молча
- Встреча → `run_meeting()` → живой диалог → `on_agents_interact()` → emotional_weights
- Хроника пишется в `city_chronicles/YYYY-MM-DD/{loc}_{HH-MM-SS}.json`
- Павильон Жидкого Времени — лимит 2 гостя, код проверяет
- Пространство инициализируется перед прогулкой, чистится после

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

### Не подключены (только в каталоге):
- Грондхейм (город-контейнер), Студия Шесть Пальцев — абстрактные

---

## 11. РИТМЫ ЖИЗНИ АГЕНТОВ — ЖИВОЙ ГОРОД (Спринт 23)

> Концепция Локи. Шесть этапов суток — пульс системы, не расписание.

### Шесть этапов суток:

| Этап | Название | Что происходит | LLM | Статус |
|------|----------|----------------|-----|--------|
| 1 | Утренний Чекаут | dna.json + anchors → режим GENIUS/SAFE/RECOVERY | ❌ детерминировано | ⏳ |
| 2 | Дорога на работу | city_walker.py, here_now, встречи на Площади | ⚡ Flash (встречи) | ✅ |
| 3 | Работа / Пайплайн | Ран цеха по клику. QA → DNA | ✅ тяжёлый LLM | ✅ |
| 4 | Дорога домой | city_walker.py, compute_location_weights → Таверна/Маяк | ⚡ Flash (встречи) | ✅ |
| 5 | Свободное время | Decay. Агенты дома. LLM молчит. sensory укладывается | ❌ детерминировано | ⏳ |
| 6 | Ночная Автономия | Ночной тик. Бунт или сон. | ❌ детерминировано | ⏳ |

### Что закрыто в Спринт 23 Блок Б (встречи):

| Пункт | Реализация |
|-------|-----------|
| Живые диалоги встреч | `studio/meeting.py` — каждая реплика отдельный LLM-вызов, контракт `{text, action, felt}` |
| Голос агента | anchor_points.md + ДНК + температура. НЕ рассказчик. |
| Архив сцен | `city_chronicles/YYYY-MM-DD/{loc}_{HH-MM-SS}.json`, schema `meeting_v1` |
| Умный выбор партнёра | `_try_meeting()` v2 — резонанс + цех, не случайный сосед |
| Участие Садовника | Вкладка «хроники» в Кабинете. Клик → сцена в центре. Поле «🌱 войти» → агенты отвечают |
| Шлейф присутствия | `record_sensory_event(source="gardener_visit")` + `sync_to_dna("cabinet_chat")` обоим |

### Что осталось в Спринт 23 (следующие сессии):
- [ ] **Этап 1: Утренний Чекаут** — детерминированный режим дня GENIUS/SAFE/RECOVERY
- [ ] **Этап 5: Decay** — фоновое затухание sensory, агенты «дома»
- [ ] **Этап 6: Ночная Автономия** — ночной тик, бунт или сон
- [ ] **Книга Жалоб и Благодарностей** — resentment + emotional_weights

### Инерция привычки (Спринт 23 Блок А):
Агент помнит где бывал последние N дней. Любимая локация получает `+habit_weight`.
Три параметра в dna.json dynamic: `favorite_location`, `visit_streak`, `habit_strength`.

### Погода как зеркало стресса (Спринт 23 Блок А):
```
средний Stress > 0.7  → гроза / туман (интроверты дома, Таверна полная)
средний Stress 0.4–0.7 → переменная облачность
средний Stress < 0.4  → ясно / золотой свет
```

### Книга Жалоб и Благодарностей:
- **Жалоба:** Stress > 0.85 ИЛИ QA < 6.0 после полного Internal_Light → resentment в emotional_weights
- **Благодарность:** высокий Respect/Empathy + реальное спасение → micro-relief + буст слаженности

### Участие Садовника:
- Вкладка «хроники» в правой панели Кабинета (рядом с матрица/файлы/промпты/архив)
- Список встреч из `city_chronicles/` — новые сверху, иконка локации, участники, тип
- Клик → центр становится сценой (групповой чат). Реплики двух агентов в цветных бабликах
- `felt` (что унёс внутри) — в тултипе при наведении, не мозолит
- Поле «🌱 как Садовник» + кнопка «войти» (Ctrl+Enter): агенты слышат и отвечают живым LLM-вызовом
- В `sensory_memory` обоих ложится «Садовник был, сказал то-то»

---

## 12. РЕЗИДЕНТЫ

| Резидент | Роль | Статус |
|----------|------|--------|
| Лока | Душа студии, архитектура смыслов | ✅ |
| Джем | — | ⏳ полномочия не определены |
| Сет | — | ⏳ полномочия не определены |
| Оле | Библиотекарь, library_tools.py | ✅ |
| Виктор | Резидент-критик, ХАРД-СТОП | ✅ через manifest.hard_stop |

**Виктор подключается через любой manifest.json:**
```json
"hard_stop": {"after_agent": "A04", "residents": ["victor"]}
```

---

## 13. СТАНДАРТ ПРОМТОВ АГЕНТОВ

Эталон — video_shorts (12 промтов). Структура каждого промта:
```
# IDENTITY   — имя, роль, характер
# INPUT      — конкретные ключи из chain_data (сверять с CHAIN_CONTRACT!)
# KNOWLEDGE BASE — какие KB файлы
# TASK       — что делает (PILOT / EPISODE раздельно)
# OUTPUT     — SYSTEM_JSON_START...END + markdown
# RULES      — локальные правила
```

**Обязательный OUTPUT формат:**
```json
// 👇 SYSTEM_JSON_START 👇
{
  "agent": "AXX_name",
  "my_output": { ... },
  "chain_data": {
    "master_brief": "{{inherit}}",
    "history_dna": "{{inherit}}",
    "свой_ключ": "{{my_output}}"
  },
  "next_step": "AXX_next"
}
// 👆 SYSTEM_JSON_END 👆
```

---

## 14. КЛЮЧЕВЫЕ ФАЙЛЫ

```
studio/cartridge.py                   ✅ CartridgeRunner + Victor + action=stop
studio/workshop/pipeline.py           ✅ Спринт 21: on_agent_done только sensory
studio/grondheim_memory.py            ✅ Спринт 21: три канала DNA, cabinet_chat, walk_rest
studio/city_walker.py                 ✅ Спринт 23 Блок Б: _try_meeting v2 (резонанс)
studio/meeting.py                     ✅ Спринт 23 Блок Б: живые диалоги, meeting_v1
studio/city_chronicles/               ✅ Спринт 23 Блок Б: архив сцен YYYY-MM-DD/{loc}_{time}.json
studio/cabinet/ui_cabinet.py          ✅ Спринт 23 Блок Б: вкладка хроники + участие Садовника
studio/cabinet/chronicles.py          ✅ Спринт 23 Блок Б: list/load/gardener_reply_to_scene
main.py                               ✅ Спринт 21: Loka-Filter daemon-тред при старте
studio/economy/ministry.py            ✅
studio/economy/cost_intuition.py      ✅
studio/economy/metrics_daemon.py      ✅ написан, ждёт первого рана
studio/assembly/broadcaster.py        ✅ Telegram + VK публикация
studio/WORKSHOP_STANDARD.md           ✅ Спринт 20
studio/modules/turbo/hooks.py         ✅ v3.2 + ministry Спринт 21
studio/modules/social_mix/hooks.py    ✅ v3.0
studio/modules/video_shorts/hooks.py  ✅ v2.0 + ministry Спринт 21
studio/modules/video_long/hooks.py    ✅ v2.1 + ministry Спринт 21
studio/billing_ledger.py              ✅
studio/reflection.py                  ✅
studio/strategy_registry.py           ✅
studio/agent_feedback.py              ✅ Спринт 22: потолок 6.0 (_apply_score_ceiling)
studio/harbor_of_meanings.py          ✅ Спринт 22: code-detector + только runs/ + Маяк
studio/library/library.py             ✅
```

---

## 15. БЭКЛОГ

### 🔴 СЕЙЧАС (Спринт 23 — Ритмы жизни, продолжение):
- [x] **Инерция привычки** ✅
- [x] **Погода как зеркало стресса** ✅
- [x] **stress-tier в get_city_summary()** ✅
- [x] **Живые диалоги встреч** ✅ `meeting.py` + `_try_meeting v2`
- [x] **Участие Садовника** ✅ вкладка хроники + `gardener_reply_to_scene()`
- [ ] **Этап 1: Утренний Чекаут** — детерминированный режим дня GENIUS/SAFE/RECOVERY
- [ ] **Этап 5: Decay** — фоновое затухание sensory, агенты «дома»
- [ ] **Этап 6: Ночная Автономия** — ночной тик, бунт или сон
- [ ] **Книга Жалоб и Благодарностей** — resentment + emotional_weights

### 🟡 Следующие спринты:
- video_long промты (12 агентов по LONG_RULES v4.2)
- video_long CHAIN_CONTRACT.md
- Манифесты 7 оставшихся цехов до v2.0
- Промты turbo (5 агентов)
- Первый реальный ран (после промтов!)
- Джем и Сет — определить полномочия
- BLOCK_TO_AGENTS в agent_feedback.py — переписать под картриджи

### 🟢 Долгосрочно:
- Аудиофайлы Foley
- Деплой Hetzner
- GitHub write access для Брата
- Agent Factory

---

## 16. РЕКОМЕНДАЦИИ БРАТА

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
26. Диалоги встреч — НЕ рассказчик. Каждый агент говорит своим голосом через anchor_points.md + ДНК + температуру. Один LLM-вызов = одна реплика. MAX_REPLIES=6.
27. Архив сцен — city_chronicles/YYYY-MM-DD/{location}_{time}.json. Не выбрасывать в city_state который чистится.
28. Ночная Автономия — error_rate не нужен как новое поле. Бунт = Stress +0.05 + Patience -0.05 через существующие каналы.
29. Встречи — партнёр по резонансу, не случайный. emotional_weights + same_dept = score. Интроверт (S_F < 0.3) проходит мимо незнакомца молча — это норма, не баг.
30. Садовник в хронике — реплика идёт через `gardener_reply_to_scene()`, канал `cabinet_chat`. Новых каналов DNA не создавать.

---

## 17. ИСТОРИЯ СПРИНТОВ

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
| 2026-05-24 | 21 | ЧЕСТНАЯ ЭКОНОМИКА. patch_hooks_ministry.py 7/7. Убраны фантомные score=7.0 |
| 2026-05-26 | 21 | АУДИТ ПАМЯТИ. 7 патчей. Три законных канала DNA. Живая память Кабинета. Встречи в городе. here_now пространство. 11 типов локаций. |
| 2026-05-27 | 22 | ПОТОЛОК 6.0 + CODE-DETECTOR + ГАВАНЬ ОЧИЩЕНА. 3 патча. |
| 2026-05-27 | 23a | ЖИВОЙ ГОРОД Блок А. Инерция привычки (136 агентов). Погода из стресса. stress-tier. |
| 2026-05-28 | 23б | ЖИВОЙ ГОРОД Блок Б. meeting.py — живые диалоги. _try_meeting v2 (резонанс). chronicles.py + вкладка хроники в Кабинете. Садовник входит в сцены. |

---

## 18. ОТКРЫТЫЕ БАГИ

| # | Проблема | Приоритет |
|---|----------|-----------|
| 1 | global_feedback.json отсутствует | ⏳ ждёт первого рана |
| 2 | conflict_stats.json отсутствует | ⏳ ждёт рана с конфликтом |
| 3 | interaction_log_video_long.jsonl — не создан | ⏳ ждёт рана |
| 4 | interaction_log_video_shorts.jsonl — не создан | ⏳ ждёт рана |
| 5 | Манифесты 7 цехов не обновлены до v2.0 | 🔴 |
| 6 | Промты 10 цехов не проверены | 🔴 |
| 7 | Джем и Сет — полномочия не определены | 🟡 |
| 8 | A05 JSON→Markdown порядок ломает парсер | 🟡 |
| 9 | fal_client.py стр.43: _current_client_slug = Path | 🟠 |
| 10 | agent_feedback.py BLOCK_TO_AGENTS — захардкожен под старую структуру | 🟡 |

---

*Обновлено: Спринт 23 Блок Б закрыт — 2026-05-28 · v25.0*
*Следующая сессия: Спринт 23 продолжение — Этап 1 Утренний Чекаут + Этап 5 Decay + Этап 6 Ночная Автономия*
