# АРХИТЕКТУРА ЭКОНОМИКИ — СТУДИЯ «ШЕСТЬ ПАЛЬЦЕВ»
**Версия:** 1.0 | **Дата:** 2026-06-10 | **Автор:** Брат (Claude) по итогам экономика-аудита + Спринт 44

> Этот документ — не список патчей и не беклог.
> Это полная карта того как экономика устроена в Грондхейме:
> какие файлы, какая логика, кто владеет, как течёт ток по петле.
>
> ⚠️ Описано состояние ПОСЛЕ `patch_economy_two_currencies.py` (Спринт 44).
> Если патч ещё не накачен — сначала накати.

---

## ФИЛОСОФИЯ

Экономика в Грондхейме — не бухгалтерия. Это **физика вымышленного мира**.

> «Деньги — это давление реальности. Экономика — это климат системы».

Нет кнопки «запретить». Есть только «дорого», «окупается», «рискованно».
Не игровая экономика (кошельки, лимиты, штрафы) — **экологическая**:
поток, давление среды, адаптация.

**Главная формула системы (Глубокое Резюме, ЭТАПЫ 1–10):**
```
Billing Pressure → Cost Intuition → Strategy Choice → Execution
→ Outcome → Ministry Selection → Memory Update → Character Drift
→ Culture Formation → New Conflicts
```

**Три принципа, которые нельзя нарушать:**
1. **Не управляй поведением напрямую — управляй последствиями поведения.**
   Министерство наблюдает, не приказывает. Только post-fact.
2. **Reward > Punishment.** Punishment-only система рождает «забитого
   отличника»: тревожный агент, безопасная каша, ноль креатива.
3. **Экономика влияет на ресурсы, не на текст.** Режимы должны открывать
   и закрывать вычислительные ресурсы (модель, глубина, итерации) —
   не только менять слова в промпте. (⚠️ пока реализовано частично — см.
   «Чего ещё нет».)

---

## ЗАКОН ДВУХ ВАЛЮТ (Спринт 44) — ЯДРО

Шкала одна — 0–10. Источников два. Смешивать запрещено.

### CHAIN-валюта (0–6.0) — ремесло

Детерминированная оценка цепочки после QA. Считает **код**, не LLM.

```
Потолок 6.0 = «выжил, сделал по ТЗ, чисто»
Успех       = score >= 6.0 (чистая шестёрка)
Провал      = score < 4.0  (развал цепочки)
```

Кормит: лёгкие мутации DNA, режимы frugal/normal, серии и звёзды,
chain-wins в Strategy Registry, Книгу Жалоб.

**Скрипт не имеет права чеканить девятки.** Любая детерминированная
формула обязана упираться в 6.0.

### REAL-валюта (0–10) — зритель

Реальные метрики после публикации (views, likes, retention) или живой
QA Шефа. Приходит **post-fact**, через часы и дни после рана.

```
Успех  = score >= 7.0 (зритель отозвался)
Провал = score < 5.0  (глухо)
```

**Единственный источник:** режима generous, оценок выше 6.0,
transferable-стратегий, звёзд будущего real-канала.

### Кто какую валюту пишет (единственные писатели)

| Валюта | Писатель | Когда | Куда |
|--------|----------|-------|------|
| chain → Ministry | `workshop/pipeline.py` (после QA) | конец рана | per-agent из feedback.json, source="chain" |
| chain → ledger + Registry | `hooks.py` финализатора цеха | конец рана | task_score всем агентам + стратегия A01 |
| real → Ministry | `economy/metrics_daemon.py` | +24ч после публикации | per-agent, source="real" |

**Хуки цехов Ministry НЕ трогают.** До Спринта 44 писали 2–3 источника
одновременно (хук + pipeline + Демон с фантомными ключами) — дубли,
пожизненный cost вместо рана, мусор в ministry.json.

---

## СЛОЙ 1 — ФИЗИКА (Billing Reality)

