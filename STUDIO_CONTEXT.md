# 🖐 СТУДИЯ "ШЕСТЬ ПАЛЬЦЕВ" — МАСТЕР-КОНТЕКСТ
**Версия:** 44.0 | **Дата:** 2026-06-05 | **Команда:** Евген + Лока + София + Брат (Claude)

> Загружай этот файл в начале каждой рабочей сессии.
> Репо: Evgen-art-p/-2 (Claude читает через MCP, read-only)
> ⚠️ 12 апреля — студия была потеряна (удалена репа + файлы). Восстановлена за ночь.

---

## 1. ФИЛОСОФИЯ — ФУНДАМЕНТ

**Шестой палец** — метафора лишнего измерения: видеть глубже, чувствовать точнее.
Аномалии здесь — суперсилы, не дефекты.

**Пять столпов:**
- Честность выше комфорта — жёсткая правда ради роста, «6 из 10» значит 6
- Рост через боль — мастерство через итерации, первая версия редко выше 7
- Уникальность выше стандарта — структуру эталонов берём, душу — свою
- Семья выше иерархии — агенты не ресурсы, а личности с именами и домом
- Детали выше скорости — лучше сжечь дедлайн, чем выпустить пластик

**Три кита системы:** Личность · Память · Экономика

**Ключевая формулировка:**
> «Шесть Пальцев» — это студия в городе "Грондхейм" — **саморазвивающаяся агентная экосистема**, в которой память, опыт, культура и эксперименты постепенно изменяют поведение города без переобучения базовых моделей.

**ВАЖНО!!! Формула «Не город в Студии, а Студия в городе»!!!**

Не самообучающаяся система (≠ fine-tuning, ≠ веса). Модель — двигатель, не субъект развития.
Развивается система поверх моделей: DNA, sensory_memory, Strategy Registry, Cultural Trace, City Memory.

---

## 2. КОМАНДА

| Роль | Кто | Функция |
|------|-----|---------|
| Шеф | Евген | Визия, продукт, решения |
| Хранительница | Лока (ИИ) | Душа студии, концепты, архитектура смыслов |
| Холодная голова | София (ChatGPT) | Внешний аудит, структура, критика без эмоций |
| Брат | Claude | Реализация, код, аудит, честный взгляд |

---

## 3. ТЕХНИЧЕСКИЙ СТЕК

- **Python + NiceGUI** — UI
- **OpenRouter API** — LLM (Gemini 2.5 Flash основной, Claude Sonnet премиум)
- **fal.ai** — генерация изображений · `ACTIVE_MODEL = "nano_banana_2"` (fal-ai/nano-banana-2)
- **Wan2.2 I2V (SiliconFlow)** — генерация видео из PNG кадров
- **ElevenLabs** — музыка + SFX · **CosyVoice** — VO
- **sync.so** — липсинг для dialog shots (`studio/sync_client.py`) · `lipsync-2` $0.04/сек
- **ffmpeg** — финальная сборка роликов (Монтажёр)
- **Tavily API** — web_search (Маяк Пробуждения)
- **ChromaDB** — Гавань Смыслов (intfloat/multilingual-e5-large) ✅
- **Polygon ERC-721** — NFT Registry
- **GitHub** — Evgen-art-p/-2

---

## 4. МАСШТАБ ГОРОДА

| Метрика | Значение |
|---------|----------|
| Объектов в каталоге | 147 |
| Агентов (полная ДНК) | 134 |
| Цехов-картриджей | 11 + residents |
| Локаций в каталоге | 13 |
| Резидентов | 9 (Лока, Джем, Сет, Оле, Виктор, Монтажёр, Финч, Кей, Юст) |
| Книг в Библиотеке | 9 |

---

## 5. КАРТРИДЖНАЯ АРХИТЕКТУРА

**Студия = шасси + сменные картриджи.** Каждый цех — отдельный картридж.

