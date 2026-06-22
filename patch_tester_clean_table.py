#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# patch_tester_clean_table.py
# ─────────────────────────────────────────────────────────────
# ПАТЧ: TESTER_CLEAN_TABLE_V1  ·  маркер: шесть·проверено·до·корня
#
# ЧТО ЧИНИТ (грязь из лога Шефа, EURUSD-прогон):
#   · «держу шорт с 1201.99», «шорт 1217.73 из другой жизни» —
#     позиции от прошлого прогона (золото) протекли в прогон EURUSD;
#   · «позиций=3» на КАЖДОМ баре — позиции бессмертны, не закрываются;
#   · стопы-уродцы (MOVE_STOP to 1.1025 при шорте золота) — следствие.
#
#   КОРЕНЬ: trading_state.json — ОДИН файл на весь цех, плоский список
#   positions без надёжной привязки к инструменту. А в тестерном пути
#   _settle_positions (закрытие по стопу/колоколу) вообще НЕ зовётся —
#   он живёт в hooks.on_before_run, а тестер дёргает агентов напрямую.
#   Итог: позиции одного актива кочуют в прогон другого и не умирают.
#
# КАК ЧИНИТ (ШАГ 1 — только тестер, живой код не трогаем):
#   1. На старте run_tester ЧИСТИМ стол прогоняемого символа:
#      сносим из trading_state["positions"] все позиции этого symbol
#      (а если у старых позиций нет поля symbol — сносим вообще все,
#      потому что они из прошлой эпохи и доверять им нельзя). Сбрасываем
#      вердикты трейдеров и состояние Искры. Прогон начинается с чистого
#      листа — как и должно быть на бэктесте.
#   2. На КАЖДОМ кандидате перед Советом зовём hooks._settle_positions
#      с market_data текущего бара — рынок закрывает позиции по стопу/
#      колоколу САМ, как в живом on_before_run. Позиции перестают быть
#      бессмертными, pnl_r пишется в trading_pnl.jsonl (это и есть
#      «прогнать живую сделку насквозь» из мастера).
#   3. Открываемые в тестере позиции метим symbol — чтобы Шаг 2 (фильтр
#      по символу во всех движках) лёг на готовое поле.
#
#   ШАГ 2 (отдельный заход): провести symbol в _my_open_position всех
#   движков + _settle + Исполнителя, чтобы мульти-актив не пересекался
#   и в ЖИВОМ режиме. Здесь НЕ делаем — только тестер.
#
# ИДЕМПОТЕНТЕН: маркер, повтор — выход. Бэкап рядом.
# ─────────────────────────────────────────────────────────────

import sys
import shutil
from pathlib import Path
from datetime import datetime

