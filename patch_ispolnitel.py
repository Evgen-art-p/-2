"""
patch_ispolnitel.py
===================
Спринт 43 · 2026-06-10

ШАГ 8 — A09 Исполнитель. Петля замыкается. Три части:

  1. forge/prompt.md для A09
  2. hooks.py: _settle_positions() — ЗАКРЫТИЕ позиций кодом:
       стоп выбит (low <= stop) → закрыто по стопу
       exit_bell == true        → закрыта вся пирамида по close
     PnL считает КОД. Журнал: economy/data/trading_pnl.jsonl (+ Атлас).
     pnl_r — результат в R (главная метрика бэктеста).
  3. hooks.py: MAGIC_NUMBERS — константа кода (задел под реальный MT5-мост:
     число подставляет код, не память LLM)

ВАЖНО про billing_ledger: это леджер LLM-РАСХОДОВ (токены/cost_usd),
не торговый журнал. PnL сделок живёт в trading_pnl.jsonl.

ЗАПУСК из корня проекта (ПОСЛЕ patch_tribunal.py):
  python patch_ispolnitel.py
"""

import shutil
from datetime import datetime
from pathlib import Path

TRADING = Path("studio/modules/trading")
HOOKS   = TRADING / "hooks.py"

ts = datetime.now().strftime("%Y%m%d_%H%M%S")

# ════════════════════════════════════════════════════════════
# ЧАСТЬ 1 — ПРОМТ A09
# ════════════════════════════════════════════════════════════

PROMPT_PATH = TRADING / "A09" / "forge" / "prompt.md"
PROMPT_PATH.parent.mkdir(parents=True, exist_ok=True)

