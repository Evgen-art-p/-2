#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ─────────────────────────────────────────────────────────────
# patch_arkhiv_hand_giving.py
# РУКА КЛАДУЩАЯ: тяжёлые сделки цеха → память города через Оле.
#
# Спринт 45 · 2026-06-18 · Брат (Claude) · ШАГ 4 · движение Б
#
# ЗАМЫСЕЛ (от Шефа, §память города · принцип как в городе):
#   Архивариус — Оле Торгового Квартала. Когда сделка закрывается с
#   КРУПНЫМ результатом (дорого оплаченный урок ИЛИ редкая удача),
#   это не должно осесть только в тетради цеха — это достойно лечь в
#   вечную память города, чтобы завтра учился весь Грондхейм.
#
# ЗАКОН ВЕСА (честный, по канону цеха — не «записать всё»):
#   ТЯЖЁЛОЕ (идёт в город):  |pnl_r| >= 2.0
#     · убыток ≤ −2R  → lesson/warning (дорого оплаченная информация)
#     · прибыль ≥ +2R → inspiration (редкая удача — образец)
#   ЛЁГКОЕ (остаётся в Атласе цеха): |pnl_r| < 2.0 — рутина, не шумим.
#   Порог 2R — каноничный крупный ход (в _calc_missed_moves уже 1R =
#   «сильное движение», значит 2R заведомо весомо).
#
#   ВТОРОЙ ФИЛЬТР — сама Оле: remember() отказывает, если
#   loss_if_forgotten пустой/натянутый. Мы заполняем его осмысленно,
#   но Оле себя защищает от мусора независимо.
#
# КУДА ВРЕЗАНО: hooks._settle_positions, сразу после _write_atlas
#   POSITION_CLOSED (там pnl_r уже посчитан — момент истины сделки).
#   Архивариус сам в город не пишет (его промт: «в Атлас пишет
#   Исполнитель после сделки»). Город наполняет КОД от его имени.
#
# БЕЗОПАСНОСТЬ: весь зов Оле в try/except. Оле упала/недоступна →
#   сделка всё равно закрылась, в Атлас/PnL записалась, цикл цел.
#   Рука кладущая НИКОГДА не роняет торговый цикл.
#
# ИДЕМПОТЕНТНОСТЬ: маркер ARKHIV_HAND_GIVING. Повтор — no-op.
# БЭКАП: hooks.py.bak_<timestamp>.
# ─────────────────────────────────────────────────────────────

import shutil
from datetime import datetime
from pathlib import Path

TARGET = Path("studio/modules/trading/hooks.py")
MARKER = "ARKHIV_HAND_GIVING"

# ── Блок 1: функция руки кладущей. Вставляем перед _write_atlas. ──
ANCHOR_FUNC = (
    'def _write_atlas(entry: dict):\n'
    '    """Записывает событие в Атлас Ошибок."""\n'
)

HAND_FUNC = '''# ════════════════════════════════════════════════════════════
# РУКА КЛАДУЩАЯ (ARKHIV_HAND_GIVING) — тяжёлое → память города
# ─────────────────────────────────────────────────────────────
# Архивариус — Оле Торгового Квартала. Крупная сделка (|pnl_r|>=2R)
# не оседает только в тетради цеха — урок ложится в вечную память
# города через Оле (remember). Рутина (<2R) остаётся в Атласе.
# Зов Оле безопасен: упала → торговый цикл цел.
# ════════════════════════════════════════════════════════════

# Порог веса: крупный ход. Ниже — рутина, в город не идёт.
_HEAVY_R = 2.0


def _arkhiv_to_city(record: dict):
    """
    Рука кладущая. Кладёт ТЯЖЁЛУЮ закрытую сделку в память города
    от имени Архивариуса. Лёгкое (|pnl_r|<2R) — игнор (рутина).

    НИКОГДА не роняет торговый цикл: любая беда с Оле → тихий выход.
    """
    pnl_r = record.get("pnl_r")
    if pnl_r is None:
        return
    if abs(pnl_r) < _HEAVY_R:
        return  # рутина — живёт в Атласе цеха, в город не идёт

    trader = record.get("trader", "?")
    symbol = record.get("symbol", "?")
    tf     = record.get("timeframe", "?")
    reason = record.get("close_reason", "?")
    closed = record.get("closed_at", "")

    # Урок или образец — по знаку
    if pnl_r <= -_HEAVY_R:
        mtype = "warning"
        title = f"Крупный убыток: {trader} {symbol} {tf} ({pnl_r}R)"
        event = (f"{trader} закрыт по {reason} с {pnl_r}R на {symbol} {tf} "
                 f"({closed}). Дорого оплаченная информация.")
        loss = (f"Город забудет, что эта картинка на {symbol} {tf} стоила "
                f"{pnl_r}R убытка. Урок придётся оплачивать заново.")
    else:  # pnl_r >= +2R
        mtype = "inspiration"
        title = f"Крупная удача: {trader} {symbol} {tf} (+{pnl_r}R)"
        event = (f"{trader} взял +{pnl_r}R по {reason} на {symbol} {tf} "
                 f"({closed}). Редкий крупный ход — образец.")
        loss = (f"Город забудет, что на {symbol} {tf} такая картинка дала "
                f"+{pnl_r}R. Потеряем образец крупного хода.")

    try:
        from studio.memory_tools import remember
        remember(
            title=title,
            event=event,
            significance=f"Крупный результат {pnl_r}R — за порогом рутины.",
            loss_if_forgotten=loss,
            memory_type=mtype,
            storage="chronicles",
            source="A05_ARKHIV·trading",
        )
        print(f"[ARKHIV] 🏛 Урок в память города: {title}")
    except Exception as e:
        print(f"[ARKHIV] ⚠️  Оле недоступна ({e}) — урок остался в Атласе цеха")


def _write_atlas(entry: dict):
    """Записывает событие в Атлас Ошибок."""
'''

