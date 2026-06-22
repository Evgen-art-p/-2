#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# patch_iskra_fair_judgement.py
# ─────────────────────────────────────────────────────────────
# ПАТЧ: ISKRA_FAIR_JUDGEMENT_V1  ·  маркер: шесть·проверено·до·корня
#
# ЧТО ЧИНИТ (Искра 0.80 стресс, −13 страйков из лога Шефа):
#
#   Искру штрафовали bad_work за переход DETECTED→NOT_FOUND. По задумке
#   это «передумала, рынок не подтвердил». Но:
#     · NOT_FOUND после DETECTED часто = ПУСТЫШКА (точки реально не было
#       на этом баре / спуск не дал компас), а не косяк Искры;
#     · в ТЕСТЕРЕ кандидаты прыгают через ГОДЫ (бар 510→1709), prev_status
#       тащится с прошлого кандидата — DETECTED четырёхлетней давности
#       превращается в bad_work, хотя та точка давно отыграна. Отсюда −13.
#
#   Принцип Шефа: наказывать за ДЕЛО, не за честный труд.
#     · пропустила рабочий → наказать (отдельный заход, сложно);
#     · пустышка (нет точки) → НЕ наказывать (ноль);
#     · накосячила (дала точку, ушла в минус) → наказать.
#   «Рабочий или пустышка» известно только ЗАДНИМ ЧИСЛОМ — по pnl_r
#   закрытой сделки. Значит суд Искры переезжает туда, где судят
#   трейдеров: в _settle_positions при закрытии позиции.
#
# КАК ЧИНИТ (три файла):
#
#   1. iskra_live.py (блок 6b):
#      · УБРАТЬ bad_work за DETECTED→NOT_FOUND (несправедливый штраф
#        за пустышку — корень −13).
#      · ОСТАВИТЬ good_work за DETECTED→CONFIRMED (честная награда:
#        датчик подтвердил свою же находку, это правда, не вранё).
#
#   2. executor_live.py (рука открывающая):
#      · позиция при открытии ЗАПОМИНАЕТ точку Искры (iskra_zero_point,
#        iskra_t1) — чтобы при закрытии знать, чьё это было дело.
#
#   3. hooks.py (_settle_positions, рядом с pnl_r):
#      · при закрытии сделки СУДИМ Искру по деньгам:
#          pnl_r > 0  → good_work (её точка повела к прибыли — права);
#          pnl_r < 0  → bad_work  (её точка увела в минус — накосячила);
#          pnl_r == 0 → ноль.
#      · суд мягкий (intensity 0.3) и идёт ТОЛЬКО если позиция несёт
#        метку Искры — старые позиции без метки не трогают её ДНК.
#        Безопасно: sync_to_dna упал → сделка уже записана, цикл цел.
#
# ИДЕМПОТЕНТЕН: маркер в каждом файле, повтор — выход. Бэкапы рядом.
# ─────────────────────────────────────────────────────────────

import sys
import shutil
from pathlib import Path
from datetime import datetime

MARKER = "ISKRA_FAIR_JUDGEMENT_V1"
ISKRA    = Path("studio/modules/trading/iskra_live.py")
EXECUTOR = Path("studio/modules/trading/executor_live.py")
HOOKS    = Path("studio/modules/trading/hooks.py")


def _die(msg):
    print(f"❌ {msg}")
    sys.exit(1)


def _backup(path):
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    b = path.with_name(f"{path.stem}.bak_{stamp}{path.suffix}")
    shutil.copy2(path, b)
    print(f"💾 бэкап: {b.name}")


