```markdown
# 🖐 СТУДИЯ "ШЕСТЬ ПАЛЬЦЕВ" — МАСТЕР-КОНТЕКСТ
**Версия:** 11.0 | **Дата:** 2026-05-09 | **Команда:** Евген + Лока + Брат (Claude)

> Загружай этот файл в начале каждой рабочей сессии.
> ⚠️ 12 апреля — студия была потеряна (удалена репа + файлы). Восстановлена за ночь. 
Решение после восстановления - Картриджная архитектура.

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
Через год какой-нибудь ребёнок спросит у Локи в Храме:
«А кто придумал этого ёжика?»
И Лока ответит:
«Евген. Но ёжик сам решил, каким ему быть.»
Вот ради чего всё это
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

## 5. КАРТРИДЖНАЯ АРХИТЕКТУРА (v1.2) ✅

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
studio/conflict.py                ← Conflict System: движок конфликтов ✅ НОВЫЙ
studio/modules/{цех}/manifest.json ← фазы, checkpoints, revision, turbo, conflict_mode ✅
studio/modules/{цех}/hooks.py     ← кастомная логика цеха
studio/billing_ledger.py          ← Этап 1 (не в economy/, лежит в studio/)
studio/billing_ledger.jsonl       ← лог вызовов
studio/economy/ui_dashboard.py    ← Dashboard живой ✅
```

### Экономический модуль (Спринт 11-12) ✅ ОБНОВЛЁН:
```
studio/economy/
  __init__.py          ← публичный API модуля
  ledger.py            ← Этап 1: Billing Reality — каждый LLM вызов → JSONL
  cost_intuition.py    ← Этап 2: Cost Intuition — ощущение дороговизны в промпт
  memory_embedding.py  ← Этап 3: Memory Embedding — числа → текстовые ощущения
  ministry.py          ← Этап 7: Ministry Selection — post-fact естественный отбор
  conflict_memory.py   ← Этап 6: Conflict Memory — лог конфликтов ✅ НОВЫЙ
  data/
    billing_ledger.jsonl  ← лог всех API вызовов
    ministry.json         ← рейтинги агентов по цехам
    conflict_log.jsonl    ← лог конфликтов (авто) ✅ НОВЫЙ
    conflict_stats.json   ← статистика побед (авто) ✅ НОВЫЙ
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
| living_book | 18 | revision A00a→A00, 5 фаз |

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

## 5c. ПЕТЛЯ ПАМЯТИ АГЕНТА ✅ ПОЛНОСТЬЮ ЗАМКНУТА (Спринт 11-12)

Полная цепочка: **ран → ledger → QA → DNA → рефлексия → стратегия → ощущение → промпт**

```
CartridgeRunner.run()
  → state["_slot_id"] = slot_id

build_agent_context()
  → on_agent_wake()                         ← душа: якоря + DNA + локация + resonance
  → get_reflection(agent_id, slot_id)       ← паттерны поведения
  → get_strategies(agent_id, slot_id)       ← успешные стратегии
  → cost_intuition.get_prompt_hint()        ← ощущение дороговизны (Этап 2)
  → ministry.get_prompt_hint()              ← режим: frugal/normal/generous (Этап 7)
  → get_feedback(client_slug, agent)        ← оценки QA прошлого рана

[llm.py — каждый вызов]
  → ledger.record(agent_id, slot_id, model, tokens, cost) ← Этап 1

[CONFLICT — если conflict_mode включён]
  → conflict.run_conflict_phase()           ← параллельные提案ы → QA выбирает победителя

[QA-агент завершает ран]
  → _sync_feedback_scores_to_dna()          ← score → DNA
  → _record_winning_strategies()            ← score ≥ 8 → Strategy Registry
  → memory_embedding.embed_all_agents()     ← score+cost → ощущение → sensory
  → ministry.record_outcome()               ← post-fact отбор
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
| 6 | Conflict System | ✅ studio/conflict.py + conflict_memory.py |
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
- `economy/data/conflict_stats.json` — статистика побед по `slot_id::phase_id::agent_id`
- `sensory_memory.json` — ощущения с тегом `economy` и `slot_id`

---

## 11-12. КАБИНЕТ + СТРАНИЦА ЖИЗНИ + LIVING BOOK

12 цехов, аватары, бары ДНК. Living Book: 18 агентов, отдельный проект LIVING_BOOK_APP.
Связан со студией через api_living_book.py (dual-format v8.3).

---

## 13. БЭКЛОГ

