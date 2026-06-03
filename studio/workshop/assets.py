# studio/workshop_assets.py — Загрузка каталога ассетов
# Вынесено из ui_workshop.py (строки 1141-1218)

import json
from pathlib import Path
from studio.config import BASE_DIR


_CATALOG_CACHE: str | None = None  # Кеш каталога — грузим 1 раз за сессию


def _load_asset_catalog(force_reload: bool = False) -> str:
    """Читает assets_catalog.json и форматирует список для агентов.
    Результат кешируется — повторные вызовы возвращают кеш без чтения диска."""
    global _CATALOG_CACHE
    if _CATALOG_CACHE is not None and not force_reload:
        return _CATALOG_CACHE

    for catalog_path in [
        Path("assets_catalog.json"),
        BASE_DIR / "assets_catalog.json",
        Path("assets/catalog.json"),
    ]:
        if catalog_path.exists():
            break
    else:
        print("[CATALOG] Файл assets_catalog.json не найден")
        return ""

    try:
        data = json.loads(catalog_path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            assets = data
        else:
            assets = data.get("assets", [])

        if not assets:
            return ""

        lines = [
            "=== КАТАЛОГ АССЕТОВ СТУДИИ ===",
            "Используй ТОЛЬКО эти ID при ссылках на персонажей и локации!",
            "FORMAT: ID | NAME | CATEGORY | VISUAL_ANCHOR | MOOD",
            ""
        ]

        chars = [a for a in assets if a.get("category") == "character"]
        locs  = [a for a in assets if a.get("category") == "location"]
        props = [a for a in assets if a.get("category") == "prop"]

        for group_label, group in [
            ("ПЕРСОНАЖИ", chars),
            ("ЛОКАЦИИ", locs),
            ("РЕКВИЗИТ", props),
        ]:
            if not group:
                continue
            lines.append(f"--- {group_label} ---")
            for asset in group:
                anchor = asset.get("visual_anchor", "")
                if isinstance(anchor, list):
                    anchor = "; ".join(anchor[:2])
                anchor_short = anchor[:80] + "..." if len(anchor) > 80 else anchor

                mood = asset.get("mood", [])
                if isinstance(mood, list):
                    mood = ", ".join(mood[:3])

                _rl = asset.get('ref_level', '')
                _ri = {'truth': '🔒', 'orientation': '🧭', 'inspiration': '✨'}.get(_rl, '')
                _rp = f'{_ri} ' if _ri else ''
                lines.append(
                    f"{_rp}{asset.get('id','?')} | {asset.get('name','?')} | "
                    f"{asset.get('category','?')} | {anchor_short} | {mood}"
                )
            lines.append("")

        lines += ["ПРАВИЛО: используй ТОЛЬКО ID из этого каталога!", "=== КОНЕЦ КАТАЛОГА ==="]
        result = "\n".join(lines)
        _CATALOG_CACHE = result
        print(f"[CATALOG] Загружено {len(assets)} ассетов "
              f"({len(chars)} персонажей, {len(locs)} локаций, {len(props)} реквизита)")
        return result
    except Exception as ex:
        print(f"[CATALOG ERROR] {ex}")
        import traceback
        traceback.print_exc()
        return ""


# ═══════════════════════════════════════════════════════════════════
# ПАТЧ v3-fix: Категории + подпапки + регистрация в каталоге
# ═══════════════════════════════════════════════════════════════════

CATEGORY_FOLDERS = {
    "character": "characters",
    "location": "locations",
    "prop": "props",
    "reference": "references",
    "reference_image": "references",
    "reference_doc": "references",
    "reference_video": "references",
}


def invalidate_catalog_cache():
    """Сбрасывает кеш — _load_asset_catalog() перечитает файл."""
    global _CATALOG_CACHE
    _CATALOG_CACHE = None
    print("[CATALOG] Кеш сброшен")


def get_category_folder(category: str) -> str:
    """Возвращает имя подпапки для категории."""
    return CATEGORY_FOLDERS.get(category, "references")


def ensure_asset_subfolders(assets_dir: Path):
    """Создаёт все подпапки категорий в assets/."""
    for folder_name in set(CATEGORY_FOLDERS.values()):
        (assets_dir / folder_name).mkdir(parents=True, exist_ok=True)


def move_file_to_category(filepath: Path, category: str) -> Path:
    """
    Перемещает файл в подпапку категории внутри assets/.
    Возвращает новый путь.
    
    Пример:
        assets/Petr.png  →  assets/characters/Petr.png
    """
    import shutil as _shutil

    subfolder = get_category_folder(category)
    assets_dir = filepath.parent

    # Если файл УЖЕ в подпапке — ищем assets/ выше
    if assets_dir.name in set(CATEGORY_FOLDERS.values()):
        assets_dir = assets_dir.parent

    target_dir = assets_dir / subfolder
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / filepath.name

    # Не двигаем если уже на месте
    if filepath == target_path or filepath.parent == target_dir:
        print(f"[CATALOG] 📁 Уже на месте: {subfolder}/{filepath.name}")
        return filepath

    if target_path.exists():
        target_path.unlink()

    _shutil.move(str(filepath), str(target_path))
    print(f"[CATALOG] 📁 Перемещён: {filepath.name} → {subfolder}/{filepath.name}")
    return target_path


def register_uploaded_asset(
    filepath: Path,
    category: str = "reference",
    name: str = "",
    visual_anchor: str = "",
    mood: str = "",
    client_slug: str = "",
    move_to_subfolder: bool = True,
    ref_level: str = "inspiration",
) -> dict | None:
    """
    Перемещает файл в подпапку категории,
    регистрирует в assets_catalog.json, сбрасывает кеш.
    """
    import time

    # ШАГ 1: Перемещаем файл
    if move_to_subfolder and filepath.exists():
        filepath = move_file_to_category(filepath, category)

    # ШАГ 2: Ищем каталог
    catalog_path = None
    for cp in [
        Path("assets_catalog.json"),
        BASE_DIR / "assets_catalog.json",
        Path("assets/catalog.json"),
    ]:
        if cp.exists():
            catalog_path = cp
            break

    if catalog_path is None:
        catalog_path = BASE_DIR / "assets_catalog.json"
        catalog_path.write_text("[]", encoding="utf-8")
        print(f"[CATALOG] Создан: {catalog_path}")

    try:
        data = json.loads(catalog_path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            assets = data.get("assets", [])
            is_wrapped = True
        else:
            assets = data
            is_wrapped = False

        prefix = client_slug if client_slug and client_slug != "_sandbox" else "upload"
        asset_id = f"{prefix}_{int(time.time())}_{filepath.stem[:20]}"

        new_asset = {
            "id": asset_id,
            "name": name or filepath.stem.replace("_", " ").replace("-", " ").title(),
            "category": category,
            "visual_anchor": visual_anchor or f"Загруженный файл: {filepath.name}",
            "mood": mood if isinstance(mood, list) else ([mood] if mood else []),
            "file_path": str(filepath),
            "file_name": filepath.name,
            "subfolder": get_category_folder(category),
            "source": "upload",
            "client": client_slug or "_sandbox",
            "ref_level": ref_level or "inspiration",
        }

        # Дедупликация
        assets = [
            a for a in assets
            if not (a.get("file_name") == filepath.name
                    and a.get("client") == new_asset["client"])
        ]
        assets.append(new_asset)
        assets.sort(key=lambda a: a.get("name", "").lower())

        if is_wrapped:
            data["assets"] = assets
        else:
            data = assets

        catalog_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        invalidate_catalog_cache()
        print(f"[CATALOG] ✅ {asset_id} → {get_category_folder(category)}/{filepath.name}")
        return new_asset

    except Exception as ex:
        print(f"[CATALOG] ❌ Ошибка: {ex}")
        import traceback
        traceback.print_exc()
        return None


def unregister_asset(file_name: str, client_slug: str = "") -> bool:
    """Удаляет ассет из каталога."""
    for cp in [
        Path("assets_catalog.json"),
        BASE_DIR / "assets_catalog.json",
        Path("assets/catalog.json"),
    ]:
        if cp.exists():
            catalog_path = cp
            break
    else:
        return False

    try:
        data = json.loads(catalog_path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            assets = data.get("assets", [])
            is_wrapped = True
        else:
            assets = data
            is_wrapped = False

        before = len(assets)
        assets = [
            a for a in assets
            if not (a.get("file_name") == file_name
                    and (not client_slug or a.get("client") == client_slug))
        ]

        if len(assets) < before:
            if is_wrapped:
                data["assets"] = assets
            else:
                data = assets
            catalog_path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
            invalidate_catalog_cache()
            print(f"[CATALOG] 🗑️ Удалён: {file_name}")
            return True
        return False

    except Exception as ex:
        print(f"[CATALOG] ❌ Ошибка удаления: {ex}")
        return False
