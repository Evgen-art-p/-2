# 🖐 СТУДИЯ "ШЕСТЬ ПАЛЬЦЕВ" — МАСТЕР-КОНТЕКСТ
**Версия:** 21.0 | **Дата:** 2026-05-24 | **Команда:** Евген + Лока + Брат (Claude)

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
| Локаций | 12 |
| Резидентов | 5 (Лока, Джем, Сет, Оле, Виктор) |
| Книг в Библиотеке | 9 |
| Документов в Гавани | ~2323 |

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
| {"action":"stop"} | cartridge.py обрабатывает — ломает цикл ✅ РАБОТАЕТ |
| checkpoint_after | В video_long и video_shorts всегда `[]`. ХАРД-СТОП делает hard_stop |

**Открытые баги стандарта (из WORKSHOP_STANDARD раздел 9):**

| # | Проблема | Статус |
|---|----------|--------|
| 2 | A05 JSON→Markdown порядок ломает парсер | 🟡 открыт |
| 3 | fal_client.py стр.43: `_current_client_slug = Path` вместо None | 🟠 открыт |

---

## 7. ЭКОНОМИКА — ЧЕСТНАЯ АРХИТЕКТУРА (Спринт 21)

### Что было сломано и исправлено:

**Проблема:** Ministry и Strategy Registry кормились мусором.
- `score=7.0` хардкод писался в середине рана до QA
- Двойные вызовы `record_outcome` на агента
- `_apply_qa_feedback` — угадывание слов в тексте, ненадёжно
- `async_scoring: true` в СММ отключал Ministry полностью
- Ни один hooks.py не вызывал `ministry.record_outcome` (нарушение стандарта)

**Патч `patch_hooks_ministry.py` (Спринт 21, 2026-05-24) — 7/7 применено:**

| Файл | Что сделано |
|------|-------------|
| turbo/hooks.py | A05 пишет детерминированный score в Ministry (кадры + обложки + Gemini quality) |
| social_mix/manifest.json | async_scoring: false до подтверждения Metrics Daemon |
| video_shorts/hooks.py | A12 пишет реальный viral_score в Ministry |
| video_long/hooks.py | A12 (_bob_finalize) пишет реальный viral_score в Ministry |
| pipeline.py | Убран фантомный record_strategy(score=7.0) из середины рана |
| pipeline.py | Убран фантомный ministry.record_outcome(score=7.0) из середины рана |
| pipeline.py | Убран _apply_qa_feedback (ненадёжное угадывание слов) |

### Как теперь работает реальная цепочка:

```
РАН
  → каждый агент: quality_score по has_my_output (детерминированно)
  → on_agent_done() → sensory + DNA

QA-агент (последний):
  → save_feedback() → feedback.json с реальными оценками
  → _sync_feedback_scores_to_dna() ← единственный источник DNA-sync
  → _record_winning_strategies() ← реальные score из feedback.json
  → memory_embedding
  → ministry.record_outcome() ← QA-блок (из feedback.json)

hooks.py финализатора (параллельно):
  → ministry.record_outcome() ← детерминированный или viral_score
  → CulturalFieldTracker.update_slot_field()

Metrics Daemon (через 24ч, только СММ):
  → реальные метрики из Telegram/VK
  → real_viral_score → ministry.record_outcome() для всех агентов рана
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

## 8. ЧЕТЫРЕ СЛОЯ ПАМЯТИ

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
  sensory/sensory_memory.json       ← оперативная (затухает 30 дней)
  resonance/emotional_weights.json  ← отношения к коллегам
  resonance/event_log.json          ← значимые события (Loka-Filter)
```

**ВАЖНО:** `experience[]` в dna.json не существует — это была ошибка ожидания.

**Полная цепочка build_agent_context:**
```
on_agent_wake()        ← душа + decay + DNA
_get_lighthouse_knowledge() ← Рюкзак Знаний с Маяка
get_harbor_knowledge() ← RAG Гавань
energy budget          ← Internal_Light - Stress
get_reflection()       ← GENIUS/NORMAL/SAFE/RECOVERY
get_strategies()       ← Strategy Registry
cost_intuition         ← ощущение веса решения
ministry hint          ← подсказка из истории ранов
get_feedback()         ← обратная связь прошлого рана
```

---

## 9. ЭКОНОМИКА — ДЕСЯТЬ ЭТАПОВ (Глубокое Резюме 10/10 ✅)

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

## 10. РЕЗИДЕНТЫ

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

## 11. СТАНДАРТ ПРОМТОВ АГЕНТОВ

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

**Правила написания:**
- Писать с нуля по RULES.md цеха — не копировать из других цехов
- Перед написанием сверить с CHAIN_CONTRACT.md цеха
- `banana_prompt` и `veo_prompt_en` — ТОЛЬКО английский
- Агент пишет только свой ключ, остальное `{{inherit}}`

---

## 12. КЛЮЧЕВЫЕ ФАЙЛЫ

