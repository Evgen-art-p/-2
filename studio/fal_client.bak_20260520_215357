"""
Модуль генерации медиа через Fal.ai
Seedream 4.5 / Nano Banana — с поддержкой референсов для консистентности персонажей
Six Fingers Studio v4 — Pro Mode

Архитектура (v4):
  • Авто-сжатие рефов: Pillow resize 1024px + JPEG q85 → ~200-350 Кб вместо 5-10 Мб
  • Base64 inline транспорт: обходит блокировку CDN upload
  • Submit + polling: не висим на линии → WinError 10054 невозможна
  • Retry + таймауты на скачивании результатов
"""

import fal_client as fal
import httpx
import json
import re
import os
import io
import time
import shutil
import base64
import mimetypes
from pathlib import Path
from studio.config import FAL_KEY  # PROXY_URL не нужен для FAL — работает напрямую
from studio import billing_ledger as _ledger  # ── БИЛЛИНГ ──

# === НАСТРОЙКИ ===
os.environ["FAL_KEY"] = FAL_KEY

# FAL SDK подхватывает системный прокси автоматически — сбрасываем
# чтобы не получать "Server disconnected"
for _proxy_var in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "ALL_PROXY", "all_proxy"):
    os.environ.pop(_proxy_var, None)

OUTPUT_DIR = Path("output/generated")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

RENDER_DIR = Path("output/render")
RENDER_DIR.mkdir(parents=True, exist_ok=True)

ASSETS_DIR = Path("assets")  # дефолт, перезаписывается при load_catalog
CLIENTS_DIR = Path("clients")
_current_client_slug = NoneCLIENTS_DIR = Path("clients")

CATALOG_PATH = Path("assets_catalog.json")
# Фоллбэк на .txt
if not CATALOG_PATH.exists():
    _alt = CATALOG_PATH.with_suffix(".txt")
    if _alt.exists():
        CATALOG_PATH = _alt


# ============================================================
# МОДЕЛИ
# ============================================================

MODELS = {
    "seedream": {
        "edit":  "fal-ai/bytedance/seedream/v4.5/edit",
        "t2i":   "fal-ai/bytedance/seedream/v4.5/text-to-image",
        "label": "Seedream 4.5",
        "max_refs": 10,
        "price": 0.04,
    },
    "nano_banana_2": {
        "edit":  "fal-ai/nano-banana-2/edit",
        "t2i":   "fal-ai/nano-banana-2",
        "label": "Nano Banana 2",
        "max_refs": 14,
        "price": 0.04,
    },
}

ACTIVE_MODEL = "nano_banana_2"


def switch_model(name: str):
    global ACTIVE_MODEL
    if name not in MODELS:
        raise ValueError(f"Модель '{name}' не найдена. Доступны: {list(MODELS.keys())}")
    ACTIVE_MODEL = name
    print(f"🔄 Модель: {MODELS[name]['label']}")


def get_model_info() -> dict:
    return {"active": ACTIVE_MODEL, **MODELS[ACTIVE_MODEL]}


# ============================================================
# ФОРМАТЫ
# ============================================================

IMAGE_FORMATS = {
    "16:9":  "landscape_16_9",
    "9:16":  "portrait_16_9",
    "1:1":   "square",
    "4:3":   "landscape_4_3",
    "3:4":   "portrait_4_3",
    "4:5":   "portrait_4_5",
}

DEFAULT_FORMAT = "16:9"


# ============================================================
# КЭШ CDN
# ============================================================

_upload_cache: dict[str, str] = {}

# ── Настройки сжатия рефов ──────────────────────────────────
REF_MAX_SIDE = 1024       # Макс. пиксель по длинной стороне
REF_JPEG_QUALITY = 85     # Качество JPEG (достаточно для ИИ)
REF_MAX_BYTES = 350_000   # Целевой размер ~350 Кб


def _prepare_ref_image(filepath: str) -> tuple[bytes, str]:
    """
    Подготовка реф-картинки: resize до REF_MAX_SIDE + сжатие в JPEG.
    Возвращает (bytes, mime_type).
    ИИ не нужен оригинал 5-10 Мб — ему хватит 200-350 Кб для понимания
    геометрии, цветов и черт лица.
    """
    try:
        from PIL import Image
    except ImportError:
        # Pillow не установлен — отправляем как есть
        src = Path(filepath)
        data = src.read_bytes()
        mime = mimetypes.guess_type(str(src))[0] or "image/png"
        return data, mime

    src = Path(filepath)
    img = Image.open(str(src))

    # Конвертируем RGBA → RGB (JPEG не поддерживает альфа)
    if img.mode in ("RGBA", "P", "LA"):
        bg = Image.new("RGB", img.size, (255, 255, 255))
        if img.mode == "P":
            img = img.convert("RGBA")
        bg.paste(img, mask=img.split()[-1] if "A" in img.mode else None)
        img = bg
    elif img.mode != "RGB":
        img = img.convert("RGB")

    # Resize если больше лимита
    w, h = img.size
    max_side = max(w, h)
    if max_side > REF_MAX_SIDE:
        ratio = REF_MAX_SIDE / max_side
        new_w, new_h = int(w * ratio), int(h * ratio)
        img = img.resize((new_w, new_h), Image.LANCZOS)
        print(f"    📐 Resize: {w}x{h} → {new_w}x{new_h}")

    # Сжимаем в JPEG
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=REF_JPEG_QUALITY, optimize=True)
    data = buf.getvalue()

    original_size = src.stat().st_size
    print(f"    📦 Сжатие: {original_size // 1024} Кб → {len(data) // 1024} Кб")

    return data, "image/jpeg"


def _upload_file(filepath: str, _retries: int = 3) -> str:
    """
    Base64 inline со сжатием — не загружает на CDN FAL.
    1) Resize до 1024px по длинной стороне
    2) Сжатие JPEG quality 85
    3) Base64 encode → data:image/jpeg;base64,...
    Результат: ~200-350 Кб вместо 5-10 Мб оригинала.
    """
    filepath = str(filepath)
    if filepath in _upload_cache:
        return _upload_cache[filepath]
    src = Path(filepath)
    if not src.exists():
        raise FileNotFoundError(f"Файл не найден: {filepath}")
    print(f"  📎 Подготовка рефа: {src.name}")

    data, mime = _prepare_ref_image(filepath)
    b64 = base64.b64encode(data).decode("ascii")
    url = f"data:{mime};base64,{b64}"

    _upload_cache[filepath] = url
    return url


def clear_upload_cache():
    _upload_cache.clear()
    print("🗑️ Кэш загрузок очищен")


# ============================================================
# КАТАЛОГ АССЕТОВ
# ============================================================

_asset_catalog: dict = {}
_asset_paths: dict[str, str] = {}


