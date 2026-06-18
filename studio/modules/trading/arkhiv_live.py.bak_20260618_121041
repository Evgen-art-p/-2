# studio/modules/trading/arkhiv_live.py
# ─────────────────────────────────────────────────────────────
# ЖИВОЙ АРХИВАРИУС (A05) — Хранитель Памяти Цеха
# ARKHIV_ENGINE_V1
# Версия: 0.1 · Спринт 45 · 2026-06-17
#
# Форма — близнец morj_live.py: живая модель + штатная память
# + душа города + голос+сигнал двухслойным JSON + чат с Шефом.
#
# НО ЛИНЗА ДРУГАЯ. Морж смотрит РЫНОК (Аллигатор, резинка).
# Архивариус рынок НЕ смотрит — ни одним глазом (его закон).
# Его глаза — СКЛАД: atlas_trading.jsonl. Он считает digest по
# сигнатуре стола и ТОЛКУЕТ числа голосом хранителя.
#
# ЗАКОН: «код считает — голова толкует». sample_size / success_rate /
#   top_failure_reason считает КОД (этот же файл, build_digest).
#   arkhiv_confidence — по жёсткому правилу контракта. Голова их
#   КОПИРУЕТ в signal и одевает в голос. Не пересчитывает.
#
# СИГНАТУРА = СУММА ВСЕХ СЕНСОРОВ (не один Ганс!):
#   t1_status (Искра) + morj_status (Морж) + panic_phase (Паникёр)
#   + fractal_valid (Ганс). Четыре голоса = лицо момента.
# ─────────────────────────────────────────────────────────────

import json
import re
from pathlib import Path
from typing import Optional

from studio.llm import chat

_HERE        = Path(__file__).resolve().parent
A05_DIR      = _HERE / "A05"
PROMPT_PATH  = A05_DIR / "forge" / "prompt.md"
STATE_DIR    = _HERE / "state"
STATS_PATH   = STATE_DIR / "arkhiv_stats.json"

# Склад Архивариуса — тот же Атлас, что пишут hooks._write_atlas / _settle.
ATLAS_PATH   = Path("economy/data/atlas_trading.jsonl")

# Грани лица момента — сумма голосов сенсоров (CHAIN_CONTRACT v1.7).
SIGNATURE_KEYS = ("t1_status", "morj_status", "panic_phase", "fractal_valid")


# ════════════════════════════════════════════════════════════
# СКЛАД: счётчик по Атласу (КОД считает — не голова)
# ─────────────────────────────────────────────────────────────
# Единственный источник чисел. Живёт здесь, чтобы и run_arkhiv,
# и chat_with_arkhiv, и hooks брали ОДНУ правду.
# ════════════════════════════════════════════════════════════

def _confidence(sample_size: int, success_rate: float) -> str:
    """
    Жёсткое правило контракта (CHAIN_CONTRACT v1.7 · prompt.md).
      HIGH   = sample >= 20 И success >= 0.65
      MEDIUM = sample >= 5  И success >= 0.50
      LOW    = всё остальное (включая пустую историю).
    Малая выборка лжёт. Не натягивать.
    """
    if sample_size >= 20 and success_rate >= 0.65:
        return "HIGH"
    if sample_size >= 5 and success_rate >= 0.50:
        return "MEDIUM"
    return "LOW"


