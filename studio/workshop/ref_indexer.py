# studio/workshop/ref_indexer.py
# Авто-индексация загруженных рефов:
#   1. Конвертация → PNG
#   2. Vision AI анализирует картинку
#   3. Запись в assets_catalog.json
#   4. Сброс кеша каталога

import io
import json
import re
import base64
from pathlib import Path

try:
    from PIL import Image as _PIL
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

from studio.llm import chat_with_images
from studio.workshop.assets import _load_asset_catalog

CATALOG_PATH = Path("assets_catalog.json")
# from studio.config import BASE_DIR
# CATALOG_PATH = BASE_DIR / "assets_catalog.json"

VISION_PROMPT = """Ты анализируешь изображение-референс для студии видеоконтента.
Стиль студии: Stylized 3D Realism (Pixar-like).

Ответь СТРОГО в формате JSON, без лишнего текста:
{
  "name": "Имя персонажа или название объекта/локации (кратко)",
  "category": "character | location | prop | background",
  "visual_anchor": "Ключевые визуальные детали для воспроизведения: одежда, цвета, поза, особенности",
  "tags": ["тег1", "тег2", "тег3"],
  "mood": ["настроение1", "настроение2"],
  "colors": ["цвет1", "цвет2", "цвет3"]
}"""


# ─── Конвертация в PNG ──────────────────────────────────
def convert_to_png(filepath: Path) -> Path:
    if not HAS_PIL or filepath.suffix.lower() == ".png":
        return filepath
    try:
        img = _PIL.open(filepath)
        if img.mode not in ("RGBA", "RGB"):
            img = img.convert("RGBA")
        out = filepath.with_suffix(".png")
        buf = io.BytesIO()
        img.save(buf, format="PNG", optimize=True)
        out.write_bytes(buf.getvalue())
        filepath.unlink(missing_ok=True)
        print(f"[REF_INDEXER] {filepath.name} → {out.name}")
        return out
    except Exception as e:
        print(f"[REF_INDEXER] convert error: {e}")
        return filepath


# ─── Vision-анализ ──────────────────────────────────────
def _analyze_image(filepath: Path) -> dict:
    """Отправляет картинку в LLM, получает метаданные."""
    try:
        b64 = base64.b64encode(filepath.read_bytes()).decode()
        result = chat_with_images(
            VISION_PROMPT,
            "Проанализируй этот референс и верни JSON.",
            images=[{"base64": b64, "media_type": "image/png"}],
        )
        # Вырезаем JSON из ответа
        match = re.search(r'\{.*\}', result, re.DOTALL)
        if match:
            return json.loads(match.group())
    except Exception as e:
        print(f"[REF_INDEXER] vision error: {e}")

    # Фоллбэк — минимальные данные из имени файла
    stem = filepath.stem
    return {
        "name": stem.replace("_", " ").replace("-", " ").title(),
        "category": "character",
        "visual_anchor": "",
        "tags": ["ref", "uploaded"],
        "mood": [],
        "colors": [],
    }


GLOBAL_ASSETS = Path("assets")  # глобальная папка рефов студии


# ─── Копирование в глобальный assets/ ───────────────────
def _ensure_in_global_assets(filepath: Path) -> Path:
    """Если файл лежит в runs/ — копируем в глобальный assets/."""
    GLOBAL_ASSETS.mkdir(parents=True, exist_ok=True)
    dest = GLOBAL_ASSETS / filepath.name
    if filepath.resolve() != dest.resolve():
        import shutil
        shutil.copy2(filepath, dest)
        print(f"[REF_INDEXER] Скопирован в assets/: {filepath.name}")
    return dest


# ─── Запись в каталог ────────────────────────────────────
def index_asset(filepath: Path) -> str | None:
    filepath = _ensure_in_global_assets(filepath)  # всегда в глобальный assets/
    try:
        if CATALOG_PATH.exists():
            data = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
        else:
            data = {"version": "1.1", "studio": "Six Fingers",
                    "visual_code": "", "total_assets": 0, "assets": []}

        assets = data.get("assets", []) if isinstance(data, dict) else data

        # Уже есть?
        if any(a.get("filename") == filepath.name for a in assets):
            print(f"[REF_INDEXER] {filepath.name} уже в каталоге")
            return None

        # Vision-анализ
        meta = _analyze_image(filepath)

        # Генерируем ID
        slug = re.sub(r"[^a-z0-9_]", "_", filepath.stem.lower()).strip("_")
        prefix = {"character": "char", "location": "loc",
                  "prop": "prop", "background": "bg"}.get(meta.get("category", ""), "ref")
        asset_id = f"{prefix}_{slug}"
        if any(a.get("id") == asset_id for a in assets):
            asset_id += "_2"

        assets.append({
            "id":            asset_id,
            "name":          meta.get("name", filepath.stem),
            "filename":      filepath.name,
            "category":      meta.get("category", "character"),
            "tags":          meta.get("tags", []),
            "style":         "stylized 3D realism",
            "background":    "transparent",
            "visual_anchor": meta.get("visual_anchor", ""),
            "description":   meta.get("visual_anchor", ""),
            "use_cases":     [],
            "mood":          meta.get("mood", []),
            "colors":        meta.get("colors", []),
        })

        if isinstance(data, dict):
            data["assets"] = assets
            data["total_assets"] = len(assets)
        else:
            data = assets

        CATALOG_PATH.write_text(
            json.dumps(data, ensure_ascii=False, indent=4), encoding="utf-8"
        )
        _load_asset_catalog(force_reload=True)

        print(f"[REF_INDEXER] ✅ {filepath.name} → [{asset_id}] | {meta.get('name')}")
        return asset_id

    except Exception as e:
        print(f"[REF_INDEXER] catalog error: {e}")
        return None
