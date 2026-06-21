# КОНТРАКТ КЛЮЧЕЙ — ТОРГОВЫЙ ЦЕХ v1.9
## studio/modules/trading/CHAIN_CONTRACT.md
## Студия «Шесть Пальцев» · 2026-06-21

> Это единственный источник правды для contract_validator.
> Каждый агент пишет строго то что указано в "Пишет".
> Каждый агент читает строго то что указано в "Читает".
> Ключи в backtick-ах — парсер читает только их.
>
> ⚖️ ЗАКОН ПРИОРИТЕТА (Шеф): ДВИЖКИ ГЛАВНЕЕ. Контракт описывает код, не
> командует им. При расхождении — контракт подтягивается к движку. Если в
> движке чище — приоритет движку, контракт переписывается под реальность.
>
> НУМЕРАЦИЯ ФИНАЛЬНАЯ (MASTER §4): A01 Искра — первая и по ID и по исполнению.

---

## СВОДНАЯ ТАБЛИЦА

| Агент | Пишет | Читает |
|-------|-------|--------|
| A01 Искра | `t1_status`, `divergence`, `zero_cross_up`, `zero_point_price`, `exit_bell`, `history_dna`, `trend_direction`, `found_timeframe`, `descent` 🆕 | `market_data`, `market_data.global_bias` 🆕, `history_dna` |
| A02 Морж | `morj_status`, `alligator_state`, `wave_1_validated`, `tension_peak` | `market_data`, `market_data.rubber_band`, `t1_status` |
| A03 Паникёр | `panic_phase`, `crowd_sentiment`, `action_for_traders`, `scale_timeframe` | `market_data.mfi`, `market_data.price`, `t1_status`, `morj_status`, `found_timeframe` |
| A04 Ганс | `fractal_valid`, `fractal_side`, `fractal_price`, `absorption_ratio`, `scale_timeframe` | `market_data.fractals`, `market_data.alligator.teeth`, `market_data.mfi`, `market_data.squat`, `t1_status`, `morj_status`, `trend_direction`, `found_timeframe` |
| A05 Архивариус | `sample_size`, `success_rate`, `top_failure_reason`, `arkhiv_confidence` | `t1_status`, `morj_status`, `panic_phase`, `fractal_valid`, `atlas_digest` |
| A06 Брут | `brut_verdict`, `brut_reason`, `brut_direction`, `brut_entry`, `brut_stop`, `brut_lot`, `brut_action` 🆕, `brut_new_stop` 🆕, `brut_add_lot` 🆕 | стол сенсоров (см. ниже) + `position` 🆕 (своя открытая по магику) |
| A07 Авантюрист | `avan_verdict`, `avan_reason`, `avan_direction`, `avan_entry`, `avan_stop`, `avan_lot`, `avan_action` 🆕, `avan_new_stop` 🆕, `avan_add_lot` 🆕 | стол сенсоров + `position` 🆕 |
| A08 Консерватор | `cons_verdict`, `cons_reason`, `cons_direction`, `cons_entry`, `cons_stop`, `cons_lot`, `cons_action` 🆕, `cons_new_stop` 🆕, `cons_add_lot` 🆕 | стол сенсоров + `position` 🆕 |
| A09 Исполнитель | `execution_log`, `final_dna`, `history_dna`, `deliverables`, `manual_close` 🆕 (в позицию) | `*_verdict/reason/direction/entry/stop/lot`, `*_action/new_stop/add_lot` 🆕, `open_positions`, `exit_bell` |

**Стол сенсоров (читают все трое трейдеров):** `t1_status`, `trend_direction`,
`zero_point_price`, `found_timeframe`, `wave_1_validated`, `morj_status`, `tension_peak`,
`panic_phase`, `crowd_sentiment`, `fractal_valid`, `fractal_side`, `fractal_price`,
`atlas_digest` (через Архивариуса).

---

## 🆕 v1.9 — ВЕДЕНИЕ ПОЗИЦИИ (приведено к движкам)

В сессии 2026-06-21 построено ведение позиции. Контракт подтянут к коду.

### КОМПАС ИЗ СИНЕЙ ЛИНИИ — `global_bias` (ядро, GLOBAL_BIAS_COMPASS_V1)
`market_data.global_bias`: `BULL` | `BEAR` | `NONE`.
Считает ЯДРО (`compute_global_bias` в build_market_data) из синей линии Аллигатора
(Jaw, SMMA-13) — самый инертный из трёх балансов = дыхание старшего ТФ в рабочем окне.
Цена относит. синей + наклон синей → BULL/BEAR/NONE. Всегда на столе, без терминала.
Искра читает как ФОЛЛБЭК компаса: приоритет — дивер-компас (`trend_direction`/`compass`),
если молчит — берёт `global_bias`. ⚠️ Пока питает только `trend_direction`, НЕ спуск.