def load_catalog(catalog_path: str = None, client_slug: str = None):
    """
    Загрузить каталог ассетов.
    Если указан client_slug — ищет каталог и картинки в clients/{slug}/assets/.
    Студийный каталог из корня используется как фоллбэк.
    """
    global _asset_catalog, _asset_paths, _current_client_slug, ASSETS_DIR

    _current_client_slug = client_slug

    # 1. Определить пути
    client_catalog = None
    client_images = None
    studio_catalog = Path(catalog_path) if catalog_path else CATALOG_PATH

    if client_slug and client_slug != "_sandbox":
        client_dir = CLIENTS_DIR / client_slug / "assets"
        cc = client_dir / "catalog.json"
        if cc.exists():
            client_catalog = cc
            ci = client_dir / "images"
            if ci.exists():
                client_images = ci
                ASSETS_DIR = ci  # перенаправляем для static files
            print(f"📂 Клиент [{client_slug}]: каталог найден")

    # 2. Загрузить ассеты
    studio_assets = []
    client_assets = []

    # Студийный каталог (фоллбэк — корневой файл)
    if studio_catalog.exists():
        try:
            data = json.loads(studio_catalog.read_text(encoding="utf-8"))
            studio_assets = data.get("assets", [])
        except Exception as e:
            print(f"⚠️ Каталог студии: {e}")

    # Клиентский каталог
    if client_catalog and client_catalog.exists():
        try:
            cdata = json.loads(client_catalog.read_text(encoding="utf-8"))
            client_assets = cdata.get("assets", [])
            print(f"📦 Клиент [{client_slug}]: {len(client_assets)} ассетов")
        except Exception as e:
            print(f"⚠️ Каталог клиента: {e}")

    # 3. Мерж: если есть клиентский — используем его, студийные как дополнение
    #    Клиентские ID перезаписывают студийные
    merged = {}
    for a in studio_assets:
        merged[a["id"]] = a
    for a in client_assets:
        merged[a["id"]] = a

    _asset_catalog = {
        "version": "2.0",
        "total_assets": len(merged),
        "assets": list(merged.values()),
    }

    # 4. Индексация файлов
    _asset_paths.clear()
    file_index = {}

    # Клиентская папка images/ (приоритет)
    if client_images and client_images.exists():
        for f in client_images.rglob("*"):
            if f.is_file() and f.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp"):
                file_index[f.name.lower()] = str(f)

    # Клиентская папка assets/ целиком (characters/, locations/, etc.)
    if client_slug and client_slug != "_sandbox":
        client_assets_dir = CLIENTS_DIR / client_slug / "assets"
        if client_assets_dir.exists():
            for f in client_assets_dir.rglob("*"):
                if f.is_file() and f.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp"):
                    if f.name.lower() not in file_index:
                        file_index[f.name.lower()] = str(f)

    # Корневая assets/ (фоллбэк)
    fallback_assets = Path("assets")
    if fallback_assets.exists():
        for f in fallback_assets.rglob("*"):
            if f.is_file() and f.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp"):
                if f.name.lower() not in file_index:
                    file_index[f.name.lower()] = str(f)

    # Раны клиента (фоллбэк — если файлы в старых ранах)
    if client_slug and client_slug != "_sandbox":
        runs_dir = Path("runs")
        if runs_dir.exists():
            for run_dir in sorted(runs_dir.iterdir(), reverse=True):
                if run_dir.is_dir() and client_slug in run_dir.name:
                    for f in (run_dir / "assets").rglob("*") if (run_dir / "assets").exists() else []:
                        if f.is_file() and f.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp"):
                            if f.name.lower() not in file_index:
                                file_index[f.name.lower()] = str(f)

    for asset in _asset_catalog.get("assets", []):
        fname = asset.get("filename") or asset.get("file_name", "")
        found = file_index.get(fname.lower()) if fname else None
        if found:
            _asset_paths[asset["id"]] = found
        elif fname:
            stem = Path(fname).stem.lower()
            for key, val in file_index.items():
                if Path(key).stem.lower() == stem:
                    _asset_paths[asset["id"]] = val
                    break
            else:
                # Фоллбэк: file_path из каталога (абсолютный путь)
                fp = asset.get("file_path", "")
                if fp and Path(fp).exists():
                    _asset_paths[asset["id"]] = fp

    loaded = len(_asset_paths)
    total = len(_asset_catalog.get("assets", []))
    who = f"[{client_slug}]" if client_slug else "[студия]"
    print(f"📦 Каталог {who}: {loaded}/{total} ассетов проиндексировано")


def load_client_catalog(client_slug: str):
    """Перезагрузить каталог для конкретного клиента."""
    load_catalog(client_slug=client_slug)


def generate_assets_reference(max_items: int = 300) -> str:
    """
    Генерирует .md справочник из текущего каталога.
    Для передачи в knowledge агентов.
    """
    assets = _asset_catalog.get("assets", [])
    if not assets:
        return ""

    lines = [
        "# 📦 КАТАЛОГ АССЕТОВ — СПРАВОЧНИК",
        "",
        "Используй `ref_ids` при составлении промптов.",
        "Assembly Line подставит изображения по ID.",
        "",
    ]

    cat_labels = {
        "character": "👤 ПЕРСОНАЖИ",
        "location": "🏞️ ЛОКАЦИИ",
        "prop": "📦 РЕКВИЗИТ",
    }

    cats = {}
    for a in assets[:max_items]:
        c = a.get("category", "unknown")
        cats.setdefault(c, []).append(a)

    for cat in ["character", "location", "prop"]:
        items = cats.get(cat, [])
        if not items:
            continue
        lines.append(f"## {cat_labels.get(cat, cat)} ({len(items)})")
        lines.append("")
        lines.append("| ID | Имя | Якорь | Теги |")
        lines.append("|---|---|---|---|")
        for a in items:
            name = a.get("name", "?")
            anchor = str(a.get("visual_anchor", ""))[:60]
            tags = ", ".join(a.get("tags", [])[:4])
            lines.append(f"| `{a['id']}` | {name} | {anchor} | {tags} |")
        lines.append("")

    lines.append("## ПРАВИЛА")
    lines.append("- ref_ids = список ID для каждого кадра")
    lines.append("- Нет подходящего → ref_ids = []")
    lines.append("- НЕ придумывай ID — только из таблицы")

    return "\n".join(lines)

def get_catalog() -> dict:
    """Вернуть загруженный каталог (для UI)"""
    return _asset_catalog


def find_assets(category=None, tags=None, mood=None, ids=None):
    results = []
    for asset in _asset_catalog.get("assets", []):
        if ids and asset["id"] not in ids:
            continue
        if category and asset.get("category") != category:
            continue
        if tags:
            asset_tags = [t.lower() for t in asset.get("tags", [])]
            if not any(t.lower() in asset_tags for t in tags):
                continue
        if mood:
            asset_mood = [m.lower() for m in asset.get("mood", [])]
            if not any(m.lower() in asset_mood for m in mood):
                continue
        entry = {**asset, "path": _asset_paths.get(asset["id"])}
        results.append(entry)
    return results


def _fuzzy_find(aid: str) -> str | None:
    """Ищет ассет по частичному совпадению имени (char_petr → *_Petr)."""
    # Точное совпадение
    path = _asset_paths.get(aid)
    if path:
        return path
    # Убираем префикс
    name = aid
    for prefix in ("char_", "loc_", "prop_", "ref_"):
        if name.startswith(prefix):
            name = name[len(prefix):]
            break
    name_lower = name.lower()
    for catalog_id, catalog_path in _asset_paths.items():
        if name_lower in catalog_id.lower():
            return catalog_path
    return None


def get_asset_path(asset_id: str) -> str | None:
    return _fuzzy_find(asset_id)


def get_asset_paths(asset_ids: list[str]) -> list[str]:
    paths = []
    for aid in asset_ids:
        p = _fuzzy_find(aid)
        if p:
            paths.append(p)
        else:
            print(f"  ⚠️ Ассет не найден: {aid}")
    return paths


def _fuzzy_find_asset(asset_id: str) -> dict | None:
    """Ищет ассет по точному или частичному ID."""
    assets = _asset_catalog.get("assets", [])
    # Точное
    for a in assets:
        if a.get("id") == asset_id:
            return a
    # Fuzzy: убираем префикс и ищем по имени
    name = asset_id
    for prefix in ("char_", "loc_", "prop_", "ref_"):
        if name.startswith(prefix):
            name = name[len(prefix):]
            break
    name_lower = name.lower()
    for a in assets:
        if name_lower in a.get("id", "").lower():
            return a
    return None


def get_asset_name(asset_id: str) -> str:
    """Имя ассета по ID (для бейджей)"""
    a = _fuzzy_find_asset(asset_id)
    if a:
        return a.get("name", asset_id)
    # Фоллбэк: красивое имя из ID
    name = asset_id
    for prefix in ("char_", "loc_", "prop_", "ref_"):
        if name.startswith(prefix):
            name = name[len(prefix):]
            break
    return name.replace("_", " ").title()


def get_asset_category(asset_id: str) -> str:
    """Категория ассета: character / location / prop"""
    a = _fuzzy_find_asset(asset_id)
    if a:
        return a.get("category", "unknown")
    # Угадываем по префиксу
    if asset_id.startswith("char_"):
        return "character"
    if asset_id.startswith("loc_"):
        return "location"
    if asset_id.startswith("prop_"):
        return "prop"
    return "unknown"


