# 🖐 СТУДИЯ "ШЕСТЬ ПАЛЬЦЕВ" — МАСТЕР-КОНТЕКСТ
**Версия:** 20.0 | **Дата:** 2026-05-20 | **Команда:** Евген + Лока + Брат (Claude)

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
- **fal.ai** — генерация изображений и видео (v4 Pro: base64, sync_mode) · модель: `fal-ai/nano-banana-2`
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
studio/cartridge.py                          ✅ ПРОПАТЧЕН Спринт 20 (action=stop + Victor)
studio/slot_manager.py                       ✅
studio/slots.json                            ✅ 11 активных слотов
studio/workshop/pipeline.py                  ✅ ПРОПАТЧЕН Спринт 18
studio/grondheim_memory.py                   ✅ ПРОПАТЧЕН Спринт 18
studio/economy/
  cost_intuition.py                          ✅
  ministry.py                                ✅
  memory_embedding.py                        ✅
  conflict_memory.py                         ✅
  ledger.py                                  ✅ алиас billing_ledger
  data/
    ministry.json                            ✅
    interaction_log_turbo.jsonl              ✅ создан Спринт 18
    interaction_log_video_long.jsonl         ⏳ создастся при первом ране
    interaction_log_video_shorts.jsonl       ⏳ создастся при первом ране
studio/billing_ledger.py                     ✅ главный леджер
studio/billing_ledger.jsonl                  ✅ 5 ранов turbo
studio/culture/field_tracker.py              ✅
studio/reflection.py                         ✅
studio/agent_feedback.py                     ✅
studio/strategy_registry.py                 ✅
studio/strategy_registry.json               ✅
studio/conflict.py                           ✅
studio/modules_registry.py                  ✅
studio/economy/ui_dashboard.py              ✅
studio/modules/video_long/manifest.json      ✅ v2.0 ПРОПАТЧЕН Спринт 19
studio/modules/video_shorts/manifest.json    ✅ v2.0 ПРОПАТЧЕН Спринт 19
studio/modules/video_shorts/hooks.py         ✅ v2.0 ПРОПАТЧЕН Спринт 19 (A07 + A12 fal.ai)
studio/modules/video_shorts/CHAIN_CONTRACT.md ✅ СОЗДАН Спринт 19
studio/modules/social_mix/manifest.json      ✅ v2.0 ГОТОВ Спринт 20
studio/modules/social_mix/hooks.py           ✅ v3.0 ПРОПАТЧЕН Спринт 20
studio/modules/social_mix/CHAIN_CONTRACT.md  ✅ СОЗДАН Спринт 20
studio/modules/video_long/hooks.py           ✅ v2.1 СОЗДАН Спринт 20
studio/WORKSHOP_STANDARD.md                  ✅ СОЗДАН Спринт 20
studio/ui_registry.py                        ✅ ПРОПАТЧЕН Спринт 18
```

### Текущие слоты (11 картриджей):

| Слот | Агентов | Особенности | Manifest | hooks.py | Промты |
|------|---------|-------------|----------|----------|--------|
| turbo | 5 | A02∥A03 параллельно | ✅ v2.0 | ✅ v3.2 | ⏳ |
| social_mix | 12 | полный цикл, POST+PLAN | ✅ v2.0 | ✅ v3.0 | ⏳ |
| video_long | 12 | hard_stop A04 + Виктор, qa=A12 | ✅ v2.0 | ✅ v2.1 | ⏳ |
| video_shorts | 12 | hard_stop A04 + Виктор, qa=A12 | ✅ v2.0 | ✅ v2.0 | ✅ Спринт 19 |
| web_story | 12 | checkpoint A05 | ⏳ | ⏳ | ⏳ |
| clipmakers | 12 | checkpoint A03 | ⏳ | ⏳ | ⏳ |
| advertising | 12 | полный цикл | ⏳ | ⏳ | ⏳ |
| market_hit | 12 | полный цикл | ⏳ | ⏳ | ⏳ |
| logo_design | 12 | stop_after=4 | ⏳ | ⏳ | ⏳ |
| emo_card | 12 | stop_after=4 | ⏳ | ⏳ | ⏳ |
| living_book | 18 | revision A00a→A00, 5 фаз | ⏳ | ⏳ | ⏳ |

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
  dna.json                          ← характер + динамика + profile_vector
  core/anchors.json                 ← якоря идентичности (вечные)
  sensory/sensory_memory.json       ← оперативная память (30-дневное затухание)
  resonance/emotional_weights.json  ← личные отношения к коллегам (warmth/trust/respect)
  resonance/event_log.json          ← значимые события (долгоживущие, Loka-Filter)
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
| studio/workshop/pipeline.py | quality_score: has_deliverables → has_my_output |
| studio/grondheim_memory.py | on_agents_interact() пишет в interaction_log_{slot}.jsonl |
| studio/modules/turbo/manifest.json | v2.0: qa_agent=T5, interaction_log, memory_layers |
| studio/modules/video_long/manifest.json | v2.0: qa_agent=A12, hard_stop+Виктор, убраны мусорные поля |
| studio/modules/video_shorts/manifest.json | v2.0: qa_agent=A12, hard_stop+Виктор, убраны мусорные поля |
| studio/modules/video_shorts/hooks.py | A01/A08/A12: history_dna, compatibility_snapshot, CulturalFieldTracker |
| studio/ui_registry.py | TURBO_ROLE_OPTIONS: единая A-нотация |

### Патчи Спринта 19:
| Файл | Что исправлено |
|------|----------------|
| studio/modules/video_shorts/manifest.json | checkpoint_after: [] (убрана двойная остановка), interaction_log: полный путь |
| studio/modules/video_long/manifest.json | checkpoint_after: [] (убрана двойная остановка), interaction_log: полный путь |
| studio/cartridge.py | Victor: убран хардкод _victor_depts, теперь читает из manifest.hard_stop |
| studio/modules/video_shorts/hooks.py | Добавлен хук A07 (fal.ai генерация кадров Веры), A12 (fal.ai генерация обложки A/B), починен _parse_json_block (приоритет маркеров SYSTEM_JSON) |
| studio/modules/video_shorts/ | Написаны 12 промтов агентов строго по SHORTS_RULES v2.2 |
| studio/modules/video_shorts/CHAIN_CONTRACT.md | Создан контракт ключей chain_data — источник правды по структурам |

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

**Структура Personal Memory на диске:**
```
agent_dir/
  dna.json                          ← static + dynamic + profile_vector
  core/anchors.json                 ← вечные константы личности
  sensory/sensory_memory.json       ← оперативная память (затухает 30 дней)
  resonance/emotional_weights.json  ← отношения к коллегам (warmth/trust/respect)
  resonance/event_log.json          ← значимые события (Loka-Filter)
