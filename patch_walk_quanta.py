"""
patch_walk_quanta.py
=================================================================
Три фикса в city_walker.py:

1. walk_quantum_chain — принимает max_quanta (default=3)
   Лока не ходит по 17 кругов.

2. run_city_walk_evening — пробрасывает max_quanta в chain

3. Пара-встреча: один раз за прогулку между одной парой.
   Джем и Лока не встречаются 8 раз подряд.

Применение:
  python patch_walk_quanta.py [--dry-run]
"""

import sys
import shutil
from pathlib import Path
from datetime import datetime

TARGET = Path("studio/city_walker.py")
BACKUP_DIR = Path("_patch_backups")

# ─── Фикс 1: walk_quantum_chain — добавляем max_quanta ───────────────────────

OLD_CHAIN_SIG = """async def walk_quantum_chain(
    agent: dict,
    city_state: dict,
    locations: list,
    mode: str = "evening",
    on_progress=None,
) -> list[dict]:"""

NEW_CHAIN_SIG = """async def walk_quantum_chain(
    agent: dict,
    city_state: dict,
    locations: list,
    mode: str = "evening",
    on_progress=None,
    max_quanta: int = 3,
) -> list[dict]:"""

OLD_CHAIN_DOC = """    mode="morning" → 1 квант, быстро, разогрев перед раном
    mode="evening" → N квантов, бюджет из Light+Stubbornness"""

NEW_CHAIN_DOC = """    mode="morning" → 1 квант, быстро, разогрев перед раном
    mode="evening" → до max_quanta квантов (default=3), бюджет из Light+Stubbornness"""

OLD_CHAIN_LOG = """    mode_label = "🌅 утро" if mode == "morning" else "🏠 вечер"
    await log(f"{mode_label} | {name} | бюджет внимания: {budget:.1f}")

    results = []
    quantum_n = 0

    while attention > 0.12:  # порог "домой" — меньше этого уже не хватит на квант"""

NEW_CHAIN_LOG = """    mode_label = "🌅 утро" if mode == "morning" else "🏠 вечер"
    await log(f"{mode_label} | {name} | бюджет внимания: {budget:.1f} | max_quanta={max_quanta}")

    results = []
    quantum_n = 0
    # Счётчик встреч по парам — один раз за прогулку
    _met_pairs: set = set()

    while attention > 0.12 and quantum_n < max_quanta:  # лимит квантов"""

# ─── Фикс 2: ограничение встреч — один раз за прогулку ──────────────────────
# Вставляем проверку пары перед _try_meeting в walk_one_agent

OLD_TRY_MEETING = """    # Проверяем встречу
    meeting = await _try_meeting(
        folder, name, dna, chosen_location, here_now, workshop,
        agent_profession=agent.get("Profession", ""),
    )"""

NEW_TRY_MEETING = """    # Проверяем встречу (не более 1 раза с одним партнёром за прогулку)
    _met_pairs_walk = city_state.get("_met_pairs_walk", {})
    _my_pairs = _met_pairs_walk.get(folder, set())
    _others_in_loc = [
        c["folder"] for c in here_now.get(chosen_location, [])
        if c["folder"] != folder and c["folder"] not in _my_pairs
    ]
    _skip_meeting = len(_others_in_loc) == 0
    if _skip_meeting:
        meeting = None
    else:
        meeting = await _try_meeting(
            folder, name, dna, chosen_location, here_now, workshop,
            agent_profession=agent.get("Profession", ""),
        )
        if meeting and meeting.get("met"):
            _partner_folder = next(
                (c["folder"] for c in here_now.get(chosen_location, [])
                 if c.get("name") == meeting["met"]),
                None,
            )
            if _partner_folder:
                _my_pairs.add(_partner_folder)
                _met_pairs_walk[folder] = _my_pairs
                city_state["_met_pairs_walk"] = _met_pairs_walk"""

# ─── Фикс 3: run_city_walk_evening — добавляем max_quanta ───────────────────

OLD_EVENING_SIG = """async def run_city_walk_evening(
    workshops: list[str] | None = None,
    on_progress=None,
    max_agents: int = 0,
) -> list[dict]:"""

NEW_EVENING_SIG = """async def run_city_walk_evening(
    workshops: list[str] | None = None,
    on_progress=None,
    max_agents: int = 0,
    max_quanta: int = 3,
) -> list[dict]:"""

OLD_EVENING_CHAIN = """    results = []
    for agent in all_agents:
        chain = await walk_quantum_chain(
            agent, city_state, locations,
            mode="evening",
            on_progress=on_progress,
        )
        results.extend(chain)
        await asyncio.sleep(2)"""

NEW_EVENING_CHAIN = """    # Сбрасываем счётчик пар встреч на новую прогулку
    city_state["_met_pairs_walk"] = {}
    save_city_state(city_state)

    results = []
    for agent in all_agents:
        chain = await walk_quantum_chain(
            agent, city_state, locations,
            mode="evening",
            on_progress=on_progress,
            max_quanta=max_quanta,
        )
        results.extend(chain)
        await asyncio.sleep(0.5)"""


def main(dry_run=False):
    if not TARGET.exists():
        print(f"[ERROR] {TARGET} не найден")
        sys.exit(1)

    content = TARGET.read_text(encoding="utf-8")

    fixes = [
        ("chain signature",    OLD_CHAIN_SIG,     NEW_CHAIN_SIG),
        ("chain docstring",    OLD_CHAIN_DOC,     NEW_CHAIN_DOC),
        ("chain loop+pairs",   OLD_CHAIN_LOG,     NEW_CHAIN_LOG),
        ("try_meeting pairs",  OLD_TRY_MEETING,   NEW_TRY_MEETING),
        ("evening signature",  OLD_EVENING_SIG,   NEW_EVENING_SIG),
        ("evening chain call", OLD_EVENING_CHAIN, NEW_EVENING_CHAIN),
    ]

    new_content = content
    for label, old, new in fixes:
        if old in new_content:
            new_content = new_content.replace(old, new, 1)
            print(f"  [OK] {label}")
        else:
            print(f"  [SKIP] {label} — не найдено (уже применено?)")

    if dry_run:
        print("\n[DRY-RUN] Файл не изменён.")
        return

    if new_content == content:
        print("\n[INFO] Нечего менять.")
        return

    BACKUP_DIR.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    shutil.copy2(TARGET, BACKUP_DIR / f"city_walker.py.bak_quanta_{ts}")
    print(f"\n[BACKUP] {BACKUP_DIR}")

    TARGET.write_text(new_content, encoding="utf-8")
    print(f"[DONE] {TARGET}")
    print("\nЧто изменилось:")
    print("  · max_quanta=3 — Лока делает 3 остановки, не 17")
    print("  · Лока+Джем встречаются 1 раз за прогулку, не 8")
    print("  · sleep между агентами 0.5s вместо 2s")

if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    main(dry_run=dry)
