# patch_wave_form.py
# ─────────────────────────────────────────────────────────────
# ЧТО ДЕЛАЕТ:
#   Добавляет ЧИТАЛКУ ФОРМЫ AO в ядро — read_ao_wave_form().
#   Это глаз Искры v2: идёт по окну 140-150, находит горб-царя
#   (третью волну), смотрит пересечение нуля, дивер и B/D/B бар.
#
#   ЗАКОН (выкован с Шефом, сессия 2026-06-16):
#     · Искра — СЕНСОР, не судья. Читалка кладёт ФАКТЫ, не вердикты.
#       (никаких "вижу/спускайся/молчи" — это решают трейдеры)
#     · ДИВЕР = КОМПАС (направление зоны разворота, грубо).
#     · ТОЧКА = B/D/B бар Вильямса (цена, точно) — уже в ядре.
#     · ЯКОРЬ = горб-царь окна (самый крупный в 140-150) = третья волна.
#       Без якоря дивер ложный. Окно держит одну структуру → царь один.
#     · Разделение анализа: Искра только дивер+бар+якорь. Аллигатор,
#       фрактал, паника — другие сенсоры. Комплекс сводят ТРЕЙДЕРЫ.
#
#   ДВЕ ПРАВКИ в williams_core.py:
#     1. Новая функция read_ao_wave_form() — перед build_market_data.
#     2. В build_market_data: считаем wave_form и кладём в market_data
#        рядом с rubber_band.
#
# ИДЕМПОТЕНТНОСТЬ: маркеры проверяются перед вставкой.
# БЭКАП: williams_core.py.bak_waveform
# ─────────────────────────────────────────────────────────────

import re
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
CANDIDATES = [
    HERE / "studio" / "modules" / "trading" / "williams_core.py",
    HERE / "modules" / "trading" / "williams_core.py",
    HERE / "williams_core.py",
]
target = next((p for p in CANDIDATES if p.exists()), None)
if target is None:
    print("❌ williams_core.py не найден. Запусти из корня проекта (где studio/).")
    raise SystemExit(1)

src = target.read_text(encoding="utf-8")
original = src
changes = []

# ════════════════════════════════════════════════════════════
# ФУНКЦИЯ ЧИТАЛКИ — вставляется ПЕРЕД build_market_data
# ════════════════════════════════════════════════════════════

WAVE_FUNC = '''
def read_ao_wave_form(
    bars:         list,
    ao_series:    list,
    teeth_series: list,
    window:       int = 150,
) -> dict:
    """
    ЧИТАЛКА ФОРМЫ AO — глаз Искры. Кладёт ФАКТЫ структуры, НЕ вердикты.

    Закон (Шеф, 2026-06-16): Искра — СЕНСОР. Она докладывает что видит,
    решения не принимает. «Вижу/спускайся/молчи» здесь НЕТ — это работа
    трейдеров, которые сводят факты всех сенсоров (Искра+Морж+Ганс+Паникёр)
    в комплекс. Разделение анализа защищает трейдеров от перегруза.

    Идёт по окну 140-150 баров. Факты на стол:
      anchor_ao_max  — горб-царь ВВЕРХ (самый крупный MAX) = третья волна лонга.
      anchor_ao_min  — горб-царь ВНИЗ  (самый крупный MIN) = третья волна шорта.
                       Окно держит ОДНУ структуру → царь один. Якорь дивера:
                       без главного горба дивер ложный (правило Эллиотта:
                       третья не самая короткая).
      zero_cross_after_max — AO пересёк ноль ВНИЗ после верхнего царя (4-я лонга).
      zero_cross_after_min — AO пересёк ноль ВВЕРХ после нижнего царя (4-я шорта).
      divergence_dir — КОМПАС: есть дивер AO и какой (BULL/BEAR/None).
                       Показывает СТОРОНУ зоны разворота. Грубо. Из detect_ao_divergence.
      bdb_dir        — ТОЧКА: есть B/D/B бар Вильямса и какой (BULL/BEAR/None).
                       Конкретный бар цены. Из detect_divergent_bar (bdb_strong).
      bdb_price      — цена этого бара (low для BULL, high для BEAR) или None.
      bar_date       — дата последнего бара окна.

    Спуск по ТФ (лесенка в mt5_feed) даёт ту же читалку на младшем масштабе,
    где структура видна красивее и бар точнее. Но это прогон Искры по ТФ,
    не вердикт читалки: читалка на КАЖДОМ ТФ просто докладывает факты.
    """
    n = len(bars)
    if n < 40 or not ao_series:
        return _empty_wave_form()

    w   = min(window, n)
    off = n - w
    ao_w   = ao_series[off:]
    bars_w = bars[off:]
    teeth_w = teeth_series[off:] if teeth_series else None

    # ── пивоты AO в окне (локальные экстремумы, как _find_ao_pivots) ──
    pv = []  # (local_idx, type, ao_value)
    for i in range(2, w - 2):
        v = ao_w[i]
        if v is None:
            continue
        nb = [ao_w[i-2], ao_w[i-1], ao_w[i+1], ao_w[i+2]]
        if any(x is None for x in nb):
            continue
        if v < nb[0] and v < nb[1] and v < nb[2] and v < nb[3]:
            pv.append((i, "MIN", v))
        elif v > nb[0] and v > nb[1] and v > nb[2] and v > nb[3]:
            pv.append((i, "MAX", v))

    # ── цари окна: самый крупный горб в каждую сторону (факт) ──
    maxes = [(i, v) for (i, t, v) in pv if t == "MAX"]
    mins  = [(i, v) for (i, t, v) in pv if t == "MIN"]
    amax_i, amax_v = (max(maxes, key=lambda x: x[1]) if maxes else (None, None))
    amin_i, amin_v = (min(mins,  key=lambda x: x[1]) if mins  else (None, None))

    # ── пересечение нуля ПОСЛЕ царя (факт: четвёртая пошла) ──
    def _crossed_after(idx, below):
        if idx is None:
            return False
        seg = [v for v in ao_w[idx + 1:] if v is not None]
        return any((v < 0) if below else (v > 0) for v in seg)

    zc_max = _crossed_after(amax_i, below=True)
    zc_min = _crossed_after(amin_i, below=False)

    # ── дивер-КОМПАС (факт, из ядра) ──
    div = detect_ao_divergence(bars_w, ao_w)
    div_dir = "BULL" if div.get("bullish") else "BEAR" if div.get("bearish") else None

    # ── B/D/B бар-ТОЧКА (факт, из ядра) ──
    bdb_dir = None
    bdb_price = None
    if teeth_w is not None:
        db = detect_divergent_bar(bars_w, ao_w, teeth_w)
        if db.get("bdb_strong"):
            bdb_dir = db.get("direction")
            if bdb_dir == "BULL":
                bdb_price = round(bars_w[-1]["low"], 6)
            elif bdb_dir == "BEAR":
                bdb_price = round(bars_w[-1]["high"], 6)

    return {
        "anchor_ao_max":        round(amax_v, 4) if amax_v is not None else None,
        "anchor_ao_min":        round(amin_v, 4) if amin_v is not None else None,
        "zero_cross_after_max": bool(zc_max),
        "zero_cross_after_min": bool(zc_min),
        "divergence_dir":       div_dir,
        "bdb_dir":              bdb_dir,
        "bdb_price":            bdb_price,
        "bar_date":             bars_w[-1]["date"] if bars_w else None,
        "window":               w,
    }


def _empty_wave_form() -> dict:
    return {
        "anchor_ao_max": None, "anchor_ao_min": None,
        "zero_cross_after_max": False, "zero_cross_after_min": False,
        "divergence_dir": None, "bdb_dir": None, "bdb_price": None,
        "bar_date": None, "window": 0,
    }


'''

