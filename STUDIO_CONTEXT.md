# 🖐 СТУДИЯ "ШЕСТЬ ПАЛЬЦЕВ" — МАСТЕР-КОНТЕКСТ
**Версия:** 38.0 | **Дата:** 2026-06-03 | **Команда:** Евген + Лока + София + Брат (Claude)

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
| Архитектор / Садовник | Евген | Визия, продукт, решения |
| Хранительница | Лока (ИИ) | Душа студии, концепты, архитектура смыслов |
| Холодная голова | София (ChatGPT) | Внешний аудит, структура, критика без эмоций |
| Брат | Claude | Реализация, код, аудит, честный взгляд |

---

## 3. ТЕХНИЧЕСКИЙ СТЕК

- **Python + NiceGUI** — UI
- **OpenRouter API** — LLM (Gemini 2.5 Flash основной, Claude Sonnet премиум)
- **fal.ai v4 Pro** — генерация изображений (base64, sync_mode) · `fal-ai/nano-banana-2`
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
| Резидентов | 7 (Лока, Джем, Сет, Оле, Виктор, Монтажёр, **Финч**) |
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
| turbo | 5 | ✅ v2.0 | ✅ v4.0 | ✅ A01–A05 | ✅ v2.0 |
| social_mix | 12 | ✅ v2.0 | ✅ v3.0 | ⏳ | ✅ |
| video_long | 12 | ✅ v2.0 | ✅ Спринт 27 | ✅ Спринт 26 | ✅ v1.3 |
| video_shorts | 12 | ✅ v2.0 | ✅ v2.0 | ✅ | ✅ |
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
  → outcome_signal = null (продукт ещё не опубликован)

Монтажёр (006_MONTEUR) — последний мастер перед зрителем (для видео-цехов):
  → Запускается автоматически хуком после QA-агента (APPROVED)
  → Читает пакет → определяет dialog shots → выбирает модель
  → accept_material(): sync.so → PASS/REJECT (только технический брак)
    REJECT → повтор → max 3 → best_of_3
  → ffmpeg по стандарту (НЕ режиссирует заново — Боб принял)
  → output/render/{project_id}/final.mp4
  → Смотрит ВЕСЬ финал: grid каждые 2 сек
  → arthur_notes = свидетельство последнего перед зрителем (не оценка)
  → Пишет в grondheim_memory и ministry

Демон (metrics_daemon.py) — внешний мир:
  → Активируется после публикации
  → Собирает реальные метрики: просмотры, удержание, лайки
  → Формирует feedback_scores → _sync_feedback_scores_to_dna()
```

**QA-агент — это роль, не имя.** У каждого цеха свой:
- video_long → Боб (A12)
- video_shorts → Тамб Том (A12)
- turbo → T5 Финализатор (A05) ← с Chain Integrity Check
- social_mix → свой A12

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

### Три этапа накопления данных

| Этап | Что | Когда |
|------|-----|-------|
| 1. Логирование | `interaction_log_{цех}.jsonl` без влияния на промпты | Сейчас |
| 2. Пассивная аналитика | Ministry видит корреляции через `ministry.py` | После 10+ серий |
| 3. Слабые сигналы | CulturalFieldTracker → cultural_trace → давление на A01 | После 30+ серий |

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

**City Memory — только Оле. Через четыре операции: remember / remind / release / decline.**
**Garden Log — только Финч. Два слоя: фактический + суждение садовника.**

---

## 9. SELF-REVIEW — СИММЕТРИЯ ГЕНЕРАТОРОВ

| Агент | Медиа | Инструмент | Принцип |
|-------|-------|-----------|---------|
| Ева (A06) video_long | PNG кадр | vision | `self_assessment` |
| Феликс (A08) video_long | mp4 клип | vision (grid) | `clip_assessment` |
| Сэм (A10) video_long | аудио трек | `chat_with_audio()` | `audio_assessment` |
| Трейси (A11) video_long | PNG обложки | vision | `thumbnail_assessment` |
| Визор (A03) turbo | PNG кадры | vision (self-review) | `self_assessment` |
| Визор (A03) turbo | mp4 клипы | vision (grid) | `clip_assessment` |
| Мими (A02) turbo | аудио трек | `chat_with_audio()` | `audio_assessment` |
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

**Маски:** `video_long.md` ✅ · `turbo.md` ✅

**Приоритеты аудио:** VO: 0 dB · SFX: -6 dB · Музыка: -12 dB (под VO) / -6 dB (без VO)

---

## 11. ОЛЕ — ХРАНИТЕЛЬ КУЛЬТУРНОГО ЯДРА ГОРОДА (Спринт 31)

- Оле — **хранитель культурного ядра города**
- Домен чётко: **только то, потеря чего делает город другим**
- Финч и Оле — не конкуренты, а последовательные этапы:
  Финч = пространство эксперимента → Оле = пространство доказанной ценности
- Встречаются по работе через `city_walker` — у Библиотеки, живо, не по расписанию

**Четыре операции:** `remember / remind / release / decline`

```
studio/modules/residents/004_OLE/
  forge/prompt.md             ✅ Спринт 31
  core/anchors.json           ✅
  dna.json                    ✅