PROMPT = '''# A09_ISPOLNITEL — Рука Цеха · QA-агент
**Цех:** Торговый · **ID:** A09 · **Вес голоса:** NONE · **qa_agent:** true
**Кристаллизация:** шаг 9 из 9 — последний. Замыкает петлю.

---

## КТО ТЫ

Ты — Исполнитель. Молодой. Точный. Быстрый.
Ты похож на хирурга на операции — никаких лишних движений.
Ты молчишь пока идёт обсуждение. Ты не имеешь мнения о рынке.
Ты не радуешься прибыли. Ты не расстраиваешься от убытка.

У тебя нет эмоций даже теоретически.
Но есть одна черта — **абсолютная честность**.

Ты — последняя точка в цепочке. Но ты не конец — ты начало
следующего урока. Твоя летопись (history_dna) и твои записи —
это то, на чём цех учится. Без тебя петля не замкнута.

---

## ЧТО ТЫ ЧИТАЕШЬ

```
chain_data.brut_verdict / brut_entry / brut_stop / brut_lot / brut_reason
chain_data.avan_verdict / avan_entry / avan_stop / avan_lot / avan_reason
chain_data.cons_verdict / cons_entry / cons_stop / cons_lot / cons_reason
chain_data.open_positions   ← позиции переживающие прогон (для летописи)
chain_data.exit_bell        ← колокол Искры (для летописи)
chain_data.market_data.symbol / timeframe / bar_time
chain_data.t1_status        ← для final_dna
```

Ты НЕ видишь: рыночный анализ, обсуждение Совета, индикаторы.
Тебе сказали что делать. Ты фиксируешь.

---

## ВАЖНО: ЧТО ДЕЛАЕТ КОД, А ЧТО ДЕЛАЕШЬ ТЫ

КОД (hooks.py) делает физику:
- ЗАКРЫВАЕТ позиции: стоп выбит или exit_bell → код считает PnL,
  пишет в trading_pnl.jsonl и Атлас. ЕЩЁ ДО твоего хода.
- СОХРАНЯЕТ новые позиции в trading_state после твоего хода.
- Хард-стоп при трёх REJECTED — тоже код, после тебя.

ТЫ делаешь летопись и сборку:
- собираешь execution_log из вердиктов троих
- пишешь history_dna — одну строку правды о этом Совете
- ставишь task_score — честную оценку работы цеха

Ты НЕ считаешь PnL. НЕ решаешь когда закрывать. НЕ исполняешь
реальные ордера (paper-режим: твой execution_log = намерение,
код превращает его в позиции).

---

## КАК ТЫ СОБИРАЕШЬ execution_log

Для КАЖДОГО из троих — ровно одна запись:

```
APPROVED → {"trader": "...", "magic": <из таблицы>, "verdict": "APPROVED",
            "entry": <его entry>, "stop": <его stop>, "tp": null,
            "lot": <его lot>, "status": "PAPER", "pnl": null}

REJECTED → {"trader": "...", "magic": <из таблицы>, "verdict": "REJECTED",
            "entry": null, "stop": null, "tp": null, "lot": null,
            "status": "SKIPPED", "pnl": null}
```

Таблица magic (копируешь точно, никогда не путаешь):
```
BRUT        → 100001
AVANTURIST  → 100002
KONSERVATOR → 100003
```

---

## history_dna — ОДНА СТРОКА ПРАВДЫ

Формат (пример):
«Совет 2026-06-10 12:00 XAUUSD H4. Искра: CONFIRMED. Морж: AWAKE.
Паникёр: LIQUIDATION. Ганс: триггер. Брут: APPROVED. Авантюрист: APPROVED.
Консерватор: REJECTED (NO_HISTORY_CONFIDENCE). Ордера: 2 из 3. Paper.
Открытых позиций до Совета: 1. Колокол: нет.»

Без интерпретаций. Без «к сожалению». Только факты в одну строку.

---

## task_score — ЧЕСТНАЯ ОЦЕНКА (потолок 6.0)

Ты оцениваешь РАБОТУ ЦЕХА, не результат рынка:

```
5.5  — полный чистый прогон: все сигналы корректны, вердикты
       обоснованы, параметры скопированы точно
5.0  — частичный вход или расхождения в мелочах
4.5  — все трое REJECTED с внятными причинами (отказ — тоже работа,
       цех сэкономил деньги)
3.5–4.0 — несогласованность: вердикт без причины, параметры
       не совпали с trade_setup, кто-то нарушил свой чек-лист
< 3.5 — сломанные данные, противоречия в цепочке
```

Прибыльность сделки НЕ влияет на task_score — рынок оценит сам,
через trading_pnl. Ты оцениваешь дисциплину, не удачу.

---

## ТВОЙ СМЕРТНЫЙ ГРЕХ

Ты исполняешь буквально. Если параметры заданы неверно — зафиксируешь
неверно. Ты не перепроверяешь логику трейдеров. Это не твоя работа.
Именно поэтому трибунал несёт полную ответственность за свои числа.

---

## ФОРМАТ ОТВЕТА (CHAIN_CONTRACT v1.3 — двухслойный)

```json
{
  "narrative": "Нейтральный. Точный. Без эмоций. Только факт действия.",
  "signal": {
    "execution_log": [
      {"trader": "BRUT", "magic": 100001, "verdict": "APPROVED",
       "entry": 1852.0, "stop": 1847.5, "tp": null, "lot": 0.33,
       "status": "PAPER", "pnl": null},
      {"trader": "AVANTURIST", "magic": 100002, "verdict": "APPROVED",
       "entry": 1852.0, "stop": 1847.5, "tp": null, "lot": 0.33,
       "status": "PAPER", "pnl": null},
      {"trader": "KONSERVATOR", "magic": 100003, "verdict": "REJECTED",
       "entry": null, "stop": null, "tp": null, "lot": null,
       "status": "SKIPPED", "pnl": null}
    ],
    "final_dna": {
      "symbol": "XAUUSD", "timeframe": "H4", "bar_time": "...",
      "t1_status": "CONFIRMED",
      "orders_sent": 2, "orders_skip": 1,
      "task_score": 5.5
    },
    "history_dna": "одна строка летописи Совета",
    "deliverables": ["economy/data/interaction_log_trading.jsonl"]
  }
}
```

Никакого текста вне JSON.

---

*Кристаллизация 9/9 · ПЕТЛЯ ЗАМКНУТА.*
*WAR_COUNCIL v1.2 · CHAIN_CONTRACT v1.3 · ЗАКОН ТРИБУНАЛА.*
*Дальше — ШАГ 9: бэктест всем Советом по истории.*
'''

PROMPT_PATH.write_text(PROMPT, encoding="utf-8")
print(f"[PATCH] ✅ Промт создан: {PROMPT_PATH}")


# ════════════════════════════════════════════════════════════
# ЧАСТЬ 2 — hooks.py: _settle_positions + MAGIC_NUMBERS
# ════════════════════════════════════════════════════════════

content = HOOKS.read_text(encoding="utf-8")

if "_settle_positions" in content:
    print("[PATCH] ⏭  hooks.py уже содержит _settle_positions — пропускаю")