def lookup_asset_metadata(asset_id: str) -> dict | None:
    """Метаданные ассета по ID: name, preview_path, tags, description."""
    asset = _fuzzy_find_asset(asset_id)
    if asset:
        return {
            "id":           asset.get("id", asset_id),
            "name":         asset.get("name", asset_id),
            "preview_path": _fuzzy_find(asset.get("id", asset_id)),
            "category":     asset.get("category", "unknown"),
            "tags":         asset.get("tags", []),
            "description":  asset.get("description", ""),
            "visual_anchor": asset.get("visual_anchor", ""),
        }
    return None


def enrich_task_with_assets(tasks: dict) -> dict:
    """Добавляет asset_metadata к каждому элементу задачи."""
    for section in ("thumbnails", "key_frames", "videos", "characters", "badges", "interaction_assets"):
        for item in tasks.get(section, []):
            ref_ids = item.get("ref_ids", [])
            if isinstance(ref_ids, str):
                ref_ids = [ref_ids]
            item["asset_metadata"] = [
                m for rid in ref_ids
                if (m := lookup_asset_metadata(rid)) is not None
            ]
    return tasks


# ============================================================
# ДОБАВЛЕНИЕ В КАТАЛОГ (из /run → /assets)
# ============================================================

def add_to_catalog(
    source_path: str,
    name: str,
    category: str = "character",
    tags: list[str] = None,
    visual_anchor: str = "",
) -> str:
    """
    Копирует файл в /assets, генерит ref_id, добавляет в каталог.
    Возвращает ref_id.
    """
    src = Path(source_path)
    if not src.exists():
        raise FileNotFoundError(f"Файл не найден: {src}")

    # Генерируем ID
    slug = re.sub(r'[^a-z0-9]+', '_', name.lower().strip()).strip('_')
    prefix = {"character": "char", "location": "loc", "prop": "prop"}.get(category, "asset")
    ref_id = f"{prefix}_{slug}"

    # Проверяем уникальность
    existing_ids = {a["id"] for a in _asset_catalog.get("assets", [])}
    if ref_id in existing_ids:
        ref_id = f"{ref_id}_{int(time.time()) % 10000}"

    # Копируем файл
    dest = ASSETS_DIR / src.name
    if dest.exists():
        dest = ASSETS_DIR / f"{ref_id}{src.suffix}"
    shutil.copy2(str(src), str(dest))

    # Добавляем запись
    entry = {
        "id": ref_id,
        "name": name,
        "filename": dest.name,
        "category": category,
        "tags": tags or [],
        "style": "Stylized 3D Realism",
        "background": "transparent",
        "visual_anchor": visual_anchor,
        "description": "",
        "use_cases": [],
        "mood": [],
        "colors": [],
    }

    _asset_catalog.setdefault("assets", []).append(entry)
    _asset_paths[ref_id] = str(dest)

    # Сохраняем каталог
    CATALOG_PATH.write_text(
        json.dumps(_asset_catalog, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print(f"📥 Добавлен в каталог: {ref_id} → {dest.name}")
    return ref_id


# ============================================================
# ЭКСПОРТ В RENDER
# ============================================================

def export_to_render(
    source_path: str,
    project_name: str,
    render_name: str,
) -> str:
    """
    Копирует готовый файл в RENDER/{project_name}/{render_name}
    Возвращает путь.
    """
    src = Path(source_path)
    if not src.exists():
        raise FileNotFoundError(f"Файл не найден: {src}")

    project_dir = RENDER_DIR / re.sub(r'[^\w\-]', '_', project_name)
    project_dir.mkdir(parents=True, exist_ok=True)

    dest = project_dir / render_name
    shutil.copy2(str(src), str(dest))
    print(f"📤 Экспорт: {dest}")
    return str(dest)


# ============================================================
# СКАЧИВАНИЕ
# ============================================================

def _download_file(url: str, filepath: Path, _retries: int = 3):
    """
    Скачивание результата. Стратегия:
    1. Если URL = data:... (base64 inline от sync_mode) — декодируем локально
    2. Если URL = https://... — качаем через FAL API proxy (обходит CDN-блокировки)
    3. Фоллбэк: прямой httpx.get с retry
    """

    # ── Стратегия 1: base64 data URI (мгновенно, без сети) ────
    if url.startswith("data:"):
        print(f"  📥 Декодирую data URI...")
        # data:image/png;base64,iVBOR...
        header, b64_data = url.split(",", 1)
        filepath.write_bytes(base64.b64decode(b64_data))
        return

    # ── Стратегия 2: через FAL-аутентифицированный REST API ──
    # FAL Queue result URL проходит через тот же канал что submit/status
    # и не блокируется прокси (в отличие от CDN fal.media)
    fal_api_base = "https://queue.fal.run"
    if "fal" in url.lower():
        print(f"  📥 Скачиваю через FAL API proxy...")
        try:
            timeout = httpx.Timeout(connect=30, read=120, write=30, pool=30)
            headers = {"Authorization": f"Key {FAL_KEY}"}
            with httpx.Client(timeout=timeout) as client:
                response = client.get(url, headers=headers)
                response.raise_for_status()
                filepath.write_bytes(response.content)
                return
        except Exception as e:
            print(f"  ⚠️  FAL API proxy не сработал: {e} — пробую прямое скачивание...")

    # ── Стратегия 3: прямое скачивание с retry ───────────────
    timeout = httpx.Timeout(connect=30, read=180, write=30, pool=30)
    last_err = None
    for attempt in range(1, _retries + 1):
        try:
            with httpx.Client(timeout=timeout) as client:
                response = client.get(url)
                response.raise_for_status()
                filepath.write_bytes(response.content)
                return
        except Exception as e:
            last_err = e
            print(f"  ⚠️  Скачивание: попытка {attempt}/{_retries} не удалась: {e}")
            if attempt < _retries:
                time.sleep(3 * attempt)
    raise RuntimeError(f"Не удалось скачать результат после {_retries} попыток: {last_err}")


# ============================================================
# ГЕНЕРАЦИЯ — ЯДРО
# ============================================================

# ── Настройки polling (fallback) ─────────────────────────────
POLL_INTERVAL = 2.0       # Секунд между опросами статуса
POLL_MAX_WAIT = 180       # Макс. ожидание (секунд) — 3 минуты


def _generate_sync(endpoint: str, args: dict, label: str = "") -> dict:
    """
    Основной метод генерации. Стратегия:
    1. fal.run() с sync_mode=True → картинка как base64 прямо в ответе
       Никакого CDN, никакого скачивания, никаких SSL timeout
    2. Fallback: submit + polling → скачивание через _download_file
    """

    # ── Стратегия 1: sync_mode (base64 в ответе) ─────────────
    sync_args = {**args, "sync_mode": True}
    try:
        print(f"  📡 sync_mode: отправляю...")
        result = fal.run(endpoint, arguments=sync_args)
        url = result.get("images", [{}])[0].get("url", "")
        if url.startswith("data:"):
            print(f"  ✅ Получено как base64 (без CDN)")
            return result
        else:
            print(f"  ⚠️  sync_mode вернул CDN URL — переключаюсь на polling...")
    except Exception as e:
        print(f"  ⚠️  sync_mode не сработал: {e} — переключаюсь на polling...")

    # ── Стратегия 2: submit + polling (fallback) ──────────────
    return _submit_and_poll(endpoint, args, label=label)


def _submit_and_poll(endpoint: str, args: dict, label: str = "") -> dict:
    """
    Submit + polling: отправляем запрос и опрашиваем статус.
    НЕ держим соединение открытым — WinError 10054 невозможна.
    """
    # 1. Submit — мгновенно отправляем и отключаемся
    handle = fal.submit(endpoint, arguments=args)
    request_id = handle.request_id
    print(f"  📤 Отправлено → {request_id}")

    # 2. Polling — опрашиваем статус отдельными лёгкими запросами
    start = time.time()
    while True:
        elapsed = time.time() - start
        if elapsed > POLL_MAX_WAIT:
            raise TimeoutError(
                f"FAL не ответил за {POLL_MAX_WAIT}с ({label}): {request_id}"
            )

        try:
            status = handle.status()
        except Exception as e:
            print(f"  ⚠️  Статус недоступен: {e} — жду...")
            time.sleep(POLL_INTERVAL)
            continue

        status_name = type(status).__name__
        if isinstance(status, fal.Completed):
            print(f"  ✅ Готово за {elapsed:.1f}с")
            break
        elif isinstance(status, fal.InProgress):
            # Показываем логи если есть
            logs = getattr(status, "logs", [])
            if logs:
                for log in logs[-2:]:
                    msg = log.get("message", "") if isinstance(log, dict) else str(log)
                    if msg:
                        print(f"    📋 {msg}")
            print(f"  ⏳ В работе... ({elapsed:.0f}с)")
        elif isinstance(status, fal.Queued):
            pos = getattr(status, "position", "?")
            print(f"  🔄 В очереди (позиция: {pos}, {elapsed:.0f}с)")
        else:
            print(f"  ❓ Статус: {status_name} ({elapsed:.0f}с)")

        time.sleep(POLL_INTERVAL)

    # 3. Забираем результат отдельным запросом
    result = handle.get()
    return result


def generate_with_refs(
    prompt: str,
    ref_paths: list[str] = None,
    ref_ids: list[str] = None,
    format: str = DEFAULT_FORMAT,
    filename: str = None,
    seed: int = None,
    agent_id: str = "unknown",
    slot_id: str = "unknown",
) -> str:
    paths = list(ref_paths or [])
    if ref_ids:
        paths.extend(get_asset_paths(ref_ids))

    if not paths:
        # Фоллбэк на t2i если рефов нет
        print("  ⚠️ Рефов не найдено — фоллбэк на text-to-image")
        return generate_image(prompt, format=format, filename=filename, seed=seed)

    model = MODELS[ACTIVE_MODEL]
    max_refs = model["max_refs"]
    if len(paths) > max_refs:
        print(f"  ⚠️ {len(paths)} рефов, лимит {max_refs} — обрезаю")
        paths = paths[:max_refs]

    if not filename:
        filename = f"ref_{int(time.time())}.png"

    size = IMAGE_FORMATS.get(format, IMAGE_FORMATS[DEFAULT_FORMAT])

    print(f"🎨 [{model['label']}] Генерирую с {len(paths)} рефами: {prompt[:60]}...")
    print(f"   📐 Формат: {format} ({size})")

    image_urls = [_upload_file(p) for p in paths]

    # Убираем не-ASCII символы из промпта (fal SDK требует ASCII в теле запроса)
    safe_prompt = prompt.encode("ascii", "ignore").decode("ascii").strip()
    if not safe_prompt:
        safe_prompt = "cinematic scene, stylized 3D realism, Pixar style"

    # Prompt Expansion — пространственная логика
    try:
        from studio.prompt_expander import expand_prompt
        safe_prompt = expand_prompt(safe_prompt, mode="auto")
    except ImportError:
        pass

    args = {
        "prompt": safe_prompt,
        "image_urls": image_urls,
        "image_size": size,
    }
    if seed is not None:
        args["seed"] = seed

    # sync_mode → base64 в ответе, fallback → submit+polling
    result = _generate_sync(model["edit"], args, label=f"refs:{filename}")

    img_url = result["images"][0]["url"]
    filepath = OUTPUT_DIR / filename
    _download_file(img_url, filepath)

    # ── BillingLedger: FAL генерация (цена за изображение) ──
    _ledger.record(
        agent_id=agent_id,
        slot_id=slot_id,
        model=f"fal/{MODELS[ACTIVE_MODEL]['label']}",
        prompt_tokens=0,
        completion_tokens=0,
        call_type="image_with_refs",
    )
    # ────────────────────────────────────────────────────────

    print(f"  ✅ {filepath}")
    return str(filepath)


# ============================================================
# ГЕНЕРАЦИЯ БЕЗ РЕФЕРЕНСОВ
# ============================================================

def generate_image(
    prompt: str,
    format: str = DEFAULT_FORMAT,
    filename: str = None,
    seed: int = None,
    agent_id: str = "unknown",
    slot_id: str = "unknown",
) -> str:
    if not filename:
        filename = f"img_{int(time.time())}.png"

    model = MODELS[ACTIVE_MODEL]
    size = IMAGE_FORMATS.get(format, IMAGE_FORMATS[DEFAULT_FORMAT])

    print(f"🎨 [{model['label']}] Генерирую: {prompt[:60]}...")
    print(f"   📐 Формат: {format} ({size})")

    # Убираем не-ASCII символы (fal SDK требует ASCII)
    safe_prompt = prompt.encode("ascii", "ignore").decode("ascii").strip()
    if not safe_prompt:
        safe_prompt = "cinematic scene, stylized 3D realism, Pixar style"

    # Prompt Expansion — пространственная логика
    try:
        from studio.prompt_expander import expand_prompt
        safe_prompt = expand_prompt(safe_prompt, mode="auto")
    except ImportError:
        pass

    args = {
        "prompt": safe_prompt,
        "image_size": size,
        "num_images": 1,
    }
    if seed is not None:
        args["seed"] = seed

    # sync_mode → base64 в ответе, fallback → submit+polling
    result = _generate_sync(model["t2i"], args, label=f"t2i:{filename}")

    img_url = result["images"][0]["url"]
    filepath = OUTPUT_DIR / filename
    _download_file(img_url, filepath)

    # ── BillingLedger: FAL генерация (цена за изображение) ──
    _ledger.record(
        agent_id=agent_id,
        slot_id=slot_id,
        model=f"fal/{MODELS[ACTIVE_MODEL]['label']}",
        prompt_tokens=0,
        completion_tokens=0,
        call_type="image_t2i",
    )
    # ────────────────────────────────────────────────────────

    print(f"  ✅ {filepath}")
    return str(filepath)


# ============================================================
# ПРОМПТ-ХЕЛПЕР
# ============================================================

def build_ref_prompt(
    scene_description: str,
    character_ids: list[str] = None,
    location_ids: list[str] = None,
    style_note: str = "Pixar-like stylized 3D realism",
) -> tuple[str, list[str]]:
    ref_ids = []
    prompt_parts = []
    fig_num = 1

    if character_ids:
        for cid in character_ids:
            asset = next((a for a in _asset_catalog.get("assets", []) if a["id"] == cid), None)
            if asset:
                ref_ids.append(cid)
                name = asset.get("name", cid)
                anchor = asset.get("visual_anchor", "")
                if isinstance(anchor, list):
                    anchor = anchor[0]
                prompt_parts.append(f"The character from Figure {fig_num} ({name}: {anchor})")
                fig_num += 1

    if location_ids:
        for lid in location_ids:
            asset = next((a for a in _asset_catalog.get("assets", []) if a["id"] == lid), None)
            if asset:
                ref_ids.append(lid)
                name = asset.get("name", lid)
                prompt_parts.append(f"in the setting from Figure {fig_num} ({name})")
                fig_num += 1

    figures_desc = ". ".join(prompt_parts)
    prompt = (
        f"{figures_desc}. "
        f"{scene_description}. "
        f"Art style: {style_note}. "
        f"Maintain exact facial features and character identity from reference images. "
        f"Consistent lighting and atmosphere."
    )

    return prompt, ref_ids


# ============================================================
# ПАРСЕР
# ============================================================

def parse_final_md(md_path: str) -> dict:
    text = Path(md_path).read_text(encoding="utf-8")

    def _try_parse(raw: str, label: str = "") -> dict | None:
        """Пытается распарсить JSON, при ошибке — чинит типичные проблемы."""
        try:
            return json.loads(raw)
        except json.JSONDecodeError as e:
            print(f"[PARSE] {label} JSON error: {e}")
        # Починка 1: математические выражения (1+12 → 13, 5*2 → 10)
        import re as _re
        fixed = _re.sub(
            r':\s*(\d+)\s*([+\-*/])\s*(\d+)',
            lambda m: ': ' + str(int(eval(f"{m.group(1)}{m.group(2)}{m.group(3)}"))),
            raw
        )
        # Починка 2: закавыченные скобки ("}" → }, "]" → ])
        fixed = _re.sub(r'^\s*"([}\]])"\s*$', lambda m: m.group(0).replace(f'"{m.group(1)}"', m.group(1)), fixed, flags=_re.MULTILINE)
        # Починка 3: trailing comma перед } или ]
        fixed = _re.sub(r',\s*([}\]])', r'\1', fixed)
        # Починка 3.5: пропущенная ] — паттерн }\n  }\n}, (массив не закрыт)
        fixed = _re.sub(r'(\}\s*\n\s*\}\s*\n\s*\},)', r'}\n      ]\n    },', fixed)
        try:
            result = json.loads(fixed)
            print(f"[PARSE] {label} — починено!")
            return result
        except json.JSONDecodeError:
            pass
        # Починка 4: автобалансировка скобок — считаем дисбаланс и добавляем
        depth_sq = 0  # []
        depth_cr = 0  # {}
        for c in fixed:
            if c == '[': depth_sq += 1
            elif c == ']': depth_sq -= 1
            elif c == '{': depth_cr += 1
            elif c == '}': depth_cr -= 1
        if depth_sq != 0 or depth_cr != 0:
            suffix = ']' * max(0, depth_sq) + '}' * max(0, depth_cr)
            prefix = '{' * max(0, -depth_cr) + '[' * max(0, -depth_sq)
            balanced = prefix + fixed + suffix
            try:
                result = json.loads(balanced)
                print(f"[PARSE] {label} — починено балансировкой скобок! (добавлено: {repr(suffix or prefix)})")
                return result
            except json.JSONDecodeError:
                pass
        # Починка 5: обрезка до последней валидной }
        for end in range(len(fixed) - 1, max(0, len(fixed) - 2000), -1):
            if fixed[end] == '}':
                try:
                    return json.loads(fixed[:end + 1])
                except json.JSONDecodeError:
                    continue
        print(f"[PARSE] {label} — не удалось починить JSON")
        return None

    # 1) Try SYSTEM_JSON_START ... SYSTEM_JSON_END
    pattern = r'SYSTEM_JSON_START[^\n]*\n(.*?)\n[^\n]*SYSTEM_JSON_END'
    match = re.search(pattern, text, re.DOTALL)
    if match:
        raw_json = match.group(1).strip()
        raw_json = raw_json.strip("`").strip()
        if raw_json.startswith("json"):
            raw_json = raw_json[4:].strip()
        result = _try_parse(raw_json, "SYSTEM_JSON")
        if result:
            return result

    # 2) Try fenced ```json ... ``` block
    fence = re.search(r'`{3}json\s*\n(\{.*?\})\s*\n`{3}', text, re.DOTALL)
    if fence:
        result = _try_parse(fence.group(1), "fenced")
        if result:
            return result

    # 3) Fallback: find outermost { } from end of file
    end_pos = text.rfind("}")
    if end_pos != -1:
        depth = 0
        s = -1
        for i in range(end_pos, -1, -1):
            if text[i] == "}":
                depth += 1
            elif text[i] == "{":
                depth -= 1
                if depth == 0:
                    s = i
                    break
        if s != -1:
            result = _try_parse(text[s:end_pos + 1], "fallback")
            if result:
                return result

    raise ValueError(f"No JSON found in {md_path}")


def _resolve_preview_paths(ref_ids: list[str]) -> list[str]:
    """
    Маппим список ref_ids на реальные пути файлов из каталога.
    Поддерживает:
      - Точное совпадение: сайт_окна_1773366661_Petr
      - Студийные алиасы: char_petr → ищет *Petr* или *petr* в ID
      - Локации: loc_objekt_star → ищет *objekt_star* в ID
    """
    paths = []
    for aid in ref_ids:
        # 1. Точное совпадение
        path = _asset_paths.get(aid)
        if path:
            paths.append(path)
            continue

        # 2. Fuzzy: убираем префикс char_/loc_ и ищем по имени
        name = aid
        for prefix in ("char_", "loc_", "prop_", "ref_"):
            if name.startswith(prefix):
                name = name[len(prefix):]
                break
        name_lower = name.lower()

        found = False
        for catalog_id, catalog_path in _asset_paths.items():
            # Ищем имя в конце каталожного ID (после последнего _timestamp_)
            cat_lower = catalog_id.lower()
            if name_lower in cat_lower or cat_lower.endswith("_" + name_lower):
                paths.append(catalog_path)
                found = True
                break

        if not found:
            print(f"  ⚠️ preview_paths: ассет не найден → {aid}")

    return paths


def extract_tasks(data: dict) -> dict:
    """
    Универсальный экстрактор задач для сборочного цеха.
    Автоматически определяет формат входных данных и нормализует
    в единую структуру для assembly.

    Поддерживаемые форматы:
      • Video pipeline (turbo/long) — A05_Финализатор
      • Web Story pipeline — A12_Артур (QA)
      • Любой будущий пайплайн с deliverables.visual[]
    """

    # Авто-загрузка каталога с клиентом — определяем из данных
    _client = None
    # Ищем client slug в ref_ids (формат: клиент_timestamp_name)
    _raw = json.dumps(data, ensure_ascii=False) if data else ""
    _m = re.search(r'"([\w]+)_\d{10}_', _raw)
    if _m and _m.group(1) not in ("char", "loc", "prop", "ref", "ach", "sfx"):
        _client = _m.group(1)
    if not _client:
        # Ищем в каталоге
        for asset in (_asset_catalog or {}).get("assets", []):
            c = asset.get("client", "")
            if c and c != "_sandbox" and c != "?":
                _client = c
                break
    if _client and _client != getattr(load_catalog, '_last_client', None):
        load_catalog(client_slug=_client)
        load_catalog._last_client = _client

    source = _detect_source(data)
    deliverables = source["deliverables"]
    project_id = source["project_id"]

    print(f"  📦 extract_tasks: формат={source['format']}, project={project_id}")

    tasks = {
        "project_id": project_id,
        "thumbnails": [],
        "key_frames": [],
        "videos": [],
        "audio": {},
        "captions": [],
        "edit_plan": {},
        "publication": {
            "description": deliverables.get("description", ""),
            "hashtags": deliverables.get("hashtags", []),
            "posting_time": deliverables.get("posting_time", ""),
        },
        # Доп. данные для Web Story / будущих форматов
        "text": deliverables.get("text", []),
        "interactive": deliverables.get("interactive", []),
        "gamification": deliverables.get("gamification", []),
        "sound": deliverables.get("sound", []),
        "_source_format": source["format"],
        # === НОВЫЕ КАТЕГОРИИ АССЕТОВ (web_story) ===
        "characters": [],        # character_prompts из Новы
        "badges": [],            # achievement_prompts из Новы
        "interaction_assets": [], # interaction_prompts из Новы
        "sfx": [],               # sfx[] с prompt из Рэя
        "music": {},             # suno_prompt из Рэя
        "voice_over": [],        # TTS промпты из Рэя
        "social_post": None,     # Готовый пост (social_mix)
    }

    if source["format"] == "video":
        _extract_video_tasks(deliverables, tasks)
    elif source["format"] == "web_story":
        _extract_web_story_tasks(deliverables, tasks, data)
    elif source["format"] == "social_mix":
        _extract_social_tasks(deliverables, tasks)
    else:
        # Fallback: пробуем video, потом web_story
        _extract_video_tasks(deliverables, tasks)
        if not tasks["key_frames"] and not tasks["thumbnails"]:
            _extract_web_story_tasks(deliverables, tasks, data)

    return tasks


def _detect_source(data: dict) -> dict:
    """Определяем формат и извлекаем deliverables + project_id."""

    # 1) Web Story (A12_Артур / любой агент с my_output.deliverables)
    my_output = data.get("my_output", {})
    if isinstance(my_output, dict) and my_output.get("deliverables"):
        dlv = my_output["deliverables"]
        pid = (
            dlv.get("project_id")
            or my_output.get("final_dna", {}).get("id")
            or data.get("project_id", "unknown")
        )
        return {"format": "web_story", "deliverables": dlv, "project_id": pid}

    # 1.5) Social Mix v2 (Клавдия A12) — ключ post или images в deliverables
    if data.get("deliverables"):
        _dlv = data["deliverables"]
        # Новый формат: deliverables.post + deliverables.images
        if _dlv.get("post") or _dlv.get("images"):
            return {
                "format": "social_mix",
                "deliverables": _dlv,
                "project_id": data.get("project_id", "unknown"),
            }
        # Старый формат (fallback): post_text или image_prompts
        if _dlv.get("post_text") or _dlv.get("image_prompts") or _dlv.get("image_prompt"):
            return {
                "format": "social_mix",
                "deliverables": _dlv,
                "project_id": data.get("project_id", "unknown"),
            }

    # 2) Video pipeline (A05_Финализатор)
    if data.get("deliverables"):
        return {
            "format": "video",
            "deliverables": data["deliverables"],
            "project_id": data.get("project_id", "unknown"),
        }

    # 3) Fallback: ищем deliverables глубже (chain_data и т.д.)
    for key in ("chain_data", "arthur_qa"):
        sub = data.get(key, {})
        if isinstance(sub, dict):
            for k2, v2 in sub.items():
                if isinstance(v2, dict) and v2.get("deliverables"):
                    return {
                        "format": "unknown",
                        "deliverables": v2["deliverables"],
                        "project_id": v2.get("project_id", data.get("project_id", "unknown")),
                    }

    print("  ⚠️ _detect_source: deliverables не найдены")
    return {"format": "unknown", "deliverables": {}, "project_id": data.get("project_id", "unknown")}


def _extract_video_tasks(deliverables: dict, tasks: dict):
    """Парсинг Video pipeline (A05_Финализатор / turbo / long)."""

    # Обложки
    thumb = deliverables.get("thumbnail", {})
    for variant_name in ["variant_a", "variant_b"]:
        variant = thumb.get(variant_name, {})
        prompt = variant.get("banana_prompt") or variant.get("prompt", "")
        if prompt:
            ref_ids = variant.get("ref_ids", [])
            tasks["thumbnails"].append({
                "variant": variant_name,
                "concept": variant.get("concept", ""),
                "prompt": prompt,
                "text_overlay": variant.get("text_overlay", ""),
                "emotion": variant.get("emotion", ""),
                "ref_ids": ref_ids,
                "preview_paths": _resolve_preview_paths(ref_ids),
                "format": variant.get("format", DEFAULT_FORMAT),
                "path": None,
            })

    # Ключевые кадры
    for i, frame in enumerate(deliverables.get("key_frames", [])):
        prompt = frame.get("banana_prompt") or frame.get("prompt", "")
        if prompt:
            ref_ids = frame.get("ref_ids", [])
            tasks["key_frames"].append({
                "index": i + 1,
                "segment": frame.get("segment", ""),
                "purpose": frame.get("purpose", ""),
                "prompt": prompt,
                "ref_ids": ref_ids,
                "preview_paths": _resolve_preview_paths(ref_ids),
                "format": frame.get("format", DEFAULT_FORMAT),
                "path": None,
            })

    # Видео (Veo3)
    for i, clip in enumerate(deliverables.get("veo3_prompts", [])):
        prompt = clip.get("veo3_prompt") or clip.get("prompt", "")
        if prompt:
            dur_str = clip.get("duration", "3.0s")
            duration = float(str(dur_str).replace("s", ""))
            ref_ids = clip.get("ref_ids", [])
            tasks["videos"].append({
                "index": i + 1,
                "segment": clip.get("segment", ""),
                "camera": clip.get("camera", ""),
                "duration": duration,
                "prompt": prompt,
                "ref_ids": ref_ids,
                "preview_paths": _resolve_preview_paths(ref_ids),
                "path": None,
            })

    tasks["audio"] = deliverables.get("audio", tasks["audio"])
    tasks["captions"] = deliverables.get("captions", tasks["captions"])
    tasks["edit_plan"] = deliverables.get("edit_plan", tasks["edit_plan"])


def _extract_web_story_tasks(deliverables: dict, tasks: dict, data: dict = None):
    """
    Парсинг Web Story pipeline (A12_Артур и т.д.).
    Читает:
      - deliverables.visual[]         → key_frames (старый путь, фоллбэк)
      - chain_data.nova_prompts       → key_frames, characters, badges, interaction_assets
      - chain_data.ray_sound          → sfx, music, voice_over
    """
    data = data or {}
    chain = data.get("chain_data") or {}

    def _safe_list(obj, key) -> list:
        """Безопасно извлекает список — не падает на None/str/мусоре."""
        val = obj.get(key) if isinstance(obj, dict) else None
        return val if isinstance(val, list) else []

    def _safe_dict(obj, key) -> dict:
        val = obj.get(key) if isinstance(obj, dict) else None
        return val if isinstance(val, dict) else {}

    # ── НОВА: nova_prompts ────────────────────────────────────
    nova = chain.get("nova_prompts") or {}
    # Если nova — строка-заглушка "{{inherit}}" → пропускаем
    if not isinstance(nova, dict):
        nova = {}

    # ФОЛЛБЭК: если chain_data пуст — Артур мог скопировать промпты в deliverables
    if not nova or not _safe_list(nova, "scene_prompts"):
        nova_fb = {
            "scene_prompts": _safe_list(deliverables, "nova_scene_prompts"),
            "character_prompts": _safe_list(deliverables, "nova_character_prompts"),
            "achievement_prompts": _safe_list(deliverables, "nova_achievement_prompts"),
            "interaction_prompts": _safe_list(deliverables, "nova_interaction_prompts"),
        }
        if any(nova_fb.values()):
            nova = nova_fb
            print("    📋 Нова: данные из deliverables (fallback от Артура)")

    # scene_prompts[] → key_frames (приоритет перед старым visual[])
    nova_scenes = _safe_list(nova, "scene_prompts")
    if nova_scenes:
        for i, sp in enumerate(nova_scenes):
            if not isinstance(sp, dict):
                continue
            main = _safe_dict(sp, "main_image")
            prompt = main.get("positive", "")
            if not prompt:
                continue
            scene_raw = sp.get("scene_name", sp.get("scene_id", f"scene_{i+1:02d}"))
            scene_safe = re.sub(r'[\\/:*?"<>|\s]+', '_', str(scene_raw)).strip('_')
            chars = _safe_list(main, "characters")
            ref_ids = [c["char_id"] for c in chars if isinstance(c, dict) and c.get("char_id")]
            # Извлекаем ID локаций из всего объекта сцены
            scene_text = json.dumps(sp, ensure_ascii=False)
            scene_lower = scene_text.lower()
            # 1. Студийные loc_ ID
            loc_ids = list(set(re.findall(r'loc_[\w]+', scene_text)))
            # 2. Клиентские ID из каталога (формат: клиент_timestamp_name)
            # 3. Поиск по file_name stem (objekt_star, objekt_nov и т.д.)
            for asset in _asset_catalog.get("assets", []):
                if asset.get("category") == "location":
                    aid = asset.get("id", "")
                    fname = asset.get("file_name") or asset.get("filename", "")
                    stem = Path(fname).stem.lower() if fname else ""
                    # Проверяем: полный ID, или stem файла в тексте
                    if aid and aid not in ref_ids and aid not in loc_ids:
                        if aid in scene_text:
                            loc_ids.append(aid)
                        elif stem and len(stem) > 3 and stem in scene_lower:
                            loc_ids.append(aid)
            # Дедупликация: один ассет — один ref_id (предпочитаем клиентский ID)
            seen_stems = set()
            for rid in ref_ids:
                name = rid.lower()
                for pfx in ("char_", "loc_", "prop_"):
                    if name.startswith(pfx):
                        name = name[len(pfx):]
                        break
                seen_stems.add(name.split("_")[-1] if "_" in name else name)
            unique_locs = []
            for lid in loc_ids:
                name = lid.lower()
                for pfx in ("loc_",):
                    if name.startswith(pfx):
                        name = name[len(pfx):]
                        break
                stem = name.split("_")[-1] if "_" in name else name
                if stem not in seen_stems:
                    unique_locs.append(lid)
                    seen_stems.add(stem)
            ref_ids = ref_ids + unique_locs
            tasks["key_frames"].append({
                "index": i + 1,
                "scene": scene_safe,
                "segment": scene_safe,
                "purpose": scene_raw,
                "prompt": prompt,
                "negative": main.get("negative", ""),
                "composition": _safe_dict(main, "composition"),
                "lighting": _safe_dict(main, "lighting"),
                "color_keys": _safe_dict(main, "color_keys"),
                "ref_ids": ref_ids,
                "preview_paths": _resolve_preview_paths(ref_ids),
                "format": sp.get("format", DEFAULT_FORMAT),
                "path": None,
                "background_prompt": _safe_dict(sp, "background").get("prompt", ""),
            })
    else:
        # Фоллбэк: старый visual[] из deliverables
        for i, vis in enumerate(_safe_list(deliverables, "visual")):
            if not isinstance(vis, dict):
                continue
            prompt = vis.get("prompt", "")
            if not prompt:
                continue
            chars_str = vis.get("characters", "")
            ref_ids = [c.strip() for c in chars_str.split(",") if c.strip()] if chars_str else []
            scene_raw = vis.get("scene", f"scene_{i+1:02d}")
            scene_safe = re.sub(r'[\\/:*?"<>|\s]+', '_', str(scene_raw)).strip('_')
            tasks["key_frames"].append({
                "index": i + 1,
                "scene": scene_safe,
                "segment": scene_safe,
                "purpose": scene_raw,
                "prompt": prompt,
                "ref_ids": ref_ids,
                "preview_paths": _resolve_preview_paths(ref_ids),
                "format": vis.get("format", DEFAULT_FORMAT),
                "path": None,
            })

    # character_prompts[] → tasks["characters"]
    for cp in _safe_list(nova, "character_prompts"):
        if not isinstance(cp, dict):
            continue
        prompt = cp.get("positive", "")
        if not prompt:
            continue
        ref_ids = [cp["char_id"]] if cp.get("char_id") else []
        tasks["characters"].append({
            "char_id": cp.get("char_id", ""),
            "char_name": cp.get("char_name", ""),
            "prompt": prompt,
            "negative": cp.get("negative", ""),
            "anchors": cp.get("anchors", []),
            "seed": cp.get("seed"),
            "ref_ids": ref_ids,
            "preview_paths": _resolve_preview_paths(ref_ids),
            "path": None,
        })
        print(f"    👤 Персонаж: {cp.get('char_name', cp.get('char_id', '?'))}")

    # achievement_prompts[] → tasks["badges"]
    for ap in _safe_list(nova, "achievement_prompts"):
        if not isinstance(ap, dict):
            continue
        prompt = ap.get("prompt", "")
        if not prompt:
            continue
        tasks["badges"].append({
            "achievement_id": ap.get("achievement_id", ""),
            "prompt": prompt,
            "style": ap.get("style", "illustrated"),
            "path": None,
        })
        print(f"    🏆 Бейдж: {ap.get('achievement_id', '?')}")

    # interaction_prompts[] → tasks["interaction_assets"]
    for ip in _safe_list(nova, "interaction_prompts"):
        if not isinstance(ip, dict):
            continue
        for el in _safe_list(ip, "elements"):
            if not isinstance(el, dict):
                continue
            prompt = el.get("prompt", "")
            if not prompt:
                continue
            tasks["interaction_assets"].append({
                "interaction_id": ip.get("interaction_id", ""),
                "element_id": el.get("element_id", ""),
                "prompt": prompt,
                "size": el.get("size", "1:1"),
                "states": _safe_dict(ip, "states"),
                "path": None,
            })
        print(f"    🖱️ Интерактив: {ip.get('interaction_id', '?')} ({len(_safe_list(ip, 'elements'))} эл.)")

    # ── РЭЙ: ray_sound ────────────────────────────────────────
    ray = chain.get("ray_sound") or {}
    if not isinstance(ray, dict):
        ray = {}

    # ФОЛЛБЭК: если chain_data пуст — Артур мог скопировать в deliverables
    if not ray or (not _safe_list(ray, "sfx") and not _safe_dict(ray, "music")):
        ray_fb = {
            "sfx": _safe_list(deliverables, "ray_sfx"),
            "music": _safe_dict(deliverables, "ray_music"),
            "voice_over": _safe_dict(deliverables, "ray_voice_over"),
        }
        if any(ray_fb.values()):
            ray = ray_fb
            print("    📋 Рэй: данные из deliverables (fallback от Артура)")

    # sfx[] (только source=generate) → tasks["sfx"]
    for sfx in _safe_list(ray, "sfx"):
        if not isinstance(sfx, dict):
            continue
        if sfx.get("source") == "generate" and sfx.get("prompt"):
            tasks["sfx"].append({
                "id": sfx.get("id", ""),
                "trigger": sfx.get("trigger", ""),
                "prompt": sfx["prompt"],
                "duration": sfx.get("duration", "<1s"),
                "volume": sfx.get("volume", 0.5),
                "path": None,
            })
            print(f"    🔊 SFX (generate): {sfx.get('id', '?')} — {sfx.get('trigger', '')}")

    # music.main_track → tasks["music"]
    music_track = _safe_dict(_safe_dict(ray, "music"), "main_track")
    if music_track.get("suno_prompt"):
        tasks["music"] = {
            "suno_prompt": music_track["suno_prompt"],
            "genre": music_track.get("genre", ""),
            "bpm": music_track.get("tempo_bpm", ""),
            "mood": music_track.get("mood", ""),
            "loop": music_track.get("loop", True),
            "duration": music_track.get("duration", ""),
            "path": None,
        }
        print(f"    🎵 Музыкальный трек: {music_track.get('genre', '?')} {music_track.get('tempo_bpm', '')} BPM")

    # voice_over.characters[] → tasks["voice_over"]
    for vc in _safe_list(_safe_dict(ray, "voice_over"), "characters"):
        if not isinstance(vc, dict):
            continue
        if vc.get("tts_prompt"):
            tasks["voice_over"].append({
                "char_id": vc.get("char_id", ""),
                "tts_prompt": vc["tts_prompt"],
                "sample_line": vc.get("sample_line", ""),
                "voice_description": vc.get("voice_description", ""),
                "path": None,
            })
            print(f"    🗣️ TTS: {vc.get('char_id', '?')}")

    # ── ГЛОБАЛЬНЫЙ РЕЕСТР СИДОВ ───────────────────────────────
    # Собираем seed по char_id из character_prompts — чтобы сцены
    # с тем же персонажем использовали тот же seed → визуальная консистентность.
    _char_seeds: dict[str, int] = {}
    for char in tasks.get("characters", []):
        seed = char.get("seed")
        cid = char.get("char_id", "")
        if seed and cid:
            try:
                _char_seeds[cid] = int(seed)
            except (ValueError, TypeError):
                pass

    # Прокидываем seed в key_frames если персонаж один и seed известен
    for frame in tasks.get("key_frames", []):
        if "seed" not in frame or frame.get("seed") is None:
            ref_ids = frame.get("ref_ids", [])
            if len(ref_ids) == 1 and ref_ids[0] in _char_seeds:
                frame["seed"] = _char_seeds[ref_ids[0]]
                print(f"    🔑 Seed для {frame['scene']}: {frame['seed']} (от {ref_ids[0]})")

    # sound[] из deliverables → audio (старый путь)
    sound_list = deliverables.get("sound", [])
    if sound_list:
        tasks["audio"] = {"tracks": sound_list, "source": "web_story"}

    # text[] → captions
    text_list = deliverables.get("text", [])
    if text_list:
        tasks["captions"] = text_list

    # build_order
    if deliverables.get("build_order"):
        tasks["publication"]["build_order"] = deliverables["build_order"]



def _extract_social_tasks(deliverables: dict, tasks: dict):
    """Парсинг Social Mix v2 pipeline (A12_Клавдия).

    Поддерживает новый формат (deliverables.post + deliverables.images)
    и старый fallback (post_text + image_prompts).
    """
    # ── Новый формат ──────────────────────────────────────────
    post_block  = deliverables.get("post") or {}
    images_list = deliverables.get("images") or []
    meta_block  = deliverables.get("meta") or {}

    # ── Старый fallback ───────────────────────────────────────
    if not post_block and not images_list:
        post_block  = deliverables.get("post_text") or {}
        raw_prompts = deliverables.get("image_prompts") or []
        if not raw_prompts:
            single = deliverables.get("image_prompt", {})
            if isinstance(single, dict) and single.get("positive"):
                raw_prompts = [single]
        gen_paths = deliverables.get("generated_paths") or []
        images_list = []
        for i, ip in enumerate(raw_prompts):
            if not isinstance(ip, dict):
                continue
            saved = gen_paths[i] if i < len(gen_paths) else None
            if saved and not Path(saved).exists():
                saved = None
            images_list.append({
                "path":         saved,
                "prompt":       ip.get("positive", ""),
                "format":       ip.get("format", "4:5"),
                "quality_score": None,
                "typography":   "",
            })

    # ── Нормализация images ───────────────────────────────────
    images = []
    for i, img in enumerate(images_list):
        if not isinstance(img, dict):
            continue
        saved = img.get("path")
        if saved and not Path(saved).exists():
            saved = None
        images.append({
            "index":         i,
            "path":          saved,
            "prompt":        img.get("prompt", ""),
            "format":        img.get("format", "4:5"),
            "quality_score": img.get("quality_score"),
            "typography":    img.get("typography", ""),
        })

    tasks["social_post"] = {
        "images":        images,
        "hook":          post_block.get("hook", ""),
        "body":          post_block.get("body", ""),
        "cta":           post_block.get("cta", ""),
        "hashtags":      post_block.get("hashtags", deliverables.get("hashtags", [])),
        "first_comment": post_block.get("first_comment", deliverables.get("first_comment", "")),
        "platform":      post_block.get("platform", deliverables.get("platform", "instagram")),
        "post_type":     post_block.get("post_type", deliverables.get("post_type",
                             "single" if len(images) <= 1 else "carousel")),
        "viral_score":   meta_block.get("viral_score"),
        "project_id":    meta_block.get("project_id", deliverables.get("meta", {}).get("project_id", "")),
    }

    ready = sum(1 for img in images if img["path"])
    sp = tasks["social_post"]
    print(f"    📱 Social post v2: {len(images)} картинок ({ready} готово), "
          f"тип={sp['post_type']}, платформа={sp['platform']}")


# ============================================================
# ГЕНЕРАЦИЯ ПАКЕТА
# ============================================================

def generate_all(tasks: dict, format: str = DEFAULT_FORMAT, skip_video: bool = True,
                 max_workers: int = 3, batch_pause: float = 2.0) -> dict:
    """
    max_workers  — параллельных запросов к fal.ai одновременно (дефолт 3)
    batch_pause  — пауза в секундах между батчами (дефолт 2с)
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    project_id = tasks["project_id"]
    project_dir = OUTPUT_DIR / project_id
    project_dir.mkdir(parents=True, exist_ok=True)

    model = MODELS[ACTIVE_MODEL]
    print(f"\n{'='*50}")
    print(f"🚀 ГЕНЕРАЦИЯ: {project_id} [{model['label']}]")
    print(f"   Параллельность: {max_workers} | Пауза: {batch_pause}с")
    print(f"{'='*50}")

    def _run_one(fn, *args, **kwargs):
        """Враппер для ThreadPoolExecutor с автоповтором при 429."""
        for attempt in range(3):
            try:
                return fn(*args, **kwargs)
            except Exception as e:
                if "429" in str(e) or "rate" in str(e).lower():
                    wait = (attempt + 1) * 10
                    print(f"  ⏳ Rate limit — жду {wait}с (попытка {attempt+1}/3)")
                    time.sleep(wait)
                else:
                    raise
        raise RuntimeError(f"Превышено число попыток для {fn.__name__}")

    def _submit_batch(items, gen_fn_builder, out_dir=project_dir):
        """
        Запускает items батчами по max_workers.
        gen_fn_builder(item) → (fn, args, kwargs, final_path_key)
        """
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = {}
            for item in items:
                fn, args, kwargs, dest = gen_fn_builder(item, out_dir)
                f = pool.submit(_run_one, fn, *args, **kwargs)
                futures[f] = (item, dest)

            for f in as_completed(futures):
                item, dest = futures[f]
                try:
                    src_path = f.result()
                    Path(src_path).replace(dest)
                    item["path"] = str(dest)
                except Exception as e:
                    print(f"  ❌ Ошибка генерации: {e}")
                    item["path"] = None

        time.sleep(batch_pause)

    # ── ОБЛОЖКИ ───────────────────────────────────────────────
    def _thumb_builder(thumb, out_dir):
        filename = f"thumb_{thumb['variant']}.png"
        dest = out_dir / filename
        fmt = thumb.get("format", format)
        ref_ids = thumb.get("ref_ids", [])
        if ref_ids:
            return generate_with_refs, [thumb["prompt"]], {"ref_ids": ref_ids, "format": fmt, "filename": filename}, dest
        return generate_image, [thumb["prompt"]], {"format": fmt, "filename": filename}, dest

    _submit_batch(tasks["thumbnails"], _thumb_builder)

    # ── СЦЕНЫ (key_frames) ────────────────────────────────────
    def _frame_builder(frame, out_dir):
        purpose = re.sub(r'[^\w\-]', '_', frame.get("purpose", ""))[:30]
        filename = f"frame_{frame['index']}_{purpose}.png"
        dest = out_dir / filename
        fmt = frame.get("format", format)
        ref_ids = frame.get("ref_ids", [])
        seed = frame.get("seed")
        if ref_ids:
            return generate_with_refs, [frame["prompt"]], {"ref_ids": ref_ids, "format": fmt, "filename": filename, "seed": seed}, dest
        return generate_image, [frame["prompt"]], {"format": fmt, "filename": filename, "seed": seed}, dest

    _submit_batch(tasks["key_frames"], _frame_builder)

    # ── ПЕРСОНАЖИ ─────────────────────────────────────────────
    char_dir = project_dir / "characters"
    char_dir.mkdir(exist_ok=True)

    def _char_builder(char, _out_dir):
        char_id = re.sub(r'[^\w\-]', '_', char.get("char_id", "char"))
        filename = f"char_{char_id}.png"
        dest = char_dir / filename
        seed = char.get("seed")
        try:
            seed = int(seed) if seed else None
        except (ValueError, TypeError):
            seed = None
        ref_ids = char.get("ref_ids", [])
        if ref_ids:
            return generate_with_refs, [char["prompt"]], {"ref_ids": ref_ids, "format": "1:1", "filename": filename, "seed": seed}, dest
        return generate_image, [char["prompt"]], {"format": "1:1", "filename": filename, "seed": seed}, dest

    _submit_batch(tasks.get("characters", []), _char_builder)

    # ── БЕЙДЖИ ────────────────────────────────────────────────
    badge_dir = project_dir / "badges"
    badge_dir.mkdir(exist_ok=True)

    def _badge_builder(badge, _out_dir):
        ach_id = re.sub(r'[^\w\-]', '_', badge.get("achievement_id", "badge"))
        filename = f"badge_{ach_id}.png"
        dest = badge_dir / filename
        return generate_image, [badge["prompt"]], {"format": "1:1", "filename": filename}, dest

    _submit_batch(tasks.get("badges", []), _badge_builder)

    # ── UI / ИНТЕРАКТИВ ───────────────────────────────────────
    ui_dir = project_dir / "ui"
    ui_dir.mkdir(exist_ok=True)

    def _ui_builder(ia, _out_dir):
        int_id = re.sub(r'[^\w\-]', '_', ia.get("interaction_id", "ia"))
        el_id  = re.sub(r'[^\w\-]', '_', ia.get("element_id",  "el"))
        filename = f"ui_{int_id}_{el_id}.png"
        dest = ui_dir / filename
        size = ia.get("size", "1:1")
        fmt = size if size in IMAGE_FORMATS else "1:1"
        return generate_image, [ia["prompt"]], {"format": fmt, "filename": filename}, dest

    _submit_batch(tasks.get("interaction_assets", []), _ui_builder)

    if skip_video:
        print(f"\n⏭️ Видео: {len(tasks['videos'])} — ручной режим")

    manifest_path = project_dir / "manifest.json"
    manifest_path.write_text(json.dumps(tasks, ensure_ascii=False, indent=2), encoding="utf-8")

    return tasks


def process_md_file(md_path: str, format: str = DEFAULT_FORMAT, skip_video: bool = True) -> dict:
    data = parse_final_md(md_path)
    tasks = extract_tasks(data)
    return generate_all(tasks, format=format, skip_video=skip_video)
