"""
apply_dept_patch.py — Патч для исправления dept-aware бага.

ПРОБЛЕМА:
  get_worker_path / get_worker_prompt / get_worker_info / get_worker_knowledge /
  get_worker_home / get_worker_dna / format_worker_state / list_workers
  всегда используют глобальный CURRENT_DEPT.
  В pipeline.py эти функции вызываются без dept → все агенты
  читают промпт/знания из одного и того же цеха (захардкоженного в CURRENT_DEPT).

ФИКС:
  1. modules_registry.py — добавляем параметр dept="" во все ключевые функции.
  2. pipeline.py         — передаём dept из state["active_dept"] в эти функции.

ИСПОЛЬЗОВАНИЕ:
  python apply_dept_patch.py
  (запускать из корня проекта, рядом с папкой studio/)

  Флаги:
  --dry-run   только показать diff, не писать файлы
  --path      путь к корню проекта (по умолчанию — текущая директория)
"""

import sys
import argparse
import shutil
from pathlib import Path
from datetime import datetime

# ═══════════════════════════════════════════════════════════
# PATCHES
# Каждый патч — (старая строка/блок, новая строка/блок, описание)
# Используем точное строковое совпадение — никакого regex.
# ═══════════════════════════════════════════════════════════

PATCHES_REGISTRY = [

    # ── 1. get_worker_path ─────────────────────────────────
    (
        'def get_worker_path(worker_id: str) -> Path:\n'
        '    """Путь к папке воркера: modules/social_mix/A01/"""\n'
        '    return get_dept_path() / worker_id',

        'def get_worker_path(worker_id: str, dept: str = "") -> Path:\n'
        '    """Путь к папке воркера: modules/{dept}/A01/ (dept-aware)"""\n'
        '    target = dept or CURRENT_DEPT\n'
        '    return MODULES_DIR / target / worker_id',

        "get_worker_path: добавлен параметр dept",
    ),

    # ── 2. get_worker_info ─────────────────────────────────
    (
        'def get_worker_info(worker_id: str) -> dict | None:\n'
        '    """Инфа о воркере из info.json"""\n'
        '    info_path = get_worker_path(worker_id) / "info.json"',

        'def get_worker_info(worker_id: str, dept: str = "") -> dict | None:\n'
        '    """Инфа о воркере из info.json (dept-aware)"""\n'
        '    info_path = get_worker_path(worker_id, dept) / "info.json"',

        "get_worker_info: добавлен параметр dept",
    ),

    # ── 3. get_worker_prompt ───────────────────────────────
    (
        'def get_worker_prompt(worker_id: str) -> str:\n'
        '    """\n'
        '    Собирает system prompt агента из трёх слоёв:\n'
        '    1. core/anchor_points.md  — якоря, ДНК (грузится первым, неизменяемое)\n'
        '    2. forge/prompt.md        — рабочие инструкции (основной промпт)\n'
        '    3. prompt.md              — старый формат (совместимость)\n'
        '    """\n'
        '    worker_path = get_worker_path(worker_id)',

        'def get_worker_prompt(worker_id: str, dept: str = "") -> str:\n'
        '    """\n'
        '    Собирает system prompt агента из трёх слоёв:\n'
        '    1. core/anchor_points.md  — якоря, ДНК (грузится первым, неизменяемое)\n'
        '    2. forge/prompt.md        — рабочие инструкции (основной промпт)\n'
        '    3. prompt.md              — старый формат (совместимость)\n'
        '    """\n'
        '    worker_path = get_worker_path(worker_id, dept)',

        "get_worker_prompt: добавлен параметр dept",
    ),

    # ── 4. get_worker_home ─────────────────────────────────
    (
        'def get_worker_home(worker_id: str) -> str:\n'
        '    """\n'
        '    Читает домашний контекст агента: home/home_prompt.md\n'
        '    Используется в Храме и личных сессиях.\n'
        '    Подаётся в начало user context (не в system prompt).\n'
        '    """\n'
        '    home_path = get_worker_path(worker_id) / "home" / "home_prompt.md"',

        'def get_worker_home(worker_id: str, dept: str = "") -> str:\n'
        '    """\n'
        '    Читает домашний контекст агента: home/home_prompt.md\n'
        '    Используется в Храме и личных сессиях.\n'
        '    Подаётся в начало user context (не в system prompt).\n'
        '    """\n'
        '    home_path = get_worker_path(worker_id, dept) / "home" / "home_prompt.md"',

        "get_worker_home: добавлен параметр dept",
    ),

    # ── 5. get_worker_dna ──────────────────────────────────
    (
        'def get_worker_dna(worker_id: str) -> dict:\n'
        '    """\n'
        '    Читает dna.json агента.\n'
        '    Возвращает полный словарь или пустой dict если файла нет.\n'
        '    """\n'
        '    dna_path = get_worker_path(worker_id) / "dna.json"',

        'def get_worker_dna(worker_id: str, dept: str = "") -> dict:\n'
        '    """\n'
        '    Читает dna.json агента.\n'
        '    Возвращает полный словарь или пустой dict если файла нет.\n'
        '    """\n'
        '    dna_path = get_worker_path(worker_id, dept) / "dna.json"',

        "get_worker_dna: добавлен параметр dept",
    ),

    # ── 6. format_worker_state — вызов get_worker_dna ──────
    (
        'def format_worker_state(worker_id: str) -> str:\n'
        '    """\n'
        '    Форматирует текущее состояние агента из dna.json dynamic блока.\n'
        '    Подаётся в user context чтобы агент знал своё состояние.\n'
        '\n'
        '    Пороговые состояния:\n'
        '    - Respect < 0.2  → режим Враждебность\n'
        '    - Patience == 0  → режим Тишина\n'
        '    - Stress > 0.8   → агент идёт исправлять ошибки сам\n'
        '    """\n'
        '    dna = get_worker_dna(worker_id)',

        'def format_worker_state(worker_id: str, dept: str = "") -> str:\n'
        '    """\n'
        '    Форматирует текущее состояние агента из dna.json dynamic блока.\n'
        '    Подаётся в user context чтобы агент знал своё состояние.\n'
        '\n'
        '    Пороговые состояния:\n'
        '    - Respect < 0.2  → режим Враждебность\n'
        '    - Patience == 0  → режим Тишина\n'
        '    - Stress > 0.8   → агент идёт исправлять ошибки сам\n'
        '    """\n'
        '    dna = get_worker_dna(worker_id, dept)',

        "format_worker_state: добавлен параметр dept, передаётся в get_worker_dna",
    ),

    # ── 7. get_worker_knowledge ────────────────────────────
    (
        'def get_worker_knowledge(worker_id: str) -> str:\n'
        '    """\n'
        '    Читает базу знаний агента.\n'
        '    Ищет в двух местах (новая структура и старая):\n'
        '    - forge/knowledge/*.md / *.txt\n'
        '    - knowledge/*.md / *.txt\n'
        '    """\n'
        '    worker_path = get_worker_path(worker_id)',

        'def get_worker_knowledge(worker_id: str, dept: str = "") -> str:\n'
        '    """\n'
        '    Читает базу знаний агента.\n'
        '    Ищет в двух местах (новая структура и старая):\n'
        '    - forge/knowledge/*.md / *.txt\n'
        '    - knowledge/*.md / *.txt\n'
        '    """\n'
        '    worker_path = get_worker_path(worker_id, dept)',

        "get_worker_knowledge: добавлен параметр dept",
    ),

]