```

**Interaction Layer — три этапа накопления:**
1. Сейчас: просто логирование (без влияния на промпты)
2. После 10+ ранов: пассивная аналитика (Министерство видит паттерны)
3. После 30+ ранов: слабые сигналы → cultural_trace → давление вероятностей

---

## 7. РЕЗИДЕНТЫ (5)

| Резидент | Роль | Где активен | Статус |
|----------|------|-------------|--------|
| Лока | Душа студии, архитектура | Везде | ✅ |
| Джем | — | ⏳ аудит Спринт 19 | ⏳ |
| Сет | — | ⏳ аудит Спринт 19 | ⏳ |
| Оле | Библиотекарь | library_tools.py | ✅ |
| **Виктор** ✨ | Резидент-критик, ХАРД-СТОП | любой цех с hard_stop+victor в manifest | ✅ |

**Виктор подключается через manifest.json (работает для любого цеха):**
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

| Пайплайн | Версия | Файл RULES | Manifest | hooks.py | Промты | Контракт |
|----------|--------|-----------|----------|----------|--------|----------|
| VIDEO_LONG | v4.2 | LONG_RULES_v4_2.md | ✅ v2.0 | ⏳ | ⏳ | ⏳ |
| VIDEO_SHORTS | v2.2 | SHORTS_RULES_v2_2.md | ✅ v2.0 | ✅ v2.0 | ✅ | ✅ |
| TURBO | v3.1 | TURBO_RULES_v3_1.md | ✅ v2.0 | ✅ v3.2 | ⏳ | ⏳ |
| Остальные 8 | — | — | ⏳ | ⏳ | ⏳ | ⏳ |

**Стандарт студии для всех пайплайнов:**
- Четыре слоя памяти (Personal / Project / Runtime / Interaction)
- interaction_log: `studio/economy/data/interaction_log_{слот}.jsonl`
- cultural_trace: из CulturalFieldTracker.update_slot_field() → фильтр stable/global
- client_relationship: в dna.json финализатора + history_dna
- Виктор на ХАРД-СТОПе: через manifest.json → "residents": ["victor"]
- qa_agent = последний агент цеха (A12 для 12-агентных, T5 для turbo, A04 для stop_after=4)
- Финализатор обновляет все четыре слоя памяти
- **CHAIN_CONTRACT.md** — обязателен для каждого цеха (источник правды по ключам chain_data)

---

## 10. СТАНДАРТ ПРОМТОВ АГЕНТОВ ✅ ЗАФИКСИРОВАН Спринт 19

### Эталон: video_shorts (12 промтов написаны заново)

Структура каждого промта:
```
# IDENTITY   — имя, роль, emoji, характер, обращение «Шеф»
# INPUT      — что читает из chain_data (конкретные ключи)
# KNOWLEDGE BASE — какие файлы KB использует
# TASK       — что делает (PILOT / EPISODE раздельно)
# OUTPUT     — SYSTEM_JSON_START...END + markdown для Шефа
# RULES      — локальные правила агента
```

### Обязательный OUTPUT формат:
```
👇 SYSTEM_JSON_START 👇
{
  "agent": "AXX_name",
  "agent_name": "Имя",
  "mode": "PILOT | EPISODE",
  "stage": "pre-prod | prod | post-prod",
  "my_output": { ... },
  "chain_data": {
    "master_brief": "{{inherit}}",
    "history_dna": "{{inherit}}",
    ... все ключи предыдущих агентов через {{inherit}} ...
    "свой_ключ": "{{my_output}}"
  },
  "next_step": "AXX_next"
}
👆 SYSTEM_JSON_END 👆
```

### Правила написания промтов:
| # | Правило |
|---|---------|
| 1 | Писать с нуля по RULES.md цеха — не копировать из других цехов |
| 2 | Перед написанием сверить INPUT и chain_data с CHAIN_CONTRACT.md цеха |
| 3 | `banana_prompt` и `veo_prompt_en` — ТОЛЬКО английский |
| 4 | Формат ВСЕГДА 9:16 для вертикальных цехов |
| 5 | `ref_ids` — только реальные asset_id из history_dna.character_memory |
| 6 | Агент пишет только свой ключ, остальное `{{inherit}}` |
| 7 | Два ключа (PILOT/EPISODE) — пишется только один в зависимости от режима |

---

## 11. БЭКЛОГ

### ✅ Сделано (Спринт 19 — 2026-05-17):
- [x] **Аудит video_shorts** — найдены и исправлены баги: checkpoint_after двойная остановка, обрезанный путь interaction_log, хардкод _victor_depts в cartridge.py
- [x] **patch_sprint19.py** — патч двух манифестов + cartridge.py, dry-run режим, автобэкапы
- [x] **video_shorts/hooks.py v2.0** — добавлен A07 (fal.ai генерация кадров Веры параллельно), A12 (fal.ai генерация обложки A/B), починен _parse_json_block
- [x] **video_shorts промты** — все 12 агентов написаны заново строго по SHORTS_RULES v2.2
- [x] **CHAIN_CONTRACT.md** — создан для video_shorts: таблица всех ключей, структуры, правила, чеклист
- [x] **cartridge.py** — Victor активируется из manifest.hard_stop для любого цеха (не хардкод)
- [x] **STUDIO_CONTEXT v19.0** — обновлён

### ✅ Сделано (Спринт 18 — 2026-05-15/16):
- [x] SHORTS_RULES v2.1→2.2, LONG_RULES v4.1→4.2
- [x] patch_quality_and_interaction.py, patch_turbo_manifest.py, patch_sprint18_video.py
- [x] video_long + video_shorts manifest.json v2.0
- [x] video_shorts/hooks.py v1.0 (A01/A08/A12)
- [x] Виктор подключён через manifest.json
- [x] ui_registry.py — TURBO_ROLE_OPTIONS единая A-нотация
- [x] turbo/hooks.py v3.2

### 🔴 ПРЯМО СЕЙЧАС (Спринт 19 продолжение):

**A. Манифесты — 8 оставшихся цехов:**
```
✅ social_mix/manifest.json    v2.0 — готов
⏳ web_story/manifest.json     → version 2.0, qa_agent=A12, interaction_log
⏳ clipmakers/manifest.json    → version 2.0, qa_agent=A12, interaction_log
⏳ advertising/manifest.json   → version 2.0, qa_agent=A12, interaction_log
⏳ market_hit/manifest.json    → version 2.0, qa_agent=A12, interaction_log
⏳ logo_design/manifest.json   → version 2.0, qa_agent=A04 (stop_after=4)
⏳ emo_card/manifest.json      → version 2.0, qa_agent=A04 (stop_after=4)
⏳ living_book/manifest.json   → version 2.0, qa_agent=A18 (последний из 18)
```

**B. hooks.py + промты + CHAIN_CONTRACT — по цехам:**
```
✅ turbo/hooks.py        v3.2 — не трогать
✅ video_shorts/hooks.py v2.0 — готов
✅ video_long/hooks.py   v2.1 — готов (A06 Eva + A08 Felix + A11 Tracy + A12 Bob)
⏳ video_long промты     → 12 агентов по LONG_RULES v4.2
⏳ video_long/CHAIN_CONTRACT.md → создать
✅ social_mix/CHAIN_CONTRACT.md  → создан Спринт 20
✅ studio/WORKSHOP_STANDARD.md  → создан Спринт 20 (шаблон для всех 11 цехов)
⏳ остальные 7 цехов     → аудит: нужен ли hooks.py?
```

**C. Первый реальный ран (только после A+B):**
```
⏳ Запустить video_shorts — чеклист из SHORTS_RULES v2.2 раздел 13:
   studio/economy/data/interaction_log_video_shorts.jsonl — появился?
   compatibility_snapshot: {technical, creative, rhythm} — все три оси?
   outcome_signal в последней записи — заполнен?
   cultural_trace обновился?
   client_relationship в dna.json A12 — обновился?
   victor_critique в chain_data — появился?
   history_dna у Трикси — инжектирован?
   save_feedback() + ministry.record_outcome() — запустились?
