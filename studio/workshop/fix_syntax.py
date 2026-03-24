"""
fix_syntax.py
─────────────
1. Восстанавливает ui.py из бэкапа
2. Применяет чистый патч для NFT каталога
Положи в студия 2/studio/workshop/ рядом с ui.py, двойной клик.
"""

import re
import shutil
from pathlib import Path

HERE = Path(__file__).parent
UI_FILE = HERE / "ui.py"

print("=" * 55)
print("  fix_syntax — Six Fingers Studio")
print("=" * 55)

# ── Найти бэкап ───────────────────────────────────────────────
backups = sorted(HERE.glob("ui.py.bak*"), key=lambda p: p.stat().st_mtime)
if not backups:
    print("❌ Бэкап не найден!")
    print("   Ищу ui.py.bak* в папке workshop/")
    input("Enter..."); exit(1)

# Берём самый ранний бэкап (до всех патчей)
best_backup = backups[0]
print(f"📂 Найдено бэкапов: {len(backups)}")
for b in backups:
    print(f"   {b.name}")

# Проверим все бэкапы на отсутствие SyntaxError
good_backup = None
for bak in backups:
    content = bak.read_text(encoding="utf-8", errors="ignore")
    if "SyntaxError" not in content and "break" not in re.findall(r'^break$', content, re.MULTILINE):
        # Попробуем скомпилировать
        try:
            compile(content, str(bak), "exec")
            good_backup = bak
            break
        except SyntaxError:
            continue

if not good_backup:
    # Берём самый ранний
    good_backup = backups[0]
    print(f"⚠️  Не нашёл идеальный бэкап, беру самый ранний: {good_backup.name}")
else:
    print(f"✅ Рабочий бэкап: {good_backup.name}")

# Восстановить
shutil.copy2(good_backup, UI_FILE)
print(f"✅ ui.py восстановлен из {good_backup.name}")

text = UI_FILE.read_text(encoding="utf-8")
changes = 0

# ── Найти 00_REGISTRY_NFT/catalog.json ───────────────────────
studio_root = HERE.parent.parent
nft_catalog = studio_root / "00_REGISTRY_NFT" / "catalog.json"
if not nft_catalog.exists():
    found = list(studio_root.rglob("00_REGISTRY_NFT/catalog.json"))
    if found:
        nft_catalog = found[0]
    else:
        print("❌ 00_REGISTRY_NFT/catalog.json не найден!")
        input("Enter..."); exit(1)

print(f"✅ NFT каталог: {nft_catalog}")

# ── ПАТЧ 1: статика /nft_registry ────────────────────────────
if '/nft_registry' not in text:
    m = re.search(r'app\.add_static_files\(["\']\/assets["\'][^\n]*\n', text)
    if m:
        line = 'app.add_static_files("/nft_registry", "00_REGISTRY_NFT")  # NFT images\n'
        text = text[:m.end()] + line + text[m.end():]
        changes += 1
        print("✅ Патч 1: статика /nft_registry добавлена")
else:
    print("⏭  Патч 1: уже есть")

# ── ПАТЧ 2: show_assets_dialog — вставить NFT загрузку ───────
# Ищем блок загрузки NFT каталога в show_assets_dialog
# Паттерн: nft_path = None ... for cp in [...]
OLD_NFT_BLOCK = re.search(
    r'        nft_path = None\n        for cp in \[(.+?)\]:\n            if cp\.exists\(\):',
    text, re.DOTALL
)

# Путь через __file__ — три уровня вверх от ui.py = студия 2/
NEW_NFT_BLOCK = (
    '        nft_path = None\n'
    '        _nft_search = [\n'
    '            _P(__file__).resolve().parent.parent.parent / "00_REGISTRY_NFT" / "catalog.json",\n'
    '            BASE_DIR / "00_REGISTRY_NFT" / "catalog.json",\n'
    '        ]\n'
    '        for _ncp in _nft_search:\n'
    '            if _ncp.exists():\n'
    '                nft_path = _ncp\n'
    '                break\n'
    '        if nft_path is not None:\n'
    '            if True:'
)

if OLD_NFT_BLOCK:
    text = text[:OLD_NFT_BLOCK.start()] + NEW_NFT_BLOCK + text[OLD_NFT_BLOCK.end():]
    changes += 1
    print("✅ Патч 2: путь к NFT каталогу исправлен")
else:
    print("⏭  Патч 2: блок nft_path не найден — show_assets_dialog_v3 не установлен?")

# ── Сохранить ─────────────────────────────────────────────────
if changes > 0:
    # Проверим синтаксис перед сохранением
    try:
        compile(text, "ui.py", "exec")
        UI_FILE.write_text(text, encoding="utf-8")
        print(f"\n🎉 Готово! Изменений: {changes}")
        print("   → Синтаксис проверен ✅")
        print("   → Перезапусти студию")
    except SyntaxError as e:
        print(f"\n❌ Синтаксическая ошибка после патча: {e}")
        print("   ui.py не изменён — студия работает с восстановленным файлом")
else:
    print("\n✅ Файл восстановлен. show_assets_dialog_v3 нужно установить отдельно.")

print(f"\n📁 Бэкап использован: {good_backup}")
input("\nEnter для закрытия...")