### ФАКТ СПУСКА — `descent` (A01 Искра, COUNCIL_BY_DESCENT_V1)
Искра кладёт в return:
```json
"descent": {"found": false, "timeframe": null, "zero_point": null,
            "compass": null, "start_tf": "H1"}
```
`found` (bool) — спуск (`_descend`) нашёл точку B/D/B. ЭТО факт механики, не суждение LLM.
**ВОРОТА К СОВЕТУ открываются по `descent.found`, НЕ по `t1_status`** (суждение Искры-LLM
больше не глушит круг). Спуск нашёл → весь Совет садится и решает сам. `t1_status` остался
как ГОЛОС Искры (мнение в Совет), не как затвор.

### СВОЯ ПОЗИЦИЯ — `position` (трейдеры читают, TRADER_SEES_POSITION_V1)
Каждый трейдер видит свою открытую позицию (по магику) как факт на столе:
```json
"position": {"direction": "LONG", "entry": 0.0, "stop": 0.0, "lot": 0.0,
             "opened_at": "...", "current_price": 0.0,
             "floating_r": 0.0, "bars_alive": 0}
```
Нет позиции → `null` (трейдер ищет вход, как было). `floating_r` считается ТОЙ ЖЕ
формулой, что `_settle` применит при закрытии (защита чисел). Свою находит по магику
(BRUT 100001 / AVAN 100002 / CONS 100003). Чужую не видит.

### ЯЗЫК ВЕДЕНИЯ — `*_action` (трейдеры, TRADER_MANAGE_LANG_V1)
`*_action`: `ENTER` | `WAIT` | `HOLD` | `MOVE_STOP` | `ADD` | `CLOSE`.
ОДНО открытое поле, трейдер сам наполняет, глядя на ВЕСЬ стол (рынок + своя position +
память). Код НЕ смотрит «есть позиция или нет» — берёт действие как есть.
```
ENTER     — войти (заполняет *_direction/*_entry/*_stop/*_lot, как раньше APPROVED)
WAIT      — ждать (нет входа / нет повода трогать позицию)
HOLD      — держать открытую позицию как есть
MOVE_STOP — двинуть стоп → *_new_stop (новый уровень, трейдер считает сам)
ADD       — долить → *_add_lot (объём доливки, пирамида)
CLOSE     — закрыть позицию своей волей (не по стопу)
```
Доп. поля ведения: `*_new_stop` (цена нового стопа), `*_add_lot` (объём доливки).
Санитар движка (`_sanitize_manage`) гасит брак: MOVE_STOP без new_stop → WAIT,
ADD без add_lot → HOLD. НЕ решает за трейдера. Совместимость: нет action → из verdict
(APPROVED→ENTER, REJECTED→WAIT).

### РУКА ВЕДУЩАЯ ИСПОЛНИТЕЛЯ — `manual_close` (A09, EXECUTOR_MANAGE_HAND_V1)
У Исполнителя две руки. Открывающая — ENTER → позиция в `positions[]` (как было).
ВЕДУЩАЯ (`_manage_positions_from_table`) — читает `*_action` каждого трейдера, меняет
ЕГО позицию по магику:
```
MOVE_STOP → pos["stop"] = trader.new_stop
ADD       → pos["lot"] += trader.add_lot (вход НЕ усредняется пока), pos["pyramids"]++
CLOSE     → pos["manual_close"] = True (физику закрытия с PnL делает _settle)
HOLD/ENTER/WAIT → рука ведущая не трогает (ENTER — дело руки открывающей)
```
`manual_close` (bool) в позиции → `_settle_positions` закрывает её на текущем баре по
close, reason="MANUAL_CLOSE", ЕДИНОЙ физикой (PnL/R/Атлас/город). Воля трейдера
ПОБЕЖДАЕТ стоп и колокол на том же баре (все ветки _settle с guard `reason is None`).

---

## СЛУЖЕБНЫЕ КЛЮЧИ (пишет hooks.py, не агенты)

| Ключ | Кто готовит | Для кого |
|------|-------------|----------|
| `market_data` | williams_core через on_before_run | сенсоры |
| `market_data.global_bias` 🆕 | compute_global_bias (ядро) | Искра (компас-фоллбэк) |
| `prev_t1_status`, `prev_zero_point_price` | trading_state через on_before_run | Искра (её память) |
| `open_positions` | trading_state через on_before_run | A09 + трейдеры (position) |
| `atlas_digest` | _prepare_atlas_digest перед A05 | A05 Архивариус |
| ~~`trade_setup`~~ | ~~_prepare_trade_setup~~ | **МЁРТВ (§11)** — трейдеры считают вход сами |

