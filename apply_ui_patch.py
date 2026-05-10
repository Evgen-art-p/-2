"""
apply_ui_patch.py — Патч для ui_workshop.py (ui.py)

ПРОБЛЕМА:
  Два старых пайплайна (run_pipeline, turbo_pipeline) и вспомогательные функции
  вызывают get_worker_info / get_worker_prompt / get_worker_knowledge /
  get_worker_home / format_worker_state без dept.
  state["active_dept"] выставляется правильно, но в функции не передаётся.

ФИКС:
  Все вызовы → dept=state.get("active_dept", "")
  Исключение: строки 474, 936, 940 — update_status / select_worker —
  там worker_id = state["active_worker"] = "SET" при старте, dept нужен.

ИСПОЛЬЗОВАНИЕ:
  python apply_ui_patch.py [--dry-run] [--path /путь/к/проекту]
"""

import sys
import argparse
import shutil
from pathlib import Path
from datetime import datetime


PATCHES_UI = [

    # ── 1. update_status: get_worker_info ────────────────────────────────
    (
        '    def update_status():\n'
        '        worker_id = state[\'active_worker\']\n'
        '        info = get_worker_info(worker_id)\n'
        '        label = info.get("label", worker_id) if info else worker_id',

        '    def update_status():\n'
        '        worker_id = state[\'active_worker\']\n'
        '        info = get_worker_info(worker_id, state.get("active_dept", ""))\n'
        '        label = info.get("label", worker_id) if info else worker_id',

        "update_status(): get_worker_info получает dept",
    ),

    # ── 2. select_worker viewer (с результатом) ───────────────────────────
    (
        '            info = get_worker_info(worker_id)\n'
        '            label = info.get("label", worker_id) if info else worker_id\n'
        '            update_viewer(f"# {label} ({worker_id})\\n\\n{text}")',

        '            info = get_worker_info(worker_id, state.get("active_dept", ""))\n'
        '            label = info.get("label", worker_id) if info else worker_id\n'
        '            update_viewer(f"# {label} ({worker_id})\\n\\n{text}")',

        "select_worker viewer (с результатом): get_worker_info получает dept",
    ),

    # ── 2b. select_worker viewer (без результата) ─────────────────────────
    (
        '            info = get_worker_info(worker_id)\n'
        '            label = info.get("label", worker_id) if info else worker_id\n'
        '            update_viewer(f"# {label} ({worker_id})\\n\\n*Отчёт пока не создан. Запустите пайплайн или напишите агенту напрямую.*")',

        '            info = get_worker_info(worker_id, state.get("active_dept", ""))\n'
        '            label = info.get("label", worker_id) if info else worker_id\n'
        '            update_viewer(f"# {label} ({worker_id})\\n\\n*Отчёт пока не создан. Запустите пайплайн или напишите агенту напрямую.*")',

        "select_worker viewer (без результата): get_worker_info получает dept",
    ),

    # ── 3. send_message: get_worker_prompt / get_worker_knowledge ─────────
    (
        '                system = get_worker_prompt(worker_id)\n'
        '                knowledge = get_worker_knowledge(worker_id)',

        '                system = get_worker_prompt(worker_id, state.get("active_dept", ""))\n'
        '                knowledge = get_worker_knowledge(worker_id, state.get("active_dept", ""))',

        "send_message(): get_worker_prompt/knowledge получают dept",
    ),

    # ── 4. continue_pipeline rebuilt_output (строка ~1159) ────────────────
    (
        '            info = get_worker_info(wid)\n'
        '            label = info.get("label", wid) if info else wid\n'
        '            my_output = meta.get("my_output", {})\n'
        '            chain_json = ""\n'
        '            if my_output:\n'
        '                try:\n'
        '                    chain_json = f"\\n```json\\n{json.dumps(my_output, ensure_ascii=False, indent=2)}\\n```"\n'
        '                except Exception:\n'
        '                    pass\n'
        '            chunk = meta.get("next_input") or (text[:800] + chain_json)\n'
        '            rebuilt_output += f"\\n\\n--- {label} ({wid}) ---\\n{chunk}"\n'
        '\n'
        '        state["paused_output"] = rebuilt_output\n'
        '        print(f"[CONTINUE] Пересобран previous_output: {len(rebuilt_output)} символов")\n'
        '        # ───────────────────────────────────────────────────────────────\n'
        '\n'
        '        ui.notify(f"▶ Продолжаю с {resume_from}...", type="positive")',

        '            info = get_worker_info(wid, state.get("active_dept", ""))\n'
        '            label = info.get("label", wid) if info else wid\n'
        '            my_output = meta.get("my_output", {})\n'
        '            chain_json = ""\n'
        '            if my_output:\n'
        '                try:\n'
        '                    chain_json = f"\\n```json\\n{json.dumps(my_output, ensure_ascii=False, indent=2)}\\n```"\n'
        '                except Exception:\n'
        '                    pass\n'
        '            chunk = meta.get("next_input") or (text[:800] + chain_json)\n'
        '            rebuilt_output += f"\\n\\n--- {label} ({wid}) ---\\n{chunk}"\n'
        '\n'
        '        state["paused_output"] = rebuilt_output\n'
        '        print(f"[CONTINUE] Пересобран previous_output: {len(rebuilt_output)} символов")\n'
        '        # ───────────────────────────────────────────────────────────────\n'
        '\n'
        '        ui.notify(f"▶ Продолжаю с {resume_from}...", type="positive")',

        "continue_pipeline rebuilt_output: get_worker_info получает dept",
    ),

    # ── 5. continue_cartridge rebuilt_output (строка ~1285) ───────────────
    (
        '            info = get_worker_info(wid)\n'
        '            label = info.get("label", wid) if info else wid\n'
        '            my_output = meta.get("my_output", {})\n'
        '            chain_json = ""\n'
        '            if my_output:\n'
        '                try:\n'
        '                    chain_json = f"\\n```json\\n{json.dumps(my_output, ensure_ascii=False, indent=2)}\\n```"\n'
        '                except Exception:\n'
        '                    pass\n'
        '            chunk = meta.get("next_input") or (text[:800] + chain_json)\n'
        '            rebuilt_output += f"\\n\\n--- {label} ({wid}) ---\\n{chunk}"\n'
        '\n'
        '        state["paused_output"] = rebuilt_output\n'
        '        print(f"[CONTINUE] Пересобран previous_output: {len(rebuilt_output)} символов")\n'
        '\n'
        '        ui.notify(f"▶ Продолжаю с {resume_from}...", type="positive")\n'
        '        await run_cartridge_pipeline(',

        '            info = get_worker_info(wid, state.get("active_dept", ""))\n'
        '            label = info.get("label", wid) if info else wid\n'
        '            my_output = meta.get("my_output", {})\n'
        '            chain_json = ""\n'
        '            if my_output:\n'
        '                try:\n'
        '                    chain_json = f"\\n```json\\n{json.dumps(my_output, ensure_ascii=False, indent=2)}\\n```"\n'
        '                except Exception:\n'
        '                    pass\n'
        '            chunk = meta.get("next_input") or (text[:800] + chain_json)\n'
        '            rebuilt_output += f"\\n\\n--- {label} ({wid}) ---\\n{chunk}"\n'
        '\n'
        '        state["paused_output"] = rebuilt_output\n'
        '        print(f"[CONTINUE] Пересобран previous_output: {len(rebuilt_output)} символов")\n'
        '\n'
        '        ui.notify(f"▶ Продолжаю с {resume_from}...", type="positive")\n'
        '        await run_cartridge_pipeline(',

        "continue_cartridge rebuilt_output: get_worker_info получает dept",
    ),

    # ── 6. turbo_pipeline: get_worker_info + prompt + knowledge + home + dna
    (
        '                info = get_worker_info(worker_id)\n'
        '                label = info.get("label", worker_id) if info else worker_id\n'
        '                ui.notify(f"🤖 {label}{tag}...", type=\'info\')\n'
        '\n'
        '            system_prompt = get_worker_prompt(worker_id)\n'
        '            worker_knowledge = get_worker_knowledge(worker_id)\n',

        '                info = get_worker_info(worker_id, state.get("active_dept", ""))\n'
        '                label = info.get("label", worker_id) if info else worker_id\n'
        '                ui.notify(f"🤖 {label}{tag}...", type=\'info\')\n'
        '\n'
        '            system_prompt = get_worker_prompt(worker_id, state.get("active_dept", ""))\n'
        '            worker_knowledge = get_worker_knowledge(worker_id, state.get("active_dept", ""))\n',

        "turbo_pipeline: get_worker_info/prompt/knowledge получают dept",
    ),

    # ── 7. turbo_pipeline: get_worker_home + format_worker_state ──────────
    (
        '            home_ctx = get_worker_home(worker_id)\n'
        '            if home_ctx:\n'
        '                context += f"=== ЛИЧНЫЙ КОНТЕКСТ ===\\n{home_ctx}\\n\\n"\n'
        '\n'
        '            # Текущее состояние агента из dna.json (Stress, Respect и др.)\n'
        '            dna_state = format_worker_state(worker_id)\n'
        '            if dna_state:\n'
        '                context += dna_state + "\\n\\n"\n'
        '\n'
        '            # Грондхейм: инжект души перед работой\n'
        '            if _GRONDHEIM_ENABLED:\n'
        '                _dept = state.get("active_dept", "")',

        '            home_ctx = get_worker_home(worker_id, state.get("active_dept", ""))\n'
        '            if home_ctx:\n'
        '                context += f"=== ЛИЧНЫЙ КОНТЕКСТ ===\\n{home_ctx}\\n\\n"\n'
        '\n'
        '            # Текущее состояние агента из dna.json (Stress, Respect и др.)\n'
        '            dna_state = format_worker_state(worker_id, state.get("active_dept", ""))\n'
        '            if dna_state:\n'
        '                context += dna_state + "\\n\\n"\n'
        '\n'
        '            # Грондхейм: инжект души перед работой\n'
        '            if _GRONDHEIM_ENABLED:\n'
        '                _dept = state.get("active_dept", "")',

        "turbo_pipeline: get_worker_home/format_worker_state получают dept",
    ),

    # ── 8. run_pipeline: get_worker_info + prompt + knowledge ─────────────
    (
        '                info = get_worker_info(worker_id)\n'
        '                label = info.get("label", worker_id) if info else worker_id\n'
        '                \n'
        '                ui.notify(f"🤖 {label} работает...", type=\'info\')\n'
        '                \n'
        '                system_prompt = get_worker_prompt(worker_id)\n'
        '                worker_knowledge = get_worker_knowledge(worker_id)',

        '                info = get_worker_info(worker_id, state.get("active_dept", ""))\n'
        '                label = info.get("label", worker_id) if info else worker_id\n'
        '                \n'
        '                ui.notify(f"🤖 {label} работает...", type=\'info\')\n'
        '                \n'
        '                system_prompt = get_worker_prompt(worker_id, state.get("active_dept", ""))\n'
        '                worker_knowledge = get_worker_knowledge(worker_id, state.get("active_dept", ""))',

        "run_pipeline: get_worker_info/prompt/knowledge получают dept",
    ),

    # ── 9. run_pipeline: get_worker_home + format_worker_state ────────────
    (
        '                home_ctx = get_worker_home(worker_id)\n'
        '                if home_ctx:\n'
        '                    context += f"=== ЛИЧНЫЙ КОНТЕКСТ ===\\n{home_ctx}\\n\\n"\n'
        '\n'
        '                # Текущее состояние агента из dna.json (Stress, Respect и др.)\n'
        '                dna_state = format_worker_state(worker_id)',

        '                home_ctx = get_worker_home(worker_id, state.get("active_dept", ""))\n'
        '                if home_ctx:\n'
        '                    context += f"=== ЛИЧНЫЙ КОНТЕКСТ ===\\n{home_ctx}\\n\\n"\n'
        '\n'
        '                # Текущее состояние агента из dna.json (Stress, Respect и др.)\n'
        '                dna_state = format_worker_state(worker_id, state.get("active_dept", ""))',

        "run_pipeline: get_worker_home/format_worker_state получают dept",
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
    parser = argparse.ArgumentParser(description="Dept-aware патч для ui_workshop.py")
    parser.add_argument("--dry-run", action="store_true", help="Только показать что изменится")
    parser.add_argument("--path", default=".", help="Корень проекта")
    args = parser.parse_args()

    root = Path(args.path).resolve()
    dry = args.dry_run

    # Ищем ui.py в workshop
    ui_file = root / "studio" / "workshop" / "ui.py"
    if not ui_file.exists():
        # Fallback: ищем по всем возможным путям
        candidates = (
            list(root.glob("studio/**/ui_workshop.py")) +
            list(root.glob("studio/**/ui.py"))
        )
        # Берём первый который не в reception/turbo/__pycache__
        for c in candidates:
            if "reception" not in c.parts and "turbo" not in c.parts and "__pycache__" not in c.parts:
                ui_file = c
                break

    print("=" * 60)
    print("  UI WORKSHOP DEPT-AWARE ПАТЧ v1.0")
    print(f"  Режим: {'DRY-RUN (файлы не изменяются)' if dry else 'ПРИМЕНИТЬ'}")
    print("=" * 60)

    print(f"\n📄 {ui_file}")
    if not ui_file.exists():
        print("  ❌ studio/workshop/ui.py не найден! Укажи --path к корню проекта.")
        sys.exit(1)

    ok, failed = apply_patches(ui_file, PATCHES_UI, dry)

    print("\n" + "=" * 60)
    print(f"  Итог: ✅ {ok} применено  |  ⚠️  {failed} пропущено")
    if dry:
        print("  (dry-run — запусти без --dry-run чтобы записать изменения)")
    print("=" * 60)


if __name__ == "__main__":
    main()
