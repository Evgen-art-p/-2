"""
index_assets.py
───────────────
Сканирует всю папку студии, находит картинки по filename
и прописывает file_path в assets_catalog.json.

Положи в корень студии 2/ и запусти двойным кликом.
"""

import json
from pathlib import Path

HERE = Path(__file__).parent

print("=" * 55)
print("  index_assets — Six Fingers Studio")
print("=" * 55)

# ── Найти assets_catalog.json ─────────────────────────────────
catalog_path = HERE / "assets_catalog.json"
if not catalog_path.exists():
    print("❌ assets_catalog.json не найден!")
    input("Enter..."); exit(1)

print(f"✅ Каталог: {catalog_path}")

data = json.loads(catalog_path.read_text(encoding="utf-8"))
assets = data.get("assets", data) if isinstance(data, dict) else data
print(f"📦 Ассетов в каталоге: {len(assets)}")

# ── Собрать индекс всех картинок на диске ────────────────────
print("\n🔍 Сканирую папки студии...")

# Папки где искать (исключаем лишнее)
EXCLUDE = {"__pycache__", ".git", "node_modules", ".venv", "venv"}

image_index = {}  # filename.lower() → абсолютный Path

for img in HERE.rglob("*"):
    if not img.is_file():
        continue
    if img.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp", ".gif"}:
        continue
    # Пропускаем исключённые папки
    if any(ex in img.parts for ex in EXCLUDE):
        continue
    name_lower = img.name.lower()
    if name_lower not in image_index:
        image_index[name_lower] = img
    # Приоритет: assets/ > runs/ > остальное
    existing = image_index[name_lower]
    if "assets" in img.parts and "assets" not in existing.parts:
        image_index[name_lower] = img

print(f"🖼  Найдено картинок: {len(image_index)}")

# ── Заполнить file_path ───────────────────────────────────────
found = 0
missing = []

for asset in assets:
    fn = asset.get("filename") or asset.get("file_name", "")
    if not fn:
        missing.append(f'{asset["id"]} (нет filename)')
        continue

    # Уже заполнен и файл существует — пропускаем
    existing_fp = asset.get("file_path", "")
    if existing_fp and Path(existing_fp).exists():
        found += 1
        continue

    # Ищем в индексе
    match = image_index.get(fn.lower())
    if match:
        asset["file_path"] = str(match)
        found += 1
        print(f"  ✅ {asset['id']:40} → {match.relative_to(HERE)}")
    else:
        asset["file_path"] = ""
        missing.append(f'{asset["id"]} ({fn})')

# ── Сохранить ─────────────────────────────────────────────────
if isinstance(data, dict):
    data["assets"] = assets
else:
    data = assets

catalog_path.write_text(
    json.dumps(data, ensure_ascii=False, indent=2),
    encoding="utf-8"
)

print(f"\n{'='*55}")
print(f"✅ Найдено и проиндексировано: {found}")
print(f"❌ Не найдено:                 {len(missing)}")
if missing:
    print("\nНе найденные файлы:")
    for m in missing[:20]:
        print(f"  • {m}")

print(f"\n💾 assets_catalog.json обновлён")
print("   Перезапусти студию — картинки должны появиться!")
input("\nEnter для закрытия...")
