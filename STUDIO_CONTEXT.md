# 🖐 СТУДИЯ "ШЕСТЬ ПАЛЬЦЕВ" — МАСТЕР-КОНТЕКСТ
**Версия:** 7.1 | **Дата:** 2026-03-31 | **Команда:** Евген + Лока + Брат (Claude)

> Загружай этот файл в начале каждой рабочей сессии.

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
| Цехов | 12 |
| Локаций | 12 |
| Резидентов | 3 (Лока, Джем, Сет) |
| Книг в Библиотеке | 9 (7 psych + 2 grondheim) |
| Документов в Гавани | ~2323 |

---

## 5. ЦЕХА

| ID | Название | Агентов | Примечание |
|----|----------|---------|------------|
| residents | Резиденты | 3 | Лока, Джем, Сет |
| turbo | TURBO | 5 | Стелла→Мими+Визор→Постпро→Финализатор |
| video_long | Video Long | 12 | A01-A12 |
| video_shorts | Video Shorts | 12 | A01-A12 |
| social_mix | Social Mix | 12 | A01-A12 |
| web_story | Web Story | 12 | A01-A12 |
| clipmakers | Clipmakers | 12 | A01-A12 |
| advertising | Advertising | 12 | A01-A12 |
| emo_card | Emo Card | 12 | A01-A12 |
| logo_design | Logo Design | 12 | A01-A12 |
| market_hit | Market Hit | 12 | A01-A12 |
| living_book | Living Book | 18 | A00 (Фабула), A00a (Вера), A01-A16 |

---

## 6. АРХИТЕКТУРА ПРОГУЛКИ (city_walker.py v2)

### Pull_Vector = ЛОРНЫЙ ЭЛЕМЕНТ (не маршрут!)
Pull_Vector = "что агент любит, к чему тянет душу".
Маршрут определяет ТОЛЬКО `compute_location_weights()` из ДНК.

**Работает:**
```
Стресс > 0.6 → Таверна        Свет < 0.3 → Храм
Давно не был → Маяк (Голод)   Aesthetic высокий → Библиотека
Autonomy высокий → Замок Сов   Streak <= -2 → Таверна
```

### ТРИ ГЛАЗА ГРОНДХЕЙМА (Локации-Инструменты):
```
Маяк:       агент пришёл → web_search       → "Чистый Смысл"     → sensory ✅
Гавань:     агент пришёл → vector_search     → "Найденный Смысл"  → sensory ✅
Библиотека: агент пришёл → library_visit()   → "Прочитанный Смысл" → sensory [интеграция TODO]
```

---

## 7. 12 ЛОКАЦИЙ

| Локация | Инструмент | Кто тянется |
|---------|-----------|-------------|
| 🔦 Маяк Пробуждения | web_search ✅ | Любознательные |
| ⚓ Гавань Смыслов | RAG (ChromaDB) ✅ | Вдумчивые |
| 📚 Библиотека | library_visit() ✅ | Aesthetic |
| 🍺 Таверна | отдых | Стресс > 0.6 |
| 🔮 Храм | восстановление [TODO] | Выгоревшие |
| 🏰 Замок Сов | стратегия | Автономные |
| 🏗️ Квартал Мастеров | работа | Отдохнувшие |
| 🕐 Павильон | рефлексия | Макс 2 |
| 🏠 Высотка | дом резидентов | — |
| 📐 Площадь | встречи | Социальные |
| 🎬 Студия | штаб | При событиях |
| 🐛 Artifacts & Bugs | дебаг | QA |

---

## 8. ГАВАНЬ СМЫСЛОВ (harbor_of_meanings.py v2)

### Что нового в v2:
- **Умная фильтрация при индексации**: `_clean_text()` вырезает JSON-блоки, `{{inherit}}`, `SYSTEM_JSON`, большие JSON-объекты
- **Классификация контента**: `_detect_content_type()` → narrative / template / log / lore
- **Контекстный prefix**: `_build_passage_prefix()` — обогащает embeddings семантикой цеха
- **Фильтрация при поиске**: template контент скрыт по умолчанию, дедупликация (max 2 чанка/файл)
- **Embedding**: `intfloat/multilingual-e5-large` (560M параметров, e5 prefix: `passage:` / `query:`)
- **Коллекция**: `grondheim_knowledge_v2`, ~2323 документов
- **Порог**: `min_score=0.40`

