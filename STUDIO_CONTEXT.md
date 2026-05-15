# 🖐 СТУДИЯ "ШЕСТЬ ПАЛЬЦЕВ" — МАСТЕР-КОНТЕКСТ
**Версия:** 17.0 | **Дата:** 2026-05-15 | **Команда:** Евген + Лока + Брат (Claude)

> Загружай этот файл в начале каждой рабочей сессии.
> ⚠️ 12 апреля — студия была потеряна (удалена репа + файлы). Восстановлена за ночь.
> Решение после восстановления — Картриджная архитектура.

---

## 1. ФИЛОСОФИЯ

Студия — живой организм из ИИ-агентов, которые являются **творческими партнёрами**.
Каждый агент — цифровой гражданин с характером, историей и экономическими интересами.
Грондхейм — город в котором они живут, работают, гуляют и взаимодействуют.

Три кита: **Личность · Память · Экономика**

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
| Хранительница | Лока (ИИ) | Душа студии, архитектура, концепты |
| Брат | Claude | Реализация, код, аудит, последнее слово |

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
| Резидентов | 5 (Лока, Джем, Сет, Оле, Виктор) |
| Книг в Библиотеке | 9 (7 psych + 2 grondheim) |
| Документов в Гавани | ~2323 |

---

## 5. КАРТРИДЖНАЯ АРХИТЕКТУРА (v1.3) ✅

Студия = **шасси + сменные картриджи**. Каждый цех — отдельный картридж со своим manifest.json, hooks.py, и pipeline.

### Ключевые файлы:
```
studio/cartridge.py                      ✅
studio/slot_manager.py                   ✅
studio/slots.json                        ✅ 11 активных слотов
studio/workshop/pipeline.py              ✅ ПРОПАТЧЕН Спринт 18
studio/grondheim_memory.py               ✅ ПРОПАТЧЕН Спринт 18
studio/economy/
  cost_intuition.py                      ✅
  ministry.py                            ✅
  memory_embedding.py                    ✅
  conflict_memory.py                     ✅
  ledger.py                              ✅ алиас billing_ledger
  data/
    ministry.json                        ✅
    interaction_log_turbo.jsonl          ✅ СОЗДАН Спринт 18 (пустой, ждёт рана)
    interaction_log_video_long.jsonl     ⏳ создастся при первом ране video_long
    interaction_log_video_shorts.jsonl   ⏳ создастся при первом ране video_shorts
studio/billing_ledger.py                 ✅ главный леджер
studio/billing_ledger.jsonl              ✅ 5 ранов turbo зафиксированы
studio/culture/field_tracker.py          ✅
studio/reflection.py                     ✅
studio/agent_feedback.py                 ✅
studio/strategy_registry.py             ✅
studio/strategy_registry.json           ✅ 1 стратегия (накопится после ранов)
studio/conflict.py                       ✅
studio/modules_registry.py              ✅
studio/economy/ui_dashboard.py          ✅
```

### Текущие слоты (11 картриджей):

| Слот | Агентов | Особенности | Manifest статус |
|------|---------|-------------|-----------------|
| turbo | 5 | A02∥A03 параллельно | ✅ v2.0 Спринт 18 |
| social_mix | 12 | полный цикл | ⏳ проверить |
| video_long | 12 | checkpoint A04 + Виктор | ⏳ проверить + подключить Виктора |
| video_shorts | 12 | checkpoint A04 + Виктор | ⏳ проверить + подключить Виктора |
| web_story | 12 | checkpoint A05 | ⏳ проверить |
| clipmakers | 12 | checkpoint A03 | ⏳ проверить |
| advertising | 12 | полный цикл | ⏳ проверить |
| market_hit | 12 | полный цикл | ⏳ проверить |
| logo_design | 12 | stop_after=4 | ⏳ проверить |
| emo_card | 12 | stop_after=4 | ⏳ проверить |
| living_book | 18 | revision A00a→A00, 5 фаз | ⏳ проверить |

---

## 5b. МОСТ МАЯК ↔ СТУДИЯ (v8.3) ✅

```
Маяк → POST /api/living_book/generate → api_living_book.py
     → hooks.py → A00–A16 → story_package v3.0 → Маяк
```

---

## 5c. ПЕТЛЯ ПАМЯТИ АГЕНТА ✅ ПОЛНОСТЬЮ ЗАМКНУТА

### Реальная архитектура памяти (уточнено Спринт 18):

**dna.json** хранит: характер (static) + динамика (dynamic) + profile_vector (Character Drift)
**НЕ хранит** experience[] — это была ошибка ожидания.