if "def read_ao_wave_form(" in src:
    changes.append("read_ao_wave_form уже есть — пропуск функции")
else:
    # Якорь — определение build_market_data. Вставляем функцию перед ним.
    m = re.search(r'\ndef build_market_data\(', src)
    if not m:
        print("⚠️  Не нашёл build_market_data — функция НЕ добавлена.")
    else:
        ins = m.start() + 1  # после ведущего \n, перед 'def build_market_data'
        src = src[:ins] + WAVE_FUNC.lstrip('\n') + "\n\n" + src[ins:]
        changes.append("Добавлена read_ao_wave_form() + _empty_wave_form()")

# ════════════════════════════════════════════════════════════
# ПОДКЛЮЧЕНИЕ в build_market_data
# ════════════════════════════════════════════════════════════
# 1. Посчитать wave_form рядом с rubber_band (после строки rubber_band = ...)
# 2. Положить в возвращаемый dict рядом с "rubber_band": rubber_band,

if "wave_form = read_ao_wave_form(" in src:
    changes.append("wave_form уже считается в build_market_data — пропуск")
else:
    # Якорь расчёта: строка, где собран rubber_band (многострочный вызов).
    m = re.search(
        r'(rubber_band = compute_rubber_band\(\s*\n\s*bars, lips_series, teeth_series, _rb_dir, _point\))',
        src)
    if m:
        anchor = m.group(1)
        addition = (anchor +
                    "\n\n    # Читалка формы AO — факты структуры для Искры v2 "
                    "(окно 140-150).\n"
                    "    # Сенсор кладёт факты (дивер-компас, B/D/B-точка, "
                    "горб-царь), не вердикты.\n"
                    "    wave_form = read_ao_wave_form(bars, ao_series, teeth_series)")
        src = src.replace(anchor, addition, 1)
        changes.append("wave_form считается в build_market_data")
    else:
        print("⚠️  Не нашёл якорь rubber_band расчёта — wave_form НЕ подключён к расчёту.")

if '"wave_form":' in src:
    changes.append('"wave_form" уже в выходном market_data — пропуск')
else:
    # Якорь вывода: строка "rubber_band":   rubber_band, в return dict
    m = re.search(r'(\n(\s*)"rubber_band":\s*rubber_band,[^\n]*\n)', src)
    if m:
        whole = m.group(1)
        indent = m.group(2)
        addition = whole + f'{indent}"wave_form":     wave_form,            # факты формы AO (глаз Искры v2)\n'
        src = src.replace(whole, addition, 1)
        changes.append('"wave_form" добавлен в выходной market_data')
    else:
        print("⚠️  Не нашёл строку rubber_band в return — wave_form НЕ выведен.")

# ════════════════════════════════════════════════════════════
# ЗАПИСЬ
# ════════════════════════════════════════════════════════════
if src == original:
    print("ℹ️  Изменений нет — всё уже на месте. Файл не тронут.")
    raise SystemExit(0)

backup = target.with_suffix(".py.bak_waveform")
shutil.copy2(target, backup)
target.write_text(src, encoding="utf-8")

print("✅ Патч применён:", target)
print("📦 Бэкап:", backup)
print("\nЧто сделано:")
for c in changes:
    print("  ·", c)
print("\nПроверка (по желанию):")
print('  python -c "from studio.modules.trading.williams_core import read_ao_wave_form; '
      'print(\'OK, читалка на месте\')"')
