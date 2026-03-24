"""
patch_nft_fix.py
────────────────
Патч для ui.py — чинит показ NFT картинок в диалоге ASSETS.

Запуск:
  1. Положи этот файл рядом с ui.py (студия 2/studio/workshop/)
  2. Двойной клик или: python patch_nft_fix.py
"""

import shutil
from pathlib import Path

# ── Найти ui.py ───────────────────────────────────────────────
HERE = Path(__file__).parent
UI_FILE = HERE / "ui.py"

if not UI_FILE.exists():
    # Попробуем найти рядом
    for candidate in [
        HERE / "studio" / "workshop" / "ui.py",
        HERE.parent / "ui.py",
        HERE.parent / "workshop" / "ui.py",
    ]:
        if candidate.exists():
            UI_FILE = candidate
            break
    else:
        input("❌ ui.py не найден! Положи скрипт рядом с ui.py и запусти снова.\nEnter для выхода...")
        exit(1)

print(f"✅ Найден: {UI_FILE}")

# ── Бэкап ─────────────────────────────────────────────────────
backup = UI_FILE.with_suffix(".py.bak_nft")
shutil.copy2(UI_FILE, backup)
print(f"💾 Бэкап: {backup.name}")

text = UI_FILE.read_text(encoding="utf-8")
original = text
changes = 0

# ══════════════════════════════════════════════════════════════
# ПАТЧ 1: Добавить статику NFT на уровне приложения (строка 14)
# ══════════════════════════════════════════════════════════════
OLD1 = 'app.add_static_files("/assets", "assets")  # ref images'
NEW1 = '''app.add_static_files("/assets", "assets")  # ref images
app.add_static_files("/nft_registry", "00_REGISTRY_NFT")  # NFT images'''

if OLD1 in text:
    if '/nft_registry' not in text:
        text = text.replace(OLD1, NEW1, 1)
        changes += 1
        print("✅ Патч 1: статика NFT добавлена")
    else:
        print("⏭  Патч 1: уже применён")
else:
    # Запасной вариант без комментария
    OLD1b = 'app.add_static_files("/assets", "assets")'
    NEW1b = 'app.add_static_files("/assets", "assets")\napp.add_static_files("/nft_registry", "00_REGISTRY_NFT")  # NFT images'
    if OLD1b in text and '/nft_registry' not in text:
        text = text.replace(OLD1b, NEW1b, 1)
        changes += 1
        print("✅ Патч 1 (запасной): статика NFT добавлена")
    else:
        print("⚠️  Патч 1: строка не найдена — добавь вручную после строки с add_static_files assets:")
        print('   app.add_static_files("/nft_registry", "00_REGISTRY_NFT")')

# ══════════════════════════════════════════════════════════════
# ПАТЧ 2: Убрать app.add_static_files из тела show_assets_dialog
# ══════════════════════════════════════════════════════════════
OLD2 = """        # ── Статика для NFT картинок ───────────────────────
        nft_static_dir = BASE_DIR / "00_REGISTRY_NFT"
        if nft_static_dir.exists():
            try:
                app.add_static_files("/nft_registry", str(nft_static_dir))
            except Exception:
                pass  # Уже добавлена"""

if OLD2 in text:
    text = text.replace(OLD2, "", 1)
    changes += 1
    print("✅ Патч 2: лишний add_static_files внутри функции убран")
else:
    print("⏭  Патч 2: блок не найден (уже убран или не было)")

# ══════════════════════════════════════════════════════════════
# ПАТЧ 3: Расширить поиск catalog.json (добавить ../catalog.json)
# ══════════════════════════════════════════════════════════════
OLD3 = """        nft_path = None
        for cp in [
            BASE_DIR / "catalog.json",
            _P("catalog.json"),
        ]:"""

NEW3 = """        nft_path = None
        for cp in [
            BASE_DIR / "catalog.json",
            _P("catalog.json"),
            _P("../catalog.json"),
            BASE_DIR.parent / "catalog.json",
        ]:"""

if OLD3 in text:
    text = text.replace(OLD3, NEW3, 1)
    changes += 1
    print("✅ Патч 3: пути поиска catalog.json расширены")
else:
    print("⏭  Патч 3: уже применён или структура отличается")

# ══════════════════════════════════════════════════════════════
# Сохранить
# ══════════════════════════════════════════════════════════════
if changes > 0:
    UI_FILE.write_text(text, encoding="utf-8")
    print(f"\n🎉 Готово! Применено патчей: {changes}")
    print("   Перезапусти студию — NFT картинки должны появиться.")
else:
    print("\n✅ Всё уже актуально, изменений не потребовалось.")

print(f"\n📁 Бэкап сохранён: {backup}")
input("\nEnter для закрытия...")
