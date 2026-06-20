# studio/modules/trading/avan_live.py
# ─────────────────────────────────────────────────────────────
# ЖИВОЙ ПРОГОН АВАНТЮРИСТА (A07) — второй ТРЕЙДЕР Совета Биржи
# AVAN_ENGINE_V1 · Версия: 0.1 · 2026-06-19
#
# Близнец brut_live.py по ФОРМЕ. Та же природа трейдера: читает весь
# накрытый стол, СЧИТАЕТ вход сам (trade_setup мёртв), все рычаги на нём,
# два следа (табло + дневник), петля обучения на pnl (отложена).
#
# СТАНЦИЯ ДРУГАЯ. Брут — §6.1 (пробой фрактала за пастью на импульсе).
# Авантюрист — §6.2: конец волны C отката, разворот. Верит первым. Ловец
# падающих ножей: меньший объём, ближний стоп. Входит ТОЛЬКО когда видит
# полную сигнатуру разворота на дне (5 пуль Уровня 5 «Эксперт»). НИКОГДА
# не входит на развороте глобальной 5-й (это начало коррекции — ждём).
#
# ХАРАКТЕР ДРУГОЙ. Илья. Автономия высокая, «в рынке или в ауте», полутонов
# нет, просадку несёт молча. Канон на полке — но рука его. Ни одной нашей
# руки на его руке: lot называет сам, цену считает сам, стоп — его.
#
# ДВА СЛЕДА вердикта:
#   · ТАБЛО  (trading_state["avan"]) — «сейчас», для Исполнителя 09.
#   · ДНЕВНИК (state/diary_avan.jsonl) — событие во времени, КОПИТСЯ.
# ─────────────────────────────────────────────────────────────

import json
import re
import time
from pathlib import Path
from typing import Optional

from studio.llm import chat

_HERE        = Path(__file__).resolve().parent
A07_DIR      = _HERE / "A07"
PROMPT_PATH  = A07_DIR / "forge" / "prompt.md"
KNOWLEDGE    = A07_DIR / "forge" / "knowledge" / "KOTIN_PHILOSOPHY.md"
DNA_PATH     = A07_DIR / "dna.json"
STATE_DIR    = _HERE / "state"
STATS_PATH   = STATE_DIR / "avan_stats.json"
DIARY_PATH   = STATE_DIR / "diary_avan.jsonl"


# ════════════════════════════════════════════════════════════
# СТОЛ: читаем ВСЮ шину — показания пяти сенсоров
# ════════════════════════════════════════════════════════════

def _read_table() -> dict:
    """Снимок накрытого стола из общей шины (trading_state)."""
    from studio.modules.trading.hooks import load_trading_state
    t = load_trading_state()
    return {
        "iskra":  t.get("iskra", {}),
        "morj":   t.get("morj", {}),
        "panic":  t.get("panic", {}),
        "hans":   t.get("hans", {}),
        "arkhiv": t.get("arkhiv", {}),
    }


def _save_verdict_to_table(signal: dict):
    """ТАБЛО: вердикт Авантюриста в шину для Исполнителя 09."""
    from studio.modules.trading.hooks import load_trading_state, save_trading_state
    t = load_trading_state()
    t.setdefault("avan", {})
    t["avan"]["verdict"]   = signal.get("avan_verdict", "REJECTED")
    t["avan"]["reason"]    = signal.get("avan_reason", "")
    t["avan"]["direction"] = signal.get("avan_direction")
    t["avan"]["entry"]     = signal.get("avan_entry")
    t["avan"]["stop"]      = signal.get("avan_stop")
    t["avan"]["lot"]       = signal.get("avan_lot")
    save_trading_state(t)


# ════════════════════════════════════════════════════════════
# ДНЕВНИК: рука пишущая (КОПИТСЯ, append)
# ════════════════════════════════════════════════════════════

