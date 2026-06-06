#!/usr/bin/env python3
"""
patch_chain_data_propagation.py — chain_data передаётся по цепочке

ПРОБЛЕМА:
  A01 пишет adam_bible в chain_data.
  A02 пишет zack_season_structure в chain_data.
  A03 пишет leo_season_breakdown в chain_data.

  Но previous_output берёт только my_output каждого агента.
  A04 (Катя Кат) получает my_output без chain_data →
  не видит adam_bible, zack_season_structure, leo_season_breakdown →
  пишет "пустая болванка" и REJECTED.

РЕШЕНИЕ:
  В process_agent_result() — если в meta есть chain_data,
  накапливаем его в state["_chain_accumulator"].
  В build_agent_context() — добавляем накопленный chain_data в контекст
  для video_long агентов (A02, A03, A04...).

  Это не ломает other цеха — chain_accumulator пустой если chain_data нет.
"""

import sys
import shutil
import py_compile
import tempfile
from pathlib import Path
from datetime import datetime

DRY_RUN = "--dry-run" in sys.argv
BACKUP_DIR = Path("_patch_backups") / f"chain_prop_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

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
# ПАТЧ 1: pipeline.py process_agent_result —
#   накапливаем chain_data в state["_chain_accumulator"]
# ══════════════════════════════════════════════════════════════════

CHAIN_ACCUMULATE_OLD = (
    "    # Сохраняем в state\n"
    "    state[\"results\"][worker_id] = {\n"
    "        \"text\": human_text,\n"
    "        \"meta\": meta,\n"
    "        \"raw\": raw_result\n"
    "    }"
)

CHAIN_ACCUMULATE_NEW = (
    "    # Сохраняем в state\n"
    "    state[\"results\"][worker_id] = {\n"
    "        \"text\": human_text,\n"
    "        \"meta\": meta,\n"
    "        \"raw\": raw_result\n"
    "    }\n"
    "\n"
    "    # ПАТЧ chain_prop: накапливаем chain_data по цепочке\n"
    "    # A01 пишет adam_bible, A02 — zack_season_structure и т.д.\n"
    "    # Каждый следующий агент должен видеть всё накопленное\n"
    "    _chain_data = meta.get(\"chain_data\", {})\n"
    "    if _chain_data and isinstance(_chain_data, dict):\n"
    "        _acc = state.setdefault(\"_chain_accumulator\", {})\n"
    "        for _ck, _cv in _chain_data.items():\n"
    "            # Пропускаем inherit-заглушки и master_brief/history_dna\n"
    "            if _cv in (\"{{inherit}}\", None, \"\"):\n"
    "                continue\n"
    "            if _ck in (\"master_brief\", \"history_dna\", \"mode\"):\n"
    "                continue\n"
    "            _acc[_ck] = _cv\n"
    "        if _acc:\n"
    "            print(f\"[CHAIN] {worker_id}: chain_accumulator = {list(_acc.keys())}\")"
)


# ══════════════════════════════════════════════════════════════════
# ПАТЧ 2: pipeline.py build_agent_context —
#   добавляем накопленный chain_data в контекст агента
# ══════════════════════════════════════════════════════════════════

CHAIN_INJECT_OLD = (
    "    # Предыдущие результаты\n"
    "    if previous_output:\n"
    "        context += f\"=== РЕЗУЛЬТАТЫ ПРЕДЫДУЩИХ ЭТАПОВ ===\\n{previous_output}\\n\""
)

CHAIN_INJECT_NEW = (
    "    # ПАТЧ chain_prop: накопленный chain_data от предыдущих агентов\n"
    "    # Это критично для video_long: A04 должна видеть adam_bible,\n"
    "    # zack_season_structure, leo_season_breakdown из chain_data A01-A03\n"
    "    _chain_acc = state.get(\"_chain_accumulator\", {})\n"
    "    if _chain_acc:\n"
    "        try:\n"
    "            import json as _cjson\n"
    "            _chain_str = _cjson.dumps(_chain_acc, ensure_ascii=False, indent=2)\n"
    "            context += (\n"
    "                f\"=== CHAIN DATA (от предыдущих агентов) ===\\n\"\n"
    "                f\"```json\\n{_chain_str}\\n```\\n\\n\"\n"
    "            )\n"
    "            print(f\"[CHAIN] {worker_id}: получил chain_data {list(_chain_acc.keys())}\")\n"
    "        except Exception as _ce:\n"
    "            print(f\"[CHAIN] {worker_id}: ошибка инжекта chain_data: {_ce}\")\n"
    "\n"
    "    # Предыдущие результаты\n"
    "    if previous_output:\n"
    "        context += f\"=== РЕЗУЛЬТАТЫ ПРЕДЫДУЩИХ ЭТАПОВ ===\\n{previous_output}\\n\""
)


def main():
    print("=" * 60)
    print("ПАТЧ: chain_data propagation по цепочке агентов")
    print("=" * 60)
    if DRY_RUN:
        print("DRY-RUN\n")

    pipeline = Path("studio/workshop/pipeline.py")

    print("\n[1/2] pipeline.py — накапливаем chain_data в _chain_accumulator")
    ok1 = apply(pipeline, CHAIN_ACCUMULATE_OLD, CHAIN_ACCUMULATE_NEW,
                "state['_chain_accumulator'] накапливает chain_data агентов")

    print("\n[2/2] pipeline.py — инжектируем chain_data в контекст следующего агента")
    ok2 = apply(pipeline, CHAIN_INJECT_OLD, CHAIN_INJECT_NEW,
                "chain_accumulator → в контекст агента перед previous_output")

    print("\n" + "=" * 60)
    if DRY_RUN:
        print("DRY-RUN завершён.")
        return

    if ok1 or ok2:
        print(f"✅ Применено {sum([ok1,ok2])}/2 патчей!")
        print(f"   Бекапы: {BACKUP_DIR}")
        print()
        print("Что изменилось:")
        print("  • A01 отдаёт adam_bible → накапливается в _chain_accumulator")
        print("  • A02 отдаёт zack_season_structure → добавляется в аккумулятор")
        print("  • A03 отдаёт leo_season_breakdown → добавляется в аккумулятор")
        print("  • A04 получает весь накопленный chain_data в контексте")
        print("  • Катя Кат видит всю цепочку и делает реальный аудит")
        print()
        print("В консоли появится:")
        print("  [CHAIN] A01: chain_accumulator = ['adam_bible']")
        print("  [CHAIN] A02: chain_accumulator = ['adam_bible', 'zack_season_structure']")
        print("  [CHAIN] A03: получил chain_data ['adam_bible', 'zack_season_structure']")
        print()
        print("Перезапусти: python main.py")
    else:
        print("⚠ Ничего не применено")


if __name__ == "__main__":
    main()