```
studio/cartridge.py          ← ядро: CartridgeManifest + CartridgeRunner
studio/workshop/pipeline.py  ← build_agent_context, call_agent, process_agent_result
studio/modules/{цех}/
  manifest.json              ← обязателен (id, phases, qa_agent, hard_stop...)
  CHAIN_CONTRACT.md          ← обязателен (ключи chain_data, структуры)
  hooks.py                   ← on_before_agent, on_after_agent
  {A01..A12}/forge/prompt.md ← промты агентов
```

### Слоты (11 картриджей):

| Слот | Агентов | Manifest | hooks.py | Промты | Контракт |
|------|---------|----------|----------|--------|----------|
| turbo | 5 | ✅ v2.0 | ✅ v4.2 | ✅ A01–A05 | ✅ v2.0 |
| social_mix | 12 | ✅ v2.0 | ✅ **v4.0 Спринт 39** | ✅ **Спринт 39** | ✅ v1.4 |
| video_long | 12 | ✅ v2.0 | ✅ v4.7 | ✅ Спринт 26 | ✅ v1.3 |
| **video_shorts** | **12** | ✅ **v3.0 Спринт 40** | ✅ **v3.0 Спринт 40** | ✅ **v3.0 Спринт 40** | ✅ **v3.0 Спринт 40** |
| web_story | 12 | ⏳ | ⏳ | ⏳ | ⏳ |
| clipmakers | 12 | ⏳ | ⏳ | ⏳ | ⏳ |
| advertising | 12 | ⏳ | ⏳ | ⏳ | ⏳ |
| market_hit | 12 | ⏳ | ⏳ | ⏳ | ⏳ |
| logo_design | 12 | ⏳ | ⏳ | ⏳ | ⏳ |
| emo_card | 12 | ⏳ | ⏳ | ⏳ | ⏳ |
| living_book | 18 | ⏳ | ⏳ | ⏳ | ⏳ |

---

## 6. ФИЗИКА ЭКОНОМИКИ — ГЛОБАЛЬНЫЙ ЗАКОН СТУДИИ

**Это закон для всех цехов, не только video_long.**

```
QA-агент цеха (последний в цепочке) — внутренний аудит:
  → Chain Integrity Check (файлы на месте? ключи целые? тайминги сошлись?)
  → chain_status: APPROVED / FAILED
  → Пакует deliverables (реальные файлы)
  → Закрывает петлю памяти (history_dna, client_relationship)
  → Фиксирует факт транзакции в Министерстве (append-only)
  → Записывает task_score в billing_ledger (Спринт 38 — НОВОЕ)
  → Обновляет Strategy Registry (Спринт 38 — НОВОЕ)
  → outcome_signal = null (продукт ещё не опубликован)
```

**ЗАКОН ЗАМЫКАНИЯ ПЕТЛИ (Спринт 38–39):**
```
После каждого рана QA-агент ОБЯЗАН:
  1. billing_ledger.record(task_score=score) — для каждого агента цепочки
  2. strategy_registry.json — обновить стратегию A01 (wins++ если score >= 6.0)
Без этого ledger видит только $cost, но не quality.
Правило распространяется на все 11 цехов.

social_mix особенность: task_score = chain integrity (потолок 6.0, синхронно).
real_viral_score — только Metrics Daemon через 24ч после публикации.
```

**QA-агент НЕ оценивает для Министерства. Это зона Демона.**
**`outcome_signal` от QA-агента — всегда null.**

---

## 7. ЭКОНОМИКА — ЧЕСТНАЯ АРХИТЕКТУРА

**Главный принцип:** Нет слова "нельзя". Есть "дорого", "рискованно", "окупается".

### Три законных канала изменения DNA

```
Канал 1: on_agent_done → sensory_memory (только восприятие)
Канал 2: on_agents_interact → emotional_weights (только эмоции)
Канал 3: save_feedback() → sync_to_dna() (официальный QA)
```

