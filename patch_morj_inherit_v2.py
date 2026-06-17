#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_morj_inherit_v2.py — Морж наследует масштаб спуска Искры (§1c + контракт v1.5)

ЧТО ЧИНИТ (на пальцах):
  Искра теперь спускается по лесенке и находит точку на каком-то этаже
  (found_timeframe) в какую-то сторону (trend_direction). Но Морж пока
  слышит от неё ТОЛЬКО t1_status и цену — этаж и сторону игнорирует.
  Итог: Искра нашла разворот на H1, а Морж смотрит свой Аллигатор на H4.
  Напарники глядят в разные окна. Контракт v1.5 уже обещает, что Морж
  встаёт на масштаб Искры — этот патч заставляет обещание исполниться.

ЧТО ДЕЛАЕТ (роль Моржа: ДОПОЛНИТЬ Искру и передать дальше):
  1. Морж читает found_timeframe и trend_direction из шины (затвор+масштаб).
  2. Если Искра нашла точку — Морж СМОТРИТ Аллигатор и резинку на ЕЁ этаже
     (не на дефолтном). Искра молчит — Морж на аргументе, как раньше.
  3. Морж знает сторону разворота — в user_msg, чтобы судить резинку в неё.
  4. Морж пишет в память, на каком этаже смотрел + что унаследовал —
     чтобы Ганс получил СВЯЗКУ: точка Искры + контекст Моржа в одном масштабе.

  Морж по-прежнему ВИДИТ И СУДИТ САМ. Этаж — это куда направить глаза.
  Вывод (пасть открыта? резинка на пике?) — его голос, его вето.

