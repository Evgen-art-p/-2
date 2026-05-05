"""
add_cartridge_authors.py — Одноразовый скрипт миграции
Добавляет поле Cartridge_Author_ID в catalog.json для каждого агента.

Запускается ОДИН РАЗ из папки ministry/.
После выполнения — удали или архивируй этот файл.
"""

import json
from pathlib import Path
import config

CATALOG_PATH = Path(config.REGISTRY_PATH)

# ============================================================================
# ТАБЛИЦА АВТОРОВ КАРТРИДЖЕЙ
# Ключ: Workshop_ID
# Значение: ID партнёра-автора (из partners.json)
#
# Сейчас все картриджи созданы Архитектором (P_0000000000).
# Когда появятся сторонние авторы — добавь их сюда.
# ============================================================================

CARTRIDGE_AUTHORS = {
    "residents":   "P_0000000000",   # Лока, Джем, Сет, Оле — Архитектор
    "turbo":       "P_0000000000",   # Shorts/Reels — Архитектор
    "social_mix":  "P_0000000000",   # Соцсети — Архитектор
    "video_long":  "P_0000000000",   # Длинные ролики — Архитектор
    "video_shorts":"P_0000000000",   # TikTok — Архитектор
    "living_book": "P_0000000000",   # Детские сказки — Архитектор
    "logo_design": "P_0000000000",   # Логотипы — Архитектор
    "emo_card":    "P_0000000000",   # Открытки — Архитектор
    "clipmakers":  "P_0000000000",   # Промо-клипы — Архитектор
    "advertising": "P_0000000000",   # Реклама — Архитектор
    "market_hit":  "P_0000000000",   # Маркетинг — Архитектор
    "web_story":   "P_0000000000",   # Веб-истории — Архитектор
}

# ============================================================================
# МИГРАЦИЯ
# ============================================================================

def migrate():
    if not CATALOG_PATH.exists():
        print(f"[ERROR] catalog.json не найден: {CATALOG_PATH}")
        return

    with open(CATALOG_PATH, "r", encoding="utf-8") as f:
        catalog = json.load(f)

    updated = 0
    skipped = 0
    unknown = set()

    for obj in catalog:
        if obj.get("Object_Type_Class") != "agent":
            continue

        workshop = obj.get("Workshop_ID")

        if not workshop:
            skipped += 1
            continue

        author_id = CARTRIDGE_AUTHORS.get(workshop)

        if not author_id:
            unknown.add(workshop)
            skipped += 1
            continue

        # Добавляем только если поля нет (не перезаписываем)
        if "Cartridge_Author_ID" not in obj:
            obj["Cartridge_Author_ID"] = author_id
            updated += 1
        else:
            skipped += 1

    with open(CATALOG_PATH, "w", encoding="utf-8") as f:
        json.dump(catalog, f, ensure_ascii=False, indent=2)

    print(f"[MIGRATE] ✅ Обновлено агентов: {updated}")
    print(f"[MIGRATE] ⏭  Пропущено:         {skipped}")
    if unknown:
        print(f"[MIGRATE] ⚠️  Неизвестные Workshop_ID: {unknown}")
        print(f"[MIGRATE]    Добавь их в CARTRIDGE_AUTHORS вручную")

    # Проверка
    catalog2 = json.load(open(CATALOG_PATH, encoding="utf-8"))
    agents = [o for o in catalog2 if o.get("Object_Type_Class") == "agent"]
    with_author = sum(1 for a in agents if a.get("Cartridge_Author_ID"))
    print(f"\n[VERIFY] Агентов с Cartridge_Author_ID: {with_author} / {len(agents)}")

if __name__ == "__main__":
    print("=" * 50)
    print("МИГРАЦИЯ: добавляем Cartridge_Author_ID")
    print("=" * 50)
    migrate()