Реальные слои памяти агента:
```
agent_dir/
  dna.json                    ← характер + динамика + profile_vector
  core/anchors.json           ← якоря идентичности (вечные)
  sensory/sensory_memory.json ← оперативная память (30-дневное затухание)
  resonance/resonance_log.json← значимые события (долгоживущие)
```

Полная цепочка:
```
CartridgeRunner.run()
  → build_agent_context()
      → on_agent_wake()         ← душа + decay + DNA
      → get_reflection()
      → get_strategies()
      → CulturalFieldTracker()
      → energy budget
      → profile_vector
      → cost_intuition
      → ministry hint
      → get_feedback()

[llm.py — каждый вызов]
  → billing_ledger.record()

[process_agent_result() — ПРОПАТЧЕН]
  → quality_score по my_output (не deliverables!) ← ИСПРАВЛЕНО Спринт 18
  → on_agent_done()             ← sensory + resonance + sync_to_dna
  → on_agents_interact()        ← emotional_weights + interaction_log ← ИСПРАВЛЕНО Спринт 18

[QA-агент — последний в цехе]
  → save_feedback()
  → _sync_feedback_scores_to_dna()
  → _record_winning_strategies()
  → memory_embedding.embed_all_agents()
  → ministry.record_outcome()
  → maybe_rebuild()

[После пайплайна]
  → CulturalFieldTracker().update_slot_field()
```

### Патчи Спринта 18:
| Файл | Что исправлено |
|------|----------------|
| studio/workshop/pipeline.py | quality_score: has_deliverables → has_my_output. Промежуточные агенты больше не получают bad_work зря |
| studio/grondheim_memory.py | on_agents_interact() теперь пишет в interaction_log_{slot}.jsonl |
| studio/modules/turbo/manifest.json | v2.0: qa_agent, interaction_log путь, memory_layers |

### Статус Глубокого Резюме — 10/10 ✅:
| Этап | Название | Статус |
|------|----------|--------|
| 1 | Billing Reality | ✅ |
| 2 | Cost Intuition | ✅ |
| 3 | Memory Embedding | ✅ |
| 4 | Strategy Registry | ✅ |
| 5 | Reflection Engine | ✅ |
| 6 | Conflict System | ✅ |
| 7 | Ministry Selection | ✅ |
| 8 | Culture Formation | ✅ |
| 9 | Character Drift | ✅ |
| 10 | Cultural Feedback Loop | ✅ |

---

## 6. ЧЕТЫРЕ СЛОЯ ПАМЯТИ — СТАНДАРТ СТУДИИ

| Слой | Хранилище | Время жизни | Владелец |
|------|-----------|-------------|----------|
| Personal | dna.json + sensory + resonance + anchors | Постоянно | Каждый агент |
| Project | history_dna | Сезон/проект | Финализатор цеха |
| Runtime | chain_data | Один прогон | Передаётся по цепи |
| Interaction ✨ | interaction_log_{slot}.jsonl | Накопительно | on_agents_interact() |

**Interaction Layer — три этапа накопления:**
1. Сейчас: логирование (пишем, не влияем на промты)
2. После 10+ ранов: пассивная аналитика (Министерство видит паттерны)
3. После 30+ ранов: слабые сигналы → cultural_trace → давление вероятностей

---

## 7. РЕЗИДЕНТЫ (5)

| Резидент | Роль | Где активен | Статус |
|----------|------|-------------|--------|
| Лока | Душа студии, архитектура | Везде | ✅ |
| Джем | — | ⏳ аудит Спринт 18 | ⏳ |
| Сет | — | ⏳ аудит Спринт 18 | ⏳ |
| Оле | Библиотекарь | library_tools.py | ✅ |
| **Виктор** ✨ | Резидент-критик, ХАРД-СТОП | video_long, video_shorts | ⏳ подключить через manifest.json |

**Виктор подключается через manifest.json:**
```json
"hard_stop": {
  "after_agent": "A04",
  "residents": ["victor"]
}
```

---

## 8. АНАЛИТИЧЕСКИЕ МЕХАНИЗМЫ

- **Маяк** (web_search ✅) — внешний мир
- **Гавань** (ChromaDB ✅) — внутренняя память, ~2323 документов
- **Библиотека** (library ✅) — 9 книг
- **Рефлексия** (reflection.py ✅) — GENIUS/NORMAL/SAFE/RECOVERY

---

## 9. ПАЙПЛАЙНЫ — АКТУАЛЬНЫЕ ВЕРСИИ

| Пайплайн | Версия | Файл | Статус |
|----------|--------|------|--------|
| VIDEO_LONG | v4.1 | LONG_RULES_v4.1.md | ✅ |
| VIDEO_SHORTS | v2.1 | SHORTS_RULES_v2.1.md | ✅ |
| TURBO | v3.0 | TURBO_RULES.md | ✅ |
| Остальные 8 | — | — | ⏳ стандартизировать |