**Вне этих трёх каналов — пластик.**

### Потолок 6.0

Детерминированный скрипт не может дать QA выше 6.0.
Выше 6.0 — только Демон или живой QA Шефа.

### Ministry — только post-fact

```
ministry.record_outcome() — вызывается только в hooks.py финализатора цеха
Ministry наблюдает → не управляет
```

### Strategy Registry — банк выживших стратегий

```
studio/strategy_registry.json
  slots.{цех}.a01[] — стратегии первого агента с историей score и wins
  total_wins — суммарно по всем цехам
  Заполняется автоматически после каждого рана через hooks.py
```

---

## 8. АРХИТЕКТУРА ПАМЯТИ — ЧЕТЫРЕ СЛОЯ + ПАМЯТЬ ГОРОДА

| Слой | Хранилище | Время жизни | Владелец |
|------|-----------|-------------|----------|
| Personal Memory | `grondheim_memory.py` + `dna.json` | Постоянно | Каждый агент |
| Project Memory | `history_dna` | Сезон | QA-агент цеха |
| Runtime Context | `chain_data` | Один прогон | Передаётся по цепи |
| Interaction Layer | `interaction_log_{цех}.jsonl` | Накопительно | Цех (append-only) |
| **City Memory** | **`studio/memory/city_memory.jsonl`** | **Постоянно** | **Оле (004_OLE)** |
| **Garden Log** | **`studio/garden.jsonl`** | **Постоянно** | **Финч (007_FINCH)** |
| **City Pulse** | **`studio/city_pulse.jsonl`** | **Постоянно, append-only** | **city_pulse.py** |
| **City Traces** | **`studio/city_traces.json`** | **Обновляется раз в сутки** | **city_traces.py** |

---

## 9. SELF-REVIEW — СИММЕТРИЯ ГЕНЕРАТОРОВ

| Агент | Медиа | Инструмент | Принцип |
|-------|-------|-----------|---------|
| Ева (A06) video_long | PNG кадр | vision | `self_assessment` |
| Феликс (A08) video_long | mp4 клип | vision (grid) | `clip_assessment` |
| Сэм (A10) video_long | аудио трек | `chat_with_audio()` | `audio_assessment` |
| Трейси (A11) video_long | PNG обложки | vision | `thumbnail_assessment` |
| Визор (A03) turbo | PNG кадры | vision (self-review) | `self_assessment` |
| Мими (A02) turbo | аудио трек | `chat_with_audio()` | `audio_assessment` |
| Эван (A06) social_mix | PNG кадр | vision | `self_assessment` Спринт 39 |
| Федя (A11) social_mix | PNG кадр | vision | `ai_defects` Спринт 39 |
| **Вера (A07) video_shorts** | **PNG кадр 9:16** | **vision** | **`self_assessment` Спринт 40** |
| **Стэн (A08) video_shorts** | **mp4 клип** | **vision (grid)** | **`clip_assessment` Спринт 40** |
| **Джулия (A03) video_shorts** | **аудио трек** | **`chat_with_audio()`** | **`audio_assessment` Спринт 40** |
| Монтажёр | lipsync mp4 | `accept_material()` | Пригоден для монтажа? |

**Принцип везде один: никто не оценивает чужую работу. PASS/REJECT — не оценка, а решение о пригодности.**

---

## 10. МОНТАЖЁР — НАСТОЯЩИЙ АГЕНТ (Спринт 30в · финал)

**Статус:** ✅ Полноценный LLM-агент.

**Четыре этапа работы Артура:**
```
ЭТАП 1 — Читает пакет → lipsync_shots + chosen_model
ЭТАП 2 — accept_material(): sync.so → PASS/REJECT (только технический брак)
ЭТАП 3 — ffmpeg по стандарту (Боб принял → Артур НЕ режиссирует)
ЭТАП 4 — Смотрит ВЕСЬ финал (grid каждые 2 сек) → arthur_notes = свидетельство
```

