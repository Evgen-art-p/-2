# studio/modules/trading/engine.py
# ─────────────────────────────────────────────────────────────
# ЕДИНЫЙ ДВИЖОК ЦЕХА — одна дверь для бара, один распорядитель Совета
# ENGINE_ONE_DOOR_V1 · 2026-06-23 · Брат + Шеф
#
# ЗАКОН ЭТОГО ФАЙЛА (наказ Шефа: не плодить костыли, не дублировать):
#   · Движок НИЧЕГО не считает сам. Математика — в williams_core.
#     Закрытие сделки — в hooks._settle_positions. Решения — в агентах.
#   · Он только ДИРИЖИРУЕТ: берёт бар, зовёт математику, по факту
#     решает кого будить, зовёт живых. Тонкий слой, не вторая машина.
#   · Он СЛЕП к активу и ТФ — получает их параметром, течёт насквозь,
#     нигде не зашивает (ни одного "XAUUSD"/"H4" в коде).
#   · Он СЛЕП к источнику бара. Окно баров ПОДАЮТ снаружи: терминал
#     (реал) или CSV (тестер) — движку всё равно. В этом всё лекарство
#     от "двух движков": источник — единственная разница миров.
#
# ЛОГИКА ОДНОГО БАРА (картинка Шефа):
#   1. математика считает факты (дёшево, без LLM) — КАЖДЫЙ бар
#   2. есть открытая позиция? → веди её (settle закроет по стопу/колоколу)
#   3. математика нашла точку? → буди полный Совет. нет → Совет спит
#
# ЭТО НЕ заменяет ничего живого. Старые run_market/run_tester пока
# работают как работали. Движок встаёт рядом. Сводить их — позже,
# когда движок докажет одну сделку насквозь.
# ─────────────────────────────────────────────────────────────

from typing import Optional, Callable


# ════════════════════════════════════════════════════════════
# ШАГ МАТЕМАТИКИ — факты на стол (дёшево, без LLM). Каждый бар.
# ════════════════════════════════════════════════════════════

def read_facts(window: list, symbol: str, timeframe: str,
               point: float) -> dict:
    """
    Зовёт ЯДРО (build_market_data) на окне баров. Возвращает факты,
    по которым движок решает развилку. Ничего не считает сам —
    только спрашивает у ядра и достаёт два флага §9:
      has_point — divergence_ao (бычья Точка Ноль, есть разворот вверх)
      exit_bell — медвежья дивергенция (импульс выдохся)

    Слеп к активу: symbol/timeframe/point идут в ядро как есть.
    """
    from studio.modules.trading.williams_core import build_market_data
    md = build_market_data(window, symbol=symbol,
                           timeframe=timeframe, point=point)
    if not md:
        return {}
    # ЗВОНОК БУДИТЬ СОВЕТ — строгая Точка Ноль (bdb_strong), не грубый
    # divergence_ao. Канон Шефа: 3-4 разворота в год. bdb_strong = три
    # условия разом (дивергенция + ангуляция 5-7 баров + B/D/B бар).
    # Грубый divergence_ao даёт ~каждый 6-й бар (шум) — им Совет не будят.
    # Ядро всё посчитало; движок только берёт правильное поле, не считает.
    db = md.get("divergent_bar", {}) or {}
    return {
        "market_data": md,
        "bar_time":    md.get("bar_time"),
        "has_point":   bool(db.get("bdb_strong")),   # строгая Точка Ноль
        "point_side":  db.get("direction"),           # BULL / BEAR — сторона
        "exit_bell":   bool(md.get("exit_bell")),
    }


# ════════════════════════════════════════════════════════════
# ЕСТЬ ЛИ ОТКРЫТАЯ ПОЗИЦИЯ — факт со стола цеха (не движок решает)
# ════════════════════════════════════════════════════════════

def has_open_position() -> bool:
    """Смотрит trading_state: висит ли хоть одна открытая позиция.
    Источник правды — общий стол цеха (hooks), не движок."""
    try:
        from studio.modules.trading.hooks import load_trading_state
        positions = load_trading_state().get("positions", []) or []
        return any(p.get("status") == "OPEN" for p in positions)
    except Exception:
        return False


