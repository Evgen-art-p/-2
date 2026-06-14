#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_clean_morj_dna.py
═══════════════════════════════════════════════════════════════════════════
ЦЕХ: trading · АГЕНТ: A02 Морж · СПРИНТ: 45

ЧТО ЛЕЧИТ
  При рождении Моржа через Страницу Жизни в его dna.json →
  resonance.trigger_keywords залип весь живой диалог Шефа с агентом
  (исповедь про мультики, 2007 год, "раз-два хитрый промт" и т.д.) —
  44 элемента, ~4600 символов. Это поле уходит в контекст агента на
  каждом прогоне как "триггерные слова" → Морж получает в голову личную
  историю Шефа вместо своей рыночной линзы. Видно даже в Кабинете.

ЧТО ДЕЛАЕТ
  Заменяет trigger_keywords на 4 чистых триггера (как задумано — одна
  осмысленная линза, по образцу Ганса/Архивариуса). pull_vector и
  hidden_taste НЕ трогает — они родились чистыми.

ЗАТРАГИВАЕТ ТОЛЬКО A02. Остальные восемь агентов цеха не касается.

БЕЗОПАСНОСТЬ
  · бэкап dna.json рядом (.bak_YYYYMMDD_HHMMSS) перед записью
  · идемпотентность: если уже чисто — выходит без изменений
  · sanity-чек: файл должен быть именно Моржом (id 152_MORJ)
  · ничего не пишет, если структура неожиданная — только сообщает

ЗАПУСК (из корня репы, рядом со studio/):
  python patch_clean_morj_dna.py
"""

import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

# ── Путь к dna.json Моржа ─────────────────────────────────────────────────
DNA_PATH = Path("studio/modules/trading/A02/dna.json")

# ── Чистые триггеры — рыночная линза Моржа (VETO, Хранитель Контекста) ─────
CLEAN_TRIGGERS = [
    "«Не спеши».",
    "«Посмотри ещё бар».",
    "«Структура есть».",
    "«Тишина».",
]


def fail(msg: str) -> None:
    print(f"❌ {msg}")
    sys.exit(1)


def main() -> None:
    print("─" * 70)
    print("🧹 ЧИСТКА trigger_keywords у Моржа (A02)")
    print("─" * 70)

    if not DNA_PATH.exists():
        fail(f"Не нашёл {DNA_PATH}. Запусти из корня репы (рядом со studio/).")

    # ── Читаем ────────────────────────────────────────────────────────────
    try:
        with DNA_PATH.open(encoding="utf-8") as f:
            dna = json.load(f)
    except Exception as e:
        fail(f"Не смог прочитать JSON: {e}")

    # ── Sanity: это точно Морж? ────────────────────────────────────────────
    agent_id = dna.get("id", "")
    if agent_id != "152_MORJ":
        fail(f"Это не Морж (id={agent_id!r}, ждал '152_MORJ'). Ничего не трогаю.")

    res = dna.get("resonance")
    if not isinstance(res, dict) or "trigger_keywords" not in res:
        fail("Нет resonance.trigger_keywords — структура неожиданная, не трогаю.")

    old = res["trigger_keywords"]
    old_count = len(old) if isinstance(old, list) else 0
    old_chars = sum(len(s) for s in old) if isinstance(old, list) else len(str(old))

    # ── Идемпотентность: уже чисто? ────────────────────────────────────────
    if old == CLEAN_TRIGGERS:
        print("✅ Уже чисто — trigger_keywords ровно 4 триггера. Выхожу без изменений.")
        return

    print(f"📊 Было: {old_count} элементов, {old_chars} символов (грязь от диалога рождения)")
    print(f"📊 Станет: {len(CLEAN_TRIGGERS)} чистых триггера")

    # ── Бэкап ──────────────────────────────────────────────────────────────
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = DNA_PATH.with_suffix(f".json.bak_{ts}")
    shutil.copy2(DNA_PATH, backup)
    print(f"💾 Бэкап: {backup}")

    # ── Чистим (только это поле) ────────────────────────────────────────────
    res["trigger_keywords"] = CLEAN_TRIGGERS

    # ── Пишем обратно (тот же отступ 2, кириллица как есть) ─────────────────
    with DNA_PATH.open("w", encoding="utf-8") as f:
        json.dump(dna, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print("✅ Готово. trigger_keywords очищен:")
    for t in CLEAN_TRIGGERS:
        print(f"   · {t}")
    print()
    print("ℹ️  pull_vector и hidden_taste не тронуты — они родились чистыми.")
    print("ℹ️  Если что не так — бэкап рядом, откатишь.")
    print("─" * 70)


if __name__ == "__main__":
    main()