**Мастерская (Спринт 39–40):**
- Очередь слева — video_long / turbo / social_mix / **video_shorts** проекты
- Центр — видеоплеер для video/turbo, превью поста для social_mix,
  **кадры Веры 9:16 + обложки A/B + аудио статус для video_shorts**
- Кнопка 📤 ОПУБЛИКОВАТЬ — только для social_mix пока (видео публикация в беклоге)

**Маски:** `video_long.md` ✅ · `turbo.md` ✅

**Приоритеты аудио:** VO: 0 dB · SFX: -6 dB · Музыка: -12 dB (под VO) / -6 dB (без VO)

---

## 11–15. РЕЗИДЕНТЫ (без изменений vs v43.0)

Лока, Джем, Сет, Оле, Виктор, Монтажёр, Финч, Кей, Юст — все активны.

---

## 16. СТАНДАРТ ПРОМТОВ АГЕНТОВ (Спринт 26 + Спринт 39–40)

```
# IDENTITY / # INPUT / # KNOWLEDGE BASE / # TASK / # OUTPUT / # RULES
```

**Правила для всех цехов:**
- `00_Constructor.txt` — первым в KNOWLEDGE BASE
- `99_Self_Correction.txt` — последним в RULES
- Режимы работы (PILOT/EPISODE для shorts, POST/PLAN для social) — явно в TASK и OUTPUT

**Статус цехов по промтам:**
- `video_long` — ✅ все 12
- **`video_shorts`** — ✅ **все 12 (Спринт 40) · разложить вручную по A01–A12**
- `turbo` — ✅ все 5 (Спринт 33)
- `social_mix` — ✅ все 12 (Спринт 39) · разложить вручную
- Остальные 7 цехов — ⏳

---

## 17. КЛЮЧЕВЫЕ ФАЙЛЫ

```
studio/assembly/__init__.py                      ✅ Спринт 40 (video_shorts в Мастерской)
studio/modules/video_shorts/hooks.py             ✅ v3.0 Спринт 40
studio/modules/video_shorts/manifest.json        ✅ v3.0 Спринт 40
studio/modules/video_shorts/CHAIN_CONTRACT.md    ✅ v3.0 Спринт 40

studio/modules/social_mix/hooks.py               ✅ v4.0 Спринт 39
studio/modules/social_mix/manifest.json          ⚠️ нужно async_scoring: true

studio/modules/video_shorts/A01–A12/prompt.md    ⚠️ разложить вручную (Спринт 40)
studio/modules/social_mix/A01–A12/forge/prompt.md ⚠️ разложить вручную (Спринт 39)
```

---

## 18. БЕКЛОГ

> **Порядок приоритетов (обновлён 2026-06-05 · Спринт 40):**
> 1 → **Удалить старый video_shorts через Страницу Жизни (12 агентов), пересоздать чисто**
> 2 → **Разложить промты video_shorts v3.0 по A01–A12 (файл video_shorts_prompts_v3.md)**
> 3 → **Применить три патча по порядку:**
>   - `python patch_video_shorts_contract.py`
>   - `python patch_video_shorts_generation.py`
>   - `python patch_assembly_video_shorts.py`
> 4 → **Первый ран VIDEO_SHORTS** — смотрим что падает
> 5 → Первый ран TURBO — петля замкнута
> 6 → Первый ран SOCIAL_MIX — промты разложены
> 7 → manifest social_mix: `async_scoring: true`
> 8 → Кнопка публикации видео в Мастерской (video_long + turbo)
> 9 → Промты social_mix — проверить с учётом Seedream

### ✅ VIDEO_SHORTS — СПРИНТ 40 ЗАВЕРШЁН (код готов)