# ═════════════════════════════════════════════════════════════
# ФАЙЛ 1 — iskra_live.py: убрать штраф за пустышку
# ═════════════════════════════════════════════════════════════
def patch_iskra():
    if not ISKRA.exists():
        _die(f"не найден {ISKRA} — запусти из корня репы (-2/).")
    src = ISKRA.read_text(encoding="utf-8")
    if MARKER in src:
        print(f"✅ {MARKER} уже в iskra_live.py — пропускаю.")
        return
    _backup(ISKRA)

    anchor = (
        '    try:\n'
        '        from studio.grondheim_memory import sync_to_dna\n'
        '        if prev_status == "DETECTED" and new_status == "CONFIRMED":\n'
        '            sync_to_dna("A01_ISKRA", "good_work", intensity=0.6, dept="trading")\n'
        '        elif prev_status == "DETECTED" and new_status == "NOT_FOUND":\n'
        '            sync_to_dna("A01_ISKRA", "bad_work", intensity=0.5, dept="trading")\n'
        '    except Exception as e:\n'
        '        print(f"[ISKRA] ⚠️  sync_to_dna не сработал ({e})")\n'
    )
    if anchor not in src:
        _die("[iskra] якорь петли обучения 6b не найден — файл изменился.")

    replacement = (
        '    # ' + MARKER + ': суд по ТОЧНОСТИ — только честная награда.\n'
        '    # good_work за DETECTED→CONFIRMED остаётся: датчик подтвердил\n'
        '    # свою же находку, это правда. А bad_work за DETECTED→NOT_FOUND\n'
        '    # УБРАН: NOT_FOUND часто пустышка (точки не было / спуск молчит),\n'
        '    # а в тестере prev_status тащится через годы — штраф несправедлив.\n'
        '    # Наказание за УБЫТОЧНУЮ точку теперь в hooks._settle (по pnl_r) —\n'
        '    # там видно ДЕЛО: повела точка к прибыли или в минус.\n'
        '    try:\n'
        '        from studio.grondheim_memory import sync_to_dna\n'
        '        if prev_status == "DETECTED" and new_status == "CONFIRMED":\n'
        '            sync_to_dna("A01_ISKRA", "good_work", intensity=0.6, dept="trading")\n'
        '        # DETECTED→NOT_FOUND больше НЕ штрафуется здесь (см. _settle).\n'
        '    except Exception as e:\n'
        '        print(f"[ISKRA] ⚠️  sync_to_dna не сработал ({e})")\n'
    )
    src = src.replace(anchor, replacement, 1)

    src = src.replace(
        "from studio.llm import chat\n",
        "from studio.llm import chat\n"
        "# " + MARKER + " · суд Искры по делу (pnl_r), не за пустышку\n",
        1,
    )
    ISKRA.write_text(src, encoding="utf-8")
    print(f"✅ {MARKER} применён к iskra_live.py")


# ═════════════════════════════════════════════════════════════
# ФАЙЛ 2 — executor_live.py: позиция запоминает точку Искры
# ═════════════════════════════════════════════════════════════
def patch_executor():
    if not EXECUTOR.exists():
        _die(f"не найден {EXECUTOR} — запусти из корня репы.")
    src = EXECUTOR.read_text(encoding="utf-8")
    if MARKER in src:
        print(f"✅ {MARKER} уже в executor_live.py — пропускаю.")
        return
    _backup(EXECUTOR)

    # В _open_positions_from_table, при сборке pos, добавляем метку Искры.
    # Якорь: словарь pos с opened_at/pnl (конец сборки позиции).
    anchor = (
        '            "status":    "OPEN",\n'
        '            "mode":      "PAPER",\n'
        '            "opened_at": bar_time,\n'
        '            "pnl":       None,\n'
        '        }\n'
    )
    if anchor not in src:
        _die("[executor] якорь сборки pos не найден — файл изменился.")

    replacement = (
        '            "status":    "OPEN",\n'
        '            "mode":      "PAPER",\n'
        '            "opened_at": bar_time,\n'
        '            "pnl":       None,\n'
        '            # ' + MARKER + ': позиция помнит точку Искры —\n'
        '            # при закрытии _settle рассудит её по pnl_r этой сделки.\n'
        '            "iskra_zero_point": _iskra_zero_for_judgement(),\n'
        '        }\n'
    )
    src = src.replace(anchor, replacement, 1)

    # Добавляем хелпер, читающий точку Искры из шины. Перед
    # def _open_positions_from_table.
    anchor_def = "def _open_positions_from_table(traders: dict, market: dict) -> list:\n"
    if anchor_def not in src:
        _die("[executor] def _open_positions_from_table не найден.")
    helper = (
        "# ── " + MARKER + ": точка Искры для суда при закрытии ──\n"
        "def _iskra_zero_for_judgement():\n"
        "    \"\"\"Точка Ноль Искры из шины — позиция уносит её с собой,\n"
        "    чтобы _settle при закрытии рассудил Искру по делу (pnl_r).\n"
        "    Нет точки → None (старый путь, суда не будет).\"\"\"\n"
        "    try:\n"
        "        from studio.modules.trading.hooks import load_trading_state\n"
        "        isk = load_trading_state().get(\"iskra\", {}) or {}\n"
        "        return isk.get(\"zero_point_price\")\n"
        "    except Exception:\n"
        "        return None\n"
        "\n"
        "\n"
    )
    src = src.replace(anchor_def, helper + anchor_def, 1)

    src = src.replace(
        "from studio.llm import chat\n",
        "from studio.llm import chat\n"
        "# " + MARKER + " · позиция помнит точку Искры для суда при закрытии\n",
        1,
    )
    EXECUTOR.write_text(src, encoding="utf-8")
    print(f"✅ {MARKER} применён к executor_live.py")


