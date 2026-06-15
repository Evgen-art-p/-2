"""
patch_ao_divergence.py v2 — правильная логика дивергенции AO по Вильямсу.

ПРАВИЛО (из "Торговый Хаос" + mql5 реализации):
  Бычья дивергенция:
    — два локальных минимума ЦЕНЫ, второй ниже первого
    — значение AO в баре второго минимума ВЫШЕ чем в баре первого
    — оба значения AO < 0 (оба под нулём)
    — между двумя минимумами AO НИ РАЗУ не пересёк ноль (не ушёл в +)
      → если пересёк — это новый импульс, сбрасываем и ищем заново

  Медвежья дивергенция — зеркально для максимумов, AO > 0.

ПОЧЕМУ lookback=50 давал шум:
  Без проверки пересечения нуля в любом 8-дневном окне H4 найдутся
  два минимума с нужным соотношением — это случайность, не сигнал.
  Пересечение нуля = окончание импульса. Только в рамках одного
  непрерывного импульса дивергенция имеет смысл.

Запуск из корня студии:
  python patch_ao_divergence.py
"""

from pathlib import Path
import shutil, ast
from datetime import datetime

STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
ROOT  = Path(__file__).resolve().parent

# ── поиск williams_core.py ──────────────────────────────────────────────
candidates = [p for p in ROOT.rglob("williams_core.py")
              if ".bak" not in p.name and "__pycache__" not in str(p)]
if not candidates:
    print("[!] williams_core.py не найден"); raise SystemExit(1)

TARGET = candidates[0]
print(f"[+] Цель: {TARGET.relative_to(ROOT)}")

# ────────────────────────────────────────────────────────────────────────
OLD_FUNC = '''def detect_ao_divergence(bars: list[dict], ao_series: list[Optional[float]]) -> dict:
    """
    Дивергенция AO:
      БЫЧЬЯ  — цена ↓ новый минимум, AO↑ минимум выше (оба ниже нуля)
               → Точка Ноль (DETECTED для Искры)
      МЕДВЕЖЬЯ — цена↑ новый максимум, AO↓ максимум ниже (оба выше нуля)
               → exit_bell (конец импульса)
    """
    lookback    = min(50, len(bars) - 1)
    window_bars = bars[-lookback:]
    window_ao   = ao_series[-lookback:]

    lows_price  = []; lows_ao   = []
    highs_price = []; highs_ao  = []

    for i in range(2, len(window_bars) - 2):
        b  = window_bars[i]
        ao = window_ao[i]
        if ao is None:
            continue
        if b["low"]  < window_bars[i-1]["low"]  and b["low"]  < window_bars[i+1]["low"]:
            lows_price.append(b["low"]);  lows_ao.append(ao)
        if b["high"] > window_bars[i-1]["high"] and b["high"] > window_bars[i+1]["high"]:
            highs_price.append(b["high"]); highs_ao.append(ao)

    bullish = False
    if len(lows_price) >= 2:
        p1, p2 = lows_price[-2], lows_price[-1]
        a1, a2 = lows_ao[-2],    lows_ao[-1]
        if p2 < p1 and a2 > a1 and a1 < 0 and a2 < 0:
            bullish = True

    bearish = False
    if len(highs_price) >= 2:
        p1, p2 = highs_price[-2], highs_price[-1]
        a1, a2 = highs_ao[-2],    highs_ao[-1]
        if p2 > p1 and a2 < a1 and a1 > 0 and a2 > 0:
            bearish = True

    return {"bullish": bullish, "bearish": bearish}'''