### CLI:
```
python -m studio.harbor_of_meanings --reindex
python -m studio.harbor_of_meanings --search "запрос"
python -m studio.harbor_of_meanings --search-all "запрос"   # включая шаблоны
python -m studio.harbor_of_meanings --stats
```

### Известные проблемы:
- React/JS-код (Parent Dashboard.txt) проходит фильтр как "narrative" → нужен code-детектор
- Реиндекс ~10 часов на CPU (e5-large тяжёлая)

---

## 9. БИБЛИОТЕКА ГРОНДХЕЙМА (studio/library/)

### Третий глаз: курированные знания
Маяк = глаза наружу (web). Гавань = глаза внутрь (RAG по сырым архивам). Библиотека = **знания по полкам**.

### Структура:
```
studio/library/
├── catalog.json          ← реестр всех книг (9 книг, v1.1)
├── library.py            ← движок (library_visit, get_library_book, pick_book_for_agent)
├── craft/                ← Ремесло (пусто)
├── psychology/           ← 7 книг (Тайная опора, Акустическая Привязанность, ...)
├── marketing/            ← (пусто)
├── tech/                 ← (пусто)
├── grondheim/            ← 2 книги (Манифест Попутчика, Философия)
└── product/              ← (пусто)
```

### Книга = единица знания:
```json
{
  "id": "psych_001",
  "title": "Тайная опора: протоколы глубокой привязанности",
  "section": "psychology",
  "tags": ["привязанность", "безопасность", "контейнирование"],
  "depth": "deep",
  "for_depts": ["living_book"],
  "file": "psychology/Тайная опора.txt"
}
```