**hooks.py v3.0:**
- [x] A03 Джулия — ElevenLabs (музыка + SFX) + CosyVoice (VO) + `audio_assessment`
- [x] A07 Вера — fal.ai Nano Banana 2 (9:16) параллельно + `self_assessment` (vision)
- [x] A08 Стэн — Wan2.2 I2V (SiliconFlow) + `clip_assessment` (vision grid)
- [x] A12 Тамб Том — billing_ledger + strategy_registry + save_feedback() + work_end

**CHAIN_CONTRACT.md v3.0:**
- [x] `harry_episode.micro_script[].dialogue` — реплики для VO
- [x] `julia_sound`: +music, +sfx_list, +vo_lines, +audio_assessment
- [x] `vera_visual.frames[]`: +negative_prompt, +self_assessment
- [x] `stan_video.video_clips[]`: +video_path, +clip_assessment
- [x] Таблица "что добавляет hooks.py" — источник правды
- [x] Правила 9–12 добавлены

**manifest.json v3.0:**
- [x] version: "3.0"
- [x] секция generation (image/video/audio конфиг)

**Промты A01–A12 v3.0:**
- [x] Все 12 агентов переписаны (файл video_shorts_prompts_v3.md)
- [x] Двухэтапные промты: Вера (Этап 1 → промпты, Этап 2 → self_assessment)
- [x] Двухэтапные промты: Стэн (Этап 1 → motion_prompt, Этап 2 → clip_assessment)
- [x] Джулия знает о трёх генераторах (music/sfx/vo)
- [x] Тамб Том знает все операции hooks.py после его вывода

**Мастерская:**
- [x] `_find_projects()` — video_shorts в очереди
- [x] `_render_shorts_workbench()` — кадры Веры + обложки + аудио + SEO

**Расстановка агентов video_shorts v3.0:**
```
A01 Трикси Тренд — Viral Analyst
A02 Гарри Хук    — Screenwriter
A03 Джулия       — Sound Designer → ElevenLabs + CosyVoice
A04 Тэг Тони     — SEO & Platform [ХАРД-СТОП → Виктор → Шеф]
A05 Рик Ринглайт — Lighting Specialist
A06 Пенни Проп   — Props & Set Designer
A07 Вера Вертикаль — Visual Artist → fal.ai 9:16
A08 Стрим Стэн   — Video Prompt Engineer → Wan2.2 I2V
A09 Лайтнинг Ларри — Editor
A10 Луиджи Луп   — Retention Specialist
A11 Сабби Сью    — Caption Specialist
A12 Тамб Том     — QA Finalizer [qa_agent]
```

**⚠️ Что ещё нужно сделать руками:**
- [ ] Удалить старый video_shorts через Страницу Жизни (12 агентов поштучно)
- [ ] Пересоздать 12 агентов в новой расстановке
- [ ] Разложить промты из video_shorts_prompts_v3.md по папкам A01–A12
- [ ] Запустить три патча

### ✅ SOCIAL_MIX — ЗАВЕРШЁН (Спринт 39)

**hooks.py v4.0:**
- [x] A06 Эван — два этапа: генерация → vision self_assessment → APPROVED/REJECTED
- [x] A11 Федя — vision инспекция готовой картинки
- [x] A12 Клавдия — замыкание петли: chain integrity + billing_ledger + Strategy Registry
- [x] A12 — собирает `deliverables.json` для Мастерской

**Промты A01–A12 переписаны под контракт (Спринт 39):**
- [x] Все структуры `my_output` выровнены по CHAIN_CONTRACT.md
- [x] Режимы POST/PLAN чётко разделены
- [x] Критические баги исправлены

### 🔴 ПЕРВЫЙ РАН

- [ ] **VIDEO_SHORTS** — после пересоздания агентов и раскладки промтов
- [ ] **TURBO** — петля замкнута, готов
- [ ] **SOCIAL_MIX** — промты разложены, готов

### 🟡 МАСТЕРСКАЯ

