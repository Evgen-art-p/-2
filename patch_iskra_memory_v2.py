#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_iskra_memory_v2.py — РАЗРЫВ 2 контура Искры v2 (§1e мастер-контекста)

ЧТО ЧИНИТ (на пальцах):
  Искра уже умеет спускаться по лесенке ТФ и находить точку. Когда находит,
  важно запомнить ДВА факта: на каком этаже (found_timeframe) и в какую
  сторону (trend_direction) — чтобы Морж встал на тот же масштаб.
  Сейчас память (_save_iskra_memory) пишет только старые 3 поля.
  Эти два теряются → связка «Морж наследует от Искры» порвана.

ЧТО ДЕЛАЕТ:
  _save_iskra_memory начинает сохранять trend_direction и found_timeframe
  в trading_state["iskra"]. Старые прогоны без этих полей → None (не падает).

БЕЗОПАСНОСТЬ:
  · идемпотентен (маркер ISKRA_MEM_V2 — повторный запуск ничего не делает)
  · авто-бэкап .bak_YYYYMMDD_HHMMSS
  · якорный replace по точной строке, CRLF-safe
"""
import re
import shutil
from datetime import datetime
from pathlib import Path

TARGET = Path("studio/modules/trading/iskra_live.py")
MARKER = "ISKRA_MEM_V2"


def main():
    if not TARGET.exists():
        print(f"❌ Не найден файл: {TARGET}")
        print("   Запускай из корня студии (где папка studio/).")
        return

    src = TARGET.read_text(encoding="utf-8")

    if MARKER in src:
        print(f"✅ Уже пропатчено (маркер {MARKER}) — ничего не делаю.")
        return

    # Якорь: старый блок сохранения (три поля). Ловим именно строку history_dna,
    # после неё дописываем два новых поля. Допускаем любые пробелы и \r.
    anchor = (
        '    tstate["iskra"]["history_dna"]      = signal.get("history_dna", "")\n'
    )
    if anchor not in src:
        # Фоллбэк с \r\n
        anchor_cr = anchor.replace("\n", "\r\n")
        if anchor_cr in src:
            anchor = anchor_cr
        else:
            print("❌ Якорь не найден — файл изменился. Патч не применён (безопасно).")
            print("   Ищу строку: tstate[\"iskra\"][\"history_dna\"] = signal.get(...)")
            return

    addition = (
        anchor
        + '    # ── ' + MARKER + ': два поля спуска v2 — Морж наследует масштаб ──\n'
        + '    # found_timeframe берём из signal (его кладёт user_msg при found),\n'
        + '    # с фоллбэком на старое имя timeframe. trend_direction = компас спуска.\n'
        + '    tstate["iskra"]["trend_direction"] = (\n'
        + '        signal.get("trend_direction") or signal.get("compass")\n'
        + '    )\n'
        + '    tstate["iskra"]["found_timeframe"] = (\n'
        + '        signal.get("found_timeframe") or signal.get("timeframe")\n'
        + '    )\n'
    )

    new_src = src.replace(anchor, addition, 1)

    if new_src == src:
        print("❌ Замена не сработала — ничего не записано (безопасно).")
        return

    # Бэкап
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = TARGET.with_suffix(TARGET.suffix + f".bak_{stamp}")
    shutil.copy2(TARGET, bak)
    print(f"💾 Бэкап: {bak.name}")

    TARGET.write_text(new_src, encoding="utf-8")
    print(f"✅ Память Искры расширена: trend_direction + found_timeframe сохраняются.")
    print(f"   Теперь Морж сможет наследовать масштаб спуска.")


if __name__ == "__main__":
    main()