def build_digest(signature: dict) -> dict:
    """
    Считает выжимку из Атласа по сигнатуре стола. ЧИСТЫЙ КОД, без LLM.

    signature: {t1_status, morj_status, panic_phase, fractal_valid}
      — сравниваем только по непустым граням (None не фильтрует).

    Возвращает (готово к копированию в signal):
      sample_size, closed_trades, success_rate,
      top_failure_reason, arkhiv_confidence, recent_cases[]
    """
    sig = {k: signature.get(k) for k in SIGNATURE_KEYS
           if signature.get(k) is not None}

    matches = []
    if ATLAS_PATH.exists():
        with open(ATLAS_PATH, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                entry = rec.get("entry", rec)
                if sig and all(entry.get(k) == v for k, v in sig.items()):
                    matches.append(entry)

    closed  = [m for m in matches if m.get("pnl") is not None]
    wins    = [m for m in closed if (m.get("pnl") or 0) > 0]
    success = round(len(wins) / len(closed), 4) if closed else 0.0

    reasons = {}
    for m in matches:
        r = m.get("reason")
        if r and (m.get("verdict") == "REJECTED" or (m.get("pnl") or 0) < 0):
            reasons[r] = reasons.get(r, 0) + 1
    top_reason = max(reasons, key=reasons.get) if reasons else "none"

    return {
        "sample_size":        len(matches),
        "closed_trades":      len(closed),
        "success_rate":       success,
        "top_failure_reason": top_reason,
        "arkhiv_confidence":  _confidence(len(matches), success),
        "recent_cases":       matches[-5:],
    }


# ════════════════════════════════════════════════════════════
# СТАТИСТИКА (для дашборда, как у Моржа)
# ════════════════════════════════════════════════════════════

def _load_stats() -> dict:
    try:
        if STATS_PATH.exists():
            return json.loads(STATS_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        pass
    return {"runs": 0, "high": 0, "medium": 0, "low": 0, "empty": 0}


def _update_stats(signal: dict) -> dict:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    stats = _load_stats()
    stats["runs"] = stats.get("runs", 0) + 1
    conf = signal.get("arkhiv_confidence", "LOW")
    if conf == "HIGH":
        stats["high"] = stats.get("high", 0) + 1
    elif conf == "MEDIUM":
        stats["medium"] = stats.get("medium", 0) + 1
    else:
        stats["low"] = stats.get("low", 0) + 1
    if signal.get("sample_size", 0) == 0:
        stats["empty"] = stats.get("empty", 0) + 1
    STATS_PATH.write_text(
        json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
    return stats


# ════════════════════════════════════════════════════════════
# ПАРСИНГ ДВУХСЛОЙНОГО ОТВЕТА (как у Моржа)
# ════════════════════════════════════════════════════════════

def _parse_arkhiv(response: str) -> tuple[str, dict]:
    """Достаёт {narrative, signal}. При сбое — текст как голос."""
    if not response:
        return "", {}
    for m in re.finditer(r"\{.*\}", response, re.DOTALL):
        try:
            obj = json.loads(m.group(0))
            if isinstance(obj, dict) and ("narrative" in obj or "signal" in obj):
                return obj.get("narrative", ""), obj.get("signal", {}) or {}
        except json.JSONDecodeError:
            continue
    return response.strip(), {}


# ════════════════════════════════════════════════════════════
# ЧАТ С АРХИВАРИУСОМ — разговор с Шефом про прошлое
# ════════════════════════════════════════════════════════════

def chat_with_arkhiv(question: str, last_run: Optional[dict] = None,
                     dialog: Optional[list] = None) -> str:
    """
    Разговор с Архивариусом. Он не смотрит рынок — он смотрит склад.
    Если был последний прогон — помнит его выжимку.
    """
    prompt = PROMPT_PATH.read_text(encoding="utf-8") if PROMPT_PATH.exists() else ""

    if last_run:
        sig = last_run.get("signal", {})
        sg  = last_run.get("signature", {})
        work_ctx = (
            "\n\n=== ТВОЙ ПОСЛЕДНИЙ ЗАПРОС К СКЛАДУ (рабочая память) ===\n"
            f"Сигнатура стола: {json.dumps(sg, ensure_ascii=False)}\n"
            f"Нашёл случаев: {sig.get('sample_size','—')} "
            f"(закрыто {sig.get('closed_trades','—')})\n"
            f"Доля прибыльных: {sig.get('success_rate','—')}\n"
            f"Частая причина потерь: {sig.get('top_failure_reason','—')}\n"
            f"Уверенность: {sig.get('arkhiv_confidence','—')}\n"
            f"Что ты сказал: {last_run.get('narrative','')}\n"
            "=== КОНЕЦ ===\n\n"
            "Шеф спрашивает про склад. Отвечай как Архивариус — тихо, "
            "медленно, со ссылками на прошлое. Никогда «я думаю» — только "
            "«было». Живым голосом, БЕЗ JSON — это разговор, не сигнал."
        )
    else:
        work_ctx = (
            "\n\n=== РАЗГОВОР ===\n"
            "Шеф пришёл с вопросом к твоему складу. Ты не смотришь рынок — "
            "только Атлас. Отвечай тихо, со ссылками на прошлое, живым "
            "голосом без JSON. Если точных данных в памяти нет — честно "
            "скажи «такого в Атласе нет», без догадок о текущем рынке."
        )

    system = prompt + work_ctx
    try:
        from studio.grondheim_memory import format_soul_for_agent
        soul = format_soul_for_agent("A05_ARKHIV", dept="trading")
        if soul:
            system = (prompt + "\n\n=== ТВОЁ СОСТОЯНИЕ (душа) ===\n"
                      + soul + "\n\n" + work_ctx)
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
                    agent_id="A05_ARKHIV", slot_id="trading")
    except Exception as e:
        return f"⚠️ Архивариус не смог ответить: {e}"


# ════════════════════════════════════════════════════════════
# ГЛАВНАЯ ФУНКЦИЯ — Архивариус отвечает Совету
# ════════════════════════════════════════════════════════════

def run_arkhiv(signature: Optional[dict] = None,
               symbol: str = "XAUUSD", timeframe: str = "H4") -> dict:
    """
    Один взгляд Архивариуса В СКЛАД по сигнатуре текущего стола.

    Линза: только прошлое. Рынок НЕ поднимается. Берём сигнатуру стола →
    считаем digest по Атласу → живая голова копирует числа и одевает
    в голос хранителя.

    signature: {t1_status, morj_status, panic_phase, fractal_valid}.
      None → читаем из общей шины (trading_state), что положили сенсоры.

    Возвращает (как run_morj):
      {ok, error, narrative, signal, stats, signature, digest}
    """
    if signature is None:
        signature = {}
        try:
            from studio.modules.trading.hooks import load_trading_state
            tstate = load_trading_state()
            iskra = tstate.get("iskra", {})
            morj  = tstate.get("morj", {})
            signature = {
                "t1_status":     iskra.get("t1_status"),
                "morj_status":   morj.get("morj_status"),
                "panic_phase":   tstate.get("panic", {}).get("panic_phase"),
                "fractal_valid": tstate.get("hans", {}).get("fractal_valid"),
            }
        except Exception as e:
            print(f"[ARKHIV] ⚠️  Не прочитал шину ({e}) — пустая сигнатура")

    digest = build_digest(signature)

    soul = ""
    try:
        from studio.grondheim_memory import format_soul_for_agent
        soul = format_soul_for_agent("A05_ARKHIV", dept="trading")
    except Exception as e:
        print(f"[ARKHIV] ⚠️  Душа не загрузилась ({e}) — работаю без неё")

    prompt = PROMPT_PATH.read_text(encoding="utf-8") if PROMPT_PATH.exists() else ""

    user_msg = (
        "=== СИГНАТУРА ТЕКУЩЕГО СТОЛА (сумма голосов сенсоров) ===\n"
        f"{json.dumps(signature, ensure_ascii=False, indent=2)}\n\n"
        "=== ATLAS_DIGEST (готовая выжимка — КОД посчитал, ты копируешь) ===\n"
        f"{json.dumps(digest, ensure_ascii=False, indent=2)}\n\n"
        "Закон: ты ХРАНИТЕЛЬ, не командир. Числа sample_size/success_rate/"
        "top_failure_reason/arkhiv_confidence — КОПИРУЙ из digest точно, "
        "не пересчитывай. Твоя работа — ИНТЕРПРЕТАЦИЯ: что эти числа значат, "
        "на что похож случай из recent_cases, какой урок прошлого тут уместен. "
        "Не советуй входить/не входить — ты контекст. Выдай строго "
        "двухслойный JSON {narrative, signal}. signal содержит: "
        "sample_size, success_rate, top_failure_reason, arkhiv_confidence. "
        "Ничего вне JSON."
    )

    system_full = prompt
    if soul:
        system_full = (
            prompt
            + "\n\n=== ТВОЁ СОСТОЯНИЕ И ПАМЯТЬ (душа) ===\n"
            + soul
            + "\n\n=== ГРАНИЦА ===\n"
            "Настроение красит твой ГОЛОС (narrative) — ты тих, печален, "
            "тебе хватает четырёх часов сна. Но СИГНАЛ (signal) — числа "
            "склада. Печаль не меняет sample_size, усталость не двигает "
            "confidence. Чувствуй как хочешь, числа копируй честно."
        )

    try:
        response = chat(system=system_full, user=user_msg,
                        agent_id="A05_ARKHIV", slot_id="trading")
    except Exception as e:
        return {"ok": False, "error": f"Архивариус не смог подумать: {e}",
                "narrative": "", "signal": {}, "stats": _load_stats(),
                "signature": signature, "digest": digest}

    narrative, signal = _parse_arkhiv(response)

    # ЗАЩИТА ЧИСЕЛ: код прав, не голова. Что бы LLM ни написала —
    # числа из digest перетирают её. Правда у кода.
    signal["sample_size"]        = digest["sample_size"]
    signal["success_rate"]       = digest["success_rate"]
    signal["top_failure_reason"] = digest["top_failure_reason"]
    signal["arkhiv_confidence"]  = digest["arkhiv_confidence"]

    stats = _update_stats(signal)

    return {
        "ok": True,
        "error": None,
        "narrative": narrative,
        "signal": signal,
        "stats": stats,
        "signature": signature,
        "digest": digest,
        "raw": response,
    }
