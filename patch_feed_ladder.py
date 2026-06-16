# patch_feed_ladder.py
# ─────────────────────────────────────────────────────────────
# ЧТО ДЕЛАЕТ:
#   Учит насос mt5_feed.py отдавать ЛЮБОЙ актив на ЛЮБОМ таймфрейме
#   по разовому запросу — фундамент под спуск Искры v2 по лесенке ТФ.
#
#   Три добавления, существующий насос (цикл/watchlist/data/council)
#   НЕ ТРОГАЕТ:
#     1. _TF_MAP   += H8 (16392), H12 (16396), M10 (10)  — коды сверены с MT5 API
#     2. _TF_LADDER = лесенка Шефа сверху вниз (его маршрут спуска, не весь MT5)
#     3. step_down(tf)            — следующая ступень вниз (None на дне M5)
#     4. pull_bars(symbol, tf)    — дверь для Искры: разовый запрос через _fetch
#
# ЗАКОН: насос остаётся СЛЕПЫМ. Он не решает "когда спускаться" — он
#        отдаёт ТФ, который попросили. Думает Искра (iskra_live), не насос.
#
# ИДЕМПОТЕНТНОСТЬ: каждый кусок проверяется по маркеру перед вставкой.
#                  Повторный запуск ничего не дублирует.
# БЭКАП: mt5_feed.py.bak_ladder создаётся перед записью.
# ─────────────────────────────────────────────────────────────

import re
import shutil
from pathlib import Path

# ── Найти файл насоса ─────────────────────────────────────────
HERE = Path(__file__).resolve().parent
CANDIDATES = [
    HERE / "studio" / "modules" / "trading" / "mt5_feed.py",
    HERE / "modules" / "trading" / "mt5_feed.py",
    HERE / "mt5_feed.py",
]
target = next((p for p in CANDIDATES if p.exists()), None)
if target is None:
    print("❌ mt5_feed.py не найден. Запусти патч из корня проекта "
          "(там где папка studio/).")
    raise SystemExit(1)

src = target.read_text(encoding="utf-8")
original = src
changes = []

# ════════════════════════════════════════════════════════════
# ПРАВКА 1 — дополнить _TF_MAP кодами H8/H12/M10
# ════════════════════════════════════════════════════════════
# Коды сверены с официальным MT5 API (ENUM_TIMEFRAMES):
#   M10 = 10 · H8 = 16392 · H12 = 16396
# Часовые ТФ кодируются как 16384 + число часов; минутные = числу минут.

needed_codes = {
    '"H8"':  '"H8": 16392',
    '"H12"': '"H12": 16396',
    '"M10"': '"M10": 10,',
}
missing = [k for k in needed_codes if k not in src]

if missing:
    # Якорь: строка с H1/H2/H4 внутри _TF_MAP. Добавим недостающие
    # коды сразу после строки с часовыми ТФ.
    m = re.search(r'("H1":\s*16385,\s*"H2":\s*16386,\s*"H4":\s*16388,)', src)
    if not m:
        print("⚠️  ПРАВКА 1: не нашёл якорь часовых ТФ в _TF_MAP. "
              "Пропускаю — проверь _TF_MAP вручную.")
    else:
        anchor = m.group(1)
        # H8/H12 пристраиваем к часовым; M10 — к минутным.
        add_hours = ' "H8": 16392, "H12": 16396,'
        replacement = anchor + add_hours
        src = src.replace(anchor, replacement, 1)

        # M10 — после M5 (минутные коды = числу минут)
        m2 = re.search(r'("M1":\s*1,\s*"M5":\s*5,\s*"M15":\s*15,\s*"M30":\s*30,)', src)
        if m2:
            anchor2 = m2.group(1)
            replacement2 = anchor2.replace('"M5": 5,', '"M5": 5, "M10": 10,')
            src = src.replace(anchor2, replacement2, 1)
        changes.append(f"_TF_MAP дополнен: {', '.join(missing)}")
else:
    changes.append("_TF_MAP: H8/H12/M10 уже на месте — пропуск")

# ════════════════════════════════════════════════════════════
# ПРАВКА 2 — _TF_LADDER + step_down() + pull_bars()
# ════════════════════════════════════════════════════════════
# Вставляем единым блоком ПЕРЕД секцией "ОБРАБОТКА ОДНОГО ИНСТРУМЕНТА".
# Маркер идемпотентности — имя функции pull_bars.

