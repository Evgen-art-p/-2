# 🖐 СТУДИЯ "ШЕСТЬ ПАЛЬЦЕВ" — МАСТЕР-КОНТЕКСТ
**Версия:** 13.0 | **Дата:** 2026-05-11 | **Команда:** Евген + Лока + Брат (Claude)

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

## 5. КАРТРИДЖНАЯ АРХИТЕКТУРА (v1.3) ✅

Студия = **шасси + сменные картриджи**. Каждый цех — отдельный картридж со своим manifest.json, hooks.py, и pipeline. Можно дублировать, убирать, компоновать. **Цех может быть любой комплектации** — QA-агент определяется динамически как последний в пайплайне.

### Ключевые файлы:
```
studio/cartridge.py               ← CartridgeRunner ✅ (Спринт 14+15)
studio/slot_manager.py            ← SlotManager
studio/slots.json                 ← 11 активных слотов
studio/workshop/pipeline.py       ← пайплайн ✅ (Спринт 15)
studio/workshop/nicegui_callbacks.py
studio/cartridge_manager/ui.py    ← UI менеджер /cartridges
studio/api_living_book.py         ← Headless API для Маяка (dual-format v8.3)
studio/reflection.py              ← Reflection Engine ✅
studio/agent_feedback.py          ← Feedback Loop ✅ (Спринт 15: универсальный)
studio/strategy_registry.py       ← Strategy Registry ✅
studio/strategy_registry.json     ← данные (наполняется после ранов)
studio/global_feedback.json       ← студийный аккумулятор (⏳ после первого рана)
studio/grondheim_memory.py        ← личная память агентов
studio/conflict.py                ← Conflict System ✅ (Спринт 15: работает)
studio/culture/field_tracker.py   ← Этап 8 Culture Formation ✅ ПОДКЛЮЧЁН (Спринт 15)
studio/modules_registry.py        ← get_worker_* (dept-aware ✅)
studio/modules/{цех}/manifest.json ← фазы, checkpoints, conflict_mode ✅
studio/modules/{цех}/hooks.py     ← кастомная логика цеха
studio/billing_ledger.py          ← Этап 1 (главный леджер, в studio/)
studio/billing_ledger.jsonl       ← лог вызовов
studio/economy/ui_dashboard.py    ← Dashboard ✅
```

### Экономический модуль (Спринт 11-12) ✅:
```
studio/economy/
  cost_intuition.py    ← Этап 2: ощущение дороговизны в промпт
  memory_embedding.py  ← Этап 3: числа → текстовые ощущения
  ministry.py          ← Этап 7: post-fact естественный отбор
  conflict_memory.py   ← Этап 6: лог конфликтов
  ledger.py            ← ⚠️ МЁРТВЫЙ ДУБЛЬ billing_ledger.py (не подключён)
  data/
    ministry.json
    conflict_stats.json  ← ⏳ появится после первого рана с конфликтом
    conflict_log.jsonl
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
Маяк → POST /api/living_book/generate → api_living_book.py
     → hooks.py → A00–A16 → story_package v3.0 → Маяк
```

---

## 5c. ПЕТЛЯ ПАМЯТИ АГЕНТА ✅ ПОЛНОСТЬЮ ЗАМКНУТА (Спринт 15)

Полная цепочка: **ран → billing → QA (любой агент) → DNA → стратегии → культура**

```
CartridgeRunner.run()
  → state["_slot_id"] = slot_id
  → state["active_dept"] = manifest.id
  → state["_qa_agent"] = последний агент цеха ✅ (Спринт 15)

build_agent_context()
  → on_agent_wake()              ← душа: якоря + DNA + локация
  → get_reflection()             ← паттерны поведения
  → get_strategies()             ← успешные стратегии (реальные оценки ✅ Спринт 15)
  → cost_intuition.get_prompt_hint()
  → ministry.get_prompt_hint()
  → get_feedback()               ← оценки QA прошлого рана

[llm.py — каждый вызов]
  → billing_ledger.record(...)

[CONFLICT — если conflict_mode != "none"]
  → conflict.run_conflict_phase()  ✅ теперь реально срабатывает (Спринт 15)

[QA-агент — последний в цехе]
  → save_feedback()              ← универсальный парсер score ✅ (Спринт 15)
  → _sync_feedback_scores_to_dna()
  → _record_winning_strategies() ← реальный score от QA ✅ (Спринт 15)
  → memory_embedding.embed_all_agents()
  → ministry.record_outcome()
  → maybe_rebuild()              ← рефлексия

[После пайплайна — cartridge.py]
  → CulturalFieldTracker().update_slot_field(slot_id) ✅ Этап 8 (Спринт 15)
```

### Статус Глубокого Резюме:
| Этап | Название | Статус |
|------|----------|--------|
| 1 | Billing Reality | ✅ billing_ledger.py |
| 2 | Cost Intuition | ✅ economy/cost_intuition.py |
| 3 | Memory Embedding | ✅ economy/memory_embedding.py |
| 4 | Strategy Registry | ✅ исправлен (Спринт 15) |
| 5 | Reflection Engine | ✅ studio/reflection.py |
| 6 | Conflict System | ✅ исправлен (Спринт 15) |
| 7 | Ministry Selection | ✅ economy/ministry.py |
| 8 | Culture Formation | ✅ подключён (Спринт 15) |
| 9 | Character Drift | ⬜ |
| 10 | Cultural Feedback Loop | ⬜ (field_tracker готов, нужно читать в build_agent_context) |

---