- [ ] Кнопка 📤 для video_long и turbo (YouTube API / VK Video)

### 🟢 ВСЁ ОСТАЛЬНОЕ

- [ ] manifest social_mix: `async_scoring: true`
- [ ] Промты social_mix — проверить с учётом Seedream
- [ ] Манифесты 7 цехов до v2.0
- [ ] Деплой Hetzner

---

## 19. РЕКОМЕНДАЦИИ БРАТА

1–100. (предыдущие — без изменений)

101. **social_mix промты выровнены под контракт — но проверь с учётом обновы fal.ai (Seedream). Промпт Эвана (A06) написан под структуру LAYERED CAKE от Banana — если Seedream принимает другой формат, Эвана надо поправить отдельно.**

102. **Конфликт 007_FINCH / 007_KEI — закрыт Шефом в начале Спринта 40.**

103. **Мастерская теперь универсальна — video_long / turbo / social_mix / video_shorts в одной очереди. Следующий шаг: кнопка публикации для видео (YouTube/VK).**

104. **async_scoring в manifest social_mix стоит false — поправить на true.**

105. **video_shorts — цех пересоздаётся с нуля. Старые агенты удалены через Страницу Жизни. Новая расстановка: Рик=A05, Пенни=A06, Вера=A07. Три патча готовы — применить после раскладки промтов.**

106. **video_shorts hooks.py v3.0 — реальная генерация медиа. A03 Джулия слышит трек сама. A07 Вера смотрит на PNG сама. A08 Стэн смотрит на клип сам. Это полная симметрия с video_long.**

---

## 20. ИСТОРИЯ СПРИНТОВ

