# 🖐 СТУДИЯ "ШЕСТЬ ПАЛЬЦЕВ" — МАСТЕР-КОНТЕКСТ
**Версия:** 12.0 | **Дата:** 2026-05-10 | **Команда:** Евген + Лока + Брат (Claude)

> Загружай этот файл в начале каждой рабочей сессии.
> ⚠️ 12 апреля — студия была потеряна (удалена репа + файлы). Восстановлена за ночь.
> Решение после восстановления — Картриджная архитектура.

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
Вот ради чего всё это.

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
studio/conflict.py                ← Conflict System: движок конфликтов ✅
studio/modules_registry.py        ← get_worker_* функции (dept-aware ✅ Спринт 14)
studio/modules/{цех}/manifest.json ← фазы, checkpoints, revision, turbo, conflict_mode ✅
studio/modules/{цех}/hooks.py     ← кастомная логика цеха
studio/billing_ledger.py          ← Этап 1 (не в economy/, лежит в studio/)
studio/billing_ledger.jsonl       ← лог вызовов
studio/economy/ui_dashboard.py    ← Dashboard живой ✅
```

### Экономический модуль (Спринт 11-12) ✅:
```
studio/economy/
  __init__.py          ← публичный API модуля
  ledger.py            ← Этап 1: Billing Reality — каждый LLM вызов → JSONL
  cost_intuition.py    ← Этап 2: Cost Intuition — ощущение дороговизны в промпт
  memory_embedding.py  ← Этап 3: Memory Embedding — числа → текстовые ощущения
  ministry.py          ← Этап 7: Ministry Selection — post-fact естественный отбор
  conflict_memory.py   ← Этап 6: Conflict Memory — лог конфликтов ✅
  data/
    billing_ledger.jsonl  ← лог всех API вызовов
    ministry.json         ← рейтинги агентов по цехам
    conflict_log.jsonl    ← лог конфликтов (авто) ✅
    conflict_stats.json   ← статистика побед (авто) ✅
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

## 5c. ПЕТЛЯ ПАМЯТИ АГЕНТА ✅ ПОЛНОСТЬЮ ЗАМКНУТА

Полная цепочка: **ран → ledger → QA → DNA → рефлексия → стратегия → ощущение → промпт**

