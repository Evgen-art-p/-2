# patch_living_book_roles.py — Добавляет A00 и A00a в LIVING_BOOK_ROLE_OPTIONS
# Запуск: python patch_living_book_roles.py

from pathlib import Path
import shutil

TARGET = Path("studio/ui_registry.py")

if not TARGET.exists():
    print("❌ studio/ui_registry.py не найден!")
    exit(1)

content = TARGET.read_text(encoding="utf-8")
backup = TARGET.with_suffix(".py.bak2")
shutil.copy(TARGET, backup)

old = '''LIVING_BOOK_ROLE_OPTIONS = [
    "", "A01", "A02", "A03", "A04", "A05",
    "A06", "A07", "A08", "A09", "A10", "A11", "A12",
    "A13", "A14", "A15", "A16",
]'''

new = '''LIVING_BOOK_ROLE_OPTIONS = [
    "", "A00", "A00a",
    "A01", "A02", "A03", "A04", "A05",
    "A06", "A07", "A08", "A09", "A10", "A11", "A12",
    "A13", "A14", "A15", "A16",
]'''

if old in content:
    content = content.replace(old, new)
    TARGET.write_text(content, encoding="utf-8")
    print("✅ Добавлены A00 и A00a в LIVING_BOOK_ROLE_OPTIONS")
else:
    print("⚠️  Строка не найдена (возможно уже применён)")
    backup.unlink(missing_ok=True)