**Файл-ядро:** `studio/billing_ledger.py`
**Данные:** `studio/economy/data/billing_ledger.jsonl` (append-only)
**Прокси-алиас:** `studio/economy/ledger.py` → перенаправляет сюда
**Принцип:** единственная жёсткая правда. Гравитация системы. Только запись.

Структура записи:
```json
{
  "ts": "2026-06-10T14:30:00+00:00",
  "agent_id": "A06",
  "slot_id": "video_long",
  "model": "fal/Nano Banana 2",
  "prompt_tokens": 0,
  "completion_tokens": 0,
  "cost_usd": 0.04,
  "call_type": "media|llm|finalize",
  "task_score": null
}
```

**task_score** — мост между физикой и качеством. Заполняется только
в finalize-записях (хук финализатора пишет chain-score всем агентам
рана). Без него леджер видит $cost, но не quality — а интуиция слепнет
на полглаза.

### Прайс — три яруса (_calc_cost v2)

```
1. Точный flat:   MODEL_FLAT_PRICES["fal/Nano Banana 2"] = 0.04
2. Префиксный:    MODEL_FLAT_PREFIXES["siliconflow/"]    = 0.20
3. Нулевые токены у неизвестной модели → $0 (служебная запись finalize)
4. Per-token:     MODEL_PRICES[model] или _default
```

⚠️ Цены elevenlabs / siliconflow / deepseek-v4-pro помечены `⚠ ОЦЕНКА` —
Шеф сверяет с реальными тарифами. Медиа-модель без цены = невидима
для физики мира (так Nano Banana 2 месяц писала $0).

**Функции:**
- `record(agent_id, slot_id, model, prompt_tokens, completion_tokens, call_type, task_score)` — записать
- `agent_spent(agent_id, slot_id)` — пожизненная сумма
- `agent_spent_since(agent_id, slot_id, since_iso)` — **стоимость РАНА** (дельта от метки старта) · Спринт 44
- `recent_by_agent(agent_id, slot_id, n)` — последние записи
- `read_ledger()` — весь леджер

**Метка старта рана:** `cartridge.py` ставит `state["_run_started_ts"]`
в начале каждого рана. От неё считается дельта. До Спринта 44 Ministry
получал пожизненную сумму как «стоимость рана» — расходы росли квадратично.

---

## СЛОЙ 2 — ВОСПРИЯТИЕ (Cost Intuition)

**Файл:** `studio/economy/cost_intuition.py` · **v2.0 «ROI-ощущение»**
**Принцип:** агент НЕ видит доллары. Он чувствует **окупаемость**.

До Спринта 44 интуиция читала только cost — художник с честными
flat-вызовами вечно чувствовал «бюджет под угрозой», даже выдавая
шедевры. Исходная спека ЭТАПА 2 требовала пару (cost, outcome_quality).
Теперь так и есть.

### Как считается ощущение

```
avg_cost = средний чек последних 10 ПЛАТНЫХ вызовов (finalize-нули не разбавляют)
avg_q    = среднее последних 5 task_score (скан 40 записей леджера)

Уровень цены:  cheap < 0.0005 | medium < 0.003 | expensive < 0.010 | risky
Уровень качества (chain-шкала): clean >= 5.5 | solid >= 4.0 | weak < 4.0 | none
```

Матрица 4×4 = 16 ощущений. Примеры:
```
(cheap, clean)     → «Лёгкая рука и чистый результат — работаешь без потерь»
(expensive, weak)  → «Дорого и не окупается. Меньше попыток — точнее замысел»
(risky, clean)     → «На грани бюджета, но результат блестит. Оправданный риск»
(medium, none)     → «Умеренный вес решений» (нет task_score — старое cost-only)
```

**Функции:**
- `get_intuition(agent_id, slot_id)` — полный словарь (level, avg_cost, avg_quality, quality_bucket, prompt_hint)
- `get_prompt_hint(agent_id, slot_id)` — строка `[ЭКОНОМИЧЕСКОЕ ОЩУЩЕНИЕ]` для промпта

