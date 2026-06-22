#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# patch_tester_trade_feed.py
# ─────────────────────────────────────────────────────────────
# ПАТЧ: TESTER_TRADE_FEED_V1  ·  маркер: шесть·проверено·до·корня
#
# ЧТО ЧИНИТ (главная боль Шефа: «открыли и годы тишины»):
#
#   Тестер показывает только КАНДИДАТОВ (точки входа). Жизнь позиции
#   между ними — ведение и закрытие — НЕ показывает. Позиция открылась
#   на кандидате 1, закрылась по exit_bell где-то между кандидатами
#   1 и 2 — но [SETTLE] ушёл в консоль, в кабинет не попал. Шеф видит:
#   открыли... тишина... новый кандидат через год. Думает — бросили,
#   забыли. И жмёт СТОП, потому что смотреть не на что.
#
#   Это не баг ведения (механика закрывает по §9) — это СЛЕПОТА вывода:
#   тестер не показывает ленту сделок, ради которой он и нужен.
#
# КАК ЧИНИТ (только тестер, _settle не трогаем):
#   Тестер сам отслеживает стол вокруг settle и Совета:
#     · ОТКРЫТИЕ: после Совета позиций стало больше → шлём в кабинет
#       «🟢 ОТКРЫТА: TRADER DIR @ entry» по каждой новой позиции.
#     · ЗАКРЫТИЕ: после прокатки settle позиция исчезла со стола →
#       читаем последнюю запись trading_pnl.jsonl (settle уже записал
#       туда сделку с pnl_r, closed_at, reason) → шлём «🔴 ЗАКРЫТА:
#       TRADER +N.NR, жила K баров (REASON)».
#   Лента летит и в кабинет (on_progress type=trade), и в консоль, и
#   в файл-отчёт. Между кандидатами больше НЕ тишина — видно жизнь сделок.
#
#   ui_exchange учится показывать type=trade жирной строкой в чате.
#
# ИДЕМПОТЕНТЕН: маркер в обоих файлах, повтор — выход. Бэкапы рядом.
# ─────────────────────────────────────────────────────────────

import sys
import shutil
from pathlib import Path
from datetime import datetime

MARKER = "TESTER_TRADE_FEED_V1"
TESTER = Path("studio/modules/trading/tester_express.py")
EXCHANGE = Path("studio/economy/ui_exchange.py")


def _die(msg):
    print(f"❌ {msg}")
    sys.exit(1)


def _backup(path):
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    b = path.with_name(f"{path.stem}.bak_{stamp}{path.suffix}")
    shutil.copy2(path, b)
    print(f"💾 бэкап: {b.name}")


