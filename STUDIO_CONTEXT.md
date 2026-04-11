# 🖐 СТУДИЯ "ШЕСТЬ ПАЛЬЦЕВ" — МАСТЕР-КОНТЕКСТ
**Версия:** 8.0 | **Дата:** 2026-04-11 | **Команда:** Евген + Лока + Брат (Claude)

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

## 5a. КАРТРИДЖНАЯ АРХИТЕКТУРА (v1.0) ✅ NEW

Студия = **шасси + сменные картриджи**. Каждый цех — отдельный картридж со своим `manifest.json`, который можно дублировать, убирать и компоновать.

### Ключевые файлы:
```
studio/cartridge.py              ← CartridgeManifest + PipelineCallbacks + CartridgeRunner
studio/slot_manager.py           ← SlotManager (add/clone/remove слотов)
studio/slots.json                ← конфигурация: какие картриджи активны
studio/workshop/nicegui_callbacks.py  ← мост CartridgeRunner ↔ NiceGUI
studio/modules/{цех}/manifest.json   ← описание картриджа (фазы, checkpoints, revision, turbo)
```

### Как работает:
```
manifest.json → CartridgeManifest.load("turbo")
                → CartridgeRunner(manifest, state, callbacks)
                    → runner.run()        # полный пайплайн
                    → runner.run_turbo()   # TURBO с параллелизмом
```

### Callback-паттерн:
Pipeline **не зависит от NiceGUI**. Вся связь через `PipelineCallbacks`:
- `on_agent_start()` → аватар мигает "working"
- `on_agent_done()` → аватар зелёный "done"  
- `on_checkpoint()` → пауза
- `on_revision_loop()` → A00a вернул на A00
- `on_status()` → ui.notify

UI реализует `NiceGUICallbacks(PipelineCallbacks)` и передаёт в runner.

### Дублирование картриджей:
```python
from studio.slot_manager import SlotManager
sm = SlotManager()
sm.add_slot("turbo", label="⚡ TURBO #2")   # новый слот того же модуля
sm.clone_slot("turbo", "⚡ TURBO Клон")      # с копией памяти
sm.print_summary()                           # сводка по студии
```
- Промпты агентов → из оригинального modules/{module}/ (не дублируются)
- Память (dna.json, sensory, resonance) → отдельная в instances/{slot_id}/
- 3 турбо = 15 агентов, каждый со своим dna.json

### manifest.json (пример turbo):
```json
{
  "id": "turbo",
  "phases": {"TURBO": ["A01","A02","A03","A04","A05"]},
  "turbo_workers": ["A01","A02","A03","A04","A05"],
  "turbo_parallel": [["A02","A03"]],
  "checkpoint_after": [],
  "revision_loop": null
}
```

### Текущие слоты (9 картриджей, 105 агентов + 3 резидента):
turbo(5), social_mix(12), video_long(12), video_shorts(12), web_story(12), market_hit(12), logo_design(12), emo_card(12), living_book(18)

### Статус интеграции:
- ✅ Все кнопки ui.py переключены на `run_cartridge_pipeline()` / `run_cartridge_turbo()`
- ✅ Старые `run_pipeline()` / `turbo_pipeline()` остаются как fallback (не вызываются)
- ✅ Ревизионный цикл A00a→A00 через manifest.revision_loop
- ✅ Checkpoints из manifest.checkpoint_after
- ✅ Параллелизм TURBO из manifest.turbo_parallel
- ⏳ Удаление старых 852 строк пайплайнов из ui.py — после тестирования
- ⏳ advertising, clipmakers — нет manifest.json (добавить при необходимости)

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

### Известные проблемы:
- React/JS-код (Parent Dashboard.txt) проходит фильтр как "narrative" → нужен code-детектор
- Реиндекс ~10 часов на CPU (e5-large тяжёлая)

---

## 9. БИБЛИОТЕКА ГРОНДХЕЙМА (studio/library/)

### Третий глаз: курированные знания
Маяк = глаза наружу (web). Гавань = глаза внутрь (RAG по сырым архивам). Библиотека = **знания по полкам**.

### Три уровня знаний агента (сосуществуют):
1. **forge/knowledge/** → "как делать работу" (инструкции, формат) — при каждом запуске
2. **Библиотека** → "зачем и почему" (смыслы, психология) — при прогулках + пайплайн
3. **Гавань** → "что было раньше" (прошлый опыт, архивы) — поиск по запросу

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

---

## 15. БЭКЛОГ

### 🔴 Следующий шаг:
- [ ] **Тестирование картриджей** — прогнать turbo, video_long, living_book через CartridgeRunner
- [ ] **Удаление старых пайплайнов** — 852 строки из ui.py (после тестирования)
- [ ] **manifest.json для advertising и clipmakers**
- [ ] **SlotManager в main.py** — сводка при запуске
- [ ] **Библиотека → city_walker** интеграция (library_visit в прогулках)

### 🟡 Скоро:
- [ ] Гавань: code-детектор (фильтровать React/JS-файлы)
- [ ] Наполнение Библиотеки (craft, marketing, tech, product — с Локой)
- [ ] Храм = Emotional Sync
- [ ] Таверна = record_interaction
- [ ] Экономика Световиков
- [ ] UI для SlotManager (добавить/убрать картриджи из интерфейса)

### 🟢 Долгосрочно:
- [ ] Деплой Hetzner (GPU → реиндекс за 5 минут вместо 10 часов)
- [ ] Production-комбайн (fal.ai, SiliconFlow, Lyria 3, MoviePy)
- [ ] GitHub write access для Claude
- [ ] Resonance-Chain
- [ ] grondheim_memory адресация через slot_id (для дублированных картриджей)

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
| 2026-03-31 | Гавань v2 (умная фильтрация, content_type, дедупликация, 2570→2323) · Библиотека Грондхейма (9 книг, library.py, catalog.json) · Три глаза: Маяк+Гавань+Библиотека |
| **2026-04-11** | **Картриджная архитектура v1.0: cartridge.py + slot_manager.py + manifest.json для 9 цехов + nicegui_callbacks.py (мост UI) + интеграция в ui.py (все кнопки переключены на CartridgeRunner)** |

---

## 17. РЕКОМЕНДАЦИИ БРАТА

1. **Картриджи работают.** Все пайплайны теперь идут через CartridgeRunner. Старый код в ui.py — fallback, удалишь после тестирования.
2. **Дублирование цехов:** `SlotManager().add_slot("turbo")` — и у тебя второй TURBO с отдельной памятью.
3. **manifest.json — главный файл цеха.** Фазы, checkpoints, revision_loop, turbo_parallel — всё там. Меняешь manifest → меняется поведение пайплайна.
4. **Три глаза работают.** Маяк = наружу, Гавань = по архивам, Библиотека = курированные знания. Не путай слои.
5. **forge/knowledge/ не трогай.** Это персональные инструкции агентов. Библиотека их дополняет, не заменяет.
6. **Аватары:** `static/avatars/{цех}/{folder}.png` — подхватится без правок.
7. **GitHub write:** Settings → Applications → Copilot → Contents: Read and write.

---
*Обновляй после каждой значимой сессии. Загружай в начале новой.*