MARKER = "TESTER_CLEAN_TABLE_V1"
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

    # ═════════════════════════════════════════════════════════
    # ПРАВКА 1 — функции-помощники (чистка стола + settle бара).
    # Вставляем перед def run_tester(.
    # ═════════════════════════════════════════════════════════
    anchor_def = "def run_tester(csv_path: str, symbol: str, timeframe: str,\n"
    if anchor_def not in src:
        _die("якорь def run_tester не найден — файл изменился.")

    helpers = (
        "# ── " + MARKER + ": чистый стол + закрытие позиций в тестере ──\n"
        "def _clean_table_for_symbol(symbol):\n"
        "    \"\"\"Сносит стол прогоняемого символа ПЕРЕД заходом. Бэктест\n"
        "    начинается с чистого листа: ни чужих позиций, ни старых\n"
        "    вердиктов. Позиции без поля symbol (старая эпоха) — сносим\n"
        "    тоже: доверять им нельзя, они из другого прогона/актива.\"\"\"\n"
        "    from studio.modules.trading.hooks import (\n"
        "        load_trading_state, save_trading_state)\n"
        "    t = load_trading_state()\n"
        "    sym = (symbol or '').upper()\n"
        "    before = t.get('positions', []) or []\n"
        "    # держим только ЧУЖИЕ символы с явной меткой; своё и безымянное сносим\n"
        "    kept = [p for p in before\n"
        "            if p.get('symbol') and p.get('symbol', '').upper() != sym]\n"
        "    dropped = len(before) - len(kept)\n"
        "    t['positions'] = kept\n"
        "    # сбрасываем вердикты трейдеров и состояние Искры на чистый лист\n"
        "    for k in ('brut', 'avan', 'cons'):\n"
        "        t[k] = {}\n"
        "    t['iskra'] = {'t1_status': 'NOT_FOUND',\n"
        "                  'zero_point_price': None, 'history_dna': ''}\n"
        "    save_trading_state(t)\n"
        "    if dropped:\n"
        "        print(f'[TESTER·CLEAN] снёс {dropped} позиций прошлой эпохи '\n"
        "              f'(символ {sym} и безымянные) — стол чист')\n"
        "    return dropped\n"
        "\n"
        "\n"
        "def _settle_bar(window, symbol, timeframe, point):\n"
        "    \"\"\"Зовёт hooks._settle_positions на текущем баре — рынок\n"
        "    закрывает позиции по стопу/колоколу САМ, как в живом\n"
        "    on_before_run. В тестерном пути этого вызова не было —\n"
        "    позиции жили вечно. Собираем мини-state с market_data бара.\"\"\"\n"
        "    from studio.modules.trading.williams_core import build_market_data\n"
        "    from studio.modules.trading.hooks import (\n"
        "        _settle_positions, load_trading_state)\n"
        "    md = build_market_data(window, symbol=symbol,\n"
        "                           timeframe=timeframe, point=point)\n"
        "    if not md:\n"
        "        return\n"
        "    positions = load_trading_state().get('positions', []) or []\n"
        "    if not positions:\n"
        "        return\n"
        "    st = {'chain_data': {'market_data': md,\n"
        "                         'open_positions': positions}}\n"
        "    try:\n"
        "        _settle_positions(st)   # закрывает по стопу/колоколу, пишет pnl_r\n"
        "    except Exception as _e:\n"
        "        print(f'[TESTER·SETTLE] пропуск ({_e})')\n"
        "\n"
        "\n"
    )
    src = src.replace(anchor_def, helpers + anchor_def, 1)

    # ═════════════════════════════════════════════════════════
    # ПРАВКА 2 — чистим стол на старте, перед Ситом 1.
    # Якорь: печать шапки тестера (точно один раз).
    # ═════════════════════════════════════════════════════════
    anchor_header = (
        '    print("═" * 64)\n'
        '    print(f"  ЭКСПРЕСС-ТЕСТЕР · {symbol} {timeframe} · {total} баров")\n'
    )
    if anchor_header not in src:
        _die("якорь шапки тестера не найден.")
    src = src.replace(
        anchor_header,
        '    # ' + MARKER + ': чистим стол прогоняемого символа ПЕРЕД заходом\n'
        '    _clean_table_for_symbol(symbol)\n'
        '    print("═" * 64)\n'
        '    print(f"  ЭКСПРЕСС-ТЕСТЕР · {symbol} {timeframe} · {total} баров")\n',
        1,
    )

    # ═════════════════════════════════════════════════════════
    # ПРАВКА 3 — settle на каждом кандидате ПЕРЕД пробуждением Искры.
    # Якорь: установка курсора + run_iskra в Сите 2.
    # ═════════════════════════════════════════════════════════
    anchor_cursor = (
        '            state["cursor"] = i\n'
        '            scanned += 1\n'
        '            _emit(f"кандидат {idx+1}/{len(candidates)} · бар {i}")\n'
        '\n'
        '            r_iskra = run_iskra(symbol=symbol, timeframe=timeframe)\n'
    )
    if anchor_cursor not in src:
        _die("якорь курсора/run_iskra в Сите 2 не найден.")
    src = src.replace(
        anchor_cursor,
        '            state["cursor"] = i\n'
        '            scanned += 1\n'
        '            _emit(f"кандидат {idx+1}/{len(candidates)} · бар {i}")\n'
        '\n'
        '            # ' + MARKER + ': рынок закрывает позиции по стопу/колоколу\n'
        '            # на текущем баре — как живой on_before_run. Без этого\n'
        '            # позиции бессмертны и кочуют между кандидатами.\n'
        '            _settle_bar(bars_all[max(0, i - 299):i + 1],\n'
        '                        symbol, timeframe, point)\n'
        '\n'
        '            r_iskra = run_iskra(symbol=symbol, timeframe=timeframe)\n',
        1,
    )

    # ═════════════════════════════════════════════════════════
    # ПРАВКА 4 — метим открытые в тестере позиции символом.
    # После прогона Исполнителя дописываем symbol в свежие позиции
    # (у которых его ещё нет), чтобы Шаг 2 лёг на готовое поле и
    # чистка следующего прогона работала точно.
    # Якорь: блок Исполнителя в тестере (rex.get("ok")).
    # ═════════════════════════════════════════════════════════
    anchor_exec = (
        "            from studio.modules.trading.executor_live import run_executor\n"
        "            rex = run_executor(symbol=symbol, timeframe=timeframe)\n"
    )
    if anchor_exec not in src:
        _die("якорь run_executor в тестере не найден.")
    src = src.replace(
        anchor_exec,
        "            from studio.modules.trading.executor_live import run_executor\n"
        "            rex = run_executor(symbol=symbol, timeframe=timeframe)\n"
        "            # " + MARKER + ": метим свежие позиции символом (для Шага 2)\n"
        "            try:\n"
        "                from studio.modules.trading.hooks import (\n"
        "                    load_trading_state, save_trading_state)\n"
        "                _ts = load_trading_state()\n"
        "                _dirty = False\n"
        "                for _p in _ts.get('positions', []) or []:\n"
        "                    if not _p.get('symbol'):\n"
        "                        _p['symbol'] = symbol\n"
        "                        _dirty = True\n"
        "                if _dirty:\n"
        "                    save_trading_state(_ts)\n"
        "            except Exception:\n"
        "                pass\n",
        1,
    )

    # маркер в шапку
    src = src.replace(
        "_HERE = Path(__file__).resolve().parent\n",
        "_HERE = Path(__file__).resolve().parent\n"
        "# " + MARKER + " · чистый стол на старте + settle на каждом баре\n",
        1,
    )

    TESTER.write_text(src, encoding="utf-8")
    print(f"✅ {MARKER} применён к tester_express.py")
    print("   · стол чистится для прогоняемого символа на старте")
    print("   · _settle зовётся на каждом баре — позиции закрываются")
    print("   · свежие позиции метятся symbol (задел под Шаг 2)")
    print("   · живой код не тронут")
    print(f"\n   откат: cp {backup.name} {TESTER.name}")


if __name__ == "__main__":
    main()