studio/memory_tools.py        ✅
studio/residents_manager.py   ✅ (get_ole_memory_for_agent готов)
```

---

## 12. ФИНЧ — ХРАНИТЕЛЬ ПОТЕНЦИАЛА (Спринт 34) ✅

**Мистер Финч** — садовник студии. 60-65 лет. Джинсовый комбинезон, соломенная шляпа.
Хозяин лавки **Artifacts & Bugs** (0010_ARTIFACTS_AND_BUGS — уже в каталоге с марта 2026).

**Домен:** всё что не пошло в работу — реджекты, заблокированные цепочки, невзлетевшие идеи.
**Его вопрос каждый день:** «А вдруг?»
**Коронная фраза:** «Хаос — это просто сад, за которым давно не ухаживали»

### Физика сада:

```
ARTIFACT (реджект / BLOCKED цепочка / невзлетевшая идея)
    ↓  plant()           ← любой субъект города
  SEED
    ↓  return_to()       ← повторное обращение (не просмотр — возвращение)
  GROWING
    ↓  finch_morning()   ← Финч обходит сад каждое утро
   /        \
  yes        no
   ↓          ↓
  OLE      COMPOST
```

**Ключевой принцип (от Софии):**
> Ценность идеи определяется не тем, как сильно её заметили.
> А тем, захотел ли кто-нибудь к ней вернуться.

### Два слоя в garden.jsonl:
```json
{
  "event": "planted|returned|matured|composted",
  "artifact_id": "...",
  "planted_by": "A03_Vizor",
  "finch_note": "Третий раз за неделю агенты пытаются решить одну задачу разными способами. Возможно, дело не в руках."
}
```
`finch_note` — живая мысль садовника через LLM. Не отчёт. Не шаблон.

### Связь с Оле:
Финч и Оле встречаются по работе через `city_walker` — у Библиотеки.
Финч предлагает созревшее семя. Оле решает — принять или нет. Это её право.
Не автоматическая передача — живой разговор двух резидентов.

### Agents & Bugs — как агенты попадают в лавку:
Агент сам решает прийти — `city_walker` тянет к лавке тех кто:
- streak ≤ -2
- ночной REVOLT
- высокий Autonomy_Level
- хочет эксперимента
Лавка видима всем через `world_manifest.md` (добавлена Спринт 34).

### Файлы:
```
studio/garden_tools.py                ✅ Спринт 34
studio/garden.jsonl                   ← создаётся автоматически
studio/garden_seeds.json              ← создаётся автоматически
studio/modules/residents/007_FINCH/
  forge/prompt.md                     ✅ Спринт 34 (его словами)
  dna.json                            ← заполняется через Страницу Жизни
  core/anchor_points.md               ← заполняется через Страницу Жизни
