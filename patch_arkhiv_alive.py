#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_arkhiv_alive.py · Спринт 45 · 2026-06-17
─────────────────────────────────────────────────────────────────
АРХИВАРИУС A05 — РОЖДЕНИЕ ГРАЖДАНИНА.

Что делает (всё идемпотентно, с бэкапами, по маркерам):

  1. Кладёт движок studio/modules/trading/arkhiv_live.py
     (run_arkhiv + chat_with_arkhiv + build_digest — по лекалу Моржа,
      линза = склад Атласа, не рынок).

  2. ЧИНИТ hooks.py · _prepare_atlas_digest:
     — сигнатура entry_trigger → fractal_valid (сумма 4 сенсоров)
     — добавляет arkhiv_confidence (правило контракта) в digest
     Делает это, делегируя расчёт в arkhiv_live.build_digest —
     один источник правды для кода и движка.

  3. ЧИНИТ hooks.py · _log_rejections:
     entry_trigger → fractal_valid в записи отказа (тот же ключ).

  4. ВЖИВЛЯЕТ чат A05 в дашборд ui_exchange.py:
     ветка `if agent_id == "A05"` → chat_with_arkhiv (как у A02/A03/A04).

Запуск из корня студии:
    python patch_arkhiv_alive.py
"""

import os
import re
import sys
import shutil
from datetime import datetime

ROOT = os.getcwd()

HOOKS  = os.path.join(ROOT, "studio", "modules", "trading", "hooks.py")
ENGINE = os.path.join(ROOT, "studio", "modules", "trading", "arkhiv_live.py")
UIEXCH = os.path.join(ROOT, "studio", "economy", "ui_exchange.py")


def _stamp():
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _backup(path):
    if os.path.exists(path):
        bak = f"{path}.bak_{_stamp()}"
        shutil.copy2(path, bak)
        print(f"  📦 бэкап: {os.path.basename(bak)}")


def _read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def _write(path, text):
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


# ════════════════════════════════════════════════════════════
# ТЕЛО ДВИЖКА (вшито в патч)
# ════════════════════════════════════════════════════════════

ENGINE_SRC = r'''# studio/modules/trading/arkhiv_live.py
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
'''


# ════════════════════════════════════════════════════════════
# ШАГ 1 — положить движок
# ════════════════════════════════════════════════════════════

def step_engine():
    print("\n[1/4] Движок arkhiv_live.py")
    if os.path.exists(ENGINE):
        cur = _read(ENGINE)
        if "ARKHIV_ENGINE_V1" in cur:
            print("  ✓ уже стоит (маркер ARKHIV_ENGINE_V1) — пропускаю")
            return
        _backup(ENGINE)
    _write(ENGINE, ENGINE_SRC)
    print(f"  ✅ записан: {ENGINE}")


# ════════════════════════════════════════════════════════════
# ШАГ 2 — сигнатура digest + arkhiv_confidence в hooks
# ════════════════════════════════════════════════════════════

def step_digest():
    print("\n[2/4] hooks.py · _prepare_atlas_digest (сигнатура + confidence)")
    src = _read(HOOKS)

    if "ARKHIV_DIGEST_PATCHED" in src:
        print("  ✓ уже пропатчено — пропускаю")
        return

    # Старый блок сигнатуры (entry_trigger) → новый (fractal_valid)
    old_sig = (
        '    signature = {\n'
        '        "t1_status":     chain.get("t1_status"),\n'
        '        "morj_status":   chain.get("morj_status"),\n'
        '        "panic_phase":   chain.get("panic_phase"),\n'
        '        "entry_trigger": chain.get("entry_trigger"),\n'
        '    }'
    )
    new_sig = (
        '    # ARKHIV_DIGEST_PATCHED · сигнатура = сумма 4 сенсоров (не один Ганс)\n'
        '    signature = {\n'
        '        "t1_status":     chain.get("t1_status"),\n'
        '        "morj_status":   chain.get("morj_status"),\n'
        '        "panic_phase":   chain.get("panic_phase"),\n'
        '        "fractal_valid": chain.get("fractal_valid"),\n'
        '    }\n'
        '    # Считает движок Архивариуса — один источник правды для\n'
        '    # кода и LLM. Внутри: правильная сигнатура + arkhiv_confidence.\n'
        '    try:\n'
        '        from studio.modules.trading.arkhiv_live import build_digest\n'
        '        chain["atlas_digest"] = build_digest(signature)\n'
        '        print(f"[ATLAS] 📖 Digest (движок): "\n'
        '              f"sample={chain[\'atlas_digest\'][\'sample_size\']}, "\n'
        '              f"conf={chain[\'atlas_digest\'][\'arkhiv_confidence\']}")\n'
        '        return\n'
        '    except Exception as _e:\n'
        '        print(f"[ATLAS] ⚠️  движок недоступен ({_e}) — старый расчёт")'
    )

    if old_sig not in src:
        print("  ⚠️  якорь сигнатуры не найден — возможно структура изменилась")
        print("      проверь hooks.py вручную, патч сигнатуры НЕ применён")
        return

    src = src.replace(old_sig, new_sig, 1)
    _backup(HOOKS)
    _write(HOOKS, src)
    print("  ✅ сигнатура → fractal_valid, расчёт делегирован движку")


# ════════════════════════════════════════════════════════════
# ШАГ 3 — сигнатура отказов в _log_rejections
# ════════════════════════════════════════════════════════════

def step_rejections():
    print("\n[3/4] hooks.py · _log_rejections (entry_trigger → fractal_valid)")
    src = _read(HOOKS)

    old_rej = '            "entry_trigger": chain.get("entry_trigger"),\n            "pnl":           None,'
    new_rej = '            "fractal_valid": chain.get("fractal_valid"),  # ARKHIV_REJ_PATCHED\n            "pnl":           None,'

    if "ARKHIV_REJ_PATCHED" in src:
        print("  ✓ уже пропатчено — пропускаю")
        return
    if old_rej not in src:
        print("  ⚠️  якорь отказов не найден — проверь _log_rejections вручную")
        return

    src = src.replace(old_rej, new_rej, 1)
    _backup(HOOKS)
    _write(HOOKS, src)
    print("  ✅ отказы пишутся с fractal_valid (согласовано со складом)")


# ════════════════════════════════════════════════════════════
# ШАГ 4 — чат A05 в дашборде
# ════════════════════════════════════════════════════════════

def step_dashboard():
    print("\n[4/4] ui_exchange.py · чат A05 → chat_with_arkhiv")
    if not os.path.exists(UIEXCH):
        print(f"  ⚠️  не найден {UIEXCH} — пропускаю")
        return
    src = _read(UIEXCH)

    if "ARKHIV_CHAT_PATCHED" in src:
        print("  ✓ уже пропатчено — пропускаю")
        return

    # Вставляем ветку A05 ПЕРЕД веткой A04 (порядок не важен, оба до A01-фоллбека)
    anchor = '        if agent_id == "A04":\n'
    branch = (
        '        if agent_id == "A05":  # ARKHIV_CHAT_PATCHED\n'
        '            ui.notify("📚 Архивариус листает Атлас...", type="info")\n'
        '            try:\n'
        '                from studio.modules.trading.arkhiv_live import chat_with_arkhiv\n'
        '                dialog = [m for m in state["chat_history"]\n'
        '                          if m.get("role") in ("user", "assistant") and m.get("content")]\n'
        '                reply = await asyncio.get_event_loop().run_in_executor(\n'
        '                    None, lambda: chat_with_arkhiv(msg, state.get("arkhiv_last_run"), dialog))\n'
        '            except Exception as e:\n'
        '                reply = f"⚠️ Архивариус не смог ответить: {e}"\n'
        '            state["chat_history"].append({\n'
        '                "role": "assistant", "agent": "A05", "content": reply})\n'
        '            update_chat_display()\n'
        '            return\n\n'
    )

    if anchor not in src:
        print("  ⚠️  якорь ветки A04 не найден — проверь дашборд вручную")
        return

    src = src.replace(anchor, branch + anchor, 1)
    _backup(UIEXCH)
    _write(UIEXCH, src)
    print("  ✅ клик по пузырьку 📚 Архивариус → живой разговор")


# ════════════════════════════════════════════════════════════

def main():
    print("=" * 60)
    print("  ПАТЧ: Архивариус A05 — рождение гражданина")
    print("=" * 60)

    if not os.path.exists(HOOKS):
        print(f"\n❌ Не найден {HOOKS}")
        print("   Запускай из КОРНЯ студии (где папка studio/).")
        sys.exit(1)

    step_engine()
    step_digest()
    step_rejections()
    step_dashboard()

    # Проверка синтаксиса того что тронули
    print("\n[проверка] синтаксис изменённых файлов")
    import py_compile
    for p in (ENGINE, HOOKS, UIEXCH):
        if os.path.exists(p):
            try:
                py_compile.compile(p, doraise=True)
                print(f"  ✅ {os.path.basename(p)}")
            except py_compile.PyCompileError as e:
                print(f"  ❌ {os.path.basename(p)}: {e}")

    print("\n" + "=" * 60)
    print("  Готово. Архивариус ожил:")
    print("  • run_arkhiv — отвечает Совету (числа + голос)")
    print("  • chat_with_arkhiv — отвечает тебе в дашборде")
    print("  • сигнатура = сумма 4 сенсоров, confidence по контракту")
    print("  Осталось вручную (рабочий момент): поправить в")
    print("  A05/forge/prompt.md метку entry_trigger → fractal_valid")
    print("  и v1.1 → v1.7 (косметика промпта).")
    print("=" * 60)


if __name__ == "__main__":
    main()
