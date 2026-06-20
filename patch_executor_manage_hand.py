#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ─────────────────────────────────────────────────────────────
# ПАТЧ: КАМЕНЬ 3 — РУКА ВЕДУЩАЯ (Исполнитель исполняет ведение)
# Маркер: EXECUTOR_MANAGE_HAND_V1
# Дата: 2026-06-20 · Брат (Claude) + Шеф
#
# ЗАКОН (Шеф): трейдер решает — Исполнитель исполняет. Защита чисел:
# действие и числа ведения — подпись трейдера в табло (action/new_stop/
# add_lot, камень 2). Рука ведущая — КОД, исполняет буквально, не судит,
# не считает за трейдера. LLM-летопись физики не касается.
#
# ЧТО ДЕЛАЕТ. У Исполнителя была одна рука — ОТКРЫВАЮЩАЯ (ENTER→позиция).
# Камень 3 добавляет рядом руку ВЕДУЩУЮ: читает action каждого трейдера
# из табло и меняет его ОТКРЫТУЮ позицию в trading_state["positions"]:
#   HOLD       — ничего (трейдер держит)
#   MOVE_STOP  — двигает stop позиции на trader.new_stop
#   ADD        — увеличивает lot позиции на trader.add_lot (пирамида);
#                вход не усредняем на этом камне (отдельная честная
#                задача) — наращиваем объём, стоп трейдер двигает сам
#                отдельным MOVE_STOP. Защита: не даём перевернуть риск.
#   CLOSE      — помечает позицию к закрытию ВОЛЕЙ трейдера; физическое
#                закрытие с PnL делает _settle на след. баре по close.
#   ENTER/WAIT — не ведение (открытие/пас), рука ведущая их не трогает.
#
# КАК НАХОДИТ позицию трейдера: по магику (BRUT/AVAN/CONS), как рука
# открывающая. Нет открытой позиции у трейдера → действие ведения
# игнорируется (вести нечего).
#
# CLOSE через _settle: чтобы закрытие шло ЕДИНОЙ физикой и формулой R
# (один источник правды), рука ведущая не считает PnL сама. Она ставит
# позиции флаг manual_close=True, а _settle_positions закрывает её на
# текущем баре по close с reason="MANUAL_CLOSE". Так PnL/Атлас/память
# города идут тем же путём, что стоп и колокол. Ноль дублирования.
#
# ДВА КАСАНИЯ:
#   1. executor_live.py — рука ведущая _manage_positions_from_table,
#      вызов после руки открывающей в run_executor.
#   2. hooks.py — _settle_positions распознаёт manual_close и закрывает
#      волей трейдера (наряду со стопом и колоколом).
#
# ИДЕМПОТЕНТНО: маркер, бэкап, py_compile. Запуск из корня репы:
#   python patch_executor_manage_hand.py
# ─────────────────────────────────────────────────────────────

import sys
import shutil
import py_compile
from datetime import datetime
from pathlib import Path

MARKER = "EXECUTOR_MANAGE_HAND_V1"
ROOT = Path.cwd()
TRADING = ROOT / "studio" / "modules" / "trading"
EXEC = TRADING / "executor_live.py"
HOOKS = TRADING / "hooks.py"


def _fail(msg: str):
    print(f"❌ {msg}")
    sys.exit(1)


def _backup(path: Path):
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = path.with_name(f"{path.name}.bak_{stamp}")
    shutil.copy2(path, bak)
    print(f"   💾 бэкап: {bak.name}")


def _check_root():
    if not TRADING.exists():
        _fail(f"Не вижу {TRADING}. Запускай из КОРНЯ репы (где папка studio/).")
    for p in (EXEC, HOOKS):
        if not p.exists():
            _fail(f"Не найден файл: {p}")


# ════════════════════════════════════════════════════════════
# КАСАНИЕ 1 — executor_live.py: рука ведущая
# ════════════════════════════════════════════════════════════

