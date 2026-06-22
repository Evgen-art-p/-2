#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# patch_tester_sterile.py
# ─────────────────────────────────────────────────────────────
# ПАТЧ: TESTER_STERILE_V1  ·  маркер: шесть·проверено·до·корня
#
# ЧТО ЧИНИТ (бэктест калечит живых агентов):
#   Тестер дёргает ЖИВЫХ агентов на истории — и их петля обучения
#   (sync_to_dna: good_work/bad_work) мутирует ДНК по-настоящему.
#   Прогнал года истории → стресс Искры/трейдеров вырос, streak ушёл
#   в минус, и в реальную торговлю агент приходит покалеченным
#   репетицией. Бэктест — это проверка кухни, а не урок жизни.
#
#   После patch_iskra_fair_judgement Искру больше не штрафуют за
#   пустышку, но суд по pnl_r при закрытии (good/bad_work) и обучение
#   трейдеров на сделках в тестере ВСЁ РАВНО дёргают живую ДНК.
#
# КАК ЧИНИТ (только тестер, флаг по умолчанию = смотреть):
#   run_tester получает параметр learn=False. Когда learn=False
#   (умолчание — стерильный прогон), на время прогона глушим
#   grondheim_memory.sync_to_dna заглушкой (как кран глушит MT5):
#   агенты думают, голоса звучат, сделки считаются и пишутся в журнал,
#   но ДНК НЕ мутирует. Снимаем заглушку в finally — всё как было.
#
#   learn=True — учебный прогон: ДНК мутирует, как в реале (для того,
#   кто сознательно хочет тренировать агентов на истории).
#
#   CLI-флаг: --learn включает обучение. Без него — стерильно.
#
# ИДЕМПОТЕНТЕН: маркер, повтор — выход. Бэкап рядом.
# ─────────────────────────────────────────────────────────────

import sys
import shutil
from pathlib import Path
from datetime import datetime