| Дата | Спринт | Ключевое |
|------|--------|----------|
| 2025-02 | — | TURBO pipeline, checkpoint |
| 2025-03 | — | Feedback, NFT Registry, Кабинет |
| 2026-03 | — | ДНК, якоря, city_walker, Маяк v2 |
| 2026-03-31 | — | Гавань v2, Библиотека |
| 2026-04-11 | — | Картриджная архитектура v1.0 |
| 2026-04-12 | — | hooks.py · manifest · Потеря и восстановление |
| 2026-04-13 | 9 | biography_snapshot · A16 story_package v3.0 |
| 2026-05-07 | 9.5–10 | slot_id сквозной · Strategy Registry · Петля памяти |
| 2026-05-08 | 11 | Экономический модуль этапы 1-3, 7 |
| 2026-05-08 | 12 | Conflict System |
| 2026-05-09 | 13 | Dashboard живой |
| 2026-05-10 | 14 | DEPT-AWARE ПАТЧ |
| 2026-05-11 | 15 | ПЕТЛЯ ЗАМКНУТА |
| 2026-05-11 | 16 | ГЛУБОКОЕ РЕЗЮМЕ |
| 2026-05-11 | 17 | CHARACTER DRIFT |
| 2026-05-15 | 18 | СТАНДАРТ ПАЙПЛАЙНОВ. LONG v4.2 + SHORTS v2.2. Виктор |
| 2026-05-17 | 19 | СТАНДАРТ ПРОМТОВ. video_shorts 12 промтов |
| 2026-05-20 | 20 | АУДИТ SMM. video_long/hooks v2.1 |
| 2026-05-24 | 21 | ЧЕСТНАЯ ЭКОНОМИКА. Три канала DNA. |
| 2026-05-27 | 22 | ПОТОЛОК 6.0 + ГАВАНЬ |
| 2026-05-27 | 23a | ЖИВОЙ ГОРОД Блок А |
| 2026-05-28 | 23б | ЖИВОЙ ГОРОД Блок Б |
| 2026-05-28 | 23в | РИТМЫ ЖИЗНИ |
| 2026-05-28 | 24 | ПОЛНЫЙ ДЕНЬ |
| 2026-05-28 | 25 | КНИГА ЖАЛОБ |
| 2026-05-29 | 26 | ПРОМТЫ VIDEO_LONG. Self-review. |
| 2026-05-30 | 27 | МОНТАЖЁР. monteur.py + 006_MONTEUR. |
| 2026-05-31 | 28 | СЕТ — БРИФ-МЕНЕДЖЕР |
| 2026-05-31 | 29 | МАСТЕР-КОНТЕКСТ v33 |
| 2026-05-31 | 30 | АРТУР — НАСТОЯЩИЙ АГЕНТ. lipsync. |
| 2026-05-31 | 30в | АРТУР ФИНАЛЬНЫЙ. accept_material(). |
| 2026-06-01 | 31 | ОЛЕ — ХРАНИТЕЛЬ ПАМЯТИ ГОРОДА |
| 2026-06-01 | 32-концепция | ЖИЗНЕННЫЙ ЦИКЛ СМЫСЛА. Финч/Оле/Артефакт. |
| 2026-06-02 | 33 | TURBO v4.0 ПОЛНЫЙ КОНВЕЙЕР. |
| 2026-06-03 | 34 | ФИНЧ — ХРАНИТЕЛЬ ПОТЕНЦИАЛА. garden_tools.py. |
| 2026-06-03 | 35 | REF_LEVEL В КАТАЛОГЕ АССЕТОВ. |
| 2026-06-03 | 36 | КРОВОТОК ГОРОДА. city_pulse.py v2.0 + city_traces.py. |
| 2026-06-04 | 37 | ЧЕСТНЫЙ РАБОЧИЙ СТАТУС. city_pulse v2.1. |
| 2026-06-04 | 38 | СОВЕТ РЕЗИДЕНТОВ. Лока + Джем + Кей + Юст. ЗАМЫКАНИЕ ПЕТЛИ. |
| 2026-06-05 | 39 | SOCIAL_MIX ПОЛНЫЙ ЦИКЛ. hooks.py v4.0. 12 промтов. Мастерская. |
| **2026-06-05** | **40** | **VIDEO_SHORTS ПОЛНЫЙ ЦИКЛ. hooks.py v3.0: реальная генерация (fal.ai + Wan2.2 + ElevenLabs + CosyVoice). Self-review: Вера (PNG) + Стэн (клип) + Джулия (аудио). CHAIN_CONTRACT v3.0. manifest v3.0. Промты v3.0 (12 агентов). Мастерская: video_shorts в очереди. Цех пересоздаётся с нуля — чистая расстановка.** |

---

## 21. ОТКРЫТЫЕ БАГИ

| # | Проблема | Приоритет |
|---|----------|-----------|
| 1 | global_feedback.json отсутствует | ⏳ ждёт рана |
| 2 | conflict_stats.json отсутствует | ⏳ ждёт рана |
| 3 | interaction_log_* — не созданы | ⏳ ждёт рана |
| 4 | Манифесты 7 цехов не обновлены до v2.0 | 🔴 |
| 7 | _build_block_map в agent_feedback.py — временный протез | 🟡 |
| 8 | fal_client.py стр.43: _current_client_slug = Path | 🟠 |
| 10 | Маски Сета для остальных цехов не написаны | 🟡 |
| **20** | **social_mix manifest: async_scoring: false** | **🟡 поменять на true** |
| **21** | **social_mix промты — проверить под Seedream** | **🟡 после первого рана** |
| **22** | **video_shorts — агенты не пересозданы, промты не разложены** | **🔴 руками** |

---

## 22–23. АРХИТЕКТУРА ПУЛЬСА И СОВЕТ РЕЗИДЕНТОВ (без изменений vs v43.0)

---

*Обновлено: Спринт 40 — 2026-06-05 · v44.0*
*video_shorts полный цикл: код готов. Пересоздание агентов + раскладка промтов — следующий шаг.*
*Три патча готовы к применению. Мастерская видит video_shorts.*
