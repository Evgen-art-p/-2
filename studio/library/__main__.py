from studio.library.library import *
import sys

if "--list" in sys.argv:
    catalog = _load_catalog()
    books = catalog.get("books", [])
    sections = catalog.get("sections", {})
    print(f"📚 Библиотека Грондхейма: {len(books)} книг\n")
    for sec_id, sec_desc in sections.items():
        sec_books = [b for b in books if b.get("section") == sec_id]
        print(f"  [{sec_id}] {sec_desc}")
        for b in sec_books:
            has_file = "✅" if (LIBRARY_ROOT / b.get("file", "")).exists() else "📝"
            print(f"    {has_file} {b['id']}: {b['title']} ({b['depth']})")
        if not sec_books:
            print("    (пусто)")
        print()
elif "--stats" in sys.argv:
    catalog = _load_catalog()
    books = catalog.get("books", [])
    existing = sum(1 for b in books if (LIBRARY_ROOT / b.get("file", "")).exists())
    print(f"📚 Всего книг в каталоге: {len(books)}")
    print(f"✅ С содержимым: {existing}")
    print(f"📝 Без файла: {len(books) - existing}")
elif "--pick" in sys.argv:
    idx = sys.argv.index("--pick")
    dept = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else "living_book"
    book = pick_book_for_agent(dept=dept)
    if book:
        print(f"📚 Для цеха [{dept}]: «{book['title']}» ({book['depth']})")
    else:
        print(f"📭 Для цеха [{dept}] книг не нашлось")
else:
    print("📚 Команды: --list, --stats, --pick <dept>")