"""
patch_vision_collect.py
Студия «Шесть Пальцев» · Спринт 39

Что делает:
  Патчит studio/workshop/utils.py — функцию _collect_images_for_vision.

Проблема:
  hooks.py кладёт пути картинок в state["vision_images"] (список путей к PNG).
  Но _collect_images_for_vision читает только state["uploaded_files"].
  Значит картинки от хуков (A06 self-review, A11 Федя) не попадают в vision API.

Исправление:
  Добавляем в начало _collect_images_for_vision чтение state["vision_images"].
  Если там есть пути к файлам — кодируем в base64 и добавляем в список.
  uploaded_files по-прежнему тоже обрабатываются (обратная совместимость).

Запуск: python patch_vision_collect.py
  из корня проекта (C:\\Users\\Евгений\\Desktop\\студия 2)
"""

import shutil
from pathlib import Path

TARGET = Path("studio/workshop/utils.py")
BACKUP = TARGET.with_suffix(".py.bak_pre_vision")

OLD = '''def _collect_images_for_vision(state) -> list:
    """Собирает base64 изображений из загруженных файлов для vision API"""
    images = []
    if not state.get("uploaded_files") or not state.get("file_processor"):
        return images'''

NEW = '''def _collect_images_for_vision(state) -> list:
    """Собирает base64 изображений для vision API.

    Два источника:
      1. state["vision_images"] — пути от hooks.py (A06 self-review, A11 Федя и др.)
      2. state["uploaded_files"] — файлы загруженные Шефом вручную через UI
    """
    import base64 as _b64
    import mimetypes as _mt

    images = []

    # ── Источник 1: hooks.py → state["vision_images"] ────────────────
    # Хук кладёт список путей к PNG после генерации картинки.
    # Pipeline видит их и передаёт агенту через chat_with_images.
    hook_images = state.get("vision_images", [])
    if hook_images:
        for item in hook_images:
            # Поддерживаем два формата:
            # - строка (путь к файлу)
            # - dict {"base64": ..., "mime_type": ..., "name": ...}
            if isinstance(item, dict) and item.get("base64"):
                images.append(item)
                print(f"[VISION] Хук-изображение (dict): {item.get('name', '?')}")
            elif isinstance(item, str):
                fp = Path(item)
                if fp.exists():
                    try:
                        b64 = _b64.b64encode(fp.read_bytes()).decode("utf-8")
                        mime = _mt.guess_type(str(fp))[0] or "image/png"
                        images.append({
                            "base64":    b64,
                            "mime_type": mime,
                            "name":      fp.name,
                        })
                        print(f"[VISION] Хук-изображение: {fp.name} ({len(b64)//1024}KB)")
                    except Exception as ex:
                        print(f"[VISION ERROR] hooks image {item}: {ex}")
                else:
                    print(f"[VISION] ⚠️ Хук-изображение не найдено: {item}")

    # ── Источник 2: uploaded_files (загружены Шефом) ─────────────────
    if not state.get("uploaded_files") or not state.get("file_processor"):
        return images'''


def main():
    if not TARGET.exists():
        print(f"❌ Файл не найден: {TARGET}")
        return

    shutil.copy2(TARGET, BACKUP)
    print(f"✅ Бэкап: {BACKUP}")

    text = TARGET.read_text(encoding="utf-8")

    if OLD in text:
        text = text.replace(OLD, NEW)
        print("✅ Патч применён: _collect_images_for_vision обновлена")
    else:
        print("⚠️  Строка не найдена — возможно уже пропатчено или текст изменился")
        return

    TARGET.write_text(text, encoding="utf-8")

    # Синтаксис-чек
    import subprocess
    r = subprocess.run(
        ["python", "-m", "py_compile", str(TARGET)],
        capture_output=True, text=True
    )
    if r.returncode == 0:
        print("✅ Синтаксис OK")
    else:
        print(f"❌ Синтаксис ошибка:\n{r.stderr}")
        print("⏪ Откатываю...")
        shutil.copy2(BACKUP, TARGET)
        print("✅ Откат выполнен")


if __name__ == "__main__":
    main()
