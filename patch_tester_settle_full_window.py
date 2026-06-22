#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# patch_tester_settle_full_window.py
# ─────────────────────────────────────────────────────────────
# ПАТЧ: TESTER_SETTLE_FULL_WINDOW_V1  ·  маркер: шесть·проверено·до·корня
#
# ЧТО ЧИНИТ (позиция висит годами — «в 2011 открыли, в 2014 не закрыли»):
#
#   Книга Котина §9: позиция живёт, пока жив импульс. Закрывается по
#   exit_bell (медвежья дивергенция AO для лонга / бычья для шорта)
#   или спячке Аллигатора — это считает build_market_data, исполняет
#   _settle_positions. Стоп Air Bag — только для катастроф, обычно
#   звонок приходит РАНЬШЕ.
#
#   КОРЕНЬ: settle при ведении (патч TESTER_SETTLE_GAPS_V1) кормил
#   build_market_data окном в 60 баров (bars_all[_b-59:_b+1]). А
#   exit_bell — это дивергенция AO, которой нужно БОЛЬШОЕ окно:
#   читалка формы берёт 140-150 баров, дивергенция ищет пивоты по
#   всей доступной истории. На 60 барах дивергенция не собирается →
#   exit_bell молчит → позиция НЕ получает звонок выхода → висит до
#   далёкого Air Bag-стопа → ГОДЫ. Математику скрипт считал, но память
#   была слишком короткой — он слеп к выходу.
#
# КАК ЧИНИТ (только окно, одна правка):
#   settle при ведении кормить ПОЛНЫМ окном 300 баров — как Сито 1 и
#   как живой режим (run_iskra берёт bars_count=300). Тогда дивергенция
#   считается честно, exit_bell звенит вовремя, и позиция закрывается
#   ровно там, где импульс выдохся — через дни/недели, а не годы. §9.
#
#   300 — тот же размер, что везде в цеху (Сито 2 берёт 300, трейдеры
#   берут 300, ядру нужно ≥40 для работы и ~150 для дивер-окна).
#
# ИДЕМПОТЕНТЕН: маркер, повтор — выход. Бэкап рядом.
# Требует: TESTER_SETTLE_GAPS_V1 (прокат settle по барам) уже стоит.
# ─────────────────────────────────────────────────────────────

import sys
import shutil
from pathlib import Path
from datetime import datetime

MARKER = "TESTER_SETTLE_FULL_WINDOW_V1"
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
    if "TESTER_SETTLE_GAPS_V1" not in src:
        _die("нужен patch_tester_settle_gaps.py (прокат settle по барам) — "
             "в файле нет проката. Накати его первым.")

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = TESTER.with_name(f"{TESTER.stem}.bak_{stamp}{TESTER.suffix}")
    shutil.copy2(TESTER, backup)
    print(f"💾 бэкап: {backup.name}")

    # Меняем окно ведения с 60 (_b-59) на полные 300 (_b-299).
    anchor = (
        "            for _b in range(_last_settled + 1, i + 1):\n"
        "                _settle_bar(bars_all[max(0, _b - 59):_b + 1],\n"
        "                            symbol, timeframe, point)\n"
        "            _last_settled = i\n"
    )
    if anchor not in src:
        _die("якорь проката settle (окно 60) не найден — файл изменился. "
             "Re-fetch свежий tester и повтори.")

    replacement = (
        "            for _b in range(_last_settled + 1, i + 1):\n"
        "                # " + MARKER + ": ПОЛНОЕ окно 300 баров (было 60).\n"
        "                # exit_bell (дивергенция AO) требует большого окна —\n"
        "                # на 60 барах он не считался, позиция висела до Air Bag\n"
        "                # годами. На 300 звонок звенит вовремя (§9 Котина).\n"
        "                _settle_bar(bars_all[max(0, _b - 299):_b + 1],\n"
        "                            symbol, timeframe, point)\n"
        "            _last_settled = i\n"
    )
    src = src.replace(anchor, replacement, 1)

    # маркер в шапку
    src = src.replace(
        "# TESTER_SETTLE_GAPS_V1 · settle прокатывается по всем барам между кандидатами\n",
        "# TESTER_SETTLE_GAPS_V1 · settle прокатывается по всем барам между кандидатами\n"
        "# " + MARKER + " · ведение кормит settle полным окном 300 (честный exit_bell)\n",
        1,
    )

    TESTER.write_text(src, encoding="utf-8")
    print(f"✅ {MARKER} применён к tester_express.py")
    print("   · ведение кормит settle полным окном 300 баров (было 60)")
    print("   · exit_bell (дивергенция AO) теперь считается честно")
    print("   · позиция закрывается по звонку выхода, а не висит годами (§9)")
    print(f"\n   откат: cp {backup.name} {TESTER.name}")
    print("\n⚠️  скорость: 300-барное окно на каждом баре тяжелее. На пустом")
    print("    столе settle выходит мгновенно (позиций нет), так что грузит")
    print("    только когда позиция реально открыта и ведётся — это редко.")


if __name__ == "__main__":
    main()
