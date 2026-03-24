"""
patch_nft_catalog.py
────────────────────
Чинит путь к NFT каталогу — он в 00_REGISTRY_NFT/catalog.json
Положи в студия 2/studio/workshop/ рядом с ui.py, двойной клик.
"""

import re
import shutil
from pathlib import Path

HERE = Path(__file__).parent
UI_FILE = HERE / "ui.py"

print("=" * 55)
print("  patch_nft_catalog — Six Fingers Studio")
print("=" * 55)

if not UI_FILE.exists():
    print("❌ ui.py не найден рядом со скриптом")
    input("Enter..."); exit(1)

# Найти 00_REGISTRY_NFT/catalog.json
studio_root = HERE.parent.parent  # студия 2/
nft_catalog = studio_root / "00_REGISTRY_NFT" / "catalog.json"

if not nft_catalog.exists():
    # Поищем рекурсивно
    found = list(studio_root.rglob("00_REGISTRY_NFT/catalog.json"))
    if found:
        nft_catalog = found[0]
    else:
        print(f"❌ 00_REGISTRY_NFT/catalog.json не найден!")
        print(f"   Искал в: {studio_root}")
        input("Enter..."); exit(1)

print(f"✅ NFT каталог: {nft_catalog}")

backup = UI_FILE.with_suffix(".py.bak_nftcat")
shutil.copy2(UI_FILE, backup)
print(f"💾 Бэкап: {backup.name}")

text = UI_FILE.read_text(encoding="utf-8")
changes = 0

# ──────────────────────────────────────────────────────────────
# ПАТЧ: заменить блок поиска nft_path
# Любой из вариантов — заменяем на жёсткий путь
# ──────────────────────────────────────────────────────────────

# Абсолютный путь для вставки в код
abs_path = str(nft_catalog).replace("\\", "\\\\")

NEW_NFT_LOAD = (
    f'        # NFT каталог: 00_REGISTRY_NFT/catalog.json\n'
    f'        _nft_abs = _P(__file__).resolve().parent.parent.parent / "00_REGISTRY_NFT" / "catalog.json"\n'
    f'        if not _nft_abs.exists():\n'
    f'            _nft_abs = _P(r"{abs_path}")\n'
    f'        nft_path = _nft_abs if _nft_abs.exists() else None\n'
    f'        if nft_path is not None:\n'
    f'            if True:'
)

# Ищем через regex — любой вариант блока nft_path
pattern = re.compile(
    r'        # [^\n]*[Nn][Ff][Tt][^\n]*\n'  # комментарий с NFT
    r'        nft_path = None\n'
    r'        for cp in \[.*?\]:\n'
    r'            if cp\.exists\(\):',
    re.DOTALL
)

m = pattern.search(text)
if m:
    text = text[:m.start()] + NEW_NFT_LOAD + text[m.end():]
    changes += 1
    print("✅ Патч (regex): блок nft_path заменён")
else:
    # Точный поиск по всем известным вариантам
    OLD_VARIANTS = [
        # оригинальный v3
        (
            '        # ── Загрузить catalog.json (NFT) ──────────────────\n'
            '        nft_path = None\n'
            '        for cp in [\n'
            '            BASE_DIR / "catalog.json",\n'
            '            _P("catalog.json"),\n'
            '        ]:\n'
            '            if cp.exists():'
        ),
        # после патча v1
        (
            '        nft_path = None\n'
            '        for cp in [\n'
            '            BASE_DIR / "catalog.json",\n'
            '            _P("catalog.json"),\n'
            '            _P("../catalog.json"),\n'
            '            BASE_DIR.parent / "catalog.json",\n'
            '        ]:\n'
            '            if cp.exists():'
        ),
        # после патча v2
        (
            '        nft_path = None\n'
            '        for cp in [\n'
            '            _P(__file__).parent.parent.parent / "catalog.json",\n'
            '            BASE_DIR / "catalog.json",\n'
            '            _P("catalog.json"),\n'
            '            _P("../catalog.json"),\n'
            '            _P("../../catalog.json"),\n'
            '            BASE_DIR.parent / "catalog.json",\n'
            '        ]:\n'
            '            if cp.exists():'
        ),
    ]

    found = False
    for OLD in OLD_VARIANTS:
        if OLD in text:
            text = text.replace(OLD, NEW_NFT_LOAD, 1)
            changes += 1
            found = True
            print("✅ Патч (точный): блок nft_path заменён")
            break

    if not found:
        # Последний вариант — просто ищем "nft_path = None"
        if 'nft_path = None' in text:
            # Найдём строку и заменим весь блок до "if cp.exists():"
            idx = text.index('nft_path = None')
            # Найдём конец блока
            end_marker = 'if cp.exists():'
            end_idx = text.index(end_marker, idx) + len(end_marker)
            text = text[:idx-8] + NEW_NFT_LOAD + text[end_idx:]
            changes += 1
            print("✅ Патч (fallback): блок nft_path заменён")
        else:
            print("❌ Блок nft_path не найден в ui.py!")
            print()
            print("Найди в ui.py строку: nft_path = None")
            print("И замени весь блок вручную на:")
            print()
            print(NEW_NFT_LOAD)

# ── /nft_registry статика ─────────────────────────────────────
if '/nft_registry' not in text:
    m2 = re.search(r'app\.add_static_files\(["\']\/assets["\'][^\n]*\n', text)
    if m2:
        line = 'app.add_static_files("/nft_registry", "00_REGISTRY_NFT")  # NFT images\n'
        text = text[:m2.end()] + line + text[m2.end():]
        changes += 1
        print("✅ Статика /nft_registry добавлена")
else:
    print("⏭  Статика /nft_registry уже есть")

# ── Сохранить ─────────────────────────────────────────────────
if changes > 0:
    UI_FILE.write_text(text, encoding="utf-8")
    print(f"\n🎉 Готово! Изменений: {changes}")
    print("   → Перезапусти студию")
    print("   → ASSETS → 💎 NFT → должно быть 9 объектов")
else:
    print("\n⚠️  Ничего не изменено.")

print(f"\n📁 NFT каталог: {nft_catalog}")
print(f"📁 Бэкап: {backup}")
input("\nEnter для закрытия...")
