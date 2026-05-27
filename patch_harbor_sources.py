#!/usr/bin/env python3
"""
patch_harbor_sources.py — Гавань = только runs/ + Маяк.

Убираем из INDEX_SOURCES:
  - knowledge/  (папки нет)
  - city_docs/  (GRONDHEIM_CITY — старый архив, мусор)

Оставляем:
  - runs/       (готовые проекты — это и есть Гавань)
  - Маяк        (index_sensory_lighthouse — живые смыслы агентов)

Запуск:
  python patch_harbor_sources.py
"""

from pathlib import Path

TARGET = Path("studio/harbor_of_meanings.py")

OLD_SOURCES = '''# Источники для индексации
INDEX_SOURCES = {
    "knowledge":    Path("knowledge"),
    "runs":         Path("runs"),
    "city_docs":    Path("GRONDHEIM_CITY"),
}'''

NEW_SOURCES = '''# Источники для индексации
# Гавань = пристань готовых проектов (runs/) + живые смыслы с Маяка
INDEX_SOURCES = {
    "runs": Path("runs"),
}'''

OLD_REINDEX = '''    # 1. Knowledge (SET промпты)
    n = index_directory(INDEX_SOURCES["knowledge"], category="set_knowledge")
    stats["knowledge"] = n
    print(f"[ГАВАНЬ]   knowledge/: {n} чанков")

    # 2. Runs (результаты проектов)
    n = index_directory(INDEX_SOURCES["runs"], category="project_results")
    stats["runs"] = n
    print(f"[ГАВАНЬ]   runs/: {n} чанков")

    # 3. City docs (концепции, лор)
    n = index_directory(INDEX_SOURCES["city_docs"], category="city_lore")
    stats["city_docs"] = n
    print(f"[ГАВАНЬ]   GRONDHEIM_CITY/: {n} чанков")

    # 4. Agent knowledge bases
    n = index_agent_knowledge()
    stats["agent_knowledge"] = n
    print(f"[ГАВАНЬ]   agent knowledge/: {n} чанков")

    # 5. Lighthouse sensory (Чистый Смысл)
    n = index_sensory_lighthouse()
    stats["lighthouse"] = n
    print(f"[ГАВАНЬ]   Маяк (sensory): {n} записей")'''

NEW_REINDEX = '''    # 1. Runs — готовые проекты (главный источник Гавани)
    n = index_directory(INDEX_SOURCES["runs"], category="project_results")
    stats["runs"] = n
    print(f"[ГАВАНЬ]   runs/: {n} чанков")

    # 2. Lighthouse sensory — живые смыслы агентов с Маяка
    n = index_sensory_lighthouse()
    stats["lighthouse"] = n
    print(f"[ГАВАНЬ]   Маяк (sensory): {n} записей")'''


def main():
    if not TARGET.exists():
        print(f"[ПАТЧ] ❌ Файл не найден: {TARGET}")
        return

    text = TARGET.read_text(encoding="utf-8")
    original = text
    applied = 0

    # ПАТЧ 1 — INDEX_SOURCES
    if OLD_SOURCES in text:
        text = text.replace(OLD_SOURCES, NEW_SOURCES, 1)
        print("[ПАТЧ] ✅ INDEX_SOURCES — оставлен только runs/")
        applied += 1
    elif '"knowledge":' not in text:
        print("[ПАТЧ] ⏭  INDEX_SOURCES уже пропатчен")
    else:
        print("[ПАТЧ] ❌ Не найден якорь INDEX_SOURCES")

    # ПАТЧ 2 — reindex_all
    if OLD_REINDEX in text:
        text = text.replace(OLD_REINDEX, NEW_REINDEX, 1)
        print("[ПАТЧ] ✅ reindex_all() — убраны knowledge и city_docs")
        applied += 1
    elif "index_agent_knowledge" not in text:
        print("[ПАТЧ] ⏭  reindex_all уже пропатчен")
    else:
        print("[ПАТЧ] ❌ Не найден якорь reindex_all")

    if text == original:
        print("[ПАТЧ] ℹ️  Файл не изменён")
        return

    # Бэкап
    backup = TARGET.with_suffix(".py.bak_sources")
    backup.write_text(original, encoding="utf-8")
    print(f"[ПАТЧ] 💾 Бэкап: {backup}")

    TARGET.write_text(text, encoding="utf-8")
    print(f"[ПАТЧ] ✅ Записано: {TARGET}")
    print()
    print(f"[ПАТЧ] 🏁 Готово ({applied}/2 патчей)")
    print()
    print("  Гавань теперь индексирует:")
    print("  • runs/   — готовые проекты цехов")
    print("  • Маяк    — живые смыслы агентов (sensory)")
    print()
    print("  Запускай реиндекс:")
    print("  python -m studio.harbor_of_meanings --reindex")


if __name__ == "__main__":
    main()