## 6-9. ПРОГУЛКИ, ЛОКАЦИИ, ГАВАНЬ, БИБЛИОТЕКА, РЕФЛЕКСИЯ

**Четыре аналитических механизма:**
- **Маяк (web_search ✅)** — внешний мир
- **Гавань (ChromaDB ✅)** — внутренняя память, эмбеддинги
- **Библиотека (library ✅)** — структурированное знание, 9 книг
- **Рефлексия (reflection.py ✅)** — GENIUS/NORMAL/SAFE/RECOVERY режимы

12 локаций. city_walker.py v2. Pull_Vector = лорный элемент.

---

## 10. ЦИФРОВАЯ ДНК

Статическая + Динамическая. Петля ЗАМКНУТА ✅.
**slot_id и active_dept — сквозные везде (dept-aware, Спринт 14).**

---

## 11-12. КАБИНЕТ + LIVING BOOK

12 цехов, аватары, бары ДНК. Living Book: 18 агентов.
Связан со студией через api_living_book.py (dual-format v8.3).

---

## 13. БЭКЛОГ

### ✅ Сделано (Спринт 15 — 2026-05-11):
- [x] **conflict_mode в CartridgeManifest** — конфликты теперь реально срабатывают
- [x] **Динамический QA-агент** — последний в цехе, не хардкод A12
- [x] **Универсальный save_feedback()** — blocks / otk_checklist / status / прямой score
- [x] **Убран record_strategy(score=7.0)** — стратегии пишутся с реальными оценками
- [x] **field_tracker подключён** — Этап 8 Culture Formation работает
- [x] **agent_ids в save_feedback()** — pipeline передаёт список агентов рана

### 🟡 Следующий спринт 16:
- [ ] **Этап 10 — Cultural Feedback Loop** (читать culture поле в build_agent_context)
- [ ] **Resource Economy — energy budget** (самая мощная незаделанная идея)
- [ ] **Recovery Mechanics** (streak ≥ 3 → Stress = 0)
- [ ] **Убить дублирование биллинга** (economy/ledger.py → alias)
- [ ] **Графики на дашборде** (canvas пустые, данные есть)
- [ ] Полный тест цикла: заказ → генерация → deliver → Искорка → biography
- [ ] ready_books/ — 3 первые книги (Эйрик/пещера, Лока/город, Фенрир/лес)

### 🟢 Долгосрочно:
- [ ] Этап 9 — Character Drift (profile_vector в dna.json)
- [ ] Agent Factory
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
| 2026-03 | ДНК, якоря, city_walker, карта, Маяк v2 |
| 2026-03-31 | Гавань v2, Библиотека (9 книг) |
| 2026-04-11 | Картриджная архитектура v1.0 |
| 2026-04-12 | hooks.py · manifest · Менеджер · Мост Маяк↔Студия · Потеря и восстановление |
| 2026-04-13 | Спринт 9 — biography_snapshot · A16 story_package v3.0 |
| 2026-05-07 | Спринт 9.5+10 — slot_id сквозной · Strategy Registry · Петля памяти |
| 2026-05-08 | Спринт 11 — Экономический модуль. Этапы 1-3, 7. |
| 2026-05-08 | Спринт 12 — Conflict System (Этап 6). 7/10 этапов. |
| 2026-05-09 | Спринт 13 — Dashboard живой. KeyError:94 убит. |
| 2026-05-10 | Спринт 14 — DEPT-AWARE ПАТЧ. 5 патч-скриптов, 30+ мест. |
| **2026-05-11** | **Спринт 15 — ПЕТЛЯ ЗАМКНУТА.** Диагностика выявила 4 системных бага: conflict_mode не читался из manifest, QA=A12 хардкодом, save_feedback только для A12, record_strategy писал score=7.0. Один патч-скрипт (apply_sprint15_patch.py), 8 фиксов. Этап 8 подключён. 8/10 этапов Глубокого Резюме готовы. |

---

## 15. РЕКОМЕНДАЦИИ БРАТА

1. **Картриджи = безопасность.** Каждый цех изолирован.
2. **hooks.py — рабочий файл.** Дорабатываешь цех? Правь hooks.py, не ui.py.
3. **Маяк — клиент, не мозг.**
4. **economy/ — не трогать data/ руками.** Все JSON пишутся автоматически.
5. **Глубокое Резюме — главный документ.** Все экономические решения сверяй с ним.
6. **slot_id и active_dept — сквозные везде.** Не хардкодить.
7. **get_worker_* — всегда с dept.** Иначе fallback на CURRENT_DEPT.
8. **QA-агент = последний в цехе.** Не нужно добавлять A12 в кастомные цеха — система сама найдёт QA. Если хочешь явно — пропиши `"qa_agent": "A05"` в manifest.json.
9. **save_feedback() универсальна.** Любой QA-формат (blocks / otk_checklist / status) будет распознан.
10. **Strategy Registry** — данные копятся сами после ранов с реальными оценками.
11. **Memory Embedding** — агент помнит ощущения, не цифры.
12. **Ministry работает ТОЛЬКО post-fact.**
13. **Conflict System** — включается через `"conflict_mode": "divergent"` в manifest.json (уже стоит в 11 манифестах).
14. **billing_ledger.py в studio/** — главный. economy/ledger.py — мёртвый дубль, не подключать.
15. **Бэкапы:** патч-скрипты создают `.bak_*` автоматически.

---

*Обновлено: Спринт 15 — Петля памяти полностью замкнута. 8/10 этапов Глубокого Резюме активны. Первый реальный ран создаст global_feedback.json, conflict_stats.json, culture/data/.*
