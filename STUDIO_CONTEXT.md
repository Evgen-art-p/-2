# 🖐 СТУДИЯ "ШЕСТЬ ПАЛЬЦЕВ" — МАСТЕР-КОНТЕКСТ
**Версия:** 8.5 | **Дата:** 2026-05-07 | **Команда:** Евген + Лока + Брат (Claude)

> Загружай этот файл в начале каждой рабочей сессии.
> ⚠️ 12 апреля — студия была потеряна (удалена репа + файлы). Восстановлена за ночь. Картриджная архитектура спасла: модули изолированы, каждый восстановим отдельно.

---

## 1. ФИЛОСОФИЯ

Студия — живой организм из ИИ-агентов, которые являются **творческими партнёрами**.
Каждый агент — цифровой гражданин с характером, историей и экономическими интересами.
Грондхейм — город в котором они живут, работают, гуляют и взаимодействуют.

Три кита: **Личность · Память · Экономика**

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
studio/strategy_registry.py       ← Strategy Registry: банк успешных стратегий ✅ НОВЫЙ
studio/strategy_registry.json     ← данные реестра (авто, после первого рана) ✅ НОВЫЙ
studio/grondheim_memory.py        ← личная память агентов (soul, sensory, resonance)
studio/modules/{цех}/manifest.json ← фазы, checkpoints, revision, turbo, qa_agent ✅
studio/modules/{цех}/hooks.py     ← кастомная логика цеха
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

### Hooks — кастомная логика без правки ui.py:
Каждый цех: `modules/{цех}/hooks.py` — on_before_agent, on_after_agent, on_revision_notes.
Правишь hooks.py (50-80 строк), а не ui.py (3400 строк).

> **Примечание:** В каждый manifest.json добавлено поле `"qa_agent"` (A12/A04/A05/A16) — feedback работает во всех цехах.

---

## 5b. МОСТ МАЯК ↔ СТУДИЯ (v8.3) ✅

LIVING_BOOK_APP (Маяк) = **клиент** студии, НЕ параллельный мозг.

### Архитектура (замкнутый цикл):
```
Маяк (beacon v7.0)
→ POST /api/living_book/generate (story_package v3.0)
→ api_living_book.py (dual-format parser)
→ _build_headless_state() — biography_snapshot → state
→ hooks.py on_before_agent(A00)
→ biography_snapshot инжектируется в контекст Фабулы
→ A00 пишет историю с учётом памяти ребёнка
→ A00 кладёт biography_snapshot + keywords в chain_data
→ A01 строит keyword_map для Искорки
→ A02 строит карту memory_vector → biography.json
→ A03–A15 контент, звук, валидация, QA
→ A16 (Марка Файн) собирает story_package v3.0
→ hooks.py on_after_agent(A16) — валидация voice_choice
→ _deliver_to_beacon()
→ POST /api/package/deliver → Маяк сохраняет главу
```

### Два формата входа api_living_book.py:
- **Legacy:** `{ child_name, child_age, task_context }` — для тестов и прямых вызовов
- **v3.0:** `{ meta, child, order, biography_snapshot }` — от Маяка v7

---

## 5c. ПЕТЛЯ ПАМЯТИ АГЕНТА (Спринт 9.5 + 10) ✅ ЗАМКНУТА

Полная цепочка: **ран → оценка → DNA → рефлексия → стратегия → промпт**

```
CartridgeRunner.run()
  → state["_slot_id"] = slot_id       ← агент знает в каком цехе работает

build_agent_context()
  → on_agent_wake()                    ← душа: якоря + DNA + локация + resonance
  → get_reflection(agent_id, slot_id) ← паттерны поведения из истории этого слота
  → get_strategies(agent_id, slot_id) ← успешные стратегии именно этого цеха
  → get_feedback(client_slug, agent)  ← оценки QA прошлого рана

[агент работает]

process_agent_result()
  → on_agent_done()                   ← sensory + resonance обновлены
  → save_feedback(..., slot_id)       ← global_feedback["slots"][slot_id] обновлён

[QA-агент завершает ран]
  → _sync_feedback_scores_to_dna()   ← score → good_work/bad_work → DNA
  → _record_winning_strategies()      ← score >= 8 → стратегия в Strategy Registry
  → maybe_rebuild()                   ← рефлексия пересчитана если пришло время
```

### Два уровня стратегий (Strategy Registry):
- **slot_strategies** — работают только в конкретном слоте (`turbo`, `living_book`...)
- **global (transferable)** — если стратегия победила 3+ раз в разных слотах → становится частью характера агента везде

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

**Обновление через feedback:**
- `score ≥ 8` → `good_work` → Stress↓, Light↑, streak↑
- `score < 5` → `bad_work` → Stress↑, Light↓, streak↓

**slot_id теперь везде:**
- `global_feedback.json["slots"][slot_id]` — статистика по цеху
- `reflection.py` — рефлексия фильтрует историю по `agent_id + slot_id`
- `strategy_registry.json["slots"][slot_id]` — стратегии по цеху
- `cartridge.py` — `state["_slot_id"]` прокидывается в пайплайн