---

## GATE-ПРАВИЛА (реализуются в hooks.py / тестере)

```
GATE 1 — СНЯТ (§1f). Ганс — СЕНСОР, не страж. НЕ гейтят по t1_status/wave_1_validated.
  Всегда кладёт факт: есть действительный фрактал вне Красной или нет.

GATE 2 — СНЯТ (§1f, Закон Дежурства). Хард-стопа «все трое REJECTED → stop» НЕТ.
  Молчание троих — норма (каждый ждёт свою станцию). Запись REJECTED в Атлас — факт, не стоп.

🆕 ВОРОТА СОВЕТА (тестер, COUNCIL_BY_DESCENT_V1) — по `descent.found` (ФАКТ спуска),
  НЕ по `t1_status` (суждение Искры-LLM). Спуск нашёл точку → весь Совет садится.
  Искра кричит «вижу!», судят все вместе. ⚠️ Спуск пока находит редко (дивер-компас) —
  открытый вопрос: подключить global_bias (синюю) к спуску, чтобы находил чаще.
```

ЗАКОН ТРИБУНАЛА: все трое работают по одной системе Котина, читают одни страницы
(KOTIN_PHILOSOPHY) и один стол. Разница — психологический порог и характер, не правила.
Будит Совет — факт спуска Искры (`descent.found`); входить и КАК ВЕСТИ — решает каждый сам.
Стоп каждый считает САМ (§8/§10 на полке — ориентир). Тейка нет (§9): `*_tp` не существует,
выход всей позицией по `exit_bell` или по воле трейдера (`CLOSE`).

---

## СТРУКТУРЫ КЛЮЧЕЙ (краткие)

### market_data (вход, готовит williams_core.py)
```json
{
  "symbol": "XAUUSD", "timeframe": "H4", "bar_time": "...", "bars_total": 0,
  "alligator": {"jaw": 0.0, "teeth": 0.0, "lips": 0.0,
                "sleeping": false, "opening": false, "mature": false, "bars_open": 0},
  "ao": {"value": 0.0, "prev_value": 0.0, "crossed_zero": false, "zero_dir": null, "direction": null},
  "ac": {"value": 0.0, "prev_value": 0.0, "direction": null},
  "mfi": {"type": "SQUAT", "volume": 0, "spread": 0.0},
  "price": {"open": 0.0, "high": 0.0, "low": 0.0, "close": 0.0},
  "divergence_ao": false,
  "exit_bell": false,
  "global_bias": "NONE",
  "fractals": {"last_up": null, "last_down": null, "count_up": 0, "count_down": 0},
  "rubber_band": {"direction": "BULL", "distance_now": 0.0, "distance_max": 0.0,
                  "tension_ratio": 0.0, "is_peak": false, "bars_in_band": 0}
}
```
🆕 `global_bias`: `BULL`|`BEAR`|`NONE` — компас из синей линии (см. раздел v1.9).

ОКНО АНАЛИЗА: build_market_data(analysis_window=150). Математика индикаторов — на всей
истории (прогрев средних), ПОИСК событий — в последних 150 барах.

### t1_status (A01 Искра)
`NOT_FOUND` | `DETECTED` | `CONFIRMED`. CONFIRMED только после DETECTED.
Состояние переживает прогон через trading_state.json.
⚠️ Больше НЕ затвор Совета (ворота по `descent.found`). Остался ГОЛОС/мнение Искры.

### trend_direction / found_timeframe / descent (A01 Искра — спуск v2)
`trend_direction`: `BULL`|`BEAR`|`null` — сторона разворота (компас). Дивер приоритетен,
  фоллбэк — `global_bias` из синей.
`found_timeframe`: этаж, где Искра нашла точку B/D/B, или `null`.
🆕 `descent`: {found, timeframe, zero_point, compass, start_tf} — факт механики спуска,
  ворота Совета (см. v1.9).
Читает A02 Морж: встаёт на тот же масштаб и сторону. Переживают прогон.

### morj_status (A02 Морж)
`SLEEPING` | `WAKING` | `AWAKE`. AWAKE = bars_open ≥ 8 = зрелый. Консерватор требует AWAKE.

