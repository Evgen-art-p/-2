#!/usr/bin/env python3
"""
patch_recovery_freeze.py — Фикс 2: заморозка RECOVERY во время работы агента

ПРОБЛЕМА (точная):
  В sync_to_dna() есть два места где стресс гасится фоном:

  1. event == "walk_rest" → stress -= 0.02
     Это нормально — агент идёт на прогулку.
     НО: walk_rest вызывается из city_walker.py для ВСЕХ агентов,
     включая тех кто сейчас в цеху (work_start).

  2. Recovery Mechanics: if streak >= 3 → Stress = 0.0 БЕЗУСЛОВНО
     Это критично: даже если Виктор дал NEEDS_REWORK и мы записали
     bad_work(0.7) → streak мог уже быть >= 3 → стресс сбрасывается в 0.
     Порядок событий: Виктор → bad_work → streak сбивается в -1 → OK.
     НО: если walk_rest приходит ПОСЛЕ bad_work, streak снова растёт
     и следующий ран может снова триггернуть Recovery.

РЕШЕНИЕ:
  1. Добавляем хелпер _is_agent_working() — проверяет city_pulse.jsonl
  2. В event == "walk_rest" добавляем guard: если агент в цеху — пропускаем
  3. В Recovery block: дополнительное условие — не сбрасываем если работает
"""

import sys
import shutil
import py_compile
import tempfile
from pathlib import Path
from datetime import datetime

DRY_RUN = "--dry-run" in sys.argv
BACKUP_DIR = Path("_patch_backups") / f"recovery_freeze_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

def backup(path: Path):
    if DRY_RUN:
        print(f"  [DRY] backup {path}")
        return
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, BACKUP_DIR / path.name)
    print(f"  ✓ backup → {BACKUP_DIR / path.name}")

def apply(path: Path, old: str, new: str, desc: str) -> bool:
    if not path.exists():
        print(f"  ❌ Файл не найден: {path}")
        return False
    content = path.read_text(encoding="utf-8")
    if old not in content:
        print(f"  ⚠ Не найдено: {desc}")
        return False
    new_content = content.replace(old, new, 1)
    if DRY_RUN:
        print(f"  [DRY] {path.name}: {desc}")
        return True
    backup(path)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8",
                                     suffix=".py", delete=False) as tmp:
        tmp.write(new_content)
        tmp_path = Path(tmp.name)
    try:
        py_compile.compile(str(tmp_path), doraise=True)
    except py_compile.PyCompileError as e:
        tmp_path.unlink()
        print(f"  ❌ Синтакс-ошибка: {e}")
        return False
    shutil.move(str(tmp_path), str(path))
    print(f"  ✓ {path.name}: {desc}")
    return True


# ══════════════════════════════════════════════════════════════════
# ПАТЧ 1: добавляем хелпер _is_agent_working() перед sync_to_dna
# ══════════════════════════════════════════════════════════════════

HELPER_OLD = "def sync_to_dna(\n    agent_id: str,"

HELPER_NEW = (
    "def _is_agent_working(agent_id: str) -> bool:\n"
    '    """Проверяет находится ли агент в рабочем статусе по city_pulse.\n'
    "    Если да — walk_rest и RECOVERY не должны сбрасывать стресс.\n"
    '    """\n'
    "    try:\n"
    "        pulse_path = Path(\"studio/city_pulse.jsonl\")\n"
    "        if not pulse_path.exists():\n"
    "            return False\n"
    "        lines = pulse_path.read_text(encoding=\"utf-8\").splitlines()[-500:]\n"
    "        for line in reversed(lines):\n"
    "            try:\n"
    "                entry = json.loads(line)\n"
    "                if entry.get(\"agent\") == agent_id:\n"
    "                    return entry.get(\"status\") in (\"work_start\", \"working\")\n"
    "            except Exception:\n"
    "                continue\n"
    "    except Exception:\n"
    "        pass\n"
    "    return False\n"
    "\n"
    "\n"
    "def sync_to_dna(\n"
    "    agent_id: str,"
)


# ══════════════════════════════════════════════════════════════════
# ПАТЧ 2: walk_rest guard — не снижаем стресс если агент в цеху
# ══════════════════════════════════════════════════════════════════

WALK_OLD = (
    "    elif event == \"walk_rest\":\n"
    "        # Прогулка по городу · Спринт 21 · хард-лимит Локи\n"
    "        # Мягче кабинета: нет живого разговора с Архитектором.\n"
    "        # Фиксировано — intensity игнорируется. Прогулка не чит-код.\n"
    "        # Полный сброс стресса только через streak ≥ 3 ранов — железное правило.\n"
    "        stress   = max(0, stress   - 0.02)\n"
    "        light    = min(1, light    + 0.01)\n"
    "        patience = min(1, patience + 0.01)"
)

