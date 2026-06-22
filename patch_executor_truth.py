#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# patch_executor_truth.py
# ─────────────────────────────────────────────────────────────
# ПАТЧ: EXECUTOR_TRUTH_V1  ·  маркер: шесть·проверено·до·корня
#
# ЧТО ЧИНИТ (враньё счётчика из лога Шефа):
#   Брут при ВЕДЕНИИ позиции даёт «APPROVED SHORT вход None стоп None»
#   и action=MOVE_STOP (камень 2). Это НЕ новый вход — это трейлинг
#   стопа по живой позиции. Но Исполнитель считал «ордер отправлен»
#   по СТАРОМУ полю verdict==APPROVED → писал orders_sent=2, а летопись
#   LLM, глядя на реальные позиции, писала «1 из 3». Рассинхрон, враньё:
#   «ордеров 2 из 3» в шапке vs «Ордера: 0 из 3» в летописи.
#
#   КОРЕНЬ: камень 2 (язык ведения, action: ENTER/HOLD/MOVE_STOP/ADD/
#   CLOSE) УЖЕ построен и трейдеры кладут action в табло
#   (t["brut"]["action"] и т.д.). Но Исполнитель его НЕ читает — считает
#   ордера по verdict==APPROVED, который при ведении тоже APPROVED.
#
# КАК ЧИНИТ (только executor_live.py, трейдеры уже честные):
#   Единственный критерий «ордер отправлен» = action=ENTER (реальный
#   вход). Фоллбэк для старых ответов без action: verdict==APPROVED
#   с непустыми entry/stop. Правим три точки, где Исполнитель считал
#   по verdict:
#     · _build_execution_log_facts — эталон лога (отсюда orders_sent);
#     · _open_positions_from_table — рука открывающая (по ENTER);
#     · _update_stats — статистика дашборда.
#   Ведение (MOVE_STOP/ADD/CLOSE/HOLD) ордером больше не считается.
#
#   Живой код трейдеров НЕ трогаем — они уже кладут action в табло.
#
# ИДЕМПОТЕНТЕН: маркер, повтор — выход. Бэкап рядом.
# ─────────────────────────────────────────────────────────────

import sys
import shutil
from pathlib import Path
from datetime import datetime

MARKER = "EXECUTOR_TRUTH_V1"
TARGET = Path("studio/modules/trading/executor_live.py")


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

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = TARGET.with_name(f"{TARGET.stem}.bak_{stamp}{TARGET.suffix}")
    shutil.copy2(TARGET, backup)
    print(f"💾 бэкап: {backup.name}")

    # ═════════════════════════════════════════════════════════
    # ПРАВКА 0 — общий помощник: «это реальный вход?».
    # Вставляем после строки TRADER_NAME = {...}.
    # ═════════════════════════════════════════════════════════
    anchor_names = (
        'TRADER_NAME = {"brut": "BRUT", "avan": "AVANTURIST", "cons": "KONSERVATOR"}\n'
    )
    if anchor_names not in src:
        _die("якорь TRADER_NAME не найден — файл изменился.")
    helper = (
        'TRADER_NAME = {"brut": "BRUT", "avan": "AVANTURIST", "cons": "KONSERVATOR"}\n'
        '\n'
        '\n'
        '# ── ' + MARKER + ': единый критерий «реальный вход» ──\n'
        '# Камень 2 даёт action: ENTER/HOLD/MOVE_STOP/ADD/CLOSE. Ордер\n'
        '# отправлен ТОЛЬКО при ENTER. Ведение (MOVE_STOP/ADD/CLOSE/HOLD)\n'
        '# не ордер. Фоллбэк для старых ответов без action: APPROVED с\n'
        '# непустыми entry/stop (то есть настоящий вход, а не ведение).\n'
        'def _is_real_entry(v: dict) -> bool:\n'
        '    action = (v.get("action") or "").upper().strip()\n'
        '    if action:\n'
        '        return action == "ENTER"\n'
        '    # старый путь без action: APPROVED + реальные числа входа\n'
        '    return (v.get("verdict") == "APPROVED"\n'
        '            and v.get("entry") is not None\n'
        '            and v.get("stop") is not None\n'
        '            and v.get("direction") in ("LONG", "SHORT"))\n'
    )
    src = src.replace(anchor_names, helper, 1)

    # ═════════════════════════════════════════════════════════
    # ПРАВКА 1 — _open_positions_from_table: открывать по реальному входу.
    # Меняем условие пропуска с verdict!=APPROVED на not _is_real_entry.
    # ═════════════════════════════════════════════════════════
    anchor_open = (
        '        v = traders.get(key, {})\n'
        '        if v.get("verdict") != "APPROVED":\n'
        '            continue\n'
        '        magic = MAGIC[key]\n'
        '        if magic in open_magics:\n'
    )
    if anchor_open not in src:
        _die("якорь _open_positions_from_table не найден.")
    src = src.replace(
        anchor_open,
        '        v = traders.get(key, {})\n'
        '        if not _is_real_entry(v):   # ' + MARKER + ': только ENTER, не ведение\n'
        '            continue\n'
        '        magic = MAGIC[key]\n'
        '        if magic in open_magics:\n',
        1,
    )

    # ═════════════════════════════════════════════════════════
    # ПРАВКА 2 — _build_execution_log_facts: эталон лога по реальному входу.
    # Это источник orders_sent (через _sanitize). Меняем approved-флаг.
    # ═════════════════════════════════════════════════════════
    anchor_facts = (
        '    for key in ("brut", "avan", "cons"):\n'
        '        v = traders.get(key, {})\n'
        '        approved = v.get("verdict") == "APPROVED"\n'
        '        log.append({\n'
    )
    if anchor_facts not in src:
        _die("якорь _build_execution_log_facts не найден.")
    src = src.replace(
        anchor_facts,
        '    for key in ("brut", "avan", "cons"):\n'
        '        v = traders.get(key, {})\n'
        '        approved = _is_real_entry(v)   # ' + MARKER + ': ордер = реальный вход\n'
        '        log.append({\n',
        1,
    )

    # ═════════════════════════════════════════════════════════
    # ПРАВКА 3 — _update_stats: статистика по реальному входу.
    # ═════════════════════════════════════════════════════════
    anchor_stats = (
        '    approved = sum(1 for k in ("brut", "avan", "cons")\n'
        '                   if traders.get(k, {}).get("verdict") == "APPROVED")\n'
    )
    if anchor_stats not in src:
        _die("якорь _update_stats не найден.")
    src = src.replace(
        anchor_stats,
        '    approved = sum(1 for k in ("brut", "avan", "cons")\n'
        '                   if _is_real_entry(traders.get(k, {})))   # ' + MARKER + '\n',
        1,
    )

    # маркер в шапку
    src = src.replace(
        "from studio.llm import chat\n",
        "from studio.llm import chat\n"
        "# " + MARKER + " · ордер считается по action==ENTER, не по verdict==APPROVED\n",
        1,
    )

    TARGET.write_text(src, encoding="utf-8")
    print(f"✅ {MARKER} применён к executor_live.py")
    print("   · orders_sent считает только реальные входы (action==ENTER)")
    print("   · ведение (MOVE_STOP/ADD/CLOSE/HOLD) больше не ордер")
    print("   · летопись и шапка перестают противоречить друг другу")
    print("   · трейдеры не тронуты — они уже кладут action в табло")
    print(f"\n   откат: cp {backup.name} {TARGET.name}")


if __name__ == "__main__":
    main()