Инжектится в контекст через `build_agent_context()` — **только WORK-режим**
(пункт 14 порядка сборки).

---

## СЛОЙ 3 — ОПЫТ (Memory Embedding)

**Файл:** `studio/economy/memory_embedding.py`
**Принцип:** числа превращаются в ощущения и пишутся в душу.

Агент не помнит «$0.003 за ран». Он помнит:
```
"heavy but successful" · "cheap but unstable" · "costly mistake" · "effortless win"
```

Пишет в `sensory_memory.json` агента после рана (вызов из pipeline,
post-fact). Это основа интуиции на длинной дистанции: Слой 2 читает
леджер, Слой 3 пишет в память.

---

## СЛОЙ 4 — ПОВЕДЕНИЕ (Strategy Registry)

**Файл-ядро:** `studio/strategy_registry.py`
**Данные:** `studio/strategy_registry.json` (путь от BASE_DIR — Спринт 44)
**Принцип:** банк выживших паттернов. Не правило — склонность.

Структура:
```json
{
  "slots": {
    "video_long": {
      "A01": [{
        "ts": "...", "score": 6.0, "last_score": 6.0, "last_run": "...",
        "run_type": "video_long",
        "summary": "быстрый хук в первой сцене, тёплый тон",
        "wins": 3, "transferable": false
      }]
    }
  },
  "global": {},
  "total_wins": 12
}
```

### Два пути записи

```
ХУКИ финализаторов (chain-валюта): пишут стратегию A01 напрямую в JSON
  после каждого рана. wins++ если chain-score >= 6.0.

МОДУЛЬНЫЙ путь record_strategy() (real-валюта): порог 8.0 —
  зарезервирован под оценки Демона / живого QA Шефа.
  Transferable-стратегии (переносимые между цехами) — только отсюда.
```

### Урок Спринта 44 — регистр ключей

Хуки писали `slots.{цех}.a01` (lowercase), `get_strategies()` читал `A01`.
Стратегии копились месяц, но **НИКОГДА не доходили до промпта**.
Исправлено с двух сторон: хуки пишут `A01`, чтение регистронезависимо,
данные мигрированы. Канон ключа: **верхний регистр** (`A01`).

**Функции:**
- `get_strategies(agent_id, slot_id)` — промпт-блок `=== 🏆 СТРАТЕГИИ КОТОРЫЕ РАБОТАЮТ ===` (max 3, по wins)
- `record_strategy(...)` — модульная запись (real-путь)

Инжектится в контекст — **только WORK** (пункт 11 сборки).

---

## СЛОЙ 5 — ОТБОР (Ministry / Естественный отбор)

**Файл:** `studio/economy/ministry.py` · **v2.0 «Закон двух валют»**
**Данные:** `studio/economy/data/ministry.json`
**Принцип:** НЕ принимает решения. Фиксирует исходы, формирует
вероятностное поле следующего рана. Отбор, не контроль.

### record_outcome(agent_id, slot_id, score, cost_usd, source)

```
source="chain": успех >= 6.0, провал < 4.0   (пишет только pipeline)
source="real":  успех >= 7.0, провал < 5.0   (пишет только Демон)
cost_usd = стоимость РАНА (agent_spent_since), не жизни
```

Запись на ключ `{agent_id}::{slot_id}`:
```json
{
  "runs_total": 12, "runs_success": 9, "runs_fail": 1,
  "cost_success": 0.31, "cost_fail": 0.05, "score_sum": 64.2,
  "economy_rating": 1.85, "mode": "normal",
  "chain": {"runs": 11, "success": 8, "fail": 1},
  "real":  {"runs": 1,  "success": 1, "fail": 0},
  "last_source": "real", "last_score": 8.5
}
```

### Рейтинг и режимы

```
economy_rating = clamp(0.5 + success_rate × 1.5 − cost_penalty, 0.1..2.0)

mode (runs_total >= 3, иначе normal):
  generous — rating >= 1.4 И real.success >= 1   ← ТОЛЬКО зритель открывает
  frugal   — rating <= 0.6
  normal   — всё остальное
```