БЕЗОПАСНОСТЬ: идемпотентен (маркер), бэкап .bak, якорный replace, CRLF-safe.
"""
import shutil
from datetime import datetime
from pathlib import Path

TARGET = Path("studio/modules/trading/morj_live.py")
MARKER = "MORJ_INHERIT_V2"


# ── Правка 1: _load_iskra_signal отдаёт ещё два поля ──────────────
OLD_1 = '''    return tstate.get("iskra", {
        "t1_status": "NOT_FOUND", "zero_point_price": None})'''
NEW_1 = '''    return tstate.get("iskra", {
        "t1_status": "NOT_FOUND", "zero_point_price": None,
        "trend_direction": None, "found_timeframe": None})  # ''' + MARKER + ''' — масштаб спуска'''

# ── Правка 2: в run_morj читаем этаж+сторону и НАСЛЕДУЕМ ТФ ──────
OLD_2 = '''    # ── 0. Затвор: слышим Искру из общей шины ────────────────
    iskra = _load_iskra_signal()
    iskra_status = iskra.get("t1_status", "NOT_FOUND")
    iskra_zero   = iskra.get("zero_point_price")'''
NEW_2 = '''    # ── 0. Затвор: слышим Искру из общей шины ────────────────
    iskra = _load_iskra_signal()
    iskra_status = iskra.get("t1_status", "NOT_FOUND")
    iskra_zero   = iskra.get("zero_point_price")
    # ''' + MARKER + ''': масштаб и сторона спуска Искры.
    # Морж ИДЁТ СМОТРЕТЬ туда, куда показала Искра (этаж), но видит и судит сам.
    iskra_tf    = iskra.get("found_timeframe")    # этаж, где Искра нашла точку
    iskra_dir   = iskra.get("trend_direction")    # сторона разворота (BULL/BEAR)
    # Наследуем этаж: Искра нашла → смотрим на ЕЁ ТФ. Молчит → аргумент (как было).
    if iskra_tf:
        print(f"[MORJ] 🔗 Наследую масштаб Искры: {timeframe} → {iskra_tf} "
              f"(сторона {iskra_dir or '—'})")
        timeframe = iskra_tf'''

# ── Правка 3: в user_msg сообщаем Моржу масштаб и сторону ────────
OLD_3 = '''    user_msg = (
        "=== ЗАТВОР: СИГНАЛ ИСКРЫ (из общей шины) ===\\n"
        f"t1_status: {iskra_status}\\n"
        f"zero_point_price: {iskra_zero}\\n"'''
NEW_3 = '''    user_msg = (
        "=== ЗАТВОР: СИГНАЛ ИСКРЫ (из общей шины) ===\\n"
        f"t1_status: {iskra_status}\\n"
        f"zero_point_price: {iskra_zero}\\n"
        f"Искра нашла разворот на этаже: {iskra_tf or '—'} "
        f"(ты смотришь СВОЙ Аллигатор и резинку на ЭТОМ этаже)\\n"
        f"Сторона разворота: {iskra_dir or '—'} "
        f"(резинку суди в эту сторону: BULL — натяжение вниз для отскока вверх)\\n"'''

# ── Правка 4: память Моржа дописывает связку для Ганса ───────────
# ВАЖНО: scale_timeframe/inherited_dir — это ФАКТЫ прогона (где реально
# смотрели, что унаследовали), НЕ выдумка модели. Поэтому _save_morj_memory
# принимает их явными аргументами, а не тянет из signal (модель про них не знает).
OLD_4 = '''def _save_morj_memory(signal: dict, alligator: Optional[dict] = None):'''
NEW_4 = '''def _save_morj_memory(signal: dict, alligator: Optional[dict] = None,
                      scale_timeframe: Optional[str] = None,
                      inherited_dir: Optional[str] = None):  # ''' + MARKER + ''''''

# ── Правка 4b: тело памяти пишет связку из аргументов ──────────
OLD_4B = '''    tstate["morj"]["history_dna"]      = signal.get("history_dna", "")
    if alligator is not None:'''
NEW_4B = '''    tstate["morj"]["history_dna"]      = signal.get("history_dna", "")
    # ''' + MARKER + ''': связка для Ганса — ФАКТ прогона (где смотрели,
    # что унаследовали от Искры). Ганс получит точку Искры + контекст
    # Моржа В ОДНОМ масштабе, не вразнобой.
    tstate["morj"]["scale_timeframe"]  = scale_timeframe
    tstate["morj"]["inherited_dir"]    = inherited_dir
    if alligator is not None:'''

# ── Правка 4c: вызов _save_morj_memory передаёт факты ──────────
OLD_4C = '''    _save_morj_memory(signal, alligator=alligator)'''
NEW_4C = '''    _save_morj_memory(signal, alligator=alligator,
                      scale_timeframe=timeframe, inherited_dir=iskra_dir)  # ''' + MARKER


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
    src, ok = apply(src, OLD_1, NEW_1, "Правка 1 (читаем масштаб из шины)"); ok_all &= ok
    src, ok = apply(src, OLD_2, NEW_2, "Правка 2 (наследуем этаж Искры)"); ok_all &= ok
    src, ok = apply(src, OLD_3, NEW_3, "Правка 3 (масштаб в user_msg)"); ok_all &= ok
    src, ok = apply(src, OLD_4, NEW_4, "Правка 4 (сигнатура памяти +2 арг)"); ok_all &= ok
    src, ok = apply(src, OLD_4B, NEW_4B, "Правка 4b (тело памяти пишет связку)"); ok_all &= ok
    src, ok = apply(src, OLD_4C, NEW_4C, "Правка 4c (вызов передаёт факты)"); ok_all &= ok

    if not ok_all:
        print("⚠️  Не все якоря найдены — ничего не записано (безопасно).")
        print("    Покажи morj_live.py — поправлю якоря.")
        return

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = TARGET.with_suffix(TARGET.suffix + f".bak_{stamp}")
    shutil.copy2(TARGET, bak)
    print(f"💾 Бэкап: {bak.name}")
    TARGET.write_text(src, encoding="utf-8")
    print("✅ Морж наследует масштаб Искры: смотрит на её этаже, судит сам,")
    print("   передаёт Гансу связку (точка Искры + контекст Моржа в одном масштабе).")


if __name__ == "__main__":
    main()