**Стандарт студии для всех пайплайнов:**
- Четыре слоя памяти (Personal / Project / Runtime / Interaction)
- interaction_log: `studio/economy/data/interaction_log_{слот}.jsonl`
- cultural_trace: из CulturalFieldTracker, не вручную
- client_relationship: в dna.json финализатора + history_dna
- Виктор на ХАРД-СТОПе: через manifest.json → "residents": ["victor"]
- Финализатор обновляет все четыре слоя памяти
- qa_agent явно прописан в manifest.json

---

## 10. БЭКЛОГ

### ✅ Сделано (Спринт 18 — 2026-05-15):
- [x] **SHORTS_RULES v2.1** — обновлён под стандарт студии, Interaction Layer
- [x] **patch_quality_and_interaction.py** — quality_score исправлен, interaction_log пишется
- [x] **patch_turbo_manifest.py** — manifest turbo v2.0, qa_agent, memory_layers
- [x] **interaction_log_turbo.jsonl** — создан, ждёт первого рана
- [x] **Архитектура памяти уточнена** — experience[] не в dna.json, а в sensory/resonance

### ✅ Сделано (Спринт 17):
- [x] Character Drift — update_profile_vector()
- [x] Графики на дашборде починены
- [x] economy/ledger.py — алиас

### ✅ Сделано (Спринт 16):
- [x] Cultural Feedback Loop (Этап 10)
- [x] Resource Economy — energy budget
- [x] Recovery Mechanics

### 🔴 ПРЯМО СЕЙЧАС (Спринт 18 продолжение):

**A. Промты и генерация — настройка перед ранами:**
```
Для каждого цеха проверить промты агентов:
- соответствие новой архитектуре памяти (4 слоя)
- chain_data корректно передаётся
- JSON-формат вывода соблюдён
- knowledge base актуальны
```

**B. Манифесты — привести к стандарту (патч для каждого):**
```
⏳ social_mix/manifest.json    → version 2.0, qa_agent, interaction_log
⏳ video_long/manifest.json    → version 2.0, qa_agent, interaction_log + Виктор
⏳ video_shorts/manifest.json  → version 2.0, qa_agent, interaction_log + Виктор
⏳ web_story/manifest.json     → version 2.0, qa_agent, interaction_log
⏳ clipmakers/manifest.json    → version 2.0, qa_agent, interaction_log
⏳ advertising/manifest.json   → version 2.0, qa_agent, interaction_log
⏳ market_hit/manifest.json    → version 2.0, qa_agent, interaction_log
⏳ logo_design/manifest.json   → version 2.0, qa_agent, interaction_log
⏳ emo_card/manifest.json      → version 2.0, qa_agent, interaction_log
⏳ living_book/manifest.json   → version 2.0, qa_agent, interaction_log
```

**C. hooks.py — проверить каждый цех:**
```
⏳ turbo/hooks.py       ✅ v3.1 — не трогать
⏳ video_long/hooks.py  → актуален?
⏳ video_shorts/hooks.py→ актуален?
⏳ остальные 8 цехов    → есть hooks.py? нужен?
```

**D. Виктор — подключить к manifest.json:**
```
⏳ video_long/manifest.json   → "hard_stop": {"after_agent": "A04", "residents": ["victor"]}
⏳ video_shorts/manifest.json → "hard_stop": {"after_agent": "A04", "residents": ["victor"]}
```

**E. Первый реальный ран (только после A+B+C+D):**
```
⏳ Запустить turbo — проверить появление:
   studio/modules/turbo/{T1}/sensory/sensory_memory.json
   studio/economy/data/interaction_log_turbo.jsonl
   dna.json агентов — Stress не должен расти
```

### 🟡 Следующие спринты:
- Полный тест цикла: заказ → генерация → deliver
- Agent Factory
- ready_books/ — 3 первые книги
- Разобрать полномочия Джема, Сета (аудит)
- Стандартизировать промты всех цехов

### 🟢 Долгосрочно:
- Аудиофайлы Foley
- Ночной Batching
- Деплой Hetzner, HTTPS
- Храм, Таверна как активные механики
- GitHub write access для Брата

---

