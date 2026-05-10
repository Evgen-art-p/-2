"""
apply_cartridge_patch.py — Патч для cartridge.py

ПРОБЛЕМА:
  CartridgeRunner вызывает get_worker_info(worker_id) без dept во всех 4 местах:
    - run():       строка ~316 — последовательный агент
    - run_turbo(): строки ~476, ~490 — параллельная группа (начало и конец)
    - run_turbo(): строка ~515 — обычный последовательный агент в turbo

  get_worker_info без dept → идёт в CURRENT_DEPT (захардкожен) → читает
  label/info не того цеха. Промпт и знания при этом берёт pipeline.py
  (уже пропатчен), но label агента в логах/UI — всё ещё из дефолтного цеха.

  Плюс: active_dept нужно выставлять в self.state при старте run/run_turbo,
  чтобы pipeline.py (call_agent, process_agent_result) видел правильный цех.

ФИКС:
  1. В начале run() и run_turbo() добавить:
         self.state["active_dept"] = self.manifest.id
  2. Все 4 вызова get_worker_info(worker_id/wid) → get_worker_info(worker_id/wid, dept)
     где dept = self.manifest.id

ИСПОЛЬЗОВАНИЕ:
  python apply_cartridge_patch.py [--dry-run] [--path /путь/к/проекту]
"""

import sys
import argparse
import shutil
from pathlib import Path
from datetime import datetime


PATCHES_CARTRIDGE = [

    # ── 1. run(): выставляем active_dept + берём dept для info ──────────
    # Добавляем self.state["active_dept"] = ... сразу после _slot_id
    # и меняем get_worker_info на dept-aware
    (
        '        self.state["_slot_id"] = self.slot_id  # ← slot_id для feedback/reflection\n'
        '        client_slug = self.state.get("current_client", "_sandbox")',

        '        self.state["_slot_id"] = self.slot_id  # ← slot_id для feedback/reflection\n'
        '        self.state["active_dept"] = self.manifest.id  # ← dept-aware патч\n'
        '        client_slug = self.state.get("current_client", "_sandbox")',

        "run(): выставляем active_dept = manifest.id перед стартом пайплайна",
    ),

    # ── 2. run(): get_worker_info в основном цикле ───────────────────────
    (
        '            info = get_worker_info(worker_id)\n'
        '            label = info.get("label", worker_id) if info else worker_id\n'
        '            phase = self.manifest.get_agent_phase(worker_id) or ""',

        '            info = get_worker_info(worker_id, self.manifest.id)\n'
        '            label = info.get("label", worker_id) if info else worker_id\n'
        '            phase = self.manifest.get_agent_phase(worker_id) or ""',

        "run() основной цикл: get_worker_info получает dept",
    ),

    # ── 3. run_turbo(): выставляем active_dept ───────────────────────────
    (
        '        run_type = "turbo"\n'
        '        client_slug = self.state.get("current_client", "_sandbox")',

        '        run_type = "turbo"\n'
        '        self.state["active_dept"] = self.manifest.id  # ← dept-aware патч\n'
        '        client_slug = self.state.get("current_client", "_sandbox")',

        "run_turbo(): выставляем active_dept = manifest.id перед стартом",
    ),

    # ── 4. run_turbo(): get_worker_info в начале параллельной группы ─────
    (
        '                async def _run_one(wid: str):\n'
        '                    _info = get_worker_info(wid)\n'
        '                    _label = _info.get("label", wid) if _info else wid\n'
        '                    await self.callbacks.on_agent_start(self.slot_id, wid, _label, "TURBO")',

        '                async def _run_one(wid: str):\n'
        '                    _info = get_worker_info(wid, self.manifest.id)\n'
        '                    _label = _info.get("label", wid) if _info else wid\n'
        '                    await self.callbacks.on_agent_start(self.slot_id, wid, _label, "TURBO")',

        "run_turbo() параллельный _run_one: get_worker_info получает dept",
    ),

    # ── 5. run_turbo(): get_worker_info в обработке результатов группы ───
    (
        '                for j, wid in enumerate(parallel_group):\n'
        '                    _info = get_worker_info(wid)\n'
        '                    _label = _info.get("label", wid) if _info else wid',

        '                for j, wid in enumerate(parallel_group):\n'
        '                    _info = get_worker_info(wid, self.manifest.id)\n'
        '                    _label = _info.get("label", wid) if _info else wid',

        "run_turbo() результаты параллельной группы: get_worker_info получает dept",
    ),

    # ── 6. run_turbo(): get_worker_info в последовательном агенте ────────
    (
        '            # Обычный последовательный агент\n'
        '            info = get_worker_info(worker_id)\n'
        '            label = info.get("label", worker_id) if info else worker_id',

        '            # Обычный последовательный агент\n'
        '            info = get_worker_info(worker_id, self.manifest.id)\n'
        '            label = info.get("label", worker_id) if info else worker_id',

        "run_turbo() последовательный агент: get_worker_info получает dept",
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
            print(f"  ⚠️  НЕ НАЙДЕНО (уже применён или изменился файл): {desc}")
            failed += 1

    if not dry_run and ok > 0:
        backup = filepath.with_suffix(f".py.bak_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        shutil.copy2(filepath, backup)
        print(f"  💾 Бэкап: {backup.name}")
        filepath.write_text(text, encoding="utf-8")
        print(f"  📝 Записан: {filepath}")

    return ok, failed


def main():
    parser = argparse.ArgumentParser(description="Dept-aware патч для cartridge.py")
    parser.add_argument("--dry-run", action="store_true", help="Только показать что изменится")
    parser.add_argument("--path", default=".", help="Корень проекта (где лежит папка studio/)")
    args = parser.parse_args()

    root = Path(args.path).resolve()
    dry = args.dry_run

    # Ищем cartridge.py
    cartridge_file = root / "studio" / "cartridge.py"
    if not cartridge_file.exists():
        candidates = list(root.glob("studio/**/cartridge.py"))
        if candidates:
            cartridge_file = candidates[0]

    print("=" * 60)
    print("  CARTRIDGE DEPT-AWARE ПАТЧ v1.0")
    print(f"  Режим: {'DRY-RUN (файлы не изменяются)' if dry else 'ПРИМЕНИТЬ'}")
    print("=" * 60)

    print(f"\n📄 {cartridge_file}")
    if not cartridge_file.exists():
        print("  ❌ cartridge.py не найден! Укажи --path к корню проекта.")
        sys.exit(1)

    ok, failed = apply_patches(cartridge_file, PATCHES_CARTRIDGE, dry)

    print("\n" + "=" * 60)
    print(f"  Итог: ✅ {ok} применено  |  ⚠️  {failed} пропущено")
    if dry:
        print("  (dry-run — запусти без --dry-run чтобы записать изменения)")
    print("=" * 60)


if __name__ == "__main__":
    main()
