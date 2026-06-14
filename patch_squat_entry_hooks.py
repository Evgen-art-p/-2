# -*- coding: utf-8 -*-
# patch_squat_entry_hooks.py
# ─────────────────────────────────────────────────────────────
# Камень 2: вход по приседающему + подушка безопасности + SHORT-зеркало.
#
# Что делает:
#   1) _prepare_trade_setup переписан под канон Котина/Вильямса:
#      — вход от ПРИСЕДАЮЩЕГО (market_data["squat"]), не от фрактала.
#        LONG:  Buy Stop  над high приседающего + тик
#        SHORT: Sell Stop под low  приседающего − тик
#      — направление по сигналу ИСКРЫ:
#        divergence_ao=True → LONG  (Точка Ноль, рождение нового)
#        exit_bell=True     → SHORT (медвежья дивергенция, выдох роста)
#        ни то, ни другое   → setup пустой, трейдеры скажут REJECTED
#      — стоп = ПОДУШКА БЕЗОПАСНОСТИ Вильямса (гл. 6):
#        экстремум второго бара назад + тик, в сторону против сделки.
#      — ЗАКОН ЯДРА: setup отдаёт ФАКТ (цены), не суждение о
#        разворотности приседающего — это уже работа трейдеров.
#
#   2) _settle_positions: добавлена ЗЕРКАЛЬНАЯ ветка для SHORT.
#      Сейчас стоп проверяется только как low<=stop (лонг).
#      Дописана: для шорта high>=stop, PnL = entry - exit.
#
#   3) Снят временный закон "v1: только LONG" — узаконен симметричный шорт.
#
# Запуск: python patch_squat_entry_hooks.py (из корня репо)
# ─────────────────────────────────────────────────────────────

import re
import sys
import shutil
import py_compile
from datetime import datetime
from pathlib import Path

TARGET = Path("studio/modules/trading/hooks.py")


# ── НОВАЯ функция _prepare_trade_setup целиком ────────────────
NEW_SETUP = '''def _prepare_trade_setup(state: dict):
    """
    Готовит цены входа/стопа для Трибунала. СЧИТАЕТ КОД — трейдеры
    читают setup как ФАКТ рынка. Суждение "входить или нет" — за ними.

    Канон Котина/Вильямса ("Торговый Хаос", гл. 6):
      ВХОД   = ПРОБОЙ приседающего (Squat = +Vol, −MFI).
               LONG:  Buy Stop  над high приседающего + тик
               SHORT: Sell Stop под low  приседающего − тик
      НАПРАВЛЕНИЕ определяется сигналом Искры:
               divergence_ao=True → LONG  (Точка Ноль, "родится новый")
               exit_bell=True     → SHORT (5-я волна выдохлась)
               иначе              → setup пустой (нет ставки)
      СТОП   = подушка безопасности Вильямса — экстремум второго
               бара назад + один тик, в сторону против сделки.
               Это защита от "пьяного рынка", а не точка входа.
      TP     = None — фикс-тейка у Вильямса нет, выход по exit_bell
               всем объёмом (в _settle_positions).

    ЗАКОН ЯДРА: ничего не решаем за трейдеров. Разворотный приседающий
    или мерный, брать или не брать — это их работа, для того их и трое.
    Здесь только цены. Если приседающего нет — entry=None, трейдеры
    вернут REJECTED с причиной NO_SQUAT.
    """
    chain = state.get("chain_data", {})
    md    = chain.get("market_data", {})

    sq_block = md.get("squat", {}) or {}
    squat    = sq_block.get("last_squat")
    bullish  = bool(md.get("divergence_ao"))
    bearish  = bool(md.get("exit_bell"))
    price_lo = md.get("price", {}).get("low")
    price_hi = md.get("price", {}).get("high")

    # ── Направление по Искре ─────────────────────────────────
    if bullish and not bearish:
        direction = "LONG"
    elif bearish and not bullish:
        direction = "SHORT"
    else:
        direction = None  # нет разворотного контекста — нет setup

    # ── Тик (минимальный шаг цены) ───────────────────────────
    # Берём из williams_core POINT_MAP через символ market_data.
    # Импорт здесь, чтобы не плодить циклических зависимостей сверху.
    from .williams_core import get_point
    tick = get_point(md.get("symbol", "UNKNOWN"))

    # ── Вход: пробой приседающего ────────────────────────────
    entry = None
    if squat and direction == "LONG":
        entry = round(squat["high"] + tick, 6)
    elif squat and direction == "SHORT":
        entry = round(squat["low"] - tick, 6)

    # ── Стоп: подушка безопасности (экстремум 2-го бара назад) ─
    # Канон: второй бар назад от рассматриваемого, со старшего ТФ.
    # У нас в market_data только один ТФ — берём 2-й бар назад
    # текущего ТФ как ближайшую к канону аппроксимацию. По-настоящему
    # двухтаймфреймовая подушка ляжет, когда hooks начнёт читать HTF.
    stop = None
    bars2_low  = chain.get("_bar_back2_low")
    bars2_high = chain.get("_bar_back2_high")
    if direction == "LONG" and bars2_low is not None:
        stop = round(bars2_low - tick, 6)
    elif direction == "SHORT" and bars2_high is not None:
        stop = round(bars2_high + tick, 6)
    # Fallback: пока on_before_run не положит _bar_back2_* —
    # используем текущий low/high как грубую защиту, чтобы
    # setup не был совсем пустым на первом прогоне после патча.
    if stop is None:
        if direction == "LONG" and price_lo is not None:
            stop = round(price_lo - tick, 6)
        elif direction == "SHORT" and price_hi is not None:
            stop = round(price_hi + tick, 6)

    chain["trade_setup"] = {
        "direction":    direction,
        "entry":        entry,
        "stop":         stop,
        "tp":           None,
        "lot_fraction": 0.33,
        "source":       "squat" if squat else None,
    }
    if entry is None:
        print(f"[SETUP] ⛔ нет setup: "
              f"squat={'есть' if squat else 'нет'}, "
              f"искра={direction or 'NOT_FOUND'}")
    else:
        print(f"[SETUP] 🎯 {direction}: entry={entry}, stop={stop}, "
              f"tp=None (exit_bell), вход по приседающему")


'''

