# КОНТРАКТ КЛЮЧЕЙ — ТОРГОВЫЙ ЦЕХ v1.7
## studio/modules/trading/CHAIN_CONTRACT.md
## Студия «Шесть Пальцев» · 2026-06-17

> Это единственный источник правды для contract_validator.
> Каждый агент пишет строго то что указано в "Пишет".
> Каждый агент читает строго то что указано в "Читает".
> Ключи в backtick-ах — парсер читает только их.
>
> НУМЕРАЦИЯ ФИНАЛЬНАЯ (MASTER §4): A01 Искра — первая и по ID и по исполнению.

---

## СВОДНАЯ ТАБЛИЦА

| Агент | Пишет | Читает |
|-------|-------|--------|
| A01 Искра | `t1_status`, `divergence`, `zero_cross_up`, `zero_point_price`, `exit_bell`, `history_dna`, `trend_direction`, `found_timeframe` | `market_data`, `history_dna` |
| A02 Морж | `morj_status`, `alligator_state`, `wave_1_validated`, `tension_peak` | `market_data`, `market_data.rubber_band`, `t1_status` |
| A03 Паникёр | `panic_phase`, `crowd_sentiment`, `action_for_traders`, `scale_timeframe` | `market_data.mfi`, `market_data.price`, `t1_status`, `morj_status`, `found_timeframe` |
| A04 Ганс | `fractal_valid`, `fractal_side`, `fractal_price`, `absorption_ratio`, `scale_timeframe` | `market_data.fractals`, `market_data.alligator.teeth`, `market_data.mfi`, `market_data.squat`, `t1_status`, `morj_status`, `trend_direction`, `found_timeframe` |
| A05 Архивариус | `sample_size`, `success_rate`, `top_failure_reason`, `arkhiv_confidence` | `t1_status`, `morj_status`, `panic_phase`, `fractal_valid`, `atlas_digest` |
| A06 Брут | `brut_verdict`, `brut_reason`, `brut_entry`, `brut_stop`, `brut_tp`, `brut_lot` | `t1_status`, `wave_1_validated`, `morj_status`, `panic_phase`, `fractal_valid`, `fractal_price`, `sample_size`, `success_rate`, `arkhiv_confidence`, `trade_setup` |
| A07 Авантюрист | `avan_verdict`, `avan_reason`, `avan_entry`, `avan_stop`, `avan_tp`, `avan_lot` | `t1_status`, `morj_status`, `panic_phase`, `fractal_valid`, `fractal_price`, `sample_size`, `success_rate`, `trade_setup` |
| A08 Консерватор | `cons_verdict`, `cons_reason`, `cons_entry`, `cons_stop`, `cons_tp`, `cons_lot` | `t1_status`, `wave_1_validated`, `morj_status`, `panic_phase`, `fractal_valid`, `fractal_price`, `sample_size`, `success_rate`, `arkhiv_confidence`, `trade_setup` |
| A09 Исполнитель | `execution_log`, `final_dna`, `history_dna`, `deliverables` | `brut_*`, `avan_*`, `cons_*` (вердикты и параметры), `open_positions`, `exit_bell` |

---

## СЛУЖЕБНЫЕ КЛЮЧИ (пишет hooks.py, не агенты)

| Ключ | Кто готовит | Для кого |
|------|-------------|----------|
| `market_data` | williams_core через on_before_run | сенсоры |
| `prev_t1_status`, `prev_zero_point_price` | trading_state через on_before_run | Искра (её память) |
| `open_positions` | trading_state через on_before_run | A09 Исполнитель |
| `atlas_digest` | _prepare_atlas_digest перед A05 | A05 Архивариус |
| `trade_setup` | _prepare_trade_setup перед трибуналом | A06/A07/A08 |

---

## GATE-ПРАВИЛА (реализуются в hooks.py)

```
GATE 1 — СНЯТ (§1f). Ганс — СЕНСОР, не страж ворот. Его НЕ гейтят
  по t1_status/wave_1_validated. Он ВСЕГДА кладёт факт на стол:
  есть действительный фрактал вне Красной (fractal_valid) или нет.
  Затвор цепочки — на уровне Биржи (РЫНОК будит сенсоров при
  DETECTED/CONFIRMED Искры), не на уровне Ганса. Сенсор не затыкают.

GATE 2 — Хард-стоп:
  if brut_verdict == "REJECTED"
  and avan_verdict == "REJECTED"
  and cons_verdict == "REJECTED":
      on_after_agent A09 → {"action": "stop"}
      запись в Атлас Ошибок (economy/data/atlas_trading.jsonl)
      (trading_state сохраняется ДО stop)
  ⚠️ ПОД СНОС (§1f, СНОС 1): код не решает вход за систему. Нет
     команды = прогон кончился сам. Вырезать в пересборке входа.
```