LADDER_BLOCK = '''
# ════════════════════════════════════════════════════════════
# ЛЕСЕНКА ТАЙМФРЕЙМОВ — спуск Искры v2 (Спринт 45)
# ════════════════════════════════════════════════════════════
#
# ЗАКОН: насос отдаёт ЛЮБОЙ ТФ по запросу — он слеп к активу и ТФ
# (как и весь файл). Он НЕ решает, когда спускаться: это работа Искры
# (iskra_live). Насос — руки, не голова. Здесь только дорога и дверь.

# Маршрут спуска Шефа: НЕ весь справочник MT5, а его человеческий шаг.
# Намеренно пропущены H6/H3/H2/M20/M12 — это выбор крупности, не дыры.
# Дно спуска — M5 ("до 5 минут максимум"): ниже шум съедает волну.
_TF_LADDER = ["MN1", "W1", "D1", "H12", "H8", "H4", "H1", "M30", "M15", "M10", "M5"]


def step_down(tf_name: str):
    """
    Следующая ступень ВНИЗ по лесенке Шефа.
    "H4" -> "H1", "D1" -> "H12". На дне (M5) или вне лесенки -> None.
    Искра зовёт это, когда форма видна, но крупно — нужен масштаб резче.
    """
    tf = (tf_name or "").upper()
    if tf not in _TF_LADDER:
        return None
    i = _TF_LADDER.index(tf)
    if i + 1 >= len(_TF_LADDER):
        return None          # уже на дне — глубже не падаем
    return _TF_LADDER[i + 1]


def pull_bars(symbol: str, timeframe: str, count: int = 2000):
    """
    ДВЕРЬ ДЛЯ ИСКРЫ — разовый запрос баров любого актива на любом ТФ.

    Возвращает (bars, point):
      bars  — список баров от старых к новым (формат williams_core).
      point — минимальный шаг цены из терминала (symbol_info.point).
    При недоступности терминала / неизвестном ТФ -> ([], None).

    В отличие от фонового цикла — НЕ читает watchlist, НЕ пишет файлы,
    НЕ зовёт Совет. Просто: "дай <символ> на <ТФ>". Вот бары.
    Терминал поднимает и закрывает сама _fetch (initialize/shutdown
    внутри неё) — здесь второй раз его не трогаем, чтобы не было
    гонки с фоновым насосом.
    """
    mt5 = _terminal()
    if mt5 is None:
        print("[FEED] ℹ️  MetaTrader5 не установлен — pull_bars простаивает")
        return [], None
    return _fetch(mt5, symbol, timeframe, count)


'''

if "def pull_bars(" in src:
    changes.append("step_down/pull_bars уже есть — пропуск")
else:
    # Якорь — заголовок секции обработки инструмента.
    # Рамка из ═ (U+2550), длина и окружающие пустые строки могут гулять —
    # поэтому ищем по тексту заголовка с гибкими границами.
    anchor_re = re.compile(
        r'\n(#\s*═+\s*\n#\s*ОБРАБОТКА ОДНОГО ИНСТРУМЕНТА\s*\n#\s*═+\s*\n)'
    )
    m = anchor_re.search(src)
    if m:
        # Вставляем перед строкой-рамкой (m.start()+1 — после ведущего \n).
        ins = m.start() + 1
        src = src[:ins] + LADDER_BLOCK.lstrip('\n') + "\n\n" + src[ins:]
        changes.append("Добавлены _TF_LADDER + step_down() + pull_bars()")
    else:
        # Запасной якорь: перед циклом насоса.
        anchor2 = "def _handle_instrument("
        idx = src.find(anchor2)
        if idx == -1:
            print("⚠️  ПРАВКА 2: не нашёл якорь для вставки лесенки. "
                  "Блок НЕ добавлен — проверь файл вручную.")
        else:
            src = src[:idx] + LADDER_BLOCK.lstrip('\n') + "\n\n" + src[idx:]
            changes.append("Добавлены _TF_LADDER + step_down() + pull_bars() "
                           "(запасной якорь)")

# ════════════════════════════════════════════════════════════
# ЗАПИСЬ
# ════════════════════════════════════════════════════════════
if src == original:
    print("ℹ️  Изменений нет — всё уже на месте. Файл не тронут.")
    raise SystemExit(0)

backup = target.with_suffix(".py.bak_ladder")
shutil.copy2(target, backup)
target.write_text(src, encoding="utf-8")

print("✅ Патч применён:", target)
print("📦 Бэкап:", backup)
print("\nЧто сделано:")
for c in changes:
    print("  ·", c)
print("\nПроверка (по желанию):")
print("  python -c \"from studio.modules.trading.mt5_feed import step_down, pull_bars, _TF_LADDER; "
      "print(_TF_LADDER); print('H4 ->', step_down('H4')); print('M5 ->', step_down('M5'))\"")
print("Ожидается: лесенка, 'H4 -> H1', 'M5 -> None'")