ANCHOR_OLD_SETUP = '''def _prepare_trade_setup(state: dict):
    """
    Готовит цены входа/стопа для трибунала. СЧИТАЕТ КОД — трейдеры копируют.
    Стоп — системный (за лоу Волны 2), не личный. ЗАКОН ТРИБУНАЛА.

    v1: только LONG (бычий разворот от Точки Ноль).
    Зеркальная SHORT-логика — после бэктеста.

    entry = цена фрактала вверх (Ганс) — Buy Stop ставится над ней
    stop  = последний нижний фрактал (аппроксимация лоу Волны 2)
    tp    = None — тейка нет, выход всей позицией по exit_bell
    """
    chain = state.get("chain_data", {})
    md    = chain.get("market_data", {})
    fr    = md.get("fractals", {})
    up    = fr.get("last_up") or {}
    down  = fr.get("last_down") or {}

    chain["trade_setup"] = {
        "direction":    "LONG",
        "entry":        up.get("price"),
        "stop":         down.get("price"),
        "tp":           None,
        "lot_fraction": 0.33,
    }
    print(f"[SETUP] 🎯 trade_setup: entry={up.get('price')}, "
          f"stop={down.get('price')}, tp=None (exit_bell)")


'''


# ── Подушка безопасности: в on_before_run кладём bar[-3] low/high ──
ANCHOR_PILLOW = '''    _settle_positions(state)          # закрытие позиций — стоп / exit_bell
    _print_market_summary(market_data)
    return state'''

REPLACE_PILLOW = '''    # Подушка безопасности Вильямса: экстремум второго бара назад.
    # Кладём в chain_data, чтобы _prepare_trade_setup взял оттуда.
    cd = state.setdefault("chain_data", {})
    if len(bars) >= 3:
        cd["_bar_back2_low"]  = bars[-3]["low"]
        cd["_bar_back2_high"] = bars[-3]["high"]

    _settle_positions(state)          # закрытие позиций — стоп / exit_bell
    _print_market_summary(market_data)
    return state'''


# ── SHORT-зеркало в _settle_positions ─────────────────────────
ANCHOR_SETTLE = '''    low       = md.get("price", {}).get("low")
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
        pnl_r     = round(pnl_price / risk, 4) if risk > 0 else None'''

