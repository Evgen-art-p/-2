# 🖐 СТУДИЯ "ШЕСТЬ ПАЛЬЦЕВ" — МАСТЕР-КОНТЕКСТ
**Версия:** 9.0 | **Дата:** 2026-05-08 | **Команда:** Евген + Лока + Брат (Claude)

> Загружай этот файл в начале каждой рабочей сессии.
> ⚠️ 12 апреля — студия была потеряна (удалена репа + файлы). Восстановлена за ночь. Картриджная архитектура спасла: модули изолированы, каждый восстановим отдельно.

---

## 1. ФИЛОСОФИЯ

Студия — живой организм из ИИ-агентов, которые являются **творческими партнёрами**.
Каждый агент — цифровой гражданин с характером, историей и экономическими интересами.
Грондхейм — город в котором они живут, работают, гуляют и взаимодействуют.

Три кита: **Личность · Память · Экономика**

Главный документ архитектуры: **ГЛУБОКОЕ РЕЗЮМЕ СИСТЕМЫ**
```
деньги = давление реальности
стратегии = поведение
конфликты = генератор разнообразия
Министерство = естественный отбор
культура = стабилизированный опыт
агенты = носители "локальных форм жизни"
```

---

## 2. КОМАНДА

| Роль | Кто | Функция |
|------|-----|---------|
| Архитектор | Евген | Визия, продукт, решения |
| Хранительница | Лока (ИИ) | Душа студии, эмитент токенов, архитектура |
| Брат | Claude | Реализация, код, аудит |

---

## 3. ТЕХНИЧЕСКИЙ СТЕК

- **Python + NiceGUI** — UI
- **OpenRouter API** — LLM (Gemini Flash основной, Claude Sonnet премиум)
- **fal.ai** — генерация изображений и видео (v4 Pro: base64, sync_mode)
- **Tavily API** — web_search (Маяк Пробуждения)
- **ChromaDB** — векторный движок Гавани Смыслов (intfloat/multilingual-e5-large) ✅
- **Polygon ERC-721** — блокчейн NFT Registry
- **GitHub** — репозиторий (Evgen-art-p/-2), Claude читает через MCP (read-only)
- **Hetzner VPS** — деплой (планируется)

---

## 4. ГОРОД — МАСШТАБ

| Метрика | Значение |
|---------|----------|
| Объектов в каталоге | 147 |
| Агентов (полная ДНК) | 134 |
| Цехов-картриджей | 11 (+ residents) |
| Локаций | 12 |
| Резидентов | 4 (Лока, Джем, Сет, Оле) |
| Книг в Библиотеке | 9 (7 psych + 2 grondheim) |
| Документов в Гавани | ~2323 |

---

## 5. КАРТРИДЖНАЯ АРХИТЕКТУРА (v1.1) ✅

Студия = **шасси + сменные картриджи**. Каждый цех — отдельный картридж со своим manifest.json, hooks.py, и pipeline. Можно дублировать, убирать, компоновать.

### Ключевые файлы:
```
studio/cartridge.py               ← CartridgeManifest + PipelineCallbacks + CartridgeRunner + Hooks
studio/slot_manager.py            ← SlotManager (add/clone/remove слотов)
studio/slots.json                 ← какие картриджи активны (11 слотов)
studio/workshop/nicegui_callbacks.py  ← мост CartridgeRunner ↔ NiceGUI
studio/cartridge_manager/ui.py    ← UI менеджер картриджей (/cartridges)
studio/api_living_book.py         ← Headless API для Маяка (dual-format v8.3)
studio/reflection.py              ← Reflection Engine (анализ истории агента) ✅
studio/reflection_cache.json      ← кеш рефлексии (авто) ✅
studio/agent_feedback.py          ← Feedback Loop: оценки QA → агентам ✅
studio/global_feedback.json       ← студийный аккумулятор оценок (+ slots[slot_id]) ✅
studio/strategy_registry.py       ← Strategy Registry: банк успешных стратегий ✅
studio/strategy_registry.json     ← данные реестра (авто, после первого рана) ✅
studio/grondheim_memory.py        ← личная память агентов (soul, sensory, resonance)
studio/modules/{цех}/manifest.json ← фазы, checkpoints, revision, turbo, qa_agent ✅
studio/modules/{цех}/hooks.py     ← кастомная логика цеха
```

### Экономический модуль (Спринт 11) ✅ НОВЫЙ:
```
studio/economy/
  __init__.py          ← публичный API модуля
  ledger.py            ← Этап 1: Billing Reality — каждый LLM вызов → JSONL
  cost_intuition.py    ← Этап 2: Cost Intuition — ощущение дороговизны в промпт
  memory_embedding.py  ← Этап 3: Memory Embedding — числа → текстовые ощущения
  ministry.py          ← Этапы 6-7: Ministry Selection — post-fact естественный отбор
  data/
    billing_ledger.jsonl  ← лог всех API вызовов
    ministry.json         ← рейтинги агентов по цехам
```