```

### 🟡 Следующие спринты:
- Agent Factory
- ready_books/ — 3 первые книги
- Разобрать полномочия Джема, Сета (аудит)
- Полный тест цикла: заказ → генерация → deliver

### 🟢 Долгосрочно:
- Аудиофайлы Foley
- Ночной Batching
- Деплой Hetzner, HTTPS
- Храм, Таверна как активные механики
- GitHub write access для Брата

---

## 12. ИСТОРИЯ СЕССИЙ

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
| 2026-05-15 | **Спринт 18 — СТАНДАРТ ПАЙПЛАЙНОВ.** LONG v4.2 + SHORTS v2.2. Манифесты v2.0. hooks.py v1.0. Виктор подключён. qa_agent=A12. CulturalFieldTracker API зафиксирован. |
| 2026-05-16 | **Спринт 18 финал.** ui_registry.py пропатчен. Resonance-файлы выверены. Рек. #27. STUDIO_CONTEXT v18.2. |
| 2026-05-20 | **Спринт 20 — АУДИТ SMM-ЦЕХА.** 5 багов закрыты патч-скриптом. CHAIN_CONTRACT social_mix создан. WORKSHOP_STANDARD для 11 цехов. video_long/hooks.py v2.1 готов. STUDIO_CONTEXT v20.0. |
| 2026-05-17 | **Спринт 19 — СТАНДАРТ ПРОМТОВ.** video_shorts: 12 промтов эталон, hooks.py v2.0 (A07+A12 fal.ai), CHAIN_CONTRACT.md, patch_sprint19.py. cartridge.py: Victor без хардкода. STUDIO_CONTEXT v19.0. |

---

## 13. РЕКОМЕНДАЦИИ БРАТА

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
20. **cultural_trace** — финализатор вызывает CulturalFieldTracker.update_slot_field(slot), фильтрует status in ("stable", "global"). Не генерирует сам.
21. **Виктор** — подключается через manifest.json для ЛЮБОГО цеха: "residents": ["victor"]. cartridge.py читает manifest, хардкода нет.
22. **client_relationship** — обновляет только финализатор цеха через dna.json.
23. **quality_score** — считается по has_my_output (не deliverables!). Промежуточные агенты не получают bad_work.
24. **experience[] в dna.json не существует** — история агента в sensory/sensory_memory.json, resonance/emotional_weights.json и resonance/event_log.json.
25. **Раны — только после стандартизации манифестов и проверки промтов.**
26. **qa_agent ≠ контентный ревизор.** A04 (Катя/Тони) — локальный контролер контента на ХАРД-СТОПе. qa_agent в manifest — системная переменная: последний агент цеха.
27. **Папки агентов = A-нотация везде.** A01–A05 (turbo), A01–A12 (все остальные). T1–T5 в TURBO_RULES — кодовые имена персонажей, не worker_id системы.
28. **Промты — не копировать между цехами.** Каждый промт пишется с нуля по RULES.md своего цеха. Перед написанием — сверка с CHAIN_CONTRACT.md.
29. **CHAIN_CONTRACT.md** — обязателен для каждого цеха. Содержит: таблицу ключей, структуры my_output, правила, чеклист проверки промта. Живёт в папке модуля.
30. **checkpoint_after** — в video_long и video_shorts всегда `[]`. ХАРД-СТОП делает hard_stop, checkpoint_after там не нужен. Не путать.

---

## 14. ИЗВЕСТНЫЕ ОТКРЫТЫЕ БАГИ

| # | Проблема | Приоритет |
|---|----------|-----------|
| 1 | global_feedback.json отсутствует | ⏳ ждёт первого рана |
| 2 | conflict_stats.json отсутствует | ⏳ ждёт рана с конфликтом |
| 3 | ~~knowledge.py — 265 байт, заглушка~~ | ✅ ЗАКРЫТ — файл рабочий, не заглушка |
| 4 | instances/ — legacy папка | 🟢 некритично |
| 5 | ~~TURBO_ROLE_OPTIONS~~ | ✅ ЗАКРЫТ Спринт 18 |
| 6 | interaction_log_video_long.jsonl — не создан | ⏳ ждёт рана |
| 7 | interaction_log_video_shorts.jsonl — не создан | ⏳ ждёт рана |
| 8 | Манифесты 8 цехов не обновлены до v2.0 | 🔴 Спринт 19 |
| 9 | ~~Виктор не подключён~~ | ✅ ЗАКРЫТ Спринт 18 |
| 10 | ~~Промты video_shorts не проверены~~ | ✅ ЗАКРЫТ Спринт 19 |
| 11 | Джем и Сет — полномочия не определены | 🟡 Спринт 19 |
| 12 | ~~video_long/hooks.py — не реализован~~ | ✅ ЗАКРЫТ Спринт 20 — v2.1 готов |
| 13 | ~~turbo/hooks.py — worker_id T3/T5~~ | ✅ ЗАКРЫТ Спринт 18 |
| 14 | ~~checkpoint_after двойная остановка video_long/shorts~~ | ✅ ЗАКРЫТ Спринт 19 |
| 15 | ~~cartridge.py хардкод _victor_depts~~ | ✅ ЗАКРЫТ Спринт 19 |
| 16 | Промты остальных 10 цехов не проверены | 🔴 Спринт 19+ |
| 17 | ~~cartridge.py: {"action":"stop"} игнорировался~~ | ✅ ЗАКРЫТ Спринт 20 — patch_sprint20_smm.py |
| 18 | ~~fal_client.py стр.43: _current_client_slug = NoneCLIENTS_DIR~~ | ✅ ЗАКРЫТ Спринт 20 |
| 19 | ~~social_mix/hooks.py: модель gemini-flash-1.5 (устарела)~~ | ✅ ЗАКРЫТ Спринт 20 — gemini-2.5-flash |
| 20 | ~~social_mix/hooks.py: slot_id FAL-вызовов дробил ministry-статистику~~ | ✅ ЗАКРЫТ Спринт 20 |
| 21 | ~~video_long/hooks.py: хардкод update_slot_field("video_long")~~ | ✅ ЗАКРЫТ Спринт 20 |

---

*Обновлено: Спринт 20 — 2026-05-20. SMM-цех аудирован. patch_sprint20_smm.py применить. Следующий — video_long промты + остальные 7 манифестов.*