def patch_tester():
    if not TESTER.exists():
        _die(f"не найден {TESTER} — запусти из корня репы (-2/).")
    src = TESTER.read_text(encoding="utf-8")
    if MARKER in src:
        print(f"✅ {MARKER} уже в tester_express.py — пропускаю.")
        return
    _backup(TESTER)

    # ── 1. помощники ленты: снимок стола + чтение закрытий ──
    # Вставляем перед def run_tester.
    anchor_def = "def run_tester(csv_path: str, symbol: str, timeframe: str,\n"
    if anchor_def not in src:
        _die("[tester] def run_tester не найден.")
    helpers = (
        "# ── " + MARKER + ": лента сделок (открытие/закрытие в кабинет) ──\n"
        "def _table_snapshot():\n"
        "    \"\"\"Множество magic открытых позиций сейчас — для сравнения\n"
        "    до/после (что открылось, что закрылось).\"\"\"\n"
        "    try:\n"
        "        from studio.modules.trading.hooks import load_trading_state\n"
        "        return {p.get('magic'): dict(p)\n"
        "                for p in load_trading_state().get('positions', []) or []\n"
        "                if p.get('status') == 'OPEN'}\n"
        "    except Exception:\n"
        "        return {}\n"
        "\n"
        "\n"
        "def _read_last_closures(n=10):\n"
        "    \"\"\"Последние n закрытых сделок из trading_pnl.jsonl —\n"
        "    settle уже записал туда pnl_r, closed_at, reason.\"\"\"\n"
        "    from pathlib import Path as _P\n"
        "    import json as _j\n"
        "    p = _P('economy/data/trading_pnl.jsonl')\n"
        "    if not p.exists():\n"
        "        return []\n"
        "    try:\n"
        "        lines = p.read_text(encoding='utf-8').strip().splitlines()\n"
        "        out = []\n"
        "        for ln in lines[-n:]:\n"
        "            try:\n"
        "                out.append(_j.loads(ln))\n"
        "            except Exception:\n"
        "                pass\n"
        "        return out\n"
        "    except Exception:\n"
        "        return []\n"
        "\n"
        "\n"
    )
    src = src.replace(anchor_def, helpers + anchor_def, 1)

    # ── 2. функция отправки ленты в кабинет+консоль+файл ──
    # Вставляем внутри run_tester после определения out(). Якорь — out().
    anchor_out = (
        "    def out(line=\"\"):\n"
        "        print(line)\n"
        "        report.write(line + \"\\n\")\n"
    )
    if anchor_out not in src:
        _die("[tester] def out не найден.")
    feed_fn = (
        "    def out(line=\"\"):\n"
        "        print(line)\n"
        "        report.write(line + \"\\n\")\n"
        "\n"
        "    # " + MARKER + ": лента сделок в кабинет+консоль+файл\n"
        "    _pnl_seen = {\"n\": len(_read_last_closures(9999))}\n"
        "    def _feed_opened(pos):\n"
        "        _d = pos.get('direction', '?')\n"
        "        _t = pos.get('trader', '?')\n"
        "        _e = pos.get('entry')\n"
        "        line = f\"🟢 ОТКРЫТА: {_t} {_d} @ {_e}\"\n"
        "        out(\"  \" + line)\n"
        "        _emit({\"type\": \"trade\", \"kind\": \"open\", \"text\": line})\n"
        "    def _feed_check_closures(cur_bar_i):\n"
        "        # читаем новые закрытия с прошлой проверки и шлём ленту\n"
        "        all_cl = _read_last_closures(9999)\n"
        "        new = all_cl[_pnl_seen['n']:]\n"
        "        _pnl_seen['n'] = len(all_cl)\n"
        "        for rec in new:\n"
        "            _t = rec.get('trader', '?')\n"
        "            _r = rec.get('pnl_r')\n"
        "            _reason = rec.get('close_reason', '?')\n"
        "            _opened = rec.get('opened_at', '?')\n"
        "            _closed = rec.get('closed_at', '?')\n"
        "            _rstr = (f\"{'+' if (_r or 0) >= 0 else ''}{_r}R\"\n"
        "                     if _r is not None else '—')\n"
        "            line = (f\"🔴 ЗАКРЫТА: {_t} {_rstr} ({_reason}) · \"\n"
        "                    f\"{_opened} → {_closed}\")\n"
        "            out(\"  \" + line)\n"
        "            _emit({\"type\": \"trade\", \"kind\": \"close\", \"text\": line})\n"
    )
    src = src.replace(anchor_out, feed_fn, 1)

    # ── 3. проверять закрытия ПОСЛЕ прокатки settle ──
    anchor_after_settle = (
        "                _settle_bar(bars_all[max(0, _b - 299):_b + 1],\n"
        "                            symbol, timeframe, point)\n"
        "            _last_settled = i\n"
    )
    # на случай если окно ещё 60 (не накачен full_window) — поддержим оба
    anchor_after_settle_60 = (
        "                _settle_bar(bars_all[max(0, _b - 59):_b + 1],\n"
        "                            symbol, timeframe, point)\n"
        "            _last_settled = i\n"
    )
    if anchor_after_settle in src:
        a = anchor_after_settle
    elif anchor_after_settle_60 in src:
        a = anchor_after_settle_60
    else:
        _die("[tester] якорь проката settle не найден (ни 300, ни 60).")
    src = src.replace(
        a,
        a + "            _feed_check_closures(i)   # " + MARKER + ": лента закрытий\n",
        1,
    )

    # ── 4. отследить открытия после Совета ──
    # Якорь: блок Исполнителя (метка символа), после него стол мог
    # пополниться. Снимаем снимок ДО Совета и сравниваем ПОСЛЕ.
    # Проще: после метки символа читаем стол и шлём новые позиции.
    anchor_exec_mark = (
        "            # TESTER_CLEAN_TABLE_V1: метим свежие позиции символом (для Шага 2)\n"
    )
    if anchor_exec_mark in src:
        # снимок ДО Совета ставим в начале обработки кандидата
        anchor_cursor = (
            "            r_iskra = run_iskra(symbol=symbol, timeframe=timeframe)\n"
        )
        if anchor_cursor in src:
            src = src.replace(
                anchor_cursor,
                "            _table_before = set(_table_snapshot().keys())   # " + MARKER + "\n"
                "            r_iskra = run_iskra(symbol=symbol, timeframe=timeframe)\n",
                1,
            )
        # после метки символа — сравнить и заявить открытия
        src = src.replace(
            anchor_exec_mark,
            "            # " + MARKER + ": лента открытий — что появилось на столе\n"
            "            try:\n"
            "                _now = _table_snapshot()\n"
            "                for _m, _p in _now.items():\n"
            "                    if _m not in _table_before:\n"
            "                        _feed_opened(_p)\n"
            "            except Exception:\n"
            "                pass\n"
            "            # TESTER_CLEAN_TABLE_V1: метим свежие позиции символом (для Шага 2)\n",
            1,
        )
    else:
        print("⚠️  [tester] якорь Исполнителя не найден — открытия в ленту "
              "не врезаны (закрытия работают). Несрочно.")

    # маркер в шапку
    src = src.replace(
        "_HERE = Path(__file__).resolve().parent\n",
        "_HERE = Path(__file__).resolve().parent\n"
        "# " + MARKER + " · лента сделок: открытие и закрытие видны в кабинете\n",
        1,
    )

    TESTER.write_text(src, encoding="utf-8")
    print(f"✅ {MARKER} применён к tester_express.py")


