"""
patch_finch_hooks.py
====================
Подключает Финча к системе студии.

Два патча:
  1. studio/vision_client.py
     После архивации реджекта → plant_from_rejection()
     Финч получает брак автоматически.

  2. studio/morning_checkout.py
     После пробуждения студии → finch_morning()
     Финч обходит сад каждое утро.

Запуск из корня проекта:
    python patch_finch_hooks.py

Создаёт бэкапы:
    studio/vision_client.py.bak_finch
    studio/morning_checkout.py.bak_finch
"""

import shutil
from pathlib import Path

# ── Цвета для вывода ─────────────────────────────────────────
OK    = "✅"
FAIL  = "❌"
INFO  = "ℹ️ "
SKIP  = "⏭️ "


def patch_file(path: Path, search: str, insert_after: str, label: str) -> bool:
    """
    Находит строку search в файле и вставляет insert_after после неё.
    Создаёт бэкап .bak_finch перед изменением.
    Возвращает True если патч применён.
    """
    if not path.exists():
        print(f"{FAIL} {label}: файл не найден — {path}")
        return False

    content = path.read_text(encoding="utf-8")

    # Уже пропатчено?
    if "garden_tools" in content:
        print(f"{SKIP} {label}: уже содержит garden_tools — пропускаю")
        return True

    if search not in content:
        print(f"{FAIL} {label}: строка для вставки не найдена:")
        print(f"     искал: {repr(search[:80])}")
        return False

    # Бэкап
    bak = path.with_suffix(path.suffix + ".bak_finch")
    shutil.copy2(path, bak)
    print(f"{INFO} {label}: бэкап → {bak.name}")

    # Вставляем после искомой строки
    new_content = content.replace(search, search + insert_after, 1)
    path.write_text(new_content, encoding="utf-8")
    print(f"{OK} {label}: патч применён")
    return True


# ════════════════════════════════════════════════════════════════
# ПАТЧ 1 — vision_client.py
# ════════════════════════════════════════════════════════════════

VISION_CLIENT = Path("studio/vision_client.py")

# Строка после которой вставляем
VISION_SEARCH = '    print(f"[ОТК архив] 📁 Брак → {dest_file.relative_to(Path(\'.\'))}")'

# Что вставляем
VISION_INSERT = """
    # 🌱 Финч получает реджект — сажает в сад
    try:
        from studio.garden_tools import plant_from_rejection
        plant_from_rejection(
            archived_file=str(dest_file),
            agent_id=agent_id,
            reason=result.get("reason", ""),
            original_prompt=original_prompt,
            artifacts=result.get("artifacts", []),
            fix_hint=result.get("fix_hint", ""),
            project_id=project_id,
        )
    except Exception:
        pass  # Финч не должен ломать ОТК
"""

# ════════════════════════════════════════════════════════════════
# ПАТЧ 2 — morning_checkout.py
# ════════════════════════════════════════════════════════════════

MORNING_CHECKOUT = Path("studio/morning_checkout.py")

# Строка после которой вставляем
MORNING_SEARCH = '    await log(f"🌅 Утренний Чекаут · {datetime.now().strftime(\'%Y-%m-%d %H:%M\')}")'

# Что вставляем
MORNING_INSERT = """
    # 🌱 Финч обходит сад каждое утро
    try:
        from studio.garden_tools import finch_morning
        finch_morning(on_progress=on_progress)
    except Exception as e:
        print(f"[CHECKOUT] ⚠ Финч не смог обойти сад: {e}")
"""

# ════════════════════════════════════════════════════════════════
# ЗАПУСК
# ════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 55)
    print("🌱 ПАТЧ ФИНЧА — подключение к системе студии")
    print("=" * 55)

    results = []

    results.append(patch_file(
        path=VISION_CLIENT,
        search=VISION_SEARCH,
        insert_after=VISION_INSERT,
        label="vision_client.py",
    ))

    results.append(patch_file(
        path=MORNING_CHECKOUT,
        search=MORNING_SEARCH,
        insert_after=MORNING_INSERT,
        label="morning_checkout.py",
    ))

    print()
    print("=" * 55)
    if all(results):
        print(f"{OK} Все патчи применены.")
        print()
        print("Следующий шаг:")
        print("  1. Положи garden_tools.py в studio/")
        print("  2. Запусти студию — Финч начнёт работать")
    else:
        print(f"{FAIL} Некоторые патчи не применились — проверь вывод выше.")
    print("=" * 55)