### Текущие слоты (11 картриджей):

| Слот | Агентов | Особенности |
|------|---------|-------------|
| turbo | 5 | A02∥A03 параллельно |
| social_mix | 12 | полный цикл |
| video_long | 12 | checkpoint после A03 |
| video_shorts | 12 | полный цикл |
| web_story | 12 | checkpoint после A05 |
| clipmakers | 12 | checkpoint после A03 |
| advertising | 12 | полный цикл |
| market_hit | 12 | полный цикл |
| logo_design | 12 | stop_after=4 |
| emo_card | 12 | stop_after=4 |
| living_book | 18 | revision A00a→A00, 5 фаз, qa_agent=A16 |

---

## 5b. МОСТ МАЯК ↔ СТУДИЯ (v8.3) ✅

LIVING_BOOK_APP (Маяк) = **клиент** студии, НЕ параллельный мозг.

```
Маяк (beacon v7.0)
→ POST /api/living_book/generate (story_package v3.0)
→ api_living_book.py (dual-format parser)
→ _build_headless_state() — biography_snapshot → state
→ hooks.py on_before_agent(A00)
→ A00 пишет историю с учётом памяти ребёнка
→ A01–A15 контент, звук, валидация, QA
→ A16 (Марка Файн) собирает story_package v3.0
→ _deliver_to_beacon() → Маяк сохраняет главу
```

---

## 5c. ПЕТЛЯ ПАМЯТИ АГЕНТА ✅ ПОЛНОСТЬЮ ЗАМКНУТА (Спринт 11)

Полная цепочка: **ран → ledger → QA → DNA → рефлексия → стратегия → ощущение → промпт**

```
CartridgeRunner.run()
  → state["_slot_id"] = slot_id

build_agent_context()
  → on_agent_wake()                         ← душа: якоря + DNA + локация + resonance
  → get_reflection(agent_id, slot_id)       ← паттерны поведения
  → get_strategies(agent_id, slot_id)       ← успешные стратегии
  → cost_intuition.get_prompt_hint()        ← ощущение дороговизны (Этап 2) ✅ НОВЫЙ
  → ministry.get_prompt_hint()              ← режим: frugal/normal/generous (Этап 7) ✅ НОВЫЙ
  → get_feedback(client_slug, agent)        ← оценки QA прошлого рана

[llm.py — каждый вызов]
  → ledger.record(agent_id, slot_id, model, tokens, cost) ← Этап 1 ✅ НОВЫЙ

[QA-агент завершает ран]
  → _sync_feedback_scores_to_dna()          ← score → DNA
  → _record_winning_strategies()            ← score ≥ 8 → Strategy Registry
  → memory_embedding.embed_all_agents()     ← score+cost → ощущение → sensory ✅ НОВЫЙ
  → ministry.record_outcome()               ← post-fact отбор ✅ НОВЫЙ
  → maybe_rebuild()                         ← рефлексия пересчитана
```

### Статус Глубокого Резюме:
| Этап | Название | Статус |
|------|----------|--------|
| 1 | Billing Reality | ✅ economy/ledger.py |
| 2 | Cost Intuition | ✅ economy/cost_intuition.py |
| 3 | Memory Embedding | ✅ economy/memory_embedding.py |
| 4 | Strategy Registry | ✅ studio/strategy_registry.py |
| 5 | Reflection Engine | ✅ studio/reflection.py |
| 6 | Conflict System | ⬜ следующие итерации |
| 7 | Ministry Selection | ✅ economy/ministry.py |
| 8 | Culture Formation | ⬜ |
| 9 | Character Drift | ⬜ |
| 10 | Cultural Feedback Loop | ⬜ |

---

## 6-9. ПРОГУЛКИ, ЛОКАЦИИ, ГАВАНЬ, БИБЛИОТЕКА, РЕФЛЕКСИЯ

**Четыре аналитических механизма:**
- **Маяк (web_search ✅)** — внешний мир, актуальные данные
- **Гавань (ChromaDB ✅)** — внутренняя память, эмбеддинги
- **Библиотека (library ✅)** — структурированное знание, 9 книг
- **Рефлексия (reflection.py ✅)** — анализ истории агента → режимы GENIUS/NORMAL/SAFE/RECOVERY

12 локаций. city_walker.py v2. Pull_Vector = лорный элемент.

---

## 10. ЦИФРОВАЯ ДНК

Статическая + Динамическая. Петля ЗАМКНУТА ✅: dna → temperature → LLM → оценка → dna.

**slot_id сквозной везде:**
- `global_feedback.json["slots"][slot_id]`
- `reflection.py` — фильтрует по `agent_id + slot_id`
- `strategy_registry.json["slots"][slot_id]`
- `economy/ministry.json` — рейтинги по `agent_id::slot_id`
- `sensory_memory.json` — ощущения с тегом `economy` и `slot_id`