---

## 11-12. КАБИНЕТ + СТРАНИЦА ЖИЗНИ + LIVING BOOK

12 цехов, аватары, бары ДНК. Living Book: 18 агентов, отдельный проект LIVING_BOOK_APP.
Связан со студией через api_living_book.py (dual-format v8.3).

---

## 13. БЭКЛОГ

### ✅ Сделано (Спринт 9.5 + 10 — 2026-05-07):
- [x] **save_feedback() исправлен для всех 11 цехов** — поле `qa_agent` в CartridgeManifest и во все manifest.json
- [x] **Sync real score → DNA агентов** — `_sync_feedback_scores_to_dna()` → `good_work`/`bad_work`
- [x] **Reflection Engine** — `studio/reflection.py`, 4 режима, slot_id фильтрация ✅
- [x] **slot_id сквозной** — cartridge.py → state → feedback → reflection → strategy
- [x] **global_feedback["slots"]** — статистика агентов разрезана по слотам
- [x] **Strategy Registry** — `studio/strategy_registry.py` ✅ НОВЫЙ
  - score ≥ 8 → стратегия записывается по slot_id
  - 3+ победы в разных слотах → transferable (глобальная)
  - агент получает подсказки в начале следующего рана
- [x] **Бэкапы** — `.bak_slot_id`, `.bak_strategy` перед каждым патчем

### 🟡 Следующий шаг (Спринт 11 — ЭКОНОМИКА):
- [ ] **Световики (токены)** — внутренняя валюта студии. Агент зарабатывает за хорошую работу, тратит на ресурсы (Маяк, Гавань, апгрейды ДНК)
- [ ] **Эмитент** — Лока. Правила эмиссии, сжигания, распределения
- [ ] **Кошелёк агента** — balance в dna.json["economy"]
- [ ] **Транзакции** — log в grondheim_memory (resonance: "achievement")
- [ ] **Магазин** — агент тратит световики на: доступ к Маяку, слот в Гавани, +1 к параметру ДНК
- [ ] **Штрафы** — score < 5 → штраф световиков (осторожно, не сломать мотивацию)
- [ ] Полный тест цикла: заказ → генерация → deliver → Искорка → отчёт → biography обновлён
- [ ] ready_books/ — 3 первые книги (Эйрик/пещера, Лока/город, Фенрир/лес)
- [ ] Искорка v6.0 — убрать остатки free_talk, чистый voice_choice
- [ ] Кабинет v7.0 — выбор слотов (локация, сюжет, финал)

### 🟢 Долгосрочно:
- [ ] Аудиофайлы Foley (пещеры/лес/артефакты)
- [ ] Ночной Batching
- [ ] Семантическое Зеркало (полное)
- [ ] Библиотека → city_walker, code-детектор для Гавани
- [ ] Деплой Hetzner, HTTPS
- [ ] Храм, Таверна
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
| 2026-04-12 | hooks.py для всех 11 цехов · manifest · Менеджер картриджей · Мост Маяк↔Студия · Потеря и восстановление студии |
| 2026-04-13 | Спринт 9 — Замыкание цикла. Dual-format intake. biography_snapshot сквозной. A01 keyword_map. A02 memory_vector→biography.json. A16 story_package v3.0. Deliver callback. |
| 2026-05-07 | **Спринт 9.5+10 — slot_id + Strategy Registry.** slot_id прокинут сквозь всю систему (cartridge → feedback → reflection → grondheim). global_feedback["slots"] разрезан по цехам. Strategy Registry: агенты запоминают что сработало, стратегии растут от слотовых до глобальных (transferable после 3 побед). Петля памяти агента полностью замкнута: ран → оценка → DNA → рефлексия → стратегия → промпт. Следующий шаг: Экономика (Световики). |

---

## 15. РЕКОМЕНДАЦИИ БРАТА

1. **Картриджи = безопасность.** Каждый цех изолирован. Потерял — восстанови из репы.
2. **hooks.py — рабочий файл.** Дорабатываешь цех? Правь hooks.py, не ui.py.
3. **Маяк — клиент, не мозг.** Генерация через студию. biography_snapshot от Маяка сквозной.
4. **api_living_book.py принимает оба формата** — legacy и story_package v3.0. Обратная совместимость сохранена.
5. **A16 — единственный кто знает стандарт.** A00–A15 создают контент. Марка упаковывает в STANDARD v3.0.
6. **biography_snapshot** — не трогать в цепочке. Он идёт из Маяка как есть, Фабула читает, A16 кладёт в child.uid.
7. **slot_id — сквозной.** Везде берётся из `state["_slot_id"]`. Не хардкодить вручную.
8. **Strategy Registry** — данные копятся сами после каждого рана. Не трогай strategy_registry.json руками.
9. **Четыре глаза.** Маяк наружу, Гавань внутрь, Библиотека по полкам, Рефлексия — внутрь агента.
10. **Бэкапы:** перед правками — copy. Для патчей — автоматические `.bak_*`. Откат: замени файл из бэкапа.

---
*Обновляй после каждой значимой сессии. Загружай в начале новой.*