MARKER = "TESTER_STERILE_V1"
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

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = TESTER.with_name(f"{TESTER.stem}.bak_{stamp}{TESTER.suffix}")
    shutil.copy2(TESTER, backup)
    print(f"💾 бэкап: {backup.name}")

    # ── 1. добавить параметр learn в сигнатуру run_tester ──
    anchor_sig = (
        "def run_tester(csv_path: str, symbol: str, timeframe: str,\n"
        "               n_signals: int = 1, point_override=None,\n"
        "               warmup: int = 60, loose: bool = False,\n"
        "               on_progress=None, should_stop=None):  # TESTER_HANDLES_V1\n"
    )
    if anchor_sig not in src:
        _die("якорь сигнатуры run_tester не найден — файл изменился.")
    src = src.replace(
        anchor_sig,
        "def run_tester(csv_path: str, symbol: str, timeframe: str,\n"
        "               n_signals: int = 1, point_override=None,\n"
        "               warmup: int = 60, loose: bool = False,\n"
        "               on_progress=None, should_stop=None,  # TESTER_HANDLES_V1\n"
        "               learn: bool = False):  # " + MARKER + ": умолчание — смотреть\n",
        1,
    )

    # ── 2. поставить заглушку sync_to_dna перед try крана ──
    # Якорь: установка крана (_fetch/_terminal) — ставим стерилизацию
    # рядом, до try, чтобы finally снял и её.
    anchor_crane = (
        "    orig_fetch = mt5_feed._fetch\n"
        "    orig_term  = mt5_feed._terminal\n"
    )
    if anchor_crane not in src:
        _die("якорь установки крана не найден.")
    src = src.replace(
        anchor_crane,
        "    # ── " + MARKER + ": стерильность — бэктест не калечит ДНК ──\n"
        "    # learn=False (умолчание): глушим петлю обучения на время\n"
        "    # прогона. Агенты думают, сделки считаются, но sync_to_dna\n"
        "    # не мутирует живую ДНК. learn=True — учебный прогон.\n"
        "    import studio.grondheim_memory as _gm\n"
        "    _orig_sync = _gm.sync_to_dna\n"
        "    if not learn:\n"
        "        _gm.sync_to_dna = lambda *a, **k: None   # заглушка-микрофон\n"
        "        print('[TESTER] 🧪 стерильный прогон: ДНК агентов НЕ мутирует '\n"
        "              '(--learn чтобы учить)')\n"
        "    else:\n"
        "        print('[TESTER] 🎓 учебный прогон: ДНК агентов мутирует, как в реале')\n"
        "\n"
        "    orig_fetch = mt5_feed._fetch\n"
        "    orig_term  = mt5_feed._terminal\n",
        1,
    )

    # ── 3. снять заглушку в finally ──
    anchor_restore = (
        "    finally:\n"
        "        # ── снимаем весь кран: всё как было (TESTER_TO_CABINET_V1) ──\n"
        "        mt5_feed._fetch    = orig_fetch\n"
    )
    if anchor_restore not in src:
        _die("якорь снятия крана (finally) не найден.")
    src = src.replace(
        anchor_restore,
        "    finally:\n"
        "        # ── снимаем весь кран: всё как было (TESTER_TO_CABINET_V1) ──\n"
        "        _gm.sync_to_dna = _orig_sync   # " + MARKER + ": вернуть обучение\n"
        "        mt5_feed._fetch    = orig_fetch\n",
        1,
    )

    # ── 4. CLI-флаг --learn ──
    anchor_arg = (
        '    ap.add_argument("--loose", action="store_true",\n'
        '                    help="мягкое сито (если строгое bdb_strong дало ноль)")\n'
    )
    if anchor_arg not in src:
        _die("якорь --loose в main не найден.")
    src = src.replace(
        anchor_arg,
        '    ap.add_argument("--loose", action="store_true",\n'
        '                    help="мягкое сито (если строгое bdb_strong дало ноль)")\n'
        '    ap.add_argument("--learn", action="store_true",   # ' + MARKER + '\n'
        '                    help="учебный прогон: ДНК агентов мутирует "\n'
        '                         "(по умолчанию стерильно — смотрим, не калеча)")\n',
        1,
    )

    # ── 5. прокинуть learn в вызов run_tester из main ──
    anchor_call = (
        "    run_tester(args.csv, args.symbol, args.tf,\n"
        "               n_signals=args.signals, point_override=args.point,\n"
        "               warmup=args.warmup, loose=args.loose)\n"
    )
    if anchor_call not in src:
        _die("якорь вызова run_tester в main не найден.")
    src = src.replace(
        anchor_call,
        "    run_tester(args.csv, args.symbol, args.tf,\n"
        "               n_signals=args.signals, point_override=args.point,\n"
        "               warmup=args.warmup, loose=args.loose,\n"
        "               learn=args.learn)   # " + MARKER + "\n",
        1,
    )

    # маркер в шапку
    src = src.replace(
        "_HERE = Path(__file__).resolve().parent\n",
        "_HERE = Path(__file__).resolve().parent\n"
        "# " + MARKER + " · бэктест по умолчанию НЕ калечит ДНК (--learn чтобы учить)\n",
        1,
    )

    TESTER.write_text(src, encoding="utf-8")
    print(f"✅ {MARKER} применён к tester_express.py")
    print("   · по умолчанию прогон СТЕРИЛЬНЫЙ — ДНК агентов не мутирует")
    print("   · флаг --learn включает учебный прогон (ДНК мутирует)")
    print("   · биржа зовёт run_tester(... learn=False) → кабинет тоже стерилен")
    print(f"\n   откат: cp {backup.name} {TESTER.name}")
    print("\n⚠️  если биржа (ui_exchange) должна уметь учить из кабинета —")
    print("    скажи, добавлю галку 'учить' в кнопку РЫНОК отдельным патчем.")


if __name__ == "__main__":
    main()