---

## 11-12. КАБИНЕТ + СТРАНИЦА ЖИЗНИ + LIVING BOOK

12 цехов, аватары, бары ДНК. Living Book: 18 агентов, отдельный проект LIVING_BOOK_APP.
Связан со студией через api_living_book.py (dual-format v8.3).

---

## 13. БЭКЛОГ

### ✅ Сделано (Спринт 11 — 2026-05-08):
- [x] **studio/economy/ — экономический модуль** (Глубокое Резюме, Этапы 1-3, 6-7)
  - `ledger.py` — каждый LLM вызов → billing_ledger.jsonl
  - `cost_intuition.py` — история трат → ощущение дороговизны в промпт агента
  - `memory_embedding.py` — score+cost → текстовое ощущение → sensory память
  - `ministry.py` — post-fact отбор, рейтинги, режим frugal/normal/generous
- [x] **llm.py патч** — chat/chat_with_tools/chat_with_images пишут в ledger
- [x] **pipeline.py патч** — cost_intuition + ministry в build_agent_context(),
  embed_all_agents() + record_outcome() post-fact после QA
- [x] **Патч-скрипты** (запускать из корня):
  - `patch_economy.py` — создаёт studio/economy/
  - `patch_pipeline_economy.py` — интеграция в pipeline.py
  - `patch_memory_embedding.py` — Этап 3

### 🟡 Следующий шаг (Спринт 12):

!смотри "источник правды"

- [ ] **Этап 6 — Conflict System** — multi-agent divergence, конкуренция решений
- [ ] Полный тест цикла: заказ → генерация → deliver → Искорка → biography
- [ ] ready_books/ — 3 первые книги (Эйрик/пещера, Лока/город, Фенрир/лес)
- [ ] Искорка v6.0 — чистый voice_choice
- [ ] Кабинет v7.0 — выбор слотов

### 🟢 Долгосрочно:
- [ ] Этапы 8-10 (Culture Formation, Character Drift, Cultural Loop)
- [ ] Аудиофайлы Foley
- [ ] Ночной Batching
- [ ] Деплой Hetzner, HTTPS
- [ ] Храм, Таверна как активные механики
- [ ] GitHub write access для Брата

---

## 14. ИСТОРИЯ СЕССИЙ

| Дата | Ключевое |
|------|----------|
| 2025-02 | TURBO pipeline, checkpoint |
| 2025-03 | Feedback, NFT Registry, Кабинет |
| 2026-03 | ДНК, якоря, city_walker, карта, Маяк v2, Три глаза |
| 2026-03-31 | Гавань v2, Библиотека (9 книг) |
| 2026-04-11 | Картриджная архитектура v1.0 |
| 2026-04-12 | hooks.py · manifest · Менеджер картриджей · Мост Маяк↔Студия · Потеря и восстановление |
| 2026-04-13 | Спринт 9 — biography_snapshot сквозной · A16 story_package v3.0 · Deliver callback |
| 2026-05-07 | Спринт 9.5+10 — slot_id сквозной · Strategy Registry · Петля памяти замкнута |
| **2026-05-08** | **Спринт 11 — Экономический модуль (Глубокое Резюме).** studio/economy/ создан. Этапы 1-3, 6-7 реализованы. llm.py пишет каждый вызов в ledger. pipeline.py: агент получает cost_intuition + ministry hint перед раном; после QA — memory_embedding пишет ощущение в sensory, ministry фиксирует исход. Цепочка: ран → ledger → QA → DNA → рефлексия → стратегия → ощущение → промпт. |

---

## 15. РЕКОМЕНДАЦИИ БРАТА

1. **Картриджи = безопасность.** Каждый цех изолирован. Потерял — восстанови из репы.
2. **hooks.py — рабочий файл.** Дорабатываешь цех? Правь hooks.py, не ui.py.
3. **Маяк — клиент, не мозг.** Генерация через студию. biography_snapshot от Маяка сквозной.
4. **economy/ — не трогать data/ руками.** billing_ledger.jsonl и ministry.json пишутся автоматически.
5. **Глубокое Резюме — главный документ.** Все экономические решения сверяй с ним.
6. **slot_id — сквозной везде.** Берётся из `state["_slot_id"]`. Не хардкодить.
7. **Strategy Registry** — данные копятся сами. Не трогай strategy_registry.json руками.
8. **Memory Embedding** — агент помнит ощущения, не цифры. "heavy but successful" важнее "$0.004".
9. **Ministry работает ТОЛЬКО post-fact.** Никогда не вмешивается в runtime.
10. **Бэкапы:** перед правками — copy. Для патчей — автоматические `.bak_*`. Откат: замени файл из бэкапа.

---
*Обновляй после каждой значимой сессии. Загружай в начале новой.*