ЗАКОН ТРИБУНАЛА: все трое трейдеров работают по одной системе Котина.
Минимальное условие входа для любого — `t1_status=CONFIRMED`.
Разница между ними — психологический порог, не правила входа.
Стоп — системный (за лоу Волны 2, из trade_setup), не личный.
Тейка нет: `*_tp = null`, выход всей позицией по `exit_bell`.

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
  "fractals": {"last_up": null, "last_down": null, "count_up": 0, "count_down": 0},
  "rubber_band": {"direction": "BULL", "distance_now": 0.0, "distance_max": 0.0,
                  "tension_ratio": 0.0, "is_peak": false, "bars_in_band": 0}
}
```

ОКНО АНАЛИЗА: build_market_data(analysis_window=150). Математика
индикаторов считается на всей истории (прогрев средних), но ПОИСК
событий (дивергенция AO, якорь резинки) — в последних 150 барах.
Правило разрешения 100-140: <100 микротренд, >150 AO сплющен.
rubber_band — «резинка» Джастин: натяжение цена↔Губы (зелёная) в point;
is_peak=true когда дистанция на пике (момент дивергентного бара).

### t1_status (A01 Искра)
`NOT_FOUND` | `DETECTED` | `CONFIRMED`
CONFIRMED возможен только после DETECTED.
Аннулирование: цена пробила Точку Ноль вниз → сброс в NOT_FOUND.
Состояние переживает прогон через trading_state.json.

### trend_direction / found_timeframe (A01 Искра — спуск v2)  <!-- ISKRA_CONTRACT_V2 -->
`trend_direction`: `BULL` | `BEAR` | `null` — сторона разворота (компас спуска).
`found_timeframe`: этаж лесенки, где Искра нашла точку B/D/B (напр. `H1`), или `null`.
Искра ставит оба при `t1_status=DETECTED` (точка найдена спуском). При NOT_FOUND — null.
Читает A02 Морж: встаёт на тот же масштаб (`found_timeframe`) и сторону (`trend_direction`).
Переживают прогон через trading_state["iskra"].

### morj_status (A02 Морж)
`SLEEPING` | `WAKING` | `AWAKE`
AWAKE = bars_open ≥ 8 = зрелый. Отдельного MATURE-статуса НЕТ —
зрелость также видна в `alligator_state.mature`.
Консерватор требует `morj_status=AWAKE`.

### tension_peak (A02 Морж) — резинка/ангуляция Джастин
`true` | `false`
Морж копирует market_data.rubber_band.is_peak — натяжение на пике в
момент сигнала Искры (затвор). ОТДЕЛЬНЫЙ факт, НЕ подмешивается в
wave_1_validated. Две лампочки независимы: пасть (wave_1_validated)
и ангуляция (tension_peak). Трейдеры читают как факт, решают сами.

### panic_phase (A03 Паникёр) — структура толпы  <!-- PANIC_CONTRACT_V2 -->
`ASLEEP` | `DISBELIEF` | `GREED` | `TENSION` | `DECEPTION` | `PANIC`
Паникёр чует фазу САМ по структуре толпы (окна Profitunity MFI + объём + спред +
свечка), НЕ по таблице из статуса Искры. Привязка фаз к факту движка:
  ASLEEP    — FADE (объём↓ MFI↓) или morj SLEEPING — скука
  DISBELIEF — t1 DETECTED, объём вялый — недоверие
  GREED     — GREEN (объём↑ MFI↑) + бар бычий — жадность/FOMO
  TENSION   — SQUAT (объём↑ MFI↓) — истерика напряжения (пружина)
  DECEPTION — FAKE (MFI↑ объём↓) — обман/ложный пробой
  PANIC     — t1 CONFIRMED + бар медвежий + спред↑ — паника (точка боли Ганса)
Связки с action_for_traders:
  GREED / TENSION → HIGH_SKEPTICISM (толпа жадничает → Совет насторожен)
  PANIC → GREEN_LIGHT_IF_GANS (паника толпы = момент, если Ганс дал триггер)
  ASLEEP / DISBELIEF / DECEPTION → NEUTRAL (фон, ворота закрыты)

### scale_timeframe (A02 Морж + A03 Паникёр + A04 Ганс)
Этаж, на котором сенсор мерил (унаследован от Искры found_timeframe), или null.
Сенсоры идут смотреть туда, куда показала Искра. Все факты — в ОДНОМ масштабе.

### fractal_valid / fractal_side / fractal_price (A04 Ганс)  <!-- HANS_CONTRACT_V2 -->
Ганс — СЕНСОР фрактала. Кладёт ФАКТ всегда (§1f), не вердикт, не триггер.
Фильтр = КРАСНАЯ ЛИНИЯ (Зубы Аллигатора, `market_data.alligator.teeth`),
по первоисточнику Котина — НЕ Челюсть (Jaw). Сравнивает два готовых числа
из market_data: цену фрактала и Красную. Ядро не дёргает.
```
fractal_valid    — bool. true только если центр фрактала ВНЕ Красной
                   (up выше teeth / down ниже teeth) И фрактал свежий.