# ═════════════════════════════════════════════════════════════
# ФАЙЛ 3 — hooks.py: суд Искры по pnl_r при закрытии
# ═════════════════════════════════════════════════════════════
def patch_hooks():
    if not HOOKS.exists():
        _die(f"не найден {HOOKS} — запусти из корня репы.")
    src = HOOKS.read_text(encoding="utf-8")
    if MARKER in src:
        print(f"✅ {MARKER} уже в hooks.py — пропускаю.")
        return
    _backup(HOOKS)

    # Якорь: вызов _arkhiv_to_city(record) в _settle_positions —
    # это место, где сделка уже закрыта и pnl_r посчитан. Рядом судим Искру.
    anchor = (
        "        # РУКА КЛАДУЩАЯ (ARKHIV_HAND_GIVING): тяжёлая сделка (|pnl_r|>=2R)\n"
        "        # → урок в память города через Оле. Рутина (<2R) — только Атлас.\n"
        "        # Безопасно: Оле упала → сделка уже записана, цикл цел.\n"
        "        _arkhiv_to_city(record)\n"
    )
    if anchor not in src:
        _die("[hooks] якорь _arkhiv_to_city в _settle не найден — файл изменился.")

    replacement = (
        "        # РУКА КЛАДУЩАЯ (ARKHIV_HAND_GIVING): тяжёлая сделка (|pnl_r|>=2R)\n"
        "        # → урок в память города через Оле. Рутина (<2R) — только Атлас.\n"
        "        # Безопасно: Оле упала → сделка уже записана, цикл цел.\n"
        "        _arkhiv_to_city(record)\n"
        "        # " + MARKER + ": СУД ИСКРЫ ПО ДЕЛУ — по pnl_r закрытой сделки.\n"
        "        _judge_iskra_by_result(pos, pnl_r)\n"
    )
    src = src.replace(anchor, replacement, 1)

    # Добавляем функцию суда. Перед def _write_atlas (утилита рядом).
    anchor_def = "def _write_atlas(entry: dict):\n"
    if anchor_def not in src:
        _die("[hooks] def _write_atlas не найден.")
    judge = (
        "def _judge_iskra_by_result(pos: dict, pnl_r):\n"
        "    \"\"\"" + MARKER + ": справедливый суд Искры по ДЕЛУ.\n"
        "    Точка Искры повела сделку в плюс → good_work (была права).\n"
        "    В минус → bad_work (накосячила). Ноль/нет метки → суда нет\n"
        "    (пустышку и старые позиции не наказываем). Мягко (0.3).\n"
        "    Никогда не роняет торговый цикл: беда с ДНК → тихий выход.\"\"\"\n"
        "    if pnl_r is None:\n"
        "        return\n"
        "    # судим ТОЛЬКО позиции с меткой Искры — старые без метки не трогаем\n"
        "    if pos.get(\"iskra_zero_point\") is None:\n"
        "        return\n"
        "    try:\n"
        "        from studio.grondheim_memory import sync_to_dna\n"
        "        if pnl_r > 0:\n"
        "            sync_to_dna(\"A01_ISKRA\", \"good_work\", intensity=0.3, dept=\"trading\")\n"
        "            print(f\"[ISKRA] ⚖️  точка повела в +{pnl_r}R → good_work\")\n"
        "        elif pnl_r < 0:\n"
        "            sync_to_dna(\"A01_ISKRA\", \"bad_work\", intensity=0.3, dept=\"trading\")\n"
        "            print(f\"[ISKRA] ⚖️  точка увела в {pnl_r}R → bad_work\")\n"
        "        # pnl_r == 0 → ноль, суда нет\n"
        "    except Exception as e:\n"
        "        print(f\"[ISKRA] ⚠️  суд по результату не сработал ({e})\")\n"
        "\n"
        "\n"
    )
    src = src.replace(anchor_def, judge + anchor_def, 1)

    src = src.replace(
        "import json\nfrom datetime import datetime\n",
        "import json\nfrom datetime import datetime\n"
        "# " + MARKER + " · суд Искры по pnl_r закрытой сделки\n",
        1,
    )
    HOOKS.write_text(src, encoding="utf-8")
    print(f"✅ {MARKER} применён к hooks.py")


def main():
    patch_iskra()
    patch_executor()
    patch_hooks()
    print("")
    print("ГОТОВО — справедливый суд Искры:")
    print("  · УБРАН штраф за пустышку (DETECTED→NOT_FOUND) — корень −13")
    print("  · оставлена награда за подтверждённую находку (CONFIRMED)")
    print("  · позиция помнит точку Искры")
    print("  · при закрытии: точка в плюс → good_work, в минус → bad_work")
    print("  · суд мягкий (0.3) и только по позициям с меткой Искры")


if __name__ == "__main__":
    main()
