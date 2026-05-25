#!/usr/bin/env python3
"""
patch_interact_and_loka.py — Спринт 21 · Двойной удар

ПАТЧ 1: grondheim_memory.py → on_agents_interact()
  ПРОБЛЕМА: При каждой передаче контекста между агентами в пайплайне
  вызывается sync_to_dna() через DNA_EVENT_MAP. Это бэкдор —
  третий канал мутации DNA в обход единственного источника правды.

  Факт рабочего контакта → фиксируем в emotional_weights (резонанс).
  Химия DNA (Стресс/Свет) → только через _sync_feedback_scores_to_dna().

  ЧТО ВЫРЕЗАЕМ:
    DNA_EVENT_MAP = { "collaboration": ("good_work", 0.3), ... }
    sync_to_dna(agent_a, dna_event, ...)
    sync_to_dna(agent_b, dna_event, ...)

ПАТЧ 2: main.py → run_loka_filter_all()
  ПРОБЛЕМА: Голый вызов run_loka_filter_all() на уровне модуля.
  Если упадёт (нет агентов, битый JSON) — студия не запустится.
  Агенты в Cabinet и city_walker никогда не "стареют" без пайплайна.

  РЕШЕНИЕ: Оборачиваем в daemon-тред + try/except.
  Пульс города — не блокирует старт.

ЗАПУСК:
  python patch_interact_and_loka.py
  python patch_interact_and_loka.py --dry-run
"""

import sys
import shutil
import argparse
from pathlib import Path
from datetime import datetime

GRONDHEIM_PATH = Path("studio/grondheim_memory.py")
MAIN_PATH      = Path("main.py")
TIMESTAMP      = datetime.now().strftime("%Y%m%d_%H%M%S")


# ═══════════════════════════════════════════
# УТИЛИТЫ
# ═══════════════════════════════════════════

def backup(path: Path) -> Path:
    bak = path.with_suffix(f".bak_{TIMESTAMP}")
    shutil.copy2(path, bak)
    print(f"  [BAK] {path} → {bak.name}")
    return bak


def apply_patch(path: Path, old: str, new: str, label: str, dry_run: bool) -> bool:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        print(f"  [SKIP] {label} — фрагмент не найден (уже пропатчено?)")
        return False
    count = text.count(old)
    if count > 1:
        print(f"  [WARN] {label} — фрагмент найден {count} раз, заменяем первый")
    if dry_run:
        print(f"  [DRY]  {label} — найден, будет заменён")
        return True
    patched = text.replace(old, new, 1)
    path.write_text(patched, encoding="utf-8")
    print(f"  [OK]   {label}")
    return True


# ═══════════════════════════════════════════
# ПАТЧ 1: on_agents_interact() — вырезаем DNA_EVENT_MAP
# ═══════════════════════════════════════════

INTERACT_OLD = '''    # ══ SYNC TO DNA: взаимодействие меняет состояние ══
    DNA_EVENT_MAP = {
        "collaboration": ("good_work", 0.3),
        "conflict":      ("conflict", 0.7),
        "praise":        ("praised", 0.6),
        "critique":      ("criticized", 0.5),
        "rescue":        ("rescued", 0.8),
    }
    dna_event, base_intensity = DNA_EVENT_MAP.get(interaction_type, ("good_work", 0.2))
    sync_to_dna(agent_a, dna_event, intensity=base_intensity * quality, dept=dept)
    sync_to_dna(agent_b, dna_event, intensity=base_intensity * quality * 0.7, dept=dept)'''

INTERACT_NEW = '''    # ══ DNA-мутация из взаимодействий: ОТКЛЮЧЕНА · Спринт 21 ══
    # Факт контакта между агентами фиксируется в emotional_weights
    # (warmth, trust, respect) — это резонансная память, не химия.
    # Стресс/Свет/Уважение/Терпение меняются ТОЛЬКО через:
    #   _sync_feedback_scores_to_dna() → реальный QA score после рана.
    # Бэкдор через DNA_EVENT_MAP закрыт.'''