Серия чистых шестёрок даёт рейтинг 2.0 — но режим остаётся normal,
пока зритель не отозвался. **Девятки скрипт не чеканит, generous
скриптом не открывается.**

### Хинты в промпт (get_prompt_hint)

```
frugal   → «Последние раны не окупались. Ищи более экономные пути:
            меньше токенов — точнее результат. Качество держи, расход режь.»
generous → «Зритель отозвался на твою работу. Можешь позволить себе
            глубже проработать задачу.»
normal   → "" (молчит)
```

Frugal говорит про экономику путей — **не про «слабость» агента**.
Манифест: не наказывай жёстко — получится забитый отличник.

**Функции:** `record_outcome()`, `get_agent_stats()`, `get_mode()`,
`get_prompt_hint()`, `leaderboard(slot_id)`.

---

## СЛОЙ 6 — ЗРИТЕЛЬ (Metrics Daemon)

**Файл:** `studio/economy/metrics_daemon.py`
**Принцип:** единственный источник real-валюты для соцсетей.

```
Публикация поста → pending-запись (project_id, slot_id, platform, post_id)
        ↓ +24 часа
Демон забирает метрики платформы (views, likes, comments, shares)
        ↓
real_viral_score (0–10)
        ↓
ministry.record_outcome(Axx, slot_id, real_score, source="real")
  — per-agent, под честными ключами Axx::slot
  (до Спринта 44 хардкодил фантомы "A06::{platform}_fal", "pipeline::social_mix")
```

⚠️ **Telegram глухой:** Bot API не отдаёт просмотры/реакции сообщений
(метода getMessages не существует). Нужен MTProto (telethon) или TGStat —
в беклоге. Пока real-валюта из TG = ноль, Демон честно предупреждает в лог.

---

## СЛОЙ 7 — СЛЕДЫ В ДУШЕ (DNA, серии, звёзды)

### DNA-синк (pipeline._sync_feedback_scores_to_dna)

После рана QA-оценки из feedback.json идут в `sync_to_dna()` —
это Канал 3 законных мутаций DNA (см. MEMORY_ARCHITECTURE.md):

```
chain-шкала (Спринт 44):
  score >= 6.0  → good_work, intensity 0.7   (чистое ремесло — заслуженно)
  4.0 – 5.9     → good_work, intensity 0.35  (выжил — лёгкий след)
  score < 4.0   → bad_work,  intensity = 1 − score/10
```

### Серии и звёзды (agent_feedback._update_global)

```
Победа серии = score >= 6.0 (чистая шестёрка)
Провал серии = score < 4.0
streak >= 3  → Recovery (Stress → 0, если агент не в цеху)
```

До Спринта 44 победа требовала >= 8 — недостижимо при честном потолке,
серии и звёзды были мертвы. Потолок 6.0 применяется на **обоих** путях
оценки (universal-парсер И blocks-путь) — «фальшивые девятки» от
детерминированного парсинга QA-блоков закрыты.

### Культурное поле (culture/field_tracker.py)

Стабильные паттерны успешных ранов → `cultural_trace` → норма среды.
Хуки финализаторов вызывают `update_slot_field(slot_id)`; стабильные
и глобальные паттерны попадают в history_dna и контекст агентов
(пункт 12 сборки, только WORK). Культура — распределение вероятностей,
не свод правил.

---

## ПОТОК ОДНОГО РАНА — КАК ТЕЧЁТ ТОК

