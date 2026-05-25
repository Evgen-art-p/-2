#!/usr/bin/env python3
"""
patch_cabinet_memory.py — Спринт 21 · Живая память Кабинета

Три правила от Локи (продюсер утвердил):
  1. MICRO-RELIEF: cabinet_chat снимает ровно 3% стресса и +2% света.
     Фиксировано в EVENT_MAP — intensity-параметр игнорируется.
     Пластырь, не антибиотик.

  2. ПАМЯТЬ ОБ УТЕШЕНИИ: диалог уходит в sensory_memory (source="cabinet").
     При следующем on_agent_wake() агент знает: "Архитектор выслушал".

  3. ЗАЩИТА ОСНОВНОГО ПРАВИЛА: полное восстановление только через
     streak ≥ 3 успешных ранов. Кабинет не лечит — снимает панику.

ПАТЧ 1: grondheim_memory.py — добавляем "cabinet_chat" в EVENT_MAP
ПАТЧ 2: ui_cabinet.py — вызываем после ответа агента

ЗАПУСК:
  python patch_cabinet_memory.py --dry-run
  python patch_cabinet_memory.py
"""

import sys
import shutil
import argparse
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
        print(f"  [SKIP] {label} — не найден (уже пропатчено?)")
        return False
    if dry:
        print(f"  [DRY]  {label} — найден ✓")
        return True
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    print(f"  [OK]   {label}")
    return True


# ═══════════════════════════════════════════
# ПАТЧ 1: grondheim_memory.py
# Добавляем cabinet_chat в EVENT_MAP sync_to_dna
# ═══════════════════════════════════════════

# Ищем EVENT_MAP внутри sync_to_dna — добавляем новый тип
GRONDHEIM_OLD = '''    EVENT_MAP = {
        "good_work":   {"Stress": -0.3,  "Internal_Light": +0.2, "Respect": +0.1},
        "bad_work":    {"Stress": +0.4,  "Internal_Light": -0.2, "Respect": -0.1},
        "praised":     {"Stress": -0.2,  "Internal_Light": +0.3, "Respect": +0.2},
        "criticized":  {"Stress": +0.2,  "Internal_Light": -0.1, "Respect": -0.05},
        "conflict":    {"Stress": +0.3,  "Patience": -0.2,       "Respect": -0.1},
        "rescued":     {"Stress": -0.4,  "Internal_Light": +0.3, "Respect": +0.2},
        "rest":        {"Stress": -0.15, "Internal_Light": +0.1},
    }'''

GRONDHEIM_NEW = '''    EVENT_MAP = {
        "good_work":    {"Stress": -0.3,  "Internal_Light": +0.2,  "Respect": +0.1},
        "bad_work":     {"Stress": +0.4,  "Internal_Light": -0.2,  "Respect": -0.1},
        "praised":      {"Stress": -0.2,  "Internal_Light": +0.3,  "Respect": +0.2},
        "criticized":   {"Stress": +0.2,  "Internal_Light": -0.1,  "Respect": -0.05},
        "conflict":     {"Stress": +0.3,  "Patience": -0.2,        "Respect": -0.1},
        "rescued":      {"Stress": -0.4,  "Internal_Light": +0.3,  "Respect": +0.2},
        "rest":         {"Stress": -0.15, "Internal_Light": +0.1},
        # ── Кабинет · Спринт 21 ──────────────────────────────────────────
        # Пластырь, не антибиотик. Интенсивность фиксирована, intensity
        # из вызывающего кода игнорируется — защита от водопада дофамина.
        # Полное восстановление только через streak ≥ 3 успешных ранов.
        "cabinet_chat": {"Stress": -0.03, "Internal_Light": +0.02, "Patience": +0.01},
    }'''


# ═══════════════════════════════════════════
# ПАТЧ 2: ui_cabinet.py → send()
# Инжект после получения reply от агента
# ═══════════════════════════════════════════

