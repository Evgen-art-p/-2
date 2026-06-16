# patch_rubber_band.py
# ─────────────────────────────────────────────────────────────
# ДОБАВЛЯЕТ «РЕЗИНКУ» ДЖАСТИН В ЯДРО — ГЛАЗА МОРЖА (A02)
#
# Что делает (3 врезки в studio/modules/trading/williams_core.py):
#   1. compute_alligator() начинает отдавать "lips_series" (как уже
#      отдаёт teeth_series) — Губы по всей истории, не только последняя.
#   2. Новая функция compute_rubber_band() — натяжение по Джастин:
#        аптренд:   distance = high - lips
#        даунтренд: distance = lips - low
#      в point, плюс история максимума ОТ ПЕРЕСЕЧЕНИЯ TEETH (старт волны).
#      Поле is_peak = текущая дистанция на пике натяжения (момент BuDB).
#   3. build_market_data() кладёт rubber_band в market_data.
#
# ЗАКОН ИЗОЛЯЦИИ держится: ядро только СЧИТАЕТ натяжение. Никакого
# «входить/выходить». Морж это ЧИТАЕТ и СОЗЕРЦАЕТ — как Шеф смотрит
# на график, а не пересчитывает линии в уме.
#
# Идемпотентен: проверяет маркеры перед каждой вставкой.
# Бэкап: williams_core.py.bak_rubber
# ─────────────────────────────────────────────────────────────

import re
import shutil
from pathlib import Path

CORE = Path("studio/modules/trading/williams_core.py")