REPLACE_SETTLE = '''    low       = md.get("price", {}).get("low")
    high      = md.get("price", {}).get("high")
    close     = md.get("price", {}).get("close")
    bell      = bool(md.get("exit_bell"))
    bar_time  = md.get("bar_time", "")
    symbol    = md.get("symbol", "")
    timeframe = md.get("timeframe", "")

    still_open, closed = [], []
    for pos in positions:
        entry = pos.get("entry")
        stop  = pos.get("stop")
        direction = pos.get("direction", "LONG")  # legacy позиции = LONG
        if entry is None or stop is None:
            still_open.append(pos)
            continue

        exit_price, reason = None, None
        # Стоп — зеркально по направлению
        if direction == "LONG" and low is not None and low <= stop:
            exit_price, reason = stop, "STOP_LOSS"
        elif direction == "SHORT" and high is not None and high >= stop:
            exit_price, reason = stop, "STOP_LOSS"
        elif bell and close is not None:
            exit_price, reason = close, "EXIT_BELL"

        if exit_price is None:
            still_open.append(pos)
            continue

        # PnL зеркально: для шорта прибыль когда цена УПАЛА (entry > exit)
        if direction == "LONG":
            risk      = entry - stop
            pnl_price = round(exit_price - entry, 6)
        else:  # SHORT
            risk      = stop - entry
            pnl_price = round(entry - exit_price, 6)
        pnl_r     = round(pnl_price / risk, 4) if risk > 0 else None'''


def main():
    if not TARGET.exists():
        print(f"[PATCH] ❌ Не найден: {TARGET}")
        print("        Запускай из корня репозитория.")
        sys.exit(1)

    src = TARGET.read_text(encoding="utf-8")
    original = src

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = TARGET.with_suffix(f".py.bak_{ts}")
    shutil.copy2(TARGET, bak)
    print(f"[PATCH] 💾 Бэкап: {bak.name}")

    # ── Идемпотентность ──────────────────────────────────────
    if "вход по приседающему" in src:
        print("[PATCH] ⚠️  Уже применён (нашли маркер 'вход по приседающему'). Выход.")
        sys.exit(0)

    # ── 1. Замена _prepare_trade_setup целиком ───────────────
    if ANCHOR_OLD_SETUP not in src:
        print("[PATCH] ❌ Якорь старой _prepare_trade_setup не найден.")
        sys.exit(1)
    src, n1 = re.subn(re.escape(ANCHOR_OLD_SETUP), NEW_SETUP, src, count=1)
    print(f"[PATCH] ✏️  _prepare_trade_setup переписан: {n1}")

    # ── 2. Подушка безопасности: на старте кладём bars[-3] ───
    if ANCHOR_PILLOW not in src:
        print("[PATCH] ❌ Якорь конца on_before_run не найден.")
        sys.exit(1)
    src, n2 = re.subn(re.escape(ANCHOR_PILLOW), REPLACE_PILLOW, src, count=1)
    print(f"[PATCH] ✏️  Подушка безопасности (bar_back2) добавлена: {n2}")

    # ── 3. SHORT-зеркало в _settle_positions ─────────────────
    if ANCHOR_SETTLE not in src:
        print("[PATCH] ❌ Якорь _settle_positions не найден.")
        sys.exit(1)
    src, n3 = re.subn(re.escape(ANCHOR_SETTLE), REPLACE_SETTLE, src, count=1)
    print(f"[PATCH] ✏️  SHORT-зеркало в _settle_positions добавлено: {n3}")

    if not (n1 == n2 == n3 == 1):
        print("[PATCH] ❌ Не все замены прошли ровно один раз — откат.")
        sys.exit(1)

    TARGET.write_text(src, encoding="utf-8")
    try:
        py_compile.compile(str(TARGET), doraise=True)
        print("[PATCH] ✅ Компиляция прошла.")
    except py_compile.PyCompileError as e:
        print(f"[PATCH] ❌ Ошибка компиляции — откат:\n{e}")
        TARGET.write_text(original, encoding="utf-8")
        sys.exit(1)

    print("[PATCH] ✅ Готово. hooks.py: вход по приседающему, шорт узаконен,")
    print("        подушка безопасности Вильямса на месте.")
    print("        Дальше: прогон раннера на золоте — посмотреть живой setup.")


if __name__ == "__main__":
    main()
