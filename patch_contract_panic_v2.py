#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_contract_panic_v2.py — контракт под нового Паникёра (структура толпы)

ЧТО ЧИНИТ (синхрон):
  Паникёр оживлён мотором panikyor_live.py + новым промтом. Он чует толпу
  СТРУКТУРОЙ (окна MFI, объём, спред), а не таблицей из статуса Искры.
  Фаз стало 6 (было 4). Контракт должен это отразить, иначе разъедется
  с промтом и мотором.

ЧТО ДЕЛАЕТ:
  1. panic_phase: 4 старых фазы → 6 новых (ASLEEP/DISBELIEF/GREED/TENSION/
     DECEPTION/PANIC). Новые связки с action_for_traders.
  2. Паникёр читает market_data.mfi (окна толпы) — добавляем в таблицу «Читает».
  3. Объявляем scale_timeframe (этаж, унаследованный от Искры) для Ганса.
  4. Версия контракта → v1.6, запись в changelog.

БЕЗОПАСНОСТЬ: идемпотентен (маркер), бэкап .bak, якорный replace, CRLF-safe.
"""
import shutil
from datetime import datetime
from pathlib import Path

TARGET = Path("studio/modules/trading/CHAIN_CONTRACT.md")
MARKER = "PANIC_CONTRACT_V2"


# ── Правка 1: строка таблицы Паникёра — добавить чтение mfi + scale ──
OLD_1 = "| A03 Паникёр | `panic_phase`, `crowd_sentiment`, `action_for_traders` | `market_data.price`, `t1_status`, `morj_status` |"
NEW_1 = "| A03 Паникёр | `panic_phase`, `crowd_sentiment`, `action_for_traders`, `scale_timeframe` | `market_data.mfi`, `market_data.price`, `t1_status`, `morj_status`, `found_timeframe` |"

# ── Правка 2: блок panic_phase — 6 фаз вместо 4 ──────────────
OLD_2 = """### panic_phase (A03 Паникёр)
`NEUTRAL` | `DISBELIEF` | `FOMO` | `LIQUIDATION`
Жёсткие связки: FOMO → HIGH_SKEPTICISM; LIQUIDATION → GREEN_LIGHT_IF_GANS;
NEUTRAL/DISBELIEF → NEUTRAL."""

NEW_2 = """### panic_phase (A03 Паникёр) — структура толпы  <!-- """ + MARKER + """ -->
`ASLEEP` | `DISBELIEF` | `GREED` | `TENSION` | `DECEPTION` | `PANIC`
Паникёр чует фазу САМ по структуре толпы (окна Profitunity MFI + объём + спред +
свечка), НЕ по таблице из статуса Искры. Привязка фаз к факту движка:
  ASLEEP    — FADE (объём↓ MFI↓) или morj SLEEPING — скука
  DISBELIEF — t1 DETECTED, объём вялый — недоверие
  GREED     — GREEN (объём↑ MFI↑) + бар бычий — жадность/FOMO
  TENSION   — SQUAT (объём↑ MFI↓) — истерика напряжения (пружина)
  DECEPTION — FAKE (MFI↑ объём↓) — обман/ложный пробой
  PANIC     — t1 CONFIRMED + бар медвежий + спред↑ — паника (точка боли Ганса)
Связки с action_for_traders:
  GREED / TENSION → HIGH_SKEPTICISM (толпа жадничает → Совет насторожен)
  PANIC → GREEN_LIGHT_IF_GANS (паника толпы = момент, если Ганс дал триггер)
  ASLEEP / DISBELIEF / DECEPTION → NEUTRAL (фон, ворота закрыты)

### scale_timeframe (A03 Паникёр + A02 Морж)
Этаж, на котором сенсор мерил (унаследован от Искры found_timeframe), или null.
Сенсоры идут смотреть туда, куда показала Искра. Ганс получит цепочку фактов
в ОДНОМ масштабе."""


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
    src, ok = apply(src, OLD_1, NEW_1, "Правка 1 (таблица Паникёра + mfi)"); ok_all &= ok
    src, ok = apply(src, OLD_2, NEW_2, "Правка 2 (6 фаз толпы)"); ok_all &= ok

    # Правка 3: версия (мягкая)
    for old_v, new_v in [
        ("*CHAIN_CONTRACT v1.5 · Торговый Цех", "*CHAIN_CONTRACT v1.6 · Торговый Цех"),
        ("*CHAIN_CONTRACT v1.4 · Торговый Цех", "*CHAIN_CONTRACT v1.6 · Торговый Цех"),
    ]:
        if old_v in src:
            src = src.replace(old_v, new_v, 1)
            break
    # changelog после любой свежей пометки
    for cl in ["*v1.5: КОНТУР ИСКРЫ v2.", "*v1.4: РЕЗИНКА ДЖАСТИН."]:
        if cl in src:
            src = src.replace(
                cl,
                "*v1.6: ПАНИКЁР ОЖИВЛЁН. 6 фаз толпы из структуры (окна MFI+объём+спред),\n"
                "не из таблицы статусов. Паникёр читает market_data.mfi. scale_timeframe.*\n"
                + cl, 1)
            break

    if not ok_all:
        print("⚠️  Не все якоря найдены — ничего не записано (безопасно).")
        return

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = TARGET.with_suffix(TARGET.suffix + f".bak_{stamp}")
    shutil.copy2(TARGET, bak)
    print(f"💾 Бэкап: {bak.name}")
    TARGET.write_text(src, encoding="utf-8")
    print("✅ Контракт v1.6: 6 фаз толпы, Паникёр читает структуру (mfi). Синхрон с промтом+мотором.")


if __name__ == "__main__":
    main()
