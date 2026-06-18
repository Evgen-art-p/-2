#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ─────────────────────────────────────────────────────────────
# patch_arkhiv_prompt_v17.py
# ОЧКИ: промт Архивариуса (A05) под нынешние правила цеха.
#
# Спринт 45 · 2026-06-18 · Брат (Claude)
#
# ЗАЧЕМ:
#   Промт A05/forge/prompt.md ссылался на CHAIN_CONTRACT v1.1 и поле
#   chain_data.entry_trigger — старую модель. Контракт давно v1.7,
#   entry_trigger разжалован в факт fractal_valid (§1i, оживление Ганса).
#   Числа Архивариус и так берёт из digest (защита чисел в моторе
#   перетирает что бы модель ни сказала), так что это НЕ ломало работу —
#   но инструкция учила смотреть на несуществующее поле. Подравниваем
#   очки: что в коде, то и в промте.
#
# ЧТО МЕНЯЕТ (только текст промта, ни строки кода):
#   1. chain_data.entry_trigger → chain_data.fractal_valid (сигнатура 4 сенсоров)
#   2. CHAIN_CONTRACT v1.1 → v1.7  (две ссылки: формат ответа + подпись ДНК)
#   3. Заголовок формата: "v1.1 — двухслойный" → "v1.7 — двухслойный"
#
# ЧЕГО НЕ ТРОГАЕТ: характер, закон "числа считает код", правило
#   confidence, смертный грех, формат signal. Всё это уже верное.
#
# ИДЕМПОТЕНТНОСТЬ: маркер-проверка по наличию старых строк.
#   Если старых строк нет — патч уже применён, no-op.
# БЭКАП: prompt.md.bak_<timestamp> рядом с оригиналом.
# ─────────────────────────────────────────────────────────────

import shutil
from datetime import datetime
from pathlib import Path

TARGET = Path("studio/modules/trading/A05/forge/prompt.md")

# Точечные замены: (старое, новое). Каждая должна встретиться 1 раз.
REPLACEMENTS = [
    (
        "chain_data.entry_trigger    ←        — // —",
        "chain_data.fractal_valid    ←        — // —  (Ганс, §1i)",
    ),
    (
        "## ФОРМАТ ОТВЕТА (CHAIN_CONTRACT v1.1 — двухслойный)",
        "## ФОРМАТ ОТВЕТА (CHAIN_CONTRACT v1.7 — двухслойный)",
    ),
    (
        "*Источники ДНК: WAR_COUNCIL_FINAL v1.2 · CHAIN_CONTRACT v1.1.*",
        "*Источники ДНК: WAR_COUNCIL_FINAL v1.2 · CHAIN_CONTRACT v1.7.*",
    ),
]


def main():
    if not TARGET.exists():
        print(f"❌ Не найден {TARGET}. Запусти из корня репозитория студии.")
        return

    src = TARGET.read_text(encoding="utf-8")

    # Идемпотентность: если ни одной старой строки нет — уже подровняли.
    found_any = any(old in src for old, _ in REPLACEMENTS)
    if not found_any:
        print("✅ Старых строк нет — очки уже подровняны ранее. Ничего не делаю.")
        return

    new_src = src
    applied = []
    skipped = []
    for old, new in REPLACEMENTS:
        if old in new_src:
            count = new_src.count(old)
            if count != 1:
                print(f"⚠️  Фрагмент встречается {count} раз (ожидал 1):")
                print(f"    «{old[:50]}...»  — пропускаю во избежание промаха.")
                skipped.append(old)
                continue
            new_src = new_src.replace(old, new, 1)
            applied.append(old)
        else:
            # уже заменён ранее — это нормально при частичном применении
            skipped.append(old)

    if not applied:
        print("✅ Все целевые строки уже в новом виде — нечего менять.")
        return

    # Бэкап
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = TARGET.with_suffix(TARGET.suffix + f".bak_{ts}")
    shutil.copy2(TARGET, backup)

    TARGET.write_text(new_src, encoding="utf-8")

    print(f"✅ Очки подровнял: промт A05 говорит про нынешние правила.")
    print(f"   Применено замен: {len(applied)} из {len(REPLACEMENTS)}")
    print(f"   Бэкап: {backup.name}")
    print()
    print("   Теперь инструкция Архивариуса совпадает с тем, что делает код:")
    print("   сигнатура = 4 сенсора (вкл. fractal_valid Ганса), контракт v1.7.")


if __name__ == "__main__":
    main()