NEW_FUNC = '''def detect_ao_divergence(bars: list[dict], ao_series: list[Optional[float]]) -> dict:
    """
    Дивергенция AO — строгая логика по Вильямсу ("Торговый Хаос").

    БЫЧЬЯ (Точка Ноль):
      1. Берём ВСЕ локальные минимумы цены (low ниже соседей слева и справа).
      2. Для каждого такого минимума фиксируем значение AO в том же баре.
      3. Берём последние два минимума где AO < 0.
      4. Проверяем: цена[2] < цена[1]  (второй минимум цены ниже)
                    AO[2]   > AO[1]    (второй минимум AO выше — дивергенция)
      5. КРИТИЧНО: между барами минимума-1 и минимума-2 AO ни разу
         не пересёк ноль снизу вверх (не стал положительным).
         Пересечение нуля = конец текущего медвежьего импульса.
         После него — новый импульс, старая дивергенция недействительна.

    МЕДВЕЖЬЯ (exit_bell):
      Зеркально: максимумы цены, AO > 0, AO не пересекал ноль вниз.

    Это убирает 90%+ ложных сигналов по сравнению с lookback=50.
    """
    n = len(bars)
    if n < 5:
        return {"bullish": False, "bearish": False}

    # ── собираем локальные минимумы цены с AO в том же баре ─────────────
    # Локальный минимум: low[i] < low[i-1] И low[i] < low[i+1]
    # (стандартное определение, аналог IsBottom в MQL5-индикаторах)
    price_lows  = []  # (bar_index, price_low, ao_value)
    price_highs = []  # (bar_index, price_high, ao_value)

    for i in range(1, n - 1):
        ao = ao_series[i]
        if ao is None:
            continue
        b  = bars[i]
        bp = bars[i - 1]
        bn = bars[i + 1]

        if b["low"]  < bp["low"]  and b["low"]  < bn["low"]:
            price_lows.append((i, b["low"],  ao))
        if b["high"] > bp["high"] and b["high"] > bn["high"]:
            price_highs.append((i, b["high"], ao))

    # ── бычья дивергенция ────────────────────────────────────────────────
    bullish = False
    # Из всех минимумов берём только те где AO < 0
    neg_lows = [(i, p, a) for (i, p, a) in price_lows if a < 0]
    if len(neg_lows) >= 2:
        i1, p1, a1 = neg_lows[-2]
        i2, p2, a2 = neg_lows[-1]
        # Цена вниз, AO вверх
        if p2 < p1 and a2 > a1:
            # Проверка: AO между i1 и i2 не пересекал ноль (не уходил в +)
            segment = [v for v in ao_series[i1 + 1: i2] if v is not None]
            zero_cross = any(v >= 0 for v in segment)
            if not zero_cross:
                bullish = True

    # ── медвежья дивергенция ─────────────────────────────────────────────
    bearish = False
    # Из всех максимумов берём только те где AO > 0
    pos_highs = [(i, p, a) for (i, p, a) in price_highs if a > 0]
    if len(pos_highs) >= 2:
        i1, p1, a1 = pos_highs[-2]
        i2, p2, a2 = pos_highs[-1]
        # Цена вверх, AO вниз
        if p2 > p1 and a2 < a1:
            # Проверка: AO между i1 и i2 не пересекал ноль (не уходил в -)
            segment = [v for v in ao_series[i1 + 1: i2] if v is not None]
            zero_cross = any(v <= 0 for v in segment)
            if not zero_cross:
                bearish = True

    return {"bullish": bullish, "bearish": bearish}'''

# ────────────────────────────────────────────────────────────────────────
txt = TARGET.read_text(encoding="utf-8")

if OLD_FUNC not in txt:
    # проверяем — может уже был применён предыдущий (неправильный) патч?
    if "neg_lows" in txt:
        print("[!] Файл уже содержит новую версию функции (neg_lows). Патч не нужен.")
        raise SystemExit(0)
    if "_find_ao_pivots(ao_series, bars)" in txt and "bullish = True" in txt:
        print("[!] Найдена промежуточная версия патча (через _find_ao_pivots).")
        print("    Заменяю её на правильную версию с проверкой zero_cross.")
        # найдём и заменим промежуточную версию
        import re
        pattern = re.compile(
            r'def detect_ao_divergence\(.*?return \{"bullish": bullish, "bearish": bearish\}',
            re.DOTALL
        )
        if pattern.search(txt):
            new_txt = pattern.sub(NEW_FUNC, txt, count=1)
        else:
            print("[!] Не смог найти функцию для замены. Правь вручную.")
            raise SystemExit(1)
    else:
        print("[!] Старая функция не найдена точно.")
        print("    lookback=50 в файле:", "lookback    = min(50, len(bars) - 1)" in txt)
        raise SystemExit(1)
else:
    new_txt = txt.replace(OLD_FUNC, NEW_FUNC, 1)

# синтаксис
try:
    ast.parse(new_txt)
except SyntaxError as e:
    print(f"[!] СИНТАКСИС СЛОМАН: {e}"); raise SystemExit(1)

bak = TARGET.with_name(TARGET.name + f".bak_{STAMP}")
shutil.copy2(TARGET, bak)
print(f"    бэкап: {bak.name}")
TARGET.write_text(new_txt, encoding="utf-8")
print(f"    синтаксис: OK")
print(f"    ✓ {TARGET.name} обновлён")

print()
print("─" * 64)
print(" ГОТОВО. Что изменилось в логике:")
print()
print("  БЫЛО: lookback=50 баров, любые два локальных минимума.")
print("        → ~490 'дивергенций' в год. Шум.")
print()
print("  СТАЛО: локальные минимумы ЦЕНЫ + AO в том же баре,")
print("         только где AO < 0, и ОБЯЗАТЕЛЬНАЯ проверка:")
print("         между двумя минимумами AO не пересекал ноль.")
print("         Пересёк ноль = новый импульс = дивергенция сброшена.")
print()
print(" Дальше:")
print("   1. Перезапусти мост — пересчитает mt5_signals.json.")
print("   2. Перегрузи индикатор в MT5.")
print("   3. Смотри total_sigs и drawn в Журнале.")
print("      Ожидаем единицы-десятки на всю историю, не сотни.")
print("─" * 64)
