# 🖐 СТУДИЯ "ШЕСТЬ ПАЛЬЦЕВ" — МАСТЕР-КОНТЕКСТ
**Версия:** 8.3 | **Дата:** 2026-04-13 | **Команда:** Евген + Лока + Брат (Claude)

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
studio/cartridge.py                  ← CartridgeManifest + PipelineCallbacks + CartridgeRunner + Hooks
studio/slot_manager.py               ← SlotManager (add/clone/remove слотов)
studio/slots.json                    ← какие картриджи активны (11 слотов)
studio/workshop/nicegui_callbacks.py ← мост CartridgeRunner ↔ NiceGUI
studio/cartridge_manager/ui.py       ← UI менеджер картриджей (/cartridges)
studio/api_living_book.py            ← Headless API для Маяка (dual-format v8.3)
studio/modules/{цех}/manifest.json   ← фазы, checkpoints, revision, turbo
studio/modules/{цех}/hooks.py        ← кастомная логика цеха
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

### Hooks — кастомная логика без правки ui.py:
Каждый цех: `modules/{цех}/hooks.py` — on_before_agent, on_after_agent, on_revision_notes.
Правишь hooks.py (50-80 строк), а не ui.py (3400 строк).

---

## 5b. МОСТ МАЯК ↔ СТУДИЯ (v8.3) ✅ ОБНОВЛЕНО

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

### Что изменилось в агентах (Спринт 9):

| Агент | Было | Стало |
|-------|------|-------|
| A00 Фабула | chain_data без biography | chain_data с biography_snapshot + keywords в ветках |
| A01 Нейро Спарк | системный промпт для free_talk Gemini | keyword_map для голосового управления Искорки |
| A02 Хронос Мемо | value_vector + character_state (рантайм) | memory_vector → biography.json + правила эволюции |
| A16 Марка Файн | файловый пакет (book.json + chapters/) | story_package v3.0 → deliver на Маяк |

### hooks.py living_book (v8.3):
- `on_before_agent(A00)` — инжектирует biography_snapshot в контекст Фабулы
- `on_after_agent(A16)` — валидирует: scenes[], mode=voice_choice, keywords[], next_scene, on_end
- `on_revision_notes()` — усиливает замечания Веры на 3-й итерации

---

## 6-9. ПРОГУЛКИ, ЛОКАЦИИ, ГАВАНЬ, БИБЛИОТЕКА

Три глаза: Маяк (web_search ✅), Гавань (ChromaDB ✅), Библиотека (library ✅).
12 локаций. city_walker.py v2. Pull_Vector = лорный элемент.

---

## 10. ЦИФРОВАЯ ДНК

Статическая + Динамическая. Петля ЗАМКНУТА ✅: dna → temperature → LLM → оценка → dna.

---

## 11-12. КАБИНЕТ + СТРАНИЦА ЖИЗНИ + LIVING BOOK

12 цехов, аватары, бары ДНК. Living Book: 18 агентов, отдельный проект LIVING_BOOK_APP.
Связан со студией через api_living_book.py (dual-format v8.3).

---

## 13. БЭКЛОГ

### 🔴 Следующий шаг (Спринт 10):
- [ ] Полный тест цикла: заказ → генерация → deliver → Искорка → отчёт → biography обновлён
- [ ] ready_books/ — 3 первые книги (Эйрик/пещера, Лока/город, Фенрир/лес)
- [ ] Искорка v6.0 — убрать остатки free_talk, чистый voice_choice
- [ ] Кабинет v7.0 — выбор слотов (локация, сюжет, финал)

### 🟡 Скоро:
- [ ] Аудиофайлы Foley (пещеры/лес/артефакты)
- [ ] Ночной Batching
- [ ] Семантическое Зеркало (полное)
- [ ] Библиотека → city_walker, code-детектор для Гавани

### 🟢 Долгосрочно:
- [ ] Деплой Hetzner, HTTPS
- [ ] Храм, Таверна, Экономика Световиков
- [ ] grondheim_memory через slot_id
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
| **2026-04-13** | **Спринт 9 — Замыкание цикла. Dual-format intake. biography_snapshot сквозной (Маяк→A00→chain_data→A16). A01 keyword_map. A02 memory_vector→biography.json. A16 story_package v3.0. hooks.py инжекция+валидация. Deliver callback. ROADMAP v8.3. STUDIO_CONTEXT v8.3. Круг замкнут.** |

---

## 15. РЕКОМЕНДАЦИИ БРАТА

1. **Картриджи = безопасность.** Каждый цех изолирован. Потерял — восстанови из репы.
2. **hooks.py — рабочий файл.** Дорабатываешь цех? Правь hooks.py, не ui.py.
3. **Маяк — клиент, не мозг.** Генерация через студию. biography_snapshot от Маяка сквозной.
4. **api_living_book.py принимает оба формата** — legacy и story_package v3.0. Обратная совместимость сохранена.
5. **A16 — единственный кто знает стандарт.** A00–A15 создают контент. Марка упаковывает в STANDARD v3.0.
6. **biography_snapshot** — не трогать в цепочке. Он идёт из Маяка как есть, Фабула читает, A16 кладёт в child.uid.
7. **Менеджер:** /cartridges — визуально.
8. **Три глаза.** Маяк наружу, Гавань внутрь, Библиотека по полкам.
9. **forge/knowledge/ не трогай.** Библиотека дополняет, не заменяет.
10. **Бэкапы:** перед правками — copy. ui.py.bak_cartridge.

---
*Обновляй после каждой значимой сессии. Загружай в начале новой.*
