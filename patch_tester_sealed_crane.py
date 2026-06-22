#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# patch_tester_sealed_crane.py
# ─────────────────────────────────────────────────────────────
# ПАТЧ: TESTER_SEALED_CRANE_V1  ·  маркер: шесть·проверено·до·корня
#
# ЧТО ЧИНИТ (корень «Искра только перебирает, Совет молчит»):
#
#   Спуск Искры (_descend → _read_form_on) берёт бары через pull_bars,
#   а pull_bars сама зовёт _terminal() и _fetch. Тестер накрывал краном
#   ТОЛЬКО _fetch и _terminal — но pull_bars на КАЖДОМ этаже спуска
#   просила свой ТФ (H1, M30, M15...), а фейковый _fetch отдавал ОДИН
#   и тот же срез загруженного CSV для любого ТФ. Спуск шёл по этажам,
#   которых в одном CSV нет → bdb_dir чужого масштаба не совпадал с
#   компасом → descent.found = False почти всегда → ворота Совета не
#   открывались → «одна Искра перебирает».
#
# КАК ЧИНИТ (без единой правки живого кода):
#
#   Тестер накрывает краном ВЕСЬ путь данных, не только _fetch:
#     · _fetch / _terminal — как было (срез CSV вместо терминала);
#     · pull_bars — теперь тоже отдаёт срез истории до курсора
#                   (раньше уходила в живой MT5 мимо крана);
#     · step_down — ЗАПЕРТ на загруженном ТФ: ниже него возвращает None.
#                   Один CSV = один этаж. Спуск не прыгает на этажи,
#                   которых нет — проверяет точку на загруженном этаже
#                   по РЕАЛЬНОЙ истории. Это честно: тестер гоняет ту
#                   историю, что Шеф зарядил, на её масштабе.
#
#   Живой режим (run_market → run_iskra XAUUSD H4) НЕ ТРОГАЕТСЯ: кран
#   живёт только внутри run_tester и снимается в finally. Спуск в реале
#   как ходил по лесенке через живой MT5, так и ходит.
#
# ПОПУТНО (тот же корень, честная мелочь):
#   · caught НЕ инкрементился — тестер игнорировал --signals N и гонял
#     ВСЕ кандидаты. Теперь caught растёт на каждом собранном Совете.
#   · Счётчик развилки в конце: «Сито 1: N · спуск нашёл K · Совет M».
#     Та самая диагностика из мастера — цифра, а не счёт строк глазами.
#
# ИДЕМПОТЕНТЕН: повторный запуск видит маркер и выходит. Бэкап рядом.
# ─────────────────────────────────────────────────────────────

import sys
import shutil
from pathlib import Path
from datetime import datetime

MARKER = "TESTER_SEALED_CRANE_V1"
TARGET = Path("studio/modules/trading/tester_express.py")


def _die(msg):
    print(f"❌ {msg}")
    sys.exit(1)


