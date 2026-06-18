#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ─────────────────────────────────────────────────────────────
# patch_exchange_arkhiv.py
# МОСТИК: Архивариус (A05) встаёт ПЯТЫМ в цепочку РЫНОК.
#
# Спринт 45 · 2026-06-18 · Брат (Claude)
#
# ЧТО ДЕЛАЕТ:
#   После того как Ганс (A04) положил факт на стол, цепочка РЫНОК
#   будит Архивариуса. Он сам собирает отпечаток момента из рабочей
#   памяти (свой штатный навык run_arkhiv: signature=None → читает
#   trading_state), листает Атлас по нужной картинке и кладёт справку.
#
#   Голос Архивариуса → в отчёт (пузырёк A05) + в чат-ленту.
#   Рабочая память прогона → state["arkhiv_last_run"] (чтобы чат
#   потом помнил, что он только что насчитал — как у всех сенсоров).
#
# ЗАКОН ЦЕПОЧКИ (§1c): Архивариус будится в том же затворе, что Морж/
#   Паникёр/Ганс — только при DETECTED/CONFIRMED Искры. Искра молчит →
#   цех спит → Архивариуса не зовут. Это правильно, не поломка.
#
# ОСОБОЕ: Архивариус рынок НЕ поднимает (его закон — только склад).
#   run_arkhiv без аргументов сам прочитает шину. Поэтому в отличие
#   от Моржа/Ганса ему НЕ передаём symbol/timeframe для котировок —
#   он не смотрит цену вообще.
#
# ИДЕМПОТЕНТНОСТЬ: маркер EXCHANGE_ARKHIV. Повторный запуск — no-op.
# БЭКАП: ui_exchange.py.bak_<timestamp> рядом с оригиналом.
# ─────────────────────────────────────────────────────────────

import re
import shutil
from datetime import datetime
from pathlib import Path

TARGET = Path("studio/economy/ui_exchange.py")
MARKER = "EXCHANGE_ARKHIV"

# Якорь — конец блока Ганса в run_market(). Вставляем СРАЗУ после него,
# не трогая ни одной существующей строки. Берём хвост ветки else Ганса.
ANCHOR = (
    '                ui.notify("🎯 Ганс смолчал (нет данных или сбой)", type="warning")\n'
)

# Блок Архивариуса — пятое звено. Отступ как у блоков Моржа/Паникёра/Ганса
# (внутри `if t1 in ("DETECTED", "CONFIRMED"):`).
INSERT = '''
            # ── EXCHANGE_ARKHIV: Архивариус после Ганса (память цеха) ──
            # Архивариус рынок НЕ смотрит. Он собирает отпечаток момента
            # из рабочей памяти (что сложили четыре сенсора) и листает
            # Атлас: сколько похожих случаев было, чем кончались. Контекст,
            # не голос (§1f). run_arkhiv без сигнатуры сам прочитает шину.
            ui.notify("📚 Бужу Архивариуса — листает Атлас...", type="info")
            try:
                from studio.modules.trading.arkhiv_live import run_arkhiv
                ar = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: run_arkhiv())
            except Exception as e:
                ui.notify(f"Архивариус не проснулся: {e}", type="negative")
                ar = {"ok": False}

            if ar.get("ok"):
                asig = ar.get("signal", {})
                state["reports"]["A05"] = ar.get("narrative", "") or ar.get("raw", "")
                state["arkhiv_signal"] = asig
                state["arkhiv_stats"]  = ar.get("stats", {})
                state["arkhiv_digest"] = ar.get("digest", {})
                state["arkhiv_last_run"] = {
                    "narrative": ar.get("narrative", ""),
                    "signal":    asig,
                    "signature": ar.get("signature", {}),
                }
                conf = asig.get("arkhiv_confidence", "—")
                n    = asig.get("sample_size", "—")
                state["chat_history"].append({
                    "role": "assistant", "agent": "A05",
                    "content": (f"📚 Похожих случаев в Атласе: {n}. "
                                f"Уверенность: {conf}. Отчёт справа.")})
                update_chat_display()
                update_avatar_states()
                ui.notify(f"📚 Архивариус: {conf} ({n} случаев)", type="positive")
            else:
                ui.notify("📚 Архивариус смолчал (нет данных или сбой)", type="warning")
'''


def main():
    if not TARGET.exists():
        print(f"❌ Не найден {TARGET}. Запусти из корня репозитория студии.")
        return

    src = TARGET.read_text(encoding="utf-8")

    if MARKER in src:
        print(f"✅ Маркер {MARKER} уже в файле — патч применён ранее. Ничего не делаю.")
        return

    if ANCHOR not in src:
        print("❌ Якорь (хвост блока Ганса) не найден. Файл изменился —")
        print("   не рискую вставлять вслепую. Покажи ui_exchange.py, поправлю якорь.")
        return

    # Вставляем блок Архивариуса сразу ПОСЛЕ якоря (хвоста Ганса).
    new_src = src.replace(ANCHOR, ANCHOR + INSERT, 1)

    if new_src == src:
        print("❌ Замена не сработала (якорь есть, но replace пуст). Стоп.")
        return

    # Бэкап
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = TARGET.with_suffix(TARGET.suffix + f".bak_{ts}")
    shutil.copy2(TARGET, backup)

    TARGET.write_text(new_src, encoding="utf-8")

    # Проверка синтаксиса
    import py_compile
    try:
        py_compile.compile(str(TARGET), doraise=True)
    except py_compile.PyCompileError as e:
        print(f"❌ СИНТАКСИС СЛОМАН после патча: {e}")
        print(f"   Откатываю из бэкапа {backup.name}")
        shutil.copy2(backup, TARGET)
        return

    print(f"✅ Мостик наведён: Архивариус (A05) встал пятым в цепочку РЫНОК.")
    print(f"   Бэкап: {backup.name}")
    print(f"   Маркер: {MARKER}")
    print()
    print("   Теперь при DETECTED/CONFIRMED Искры цепочка:")
    print("   Искра → Морж → Паникёр → Ганс → 📚 Архивариус (листает Атлас).")
    print()
    print("   ⚠️  Живьём увидишь только на реальном сигнале Искры —")
    print("   на молчании рынка цех спит (это правильно).")


if __name__ == "__main__":
    main()