# ═══════════════════════════════════════════
# ПАТЧ 2: main.py — защищаем Loka-Filter
# ═══════════════════════════════════════════

MAIN_OLD = '''from studio.grondheim_memory import run_loka_filter_all
run_loka_filter_all()'''

MAIN_NEW = '''# ══ Loka-Filter: пульс города при старте · Спринт 21 ══
# Daemon-тред — не блокирует запуск студии если что-то пойдёт не так.
# Затухает сенсорная память ВСЕХ агентов: Cabinet, city_walker, резиденты.
# Без этого агенты не стареют вне пайплайна — город стоит.
import threading as _loka_thread
def _run_loka_filter():
    try:
        from studio.grondheim_memory import run_loka_filter_all
        run_loka_filter_all()
        print("[LOKA-FILTER] Пульс города завершён")
    except Exception as _err:
        print(f"[LOKA-FILTER] Ошибка: {_err}")
_loka_thread.Thread(
    target=_run_loka_filter,
    daemon=True,
    name="LokaFilterStartup",
).start()
print("[LOKA-FILTER] Пульс города запущен в фоне")
# ══ END Loka-Filter ══'''


# ═══════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="Двойной патч: бэкдор on_agents_interact + Loka-Filter"
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="только показать что изменится, не трогать файлы")
    args = parser.parse_args()
    dry = args.dry_run
    mode = "DRY RUN" if dry else "ПРИМЕНЕНИЕ"

    print(f"\n{'='*60}")
    print(f"patch_interact_and_loka.py · {mode}")
    print(f"{'='*60}\n")

    # Проверка файлов
    for p in [GRONDHEIM_PATH, MAIN_PATH]:
        if not p.exists():
            print(f"[ERROR] Файл не найден: {p}")
            print("  Запускай из корня проекта.")
            sys.exit(1)

    # Бэкапы
    if not dry:
        print("Создаём бэкапы...")
        backup(GRONDHEIM_PATH)
        backup(MAIN_PATH)
        print()

    # ── Патч 1 ──
    print("ПАТЧ 1 · grondheim_memory.py: on_agents_interact() → без sync_to_dna")
    ok1 = apply_patch(
        GRONDHEIM_PATH, INTERACT_OLD, INTERACT_NEW,
        "on_agents_interact(): DNA_EVENT_MAP + sync_to_dna → удалены", dry
    )
    print()

    # ── Патч 2 ──
    print("ПАТЧ 2 · main.py: run_loka_filter_all() → daemon-тред + try/except")
    ok2 = apply_patch(
        MAIN_PATH, MAIN_OLD, MAIN_NEW,
        "main.py: bare call → защищённый daemon-тред", dry
    )
    print()

    # ── Итог ──
    print(f"{'='*60}")
    if dry:
        print("DRY RUN завершён. Файлы не изменены.")
        print(f"  Патч 1 (on_agents_interact): {'найден ✓' if ok1 else 'НЕ найден ✗'}")
        print(f"  Патч 2 (main.py Loka-Filter): {'найден ✓' if ok2 else 'НЕ найден ✗'}")
        if ok1 and ok2:
            print("\nВсё готово — запускай без --dry-run.")
        else:
            print("\nЧасть фрагментов не найдена — возможно уже пропатчено.")
    else:
        applied = sum([ok1, ok2])
        print(f"ПРИМЕНЕНО ПАТЧЕЙ: {applied}/2")
        print()
        if ok1:
            print("  ✓ on_agents_interact(): DNA_EVENT_MAP удалён")
            print("    Взаимодействия → только emotional_weights (резонанс)")
        if ok2:
            print("  ✓ main.py: Loka-Filter в daemon-треде")
            print("    Город стареет при каждом старте студии")
        print()
        print("Единственные источники DNA-мутаций:")
        print("  • _sync_feedback_scores_to_dna() → после QA (пайплайн)")
        print("  • sync_to_dna() напрямую — только для city_walker/Маяка")
        print()
        print("Бэкапы:")
        print(f"  studio/grondheim_memory.bak_{TIMESTAMP}")
        print(f"  main.bak_{TIMESTAMP}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