WALK_NEW = (
    "    elif event == \"walk_rest\":\n"
    "        # Прогулка по городу · Спринт 21 · хард-лимит Локи\n"
    "        # ПАТЧ recovery_freeze: если агент в цеху — прогулка не снижает стресс\n"
    "        # Стресс от критики Виктора должен оставаться до конца рана\n"
    "        if _is_agent_working(agent_id):\n"
    "            print(f\"[RECOVERY] 🔒 {agent_id}: в цеху — walk_rest заморожен\")\n"
    "        else:\n"
    "            stress   = max(0, stress   - 0.02)\n"
    "            light    = min(1, light    + 0.01)\n"
    "            patience = min(1, patience + 0.01)"
)


# ══════════════════════════════════════════════════════════════════
# ПАТЧ 3: Recovery block guard — не сбрасываем стресс если в цеху
# ══════════════════════════════════════════════════════════════════

RECOVERY_OLD = (
    "    # ══ Recovery Mechanics (Спринт 16) ══\n"
    "    # 3 победы подряд — стресс сбрасывается физиологически\n"
    "    if streak >= 3:\n"
    "        old_stress = dynamic[\"Stress\"]\n"
    "        dynamic[\"Stress\"] = 0.0\n"
    "        dynamic[\"Internal_Light\"] = min(1.0, round(dynamic[\"Internal_Light\"] + 0.05, 3))\n"
    "        print(\n"
    "            f\"[RECOVERY] 🌟 {agent_id}: streak={streak} → \"\n"
    "            f\"Stress сброшен ({old_stress:.2f} → 0.0), \"\n"
    "            f\"Light={dynamic['Internal_Light']:.2f}\"\n"
    "        )\n"
    "    # ══ END Recovery ══"
)

RECOVERY_NEW = (
    "    # ══ Recovery Mechanics (Спринт 16) ══\n"
    "    # 3 победы подряд — стресс сбрасывается физиологически\n"
    "    # ПАТЧ recovery_freeze: не сбрасываем если агент сейчас в цеху\n"
    "    if streak >= 3 and not _is_agent_working(agent_id):\n"
    "        old_stress = dynamic[\"Stress\"]\n"
    "        dynamic[\"Stress\"] = 0.0\n"
    "        dynamic[\"Internal_Light\"] = min(1.0, round(dynamic[\"Internal_Light\"] + 0.05, 3))\n"
    "        print(\n"
    "            f\"[RECOVERY] 🌟 {agent_id}: streak={streak} → \"\n"
    "            f\"Stress сброшен ({old_stress:.2f} → 0.0), \"\n"
    "            f\"Light={dynamic['Internal_Light']:.2f}\"\n"
    "        )\n"
    "    elif streak >= 3:\n"
    "        print(f\"[RECOVERY] 🔒 {agent_id}: streak={streak} но в цеху — Recovery заморожен\")\n"
    "    # ══ END Recovery ══"
)


def main():
    print("=" * 60)
    print("ПАТЧ: Заморозка RECOVERY во время работы агента")
    print("=" * 60)
    if DRY_RUN:
        print("DRY-RUN\n")

    path = Path("studio/grondheim_memory.py")

    print("\n[1/3] grondheim_memory.py — хелпер _is_agent_working()")
    ok1 = apply(path, HELPER_OLD, HELPER_NEW,
                "читает city_pulse.jsonl чтобы знать статус агента")

    print("\n[2/3] grondheim_memory.py — walk_rest guard")
    ok2 = apply(path, WALK_OLD, WALK_NEW,
                "агент в цеху → прогулка не снижает стресс")

    print("\n[3/3] grondheim_memory.py — Recovery block guard")
    ok3 = apply(path, RECOVERY_OLD, RECOVERY_NEW,
                "streak>=3 но в цеху → стресс не сбрасывается в 0")

    print("\n" + "=" * 60)
    if DRY_RUN:
        print("DRY-RUN завершён.")
        return

    applied = sum([ok1, ok2, ok3])
    if applied > 0:
        print(f"✅ Применено {applied}/3 патчей!")
        print(f"   Бекапы: {BACKUP_DIR}")
        print()
        print("Как теперь работает RECOVERY:")
        print("  • Агент гуляет (нет в city_pulse work_start):")
        print("    → walk_rest снижает стресс нормально")
        print("    → streak>=3 сбрасывает стресс в 0")
        print("  • Агент в цеху (work_start в city_pulse):")
        print("    → walk_rest заморожен — стресс не трогаем")
        print("    → Recovery заморожен — стресс от Виктора остаётся")
        print()
        print("Перезапусти: python main.py")
    else:
        print("⚠ Ничего не применено")


if __name__ == "__main__":
    main()