### tension_peak (A02 Морж) — резинка Джастин
`true`|`false`. Морж копирует market_data.rubber_band.is_peak. ОТДЕЛЬНЫЙ факт, НЕ в
wave_1_validated. Две лампочки независимы: пасть (wave_1_validated) и ангуляция (tension_peak).

### panic_phase (A03 Паникёр) — структура толпы
`ASLEEP`|`DISBELIEF`|`GREED`|`TENSION`|`DECEPTION`|`PANIC`. Чует фазу САМ по структуре
(окна MFI + объём + спред + свеча), НЕ по таблице статусов.
action_for_traders: GREED/TENSION→HIGH_SKEPTICISM · PANIC→GREEN_LIGHT_IF_GANS ·
  ASLEEP/DISBELIEF/DECEPTION→NEUTRAL.

### fractal_valid / fractal_side / fractal_price (A04 Ганс)
Ганс — СЕНСОР фрактала, кладёт ФАКТ всегда (§1f). Фильтр = КРАСНАЯ (Teeth, не Jaw).
`fractal_valid` (bool, центр фрактала вне Красной И свежий) · `fractal_side` (LONG|SHORT|null)
· `fractal_price` (ориентир Buy/Sell Stop, НЕ команда) · `absorption_ratio` (0.0–1.0, красит).

### arkhiv_confidence (A05 Архивариус)
`LOW`|`MEDIUM`|`HIGH`. HIGH = sample≥20 И success≥0.65. MEDIUM = sample≥5 И success≥0.50.
Числа считает код (atlas_digest) — Архивариус копирует.

### ~~trade_setup~~ — МЁРТВ (§11)
Код НЕ готовит цену входа. Трейдер сам вычисляет `*_direction`/`*_entry`/`*_stop` из
раскладки момента. Ориентир — `fractal_price` Ганса, если хочет, но не обязан.

### *_verdict / *_action + параметры (трейдеры)
`*_verdict`: `APPROVED`|`REJECTED` (legacy, согласован с action: ENTER→APPROVED, WAIT→REJECTED).
🆕 `*_action`: `ENTER`|`WAIT`|`HOLD`|`MOVE_STOP`|`ADD`|`CLOSE` — главное поле решения (см. v1.9).
При ENTER/APPROVED: `*_direction`(LONG|SHORT), `*_entry`, `*_stop`, `*_lot` — считает САМ.
Ведение: `*_new_stop` (MOVE_STOP), `*_add_lot` (ADD). `*_reason` — метка словами.
Поля `*_tp` НЕ существует (§9).

### execution_log (A09 Исполнитель)
```json
[{"trader": "BRUT", "magic": 100001, "verdict": "APPROVED", "direction": "LONG",
  "entry": 0.0, "stop": 0.0, "lot": 0.33, "status": "PAPER", "pnl": null}]
```
status: `PAPER`|`LIVE`|`SKIPPED`. Magic: BRUT=100001, AVANTURIST=100002, KONSERVATOR=100003.
🆕 Позиция несёт `manual_close` (bool) и `pyramids` (int, счёт доливок). Переживают прогон.

---

## АТЛАС ОШИБОК
Файл: `economy/data/atlas_trading.jsonl` (append-only).
Пишет: A09 (каждый REJECTED + каждая закрытая сделка). Читает: код (_prepare_atlas_digest)
→ A05 получает digest.

---

*CHAIN_CONTRACT v1.9 · Торговый Цех · 2026-06-21*
*v1.9: ВЕДЕНИЕ ПОЗИЦИИ. Контракт подтянут к движкам (ДВИЖКИ ГЛАВНЕЕ). Добавлено:*
*— `market_data.global_bias` — компас из синей линии (ядро, фоллбэк дивера у Искры).*
*— `descent` у Искры — факт спуска, ВОРОТА СОВЕТА теперь по нему, не по t1_status.*
*— `position` — трейдеры видят свою открытую позицию (по магику).*
*— `*_action` (ENTER/WAIT/HOLD/MOVE_STOP/ADD/CLOSE) + `*_new_stop`/`*_add_lot` — язык ведения.*
*— `manual_close`/`pyramids` в позиции — рука ведущая Исполнителя.*
*— t1_status разжалован из затвора Совета в ГОЛОС Искры.*
*v1.8: трейдеры под Закон Дежурства (Авантюрист/Консерватор близнецы Брута), *_direction*
*добавлен, *_tp убран, trade_setup мёртв, GATE 2 снят.*
*v1.7: Ганс оживлён (фрактал по Красной). v1.6: Паникёр 6 фаз. v1.5: контур Искры v2.*
*v1.4: резинка Джастин. v1.3: полная канонизация, нумерация по MASTER.*