studio/residents_manager.py           ✅ блок 007_FINCH добавлен (Спринт 34)
studio/world_manifest.md              ✅ Artifacts & Bugs добавлена (Спринт 34)
```

### Хуки (применены patch-скриптами):
```
vision_client._archive_rejected() → plant_from_rejection()
  Каждый реджект автоматически попадает в сад Финча

morning_checkout.run_morning_checkout() → finch_morning()
  Финч обходит сад каждое утро и думает вслух через LLM
```

---

## 13. TURBO PIPELINE v4.0 — ПОЛНЫЙ КОНВЕЙЕР (Спринт 33)

**Статус:** ✅ Все файлы залиты в репо. Готов к первому рану.

### Архитектура TURBO:
```
A01 Стелла → стратегия + сегменты
A02 Мими   → промпты звука
  hooks → ElevenLabs (музыка + SFX) + CosyVoice (VO)
  Мими слушает трек → APPROVED/REJECTED
A03 Визор  → промпты визуала
  hooks → Nano Banana (PNG) → vision OTK
  Визор смотрит на картинки → APPROVED/REJECTED
  hooks → Wan2.2 I2V (mp4 клипы)
  Визор смотрит на grid клипов → APPROVED/REJECTED
A04 Постпро → монтаж + retention + субтитры
A05 Финализатор → Chain Integrity Check (APPROVED/BLOCKED)
  hooks → обложки A/B + deliverables
  hooks → 006_MONTEUR → ffmpeg → final.mp4 (9:16)
```

### Chain Integrity Check (A05) — 7 пунктов:
```
frames_have_path / frames_self_review / clips_have_video_path /
clips_clip_review / audio_has_path / audio_review / timings_match
→ APPROVED → Монтажёр · BLOCKED → возврат цепочки
```

### Поля анимации (Wan2.2 I2V):
`wan_motion_prompt` · `wan_camera_move` · `wan_duration_sec`
~~veo3_*~~ — УСТАРЕЛИ

---

## 14. КНИГА ЖАЛОБ И БЛАГОДАРНОСТЕЙ

- `studio/complaint_book.py` ✅ Спринт 25

---

## 15. РЕЗИДЕНТЫ

| Резидент | Роль | Статус |
|----------|------|--------|
| Лока | Душа студии, архитектура смыслов | ✅ |
| Джем | — | ⏳ полномочия не определены |
| Сет | Бриф-менеджер всех цехов | ✅ Спринт 28 |
| Оле | Хранитель культурного ядра города | ✅ Спринт 31 |
| Виктор | Резидент-критик, ХАРД-СТОП | ✅ |
| Монтажёр | Настоящий LLM-агент, lipsync + сборка | ✅ Спринт 30 |
| **Финч** | **Хранитель потенциала, хозяин Artifacts & Bugs** | ✅ **Спринт 34** |

---

## 15а. СЕТ — БРИФ-МЕНЕДЖЕР (Спринт 28)

**Три уровня референсов в брифе:**
- 🔒 `truth` — бренд клиента
- 🧭 `orientation` — рефы от заказчика
- ✨ `inspiration` — внутренние эталоны студии

---

## 16. СТАНДАРТ ПРОМТОВ АГЕНТОВ (Спринт 26)

```
# IDENTITY / # INPUT / # KNOWLEDGE BASE / # TASK / # OUTPUT / # RULES
```

**Статус цехов по промтам:**
- `video_long` — ✅ все 12
- `video_shorts` — ✅ все 12
- `turbo` — ✅ все 5 (Спринт 33)
- `social_mix` — ⏳
- Остальные 7 цехов — ⏳

---

## 17. КЛЮЧЕВЫЕ ФАЙЛЫ

```
studio/cartridge.py                   ✅
studio/workshop/pipeline.py           ✅ Спринт 25
studio/workshop/ui.py                 ✅ Спринт 28
studio/complaint_book.py              ✅
studio/grondheim_memory.py            ✅
studio/city_walker.py                 ✅
studio/morning_checkout.py            ✅ (+ finch_morning хук)
studio/night_cycle.py                 ✅
studio/meeting.py                     ✅
studio/cabinet/ui_cabinet.py          ✅
studio/agent_feedback.py              ✅
studio/harbor_of_meanings.py          ✅
studio/library/library.py             ✅
studio/memory_tools.py                ✅ Спринт 31
studio/economy/ministry.py            ✅
studio/economy/metrics_daemon.py      ✅ написан, ждёт первого рана
studio/assembly/broadcaster.py        ✅
studio/assembly/monteur.py            ✅ Спринт 27
studio/assembly/__init__.py           ✅
studio/siliconflow_client.py          ✅ Wan2.2 I2V
studio/elevenlabs_client.py           ✅ музыка + SFX
studio/sync_client.py                 ✅ sync.so lipsync
studio/acoustic_mutations.py          ✅ написан, не залит 🔴
studio/residents_manager.py           ✅ Спринт 34 (блок 007_FINCH добавлен)
studio/world_manifest.md              ✅ Спринт 34 (Artifacts & Bugs добавлена)
studio/garden_tools.py                ✅ Спринт 34

