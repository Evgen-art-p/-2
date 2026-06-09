"""
patch_trading_state.py
======================
Спринт 43 · 2026-06-09

ЗАДАЧА — закрыть две дыры памяти Торгового Цеха:
  Дыра 1: состояние Искры между прогонами (t1_status — машина состояний
          живёт несколько баров; без памяти CONFIRMED недостижим)
  Дыра 2: открытые позиции между прогонами (exit_bell не знает что закрывать)

РЕШЕНИЕ:
  studio/modules/trading/state/trading_state.json — рабочая память цеха.
  on_before_run  → читает state → кладёт в chain_data
  on_after_agent (A09) → сохраняет state обратно

КОНТРАКТ НЕ МЕНЯЕТСЯ:
  Искра как читала history_dna из chain_data — так и читает.
  Просто теперь history_dna реально переживает прогон.

ЗАПУСК из корня проекта (ПОСЛЕ patch_williams_core.py):
  python patch_trading_state.py
"""

import json
import shutil
from datetime import datetime
from pathlib import Path

HOOKS_PATH = Path("studio/modules/trading/hooks.py")
STATE_DIR  = Path("studio/modules/trading/state")
STATE_FILE = STATE_DIR / "trading_state.json"

# ── Резервная копия ───────────────────────────────────────
ts  = datetime.now().strftime("%Y%m%d_%H%M%S")
bak = HOOKS_PATH.with_suffix(f".py.bak_{ts}")
shutil.copy2(HOOKS_PATH, bak)
print(f"[PATCH] 💾 Резервная копия: {bak}")

content = HOOKS_PATH.read_text(encoding="utf-8")

# ── Проверка: это hooks v2.0 (шлюз), не старый монолит ───
assert "from .williams_core import" in content, \
    "Это старый hooks.py! Сначала запусти patch_williams_core.py"

# ── Идемпотентность ───────────────────────────────────────
if "trading_state.json" in content:
    print("[PATCH] ⏭  Уже применён — trading_state найден в hooks.py. Выход.")
    raise SystemExit(0)


# ════════════════════════════════════════════════════════════
# ПРАВКА 1 — STATE_PATH + функции load/save после ATLAS_PATH
# ════════════════════════════════════════════════════════════

old1 = '''# ── Путь к Атласу Ошибок ──────────────────────────────────
ATLAS_PATH = Path("economy/data/atlas_trading.jsonl")'''

new1 = '''# ── Путь к Атласу Ошибок ──────────────────────────────────
ATLAS_PATH = Path("economy/data/atlas_trading.jsonl")

# ── Рабочая память цеха (Спринт 43) ──────────────────────
# Закрывает две дыры:
#   1. Состояние Искры между прогонами (t1_status — машина состояний)
#   2. Открытые позиции между прогонами (что закрывать по exit_bell)
STATE_PATH = Path("studio/modules/trading/state/trading_state.json")

_DEFAULT_STATE = {
    "version": 1,
    "updated": None,
    "iskra": {
        "t1_status":        "NOT_FOUND",
        "zero_point_price": None,
        "history_dna":      "",
    },
    "positions": [],
}


def load_trading_state() -> dict:
    """Читает рабочую память цеха. Если файла нет — дефолт."""
    if not STATE_PATH.exists():
        return json.loads(json.dumps(_DEFAULT_STATE))
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        print(f"[STATE] ⚠️  Повреждён trading_state.json ({e}) — дефолт")
        return json.loads(json.dumps(_DEFAULT_STATE))


def save_trading_state(tstate: dict):
    """Сохраняет рабочую память цеха."""
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    tstate["updated"] = datetime.now().isoformat()
    STATE_PATH.write_text(
        json.dumps(tstate, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[STATE] 💾 trading_state сохранён: "
          f"t1={tstate['iskra']['t1_status']}, "
          f"позиций={len(tstate['positions'])}")'''

assert old1 in content, f"NOT FOUND: блок ATLAS_PATH"
content = content.replace(old1, new1, 1)
print("[PATCH] ✅ 1/3 — STATE_PATH + load/save добавлены")


# ════════════════════════════════════════════════════════════
# ПРАВКА 2 — on_before_run: читаем state в chain_data
# ════════════════════════════════════════════════════════════

old2 = '''    print(f"\\n[TRADING] ⚔️  Военный Совет запускается")
    print(f"[TRADING]    Символ: {symbol} | ТФ: {timeframe}")'''

new2 = '''    print(f"\\n[TRADING] ⚔️  Военный Совет запускается")
    print(f"[TRADING]    Символ: {symbol} | ТФ: {timeframe}")

    # ── Рабочая память цеха: загружаем ПЕРЕД любым режимом ──
    tstate = load_trading_state()
    cd = state.setdefault("chain_data", {})
    cd["history_dna"]          = tstate["iskra"].get("history_dna", "")
    cd["prev_t1_status"]       = tstate["iskra"].get("t1_status", "NOT_FOUND")
    cd["prev_zero_point_price"] = tstate["iskra"].get("zero_point_price")
    cd["open_positions"]       = tstate.get("positions", [])
    if cd["open_positions"]:
        print(f"[STATE] 📂 Открытых позиций: {len(cd['open_positions'])}")
    if cd["prev_t1_status"] != "NOT_FOUND":
        print(f"[STATE] 📂 Искра помнит: t1={cd['prev_t1_status']}, "
              f"Точка Ноль={cd['prev_zero_point_price']}")'''

assert old2 in content, "NOT FOUND: print-блок on_before_run"
content = content.replace(old2, new2, 1)
print("[PATCH] ✅ 2/3 — on_before_run читает trading_state")

