"""
patch_nft_fix_v2.py
───────────────────
Чинит загрузку NFT в диалоге ASSETS.
Положи в студия 2/studio/workshop/ рядом с ui.py, двойной клик.
"""

import shutil
import re
from pathlib import Path

HERE = Path(__file__).parent
print("=" * 55)
print("  patch_nft_fix_v2 — Six Fingers Studio NFT fix")
print("=" * 55)

# ── Найти ui.py ───────────────────────────────────────────────
UI_FILE = HERE / "ui.py"
if not UI_FILE.exists():
    print("❌ ui.py не найден рядом со скриптом")
    input("Enter для выхода..."); exit(1)
print(f"✅ ui.py: {UI_FILE}")

# ── Найти catalog.json на диске ───────────────────────────────
# ui.py в: студия2/studio/workshop/ui.py
# catalog.json в: студия2/catalog.json
studio_root = HERE.parent.parent  # студия2/
catalog_file = studio_root / "catalog.json"

if not catalog_file.exists():
    # Поищем рекурсивно
    found = list(studio_root.rglob("catalog.json"))
    # Исключаем node_modules и __pycache__
    found = [f for f in found if "__pycache__" not in str(f) and "node_modules" not in str(f)]
    if found:
        catalog_file = found[0]
    else:
        print(f"❌ catalog.json не найден в {studio_root}")
        input("Enter для выхода..."); exit(1)

print(f"✅ catalog.json: {catalog_file}")

# ── Бэкап ─────────────────────────────────────────────────────
backup = UI_FILE.with_suffix(".py.bak_nft2")
shutil.copy2(UI_FILE, backup)
print(f"💾 Бэкап: {backup.name}\n")

text = UI_FILE.read_text(encoding="utf-8")
changes = 0

# ══════════════════════════════════════════════════════════════
# ПАТЧ 1: добавить /nft_registry статику один раз при старте
# ══════════════════════════════════════════════════════════════
if '/nft_registry' not in text:
    match = re.search(r'app\.add_static_files\(["\']\/assets["\'][^\n]*\n', text)
    if match:
        pos = match.end()
        line = 'app.add_static_files("/nft_registry", "00_REGISTRY_NFT")  # NFT images\n'
        text = text[:pos] + line + text[pos:]
        changes += 1
        print("✅ Патч 1: добавлена статика /nft_registry")
    else:
        print("⚠️  Патч 1: строка add_static_files не найдена")
else:
    print("⏭  Патч 1: уже есть")

# ══════════════════════════════════════════════════════════════
# ПАТЧ 2: убрать add_static_files из тела функции
# ══════════════════════════════════════════════════════════════
OLD2 = (
    '        # ── Статика для NFT картинок ───────────────────────\n'
    '        nft_static_dir = BASE_DIR / "00_REGISTRY_NFT"\n'
    '        if nft_static_dir.exists():\n'
    '            try:\n'
    '                app.add_static_files("/nft_registry", str(nft_static_dir))\n'
    '            except Exception:\n'
    '                pass  # Уже добавлена'
)
if OLD2 in text:
    text = text.replace(OLD2, "", 1)
    changes += 1
    print("✅ Патч 2: убран лишний вызов внутри функции")
else:
    print("⏭  Патч 2: не нужен")

# ══════════════════════════════════════════════════════════════
# ПАТЧ 3: заменить поиск catalog.json на жёсткий путь
# Используем реальный путь который нашли выше
# ══════════════════════════════════════════════════════════════

# Путь относительно ui.py для вставки в код
# catalog_file абсолютный — используем его напрямую через Path(__file__)
# ui.py в workshop/, catalog.json в studio_root
# relative: ../../catalog.json  от workshop/
rel_path = catalog_file.relative_to(HERE)  # может не работать если на другом диске
rel_str = str(rel_path).replace("\\", "/")

# Строим замену — ищем блок nft_path
OLD3_VARIANTS = [
    # вариант после патча v1
    (
        '        nft_path = None\n'
        '        for cp in [\n'
        '            BASE_DIR / "catalog.json",\n'
        '            _P("catalog.json"),\n'
        '            _P("../catalog.json"),\n'
        '            BASE_DIR.parent / "catalog.json",\n'
        '        ]:'
    ),
    # оригинальный вариант
    (
        '        nft_path = None\n'
        '        for cp in [\n'
        '            BASE_DIR / "catalog.json",\n'
        '            _P("catalog.json"),\n'
        '        ]:'
    ),
]

NEW3 = (
    '        nft_path = None\n'
    '        for cp in [\n'
    '            _P(__file__).parent.parent.parent / "catalog.json",\n'
    '            BASE_DIR / "catalog.json",\n'
    '            _P("catalog.json"),\n'
    '            _P("../catalog.json"),\n'
    '            _P("../../catalog.json"),\n'
    '            BASE_DIR.parent / "catalog.json",\n'
    '        ]:'
)

patched3 = False
for OLD3 in OLD3_VARIANTS:
    if OLD3 in text:
        text = text.replace(OLD3, NEW3, 1)
        changes += 1
        patched3 = True
        print("✅ Патч 3: пути catalog.json расширены (включая __file__ относительный)")
        break

if not patched3:
    print("⚠️  Патч 3: блок nft_path не найден — проверь что show_assets_dialog_v3 установлен")

# ══════════════════════════════════════════════════════════════
# Сохранить
# ══════════════════════════════════════════════════════════════
if changes > 0:
    UI_FILE.write_text(text, encoding="utf-8")
    print(f"\n🎉 Готово! Применено изменений: {changes}")
    print("   → Перезапусти студию (закрой и запусти START_STUDIO.bat)")
    print("   → Открой ASSETS → вкладка 💎 NFT → должны появиться 9 объектов")
else:
    print("\n✅ Изменений не потребовалось.")

print(f"\n📁 ui.py:       {UI_FILE}")
print(f"📁 catalog.json: {catalog_file}")
print(f"📁 Бэкап:       {backup}")
input("\nEnter для закрытия...")