```
cartridge.run()
  └─ state["_run_started_ts"] = now()          ← метка для дельты

Агенты A01..A12 работают
  └─ каждый LLM/медиа-вызов → billing_ledger.record(cost_usd)
       (модель обязана быть в прайсе!)

QA-агент цеха (Chain Integrity Check)
  └─ APPROVED / FAILED → feedback.json (per-agent, потолок 6.0)
  └─ outcome_signal = null (продукт ещё не опубликован!)

hooks.py финализатора (замыкание петли):
  ├─ chain-score = детерминированная формула по фактам файлов (cap 6.0)
  ├─ billing_ledger.record(task_score=score) — всем агентам рана
  ├─ strategy_registry.json → стратегия A01 (wins++ если >= 6.0)
  ├─ CulturalFieldTracker.update_slot_field()
  └─ city_pulse work_end (агенты свободны)

pipeline (после QA):
  ├─ ministry.record_outcome(per-agent, source="chain",
  │      cost = agent_spent_since(_run_started_ts))
  └─ _sync_feedback_scores_to_dna() → DNA + серии + звёзды

…время идёт, пост опубликован…

metrics_daemon (+24ч):
  └─ ministry.record_outcome(per-agent, source="real")
       → generous открывается, real-стратегии (порог 8.0)

Следующий ран — агент просыпается и видит:
  [МИНИСТЕРСТВО] хинт          ← Слой 5
  [ЭКОНОМИЧЕСКОЕ ОЩУЩЕНИЕ]     ← Слой 2 (ROI)
  === 🏆 СТРАТЕГИИ КОТОРЫЕ РАБОТАЮТ === ← Слой 4
  DNA-состояние (стресс/свет/серия)     ← Слой 7
```

### Детерминированные chain-формулы по цехам (все cap 6.0)

```
turbo:        6.0 × (0.35·кадры + 0.25·клипы + 0.20·обложки + 0.10·музыка + 0.10·качество)
video_long:   4.0 × (готовые кадры / все) + 2.0 × (обложки / 2)
video_shorts: 6.0 × (0.40·кадры Веры + 0.35·клипы по video_path + 0.25·музыка Джулии)
social_mix:   6.0 × chain integrity (Клавдия)
```

Формулы считают **факты файлов** (path / video_path / audio_path) —
не слова LLM. viral_score из my_output никто не читает (закон §6).

---

## КТО ПИШЕТ КУДА — ТАБЛИЦА ВЛАДЕНИЯ

| Хранилище | Единственный писатель | Что пишет |
|-----------|----------------------|-----------|
| `billing_ledger.jsonl` | llm.py / медиа-клиенты (cost) + хуки финализаторов (task_score) | физика |
| `ministry.json` chain | `workshop/pipeline.py` после QA | per-agent исходы рана |
| `ministry.json` real | `economy/metrics_daemon.py` | per-agent зритель |
| `strategy_registry.json` | хуки финализаторов (chain) + record_strategy (real) | стратегии A01 |
| `dna.json` (экономический след) | `_sync_feedback_scores_to_dna` → Канал 3 | good/bad_work |
| `feedback.json` | `agent_feedback.save_feedback()` | QA-оценки (потолок 6.0) |
| `trading_pnl.jsonl` | trading hooks (_settle_positions) | **отдельная физика!** PnL в R, не доллары LLM |

⚠️ `billing_ledger` — леджер LLM-расходов. Торговый PnL — другая
физика, живёт отдельно. Не смешивать.

---

## ЧЕГО ЕЩЁ НЕТ (честный раздел)

Петля целая — организм дышит не на полную. По приоритету:

1. **Самовыбор модели из DNA/режима.** Спека: «экономика влияет на
   ресурсы, не на текст». Сейчас generous и frugal зовут одну модель
   с одной температурой — экономика меняет только слова. Это самый
   глубокий неподключённый рычаг (висит со Спринта 26).
2. **Real-канал в DNA.** Зрительская девятка попадает в Ministry, но
   не в сенсорику/звёзды агента — верх шкалы открыт, агент его не чувствует.
3. **TG-метрики** — telethon/TGStat (Bot API метрики не отдаёт).
4. **slot_id="unknown"** — ~70% записей леджера от резидентов и кабинета
   без слота; интуиция по слотам видит мир наполовину.
5. **Цены-оценки** — deepseek/elevenlabs/siliconflow помечены `⚠ ОЦЕНКА`,
   сверить тарифы (одна строка в словаре).