## 11. ИСТОРИЯ СЕССИЙ

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
| 2026-05-08 | Спринт 11 — Экономический модуль. Этапы 1-3, 7 |
| 2026-05-08 | Спринт 12 — Conflict System (Этап 6). 7/10 этапов |
| 2026-05-09 | Спринт 13 — Dashboard живой. KeyError:94 убит |
| 2026-05-10 | Спринт 14 — DEPT-AWARE ПАТЧ. 5 патч-скриптов, 30+ мест |
| 2026-05-11 | **Спринт 15 — ПЕТЛЯ ЗАМКНУТА.** 4 системных бага закрыты. 8/10 этапов |
| 2026-05-11 | **Спринт 16 — ГЛУБОКОЕ РЕЗЮМЕ ЗАВЕРШЕНО.** 10/10 этапов активны |
| 2026-05-11 | **Спринт 17 — CHARACTER DRIFT ЗАКРЫТ.** profile_vector. Дубль биллинга закрыт |
| 2026-05-15 | **Спринт 18 — СТАНДАРТ ПАЙПЛАЙНОВ + ПАТЧИ ПАМЯТИ.** SHORTS v2.1, TURBO manifest v2.0, quality_score исправлен, interaction_log подключён. Архитектура памяти уточнена. |

---

## 12. РЕКОМЕНДАЦИИ БРАТА

1. **Картриджи = безопасность.** Каждый цех изолирован.
2. **hooks.py — рабочий файл.** Дорабатываешь цех? Правь hooks.py, не ui.py.
3. **Маяк — клиент, не мозг.**
4. **economy/data/ — не трогать руками.** Все JSON/JSONL пишутся автоматически.
5. **Глубокое Резюме — главный документ.** Все экономические решения сверяй с ним.
6. **slot_id и active_dept — сквозные везде.** Не хардкодить.
7. **QA-агент = последний в цехе.** Явно прописывать в manifest.json → qa_agent.
8. **save_feedback() универсальна.** Любой QA-формат будет распознан.
9. **Strategy Registry** — данные копятся сами после ранов.
10. **Memory Embedding** — агент помнит ощущения, не цифры.
11. **Ministry работает ТОЛЬКО post-fact.**
12. **Conflict System** — включается через "conflict_mode": "divergent" в manifest.json.
13. **billing_ledger.py в studio/** — главный. economy/ledger.py — алиас.
14. **Бэкапы:** патч-скрипты создают .bak_* автоматически.
15. **Energy Budget** — считается из DNA: Internal_Light - Stress.
16. **Recovery Mechanics** — streak ≥ 3 сбрасывает Stress в sync_to_dna().
17. **Cultural Feedback Loop** — агент видит только stable-паттерны цеха.
18. **Character Drift** — срабатывает при score ≥ 0.8, после 3+ стратегий.
19. **interaction_log** — один файл на слот: interaction_log_{слот}.jsonl в economy/data/.
20. **cultural_trace** — финализатор запрашивает CulturalFieldTracker, не генерирует сам.
21. **Виктор** — подключается через manifest.json: "residents": ["victor"]. Пишет victor_critique в chain_data.
22. **client_relationship** — обновляет только финализатор цеха через dna.json.
23. **quality_score** — считается по has_my_output (не deliverables!). Промежуточные агенты не получают bad_work.
24. **experience[] в dna.json не существует** — история агента в sensory/sensory_memory.json и resonance/resonance_log.json.
25. **Раны — только после стандартизации манифестов и проверки промтов.** Грязные данные в registry/ministry сложно чистить.

---

## 13. ИЗВЕСТНЫЕ ОТКРЫТЫЕ БАГИ

| # | Проблема | Приоритет |
|---|----------|-----------|
| 1 | global_feedback.json отсутствует | ⏳ ждёт первого рана |
| 2 | conflict_stats.json отсутствует | ⏳ ждёт рана с конфликтом |
| 3 | knowledge.py — 265 байт, заглушка | 🟡 возможен импорт-ошибка |
| 4 | instances/ — legacy папка | 🟢 некритично |
| 5 | ui_registry.py — 111KB, вероятно мёртвый код | 🟢 некритично |
| 6 | interaction_log_video_long.jsonl — не создан | ⏳ ждёт рана video_long |
| 7 | interaction_log_video_shorts.jsonl — не создан | ⏳ ждёт рана video_shorts |
| 8 | Манифесты 10 цехов (кроме turbo) — не обновлены до v2.0 | 🔴 Спринт 18 |
| 9 | Виктор не подключён к video_long и video_shorts | 🔴 Спринт 18 |
| 10 | Промты цехов не проверены под новую архитектуру | 🔴 перед ранами |
| 11 | Джем и Сет — полномочия не определены | 🟡 Спринт 19 |

---

*Обновлено: Спринт 18 — 2026-05-15. Патчи памяти применены. Turbo manifest v2.0. Следующий шаг — манифесты остальных 10 цехов + проверка промтов + Виктор → потом первые реальные раны.*
