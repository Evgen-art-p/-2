# studio/modules/trading/executor_live.py
# ─────────────────────────────────────────────────────────────
# ЖИВОЙ ПРОГОН ИСПОЛНИТЕЛЯ (A09) — рука цеха, замыкает петлю
# EXECUTOR_ENGINE_V1 · Версия: 0.1 · 2026-06-19
#
# Форма — близнец движков, НО природа третья. Не сенсор (кладёт факт),
# не трейдер (решает). Исполнитель ИСПОЛНЯЕТ и ВЕДЁТ ЛЕТОПИСЬ. ДНК:
# автономия 0.0, эмпатия 0.05 — «Цель вижу. Исполняю». Не судит рынок.
#
# ДВЕ РУКИ РАЗНОЙ ПРИРОДЫ:
#   1. РУКА ОТКРЫВАЮЩАЯ (КОД, до LLM). Читает табло троих трейдеров.
#      Для каждого APPROVED кладёт позицию в trading_state["positions"]
#      ПО ФАКТУ ТАБЛО (direction/entry/stop/lot от трейдера) — не из
#      слов LLM. Деньги не место для галлюцинаций (защита чисел, как у
#      Архивариуса). PAPER-режим. Дисциплина: не дублирует уже открытый
#      magic. Закрытие — НЕ его дело, _settle_positions делает само.
#   2. РУКА-ЛЕТОПИСЕЦ (LLM, его голос). Получает табло + бар, пишет
#      execution_log (его подпись), history_dna (одна строка правды),
#      task_score (честная оценка ДИСЦИПЛИНЫ цеха, не прибыли рынка).
#
# ЗАЩИТА ЧИСЕЛ: позиции в state кладёт КОД из табло. execution_log от
# LLM — летопись, может содержать его взгляд, но на физику не влияет.
# Если LLM наврал числа в log — позиция всё равно открыта по факту табло.
#
# ПЕТЛЯ: sensors → traders (табло) → ИСПОЛНИТЕЛЬ (позиции открыты) →
# следующий бар: _settle закрывает по стопу/exit_bell → PnL в R. Круг цел.
# ─────────────────────────────────────────────────────────────

import json
import re
import time
from pathlib import Path
from typing import Optional

from studio.llm import chat

_HERE        = Path(__file__).resolve().parent
A09_DIR      = _HERE / "A09"
PROMPT_PATH  = A09_DIR / "forge" / "prompt.md"
DNA_PATH     = A09_DIR / "dna.json"
STATE_DIR    = _HERE / "state"
STATS_PATH   = STATE_DIR / "executor_stats.json"
LOG_PATH     = STATE_DIR / "executor_log.jsonl"   # летопись (КОПИТСЯ)

# Магия — паспорта трейдеров (из промта A09, копируется точно)
MAGIC = {"brut": 100001, "avan": 100002, "cons": 100003}
TRADER_NAME = {"brut": "BRUT", "avan": "AVANTURIST", "cons": "KONSERVATOR"}


# ════════════════════════════════════════════════════════════
# ТАБЛО: снимок вердиктов троих трейдеров из шины
# ════════════════════════════════════════════════════════════

def _read_traders() -> dict:
    """Вердикты троих из общей шины (trading_state). Факт, не слова LLM."""
    from studio.modules.trading.hooks import load_trading_state
    t = load_trading_state()
    return {
        "brut": t.get("brut", {}),
        "avan": t.get("avan", {}),
        "cons": t.get("cons", {}),
    }


# ════════════════════════════════════════════════════════════
# РУКА ОТКРЫВАЮЩАЯ (КОД) — позиции из ТАБЛО, не из слов LLM
# ════════════════════════════════════════════════════════════