def main():
    if not TARGET.exists():
        _die(f"не найден {TARGET} — запусти из корня репы (-2/).")

    src = TARGET.read_text(encoding="utf-8")

    if MARKER in src:
        print(f"✅ {MARKER} уже стоит — патч идемпотентен, выхожу.")
        return

    # ── бэкап ──
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = TARGET.with_name(f"{TARGET.stem}.bak_{stamp}{TARGET.suffix}")
    shutil.copy2(TARGET, backup)
    print(f"💾 бэкап: {backup.name}")

    # ═════════════════════════════════════════════════════════
    # ПРАВКА 1 — герметичный кран: pull_bars + step_down под краном.
    # Якорим на блоке установки крана (_fetch/_terminal) и дополняем
    # его подменой pull_bars (срез истории) и step_down (запор ТФ).
    # ═════════════════════════════════════════════════════════
    anchor_crane = (
        "    orig_fetch = mt5_feed._fetch\n"
        "    orig_term  = mt5_feed._terminal\n"
        "    mt5_feed._fetch    = _fake_fetch\n"
        "    mt5_feed._terminal = lambda: _FakeMT5()\n"
    )
    if anchor_crane not in src:
        _die("якорь установки крана не найден — файл изменился, патч не лёг. "
             "Re-fetch свежий tester_express.py и повтори.")

    crane_sealed = (
        "    orig_fetch = mt5_feed._fetch\n"
        "    orig_term  = mt5_feed._terminal\n"
        "    orig_pull  = mt5_feed.pull_bars     # " + MARKER + "\n"
        "    orig_step  = mt5_feed.step_down     # " + MARKER + "\n"
        "    mt5_feed._fetch    = _fake_fetch\n"
        "    mt5_feed._terminal = lambda: _FakeMT5()\n"
        "\n"
        "    # ── ГЕРМЕТИЧНЫЙ КРАН (" + MARKER + ") ──\n"
        "    # Спуск Искры (_read_form_on) берёт бары через pull_bars, а не\n"
        "    # через _fetch напрямую. Накрываем и её: pull_bars в тестере\n"
        "    # отдаёт тот же срез истории до курсора (формат (bars, point)).\n"
        "    # Раньше она уходила в живой MT5 мимо крана и спуск слеп.\n"
        "    def _fake_pull(sym, tf_name, count=2000):\n"
        "        return _fake_fetch(None, sym, tf_name, count)\n"
        "\n"
        "    # step_down ЗАПЕРТ на загруженном ТФ: один CSV = один этаж.\n"
        "    # Спуск не прыгает на этажи, которых в этой истории нет —\n"
        "    # проверяет точку на загруженном этаже по реальной истории.\n"
        "    # Возвращаем None ниже стартового ТФ → _descend проверит\n"
        "    # точку на месте (top_form) и либо найдёт, либо честно нет.\n"
        "    def _locked_step_down(tf_name):\n"
        "        return None\n"
        "\n"
        "    mt5_feed.pull_bars = _fake_pull\n"
        "    mt5_feed.step_down = _locked_step_down\n"
    )
    src = src.replace(anchor_crane, crane_sealed, 1)

    # ═════════════════════════════════════════════════════════
    # ПРАВКА 2 — снять весь кран в finally (было только _fetch/_terminal).
    # ═════════════════════════════════════════════════════════
    anchor_restore = (
        "    finally:\n"
        "        # ── снимаем кран: всё как было ──\n"
        "        mt5_feed._fetch    = orig_fetch\n"
        "        mt5_feed._terminal = orig_term\n"
        "        report.close()\n"
    )
    if anchor_restore not in src:
        _die("якорь снятия крана (finally) не найден — патч откатан, бэкап цел.")

    restore_sealed = (
        "    finally:\n"
        "        # ── снимаем весь кран: всё как было (" + MARKER + ") ──\n"
        "        mt5_feed._fetch    = orig_fetch\n"
        "        mt5_feed._terminal = orig_term\n"
        "        mt5_feed.pull_bars = orig_pull\n"
        "        mt5_feed.step_down = orig_step\n"
        "        report.close()\n"
    )
    src = src.replace(anchor_restore, restore_sealed, 1)

    # ═════════════════════════════════════════════════════════
    # ПРАВКА 3 — счётчик развилки: считаем, у скольких кандидатов спуск
    # нашёл точку (found_cnt). caught растёт на собранном Совете.
    # ═════════════════════════════════════════════════════════
    # 3a. Завести found_cnt рядом с caught/scanned.
    anchor_counters = (
        "    caught = 0\n"
        "    scanned = 0\n"
    )
    if anchor_counters not in src:
        _die("якорь счётчиков (caught/scanned) не найден — патч откатан, бэкап цел.")
    src = src.replace(
        anchor_counters,
        "    caught = 0\n"
        "    scanned = 0\n"
        "    found_cnt = 0          # " + MARKER + ": у скольких спуск нашёл точку\n",
        1,
    )

    # 3b. Инкремент found_cnt на found=True (сразу после прохода ворот).
    anchor_found = (
        '            out("")\n'
        '            out("🎯 " + "─" * 60)\n'
        '            out(f"🎯 бар {i} ({bd}) — ИСКРА: {t1}")\n'
    )
    if anchor_found not in src:
        _die("якорь прохода ворот не найден — патч откатан, бэкап цел.")
    src = src.replace(
        anchor_found,
        '            found_cnt += 1   # ' + MARKER + ': спуск долетел до Совета\n'
        '            out("")\n'
        '            out("🎯 " + "─" * 60)\n'
        '            out(f"🎯 бар {i} ({bd}) — ИСКРА: {t1}")\n',
        1,
    )

    # 3c. caught растёт после того как Совет отработал (Исполнитель —
    # последнее звено цепи). Якорим на финальной проверке caught.
    anchor_caught_check = (
        "            if caught >= n_signals:\n"
        '                out(f"✓ поймал {caught} срабатываний из {scanned} "\n'
        '                    f"проверенных кандидатов — стоп.")\n'
        "                break\n"
    )
    if anchor_caught_check not in src:
        _die("якорь проверки caught не найден — патч откатан, бэкап цел.")
    src = src.replace(
        anchor_caught_check,
        "            caught += 1   # " + MARKER + ": Совет собрался и отработал\n"
        "            if caught >= n_signals:\n"
        '                out(f"✓ поймал {caught} срабатываний из {scanned} "\n'
        '                    f"проверенных кандидатов — стоп.")\n'
        "                break\n",
        1,
    )

    # ═════════════════════════════════════════════════════════
    # ПРАВКА 4 — строка развилки в самом конце (после цикла, в try).
    # Якорим на else цикла for (печатается, если прошли всех кандидатов).
    # Добавляем ПЕРЕД finally сводку независимо от пути выхода — кладём
    # её в конце функции после снятия крана, через _emit и print.
    # Проще: дописываем сводку в финальный print блок.
    # ═════════════════════════════════════════════════════════
    anchor_tail = (
        '    print("")\n'
        '    print(f"📄 полный разговор записан: {report_path}")\n'
        '    print("═" * 64)\n'
    )
    if anchor_tail not in src:
        _die("якорь финального print не найден — патч откатан, бэкап цел.")
    src = src.replace(
        anchor_tail,
        '    print("")\n'
        '    # ── РАЗВИЛКА ДИАГНОСТИКИ (' + MARKER + ') ──\n'
        '    print("─" * 64)\n'
        '    print(f"  РАЗВИЛКА · Сито 1: {len(candidates)} кандидатов · "\n'
        '          f"спуск нашёл точку: {found_cnt} · Совет собрался: {caught}")\n'
        '    if found_cnt == 0:\n'
        '        print("  → Совет молчит, потому что СПУСК НЕ НАШЁЛ точку ни у кого.")\n'
        '        print("    Кандидаты есть, ворота исправны — редкость дивер-компаса.")\n'
        '        print("    Следующий шаг: подключить global_bias (синюю) к спуску.")\n'
        '    else:\n'
        '        print(f"  → Спуск долетел до Совета {found_cnt} раз — ворота работают.")\n'
        '    print("─" * 64)\n'
        '    print("")\n'
        '    print(f"📄 полный разговор записан: {report_path}")\n'
        '    print("═" * 64)\n',
        1,
    )

    # ── финальный маркер-печать в шапку файла (чтобы grep ловил) ──
    src = src.replace(
        "_HERE = Path(__file__).resolve().parent\n",
        "_HERE = Path(__file__).resolve().parent\n"
        "# " + MARKER + " · герметичный кран тестера (pull_bars+step_down) "
        "+ фикс caught + развилка\n",
        1,
    )

    TARGET.write_text(src, encoding="utf-8")
    print(f"✅ {MARKER} применён к {TARGET}")
    print("   · pull_bars и step_down теперь под краном тестера")
    print("   · step_down заперт на загруженном ТФ (один CSV = один этаж)")
    print("   · caught инкрементится — --signals N снова работает")
    print("   · в конце прогона печатается РАЗВИЛКА (Сито1 · спуск · Совет)")
    print("   · живой режим (run_market) НЕ тронут")
    print(f"\n   откат при нужде: cp {backup.name} {TARGET.name}")


if __name__ == "__main__":
    main()