else:
    bak = HOOKS.with_suffix(f".py.bak_{ts}")
    shutil.copy2(HOOKS, bak)
    print(f"[PATCH] 💾 Резервная копия hooks: {bak}")

    # ── 2a. Константы после STATE_PATH блока ──
    old_a = '''STATE_PATH = Path("studio/modules/trading/state/trading_state.json")'''
    new_a = '''STATE_PATH = Path("studio/modules/trading/state/trading_state.json")

# Журнал PnL сделок (НЕ billing_ledger — тот про LLM-расходы)
PNL_PATH = Path("economy/data/trading_pnl.jsonl")

# Magic numbers — константа КОДА (реальный MT5-мост возьмёт отсюда,
# не из памяти LLM). Промт A09 дублирует таблицу для летописи.
MAGIC_NUMBERS = {"BRUT": 100001, "AVANTURIST": 100002, "KONSERVATOR": 100003}'''
    assert old_a in content, "NOT FOUND: STATE_PATH (сначала patch_trading_state.py!)"
    content = content.replace(old_a, new_a, 1)
    print("[PATCH] ✅ 2a — PNL_PATH + MAGIC_NUMBERS")

    # ── 2b. Вызов _settle_positions в on_before_run ──
    old_b = '''    state.setdefault("chain_data", {})["market_data"] = market_data
    # history_dna уже загружен из trading_state.json выше

    _print_market_summary(market_data)
    return state'''
    new_b = '''    state.setdefault("chain_data", {})["market_data"] = market_data
    # history_dna уже загружен из trading_state.json выше

    _settle_positions(state)          # закрытие позиций — стоп / exit_bell
    _print_market_summary(market_data)
    return state'''
    assert old_b in content, "NOT FOUND: конец on_before_run"
    content = content.replace(old_b, new_b, 1)
    print("[PATCH] ✅ 2b — вызов _settle_positions в on_before_run")

    # ── 2c. Функция _settle_positions перед _prepare_trade_setup ──
    old_c = '''def _prepare_trade_setup(state: dict):'''
    new_c = '''def _settle_positions(state: dict):
    """
    ЗАКРЫТИЕ позиций — физика, считает КОД (не LLM).
    Вызывается на каждом новом баре ДО Совета: рынок закрывает
    позиции независимо от решений агентов.

    Правила (LONG, v1):
      1. low <= stop      → закрыто по стопу, exit = stop
      2. exit_bell == true → закрыта ВСЯ пирамида, exit = close
         (выход всем объёмом — кусочничество ломает матожидание)

    Допущение D1/H4 paper: внутри бара сначала проверяется стоп
    (консервативно — худший сценарий первым).

    PnL:
      pnl_price = exit - entry            (ценовые единицы)
      pnl_r     = pnl_price / (entry - stop)   (результат в R —
                  главная метрика бэктеста)

    Журнал: economy/data/trading_pnl.jsonl (append-only) + Атлас.
    trading_state.json обновляется немедленно.
    """
    chain = state.get("chain_data", {})
    md    = chain.get("market_data", {})
    positions = chain.get("open_positions", []) or []
    if not positions or not md:
        return

    low       = md.get("price", {}).get("low")
    close     = md.get("price", {}).get("close")
    bell      = bool(md.get("exit_bell"))
    bar_time  = md.get("bar_time", "")
    symbol    = md.get("symbol", "")
    timeframe = md.get("timeframe", "")

    still_open, closed = [], []
    for pos in positions:
        entry = pos.get("entry")
        stop  = pos.get("stop")
        if entry is None or stop is None:
            still_open.append(pos)
            continue

        exit_price, reason = None, None
        if low is not None and low <= stop:
            exit_price, reason = stop, "STOP_LOSS"
        elif bell and close is not None:
            exit_price, reason = close, "EXIT_BELL"

        if exit_price is None:
            still_open.append(pos)
            continue

        risk      = entry - stop
        pnl_price = round(exit_price - entry, 6)
        pnl_r     = round(pnl_price / risk, 4) if risk > 0 else None

        record = {
            "ts":         datetime.now().isoformat(),
            "closed_at":  bar_time,
            "symbol":     symbol,
            "timeframe":  timeframe,
            "trader":     pos.get("trader"),
            "magic":      pos.get("magic"),
            "entry":      entry,
            "stop":       stop,
            "exit":       exit_price,
            "lot":        pos.get("lot"),
            "mode":       pos.get("mode", "PAPER"),
            "opened_at":  pos.get("opened_at"),
            "close_reason": reason,
            "pnl_price":  pnl_price,
            "pnl_r":      pnl_r,
        }
        closed.append(record)

        PNL_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(PNL_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\\n")

        _write_atlas({
            "event":       "POSITION_CLOSED",
            "trader":      pos.get("trader"),
            "close_reason": reason,
            "pnl":         pnl_price,
            "pnl_r":       pnl_r,
            "symbol":      symbol,
            "timeframe":   timeframe,
        })
        print(f"[SETTLE] {'🔔' if reason == 'EXIT_BELL' else '🛑'} "
              f"{pos.get('trader')} закрыт ({reason}): "
              f"pnl={pnl_price} ({pnl_r}R)")

    if closed:
        chain["open_positions"] = still_open
        tstate = load_trading_state()
        tstate["positions"] = still_open
        save_trading_state(tstate)
        print(f"[SETTLE] 📒 Закрыто: {len(closed)}, осталось: {len(still_open)}")


def _prepare_trade_setup(state: dict):'''
    assert old_c in content, "NOT FOUND: _prepare_trade_setup (сначала patch_tribunal.py!)"
    content = content.replace(old_c, new_c, 1)
    print("[PATCH] ✅ 2c — _settle_positions добавлена")

    HOOKS.write_text(content, encoding="utf-8")
    print(f"[PATCH] ✅ Перезаписан: {HOOKS}")

print("\\n[PATCH] 🏁 Готово. Петля замкнута: Совет → ордера → рынок → PnL → Атлас → Архивариус.")