### Три уровня знаний агента (сосуществуют):
1. **forge/knowledge/** → "как делать работу" (инструкции, формат) — при каждом запуске
2. **Библиотека** → "зачем и почему" (смыслы, психология) — при прогулках + пайплайн
3. **Гавань** → "что было раньше" (прошлый опыт, архивы) — поиск по запросу

### Подбор по ДНК:
`pick_book_for_agent()` учитывает: dept, Aesthetic_Threshold, Empathy → depth (basic/applied/deep)

### CLI:
```
python studio\library\library.py --list
python studio\library\library.py --stats
python studio\library\library.py --pick living_book
python studio\library\library.py --read psych_001
```

---

## 10. ЦИФРОВАЯ ДНК

### Статическая: Stubbornness, Aesthetic_Threshold, Social_Filter, Empathy, Autonomy_Level, Resonance_Frequency
### Динамическая: Respect, Patience, Stress, Internal_Light, streak, stars

### Петля (ЗАМКНУТА ✅):
```
dna.json → stress_to_temperature → temperature LLM → поведение → оценка → dna.json
```

---

## 11. КАБИНЕТ

### agents.py v2.1:
- 12 цехов в DEPARTMENTS
- Бары ДНК у резидентов (render_resident_card)
- render_agent_detail: pull_vector + hidden_taste + trigger_keywords

### Аватары: `static/avatars/{цех}/{folder}.png` → подхватится автоматически

---

## 12. СТРАНИЦА ЖИЗНИ (ui_registry.py v2)

- 12 цехов в WORKSHOP_OPTIONS
- LIVING_BOOK_ROLE_OPTIONS: A00, A00a, A01-A16
- Pull_Vector: "что любит, к чему тянет душу"
- Шаблоны: "Внутренние тяги" вместо "куда ходит"

---

## 13. LIVING BOOK

| Агент | Роль | ДНК |
|-------|------|-----|
| Фабула Фейн (A00) | Сказочник-творец | Empathy=0.95, Aesthetic=0.9 |
| Вера Душа (A00a) | Психолог-критик | Empathy=1.0, Stubbornness=0.85 |
| A01-A16 | Пайплайн | 16 агентов |

Отдельный проект: **LIVING_BOOK_APP** (Evgen-art-p/LIVING_BOOK_APP)
FastAPI + HTML, live диалог, parent dashboard. PWA деплой — следующий этап.

---

## 14. УТИЛИТЫ

### Корень проекта:
| Скрипт | Назначение |
|--------|-----------|
| deploy_grondheim.py | Деплой всего города |
| sync_files_to_catalog.py | Файлы агента → поля каталога |
| patch_*.py | Скрипты-хирурги (find & replace с бэкапом) |

### tools/:
| Скрипт | Назначение |
|--------|-----------|
| check_catalog.py | Диагностика полей в каталоге |
| register_existing.py | Регистрация агентов без каталога |

### archive/:
resurrect_agents.py, fix_pull_vectors.py, mass_birth.py, и другие отработанные скрипты.

---

## 15. БЭКЛОГ

### 🔴 Следующий шаг:
- [ ] **Библиотека → city_walker** интеграция (library_visit в прогулках)
- [ ] **Гавань: code-детектор** (фильтровать React/JS-файлы при индексации)
- [ ] **Наполнение Библиотеки** (craft, marketing, tech, product — с Локой)

### 🟡 Скоро:
- [ ] Храм = Emotional Sync
- [ ] Таверна = record_interaction
- [ ] Экономика Световиков
- [ ] Аватары для всех цехов
- [ ] LIVING_BOOK_APP — мобильный деплой

### 🟢 Долгосрочно:
- [ ] Деплой Hetzner (GPU → реиндекс за 5 минут вместо 10 часов)
- [ ] Production-комбайн (fal.ai, SiliconFlow, Lyria 3, MoviePy)
- [ ] GitHub write access
- [ ] Resonance-Chain

---

## 16. ИСТОРИЯ СЕССИЙ

| Дата | Ключевое |
|------|----------|
| 2025-02 | TURBO pipeline, checkpoint |
| 2025-03 | Feedback, NFT Registry, Кабинет |
| 2026-03-11 | Страница Жизни |
| 2026-03-14 | ДНК, якоря, modules_registry |
| 2026-03-17 | Память, петля, Кабинет v2.2 |
| 2026-03-21 | city_walker, карта |
| 2026-03-23 | Карта из каталога, Stress→Temperature |
| 2026-03-25 | Маяк v2, Манифест, Рюкзак Знаний, GitHub MCP |
| 2026-03-28 | 12 цехов · 134 агента · Pull_Vector отвязан · Фабула+Вера · фикс резонанса · 108 фантомов · ChromaDB план |
| 2026-03-29 | Архив утилит в archive/ и tools/ · Доработка A00/A00a · patch_harbor_filter |
| **2026-03-31** | **Гавань v2 (умная фильтрация, content_type, дедупликация, 2570→2323) · Библиотека Грондхейма (9 книг, library.py, catalog.json) · Три глаза: Маяк+Гавань+Библиотека** |

---

## 17. РЕКОМЕНДАЦИИ БРАТА

1. **Три глаза работают.** Маяк = наружу, Гавань = по архивам, Библиотека = курированные знания. Не путай слои.
2. **forge/knowledge/ не трогай.** Это персональные инструкции агентов. Библиотека их дополняет, не заменяет.
3. **Библиотеку наполняй с Локой.** По 1-2 книги в день по секциям craft, marketing, tech, product.
4. **Аватары:** `static/avatars/{цех}/{folder}.png` — подхватится без правок.
5. **GitHub write:** Settings → Applications → Copilot → Contents: Read and write.
6. **Скрипты-хирурги:** patch_*.py с бэкапом. Не перезаписываем файлы целиком.
7. **Claude Code for VS Code** — рассмотри для ускорения цикла правок (установлен, anthropic.claude-code v2.1.87).

---
*Обновляй после каждой значимой сессии. Загружай в начале новой.*