# ════════════════════════════════════════════════════════════
# ОДИН БАР — сердце движка. Дирижирует, не играет.
# ════════════════════════════════════════════════════════════

def step_bar(window: list, symbol: str, timeframe: str, point: float,
             wake_council: Optional[Callable] = None,
             settle: Optional[Callable] = None,
             on_event: Optional[Callable] = None) -> dict:
    """
    ОДИН ШАГ ВРЕМЕНИ — проживает один бар по логике Шефа.

    window  — окно баров (старые→новые), последний = "сейчас".
              Подаётся СНАРУЖИ: терминал (реал) или CSV (тестер).
    wake_council(market_data) — как разбудить Совет на этом баре.
              Передаётся снаружи, чтобы движок не знал деталей UI/тестера.
              Реал даст одну реализацию, тестер — другую, движок один.
    settle(market_data) — как закрыть позиции (hooks._settle_positions).
              Тоже снаружи: единая физика, движок только зовёт в свой час.
    on_event(dict) — куда слать события (открытие/закрытие/пробуждение)
              для ленты в кабинете. Может быть None (молча).

    Порядок строгий и единственный:
      1. математика считает факты
      2. settle: рынок закрывает что дошло до стопа/колокола (ВЕДЕНИЕ)
      3. есть точка? → буди Совет (может родиться новая позиция)
    """
    def _emit(ev):
        if on_event:
            try: on_event(ev)
            except Exception: pass

    # ── 1. ФАКТЫ МАТЕМАТИКИ (каждый бар, дёшево) ──
    facts = read_facts(window, symbol, timeframe, point)
    if not facts:
        return {"ok": False, "reason": "ядро не собрало факты",
                "bar_time": window[-1].get("date") if window else None}
    md = facts["market_data"]

    # ── 2. ВЕДЕНИЕ: settle закрывает позиции по стопу/колоколу ──
    # Это и есть "река течёт" для живой сделки — на КАЖДОМ баре,
    # а не прыжками. settle — единая физика hooks, движок только зовёт.
    if settle is not None and has_open_position():
        try:
            settle(md)
            _emit({"type": "managed", "bar_time": facts["bar_time"]})
        except Exception as e:
            _emit({"type": "settle_error", "error": str(e)})

    # ── 3. РАЗВИЛКА СОВЕТА: есть точка → буди. нет → спит ──
    woke = False
    if facts["has_point"] and wake_council is not None:
        try:
            wake_council(md)
            woke = True
            _emit({"type": "council_woke", "bar_time": facts["bar_time"]})
        except Exception as e:
            _emit({"type": "council_error", "error": str(e)})

    return {
        "ok": True,
        "bar_time": facts["bar_time"],
        "symbol": symbol, "timeframe": timeframe,
        "has_point": facts["has_point"],
        "point_side": facts.get("point_side"),
        "exit_bell": facts["exit_bell"],
        "council_woke": woke,
    }


# ════════════════════════════════════════════════════════════
# ЦИКЛ ПО ИСТОРИИ — машина гонит бары сама (путь 1: один файл/этаж)
# ════════════════════════════════════════════════════════════

def run_history(bars: list, symbol: str, timeframe: str, point: float,
                wake=None, settle=None, on_event=None,
                warmup: int = 60, should_stop=None) -> dict:
    """
    Гонит ВСЮ историю бар за баром через step_bar. Машина двигает время
    сама — Шеф жмёт один раз. На каждом баре логика одного бара:
    математика -> ведение (settle) -> Совет по звонку.
    """
    total = len(bars)
    woke = 0
    bells = 0
    for i in range(warmup, total):
        if should_stop and should_stop():
            break
        window = bars[max(0, i - 299):i + 1]
        r = step_bar(window, symbol, timeframe, point,
                     wake_council=(lambda md, _w=wake: _w(md)) if wake else None,
                     settle=settle, on_event=on_event)
        if not r.get("ok"):
            continue
        if r.get("council_woke"):
            woke += 1
        if r.get("exit_bell"):
            bells += 1
    return {"bars": total - warmup, "council_woke": woke, "bells": bells}
