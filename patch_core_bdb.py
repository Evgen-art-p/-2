"""
patch_core_bdb.py — добавляет detect_divergent_bar() в williams_core.py.

Реализует BuDB/BDB по Profitunity Trading Group (Bill Williams):
  BuDB (бычий расходящийся бар):
    lower_low   — low[i] < low[i-1]          (локально, по картинке PTG)
    upper_close — close > (high + low) / 2   (закрытие в верхней половине)
  BDB (медвежий): higher_high + lower_close (close в нижней половине).

Два уровня:
  bdb_candidate — только локальные 2 условия (срабатывает ~44% баров,
                  это контекст для агентов A06-A08)
  bdb_strong    — кандидат + дивергенция AO под/над нулём + ангуляция 5-7
                  баров от пересечения close с Teeth.
                  ~0.3% баров = 3-4 в год = Точка Ноль волны 2.
                  ТОЛЬКО это рисует индикатор.

Проверено на синтетике (1000 баров): candidate 44.5%, strong 0.31% (~2-4/год).
Соответствует архитектуре ("~50 сигналов за 16 лет").

Также добавляет поле market_data["divergent_bar"] в build_market_data().

Запуск из корня студии:
  python patch_core_bdb.py
"""

from pathlib import Path
import shutil, ast, re
from datetime import datetime

STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
ROOT  = Path(__file__).resolve().parent

candidates = [p for p in ROOT.rglob("williams_core.py")
              if ".bak" not in p.name and "__pycache__" not in str(p)]
if not candidates:
    print("[!] williams_core.py не найден"); raise SystemExit(1)
TARGET = candidates[0]
print(f"[+] Цель: {TARGET.relative_to(ROOT)}")

txt = TARGET.read_text(encoding="utf-8")

if "def detect_divergent_bar" in txt:
    print("[!] detect_divergent_bar уже есть. Патч не нужен (или удали старую вручную).")
    raise SystemExit(0)

