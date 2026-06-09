"""
patch_contract_sync.py
======================
Спринт 43 · 2026-06-10

Доделка после patch_tribunal.py (промты и hooks встали, контракт упал
на точном совпадении строки). Этот скрипт ищет ГИБКО:

  1. Строка статусов Моржа с MATURE → три статуса + пояснение
  2. "morj_status=MATURE" → "morj_status=AWAKE" (везде)
  3. "требую MATURE" → "требую AWAKE" (везде)
  4. Версия футера → v1.2

Перед правкой печатает все строки с MATURE — видно что меняем.

ЗАПУСК из корня проекта:
  python patch_contract_sync.py
"""

import re
import shutil
from datetime import datetime
from pathlib import Path

CONTRACT = Path("studio/modules/trading/CHAIN_CONTRACT.md")

cc = CONTRACT.read_text(encoding="utf-8")

# ── Идемпотентность ───────────────────────────────────────
if "MATURE" not in cc:
    print("[PATCH] ⏭  MATURE в контракте не найден — уже синхронизирован. Выход.")
    raise SystemExit(0)

# ── Диагностика: показываем что нашли ─────────────────────
print("[PATCH] 🔍 Строки с MATURE в контракте:")
for i, line in enumerate(cc.splitlines(), 1):
    if "MATURE" in line:
        print(f"  {i}: {line.strip()}")
print()

# ── Резервная копия ───────────────────────────────────────
ts  = datetime.now().strftime("%Y%m%d_%H%M%S")
bak = CONTRACT.with_suffix(f".md.bak_{ts}")
shutil.copy2(CONTRACT, bak)
print(f"[PATCH] 💾 Резервная копия: {bak}\n")

changes = 0

# ── 1. Строка статусов Моржа (любой формат backtick-ов) ──
status_line_re = re.compile(
    r"^(.*morj_status.*SLEEPING.*WAKING.*AWAKE.*\|\s*`?MATURE`?.*)$",
    re.MULTILINE)
m = status_line_re.search(cc)
if m:
    new_line = ("`morj_status`: `SLEEPING` | `WAKING` | `AWAKE`\n"
                "(AWAKE = bars_open ≥ 8 = зрелый; отдельного MATURE-статуса нет, "
                "зрелость также в `alligator_state.mature`)")
    cc = cc[:m.start(1)] + new_line + cc[m.end(1):]
    changes += 1
    print("[PATCH] ✅ 1 — строка статусов: MATURE убран из перечня")
else:
    print("[PATCH] ⚠️  1 — строка статусов с MATURE не найдена (возможно уже другой формат)")

# ── 2. morj_status=MATURE → AWAKE (везде) ─────────────────
n = cc.count("morj_status=MATURE")
if n:
    cc = cc.replace("morj_status=MATURE", "morj_status=AWAKE")
    changes += n
    print(f"[PATCH] ✅ 2 — morj_status=MATURE → AWAKE ({n} шт)")

# ── 3. «требую MATURE» → «требую AWAKE» (везде) ───────────
n = cc.count("требую MATURE")
if n:
    cc = cc.replace("требую MATURE", "требую AWAKE")
    changes += n
    print(f"[PATCH] ✅ 3 — «требую MATURE» → «требую AWAKE» ({n} шт)")

# ── 4. Версия футера ──────────────────────────────────────
ver_re = re.compile(r"\*CHAIN_CONTRACT v1\.\d+ · Торговый Цех · [\d-]+\*")
m = ver_re.search(cc)
if m and "v1.2" not in m.group(0):
    cc = cc[:m.start()] + (
        "*CHAIN_CONTRACT v1.2 · Торговый Цех · 2026-06-10*\n"
        "*v1.2: morj_status — три статуса (MATURE убран, AWAKE = зрелый); "
        "Консерватор требует AWAKE*"
    ) + cc[m.end():]
    changes += 1
    print("[PATCH] ✅ 4 — версия → v1.2")

# ── Остатки MATURE? ───────────────────────────────────────
leftover = [l.strip() for l in cc.splitlines() if "MATURE" in l]
if leftover:
    print("\n[PATCH] ⚠️  ОСТАЛИСЬ строки с MATURE — проверь глазами:")
    for l in leftover:
        print(f"   {l}")

if changes == 0:
    print("\n[PATCH] ❌ Ни одной правки не применено — покажи мне файл, разберём.")
    raise SystemExit(1)

CONTRACT.write_text(cc, encoding="utf-8")
print(f"\n[PATCH] ✅ Записан: {CONTRACT} ({changes} правок)")
print("[PATCH] 🏁 Готово.")
