# patch_williams_history.py
# Запускать из корня проекта:
#   python patch_williams_history.py
#
# Патчит studio/modules/trading/williams_core.py:
#   build_market_data() теперь кладёт в ao/ac историю последних 50 значений
#   и список пивотов AO — Искра не может найти дивергенцию без этого.

from pathlib import Path
import shutil
from datetime import datetime

TARGET = Path("studio/modules/trading/williams_core.py")

# Якорь — блок ao в return
OLD = '''\
        "ao": {
            "value":        round(ao_cur,  8) if ao_cur  is not None else None,
            "prev_value":   round(ao_prev, 8) if ao_prev is not None else None,
            "crossed_zero": ao_crossed_zero,
            "zero_dir":     ao_zero_dir,
            "direction":    ao_direction,
        },

        "ac": {
            "value":      round(ac_cur,  8) if ac_cur  is not None else None,
            "prev_value": round(ac_prev, 8) if ac_prev is not None else None,
            "direction":  ac_direction,
        },'''

NEW = '''\
        "ao": {
            "value":        round(ao_cur,  8) if ao_cur  is not None else None,
            "prev_value":   round(ao_prev, 8) if ao_prev is not None else None,
            "crossed_zero": ao_crossed_zero,
            "zero_dir":     ao_zero_dir,
            "direction":    ao_direction,
            # История последних 50 значений — нужна Искре для поиска пивотов/дивергенций
            "history":      [round(v, 8) for v in ao_series[-50:] if v is not None],
            # Пивоты AO (локальные минимумы и максимумы) — последние 10
            "pivots":       _find_ao_pivots(ao_series, bars)[-10:],
        },

        "ac": {
            "value":      round(ac_cur,  8) if ac_cur  is not None else None,
            "prev_value": round(ac_prev, 8) if ac_prev is not None else None,
            "direction":  ac_direction,
            # История последних 50 значений
            "history":    [round(v, 8) for v in ac_series[-50:] if v is not None],
        },'''


# Вставляем вспомогательную функцию перед build_market_data
OLD_FN = '''\
def build_market_data(
    bars:      list[dict],
    symbol:    str   = "UNKNOWN",
    timeframe: str   = "D1",
    point:     float = None,
) -> dict:'''

NEW_FN = '''\
def _find_ao_pivots(ao_series: list, bars: list[dict]) -> list[dict]:
    """
    Находит пивоты AO (локальные минимумы и максимумы).
    Пивот = значение ниже/выше двух соседних с каждой стороны.
    Возвращает список {index, ao_value, price_low, price_high, date, type}.
    Нужен Искре для поиска дивергенций.
    """
    pivots = []
    n = len(ao_series)
    for i in range(2, n - 2):
        v = ao_series[i]
        if v is None:
            continue
        neighbors = [ao_series[i-2], ao_series[i-1],
                     ao_series[i+1], ao_series[i+2]]
        if any(x is None for x in neighbors):
            continue
        b = bars[i] if i < len(bars) else {}
        if v < neighbors[0] and v < neighbors[1] and \
           v < neighbors[2] and v < neighbors[3]:
            pivots.append({
                "type":       "MIN",
                "ao_value":   round(v, 8),
                "price_low":  round(b.get("low",  0), 6),
                "price_high": round(b.get("high", 0), 6),
                "date":       b.get("date", ""),
            })
        elif v > neighbors[0] and v > neighbors[1] and \
             v > neighbors[2] and v > neighbors[3]:
            pivots.append({
                "type":       "MAX",
                "ao_value":   round(v, 8),
                "price_low":  round(b.get("low",  0), 6),
                "price_high": round(b.get("high", 0), 6),
                "date":       b.get("date", ""),
            })
    return pivots


def build_market_data(
    bars:      list[dict],
    symbol:    str   = "UNKNOWN",
    timeframe: str   = "D1",
    point:     float = None,
) -> dict:'''


def main():
    if not TARGET.exists():
        print(f"❌ Файл не найден: {TARGET}")
        print("   Убедись что запускаешь из корня проекта.")
        return

    text = TARGET.read_text(encoding="utf-8")

    missing = []
    if OLD not in text:
        missing.append("блок ao/ac в return")
    if OLD_FN not in text:
        missing.append("def build_market_data")

    if missing:
        print(f"⚠️  Якоря не найдены: {', '.join(missing)}")
        print("   Патч не применён.")
        return

    # Бэкап
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = TARGET.with_suffix(f".py.bak_{ts}")
    shutil.copy2(TARGET, backup)
    print(f"💾 Бэкап: {backup}")

    patched = text.replace(OLD_FN, NEW_FN, 1)
    patched = patched.replace(OLD, NEW, 1)
    TARGET.write_text(patched, encoding="utf-8")

    print(f"✅ Патч применён: {TARGET}")
    print("   + ao.history (последние 50 значений AO)")
    print("   + ao.pivots (пивоты AO с ценой и датой)")
    print("   + ac.history (последние 50 значений AC)")
    print()
    print("Теперь запускай:")
    print("  python run_council.py EURUSDDaily.csv EURUSDDaily D1 --bars 100")


if __name__ == "__main__":
    main()