def _append_diary(signal: dict, diary_entry: dict, market: dict, table: dict):
    """Открывает запись события в личной тетради. result=null — допишет
    рука дописывающая при закрытии позиции (hooks._settle)."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    event = {
        "ts":        time.time(),
        "bar_time":  market.get("bar_time"),
        "symbol":    market.get("symbol"),
        "timeframe": market.get("timeframe"),
        "table": {
            "t1":     table.get("iskra", {}).get("t1_status"),
            "morj":   table.get("morj", {}).get("morj_status"),
            "panic":  table.get("panic", {}).get("panic_phase"),
            "fractal_valid": table.get("hans", {}).get("fractal_valid"),
        },
        "verdict":   signal.get("avan_verdict"),
        "direction": signal.get("avan_direction"),
        "entry":     signal.get("avan_entry"),
        "stop":      signal.get("avan_stop"),
        "lot":       signal.get("avan_lot"),
        "input":     (diary_entry or {}).get("input", ""),
        "action":    (diary_entry or {}).get("action", ""),
        "result":    None,
    }
    with open(DIARY_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")


def _read_recent_diary(n: int = 5) -> list:
    """Последние n событий из личной тетради."""
    if not DIARY_PATH.exists():
        return []
    try:
        lines = DIARY_PATH.read_text(encoding="utf-8").strip().splitlines()
        out = []
        for line in lines[-n:]:
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return out
    except OSError:
        return []


# ════════════════════════════════════════════════════════════
# СТАТИСТИКА (для дашборда)
# ════════════════════════════════════════════════════════════

def _load_stats() -> dict:
    try:
        if STATS_PATH.exists():
            return json.loads(STATS_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        pass
    return {"runs": 0, "approved": 0, "rejected": 0, "long": 0, "short": 0}


def _update_stats(signal: dict) -> dict:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    stats = _load_stats()
    stats["runs"] = stats.get("runs", 0) + 1
    if signal.get("avan_verdict") == "APPROVED":
        stats["approved"] = stats.get("approved", 0) + 1
        d = signal.get("avan_direction")
        if d == "LONG":
            stats["long"] = stats.get("long", 0) + 1
        elif d == "SHORT":
            stats["short"] = stats.get("short", 0) + 1
    else:
        stats["rejected"] = stats.get("rejected", 0) + 1
    STATS_PATH.write_text(
        json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
    return stats


# ════════════════════════════════════════════════════════════
# ПАРСИНГ ТРЁХСЛОЙНОГО ОТВЕТА {narrative, signal, diary_entry}
# ════════════════════════════════════════════════════════════

def _parse_avan(response: str) -> tuple[str, dict, dict]:
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
                                obj.get("signal", {}) or {},
                                obj.get("diary_entry", {}) or {})
                    except json.JSONDecodeError:
                        break
    return response.strip(), {}, {}


def _sanitize(signal: dict) -> dict:
    """APPROVED только с направлением; иначе всё null."""
    v = signal.get("avan_verdict")
    if v not in ("APPROVED", "REJECTED"):
        v = "REJECTED"
    signal["avan_verdict"] = v
    if v == "REJECTED":
        signal["avan_direction"] = None
        signal["avan_entry"] = None
        signal["avan_stop"]  = None
        signal["avan_lot"]   = None
    else:
        d = signal.get("avan_direction")
        if d not in ("LONG", "SHORT"):
            signal["avan_verdict"]   = "REJECTED"
            signal["avan_reason"]    = (signal.get("avan_reason", "") +
                                        " [гашу: APPROVED без направления]").strip()
            signal["avan_direction"] = None
            signal["avan_entry"] = None
            signal["avan_stop"]  = None
            signal["avan_lot"]   = None
    return signal


# ════════════════════════════════════════════════════════════
# ЧАТ С АВАНТЮРИСТОМ (клик пузырька)
# ════════════════════════════════════════════════════════════

def chat_with_avan(question: str, last_run: Optional[dict] = None,
                   dialog: Optional[list] = None) -> str:
    prompt = PROMPT_PATH.read_text(encoding="utf-8") if PROMPT_PATH.exists() else ""

    if last_run:
        sig = last_run.get("signal", {})
        mk  = last_run.get("market", {})
        work_ctx = (
            "\n\n=== ТВОЁ ПОСЛЕДНЕЕ РЕШЕНИЕ (рабочая память) ===\n"
            f"Инструмент: {mk.get('symbol','?')} {mk.get('timeframe','?')} "
            f"· бар {mk.get('bar_time','?')}\n"
            f"Вердикт: {sig.get('avan_verdict','—')} "
            f"({sig.get('avan_reason','')})\n"
            f"Направление: {sig.get('avan_direction','—')}  ·  "
            f"вход {sig.get('avan_entry','—')} · стоп {sig.get('avan_stop','—')}\n"
            f"Что ты сказал: {last_run.get('narrative','')}\n"
            "=== КОНЕЦ ===\n\n"
            "Шеф спрашивает про ЭТО решение. Отвечай как Авантюрист — быстро, "
            "уверенно, своим голосом. Живым голосом, БЕЗ JSON — это разговор."
        )
    else:
        work_ctx = (
            "\n\n=== РАБОЧИЙ РЕЖИМ ===\n"
            "Ты ещё не смотрел стол в этой сессии. Если Шеф спрашивает про "
            "рынок — скажи, что нужно нажать РЫНОК. Живым голосом, без JSON."
        )

    system = prompt + work_ctx
    try:
        from studio.grondheim_memory import format_soul_for_agent
        soul = format_soul_for_agent("A07_AVANTURIST", dept="trading")
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
                    agent_id="A07_AVANTURIST", slot_id="trading")
    except Exception as e:
        return f"⚠️ Авантюрист не смог ответить: {e}"


# ════════════════════════════════════════════════════════════
# ГЛАВНАЯ ФУНКЦИЯ — один взгляд Авантюриста на накрытый стол
# ════════════════════════════════════════════════════════════

# ════════════════════════════════════════════════════════════
# КАМЕНЬ 1: СВОЯ ОТКРЫТАЯ ПОЗИЦИЯ — ФАКТ на стол (не приказ)  # TRADER_SEES_POSITION_V1
# ─────────────────────────────────────────────────────────────
# Трейдер видит, что он в рынке: что открыто, сколько живёт, как
# плавает. Решение — его природа. R считаем ТОЙ ЖЕ формулой, что
# _settle_positions применит при закрытии (защита чисел).
# ════════════════════════════════════════════════════════════

_MY_MAGIC = 100002   # паспорт трейдера (как у Исполнителя)


def _my_open_position(md: dict) -> dict:
    """
    Факт открытой позиции ЭТОГО трейдера (по магику) из trading_state.
    Нет позиции → None. Есть → живой факт с плавающим R. Без суждений.
    """
    try:
        from studio.modules.trading.hooks import load_trading_state
        positions = load_trading_state().get("positions", []) or []
    except Exception:
        return None

    mine = None
    for p in positions:
        if p.get("magic") == _MY_MAGIC and p.get("status") == "OPEN":
            mine = p
            break
    if not mine:
        return None

    entry = mine.get("entry")
    stop  = mine.get("stop")
    direction = mine.get("direction", "LONG")
    price = (md.get("price", {}) or {}).get("close")

    # Плавающий R — эталон формулы из hooks._settle_positions.
    floating_r = None
    if entry is not None and stop is not None and price is not None:
        if direction == "LONG":
            risk = entry - stop
            pnl_price = price - entry
        else:  # SHORT
            risk = stop - entry
            pnl_price = entry - price
        if risk and risk > 0:
            floating_r = round(pnl_price / risk, 2)

    # bars_alive — сколько баров живёт (по дате открытия vs текущий бар).
    bars_alive = None
    opened_at = mine.get("opened_at")
    bar_time  = md.get("bar_time")
    if opened_at and bar_time and opened_at == bar_time:
        bars_alive = 0   # открыта на этом же баре

    return {
        "direction":     direction,
        "entry":         entry,
        "stop":          stop,
        "lot":           mine.get("lot"),
        "opened_at":     opened_at,
        "current_price": price,
        "floating_r":    floating_r,   # нереализованный R «закрой сейчас»
        "bars_alive":    bars_alive,
    }



def run_avan(symbol: str = "XAUUSD", timeframe: str = "H4",
             bars_count: int = 300) -> dict:
    """Один взгляд Авантюриста на стол. Читает показания сенсоров (шина)
    + market_data ядра, судит сам по §6.2 (конец волны C, разворот)."""
    # ── 1. Контур: наследуем этаж Искры ──
    table = _read_table()
    iskra_tf = table.get("iskra", {}).get("found_timeframe")
    if iskra_tf:
        timeframe = iskra_tf

    from studio.modules.trading.mt5_feed import _terminal, _fetch
    mt5 = _terminal()
    if mt5 is None:
        return {"ok": False, "error": "MetaTrader5 не установлен в Python",
                "narrative": "", "signal": {}, "diary_entry": {},
                "stats": _load_stats(), "market": {}, "table": table}

    bars, point = _fetch(mt5, symbol, timeframe, bars_count)
    if not bars or point is None:
        return {"ok": False,
                "error": f"Терминал не дал котировки {symbol} {timeframe}.",
                "narrative": "", "signal": {}, "diary_entry": {},
                "stats": _load_stats(), "market": {}, "table": table}

    from studio.modules.trading.williams_core import build_market_data
    md = build_market_data(bars, symbol=symbol, timeframe=timeframe, point=point)
    if not md:
        return {"ok": False, "error": "Ядро не собрало market_data",
                "narrative": "", "signal": {}, "diary_entry": {},
                "stats": _load_stats(), "market": {}, "table": table}

    # ── 2. Душа + ДНК (вот ТЫ) ──
    soul = ""
    try:
        from studio.grondheim_memory import format_soul_for_agent
        soul = format_soul_for_agent("A07_AVANTURIST", dept="trading")
    except Exception as e:
        print(f"[AVAN] ⚠️  Душа не загрузилась ({e}) — работаю без неё")

    dna_raw = ""
    try:
        if DNA_PATH.exists():
            dna_raw = DNA_PATH.read_text(encoding="utf-8")
    except OSError:
        pass

    prompt    = PROMPT_PATH.read_text(encoding="utf-8") if PROMPT_PATH.exists() else ""
    knowledge = KNOWLEDGE.read_text(encoding="utf-8") if KNOWLEDGE.exists() else ""

    # ── 3. Личный дневник ──
    recent = _read_recent_diary(5)

    # ── 4. РАСКЛАДКА МОМЕНТА ──
    alligator = md.get("alligator", {})
    fractals  = md.get("fractals", {})
    price     = md.get("price", {})
    table_for_avan = {
        # КАМЕНЬ 1: своя открытая позиция — ФАКТ (null если не в рынке).  # TRADER_SEES_POSITION_V1
        "position": _my_open_position(md),
        "anchor": {
            "global_trend": table.get("iskra", {}).get("trend_direction"),
            "found_timeframe": iskra_tf,
        },
        "sensors": {
            "iskra":  {k: table["iskra"].get(k) for k in
                       ("t1_status", "zero_point_price", "trend_direction")},
            "morj":   {k: table["morj"].get(k) for k in
                       ("morj_status", "wave_1_validated", "tension_peak")},
            "panic":  {k: table["panic"].get(k) for k in
                       ("panic_phase", "crowd_sentiment")},
            "hans":   {k: table["hans"].get(k) for k in
                       ("fractal_valid", "fractal_side", "fractal_price")},
            "arkhiv": table.get("arkhiv", {}),
        },
        "market": {
            "teeth":  alligator.get("teeth"),
            "alligator_sleeping": alligator.get("sleeping"),
            "fractal_up":   fractals.get("last_up"),
            "fractal_down": fractals.get("last_down"),
            "hans_fractal_price": table.get("hans", {}).get("fractal_price"),
            "price":    price,
            "point":    point,
        },
    }

    user_msg = (
        "=== НАКРЫТЫЙ СТОЛ (раскладка момента) ===\n"
        f"{json.dumps(table_for_avan, ensure_ascii=False, indent=2)}\n\n"
        "=== ТВОЙ ДНЕВНИК (последние события — твоя память) ===\n"
        f"{json.dumps(recent, ensure_ascii=False, indent=2) if recent else '(пусто — первое решение)'}\n\n"
        "Перед тобой стол и ты сам. Канон у тебя на полке (книга Котина), "
        "твоя ДНК — ниже. Решаешь только ты. По системе сигнал ранней добычи "
        "— Разворотный Бар конца волны C (книга, §12): дивергенция на дне, "
        "целевая зона, фрактал, приседающий, смена моментума. Это знание о "
        "рынке, не команда тебе. Веришь дну сегодня или нет — твоё. Входишь "
        "— называешь сторону, СЧИТАЕШЬ entry и stop сам из чисел стола; где "
        "стоп, какой lot — твоя рука, не рельса. Не входишь — verdict "
        "REJECTED. Никто не подложит тебе готовую цену и не скажет, как "
        "поступить. Выдай строго JSON {narrative, signal, "
        "diary_entry}. signal: avan_verdict, avan_reason, avan_direction, "
        "avan_entry, avan_stop, avan_lot. diary_entry: input, action, "
        "result(=null). Ничего вне JSON."
    )

    system_full = prompt
    if dna_raw:
        system_full += "\n\n=== ВОТ ТЫ (твоя ДНК — читай как себя) ===\n" + dna_raw
    if soul:
        system_full += "\n\n=== ТВОЁ СОСТОЯНИЕ (душа) ===\n" + soul

    try:
        response = chat(system=system_full, user=user_msg, knowledge=knowledge,
                        agent_id="A07_AVANTURIST", slot_id="trading")
    except Exception as e:
        return {"ok": False, "error": f"Авантюрист не смог решить: {e}",
                "narrative": "", "signal": {}, "diary_entry": {},
                "stats": _load_stats(),
                "market": {"symbol": symbol, "timeframe": timeframe,
                           "bar_time": md.get("bar_time"), "point": point},
                "table": table}

    # ── 5. Парс + санитар + два следа ──
    narrative, signal, diary_entry = _parse_avan(response)
    signal = _sanitize(signal)

    market = {"symbol": symbol, "timeframe": timeframe,
              "bar_time": md.get("bar_time"), "point": point}

    _save_verdict_to_table(signal)
    _append_diary(signal, diary_entry, market, table)
    stats = _update_stats(signal)

    return {
        "ok": True,
        "error": None,
        "narrative": narrative,
        "signal": signal,
        "diary_entry": diary_entry,
        "stats": stats,
        "market": market,
        "table": table,
        "raw": response,
    }