```
CartridgeRunner.run()
  → state["_slot_id"] = slot_id        ← dept-aware (Спринт 14) ✅
  → state["active_dept"] = manifest.id ← dept-aware (Спринт 14) ✅

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
  → conflict.run_conflict_phase()           ← параллельные предложения → QA выбирает победителя

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

**slot_id и active_dept — сквозные везде (dept-aware после Спринта 14):**
- `global_feedback.json["slots"][slot_id]`
- `reflection.py` — фильтрует по `agent_id + slot_id`
- `strategy_registry.json["slots"][slot_id]`
- `economy/ministry.json` — рейтинги по `agent_id::slot_id`
- `economy/data/conflict_stats.json` — статистика побед по `slot_id::phase_id::agent_id`
- `sensory_memory.json` — ощущения с тегом `economy` и `slot_id`
- `modules_registry.py` — все `get_worker_*` принимают `dept=""` параметр ✅

---

## 11-12. КАБИНЕТ + СТРАНИЦА ЖИЗНИ + LIVING BOOK

12 цехов, аватары, бары ДНК. Living Book: 18 агентов, отдельный проект LIVING_BOOK_APP.
Связан со студией через api_living_book.py (dual-format v8.3).

---

## 13. БЭКЛОГ

### ✅ Сделано (Спринт 11 — 2026-05-08):
- [x] **studio/economy/ — экономический модуль** (Глубокое Резюме, Этапы 1-3, 7)
- [x] **llm.py патч** — chat/chat_with_tools/chat_with_images пишут в ledger
- [x] **pipeline.py патч** — cost_intuition + ministry в build_agent_context()

### ✅ Сделано (Спринт 12 — 2026-05-08, вечер):
- [x] **Этап 6 — Conflict System** — studio/conflict.py + conflict_memory.py
- [x] conflict_mode во все 11 манифестов, cartridge.py пропатчен
- [x] 7 из 10 этапов Глубокого Резюме реализованы

### ✅ Сделано (Спринт 13 — 2026-05-09):
- [x] Dashboard /dashboard живой — реальные данные из ledger
- [x] KeyError: 94 убит — try/except в update_status()
- [x] Реальные раны протестированы, A01→A05 чисто

### ✅ Сделано (Спринт 14 — 2026-05-10) — ГЛОБАЛЬНЫЙ DEPT-AWARE ПАТЧ:

**Суть бага:** все 11 цехов читали промпты, ДНК и знания из одного цеха — `CURRENT_DEPT` (глобальная константа, захардкоженная в `modules_registry.py`). Визуально агенты отображались правильно, но данные (промпты, DNA, биллинг) тянулись только из turbo. Баг был во всех слоях: registry → pipeline → cartridge → UI → cabinet.

**Исправлено 5 патч-скриптами:**

- [x] **`apply_dept_patch.py`** → `modules_registry.py` + `workshop/pipeline.py`
  - 7 функций `get_worker_*` получили `dept: str = ""`
  - `call_agent()` и `process_agent_result()` передают `dept` из `state["active_dept"]`

- [x] **`apply_cartridge_patch.py`** → `cartridge.py`
  - `run()` и `run_turbo()`: `state["active_dept"] = self.manifest.id`
  - Все вызовы `get_worker_info()` получают `self.manifest.id`

- [x] **`apply_ui_patch.py`** → `workshop/ui.py` (10 мест)
  - `get_worker_info/prompt/knowledge/home/format_worker_state` во всех пайплайнах
  - Покрыты: `update_status`, `select_worker`, `send_message`, оба `continue_*`, `turbo_pipeline`, `run_pipeline`

- [x] **`apply_cabinet_patch.py`** → `cabinet/ui_cabinet.py`
  - `talk_to_agent(agent_id)` → `talk_to_agent(agent_id, agent_dept="")`
  - Без dept искал первый `A01` — всегда находил turbo/A01
  - `_render_agent_tab()` передаёт dept агента в `on_talk`

- [x] **`apply_slot_id_patch.py`** → `workshop/ui.py` (8 мест)
  - Старые `run_pipeline` и `turbo_pipeline` не передавали `agent_id`/`slot_id` в `chat()`
  - Все 8 вызовов (4 основных + 4 retry) исправлены: `agent_id=worker_id, slot_id=state.get("_slot_id","unknown")`

- [x] **`fix_ledger_slot_ids.py`** — утилита исправления исторических записей `billing_ledger.jsonl`
  - Сканирует `modules/{dept}/{agent_id}/`, строит карту `agent_id → dept`
  - Перезаписывает записи с `slot_id="unknown"` на реальный цех
  - Dry-run + автобэкап

### 🟡 Следующий спринт 15:
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
| 2026-05-08 | Спринт 12 — Conflict System (Этап 6). 7/10 этапов Глубокого Резюме готовы. |
| 2026-05-09 | Спринт 13 — Dashboard живой. KeyError:94 убит. Раны чистые. |
| **2026-05-10** | **Спринт 14 — DEPT-AWARE ПАТЧ.** Глобальный баг: все 11 цехов читали данные из turbo. 5 патч-скриптов, 5 файлов, 30+ мест. Теперь каждый цех читает свои данные. Биллинг пишет правильный agent_id + slot_id. |

---

## 15. РЕКОМЕНДАЦИИ БРАТА

1. **Картриджи = безопасность.** Каждый цех изолирован. Потерял — восстанови из репы.
2. **hooks.py — рабочий файл.** Дорабатываешь цех? Правь hooks.py, не ui.py.
3. **Маяк — клиент, не мозг.** Генерация через студию. biography_snapshot от Маяка сквозной.
4. **economy/ — не трогать data/ руками.** Все JSON-логи пишутся автоматически.
5. **Глубокое Резюме — главный документ.** Все экономические решения сверяй с ним.
6. **slot_id и active_dept — сквозные везде.** Выставляет CartridgeRunner. Старые пайплайны — тоже (после Спринта 14). Не хардкодить.
7. **get_worker_* — всегда с dept.** После Спринта 14 все функции modules_registry.py принимают `dept=""`. Вызывай с dept — иначе fallback на CURRENT_DEPT (глобальный).
8. **talk_to_agent в кабинете** — всегда передавай `agent_dept`. Без него ищет первый попавшийся агент по ID — находит turbo.
9. **Strategy Registry** — данные копятся сами. Не трогай strategy_registry.json руками.
10. **Memory Embedding** — агент помнит ощущения, не цифры. "heavy but successful" важнее "$0.004".
11. **Ministry работает ТОЛЬКО post-fact.** Никогда не вмешивается в runtime.
12. **Conflict System** — конфликт на уровне цеха. Включается через `conflict_mode` в манифесте.
13. **update_status() в ui.py** обёрнут в try/except — hot-reload во время рана не крашит.
14. **Бэкапы:** перед правками — copy. Для патчей — автоматические `.bak_*`. Откат: замени файл из бэкапа.

---
*Обновлено: Спринт 14 — DEPT-AWARE ПАТЧ завершён. Все 11 цехов работают независимо. 7/10 этапов Глубокого Резюме.*