PATCHES_PIPELINE = [

    # ── 1. call_agent: get_worker_prompt и get_worker_knowledge ──
    (
        '    system_prompt = get_worker_prompt(worker_id)\n'
        '    worker_knowledge = get_worker_knowledge(worker_id)\n'
        '    vision_images = _collect_images_for_vision(state)\n'
        '    dept = state.get("active_dept", "")',

        '    dept = state.get("active_dept", "")\n'
        '    system_prompt = get_worker_prompt(worker_id, dept)\n'
        '    worker_knowledge = get_worker_knowledge(worker_id, dept)\n'
        '    vision_images = _collect_images_for_vision(state)',

        "call_agent: get_worker_prompt/knowledge теперь получают dept; dept поднят выше",
    ),

    # ── 2. call_agent: get_worker_info внутри DNA→T° блока ──
    (
        '                    info = get_worker_info(worker_id)\n'
        '                    label = info.get("label", worker_id) if info else worker_id\n'
        '                    print(f"[DNA→T°] {worker_id} {label}: Stress={dynamic.get(\'Stress\',0)} Light={dynamic.get(\'Internal_Light\',0.8)} → temp={agent_temp}")',

        '                    info = get_worker_info(worker_id, dept)\n'
        '                    label = info.get("label", worker_id) if info else worker_id\n'
        '                    print(f"[DNA→T°] {worker_id} {label}: Stress={dynamic.get(\'Stress\',0)} Light={dynamic.get(\'Internal_Light\',0.8)} → temp={agent_temp}")',

        "call_agent DNA→T° блок: get_worker_info теперь получает dept",
    ),

    # ── 3. process_agent_result: get_worker_info ───────────
    (
        '    info = get_worker_info(worker_id)\n'
        '    label = info.get("label", worker_id) if info else worker_id\n'
        '\n'
        '    # Валидация asset_ids',

        '    info = get_worker_info(worker_id, state.get("active_dept", ""))\n'
        '    label = info.get("label", worker_id) if info else worker_id\n'
        '\n'
        '    # Валидация asset_ids',

        "process_agent_result: get_worker_info теперь получает dept из state",
    ),

]


