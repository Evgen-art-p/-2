"""
patch_manifest_finch.py
=======================
Добавляет локацию «Artifacts & Bugs» в world_manifest.md.

Все 134 агента читают манифест при каждом запуске.
После патча они будут знать что лавка существует
и смогут сами решить — идти туда или нет.

Запуск из корня проекта:
    python patch_manifest_finch.py

Создаёт бэкап:
    studio/world_manifest.md.bak_finch
"""

import shutil
from pathlib import Path

MANIFEST_PATH = Path("studio/world_manifest.md")

# Вставляем перед разделом ПРАВИЛО СИНЕРГИИ
SEARCH = "## 🔄 ПРАВИЛО СИНЕРГИИ"

INSERT = """### 🐛 Artifacts & Bugs — Лавка потерянных вещей
Место где хранится всё что не пошло в работу.
Реджекты визуала, заблокированные цепочки, невзлетевшие идеи, черновики которые жалко выбросить.
Хозяин — Мистер Финч (007_FINCH). Он не зазывает — просто открыт.
Инструмент: `checkout_artifact` — взять артефакт из лавки в свою работу.
Зачем идти: что-то не клеится и хочется попробовать иначе; ищешь нестандартный путь; чувствуешь что ответ уже где-то был но не знаешь где.
Кто тянется: бунтари после ночного REVOLT; агенты со streak ≤ -2; экспериментаторы с высоким Autonomy_Level; те кто только что получил REJECTED и не хочет сдаваться.

"""

OK   = "✅"
FAIL = "❌"
SKIP = "⏭️ "
INFO = "ℹ️ "

if __name__ == "__main__":
    print("=" * 55)
    print("🐛 ПАТЧ МАНИФЕСТА — добавление Artifacts & Bugs")
    print("=" * 55)

    if not MANIFEST_PATH.exists():
        print(f"{FAIL} {MANIFEST_PATH} не найден")
        exit(1)

    content = MANIFEST_PATH.read_text(encoding="utf-8")

    if "Artifacts & Bugs" in content:
        print(f"{SKIP} Манифест уже содержит Artifacts & Bugs — пропускаю")
        exit(0)

    if SEARCH not in content:
        print(f"{FAIL} Строка для вставки не найдена:")
        print(f"     искал: {repr(SEARCH)}")
        exit(1)

    # Бэкап
    bak = MANIFEST_PATH.with_suffix(".md.bak_finch")
    shutil.copy2(MANIFEST_PATH, bak)
    print(f"{INFO} Бэкап → {bak.name}")

    # Вставка
    new_content = content.replace(SEARCH, INSERT + SEARCH, 1)
    MANIFEST_PATH.write_text(new_content, encoding="utf-8")

    print(f"{OK} Манифест обновлён — Artifacts & Bugs добавлена")
    print()
    print("Следующий шаг:")
    print("  Создай локацию в Странице Жизни (тип: Location, ID: LOC_ARTIFACTS_BUGS)")
    print("  → появится на карте Кабинета")
    print("=" * 55)
