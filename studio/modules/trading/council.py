# studio/modules/trading/council.py
# ─────────────────────────────────────────────────────────────
# ЧИСТАЯ БУДИЛКА СОВЕТА — одно место, где оживает девятка.
# ENGINE_ONE_DOOR_V1 · 2026-06-23 · Брат + Шеф
#
# ЗАКОН (наказ Шефа): одно место пробуждения Совета на ОБА мира.
# Раньше Совет будился в ДВУХ местах руками — в кнопке РЫНОК (с UI)
# и в тестере (своя лестница). Это и был маскарад. Теперь — одна
# лестница, без UI. Реал и тест зовут ЕЁ, отличаясь только источником
# бара (его подал движок снаружи) и тем, куда слать вести (on_event).
#
# Порядок ОДИН-В-ОДИН с кнопкой РЫНОК (ui_exchange):
#   Искра → Морж → Паникёр → Ганс → Архивариус
#        → [Брут · Авантюрист · Консерватор] → Исполнитель
#
# Движок НЕ дублирует агентов — зовёт ЖИВЫЕ run_*. Слеп к активу/ТФ.
# ─────────────────────────────────────────────────────────────

from typing import Optional, Callable
import importlib


# сенсоры после Искры — порядок как в кнопке РЫНОК
_SENSORS = [
    ("A02", "morj_live",     "run_morj"),
    ("A03", "panikyor_live", "run_panikyor"),
    ("A04", "hans_live",     "run_hans"),
]
# трое трейдеров за столом
_TRADERS = [
    ("A06", "brut_live", "run_brut"),
    ("A07", "avan_live", "run_avan"),
    ("A08", "cons_live", "run_cons"),
]


def _call(mod_name: str, fn_name: str, **kw) -> dict:
    """Зовёт живой run_* агента. Любой сбой — мягко, не роняем Совет."""
    try:
        mod = importlib.import_module(f"studio.modules.trading.{mod_name}")
        fn = getattr(mod, fn_name)
        return fn(**kw) or {}
    except Exception as e:
        return {"ok": False, "error": f"{fn_name}: {e}"}


def wake_council(symbol: str, timeframe: str,
                 on_event: Optional[Callable] = None) -> dict:
    """
    БУДИТ СОВЕТ на текущем баре. symbol/timeframe — паспорт, течёт
    в каждого агента (они сами берут бар своего этажа — спуск Искры
    решает где). on_event(dict) — вести наружу (лента кабинета), может
    быть None.

    Возвращает сводку: кто что сказал. Позиции открывает Исполнитель
    (рука-код), закрывает _settle на следующем баре — движок этого не
    трогает, только будит по порядку.
    """
    def _emit(ev):
        if on_event:
            try: on_event(ev)
            except Exception: pass

    summary = {"woke": [], "verdicts": {}, "orders": None}

    # ── Искра (голова) ──
    ri = _call("iskra_live", "run_iskra", symbol=symbol, timeframe=timeframe)
    summary["woke"].append("A01")
    _emit({"type": "agent", "id": "A01", "ok": ri.get("ok"),
           "narrative": ri.get("narrative", "")})
    # ворота по спуску: нашёл точку — Совет собирается. нет — расходимся.
    descent = ri.get("descent", {}) or {}
    if not descent.get("found"):
        _emit({"type": "council_idle",
               "why": "спуск не нашёл точку — Совет не собирается"})
        summary["idle"] = True
        return summary

    # ── сенсоры ──
    for aid, mod, fn in _SENSORS:
        r = _call(mod, fn, symbol=symbol, timeframe=timeframe)
        summary["woke"].append(aid)
        _emit({"type": "agent", "id": aid, "ok": r.get("ok"),
               "narrative": r.get("narrative", "")})

    # ── Архивариус (память, без рынка — сам читает шину) ──
    ra = _call("arkhiv_live", "run_arkhiv")
    summary["woke"].append("A05")
    _emit({"type": "agent", "id": "A05", "ok": ra.get("ok"),
           "narrative": ra.get("narrative", "")})

    # ── трое трейдеров ──
    for aid, mod, fn in _TRADERS:
        r = _call(mod, fn, symbol=symbol, timeframe=timeframe)
        summary["woke"].append(aid)
        sig = r.get("signal", {}) or {}
        pre = {"A06": "brut", "A07": "avan", "A08": "cons"}[aid]
        summary["verdicts"][aid] = sig.get(f"{pre}_verdict")
        _emit({"type": "agent", "id": aid, "ok": r.get("ok"),
               "verdict": sig.get(f"{pre}_verdict"),
               "narrative": r.get("narrative", "")})

    # ── Исполнитель (рука-код открывает по табло) ──
    rex = _call("executor_live", "run_executor",
                symbol=symbol, timeframe=timeframe)
    summary["woke"].append("A09")
    esig = rex.get("signal", {}) or {}
    summary["orders"] = (esig.get("final_dna", {}) or {}).get("orders_sent")
    _emit({"type": "agent", "id": "A09", "ok": rex.get("ok"),
           "orders": summary["orders"],
           "narrative": rex.get("narrative", "")})

    return summary