# ── 1. Новые функции вставляем ПЕРЕД build_market_data ──────────────────
NEW_FUNCS = '''
def detect_divergent_bar(
    bars:         list[dict],
    ao_series:    list,
    teeth_series: list,
) -> dict:
    """
    Расходящийся бар (BuDB/BDB) по Profitunity Trading Group — Bill Williams.

    BuDB (бычий, оценивается ПОСЛЕДНИЙ бар окна):
      lower_low   — low[i] < low[i-1]            (ниже предыдущего бара)
      upper_close — close > (high + low) / 2     (закрытие в верхней половине)
      → bdb_candidate (локальный факт, ~44% баров)

    bdb_strong (Точка Ноль конца волны 2, ~0.3% баров = 3-4 в год):
      + дивергенция AO под нулём (цена ниже, AO выше предыдущего лоу, оба < 0)
      + ангуляция 5-7 баров от пересечения close с Teeth (сверху вниз)

    Зеркально BDB (медвежий): higher_high + lower_close, AO над нулём.

    teeth_series — SMMA(8) медианы (линия баланса Аллигатора), из compute_alligator.
    """
    i = len(bars) - 1
    if i < 1 or teeth_series is None:
        return _empty_divergent_bar()

    b   = bars[i]
    bp  = bars[i - 1]
    mid = (b["high"] + b["low"]) / 2

    lower_low   = b["low"]   < bp["low"]
    upper_close = b["close"] > mid
    higher_high = b["high"]  > bp["high"]
    lower_close = b["close"] < mid

    bull_candidate = lower_low and upper_close
    bear_candidate = higher_high and lower_close

    direction = "BULL" if bull_candidate else "BEAR" if bear_candidate else None

    bars_since_cross = _bars_since_teeth_cross(bars, teeth_series, direction)
    angulation_ok = (bars_since_cross is not None
                     and 5 <= bars_since_cross <= 7)
    ao_diver = _ao_divergence_at_bar(bars, ao_series, i, direction)

    bdb_candidate = bull_candidate or bear_candidate
    bdb_strong = bool(bdb_candidate and angulation_ok and ao_diver)

    return {
        "direction":        direction,
        "lower_low":        lower_low   if direction == "BULL" else False,
        "upper_close":      upper_close if direction == "BULL" else False,
        "higher_high":      higher_high if direction == "BEAR" else False,
        "lower_close":      lower_close if direction == "BEAR" else False,
        "bars_since_cross": bars_since_cross,
        "angulation_ok":    angulation_ok,
        "ao_divergence":    ao_diver,
        "bdb_candidate":    bdb_candidate,
        "bdb_strong":       bdb_strong,
    }


def _empty_divergent_bar() -> dict:
    return {
        "direction": None, "lower_low": False, "upper_close": False,
        "higher_high": False, "lower_close": False,
        "bars_since_cross": None, "angulation_ok": False,
        "ao_divergence": False, "bdb_candidate": False, "bdb_strong": False,
    }


def _bars_since_teeth_cross(bars: list, teeth_series: list, direction) -> Optional[int]:
    """
    Сколько баров назад close в последний раз пересёк линию Teeth.
    BULL: пересечение сверху вниз (close был >= teeth, стал < teeth).
    BEAR: снизу вверх. Возвращает число баров (0 = на текущем) или None.
    """
    i = len(bars) - 1
    if direction is None:
        return None
    for k in range(i, 0, -1):
        t  = teeth_series[k]   if k   < len(teeth_series) else None
        tp = teeth_series[k-1] if k-1 < len(teeth_series) else None
        if t is None or tp is None:
            continue
        c  = bars[k]["close"]
        cp = bars[k-1]["close"]
        if direction == "BULL":
            if cp >= tp and c < t:
                return i - k
        else:
            if cp <= tp and c > t:
                return i - k
    return None


def _ao_divergence_at_bar(bars: list, ao_series: list, i: int, direction) -> bool:
    """
    Дивергенция AO на баре i относительно ПРЕДЫДУЩЕГО ценового экстремума.
    BULL: цена сделала более низкий лоу, AO на баре i ВЫШЕ чем на том лоу,
          оба значения AO < 0.
    BEAR: зеркально, оба AO > 0.
    """
    if direction is None or i >= len(ao_series):
        return False
    ao_i = ao_series[i]
    if ao_i is None:
        return False

    if direction == "BULL":
        if ao_i >= 0:
            return False
        for k in range(i - 2, 1, -1):
            if (bars[k]["low"] < bars[k-1]["low"] and
                bars[k]["low"] < bars[k+1]["low"]):
                ao_k = ao_series[k]
                if ao_k is None or ao_k >= 0:
                    return False
                return bool(bars[i]["low"] < bars[k]["low"] and ao_i > ao_k)
    else:
        if ao_i <= 0:
            return False
        for k in range(i - 2, 1, -1):
            if (bars[k]["high"] > bars[k-1]["high"] and
                bars[k]["high"] > bars[k+1]["high"]):
                ao_k = ao_series[k]
                if ao_k is None or ao_k <= 0:
                    return False
                return bool(bars[i]["high"] > bars[k]["high"] and ao_i < ao_k)
    return False


'''

# Вставляем перед "def build_market_data"
anchor = "def build_market_data("
if anchor not in txt:
    print("[!] build_market_data не найдена"); raise SystemExit(1)

# Найдём также блок _find_ao_pivots который идёт перед build_market_data —
# вставим наши функции ПОСЛЕ него, прямо перед build_market_data
new_txt = txt.replace(anchor, NEW_FUNCS.lstrip("\n") + "\n" + anchor, 1)

