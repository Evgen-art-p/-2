#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# patch_tester_settle_gaps.py
# ─────────────────────────────────────────────────────────────
# ПАТЧ: TESTER_SETTLE_GAPS_V1  ·  маркер: шесть·проверено·до·корня
#
# ЧТО ЧИНИТ (зомби-позиции из лога Шефа):
#   Брут вошёл SHORT на баре 510 (2013) со стопом 1.28896. На баре
#   2846 (2022!) он всё ещё «ведёт» эту позицию — она прожила ДЕВЯТЬ
#   ЛЕТ и не закрылась. Почему: _settle_bar зовётся ТОЛЬКО на барах-
#   кандидатах Сита 1 (510 → 1709 → 2846...), а между ними — годы
#   рынка, которые никто не проверяет. Стоп Брута за эти годы был
#   многократно пройден, но settle туда не заглядывал → позиция
#   бессмертна, «ведение» нечестное.
#
#   В ЖИВОМ режиме такого нет (там settle на каждом баре). Это
#   артефакт тестера: прыжки по кандидатам перепрыгивают историю.
#
# КАК ЧИНИТ (только тестер, живой код не трогаем):
#   Заводим курсор пройденного бара (_last_settled). Перед каждым
#   кандидатом прокатываем _settle_bar по ВСЕМ барам от прошлого
#   обработанного до текущего кандидата — рынок закрывает позиции
#   ровно там, где реально дошёл до стопа/колокола, а не на
#   следующем кандидате через годы.
#
#   Дёшево: _settle_bar сам выходит мгновенно, если стол пуст (а он
#   пуст почти всегда — позиции открываются редко). Считает ядро
#   только когда есть что вести. Окно market_data — 60 баров (хватает
#   на индикаторы для цены закрытия; полные 300 не нужны для settle,
#   ему важны low/high/close/exit_bell текущего бара).
#
# ИДЕМПОТЕНТЕН: маркер, повтор — выход. Бэкап рядом.
# ─────────────────────────────────────────────────────────────

import sys
import shutil
from pathlib import Path
from datetime import datetime

MARKER = "TESTER_SETTLE_GAPS_V1"
TESTER = Path("studio/modules/trading/tester_express.py")


def _die(msg):
    print(f"❌ {msg}")
    sys.exit(1)


def main():
    if not TESTER.exists():
        _die(f"не найден {TESTER} — запусти из корня репы (-2/).")
    src = TESTER.read_text(encoding="utf-8")
    if MARKER in src:
        print(f"✅ {MARKER} уже стоит — патч идемпотентен, выхожу.")
        return
    if "TESTER_CLEAN_TABLE_V1" not in src:
        _die("сначала нужен patch_tester_clean_table.py (Шаг 1) — "
             "в файле нет _settle_bar. Накати его первым.")

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = TESTER.with_name(f"{TESTER.stem}.bak_{stamp}{TESTER.suffix}")
    shutil.copy2(TESTER, backup)
    print(f"💾 бэкап: {backup.name}")

    # ═════════════════════════════════════════════════════════
    # ПРАВКА 1 — завести курсор пройденного бара перед циклом Сита 2.
    # Якорь: счётчики found_cnt (объявлены до try).
    # ═════════════════════════════════════════════════════════
    anchor_counters = (
        "    caught = 0\n"
        "    scanned = 0\n"
        "    found_cnt = 0          # TESTER_TO_CABINET_V1: у скольких спуск нашёл точку\n"
    )
    if anchor_counters not in src:
        _die("якорь счётчиков (found_cnt) не найден — файл изменился.")
    src = src.replace(
        anchor_counters,
        "    caught = 0\n"
        "    scanned = 0\n"
        "    found_cnt = 0          # TESTER_TO_CABINET_V1: у скольких спуск нашёл точку\n"
        "    _last_settled = warmup - 1   # " + MARKER + ": докуда докатан settle\n",
        1,
    )

    # ═════════════════════════════════════════════════════════
    # ПРАВКА 2 — заменить одиночный settle на прокат по всем пропущенным.
    # Якорь: текущий блок _settle_bar на кандидате (из Шага 1).
    # ═════════════════════════════════════════════════════════
    anchor_settle = (
        "            # TESTER_CLEAN_TABLE_V1: рынок закрывает позиции по стопу/колоколу\n"
        "            # на текущем баре — как живой on_before_run. Без этого\n"
        "            # позиции бессмертны и кочуют между кандидатами.\n"
        "            _settle_bar(bars_all[max(0, i - 299):i + 1],\n"
        "                        symbol, timeframe, point)\n"
    )
    if anchor_settle not in src:
        _die("якорь одиночного _settle_bar не найден — Шаг 1 изменился?")
    src = src.replace(
        anchor_settle,
        "            # " + MARKER + ": прокатываем settle по ВСЕМ барам от\n"
        "            # прошлого кандидата до текущего — рынок закрывает позиции\n"
        "            # ровно там, где реально дошёл до стопа/колокола, а не\n"
        "            # через годы на следующем кандидате (убивает зомби-позиции).\n"
        "            # _settle_bar мгновенно выходит на пустом столе — дёшево.\n"
        "            for _b in range(_last_settled + 1, i + 1):\n"
        "                _settle_bar(bars_all[max(0, _b - 59):_b + 1],\n"
        "                            symbol, timeframe, point)\n"
        "            _last_settled = i\n",
        1,
    )

    # маркер в шапку
    src = src.replace(
        "# TESTER_CLEAN_TABLE_V1 · чистый стол на старте + settle на каждом баре\n",
        "# TESTER_CLEAN_TABLE_V1 · чистый стол на старте + settle на каждом баре\n"
        "# " + MARKER + " · settle прокатывается по всем барам между кандидатами\n",
        1,
    )

    TESTER.write_text(src, encoding="utf-8")
    print(f"✅ {MARKER} применён к tester_express.py")
    print("   · settle прокатывается по КАЖДОМУ бару между кандидатами")
    print("   · позиции закрываются там, где рынок реально дошёл до стопа")
    print("   · зомби-позиции (девятилетний шорт Брута) больше невозможны")
    print("   · дёшево: пустой стол → settle выходит мгновенно")
    print(f"\n   откат: cp {backup.name} {TESTER.name}")


if __name__ == "__main__":
    main()
