"""
apply_cabinet_patch.py — Патч для studio/cabinet/ui_cabinet.py

ПРОБЛЕМА:
  talk_to_agent(agent_id) ищет агента по ID без учёта цеха.
  DEPARTMENTS в agents.py начинается с "turbo" — поэтому A01 из любого
  цеха резолвится как turbo/A01, и диалог открывается с промптом turbo.

  Цепочка:
    render_agent_detail(agent, on_talk=talk_to_agent)
      → on_talk(_id)                    # dept не передаётся
    talk_to_agent(agent_id):
      for dept_id, agents in ...:
        found = next(a for a in agents if a["id"] == agent_id)
        if found: break                 # берёт первый попавшийся цех!

ФИКС:
  1. talk_to_agent(agent_id) → talk_to_agent(agent_id, agent_dept="")
     Если agent_dept передан — ищем только в этом цехе.
  2. render_agent_detail вызывает on_talk(_id) →
     нужно передавать on_talk(_id, _dept).
     Но render_agent_detail живёт в agents.py и принимает on_talk как callback.
     Проще всего: в ui_cabinet.py оборачиваем on_talk в лямбду с dept.
  3. В _render_agent_tab() меняем вызов:
     render_agent_detail(agent, on_talk=talk_to_agent)
     →
     render_agent_detail(agent, on_talk=lambda aid, _dept=agent.get("dept",""): talk_to_agent(aid, _dept))

ИСПОЛЬЗОВАНИЕ:
  python apply_cabinet_patch.py [--dry-run] [--path /путь/к/проекту]
"""

import sys
import argparse
import shutil
from pathlib import Path
from datetime import datetime


PATCHES_CABINET = [

    # ── 1. talk_to_agent: добавить agent_dept параметр ───────────────────
    (
        '    def talk_to_agent(agent_id):\n'
        '        """Начать разговор с агентом — полноценный режим диалога."""\n'
        '        if state["talking_agent"] and len(state["chat_history"]) >= 2:\n'
        '            ui.timer(0, lambda: _finalize_current_dialog(), once=True)\n'
        '\n'
        '        agent = None\n'
        '        for dept_id, agents in state["all_agents"].items():\n'
        '            found = next((a for a in agents if a["id"] == agent_id), None)\n'
        '            if found:\n'
        '                agent = found\n'
        '                break',

        '    def talk_to_agent(agent_id, agent_dept=""):\n'
        '        """Начать разговор с агентом — полноценный режим диалога."""\n'
        '        if state["talking_agent"] and len(state["chat_history"]) >= 2:\n'
        '            ui.timer(0, lambda: _finalize_current_dialog(), once=True)\n'
        '\n'
        '        agent = None\n'
        '        # Сначала ищем в конкретном цехе если dept передан\n'
        '        if agent_dept:\n'
        '            for a in state["all_agents"].get(agent_dept, []):\n'
        '                if a["id"] == agent_id:\n'
        '                    agent = a\n'
        '                    break\n'
        '        # Фоллбэк: поиск по всем цехам\n'
        '        if not agent:\n'
        '            for dept_id, agents in state["all_agents"].items():\n'
        '                found = next((a for a in agents if a["id"] == agent_id), None)\n'
        '                if found:\n'
        '                    agent = found\n'
        '                    break',

        "talk_to_agent: добавлен agent_dept — теперь ищет в правильном цехе",
    ),

    # ── 2. _render_agent_tab: передаём dept в on_talk ─────────────────────
    (
        '    def _render_agent_tab():\n'
        '        agent = state["selected_agent"]\n'
        '        if not agent:\n'
        '            ui.html(\'<div style="text-align:center;padding:32px;font-family:JetBrains Mono;font-size:0.56rem;color:rgba(140,150,180,0.3)">выбери агента слева</div>\')\n'
        '            return\n'
        '        render_agent_detail(agent, on_talk=talk_to_agent)',

        '    def _render_agent_tab():\n'
        '        agent = state["selected_agent"]\n'
        '        if not agent:\n'
        '            ui.html(\'<div style="text-align:center;padding:32px;font-family:JetBrains Mono;font-size:0.56rem;color:rgba(140,150,180,0.3)">выбери агента слева</div>\')\n'
        '            return\n'
        '        _dept = agent.get("dept", "")\n'
        '        render_agent_detail(agent, on_talk=lambda aid, _d=_dept: talk_to_agent(aid, _d))',

        "_render_agent_tab: on_talk теперь передаёт dept в talk_to_agent",
    ),

]


def apply_patches(filepath: Path, patches: list, dry_run: bool) -> tuple[int, int]:
    text = filepath.read_text(encoding="utf-8")
    ok = 0
    failed = 0

    for old, new, desc in patches:
        if old in text:
            text = text.replace(old, new, 1)
            print(f"  ✅ {desc}")
            ok += 1
        else:
            print(f"  ⚠️  НЕ НАЙДЕНО: {desc}")
            failed += 1

    if not dry_run and ok > 0:
        backup = filepath.with_suffix(f".py.bak_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        shutil.copy2(filepath, backup)
        print(f"  💾 Бэкап: {backup.name}")
        filepath.write_text(text, encoding="utf-8")
        print(f"  📝 Записан: {filepath}")

    return ok, failed


def main():
    parser = argparse.ArgumentParser(description="Dept-aware патч для cabinet/ui_cabinet.py")
    parser.add_argument("--dry-run", action="store_true", help="Только показать что изменится")
    parser.add_argument("--path", default=".", help="Корень проекта")
    args = parser.parse_args()

    root = Path(args.path).resolve()
    dry = args.dry_run

    cabinet_file = root / "studio" / "cabinet" / "ui_cabinet.py"

    print("=" * 60)
    print("  CABINET DEPT-AWARE ПАТЧ v1.0")
    print(f"  Режим: {'DRY-RUN (файлы не изменяются)' if dry else 'ПРИМЕНИТЬ'}")
    print("=" * 60)

    print(f"\n📄 {cabinet_file}")
    if not cabinet_file.exists():
        print("  ❌ studio/cabinet/ui_cabinet.py не найден!")
        sys.exit(1)

    ok, failed = apply_patches(cabinet_file, PATCHES_CABINET, dry)

    print("\n" + "=" * 60)
    print(f"  Итог: ✅ {ok} применено  |  ⚠️  {failed} пропущено")
    if dry:
        print("  (dry-run — запусти без --dry-run чтобы записать изменения)")
    print("=" * 60)


if __name__ == "__main__":
    main()
