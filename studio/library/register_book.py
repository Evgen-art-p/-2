"""
📚 Регистратор книг Библиотеки Грондхейма

Сканирует папки секций, находит .txt/.md файлы которых нет в catalog.json,
и добавляет их автоматически.

Использование:
  python studio\\library\\register_book.py              — добавить новые книги
  python studio\\library\\register_book.py --dry         — показать что добавится
  python studio\\library\\register_book.py --list        — все книги в каталоге
"""

import json
import sys
from pathlib import Path

# ═══════════════════════════════════════════════════════
# КОНФИГ
# ═══════════════════════════════════════════════════════

LIBRARY_ROOT = Path("studio/library")
CATALOG_FILE = LIBRARY_ROOT / "catalog.json"

SECTIONS = ["craft", "psychology", "marketing", "tech", "grondheim", "product"]
BOOK_EXTENSIONS = {".txt", ".md"}
SKIP_FILES = {"_placeholder.md", "_placeholder.txt"}

# ID-префиксы по секции
SECTION_PREFIX = {
    "craft": "craft",
    "psychology": "psych",
    "marketing": "mktg",
    "tech": "tech",
    "grondheim": "grond",
    "product": "prod",
}

# Автотеги по секции
SECTION_AUTO_TAGS = {
    "craft": ["ремесло"],
    "psychology": ["психология"],
    "marketing": ["маркетинг"],
    "tech": ["технологии"],
    "grondheim": ["грондхейм"],
    "product": ["продукт"],
}


# ═══════════════════════════════════════════════════════
# УТИЛИТЫ
# ═══════════════════════════════════════════════════════

def load_catalog() -> dict:
    if not CATALOG_FILE.exists():
        print(f"❌ Каталог не найден: {CATALOG_FILE}")
        sys.exit(1)
    return json.loads(CATALOG_FILE.read_text(encoding="utf-8"))


def save_catalog(catalog: dict):
    CATALOG_FILE.write_text(
        json.dumps(catalog, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def get_next_id(catalog: dict, section: str) -> str:
    prefix = SECTION_PREFIX.get(section, section[:5])
    existing_nums = []
    for b in catalog.get("books", []):
        if b["id"].startswith(prefix + "_"):
            try:
                existing_nums.append(int(b["id"].split("_")[-1]))
            except ValueError:
                pass
    next_num = max(existing_nums, default=0) + 1
    return f"{prefix}_{next_num:03d}"


def extract_tags(filepath: Path, section: str) -> list:
    """Автотеги секции + слова из первых заголовков файла."""
    tags = list(SECTION_AUTO_TAGS.get(section, []))
    try:
        text = filepath.read_text(encoding="utf-8")[:2000].lower()
        for line in text.split("\n")[:20]:
            line = line.strip()
            if line.startswith("#") or line.startswith("##") or (line and line[0].isupper()):
                words = line.replace("#", "").strip().split()
                for w in words:
                    w = w.strip(".,;:!?()«»\"'—-")
                    if len(w) > 3 and w not in tags and w.isalpha():
                        tags.append(w)
                        if len(tags) >= 6:
                            return tags
    except Exception:
        pass
    return tags[:6]


# ═══════════════════════════════════════════════════════
# СКАНИРОВАНИЕ
# ═══════════════════════════════════════════════════════

def scan_new_books(catalog: dict) -> list:
    registered = {b.get("file", "") for b in catalog.get("books", [])}
    new_books = []

    for section in SECTIONS:
        section_dir = LIBRARY_ROOT / section
        if not section_dir.exists():
            continue

        for filepath in sorted(section_dir.iterdir()):
            if not filepath.is_file():
                continue
            if filepath.suffix.lower() not in BOOK_EXTENSIONS:
                continue
            if filepath.name in SKIP_FILES:
                continue

            rel_path = f"{section}/{filepath.name}"
            if rel_path in registered:
                continue

            book_id = get_next_id(catalog, section)
            title = filepath.stem
            tags = extract_tags(filepath, section)

            book = {
                "id": book_id,
                "title": title,
                "section": section,
                "tags": tags,
                "depth": "basic",
                "file": rel_path,
                "source": "",
                "linked_books": [],
            }

            new_books.append(book)
            catalog["books"].append(book)

    return new_books


# ═══════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════

def main():
    dry_run = "--dry" in sys.argv

    if "--list" in sys.argv:
        catalog = load_catalog()
        books = catalog.get("books", [])
        print(f"📚 В каталоге {len(books)} книг:\n")
        for b in books:
            exists = "✅" if (LIBRARY_ROOT / b.get("file", "")).exists() else "📝"
            tags = ", ".join(b.get("tags", [])[:4])
            print(f"  {exists} [{b['section']}] {b['id']}: {b['title']} ({b['depth']}) [{tags}]")
        return

    catalog = load_catalog()
    new_books = scan_new_books(catalog)

    if not new_books:
        print("📚 Новых книг не найдено. Каталог актуален.")
        return

    print(f"📚 Найдено {len(new_books)} новых книг:\n")
    for b in new_books:
        print(f"  ✨ [{b['section']}] {b['id']}: {b['title']}")
        print(f"     Теги: {', '.join(b['tags'])}")
        print()

    if dry_run:
        print("🔍 --dry: ничего не записано. Убери --dry чтобы добавить.")
        return

    save_catalog(catalog)
    print(f"✅ Каталог обновлён: {len(catalog['books'])} книг")
    print(f"💾 {CATALOG_FILE}")
    print()
    print("💡 Подкрути depth и теги в catalog.json если нужно")


if __name__ == "__main__":
    main()