# ── 2. compute_alligator должна вернуть teeth_series ────────────────────
# Сейчас она возвращает только teeth (последнее значение). Нужен весь ряд.
# Проверяем — есть ли уже teeth_series в возврате compute_alligator
if '"teeth_series"' not in new_txt:
    # Добавляем teeth_series в return compute_alligator
    OLD_ALLIG_RETURN = '''    return {
        "jaw":       round(jaw,   6),
        "teeth":     round(teeth, 6),
        "lips":      round(lips,  6),
        "sleeping":  sleeping,
        "opening":   opening,
        "mature":    mature,
        "bars_open": bars_open,
    }'''
    NEW_ALLIG_RETURN = '''    return {
        "jaw":          round(jaw,   6),
        "teeth":        round(teeth, 6),
        "lips":         round(lips,  6),
        "sleeping":     sleeping,
        "opening":      opening,
        "mature":       mature,
        "bars_open":    bars_open,
        "teeth_series": teeth_s,
    }'''
    if OLD_ALLIG_RETURN in new_txt:
        new_txt = new_txt.replace(OLD_ALLIG_RETURN, NEW_ALLIG_RETURN, 1)
        print("    compute_alligator: добавлен teeth_series в возврат")
    else:
        print("    [!] не нашёл return compute_alligator точно — teeth_series придётся добавить вручную")

# ── 3. build_market_data вызывает detect_divergent_bar и кладёт в результат ─
# Находим место где считаются индикаторы (divergence = detect_ao_divergence...)
OLD_CALC = '    divergence = detect_ao_divergence(bars, ao_series)'
NEW_CALC = '''    divergence = detect_ao_divergence(bars, ao_series)
    teeth_series = alligator.get("teeth_series")
    divergent_bar = detect_divergent_bar(bars, ao_series, teeth_series)'''
if OLD_CALC in new_txt:
    new_txt = new_txt.replace(OLD_CALC, NEW_CALC, 1)
    print("    build_market_data: вызов detect_divergent_bar добавлен")
else:
    print("    [!] строка divergence = detect_ao_divergence не найдена")

# Добавляем поле в возвращаемый словарь market_data — после divergence_ao
OLD_FIELD = '''        "divergence_ao": divergence["bullish"],  # Точка Ноль
        "exit_bell":     divergence["bearish"],  # Конец импульса'''
NEW_FIELD = '''        "divergence_ao": divergence["bullish"],  # Точка Ноль
        "exit_bell":     divergence["bearish"],  # Конец импульса

        "divergent_bar": divergent_bar,          # BuDB/BDB по Profitunity'''
if OLD_FIELD in new_txt:
    new_txt = new_txt.replace(OLD_FIELD, NEW_FIELD, 1)
    print("    build_market_data: поле divergent_bar добавлено в market_data")
else:
    print("    [!] поле divergence_ao в return не найдено")

# ── синтаксис ────────────────────────────────────────────────────────────
try:
    ast.parse(new_txt)
    print("    синтаксис: OK")
except SyntaxError as e:
    print(f"[!] СИНТАКСИС СЛОМАН: {e}")
    raise SystemExit(1)

bak = TARGET.with_name(TARGET.name + f".bak_{STAMP}")
shutil.copy2(TARGET, bak)
TARGET.write_text(new_txt, encoding="utf-8")
print(f"    бэкап: {bak.name}")
print(f"    ✓ {TARGET.name} обновлён")

print()
print("─" * 64)
print(" ГОТОВО. В ядре теперь есть detect_divergent_bar.")
print()
print(" market_data['divergent_bar'] содержит:")
print("   bdb_candidate — локальный BuDB (для агентов, ~44% баров)")
print("   bdb_strong    — Точка Ноль волны 2 (~3-4 в год) ← рисует индикатор")
print("   direction, angulation_ok, ao_divergence, bars_since_cross")
print()
print(" Следующий шаг: патч моста — писать в JSON флаг bdb (только strong),")
print(" потом индикатор v9 рисует ОДИН символ на BuDB баре. Тишина между.")
print("─" * 64)