EXEC_HAND = '''
# ════════════════════════════════════════════════════════════
# РУКА ВЕДУЩАЯ (КОД) — исполняет ВЕДЕНИЕ по действию трейдера.  # EXECUTOR_MANAGE_HAND_V1
# ─────────────────────────────────────────────────────────────
# Трейдер назвал action (камень 2): HOLD/MOVE_STOP/ADD/CLOSE.
# Рука находит ЕГО открытую позицию по магику и исполняет буквально.
# Защита чисел: уровни/объёмы — подпись трейдера, не пересказ LLM.
# CLOSE не считает PnL — ставит флаг, _settle закроет единой физикой.
# ════════════════════════════════════════════════════════════

def _manage_positions_from_table(traders: dict) -> list:
    """
    Для каждого трейдера с открытой позицией исполняет его действие
    ведения над trading_state["positions"]. Возвращает список изменений
    (для летописи). Открытие (ENTER) — не здесь, это рука открывающая.
    """
    from studio.modules.trading.hooks import load_trading_state, save_trading_state
    tstate = load_trading_state()
    positions = tstate.get("positions", []) or []
    if not positions:
        return []

    changed = []
    dirty = False
    for key in ("brut", "avan", "cons"):
        v = traders.get(key, {})
        action = (v.get("action") or "").upper().strip()
        if action in ("", "ENTER", "WAIT", "HOLD"):
            # ENTER/WAIT — не ведение; HOLD — держит как есть, трогать нечего
            continue
        magic = MAGIC[key]
        # ищем ЕГО открытую позицию
        pos = next((p for p in positions
                    if p.get("magic") == magic and p.get("status") == "OPEN"), None)
        if not pos:
            continue  # вести нечего

        if action == "MOVE_STOP":
            ns = v.get("new_stop")
            if ns is None:
                continue
            old = pos.get("stop")
            pos["stop"] = ns
            dirty = True
            changed.append({"trader": TRADER_NAME[key], "action": "MOVE_STOP",
                            "from": old, "to": ns})

        elif action == "ADD":
            al = v.get("add_lot")
            if al is None or al <= 0:
                continue
            old_lot = pos.get("lot") or 0
            pos["lot"] = round(old_lot + al, 4)
            # вход не усредняем на этом камне — наращиваем объём;
            # стоп трейдер двигает отдельным MOVE_STOP, если хочет.
            pos.setdefault("pyramids", 0)
            pos["pyramids"] += 1
            dirty = True
            changed.append({"trader": TRADER_NAME[key], "action": "ADD",
                            "add_lot": al, "lot_now": pos["lot"]})

        elif action == "CLOSE":
            # волей трейдера — флаг, физику закрытия делает _settle (PnL/R).
            pos["manual_close"] = True
            dirty = True
            changed.append({"trader": TRADER_NAME[key], "action": "CLOSE"})

    if dirty:
        tstate["positions"] = positions
        save_trading_state(tstate)
    return changed


'''

EXEC_ANCHOR_FN = "def _open_positions_from_table(traders: dict, market: dict) -> list:"

# Вызов руки ведущей сразу после руки открывающей в run_executor.
EXEC_ANCHOR_CALL = "    opened = _open_positions_from_table(traders, market)\n"
EXEC_INSERT_CALL = (
    "    opened = _open_positions_from_table(traders, market)\n"
    "    # КАМЕНЬ 3: рука ведущая — исполняет HOLD/MOVE_STOP/ADD/CLOSE.  # EXECUTOR_MANAGE_HAND_V1\n"
    "    managed = _manage_positions_from_table(traders)\n"
    "    if managed:\n"
    "        print(f'[EXECUTOR] ✋ ведение: {managed}')\n"
)


def patch_executor() -> bool:
    src = EXEC.read_text(encoding="utf-8")
    if MARKER in src:
        print("✅ executor_live.py уже пропатчен — пропускаю.")
        return False

    if EXEC_ANCHOR_FN not in src:
        _fail("executor: не нашёл '_open_positions_from_table' — структура изменилась.")
    src = src.replace(EXEC_ANCHOR_FN, EXEC_HAND.lstrip("\n") + "\n" + EXEC_ANCHOR_FN, 1)

    if EXEC_ANCHOR_CALL not in src:
        _fail("executor: не нашёл вызов opened = _open_positions_from_table — структура изменилась.")
    src = src.replace(EXEC_ANCHOR_CALL, EXEC_INSERT_CALL, 1)

    _backup(EXEC)
    EXEC.write_text(src, encoding="utf-8")
    print("✅ executor_live.py пропатчен: рука ведущая _manage_positions_from_table.")
    return True


# ════════════════════════════════════════════════════════════
# КАСАНИЕ 2 — hooks.py: _settle закрывает по воле трейдера (manual_close)
# ════════════════════════════════════════════════════════════