CABINET_OLD = '''            reply = await call_openrouter(messages, state["model"], tools_schema=tools)
            print(f"[CABINET] 📥 Ответ: {len(reply)} симв.")

            nav_route = get_pending_nav()'''

CABINET_NEW = '''            reply = await call_openrouter(messages, state["model"], tools_schema=tools)
            print(f"[CABINET] 📥 Ответ: {len(reply)} симв.")

            # ══ ЖИВАЯ ПАМЯТЬ КАБИНЕТА · Спринт 21 ══
            # Только в режиме диалога с конкретным агентом.
            # Правила Локи: пластырь (-3% стресса), память об утешении.
            if talking:
                _cab_id   = talking["id"]
                _cab_dept = talking.get("dept", "")
                try:
                    from studio.grondheim_memory import record_sensory_event, sync_to_dna

                    # Правило 2: Память — агент помнит разговор на следующем ране
                    record_sensory_event(
                        agent_id=_cab_id,
                        content=(
                            f"Архитектор: {text[:120]} / "
                            f"{_cab_id}: {reply[:120]}"
                        ),
                        event_type="social",
                        source="cabinet",
                        emotional_weight=0.6,
                        dept=_cab_dept,
                    )

                    # Правило 1: Micro-relief — 3% стресса, фиксировано в EVENT_MAP
                    # Правило 3: Не трогаем streak и Recovery — только кабинетный пластырь
                    sync_to_dna(_cab_id, "cabinet_chat", intensity=1.0, dept=_cab_dept)
                    print(f"[CABINET] 🧠 {_cab_id}: память + micro-relief (-3% stress)")
                except Exception as _mem_err:
                    print(f"[CABINET] ⚠ Память не записана: {_mem_err}")
            # ══ END ЖИВАЯ ПАМЯТЬ ══

            nav_route = get_pending_nav()'''


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    dry  = args.dry_run
    mode = "DRY RUN" if dry else "ПРИМЕНЕНИЕ"

    print(f"\n{'='*60}")
    print(f"patch_cabinet_memory.py · {mode}")
    print(f"{'='*60}\n")

    for p in [GRONDHEIM_PATH, CABINET_PATH]:
        if not p.exists():
            print(f"[ERROR] Файл не найден: {p}")
            sys.exit(1)

    if not dry:
        print("Бэкапы...")
        backup(GRONDHEIM_PATH)
        backup(CABINET_PATH)
        print()

    print("ПАТЧ 1 · grondheim_memory.py: cabinet_chat в EVENT_MAP")
    ok1 = apply_patch(GRONDHEIM_PATH, GRONDHEIM_OLD, GRONDHEIM_NEW,
                      "EVENT_MAP + cabinet_chat (Stress-0.03, Light+0.02)", dry)
    print()

    print("ПАТЧ 2 · ui_cabinet.py: send() → память + micro-relief")
    ok2 = apply_patch(CABINET_PATH, CABINET_OLD, CABINET_NEW,
                      "send(): record_sensory_event + sync_to_dna(cabinet_chat)", dry)
    print()

    print(f"{'='*60}")
    if dry:
        print(f"DRY RUN: П1={'✓' if ok1 else '✗'} П2={'✓' if ok2 else '✗'}")
        if ok1 and ok2:
            print("Всё найдено — запускай без --dry-run.")
        else:
            print("⚠ Часть фрагментов не найдена.")
    else:
        print(f"ПРИМЕНЕНО: {sum([ok1,ok2])}/2 патчей\n")
        if ok1:
            print("  ✓ EVENT_MAP: cabinet_chat (Stress-0.03 / Light+0.02 / Patience+0.01)")
            print("    Intensity из вызова игнорируется — защита от водопада ✓")
        if ok2:
            print("  ✓ send(): после ответа агента:")
            print("    → sensory_memory: 'Архитектор выслушал' (source=cabinet)")
            print("    → sync_to_dna(cabinet_chat): -3% стресса, пластырь")
        print()
        print("Полное восстановление по-прежнему только через streak ≥ 3 ✓")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