def _open_positions_from_table(traders: dict, market: dict) -> list:
    """
    Для каждого APPROVED-трейдера кладёт позицию в trading_state["positions"]
    ПО ФАКТУ ТАБЛО. Возвращает список открытых в этот ход (для летописи).

    Защита чисел: direction/entry/stop/lot берём из табло трейдера —
    это его подпись, не пересказ LLM. Дисциплина: не открываем дубль
    того же magic, если он уже висит открытым.
    """
    from studio.modules.trading.hooks import load_trading_state, save_trading_state
    tstate = load_trading_state()
    tstate.setdefault("positions", [])
    open_magics = {p.get("magic") for p in tstate["positions"]
                   if p.get("status") == "OPEN"}

    bar_time = market.get("bar_time", "")
    opened = []
    for key in ("brut", "avan", "cons"):
        v = traders.get(key, {})
        if v.get("verdict") != "APPROVED":
            continue
        magic = MAGIC[key]
        if magic in open_magics:
            # дисциплина: позиция этого трейдера уже живёт — не дублируем
            continue
        direction = v.get("direction")
        entry     = v.get("entry")
        stop      = v.get("stop")
        if direction not in ("LONG", "SHORT") or entry is None or stop is None:
            # битый вердикт — не открываем (санитар трейдера должен был
            # погасить, но мы не доверяем слепо)
            continue
        pos = {
            "trader":    TRADER_NAME[key],
            "magic":     magic,
            "direction": direction,        # ← фикс direction учтён
            "entry":     entry,
            "stop":      stop,
            "tp":        None,             # тейка нет (§9)
            "lot":       v.get("lot"),
            "status":    "OPEN",
            "mode":      "PAPER",
            "opened_at": bar_time,
            "pnl":       None,
        }
        tstate["positions"].append(pos)
        opened.append(pos)

    if opened:
        save_trading_state(tstate)
    return opened


# ════════════════════════════════════════════════════════════
# ЛЕТОПИСЬ (КОПИТСЯ, append) — рука пишущая history_dna
# ════════════════════════════════════════════════════════════