def patch_exchange():
    if not EXCHANGE.exists():
        _die(f"не найден {EXCHANGE} — запусти из корня репы.")
    src = EXCHANGE.read_text(encoding="utf-8")
    if MARKER in src:
        print(f"✅ {MARKER} уже в ui_exchange.py — пропускаю.")
        return
    _backup(EXCHANGE)

    anchor_print = '            print(f"[EXCHANGE·TESTER] {msg}")\n'
    if anchor_print not in src:
        _die("[exchange] якорь print([EXCHANGE·TESTER]) не найден.")
    src = src.replace(
        anchor_print,
        '            # ── ' + MARKER + ': лента сделок → строка в чат ──\n'
        '            if isinstance(msg, dict) and msg.get("type") == "trade":\n'
        '                state["chat_history"].append({\n'
        '                    "role": "assistant", "agent": "СДЕЛКА",\n'
        '                    "content": msg.get("text", "")})\n'
        '                try:\n'
        '                    update_chat_display()\n'
        '                except Exception:\n'
        '                    pass\n'
        '                return\n'
        '            print(f"[EXCHANGE·TESTER] {msg}")\n',
        1,
    )
    src = src.replace(
        "from pathlib import Path\nfrom nicegui import ui, app\n",
        "from pathlib import Path\nfrom nicegui import ui, app\n"
        "# " + MARKER + " · лента сделок в чате биржи\n",
        1,
    )
    EXCHANGE.write_text(src, encoding="utf-8")
    print(f"✅ {MARKER} применён к ui_exchange.py")


def main():
    patch_tester()
    patch_exchange()
    print("")
    print("ГОТОВО — лента сделок:")
    print("  · 🟢 ОТКРЫТА — когда трейдер вошёл (видно сразу)")
    print("  · 🔴 ЗАКРЫТА — когда вышел: R, причина, сроки (видно между кандидатами)")
    print("  · больше НЕ тишина в годы — жизнь сделки видна в кабинете")


if __name__ == "__main__":
    main()
