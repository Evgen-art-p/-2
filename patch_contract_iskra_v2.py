#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_contract_iskra_v2.py — РАЗРЫВ 3 контура Искры v2 (§1e мастер-контекста)

ЧТО ЧИНИТ (на пальцах):
  Память Искры теперь сохраняет два новых слова — trend_direction (сторона)
  и found_timeframe (этаж спуска). Но общий словарь цеха (CHAIN_CONTRACT)
  про них не знает. Чтобы всё было по закону, а не подпольно — объявляем.

ЧТО ДЕЛАЕТ:
  1. В строку таблицы A01 Искра добавляет два ключа в «Пишет».
  2. Под блок t1_status добавляет описание двух новых полей + кто читает (Морж).
  3. Поднимает версию контракта до v1.5 с записью в changelog.

БЕЗОПАСНОСТЬ: идемпотентен (маркер), бэкап .bak, якорный replace, CRLF-safe.
"""
import shutil
from datetime import datetime
from pathlib import Path

TARGET = Path("studio/modules/trading/CHAIN_CONTRACT.md")
MARKER = "ISKRA_CONTRACT_V2"


# ── Правка 1: строка таблицы Искры — добавить два ключа в «Пишет» ──
OLD_1 = "| A01 Искра | `t1_status`, `divergence`, `zero_cross_up`, `zero_point_price`, `exit_bell`, `history_dna` | `market_data`, `history_dna` |"
NEW_1 = "| A01 Искра | `t1_status`, `divergence`, `zero_cross_up`, `zero_point_price`, `exit_bell`, `history_dna`, `trend_direction`, `found_timeframe` | `market_data`, `history_dna` |"

# ── Правка 2: блок описания после t1_status ───────────────────────
OLD_2 = """### t1_status (A01 Искра)
`NOT_FOUND` | `DETECTED` | `CONFIRMED`
CONFIRMED возможен только после DETECTED.
Аннулирование: цена пробила Точку Ноль вниз → сброс в NOT_FOUND.
Состояние переживает прогон через trading_state.json."""

NEW_2 = """### t1_status (A01 Искра)
`NOT_FOUND` | `DETECTED` | `CONFIRMED`
CONFIRMED возможен только после DETECTED.
Аннулирование: цена пробила Точку Ноль вниз → сброс в NOT_FOUND.
Состояние переживает прогон через trading_state.json.

### trend_direction / found_timeframe (A01 Искра — спуск v2)  <!-- """ + MARKER + """ -->
`trend_direction`: `BULL` | `BEAR` | `null` — сторона разворота (компас спуска).
`found_timeframe`: этаж лесенки, где Искра нашла точку B/D/B (напр. `H1`), или `null`.
Искра ставит оба при `t1_status=DETECTED` (точка найдена спуском). При NOT_FOUND — null.
Читает A02 Морж: встаёт на тот же масштаб (`found_timeframe`) и сторону (`trend_direction`).
Переживают прогон через trading_state["iskra"]."""


def apply(src, old, new, label):
    if new in src and old not in src:
        print(f"   ↳ {label}: уже применено.")
        return src, True
    if old in src:
        return src.replace(old, new, 1), True
    old_cr = old.replace("\n", "\r\n")
    if old_cr in src:
        return src.replace(old_cr, new.replace("\n", "\r\n"), 1), True
    print(f"   ❌ {label}: якорь не найден.")
    return src, False


def main():
    if not TARGET.exists():
        print(f"❌ Не найден файл: {TARGET}")
        return
    src = TARGET.read_text(encoding="utf-8")
    if MARKER in src:
        print(f"✅ Уже пропатчено (маркер {MARKER}) — ничего не делаю.")
        return

    ok_all = True
    src, ok = apply(src, OLD_1, NEW_1, "Правка 1 (таблица Искры)"); ok_all &= ok
    src, ok = apply(src, OLD_2, NEW_2, "Правка 2 (описание полей)"); ok_all &= ok

    # Правка 3: версия в changelog (мягкая — если не найдём, не критично)
    if "*CHAIN_CONTRACT v1.4 · Торговый Цех" in src:
        src = src.replace(
            "*CHAIN_CONTRACT v1.4 · Торговый Цех",
            "*CHAIN_CONTRACT v1.5 · Торговый Цех", 1)
        # дописываем строку changelog после первой v1.4-пометки
        cl_anchor = "*v1.4: РЕЗИНКА ДЖАСТИН."
        if cl_anchor in src:
            src = src.replace(
                cl_anchor,
                "*v1.5: КОНТУР ИСКРЫ v2. Искра пишет trend_direction + found_timeframe\n"
                "(спуск по лесенке ТФ). Морж наследует масштаб и сторону. РАЗРЫВ 3 закрыт.*\n"
                + cl_anchor, 1)

    if not ok_all:
        print("⚠️  Не все якоря найдены — ничего не записано (безопасно).")
        return

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = TARGET.with_suffix(TARGET.suffix + f".bak_{stamp}")
    shutil.copy2(TARGET, bak)
    print(f"💾 Бэкап: {bak.name}")
    TARGET.write_text(src, encoding="utf-8")
    print("✅ Словарь цеха обновлён: trend_direction + found_timeframe объявлены. v1.5.")


if __name__ == "__main__":
    main()