# В _settle_positions распознаём manual_close ПЕРВЫМ (воля трейдера —
# раньше стопа и колокола). Закрытие по close, reason="MANUAL_CLOSE".
HOOKS_ANCHOR = (
    "        exit_price, reason = None, None\n"
    "        # Стоп — зеркально по направлению\n"
)
HOOKS_INSERT = (
    "        exit_price, reason = None, None\n"
    "        # КАМЕНЬ 3: воля трейдера (CLOSE) — раньше стопа и колокола.  # EXECUTOR_MANAGE_HAND_V1\n"
    "        if pos.get(\"manual_close\") and close is not None:\n"
    "            exit_price, reason = close, \"MANUAL_CLOSE\"\n"
    "        # Стоп — зеркально по направлению\n"
)

# Стоп/колокол проверяем только если воля трейдера не сработала.
# Заменяем 'if direction == \"LONG\" and low' на 'elif ...' чтобы manual_close
# имел приоритет. Аккуратно: только первое вхождение в _settle.
# Разрываем elif-цепочку: каждая ветка стопа/колокола проверяет reason is None,
# иначе manual_close на SHORT/колоколе перетирается стопом того же бара.
HOOKS_STOP_ANCHOR = (
    '        if direction == "LONG" and low is not None and low <= stop:\n'
    '            exit_price, reason = stop, "STOP_LOSS"\n'
    '        elif direction == "SHORT" and high is not None and high >= stop:\n'
    '            exit_price, reason = stop, "STOP_LOSS"\n'
    '        elif bell and close is not None:\n'
    '            exit_price, reason = close, "EXIT_BELL"\n'
)
HOOKS_STOP_INSERT = (
    '        if reason is None and direction == "LONG" and low is not None and low <= stop:\n'
    '            exit_price, reason = stop, "STOP_LOSS"\n'
    '        elif reason is None and direction == "SHORT" and high is not None and high >= stop:\n'
    '            exit_price, reason = stop, "STOP_LOSS"\n'
    '        elif reason is None and bell and close is not None:\n'
    '            exit_price, reason = close, "EXIT_BELL"\n'
)


def patch_hooks() -> bool:
    src = HOOKS.read_text(encoding="utf-8")
    if MARKER in src:
        print("✅ hooks.py уже пропатчен — пропускаю.")
        return False

    if HOOKS_ANCHOR not in src:
        _fail("hooks: не нашёл блок 'exit_price, reason = None' в _settle — структура изменилась.")
    src = src.replace(HOOKS_ANCHOR, HOOKS_INSERT, 1)

    if HOOKS_STOP_ANCHOR not in src:
        _fail("hooks: не нашёл проверку стопа LONG — структура изменилась.")
    src = src.replace(HOOKS_STOP_ANCHOR, HOOKS_STOP_INSERT, 1)

    _backup(HOOKS)
    HOOKS.write_text(src, encoding="utf-8")
    print("✅ hooks.py пропатчен: _settle закрывает по воле трейдера (MANUAL_CLOSE).")
    return True


def _verify_compiles():
    for p in (EXEC, HOOKS):
        try:
            py_compile.compile(str(p), doraise=True)
        except py_compile.PyCompileError as e:
            _fail(f"После патча {p.name} НЕ компилируется:\n{e}")
    print("🧪 Песочница: executor_live.py и hooks.py компилируются.")


def main():
    print("═" * 62)
    print("  КАМЕНЬ 3: РУКА ВЕДУЩАЯ (Исполнитель исполняет ведение)  ·", MARKER)
    print("═" * 62)
    _check_root()

    changed = False
    changed |= patch_executor()
    changed |= patch_hooks()

    if changed:
        _verify_compiles()
        print("─" * 62)
        print("✅ ГОТОВО. Рука Исполнителя обрела пальцы.")
        print("   MOVE_STOP двигает стоп · ADD доливает · CLOSE закрывает волей.")
        print("   Закрытие по воле — единой физикой _settle (PnL/R/Атлас/город).")
        print("   Трое теперь ВЕДУТ позицию бар за баром. Курсор-часы — камень 4.")
    else:
        print("─" * 62)
        print("ℹ️  Всё уже было пропатчено ранее — ничего не менял.")


if __name__ == "__main__":
    main()