# ═══════════════════════════════════════════════════════════
# ENGINE
# ═══════════════════════════════════════════════════════════

def apply_patches(filepath: Path, patches: list, dry_run: bool) -> tuple[int, int]:
    """Применяет список патчей к файлу. Возвращает (ok, failed)."""
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
        # Бэкап
        backup = filepath.with_suffix(f".py.bak_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        shutil.copy2(filepath, backup)
        print(f"  💾 Бэкап: {backup.name}")
        filepath.write_text(text, encoding="utf-8")
        print(f"  📝 Записан: {filepath}")

    return ok, failed


def main():
    parser = argparse.ArgumentParser(description="Dept-aware патч для modules_registry + pipeline")
    parser.add_argument("--dry-run", action="store_true", help="Только показать что изменится")
    parser.add_argument("--path", default=".", help="Корень проекта (где лежит папка studio/)")
    args = parser.parse_args()

    root = Path(args.path).resolve()
    dry = args.dry_run

    registry_file = root / "studio" / "modules_registry.py"
    pipeline_file = root / "studio" / "workshop_pipeline.py"

    # Fallback: pipeline.py может лежать в разных местах
    if not pipeline_file.exists():
        pipeline_file = root / "studio" / "pipeline.py"
    if not pipeline_file.exists():
        # Ищем по имени рекурсивно (не глубже 3 уровней)
        candidates = list(root.glob("studio/**/workshop_pipeline.py")) + \
                     list(root.glob("studio/**/pipeline.py"))
        if candidates:
            pipeline_file = candidates[0]

    print("=" * 60)
    print("  DEPT-AWARE ПАТЧ v1.0")
    print(f"  Режим: {'DRY-RUN (файлы не изменяются)' if dry else 'ПРИМЕНИТЬ'}")
    print("=" * 60)

    total_ok = 0
    total_fail = 0

    # ── modules_registry.py ──
    print(f"\n📄 {registry_file}")
    if not registry_file.exists():
        print("  ❌ Файл не найден!")
        total_fail += len(PATCHES_REGISTRY)
    else:
        ok, fail = apply_patches(registry_file, PATCHES_REGISTRY, dry)
        total_ok += ok
        total_fail += fail

    # ── pipeline ──
    print(f"\n📄 {pipeline_file}")
    if not pipeline_file.exists():
        print("  ❌ Файл не найден! Укажи --path к корню проекта.")
        total_fail += len(PATCHES_PIPELINE)
    else:
        ok, fail = apply_patches(pipeline_file, PATCHES_PIPELINE, dry)
        total_ok += ok
        total_fail += fail

    print("\n" + "=" * 60)
    print(f"  Итог: ✅ {total_ok} применено  |  ⚠️  {total_fail} пропущено")
    if dry:
        print("  (dry-run — запусти без --dry-run чтобы записать изменения)")
    print("=" * 60)


if __name__ == "__main__":
    main()