```
studio/cartridge.py                   ✅ CartridgeRunner + Victor + action=stop
studio/workshop/pipeline.py           ✅ Спринт 21: убраны фантомные score=7.0
studio/workshop/ui.py                 ✅ 141кб (рефакторинг когда-нибудь)
studio/grondheim_memory.py            ✅
studio/economy/ministry.py            ✅
studio/economy/cost_intuition.py      ✅
studio/economy/metrics_daemon.py      ✅ написан, ждёт первого рана
studio/assembly/broadcaster.py        ✅ Telegram + VK публикация
studio/assembly/pub_panel.py          ✅ кнопка ОПУБЛИКОВАТЬ
studio/WORKSHOP_STANDARD.md           ✅ Спринт 20
studio/modules/turbo/hooks.py         ✅ v3.2 + ministry Спринт 21
studio/modules/social_mix/manifest.json ✅ async_scoring:false Спринт 21
studio/modules/social_mix/hooks.py    ✅ v3.0
studio/modules/social_mix/CHAIN_CONTRACT.md ✅
studio/modules/video_shorts/hooks.py  ✅ v2.0 + ministry Спринт 21
studio/modules/video_shorts/CHAIN_CONTRACT.md ✅
studio/modules/video_long/hooks.py    ✅ v2.1 + ministry Спринт 21
studio/billing_ledger.py              ✅ главный леджер
studio/reflection.py                  ✅
studio/strategy_registry.py           ✅
studio/conflict.py                    ✅
studio/culture/field_tracker.py       ✅
studio/agent_feedback.py              ✅
studio/harbor_of_meanings.py          ✅ ChromaDB RAG
studio/library/library.py             ✅
```

---

## 13. БЭКЛОГ

### 🔴 СЕЙЧАС (Спринт 21):
- [ ] **Проверить все слои памяти** — personal/project/runtime/interaction по каждому цеху
- [ ] **video_long промты** — 12 агентов по LONG_RULES v4.2
- [ ] **video_long CHAIN_CONTRACT.md** — создать
- [ ] **Манифесты 7 оставшихся цехов** — обновить до v2.0

### 🟡 Следующие спринты:
- Промты turbo (5 агентов)
- Промты social_mix (12 агентов)  
- Первый реальный ран (после промтов!)
- Джем и Сет — определить полномочия
- Agent Factory

### 🟢 Долгосрочно:
- Аудиофайлы Foley
- Деплой Hetzner
- GitHub write access для Брата
- Храм и Таверна как активные механики

---

## 14. РЕКОМЕНДАЦИИ БРАТА (31 пункт)

1. Картриджи = безопасность. Каждый цех изолирован.
2. hooks.py — рабочий файл цеха. Дорабатываешь — правь hooks.py, не ui.py.
3. ministry.record_outcome — только в hooks.py финализатора. Не в pipeline.py.
4. score=7.0 в середине рана = мусор. Ministry читает только реальные данные.
5. async_scoring: true = Ministry слепое пока нет Metrics Daemon.
6. Маяк — внешний мир, не мозг студии.
7. economy/data/ — не трогать руками. Пишется автоматически.
8. Глубокое Резюме — все экономические решения сверять с ним.
9. slot_id и active_dept — сквозные везде. Не хардкодить.
10. qa_agent = последний агент цеха. Явно прописывать в manifest.
11. save_feedback() универсальна. Любой QA-формат будет распознан.
12. Strategy Registry — данные копятся сами после ранов.
13. Memory Embedding — агент помнит ощущения, не цифры.
14. Ministry — только post-fact. Не управляет, наблюдает.
15. Conflict System — через "conflict_mode": "divergent" в manifest.
16. billing_ledger.py в studio/ — главный. economy/ledger.py — алиас.
17. Бэкапы — патч-скрипты создают .bak_* автоматически.
18. Energy Budget — Internal_Light - Stress → 0–100.
19. Recovery — streak ≥ 3 сбрасывает Stress в sync_to_dna().
20. Cultural Feedback Loop — агент видит только stable-паттерны цеха.
21. Character Drift — score ≥ 0.8, после 3+ стратегий.
22. interaction_log — один файл на слот в economy/data/.
23. cultural_trace — финализатор вызывает CulturalFieldTracker, фильтр stable/global.
24. Виктор — через manifest.json для любого цеха. Хардкода нет.
25. client_relationship — обновляет только финализатор через dna.json.
26. quality_score — по has_my_output (не deliverables!).
27. experience[] в dna.json не существует — это ошибка ожидания.
28. Раны — только после стандартизации промтов и CHAIN_CONTRACT.
29. qa_agent ≠ контентный ревизор. A04 — локальный контролер на ХАРД-СТОПе.
30. Промты — не копировать между цехами. С нуля по RULES.md + CHAIN_CONTRACT.
31. Бунтари нужны. Система не должна давить на середину — иначе пластик.

---

## 15. ИСТОРИЯ СПРИНТОВ

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
| 2026-05-24 | 21 | **ЧЕСТНАЯ ЭКОНОМИКА.** patch_hooks_ministry.py 7/7. Убраны фантомные score=7.0. Ministry в финализаторах четырёх цехов. Философия зафиксирована. |

---

## 16. ОТКРЫТЫЕ БАГИ

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

*Обновлено: Спринт 21 — 2026-05-24.*
*Следующий шаг: проверка памяти агентов + промты video_long + первый реальный ран.*