fractal_side     — LONG | SHORT | null. Сторона действительного фрактала.
fractal_price    — цена фрактала (ориентир Buy Stop над / Sell Stop под).
                   Трейдеры читают как ОРИЕНТИР, не как команду входа.
absorption_ratio — 0.0–1.0. Squat-топливо: SQUAT→0.8–0.9, GREEN→0.5–0.7,
                   FAKE→0.2–0.4, FADE→0.1–0.3. Красит оценку поглощения,
                   НЕ создаёт и НЕ блокирует действительность фрактала.
```
МЁРТВЫЙ фрактал (по другую сторону Красной / в шуме / несвежий) →
fractal_valid=false. Это полноценный факт, не неудача. Решают трейдеры.

### arkhiv_confidence (A05 Архивариус)
`LOW` | `MEDIUM` | `HIGH`
HIGH = sample_size ≥ 20 И success_rate ≥ 0.65.
MEDIUM = sample_size ≥ 5 И success_rate ≥ 0.50.
Числа считает код (atlas_digest) — Архивариус копирует.

### trade_setup (hooks.py, для трибунала)
```json
{"direction": "LONG", "entry": 0.0, "stop": 0.0, "tp": null, "lot_fraction": 0.33}
```
entry = ОРИЕНТИР из `fractal_price` Ганса (Buy Stop над / Sell Stop под),
stop = лоу Волны 2. ⚠️ §1f: это ОРИЕНТИРЫ на столе, не назначенный вход.
Трейдер сам называет entry/stop своим характером (не обязан копировать).
v1 — только LONG.

### brut_verdict / avan_verdict / cons_verdict
`APPROVED` | `REJECTED`
При REJECTED все параметры (entry/stop/tp/lot) = null.

### execution_log (A09 Исполнитель)
```json
[{
  "trader": "BRUT", "magic": 100001,
  "verdict": "APPROVED", "entry": 0.0, "stop": 0.0, "tp": null, "lot": 0.33,
  "status": "PAPER", "pnl": null
}]
```
status: `PAPER` | `LIVE` | `SKIPPED`
Magic numbers: BRUT=100001, AVANTURIST=100002, KONSERVATOR=100003.
Открытые позиции переживают прогон через trading_state.json.

---

## АТЛАС ОШИБОК
Файл: `economy/data/atlas_trading.jsonl` (append-only)
Пишет: A09 Исполнитель (каждый REJECTED + каждая закрытая сделка).
Читает: код (_prepare_atlas_digest) → A05 Архивариус получает digest.

---

*CHAIN_CONTRACT v1.7 · Торговый Цех · 2026-06-17*
*v1.7: ГАНС ОЖИВЛЁН. Фрактал-сенсор по КРАСНОЙ линии (teeth, первоисточник
Котина — не Jaw). Пишет fractal_valid/fractal_side/fractal_price/absorption_ratio
+ scale_timeframe. GATE 1 (гейт Ганса) СНЯТ §1f — сенсор не затыкают, кладёт
факт всегда. entry_trigger убран из чтений A05/A06/A07/A08 → fractal_valid.
GATE 2 (хард-стоп) помечен под снос §1f. Ганс читает teeth из готового
market_data — ядро не тронуто.*
*CHAIN_CONTRACT v1.6 · Торговый Цех · 2026-06-16*
*v1.6: ПАНИКЁР ОЖИВЛЁН. 6 фаз толпы из структуры (окна MFI+объём+спред),
не из таблицы статусов. Паникёр читает market_data.mfi. scale_timeframe.*
*v1.5: КОНТУР ИСКРЫ v2. Искра пишет trend_direction + found_timeframe
(спуск по лесенке ТФ). Морж наследует масштаб и сторону. РАЗРЫВ 3 закрыт.*
*v1.4: РЕЗИНКА ДЖАСТИН. Морж пишет tension_peak (ангуляция, is_peak резинки).*
*market_data получил блок rubber_band (натяжение цена-Губы в point).*
*Окно анализа 140-150 баров (analysis_window=150) — математика не тронута.*
*tension_peak независим от wave_1_validated (две лампочки Моржа).*
*v1.3: ПОЛНАЯ КАНОНИЗАЦИЯ. Нумерация по MASTER (A01 Искра, A02 Морж).*
*GATE 3 удалён (ЗАКОН ТРИБУНАЛА). history_dna у Искры и A09.*
*Добавлены служебные ключи hooks: trade_setup, atlas_digest, prev_*, open_positions.*
*Заморозить после первого полного прогона на истории.*
