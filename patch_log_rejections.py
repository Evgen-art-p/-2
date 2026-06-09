"""
patch_log_rejections.py
=======================
Спринт 43 · 2026-06-10 · Находка Локи

ДЫРА: одиночные REJECTED не писались в Атлас. Закрытия — писались,
HARD_STOP (все трое) — писался, а отказ одного трейдера при входе
других — терялся. Архивариусу нужны именно отказы для top_failure_reason.

ПРАВКА: on_after_agent A09 → _log_rejections() — каждая REJECTED-запись
уходит в Атлас с полной сигнатурой Совета (по контракту v1.3).

ЗАПУСК из корня проекта (ПОСЛЕ patch_ispolnitel.py):
  python patch_log_rejections.py
"""

import shutil
from datetime import datetime
from pathlib import Path

HOOKS = Path("studio/modules/trading/hooks.py")

content = HOOKS.read_text(encoding="utf-8")

if "_log_rejections" in content:
    print("[PATCH] ⏭  Уже применён. Выход.")
    raise SystemExit(0)

ts  = datetime.now().strftime("%Y%m%d_%H%M%S")
bak = HOOKS.with_suffix(f".py.bak_{ts}")
shutil.copy2(HOOKS, bak)
print(f"[PATCH] 💾 Резервная копия: {bak}")

# ── 1. Вызов после _persist_trading_state ──
old1 = '''        # ── Сохраняем рабочую память цеха (ДО любого stop) ──
        _persist_trading_state(state)'''
new1 = '''        # ── Сохраняем рабочую память цеха (ДО любого stop) ──
        _persist_trading_state(state)

        # ── Каждый REJECTED — в Атлас (Архивариусу нужны отказы) ──
        _log_rejections(state)'''
assert old1 in content, "NOT FOUND: вызов _persist_trading_state"
content = content.replace(old1, new1, 1)
print("[PATCH] ✅ 1 — вызов _log_rejections в A09")

# ── 2. Функция перед _settle_positions ──
old2 = '''def _settle_positions(state: dict):'''
new2 = '''def _log_rejections(state: dict):
    """
    Пишет в Атлас запись по КАЖДОМУ одиночному REJECTED —
    с полной сигнатурой Совета (CHAIN_CONTRACT v1.3).
    HARD_STOP (все трое) пишется отдельно в on_after_agent.
    Без этих записей Архивариус слеп к причинам отказов.
    """
    results = state.get("results", {})
    chain   = state.get("chain_data", {})
    md      = chain.get("market_data", {})

    traders = [
        ("A06", "BRUT",        "brut_verdict", "brut_reason"),
        ("A07", "AVANTURIST",  "avan_verdict", "avan_reason"),
        ("A08", "KONSERVATOR", "cons_verdict", "cons_reason"),
    ]

    verdicts = {}
    for aid, name, v_key, r_key in traders:
        out = (results.get(aid, {}).get("meta", {}) or {}) \\
            .get("my_output", {}) or {}
        verdicts[name] = (out.get(v_key), out.get(r_key))

    # Если все трое REJECTED — HARD_STOP запишет их сам, не дублируем
    if all(v == "REJECTED" for v, _ in verdicts.values()):
        return

    for name, (verdict, reason) in verdicts.items():
        if verdict != "REJECTED":
            continue
        _write_atlas({
            "event":         "TRADER_REJECTED",
            "trader":        name,
            "verdict":       "REJECTED",
            "reason":        reason or "unknown",
            "symbol":        md.get("symbol"),
            "timeframe":     md.get("timeframe"),
            "bar_time":      md.get("bar_time"),
            "t1_status":     chain.get("t1_status"),
            "morj_status":   chain.get("morj_status"),
            "panic_phase":   chain.get("panic_phase"),
            "entry_trigger": chain.get("entry_trigger"),
            "pnl":           None,
        })
        print(f"[ATLAS] 📝 Отказ записан: {name} — {reason}")


def _settle_positions(state: dict):'''
assert old2 in content, "NOT FOUND: _settle_positions (сначала patch_ispolnitel.py!)"
content = content.replace(old2, new2, 1)
print("[PATCH] ✅ 2 — _log_rejections добавлена")

HOOKS.write_text(content, encoding="utf-8")
print(f"[PATCH] ✅ Перезаписан: {HOOKS}")
print("\\n[PATCH] 🏁 Готово. Спасибо Локе — петля теперь честная целиком.")
