#!/usr/bin/env python3
"""
patch_cabinet_memory.py — Спринт 21 · Живая память Кабинета

Первые патчи уже применены (on_agent_done, on_agents_interact).
Этот скрипт добивает оставшееся:

ПАТЧ 1: grondheim_memory.py → sync_to_dna()
  Добавляем elif "cabinet_chat" — пластырь Локи:
  Stress -0.03, Light +0.02, Patience +0.01 (фиксировано, intensity игнорируется)

ПАТЧ 2: ui_cabinet.py → send()
  После ответа агента: record_sensory_event + sync_to_dna("cabinet_chat")
  Только когда talking_agent активен.

ЗАПУСК:
  python patch_cabinet_memory.py --dry-run
  python patch_cabinet_memory.py
"""

import sys, shutil, argparse
from pathlib import Path
from datetime import datetime

GRONDHEIM_PATH = Path("studio/grondheim_memory.py")
CABINET_PATH   = Path("studio/cabinet/ui_cabinet.py")
TIMESTAMP      = datetime.now().strftime("%Y%m%d_%H%M%S")


def backup(path):
    bak = path.with_suffix(f".bak_{TIMESTAMP}")
    shutil.copy2(path, bak)
    print(f"  [BAK] {path} → {bak.name}")


def apply_patch(path, old, new, label, dry):
    text = path.read_text(encoding="utf-8")
    if old not in text:
        print(f"  [SKIP] {label} — не найден")
        return False
    if dry:
        print(f"  [DRY]  {label} — найден ✓")
        return True
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    print(f"  [OK]   {label}")
    return True


# ═══════════════════════════════════════════
# ПАТЧ 1: sync_to_dna → cabinet_chat
# Вставляем перед строкой "# ── Записываем обратно ──"
# ═══════════════════════════════════════════

G_OLD = '''    elif event == "rest":
        stress = max(0, stress - 0.25 * i)
        patience = min(1, patience + 0.15 * i)
        light = min(1, light + 0.05 * i)

    # ── Записываем обратно ──'''

G_NEW = '''    elif event == "rest":
        stress = max(0, stress - 0.25 * i)
        patience = min(1, patience + 0.15 * i)
        light = min(1, light + 0.05 * i)

    elif event == "cabinet_chat":
        # Пластырь Кабинета · Спринт 21 · правила Локи
        # Фиксировано — intensity не влияет. Защита от водопада дофамина.
        # Полное восстановление только через streak ≥ 3 успешных ранов.
        stress   = max(0, stress   - 0.03)
        light    = min(1, light    + 0.02)
        patience = min(1, patience + 0.01)

    # ── Записываем обратно ──'''


# ═══════════════════════════════════════════
# ПАТЧ 2: send() → инжект памяти
# ═══════════════════════════════════════════

C_OLD = '''            reply = await call_openrouter(messages, state["model"], tools_schema=tools)
            print(f"[CABINET] 📥 Ответ: {len(reply)} симв.")

            nav_route = get_pending_nav()'''

C_NEW = '''            reply = await call_openrouter(messages, state["model"], tools_schema=tools)
            print(f"[CABINET] 📥 Ответ: {len(reply)} симв.")

            # ══ ЖИВАЯ ПАМЯТЬ КАБИНЕТА · Спринт 21 ══
            if talking:
                _cab_id   = talking["id"]
                _cab_dept = talking.get("dept", "")
                try:
                    from studio.grondheim_memory import record_sensory_event, sync_to_dna
                    record_sensory_event(
                        agent_id=_cab_id,
                        content=f"Архитектор: {text[:120]} / {_cab_id}: {reply[:120]}",
                        event_type="social",
                        source="cabinet",
                        emotional_weight=0.6,
                        dept=_cab_dept,
                    )
                    sync_to_dna(_cab_id, "cabinet_chat", intensity=1.0, dept=_cab_dept)
                    print(f"[CABINET] 🧠 {_cab_id}: память + micro-relief (-3% stress)")
                except Exception as _mem_err:
                    print(f"[CABINET] ⚠ Память: {_mem_err}")
            # ══ END ЖИВАЯ ПАМЯТЬ ══

            nav_route = get_pending_nav()'''


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    dry  = args.dry_run

    print(f"\n{'='*55}")
    print(f"patch_cabinet_memory.py · {'DRY RUN' if dry else 'ПРИМЕНЕНИЕ'}")
    print(f"{'='*55}\n")

    for p in [GRONDHEIM_PATH, CABINET_PATH]:
        if not p.exists():
            print(f"[ERROR] Не найден: {p}")
            sys.exit(1)

    if not dry:
        backup(GRONDHEIM_PATH)
        backup(CABINET_PATH)
        print()

    print("ПАТЧ 1 · grondheim_memory.py: cabinet_chat в sync_to_dna()")
    ok1 = apply_patch(GRONDHEIM_PATH, G_OLD, G_NEW,
                      "sync_to_dna: elif cabinet_chat (-3% stress)", dry)
    print()

    print("ПАТЧ 2 · ui_cabinet.py: send() → память + micro-relief")
    ok2 = apply_patch(CABINET_PATH, C_OLD, C_NEW,
                      "send(): record_sensory_event + sync_to_dna(cabinet_chat)", dry)
    print()

    print(f"{'='*55}")
    if dry:
        print(f"DRY RUN: П1={'✓' if ok1 else '✗'}  П2={'✓' if ok2 else '✗'}")
        if ok1 and ok2:
            print("Всё найдено — запускай без --dry-run.")
    else:
        print(f"ПРИМЕНЕНО: {sum([ok1,ok2])}/2")
        if ok1:
            print("  ✓ cabinet_chat: Stress-0.03 / Light+0.02 / Patience+0.01")
        if ok2:
            print("  ✓ send(): память в sensory + micro-relief после каждого ответа")
        print("\n  Полное восстановление — только streak ≥ 3 ✓")
    print(f"{'='*55}\n")


if __name__ == "__main__":
    main()
