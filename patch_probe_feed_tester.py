#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# patch_probe_feed_tester.py
# ─────────────────────────────────────────────────────────────
# ЧИНИТ: probe_engine не включал кран tester → feed_source шёл в
# терминал (mode по умолчанию "real") за D1 → "Нет котировок: D1",
# хотя вся лесенка золота лежит в test_data/. Спуск Искры слеп к
# папке, компас=None навсегда.
#
# ЛЕЧЕНИЕ: на старте probe.main() включаем кран tester для символа
# (set_feed_mode("tester", symbol)) — рядом с чисткой стола. Вся
# лесенка читается из test_data/, терминал не нужен. После прогона
# кран возвращаем как был — не оставляем цех в тестовом режиме.
#
# Идемпотентность: метка PROBE_FEED_TESTER_V1. Повторный запуск —
# no-op. Делает .bak с таймстампом.
# ─────────────────────────────────────────────────────────────
import sys, shutil
from datetime import datetime
from pathlib import Path

TARGET = Path("studio/modules/trading/probe_engine.py")
MARK = "PROBE_FEED_TESTER_V1"


def main():
    if not TARGET.exists():
        print(f"[ОШИБКА] не найден {TARGET} — запускай из корня студии")
        sys.exit(1)

    src = TARGET.read_text(encoding="utf-8")

    if MARK in src:
        print(f"[OK] метка {MARK} уже стоит — патч применён ранее, no-op")
        return

    # ── якорь: чистка стола (есть в probe). Встаём ПЕРЕД ней. ──
    anchor = "    # ── чистим стол этого символа перед заходом (как тестер Шефа) ──"
    if anchor not in src:
        print("[ОШИБКА] не нашёл якорь чистки стола — probe изменён, "
              "покажи Брату текущий probe_engine.py")
        sys.exit(1)

    # ── блок: включить кран tester + запомнить прежний, чтобы вернуть ──
    inject_before = (
        "    # " + MARK + ": включаем кран tester ДО любого спуска.\n"
        "    # Без этого feed_source идёт в терминал (mode=real по умолч.)\n"
        "    # за старшими ТФ и получает 'Нет котировок'. Лесенка золота\n"
        "    # лежит в test_data/ — кран tester её и читает. Терминал спит.\n"
        "    _feed_prev = None\n"
        "    try:\n"
        "        from studio.modules.trading.feed_source import (\n"
        "            get_feed_mode, set_feed_mode)\n"
        "        _feed_prev = get_feed_mode()\n"
        "        set_feed_mode(\"tester\", args.symbol.upper())\n"
        "        print(f\"  кран → TESTER (папка test_data), символ \"\n"
        "              f\"{args.symbol.upper()} · терминал не трогаем\")\n"
        "    except Exception as e:\n"
        "        print(f\"  (кран не переключился: {e})\")\n"
        "\n"
    )

    src = src.replace(anchor, inject_before + anchor, 1)

    # ── вернуть кран как был — после прогона, перед финальным выводом ──
    # Якорь: финальная шапка вывода статистики.
    tail_anchor = '    print("\\n" + "=" * 60)\n    print(f"  прошёл баров:'
    if tail_anchor not in src:
        # запасной якорь — просто перед "if __name__"
        tail_anchor2 = 'if __name__ == "__main__":'
        restore = (
            "    # " + MARK + ": возвращаем кран как был — не оставляем\n"
            "    # цех в тестовом режиме после верстака.\n"
            "    try:\n"
            "        if _feed_prev is not None:\n"
            "            set_feed_mode(_feed_prev.get(\"mode\", \"real\"),\n"
            "                          _feed_prev.get(\"symbol\"))\n"
            "            print(f\"  кран ← {_feed_prev.get('mode','real')} \"\n"
            "                  f\"(возвращён как был)\")\n"
            "    except Exception as e:\n"
            "        print(f\"  (кран не вернулся: {e})\")\n"
            "\n\n"
        )
        src = src.replace(tail_anchor2, restore + tail_anchor2, 1)
    else:
        restore = (
            "    # " + MARK + ": возвращаем кран как был — не оставляем\n"
            "    # цех в тестовом режиме после верстака.\n"
            "    try:\n"
            "        if _feed_prev is not None:\n"
            "            set_feed_mode(_feed_prev.get(\"mode\", \"real\"),\n"
            "                          _feed_prev.get(\"symbol\"))\n"
            "    except Exception:\n"
            "        pass\n"
        )
        src = src.replace(tail_anchor, restore + tail_anchor, 1)

    # ── бэкап + запись ──
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = TARGET.with_suffix(f".py.bak_{ts}")
    shutil.copy2(TARGET, bak)
    TARGET.write_text(src, encoding="utf-8")

    print(f"[OK] патч применён · {MARK}")
    print(f"     бэкап: {bak.name}")
    print()
    print("Теперь перепрогон читает лесенку из папки, без терминала:")
    print("  del economy\\data\\trading_pnl.jsonl")
    print("  python -m studio.modules.trading.probe_engine "
          "studio/modules/trading/test_data/XAUUSD_H4.csv XAUUSD H4")
    print()
    print("ВНИМАНИЕ: спуск Искры теперь оживёт — это ЖИВОЙ Совет (LLM)")
    print("на 24 Точках Ноль. Если хочешь сперва без LLM (чистая")
    print("математика входа) — скажи Брату, дам отдельный путь --math.")


if __name__ == "__main__":
    main()