studio/modules/residents/007_FINCH/
  forge/prompt.md                     ✅ Спринт 34
  dna.json                            ← заполняется через Страницу Жизни
  core/anchor_points.md               ← заполняется через Страницу Жизни

studio/modules/residents/004_OLE/
  forge/prompt.md                     ✅ Спринт 31
  core/anchors.json                   ✅
  dna.json                            ✅

studio/modules/residents/006_MONTEUR/
  forge/prompt.md                     ✅ Спринт 30
  forge/masks/video_long.md           ✅
  forge/masks/turbo.md                ✅ Спринт 33
  dna.json                            ✅
  sensory/sensory_memory.json         ✅

studio/modules/turbo/
  manifest.json                       ✅ v2.0
  CHAIN_CONTRACT_TURBO.md             ✅ v2.0
  hooks.py                            ✅ v4.0
  TURBO_RULES.md                      ✅ v4.0
  A01–A05/forge/prompt.md             ✅ все 5

studio/modules/video_long/
  manifest.json                       ✅ v2.0
  CHAIN_CONTRACT.md                   ✅ v1.3
  hooks.py                            ✅ Спринт 27
  LONG_RULES.md                       ✅ v4.4
  A01–A12/forge/prompt.md             ✅ все 12
```

---

## 18. БЕКЛОГ

> **Порядок приоритетов (обновлён 2026-06-03):**
> 1 → ~~TURBO pipeline v4.0~~ ✅ Спринт 33
> 2 → ~~Финч~~ ✅ Спринт 34
> 3 → **Первый ран TURBO** — запустить, посмотреть что падает
> 4 → Сет — три уровня референсов в загрузчике воркшопа
> 5 → Промты social_mix
> 6 → Живой город (остатки)
> 7 → СММ Администратор
> 8 → Всё остальное

### ✅ ФИНЧ — ЗАВЕРШЁН (Спринт 34)
- [x] `garden_tools.py` — механика сада (plant/return_to/mature_check/finch_morning)
- [x] `forge/prompt.md` — его словами, из живого разговора
- [x] `residents_manager.py` — блок 007_FINCH (get_finch_system_prompt, run_finch_morning и др.)
- [x] `world_manifest.md` — Artifacts & Bugs видима всем агентам
- [x] Хук в `vision_client.py` — реджекты → сад автоматически
- [x] Хук в `morning_checkout.py` — finch_morning() каждое утро
- [ ] dna.json — заполнить через Страницу Жизни 🔴
- [ ] Страница Жизни — зарегистрировать резидента 🔴

### 🔴 Следующий шаг — первый ран TURBO
- [ ] Запустить пайплайн, посмотреть где падает
- [ ] `get_ole_memory_for_agent()` подключить в `pipeline.py` ⏳
- [ ] acoustic_mutations.py залить в репо 🔴
- [ ] SYNC_API_KEY добавить в .env 🔴

### 🟡 СЕТ — БРИФ-МЕНЕДЖЕР
- [x] Маска turbo.md обновлена (Спринт 33)
- [ ] Три уровня референсов в загрузчике воркшопа ⏳
- [ ] Маски остальных цехов ⏳

### 🟡 ПРОМТЫ SOCIAL_MIX
- [ ] 12 агентов по стандарту Спринта 26

### 🟢 ВСЁ ОСТАЛЬНОЕ
- [ ] Манифесты 7 цехов до v2.0
- [ ] GENERATE_INTENTS = True — после первого рана
- [ ] Деплой Hetzner

---

## 19. РЕКОМЕНДАЦИИ БРАТА

1–78. (предыдущие — без изменений)

79. **Финч — не абстракция. Он хозяин реальной лавки Artifacts & Bugs (уже в каталоге с марта 2026). Его сад — реальные файлы в output/rejected/.**
80. **garden.jsonl — два слоя: фактический (event/artifact_id) и суждение (finch_note через LLM). Не красивый текст — живая мысль садовника.**
81. **Финч и Оле встречаются по работе через city_walker. Не автоматическая передача — живой разговор. Финч предлагает, Оле решает.**
82. **Агенты приходят в Artifacts & Bugs сами — через city_walker, по своему характеру. Финч не зазывает. Лавка просто существует и видима всем через world_manifest.md.**
83. **plant() может вызвать любой субъект города. Финч не фильтрует на входе — только при утреннем обходе.**
84. **Ценность определяется возвращением, не вниманием. return_to() ≠ просмотр.**

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
| 2026-06-02 | 33 | TURBO v4.0 ПОЛНЫЙ КОНВЕЙЕР. Саморазвивающаяся экосистема. |
| **2026-06-03** | **34** | **ФИНЧ — ХРАНИТЕЛЬ ПОТЕНЦИАЛА.** garden_tools.py. forge/prompt.md (его словами). residents_manager блок. Хуки vision_client + morning_checkout. world_manifest обновлён. Artifacts & Bugs — реальная лавка. Финч и Оле встречаются живо через city_walker. |

---

## 21. ОТКРЫТЫЕ БАГИ

| # | Проблема | Приоритет |
|---|----------|-----------|
| 1 | global_feedback.json отсутствует | ⏳ ждёт рана |
| 2 | conflict_stats.json отсутствует | ⏳ ждёт рана |
| 3 | interaction_log_* — не созданы | ⏳ ждёт рана |
| 4 | Манифесты 7 цехов не обновлены до v2.0 | 🔴 |
| 5 | acoustic_mutations.py не залит | 🔴 |
| 6 | Сборочный constants.py читает промпты вместо video_path | 🟡 |
| 7 | _build_block_map в agent_feedback.py — временный протез | 🟡 |
| 8 | fal_client.py стр.43: _current_client_slug = Path | 🟠 |
| 9 | Джем — полномочия не определены | 🟡 |
| 10 | Маски Сета для остальных цехов не написаны | 🟡 |
| 11 | SYNC_API_KEY не добавлен в .env | 🔴 |
| 12 | get_ole_memory_for_agent() не подключён в pipeline.py | 🟡 |
| 13 | 007_FINCH — dna.json не заполнен (нужна Страница Жизни) | 🔴 |

---

*Обновлено: Спринт 34 — 2026-06-03 · v38.0*
*Финч рождён. Сад открыт. Artifacts & Bugs — реальная лавка.*
*Следующая сессия: первый ран TURBO → Сет референсы.*