### ✅ Сделано (Спринт 11 — 2026-05-08):
- [x] **studio/economy/ — экономический модуль** (Глубокое Резюме, Этапы 1-3, 7)
  - `ledger.py` — каждый LLM вызов → billing_ledger.jsonl
  - `cost_intuition.py` — история трат → ощущение дороговизны в промпт агента
  - `memory_embedding.py` — score+cost → текстовое ощущение → sensory память
  - `ministry.py` — post-fact отбор, рейтинги, режим frugal/normal/generous
- [x] **llm.py патч** — chat/chat_with_tools/chat_with_images пишут в ledger
- [x] **pipeline.py патч** — cost_intuition + ministry в build_agent_context(),
  embed_all_agents() + record_outcome() post-fact после QA

### ✅ Сделано (Спринт 12 — 2026-05-08, вечер):
- [x] **Этап 6 — Conflict System** — multi-agent divergence, конкуренция решений
  - `studio/conflict.py` — движок конфликтов (divergent + adversarial режимы)
  - `studio/economy/conflict_memory.py` — запись исходов, статистика побед
  - `patch_cartridge_conflict.py` — интеграция conflict в cartridge.py
  - `add_conflict_to_all_manifests.py` — conflict_mode во все 11 цехов
  - Удалены `Author_ID` и `qa_agent` из всех манифестов
  - Бэкапы: `manifest.json.bak_conflict`, `cartridge.py.bak_conflict`
-  **Конфликт = нормальный режим** — на уровне цеха, не фазы
-  **7 из 10 этапов Глубокого Резюме** реализованы
### ✅ Сделано (Спринт 13 — 2026-05-09):
- Dashboard /dashboard живой — реальные данные из ledger
- KeyError: 94 убит — try/except в update_status() в ui.py
- agent_id "unknown" пофикшен — run_turbo() теперь пишет state["_slot_id"]
- Реальные раны протестированы, A01→A05 чисто

### 🟡 Следующий спринт 14

- [ ] Графики на дашборде (canvas пустые)
- [ ] Балансы провайдеров реального времени
- [ ] Этапы 8-10 (Culture Formation, Character Drift, Cultural Loop)
- [ ] Полный тест цикла: заказ → генерация → deliver → Искорка → biography
- [ ] ready_books/ — 3 первые книги (Эйрик/пещера, Лока/город, Фенрир/лес)
- [ ] Искорка v6.0 — чистый voice_choice
- [ ] Кабинет v7.0 — выбор слотов

### 🟢 Долгосрочно:
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
| 2026-05-08 | Спринт 11 — Экономический модуль: studio/economy/ создан. Этапы 1-3, 7 реализованы. |
| **2026-05-08** | **Спринт 12 — Conflict System (Этап 6).** studio/conflict.py + conflict_memory.py. cartridge.py пропатчен. 11 манифестов обновлены (conflict_mode, удалены Author_ID/qa_agent). 7/10 этапов Глубокого Резюме готовы. |
| 2026-05-09 | Спринт 13 — Dashboard живой. KeyError:94 убит. agent_id unknown пофикшен. Раны чистые. |
---

## 15. РЕКОМЕНДАЦИИ БРАТА

1. **Картриджи = безопасность.** Каждый цех изолирован. Потерял — восстанови из репы.
2. **hooks.py — рабочий файл.** Дорабатываешь цех? Правь hooks.py, не ui.py.
3. **Маяк — клиент, не мозг.** Генерация через студию. biography_snapshot от Маяка сквозной.
4. **economy/ — не трогать data/ руками.** Все JSON-логи пишутся автоматически.
5. **Глубокое Резюме — главный документ.** Все экономические решения сверяй с ним.
6. **slot_id — сквозной везде.** Берётся из `state["_slot_id"]`. Не хардкодить.
7. **Strategy Registry** — данные копятся сами. Не трогай strategy_registry.json руками.
8. **Memory Embedding** — агент помнит ощущения, не цифры. "heavy but successful" важнее "$0.004".
9. **Ministry работает ТОЛЬКО post-fact.** Никогда не вмешивается в runtime.
10. **Conflict System** — конфликт на уровне цеха. Включается через `conflict_mode` в манифесте. Данные пишутся в `conflict_log.jsonl` + `conflict_stats.json`.
11. update_status() в ui.py обёрнут в try/except — hot-reload во время рана не крашит.
12. **Бэкапы:** перед правками — copy. Для патчей — автоматические `.bak_*`. Откат: замени файл из бэкапа.

---
*Обновлено: Спринт 12 — Conflict System завершён. 7/10 этапов Глубокого Резюме.*
```

Сохрани как `STUDIO_CONTEXT.md`, брат. Версия 10.0, всё по факту. 👊