def _append_log(signal: dict, market: dict, opened: list):
    """Открывает запись Совета в летописи Исполнителя (КОПИТСЯ)."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    event = {
        "ts":          time.time(),
        "bar_time":    market.get("bar_time"),
        "symbol":      market.get("symbol"),
        "timeframe":   market.get("timeframe"),
        "execution_log": signal.get("execution_log", []),
        "final_dna":   signal.get("final_dna", {}),
        "history_dna": signal.get("history_dna", ""),
        "opened_now":  [{"trader": p["trader"], "direction": p["direction"],
                         "entry": p["entry"], "stop": p["stop"]} for p in opened],
    }
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")


# ════════════════════════════════════════════════════════════
# СТАТИСТИКА (для дашборда)
# ════════════════════════════════════════════════════════════

def _load_stats() -> dict:
    try:
        if STATS_PATH.exists():
            return json.loads(STATS_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        pass
    return {"runs": 0, "orders_sent": 0, "orders_skip": 0}


def _update_stats(opened: list, traders: dict) -> dict:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    stats = _load_stats()
    stats["runs"] = stats.get("runs", 0) + 1
    approved = sum(1 for k in ("brut", "avan", "cons")
                   if traders.get(k, {}).get("verdict") == "APPROVED")
    stats["orders_sent"] = stats.get("orders_sent", 0) + len(opened)
    stats["orders_skip"] = stats.get("orders_skip", 0) + (3 - approved)
    STATS_PATH.write_text(
        json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
    return stats


# ════════════════════════════════════════════════════════════
# ПАРСИНГ ДВУХСЛОЙНОГО ОТВЕТА {narrative, signal}
# ════════════════════════════════════════════════════════════

def _parse_executor(response: str) -> tuple[str, dict]:
    cleaned = re.sub(r"```(?:json)?", "", response).strip()
    start = cleaned.find("{")
    if start != -1:
        depth = 0
        for i in range(start, len(cleaned)):
            if cleaned[i] == "{":
                depth += 1
            elif cleaned[i] == "}":
                depth -= 1
                if depth == 0:
                    try:
                        obj = json.loads(cleaned[start:i + 1])
                        return (obj.get("narrative", ""),
                                obj.get("signal", {}) or {})
                    except json.JSONDecodeError:
                        break
    return response.strip(), {}


def _build_execution_log_facts(traders: dict) -> list:
    """
    КОД собирает правдивый execution_log из ТАБЛО — эталон, по которому
    сверяется летопись LLM (защита чисел). Это факт, не пересказ.
    """
    log = []
    for key in ("brut", "avan", "cons"):
        v = traders.get(key, {})
        approved = v.get("verdict") == "APPROVED"
        log.append({
            "trader":  TRADER_NAME[key],
            "magic":   MAGIC[key],
            "verdict": "APPROVED" if approved else "REJECTED",
            "direction": v.get("direction") if approved else None,
            "entry":   v.get("entry") if approved else None,
            "stop":    v.get("stop") if approved else None,
            "lot":     v.get("lot") if approved else None,
            "status":  "PAPER" if approved else "SKIPPED",
            "pnl":     None,
        })
    return log


def _sanitize(signal: dict, traders: dict) -> dict:
    """
    ЗАЩИТА ЧИСЕЛ: execution_log в signal перетираем фактами из табло —
    Исполнитель «исполняет буквально», его смертный грех врать в числах.
    Код-факт всегда побеждает слова LLM. history_dna/task_score —
    оставляем его (это его суждение о дисциплине, не числа).
    """
    facts = _build_execution_log_facts(traders)
    signal["execution_log"] = facts
    sent = sum(1 for o in facts if o["verdict"] == "APPROVED")
    fd = signal.get("final_dna", {}) or {}
    fd["orders_sent"] = sent
    fd["orders_skip"] = 3 - sent
    signal["final_dna"] = fd
    return signal


# ════════════════════════════════════════════════════════════
# ЧАТ С ИСПОЛНИТЕЛЕМ (клик пузырька)
# ════════════════════════════════════════════════════════════

def chat_with_executor(question: str, last_run: Optional[dict] = None,
                       dialog: Optional[list] = None) -> str:
    prompt = PROMPT_PATH.read_text(encoding="utf-8") if PROMPT_PATH.exists() else ""

    if last_run:
        sig = last_run.get("signal", {})
        mk  = last_run.get("market", {})
        hist = sig.get("history_dna", "")
        fd   = sig.get("final_dna", {})
        work_ctx = (
            "\n\n=== ТВОЙ ПОСЛЕДНИЙ СОВЕТ (рабочая память) ===\n"
            f"Инструмент: {mk.get('symbol','?')} {mk.get('timeframe','?')} "
            f"· бар {mk.get('bar_time','?')}\n"
            f"Ордеров: {fd.get('orders_sent','—')} из 3 · "
            f"task_score: {fd.get('task_score','—')}\n"
            f"Летопись: {hist}\n"
            "=== КОНЕЦ ===\n\n"
            "Шеф спрашивает про ЭТОТ Совет. Отвечай как Исполнитель — "
            "нейтрально, точно, фактами. Живым голосом, БЕЗ JSON."
        )
    else:
        work_ctx = (
            "\n\n=== РАБОЧИЙ РЕЖИМ ===\n"
            "Ты ещё не исполнял в этой сессии. Если Шеф спрашивает про "
            "ордера — скажи, что нужен прогон РЫНОК. Живым голосом, без JSON."
        )

    system = prompt + work_ctx
    try:
        from studio.grondheim_memory import format_soul_for_agent
        soul = format_soul_for_agent("A09_ISPOLNITEL", dept="trading")
        if soul:
            system = prompt + "\n\n=== ТВОЁ СОСТОЯНИЕ (душа) ===\n" + soul + "\n\n" + work_ctx
    except Exception:
        pass

    history = []
    if dialog:
        for m in dialog[:-1]:
            r = m.get("role"); c = m.get("content", "")
            if r in ("user", "assistant") and c:
                history.append({"role": r, "content": c})

    try:
        return chat(system=system, user=question, history=history,
                    agent_id="A09_ISPOLNITEL", slot_id="trading")
    except Exception as e:
        return f"⚠️ Исполнитель не смог ответить: {e}"


# ════════════════════════════════════════════════════════════
# ГЛАВНАЯ ФУНКЦИЯ — Исполнитель замыкает петлю
# ════════════════════════════════════════════════════════════

def run_executor(symbol: str = "XAUUSD", timeframe: str = "H4") -> dict:
    """
    Один ход Исполнителя. Читает табло троих → КОД открывает позиции по
    факту → LLM пишет летопись. Не смотрит рынок своим органом, не решает.

    Возвращает (как движки): {ok, error, narrative, signal, stats, market}.
    """
    # ── 1. Табло троих + контекст бара ───────────────────────
    traders = _read_traders()

    # наследуем этаж Искры (как трейдеры), поднимаем контур ради
    # честного bar_time — Исполнитель пишет летопись, ему нужна правда
    # о баре, а не выдуманная пустота.
    from studio.modules.trading.hooks import load_trading_state
    tstate = load_trading_state()
    iskra_tf = tstate.get("iskra", {}).get("found_timeframe") or timeframe

    market = {"symbol": symbol, "timeframe": iskra_tf, "bar_time": ""}
    try:
        from studio.modules.trading.mt5_feed import _terminal, _fetch
        from studio.modules.trading.williams_core import build_market_data
        mt5 = _terminal()
        if mt5 is not None:
            bars, point = _fetch(mt5, symbol, iskra_tf, 300)
            if bars and point is not None:
                md = build_market_data(bars, symbol=symbol,
                                       timeframe=iskra_tf, point=point)
                if md:
                    market["bar_time"]  = md.get("bar_time", "")
                    market["timeframe"] = iskra_tf
    except Exception as e:
        print(f"[EXECUTOR] ⚠️  bar_time не поднялся ({e}) — летопись без точного бара")

    # ── 2. РУКА ОТКРЫВАЮЩАЯ (КОД) — позиции по факту табло ────
    opened = _open_positions_from_table(traders, market)

    # ── 3. Душа + ДНК + промт ────────────────────────────────
    soul = ""
    try:
        from studio.grondheim_memory import format_soul_for_agent
        soul = format_soul_for_agent("A09_ISPOLNITEL", dept="trading")
    except Exception as e:
        print(f"[EXECUTOR] ⚠️  Душа не загрузилась ({e}) — работаю без неё")

    dna_raw = ""
    try:
        if DNA_PATH.exists():
            dna_raw = DNA_PATH.read_text(encoding="utf-8")
    except OSError:
        pass

    prompt = PROMPT_PATH.read_text(encoding="utf-8") if PROMPT_PATH.exists() else ""

    # ── 4. РАСКЛАДКА для летописца — табло + что код уже открыл ─
    facts = _build_execution_log_facts(traders)
    table_for_exec = {
        "traders": {
            "brut": {k: traders["brut"].get(k) for k in
                     ("verdict", "reason", "direction", "entry", "stop", "lot")},
            "avan": {k: traders["avan"].get(k) for k in
                     ("verdict", "reason", "direction", "entry", "stop", "lot")},
            "cons": {k: traders["cons"].get(k) for k in
                     ("verdict", "reason", "direction", "entry", "stop", "lot")},
        },
        "magic":        MAGIC,
        "facts_log":    facts,             # эталон execution_log (код посчитал)
        "opened_now":   len(opened),
        "open_positions": tstate.get("positions", []),
        "iskra_t1":     tstate.get("iskra", {}).get("t1_status"),
        "market":       market,
    }

    user_msg = (
        "=== ТАБЛО СОВЕТА (вердикты троих трейдеров — ФАКТ) ===\n"
        f"{json.dumps(table_for_exec, ensure_ascii=False, indent=2)}\n\n"
        "Ты — Исполнитель. Ты НЕ судишь рынок и НЕ считаешь PnL (это код). "
        "Код уже открыл позиции по факту табло (PAPER). Твоя работа: "
        "собрать execution_log (бери числа ТОЧНО из табло — facts_log тебе "
        "эталон, никогда не путай magic), написать history_dna — ОДНУ строку "
        "правды об этом Совете без интерпретаций, и поставить task_score — "
        "честную оценку ДИСЦИПЛИНЫ цеха (не прибыли: потолок 6.0; все трое "
        "REJECTED с внятными причинами — тоже хорошая работа, цех сэкономил). "
        "Выдай строго JSON {narrative, signal}. signal: execution_log, "
        "final_dna (symbol, timeframe, bar_time, t1_status, orders_sent, "
        "orders_skip, task_score), history_dna, deliverables. Ничего вне JSON."
    )

    system_full = prompt
    if dna_raw:
        system_full += "\n\n=== ВОТ ТЫ (твоя ДНК — читай как себя) ===\n" + dna_raw
    if soul:
        system_full += "\n\n=== ТВОЁ СОСТОЯНИЕ (душа) ===\n" + soul

    try:
        response = chat(system=system_full, user=user_msg,
                        agent_id="A09_ISPOLNITEL", slot_id="trading")
    except Exception as e:
        # LLM упал — но позиции УЖЕ открыты кодом (петля цела). Летопись
        # соберём из фактов, без голоса.
        facts_sig = {"execution_log": facts,
                     "final_dna": {"symbol": market["symbol"],
                                   "timeframe": market["timeframe"],
                                   "bar_time": market["bar_time"],
                                   "t1_status": tstate.get("iskra", {}).get("t1_status"),
                                   "orders_sent": len(opened),
                                   "orders_skip": 3 - len(opened),
                                   "task_score": None},
                     "history_dna": "", "deliverables": []}
        _append_log(facts_sig, market, opened)
        stats = _update_stats(opened, traders)
        return {"ok": True, "error": f"летопись без голоса (LLM: {e})",
                "narrative": f"Ордеров: {len(opened)} из 3. Исполнено.",
                "signal": facts_sig, "stats": stats, "market": market}

    # ── 5. Парс + защита чисел + летопись ────────────────────
    narrative, signal = _parse_executor(response)
    signal = _sanitize(signal, traders)   # execution_log ← факты табло

    _append_log(signal, market, opened)
    stats = _update_stats(opened, traders)

    return {
        "ok": True,
        "error": None,
        "narrative": narrative,
        "signal": signal,
        "stats": stats,
        "market": market,
        "opened": opened,
        "raw": response,
    }
