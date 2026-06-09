"""
patch_iskra_prompt.py
=====================
Спринт 43 · 2026-06-09

Три точечные правки в studio/modules/trading/A01/forge/prompt.md:
  1. CHAIN_CONTRACT v1.0 → v1.1
  2. hooks.py → williams_core.py (источник расчёта market_data)
  3. ZERO_POINT_PROTOCOL v1.1 → v0.3 (исправление опечатки)

ЗАПУСК из корня проекта:
  python patch_iskra_prompt.py
"""

import shutil
from datetime import datetime
from pathlib import Path

PROMPT_PATH = Path("studio/modules/trading/A01/forge/prompt.md")

# ── Резервная копия ───────────────────────────────────────
ts  = datetime.now().strftime("%Y%m%d_%H%M%S")
bak = PROMPT_PATH.with_suffix(f".md.bak_{ts}")
shutil.copy2(PROMPT_PATH, bak)
print(f"[PATCH] 💾 Резервная копия: {bak}")

content = PROMPT_PATH.read_text(encoding="utf-8")

# ── 1. CHAIN_CONTRACT версия ──────────────────────────────
old1 = "CHAIN_CONTRACT v1.0 — двухслойный)"
new1 = "CHAIN_CONTRACT v1.1 — двухслойный)"
assert old1 in content, f"NOT FOUND: {old1!r}"
content = content.replace(old1, new1, 1)
print("[PATCH] ✅ CHAIN_CONTRACT v1.0 → v1.1")

# ── 2. hooks.py → williams_core.py ───────────────────────
old2 = "Расчёт на стороне `hooks.py` цеха по точным формулам Вильямса. Ты только читаешь:"
new2 = ("Расчёт на стороне `williams_core.py` — изолированного ядра математики Вильямса.\n"
        "`hooks.py` — только шлюз картриджа. Ты только читаешь:")
assert old2 in content, f"NOT FOUND: {old2!r}"
content = content.replace(old2, new2, 1)
print("[PATCH] ✅ hooks.py → williams_core.py")

# ── 3. ZERO_POINT_PROTOCOL версия (опечатка v1.1 → v0.3) ─
old3 = "ZERO_POINT_PROTOCOL v1.1"
new3 = "ZERO_POINT_PROTOCOL v0.3"
assert old3 in content, f"NOT FOUND: {old3!r}"
content = content.replace(old3, new3, 1)
print("[PATCH] ✅ ZERO_POINT_PROTOCOL v1.1 → v0.3")

# ── Запись ────────────────────────────────────────────────
PROMPT_PATH.write_text(content, encoding="utf-8")
print(f"\n[PATCH] 🏁 Готово: {PROMPT_PATH}")
