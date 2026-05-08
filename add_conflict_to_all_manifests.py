# add_conflict_to_all_manifests.py
# Запустить: python add_conflict_to_all_manifests.py
# Делает: удаляет Author_ID и qa_agent, добавляет conflict_mode в корень

import json
from pathlib import Path

MODULES_DIR = Path("studio/modules")

# Список цехов (папки с manifest.json)
workshops = [d for d in MODULES_DIR.iterdir() if d.is_dir() and (d / "manifest.json").exists()]

print(f"Найдено цехов: {len(workshops)}")
print("=" * 50)

for workshop_dir in sorted(workshops):
    manifest_path = workshop_dir / "manifest.json"
    backup_path = workshop_dir / "manifest.json.bak_conflict"
    
    # Читаем
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"❌ {workshop_dir.name}: ошибка чтения — {e}")
        continue
    
    # Бэкап
    manifest_path.rename(backup_path)
    
    # Удаляем Author_ID и qa_agent
    removed = []
    for key in ["Author_ID", "qa_agent"]:
        if key in data:
            del data[key]
            removed.append(key)
    
    # Добавляем conflict_mode в корень
    data["conflict_mode"] = "divergent"
    
    # Сохраняем
    manifest_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    
    print(f"✅ {workshop_dir.name}")
    if removed:
        print(f"   Удалено: {', '.join(removed)}")
    print(f"   Добавлено: conflict_mode = divergent")

print("=" * 50)
print("Готово! Все манифесты обновлены.")
print("Бэкапы сохранены как manifest.json.bak_conflict")