"""
patch_contract_v13.py
=====================
Спринт 43 · 2026-06-10

НАХОДКА: в проекте лежал альтернативный CHAIN_CONTRACT со старой
нумерацией (A01 Морж / A02 Искра), живым GATE 3 и history_dna у Моржа.
Это расходится с замороженным MASTER и уже установленными промтами.

РЕШЕНИЕ: полная перезапись канонической версией v1.3.
Точечные правки неизвестного файла — костыль.

КАНОН v1.3:
  · A01 Искра (первая, Root Event Generator), A02 Морж — по MASTER
  · morj_status: три статуса (AWAKE = зрелый), Консерватор требует AWAKE
  · GATE 3 удалён — ЗАКОН ТРИБУНАЛА (все требуют CONFIRMED)
  · history_dna: пишут Искра и A09
  · Служебные ключи hooks: trade_setup, atlas_digest, prev_*, open_positions

ЗАПУСК из корня проекта:
  python patch_contract_v13.py
"""

import shutil
from datetime import datetime
from pathlib import Path

CONTRACT = Path("studio/modules/trading/CHAIN_CONTRACT.md")

ts  = datetime.now().strftime("%Y%m%d_%H%M%S")
bak = CONTRACT.with_suffix(f".md.bak_{ts}")
shutil.copy2(CONTRACT, bak)
print(f"[PATCH] 💾 Резервная копия: {bak}")

CANON = '''# КОНТРАКТ КЛЮЧЕЙ — ТОРГОВЫЙ ЦЕХ v1.3
## studio/modules/trading/CHAIN_CONTRACT.md
## Студия «Шесть Пальцев» · 2026-06-10

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
| A01 Искра | `t1_status`, `divergence`, `zero_cross_up`, `zero_point_price`, `exit_bell`, `history_dna` | `market_data`, `history_dna` |
| A02 Морж | `morj_status`, `alligator_state`, `wave_1_validated` | `market_data`, `t1_status` |
| A03 Паникёр | `panic_phase`, `crowd_sentiment`, `action_for_traders` | `market_data.price`, `t1_status`, `morj_status` |
| A04 Ганс | `fractal_detected`, `fractal_outside_jaw`, `absorption_ratio`, `entry_trigger` | `market_data.fractals`, `market_data.mfi`, `market_data.alligator.jaw`, `t1_status`, `wave_1_validated` |
| A05 Архивариус | `sample_size`, `success_rate`, `top_failure_reason`, `arkhiv_confidence` | `t1_status`, `morj_status`, `panic_phase`, `entry_trigger`, `atlas_digest` |
| A06 Брут | `brut_verdict`, `brut_reason`, `brut_entry`, `brut_stop`, `brut_tp`, `brut_lot` | `t1_status`, `wave_1_validated`, `morj_status`, `panic_phase`, `entry_trigger`, `sample_size`, `success_rate`, `arkhiv_confidence`, `trade_setup` |
| A07 Авантюрист | `avan_verdict`, `avan_reason`, `avan_entry`, `avan_stop`, `avan_tp`, `avan_lot` | `t1_status`, `morj_status`, `panic_phase`, `entry_trigger`, `sample_size`, `success_rate`, `trade_setup` |
| A08 Консерватор | `cons_verdict`, `cons_reason`, `cons_entry`, `cons_stop`, `cons_tp`, `cons_lot` | `t1_status`, `wave_1_validated`, `morj_status`, `panic_phase`, `entry_trigger`, `sample_size`, `success_rate`, `arkhiv_confidence`, `trade_setup` |
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
GATE 1 — Ганс:
  if t1_status != "CONFIRMED" or wave_1_validated != true:
      A04 пропускается, entry_trigger = false (дефолт)

GATE 2 — Хард-стоп:
  if brut_verdict == "REJECTED"
  and avan_verdict == "REJECTED"
  and cons_verdict == "REJECTED":
      on_after_agent A09 → {"action": "stop"}
      запись в Атлас Ошибок (economy/data/atlas_trading.jsonl)
      (trading_state сохраняется ДО stop)
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
  "fractals": {"last_up": null, "last_down": null, "count_up": 0, "count_down": 0}
}
```

### t1_status (A01 Искра)
`NOT_FOUND` | `DETECTED` | `CONFIRMED`
CONFIRMED возможен только после DETECTED.
Аннулирование: цена пробила Точку Ноль вниз → сброс в NOT_FOUND.
Состояние переживает прогон через trading_state.json.

### morj_status (A02 Морж)
`SLEEPING` | `WAKING` | `AWAKE`
AWAKE = bars_open ≥ 8 = зрелый. Отдельного MATURE-статуса НЕТ —
зрелость также видна в `alligator_state.mature`.
Консерватор требует `morj_status=AWAKE`.

### panic_phase (A03 Паникёр)
`NEUTRAL` | `DISBELIEF` | `FOMO` | `LIQUIDATION`
Жёсткие связки: FOMO → HIGH_SKEPTICISM; LIQUIDATION → GREEN_LIGHT_IF_GANS;
NEUTRAL/DISBELIEF → NEUTRAL.

### entry_trigger (A04 Ганс)
true только если fractal_detected=true И fractal_outside_jaw=true.

### arkhiv_confidence (A05 Архивариус)
`LOW` | `MEDIUM` | `HIGH`
HIGH = sample_size ≥ 20 И success_rate ≥ 0.65.
MEDIUM = sample_size ≥ 5 И success_rate ≥ 0.50.
Числа считает код (atlas_digest) — Архивариус копирует.

### trade_setup (hooks.py, для трибунала)
```json
{"direction": "LONG", "entry": 0.0, "stop": 0.0, "tp": null, "lot_fraction": 0.33}
```
entry = фрактал Ганса (Buy Stop над ним), stop = лоу Волны 2.
Трейдеры КОПИРУЮТ цены при APPROVED. v1 — только LONG.

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

*CHAIN_CONTRACT v1.3 · Торговый Цех · 2026-06-10*
*v1.3: ПОЛНАЯ КАНОНИЗАЦИЯ. Нумерация по MASTER (A01 Искра, A02 Морж).*
*GATE 3 удалён (ЗАКОН ТРИБУНАЛА). history_dna у Искры и A09.*
*Добавлены служебные ключи hooks: trade_setup, atlas_digest, prev_*, open_positions.*
*Заморозить после первого полного прогона на истории.*
'''

CONTRACT.write_text(CANON, encoding="utf-8")
print(f"[PATCH] ✅ Перезаписан канонической версией v1.3: {CONTRACT}")
print("[PATCH] 🏁 Готово. Контракт = MASTER = промты. Один источник правды.")
