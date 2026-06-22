#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# patch_tester_to_cabinet.py
# ─────────────────────────────────────────────────────────────
# ПАТЧ: TESTER_TO_CABINET_V1  ·  маркер: шесть·проверено·до·корня
#
# ЧТО ЧИНИТ:
#   Жалоба Шефа: «опять всё в терминале, делал же через кабинет».
#   Тестер гоняется кнопкой РЫНОК (режим ТЕСТЕР) на бирже, но:
#     · развилка диагностики (Сито1 · спуск · Совет) печаталась голым
#       print() в конце run_tester → уходила в КОНСОЛЬ, не в кабинет;
#     · строки «спуск не нашёл точку (компас=...)» — тоже print() в
#       консоль → перебор не видно живьём в чате биржи.
#   Биржа (_on_progress) показывает в чате только структурные dict с
#   type=="report". Всё остальное — print(f"[EXCHANGE·TESTER] {msg}").
#
# КАК ЧИНИТ (два файла, аккуратно):
#   tester_express.py:
#     · кран тестера накрывает ВЕСЬ путь данных спуска (pull_bars +
#       step_down), не только _fetch — иначе спуск Искры в тестере
#       уходит в живой MT5 и находит точку редко (корень «Совет молчит»);
#     · step_down заперт на загруженном ТФ (один CSV = один этаж);
#     · фикс caught (не инкрементился → --signals игнорировался);
#     · РАЗВИЛКА и ПРОГРЕСС идут через on_progress структурными
#       событиями {type:"verdict"} и {type:"progress"} — в кабинет.
#       Консольный print оставлен ДОПОЛНИТЕЛЬНО (запуск из терминала
#       тоже должен работать) — но кабинет теперь видит всё.
#   ui_exchange.py:
#     · _on_progress учится принимать verdict (развилка → жирная
#       SYSTEM-строка в чат) и progress (лёгкая строка хода в чат).
#
#   Живой режим (run_market → XAUUSD H4) НЕ ТРОГАЕТСЯ.
#
# ИДЕМПОТЕНТЕН: маркер в обоих файлах, повтор — выход. Бэкапы рядом.
# ─────────────────────────────────────────────────────────────

import sys
import shutil
from pathlib import Path
from datetime import datetime

MARKER = "TESTER_TO_CABINET_V1"
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
    return b