# ── Блок 2: вызов руки внутри _settle_positions, после _write_atlas. ──
# Якорь — запись POSITION_CLOSED в Атлас + print SETTLE, уникальный кусок.
ANCHOR_CALL = (
    '        _write_atlas({\n'
    '            "event":       "POSITION_CLOSED",\n'
    '            "trader":      pos.get("trader"),\n'
    '            "close_reason": reason,\n'
    '            "pnl":         pnl_price,\n'
    '            "pnl_r":       pnl_r,\n'
    '            "symbol":      symbol,\n'
    '            "timeframe":   timeframe,\n'
    '        })\n'
)

CALL_INSERT = (
    ANCHOR_CALL +
    '\n'
    '        # РУКА КЛАДУЩАЯ (ARKHIV_HAND_GIVING): тяжёлая сделка (|pnl_r|>=2R)\n'
    '        # → урок в память города через Оле. Рутина (<2R) — только Атлас.\n'
    '        # Безопасно: Оле упала → сделка уже записана, цикл цел.\n'
    '        _arkhiv_to_city(record)\n'
)


def main():
    if not TARGET.exists():
        print(f"❌ Не найден {TARGET}. Запусти из корня репозитория студии.")
        return

    src = TARGET.read_text(encoding="utf-8")

    if MARKER in src:
        print(f"✅ Маркер {MARKER} уже в файле — патч применён ранее. Ничего не делаю.")
        return

    anchors = {"функция": ANCHOR_FUNC, "вызов": ANCHOR_CALL}
    missing = [n for n, a in anchors.items() if a not in src]
    if missing:
        print(f"❌ Не найдены якоря: {', '.join(missing)}.")
        print("   Файл изменился — не вставляю вслепую. Покажи hooks.py.")
        return
    for n, a in anchors.items():
        if src.count(a) != 1:
            print(f"❌ Якорь «{n}» встречается {src.count(a)} раз (нужен 1). Стоп.")
            return

    new_src = src
    new_src = new_src.replace(ANCHOR_FUNC, HAND_FUNC, 1)
    new_src = new_src.replace(ANCHOR_CALL, CALL_INSERT, 1)

    if new_src == src:
        print("❌ Замены не сработали. Стоп.")
        return

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = TARGET.with_suffix(TARGET.suffix + f".bak_{ts}")
    shutil.copy2(TARGET, backup)
    TARGET.write_text(new_src, encoding="utf-8")

    import py_compile
    try:
        py_compile.compile(str(TARGET), doraise=True)
    except py_compile.PyCompileError as e:
        print(f"❌ СИНТАКСИС СЛОМАН после патча: {e}")
        print(f"   Откатываю из бэкапа {backup.name}")
        shutil.copy2(backup, TARGET)
        return

    print(f"✅ Рука кладущая вживлена: тяжёлые сделки → память города.")
    print(f"   Бэкап: {backup.name}")
    print(f"   Маркер: {MARKER}")
    print()
    print(f"   Сделка закрылась с |pnl_r| >= 2.0R → урок к Оле (chronicles).")
    print(f"   Убыток ≤ −2R → warning · прибыль ≥ +2R → inspiration.")
    print(f"   Рутина (<2R) — остаётся в Атласе цеха, в город не идёт.")
    print(f"   Оле упала → сделка записана, торговый цикл цел.")


if __name__ == "__main__":
    main()