# Убираем старую строку history_dna (теперь загружается из state-файла)
old2b = '''    state.setdefault("chain_data", {})["market_data"] = market_data
    state.setdefault("chain_data", {})["history_dna"] = \\
        state["chain_data"].get("history_dna", {})'''

new2b = '''    state.setdefault("chain_data", {})["market_data"] = market_data
    # history_dna уже загружен из trading_state.json выше'''

assert old2b in content, "NOT FOUND: старая строка history_dna"
content = content.replace(old2b, new2b, 1)
print("[PATCH] ✅ 2b — старая инициализация history_dna убрана")


# ════════════════════════════════════════════════════════════
# ПРАВКА 3 — on_after_agent A09: сохраняем state
# ════════════════════════════════════════════════════════════

old3 = '''    if agent_id == "A09":
        results = state.get("results", {})
        brut_v  = _extract_verdict(results.get("A06", {}), "brut_verdict")
        avan_v  = _extract_verdict(results.get("A07", {}), "avan_verdict")
        cons_v  = _extract_verdict(results.get("A08", {}), "cons_verdict")'''

new3 = '''    if agent_id == "A09":
        results = state.get("results", {})
        brut_v  = _extract_verdict(results.get("A06", {}), "brut_verdict")
        avan_v  = _extract_verdict(results.get("A07", {}), "avan_verdict")
        cons_v  = _extract_verdict(results.get("A08", {}), "cons_verdict")

        # ── Сохраняем рабочую память цеха (ДО любого stop) ──
        _persist_trading_state(state)'''

assert old3 in content, "NOT FOUND: A09 branch on_after_agent"
content = content.replace(old3, new3, 1)
print("[PATCH] ✅ 3/3 — on_after_agent A09 сохраняет trading_state")


# ════════════════════════════════════════════════════════════
# ПРАВКА 4 — функция _persist_trading_state в утилиты
# ════════════════════════════════════════════════════════════

old4 = '''def _extract_verdict(agent_result: dict, key: str) -> Optional[str]:'''

new4 = '''def _persist_trading_state(state: dict):
    """
    Собирает из результатов прогона то что должно пережить прогон:
      — состояние Искры (t1_status, zero_point_price, history_dna)
      — открытые позиции (из execution_log A09)
    И сохраняет в trading_state.json.

    Логика закрытия позиций (по exit_bell / стопу) — ШАГ 8,
    промт Исполнителя. Здесь только хранение.
    """
    results = state.get("results", {})
    chain   = state.get("chain_data", {})
    tstate  = load_trading_state()

    # ── Состояние Искры ──
    iskra_out = (results.get("A01", {}).get("meta", {}) or {}) \\
        .get("my_output", {}) or {}
    if iskra_out:
        tstate["iskra"]["t1_status"] = \\
            iskra_out.get("t1_status", tstate["iskra"]["t1_status"])
        tstate["iskra"]["zero_point_price"] = \\
            iskra_out.get("zero_point_price",
                          tstate["iskra"]["zero_point_price"])
        if iskra_out.get("history_dna"):
            tstate["iskra"]["history_dna"] = iskra_out["history_dna"]
    elif chain.get("t1_status"):
        # fallback: Искра писала прямо в chain_data
        tstate["iskra"]["t1_status"] = chain["t1_status"]
        if chain.get("zero_point_price") is not None:
            tstate["iskra"]["zero_point_price"] = chain["zero_point_price"]
        if chain.get("history_dna"):
            tstate["iskra"]["history_dna"] = chain["history_dna"]

    # ── Открытые позиции: новые APPROVED из execution_log ──
    a09_out = (results.get("A09", {}).get("meta", {}) or {}) \\
        .get("my_output", {}) or {}
    exec_log = a09_out.get("execution_log", []) or []
    bar_time = chain.get("market_data", {}).get("bar_time", "")

    for order in exec_log:
        if order.get("verdict") != "APPROVED":
            continue
        if order.get("status") not in ("PAPER", "LIVE"):
            continue
        tstate["positions"].append({
            "trader":    order.get("trader"),
            "magic":     order.get("magic"),
            "entry":     order.get("entry"),
            "stop":      order.get("stop"),
            "tp":        order.get("tp"),
            "lot":       order.get("lot"),
            "status":    "OPEN",
            "mode":      order.get("status"),       # PAPER | LIVE
            "opened_at": bar_time,
            "pnl":       None,
        })

    save_trading_state(tstate)


def _extract_verdict(agent_result: dict, key: str) -> Optional[str]:'''

assert old4 in content, "NOT FOUND: _extract_verdict"
content = content.replace(old4, new4, 1)
print("[PATCH] ✅ 4 — _persist_trading_state добавлена")


# ── Запись hooks.py ───────────────────────────────────────
HOOKS_PATH.write_text(content, encoding="utf-8")
print(f"[PATCH] ✅ Перезаписан: {HOOKS_PATH}")

# ── Начальный trading_state.json (если нет) ──────────────
if not STATE_FILE.exists():
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    init_state = {
        "version": 1,
        "updated": datetime.now().isoformat(),
        "iskra": {
            "t1_status":        "NOT_FOUND",
            "zero_point_price": None,
            "history_dna":      "",
        },
        "positions": [],
    }
    STATE_FILE.write_text(
        json.dumps(init_state, ensure_ascii=False, indent=2),
        encoding="utf-8")
    print(f"[PATCH] ✅ Создан начальный: {STATE_FILE}")
else:
    print(f"[PATCH] ⏭  {STATE_FILE} уже существует — не трогаю")

print("\n[PATCH] 🏁 Готово.")
print("  Проверка: python -c \"from studio.modules.trading.hooks import load_trading_state; print(load_trading_state())\"")