def patch_tester():
    if not TESTER.exists():
        _die(f"не найден {TESTER} — запусти из корня репы (-2/).")
    src = TESTER.read_text(encoding="utf-8")
    if MARKER in src:
        print(f"✅ {MARKER} уже в tester_express.py — пропускаю.")
        return
    _backup(TESTER)

    # ── 1. герметичный кран: pull_bars + step_down под краном ──
    anchor_crane = (
        "    orig_fetch = mt5_feed._fetch\n"
        "    orig_term  = mt5_feed._terminal\n"
        "    mt5_feed._fetch    = _fake_fetch\n"
        "    mt5_feed._terminal = lambda: _FakeMT5()\n"
    )
    if anchor_crane not in src:
        _die("[tester] якорь установки крана не найден — re-fetch свежий файл.")
    crane = (
        "    orig_fetch = mt5_feed._fetch\n"
        "    orig_term  = mt5_feed._terminal\n"
        "    orig_pull  = mt5_feed.pull_bars     # " + MARKER + "\n"
        "    orig_step  = mt5_feed.step_down     # " + MARKER + "\n"
        "    mt5_feed._fetch    = _fake_fetch\n"
        "    mt5_feed._terminal = lambda: _FakeMT5()\n"
        "\n"
        "    # ── ГЕРМЕТИЧНЫЙ КРАН (" + MARKER + ") ──\n"
        "    # Спуск Искры (_read_form_on) берёт бары через pull_bars, не\n"
        "    # через _fetch. Накрываем и её: тот же срез истории до курсора.\n"
        "    # step_down ЗАПЕРТ — один CSV = один этаж, спуск проверяет\n"
        "    # точку на загруженном ТФ по реальной истории, не прыгает на\n"
        "    # этажи, которых в этой истории нет.\n"
        "    def _fake_pull(sym, tf_name, count=2000):\n"
        "        return _fake_fetch(None, sym, tf_name, count)\n"
        "    def _locked_step_down(tf_name):\n"
        "        return None\n"
        "    mt5_feed.pull_bars = _fake_pull\n"
        "    mt5_feed.step_down = _locked_step_down\n"
    )
    src = src.replace(anchor_crane, crane, 1)

    # ── 2. снять весь кран в finally ──
    anchor_restore = (
        "    finally:\n"
        "        # ── снимаем кран: всё как было ──\n"
        "        mt5_feed._fetch    = orig_fetch\n"
        "        mt5_feed._terminal = orig_term\n"
        "        report.close()\n"
    )
    if anchor_restore not in src:
        _die("[tester] якорь снятия крана (finally) не найден.")
    src = src.replace(
        anchor_restore,
        "    finally:\n"
        "        # ── снимаем весь кран: всё как было (" + MARKER + ") ──\n"
        "        mt5_feed._fetch    = orig_fetch\n"
        "        mt5_feed._terminal = orig_term\n"
        "        mt5_feed.pull_bars = orig_pull\n"
        "        mt5_feed.step_down = orig_step\n"
        "        report.close()\n",
        1,
    )

    # ── 3. счётчики found_cnt ──
    anchor_counters = (
        "    caught = 0\n"
        "    scanned = 0\n"
    )
    if anchor_counters not in src:
        _die("[tester] якорь счётчиков не найден.")
    src = src.replace(
        anchor_counters,
        "    caught = 0\n"
        "    scanned = 0\n"
        "    found_cnt = 0          # " + MARKER + ": у скольких спуск нашёл точку\n",
        1,
    )

    # ── 4. строки «спуск не нашёл» → через on_progress (в кабинет) ──
    anchor_skip = (
        '            if not found:\n'
        '                print(f"  кандидат {idx+1}/{len(candidates)} ({bd}, {side}): "\n'
        '                      f"спуск не нашёл точку (компас={descent.get(\'compass\')}) — пропускаю")\n'
        '                continue\n'
    )
    if anchor_skip not in src:
        _die("[tester] якорь строки пропуска кандидата не найден.")
    src = src.replace(
        anchor_skip,
        '            if not found:\n'
        '                _msg = (f"кандидат {idx+1}/{len(candidates)} ({bd}, {side}): "\n'
        '                        f"спуск не нашёл точку (компас={descent.get(\'compass\')})")\n'
        '                print("  " + _msg + " — пропускаю")\n'
        '                _emit({"type": "progress", "text": _msg})   # ' + MARKER + ': в кабинет\n'
        '                continue\n',
        1,
    )

    # ── 5. found_cnt++ на проходе ворот ──
    anchor_found = (
        '            out("")\n'
        '            out("🎯 " + "─" * 60)\n'
        '            out(f"🎯 бар {i} ({bd}) — ИСКРА: {t1}")\n'
    )
    if anchor_found not in src:
        _die("[tester] якорь прохода ворот не найден.")
    src = src.replace(
        anchor_found,
        '            found_cnt += 1   # ' + MARKER + ': спуск долетел до Совета\n'
        '            out("")\n'
        '            out("🎯 " + "─" * 60)\n'
        '            out(f"🎯 бар {i} ({bd}) — ИСКРА: {t1}")\n',
        1,
    )

    # ── 6. caught++ ──
    anchor_caught = (
        "            if caught >= n_signals:\n"
        '                out(f"✓ поймал {caught} срабатываний из {scanned} "\n'
        '                    f"проверенных кандидатов — стоп.")\n'
        "                break\n"
    )
    if anchor_caught not in src:
        _die("[tester] якорь проверки caught не найден.")
    src = src.replace(
        anchor_caught,
        "            caught += 1   # " + MARKER + ": Совет собрался и отработал\n"
        "            if caught >= n_signals:\n"
        '                out(f"✓ поймал {caught} срабатываний из {scanned} "\n'
        '                    f"проверенных кандидатов — стоп.")\n'
        "                break\n",
        1,
    )

    # ── 7. развилка через on_progress + print (финал run_tester) ──
    anchor_tail = (
        '    print("")\n'
        '    print(f"📄 полный разговор записан: {report_path}")\n'
        '    print("═" * 64)\n'
    )
    if anchor_tail not in src:
        _die("[tester] якорь финального print не найден.")
    src = src.replace(
        anchor_tail,
        '    # ── РАЗВИЛКА (' + MARKER + ') — в кабинет через on_progress + в консоль ──\n'
        '    _verdict = (f"РАЗВИЛКА · Сито 1: {len(candidates)} кандидатов · "\n'
        '                f"спуск нашёл точку: {found_cnt} · Совет собрался: {caught}")\n'
        '    if found_cnt == 0:\n'
        '        _hint = ("Совет молчит — спуск не нашёл точку ни у кого. Кандидаты "\n'
        '                 "есть, ворота исправны: редок дивер-компас. Следующий шаг — "\n'
        '                 "подключить global_bias (синюю) к спуску.")\n'
        '    else:\n'
        '        _hint = f"Спуск долетел до Совета {found_cnt} раз — ворота работают."\n'
        '    _emit({"type": "verdict", "text": _verdict, "hint": _hint,\n'
        '           "candidates": len(candidates), "found": found_cnt, "council": caught})\n'
        '    print("")\n'
        '    print("─" * 64)\n'
        '    print("  " + _verdict)\n'
        '    print("  → " + _hint)\n'
        '    print("─" * 64)\n'
        '    print("")\n'
        '    print(f"📄 полный разговор записан: {report_path}")\n'
        '    print("═" * 64)\n',
        1,
    )

    # маркер в шапку для grep
    src = src.replace(
        "_HERE = Path(__file__).resolve().parent\n",
        "_HERE = Path(__file__).resolve().parent\n"
        "# " + MARKER + " · кран+caught+развилка/прогресс через on_progress в кабинет\n",
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

    # Врезаем разбор verdict/progress ПЕРЕД финальным print консоли в _on_progress.
    anchor = (
        '            if aid and narrative:\n'
    )
    # Точнее — якорим на самой последней строке колбэка: print(f"[EXCHANGE·TESTER] {msg}")
    anchor_print = '            print(f"[EXCHANGE·TESTER] {msg}")\n'
    if anchor_print not in src:
        _die("[exchange] якорь print([EXCHANGE·TESTER]) не найден — файл изменился.")

    replacement = (
        '            # ── РАЗВИЛКА (' + MARKER + ') → жирная строка в чат ──\n'
        '            if isinstance(msg, dict) and msg.get("type") == "verdict":\n'
        '                txt = msg.get("text", "")\n'
        '                hint = msg.get("hint", "")\n'
        '                state["chat_history"].append({\n'
        '                    "role": "assistant", "agent": "РАЗВИЛКА",\n'
        '                    "content": f"📊 {txt}\\n→ {hint}"})\n'
        '                try:\n'
        '                    update_chat_display()\n'
        '                except Exception:\n'
        '                    pass\n'
        '                print(f"[EXCHANGE·TESTER] {msg}")\n'
        '                return\n'
        '            # ── ПРОГРЕСС перебора (' + MARKER + ') → лёгкая строка в чат ──\n'
        '            if isinstance(msg, dict) and msg.get("type") == "progress":\n'
        '                state["chat_history"].append({\n'
        '                    "role": "assistant", "agent": "···",\n'
        '                    "content": msg.get("text", "")})\n'
        '                try:\n'
        '                    update_chat_display()\n'
        '                except Exception:\n'
        '                    pass\n'
        '                return\n'
        '            print(f"[EXCHANGE·TESTER] {msg}")\n'
    )
    src = src.replace(anchor_print, replacement, 1)

    # маркер в шапку
    src = src.replace(
        "from pathlib import Path\nfrom nicegui import ui, app\n",
        "from pathlib import Path\nfrom nicegui import ui, app\n"
        "# " + MARKER + " · тестер шлёт развилку и прогресс в чат биржи\n",
        1,
    )

    EXCHANGE.write_text(src, encoding="utf-8")
    print(f"✅ {MARKER} применён к ui_exchange.py")


def main():
    patch_tester()
    patch_exchange()
    print("")
    print("ГОТОВО. Теперь в режиме ТЕСТЕР на бирже:")
    print("  · ход перебора виден в чате (строки «спуск не нашёл точку...»)")
    print("  · в конце — жирная строка РАЗВИЛКА (Сито1 · спуск · Совет) в чате")
    print("  · консольный запуск тоже печатает всё (как было)")
    print("  · кран накрывает спуск герметично, --signals работает")
    print("  · живой режим (РЕАЛ) не тронут")


if __name__ == "__main__":
    main()