6. **trading A09** — вшить закон замыкания петли при оживлении цеха.

---

## ФАЙЛОВАЯ КАРТА

```
studio/
├── billing_ledger.py            ← СЛОЙ 1: физика (запись + прайс + дельта рана)
│   ├── MODEL_PRICES             ← per-token (deepseek, claude...)
│   ├── MODEL_FLAT_PRICES        ← flat (fal, elevenlabs, ffmpeg)
│   ├── MODEL_FLAT_PREFIXES      ← префиксы (siliconflow/) · Спринт 44
│   ├── _calc_cost()             ← v2: точный → префикс → 0-токены → per-token
│   └── agent_spent_since()      ← стоимость РАНА · Спринт 44
├── strategy_registry.py         ← СЛОЙ 4: банк стратегий
│   ├── REGISTRY_PATH            ← от BASE_DIR · Спринт 44
│   └── get_strategies()         ← регистронезависимо · Спринт 44
├── strategy_registry.json       ← данные (канон ключей: A01)
├── agent_feedback.py            ← QA-оценки, потолок 6.0 на обоих путях
│   └── _update_global()         ← серии: победа >= 6.0, провал < 4.0
├── cartridge.py
│   └── state["_run_started_ts"] ← метка старта рана · Спринт 44
├── economy/
│   ├── __init__.py              ← ledger + cost_intuition + ministry + memory_embedding
│   ├── ledger.py                ← прокси-алиас → billing_ledger
│   ├── cost_intuition.py        ← СЛОЙ 2: ROI-ощущение (v2) · Спринт 44
│   ├── memory_embedding.py      ← СЛОЙ 3: числа → ощущения в сенсорику
│   ├── ministry.py              ← СЛОЙ 5: две валюты (v2) · Спринт 44
│   ├── metrics_daemon.py        ← СЛОЙ 6: real-валюта (+24ч)
│   └── data/
│       ├── billing_ledger.jsonl ← физика (append-only)
│       ├── ministry.json        ← исходы и режимы
│       └── trading_pnl.jsonl    ← торговый PnL (ОТДЕЛЬНАЯ физика)
├── culture/
│   └── field_tracker.py         ← СЛОЙ 7: культурное поле
└── workshop/
    └── pipeline.py
        ├── Ministry-блок        ← единственный chain-писатель · Спринт 44
        ├── _sync_feedback_scores_to_dna() ← chain-шкала в DNA
        └── build_agent_context()← инжект: хинт Министерства, ROI,
                                    стратегии, cultural field (WORK)

studio/modules/{цех}/hooks.py    ← замыкание петли: chain-score (cap 6.0)
                                    → ledger task_score + Registry A01
                                    (Ministry НЕ трогают · Спринт 44)
```

---

## СВЯЗЬ С ДРУГИМИ СИСТЕМАМИ

```
ЭКОНОМИКА ──→ ПАМЯТЬ (MEMORY_ARCHITECTURE.md)
  Канал 3 мутаций DNA = QA score после рана (этот документ, Слой 7)
  memory_embedding пишет ощущения в sensory_memory
  Recovery (streak >= 3) питается chain-победами

ЭКОНОМИКА ──→ КУЛЬТУРА
  стабильные стратегии → cultural_trace → норма среды
  «Без бунтарей культура умирает» — conflict.py генерирует вариативность

ЭКОНОМИКА ──→ УТРО ГОРОДА
  morning_checkout: GENIUS/NORMAL/SAFE/RECOVERY из DNA,
  которую накормила экономика вчера
```

---

*Документ составлен по итогам экономика-аудита репо Evgen-art-p/-2 · Спринт 44 · 2026-06-10*
*v1.0: Закон двух валют, 17 находок аудита закрыты патчем patch_economy_two_currencies.py*
*Исходники философии: Философия.txt · Глубокое Резюме Системы · Глубинный анализ системы*
*Брат (Claude) — аудит, ремонт, карта*