def main():
    if not CORE.exists():
        print(f"❌ Не найден {CORE} — запусти из корня репо (где папка studio/)")
        return

    txt = CORE.read_text(encoding="utf-8")
    original = txt
    changed = []

    # ── ВРЕЗКА 1: lips_series в выхлоп compute_alligator ──────────
    if '"lips_series"' in txt:
        print("• lips_series уже есть — пропускаю врезку 1")
    else:
        old1 = '        "teeth_series": teeth_s,\n    }'
        new1 = '        "teeth_series": teeth_s,\n        "lips_series":  lips_s,\n    }'
        if old1 in txt:
            txt = txt.replace(old1, new1, 1)
            changed.append("1) lips_series в compute_alligator")
        else:
            print("⚠️  не нашёл точку врезки 1 (teeth_series return) — пропуск")

    # ── ВРЕЗКА 2: функция compute_rubber_band перед build_market_data ──
    if "def compute_rubber_band" in txt:
        print("• compute_rubber_band уже есть — пропускаю врезку 2")
    else:
        func = '''
def compute_rubber_band(
    bars:         list,
    lips_series:  list,
    teeth_series: list,
    direction:    str,
    point:        float,
) -> dict:
    """
    «РЕЗИНКА» Джастин Вильямс — натяжение цены от Зелёной линии (Губы).
    Делает наглядным то, что раньше мерили «на глаз» (ангуляцию).

    Натяжение = пустота между экстремумом цены и Губами:
      UP (аптренд):   distance = high - lips   (как далеко вершина оторвалась)
      DOWN (даунтренд): distance = lips - low   (как далеко дно убежало)
    Всё в point — безразмерно, на любом активе (закон ядра).

    История максимума копится ОТ ПЕРЕСЕЧЕНИЯ close с Teeth (рождение
    волны). По Джастин: натяжение достигает ПИКА на дивергентном баре —
    поэтому is_peak = текущая дистанция это максимум за жизнь движения.

    direction приходит снаружи (из divergent_bar.direction или наклона
    Аллигатора). Если None — резинка не натянута (нет тренда для отрыва).

    ЗАКОН: ядро только МЕРЯЕТ. «Натянута/вяло» — факт физики, не команда.
    Морж это ЧИТАЕТ и созерцает. Решают трейдеры.
    """
    empty = {
        "direction": None, "distance_now": None, "distance_max": None,
        "tension_ratio": None, "is_peak": False, "bars_in_band": None,
    }
    if direction not in ("BULL", "BEAR") or not point:
        return empty
    if not lips_series or not teeth_series:
        return empty

    i = len(bars) - 1
    if i < 1:
        return empty

    def _dist(idx):
        """Натяжение на баре idx в point. None если нет Губ."""
        lp = lips_series[idx] if idx < len(lips_series) else None
        if lp is None:
            return None
        b = bars[idx]
        if direction == "BULL":
            return (b["high"] - lp) / point
        else:
            return (lp - b["low"]) / point

    # Якорь: последнее пересечение close с Teeth в сторону тренда.
    # BULL-импульс рождается, когда close ушёл ВВЕРХ через Teeth.
    anchor = None
    for k in range(i, 0, -1):
        t  = teeth_series[k]   if k   < len(teeth_series) else None
        tp = teeth_series[k-1] if k-1 < len(teeth_series) else None
        if t is None or tp is None:
            continue
        c  = bars[k]["close"]
        cp = bars[k-1]["close"]
        if direction == "BULL":
            if cp <= tp and c > t:   # пробил Teeth вверх — старт волны
                anchor = k
                break
        else:
            if cp >= tp and c < t:   # пробил Teeth вниз
                anchor = k
                break
    if anchor is None:
        anchor = max(1, i - 7)   # нет чистого пересечения — окно по умолчанию

    distance_now = _dist(i)
    if distance_now is None:
        return empty

    # Максимум натяжения от якоря до текущего бара
    distance_max = distance_now
    for k in range(anchor, i + 1):
        d = _dist(k)
        if d is not None and d > distance_max:
            distance_max = d

    eps = 1e-6
    tension_ratio = (distance_now / distance_max) if distance_max > eps else 0.0
    is_peak = distance_now >= distance_max * (1 - 0.02)   # на пике (±2%)
    bars_in_band = i - anchor

    return {
        "direction":     direction,
        "distance_now":  round(distance_now, 1),
        "distance_max":  round(distance_max, 1),
        "tension_ratio": round(tension_ratio, 3),
        "is_peak":       bool(is_peak),
        "bars_in_band":  bars_in_band,
    }


'''
        anchor_def = "def build_market_data("
        if anchor_def in txt:
            txt = txt.replace(anchor_def, func + anchor_def, 1)
            changed.append("2) функция compute_rubber_band")
        else:
            print("⚠️  не нашёл build_market_data для врезки 2 — пропуск")

    # ── ВРЕЗКА 3: вызов + поле rubber_band в build_market_data ────
    if '"rubber_band"' in txt:
        print("• rubber_band уже в market_data — пропускаю врезку 3")
    else:
        # 3a. посчитать после divergent_bar
        old3a = ('    teeth_series = alligator.get("teeth_series")\n'
                 '    divergent_bar = detect_divergent_bar(bars, ao_series, teeth_series)')
        new3a = (old3a + '\n'
                 '    lips_series   = alligator.get("lips_series")\n'
                 '    # Резинка Джастин: направление берём из дивергентного бара,\n'
                 '    # а если он молчит — из наклона Аллигатора (Губы vs Зубы).\n'
                 '    _rb_dir = divergent_bar.get("direction")\n'
                 '    if _rb_dir is None and alligator.get("lips") is not None:\n'
                 '        _rb_dir = "BULL" if alligator["lips"] > alligator["teeth"] else "BEAR"\n'
                 '    rubber_band = compute_rubber_band(\n'
                 '        bars, lips_series, teeth_series, _rb_dir, _point)')
        if old3a in txt:
            txt = txt.replace(old3a, new3a, 1)
            changed.append("3a) вызов compute_rubber_band")
        else:
            print("⚠️  не нашёл точку врезки 3a (divergent_bar=) — пропуск")

        # 3b. положить в выхлоп рядом с divergent_bar
        old3b = '        "divergent_bar": divergent_bar,          # BuDB/BDB по Profitunity'
        new3b = (old3b + '\n'
                 '        "rubber_band":   rubber_band,            # резинка Джастин (глаза Моржа)')
        if old3b in txt:
            txt = txt.replace(old3b, new3b, 1)
            changed.append("3b) поле rubber_band в market_data")
        else:
            print("⚠️  не нашёл точку врезки 3b (divergent_bar field) — пропуск")

    if txt == original:
        print("\n✓ Изменений нет — патч уже применён ранее.")
        return

    # Бэкап + запись
    backup = CORE.with_suffix(".py.bak_rubber")
    shutil.copy2(CORE, backup)
    CORE.write_text(txt, encoding="utf-8")

    print("\n✅ Патч применён. Врезки:")
    for c in changed:
        print(f"   • {c}")
    print(f"\n💾 Бэкап: {backup}")
    print("Проверь синтаксис:  python -c \"import ast; ast.parse(open('studio/modules/trading/williams_core.py',encoding='utf-8').read()); print('OK')\"")


if __name__ == "__main__":
    main()
