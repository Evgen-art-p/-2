"""
ПАТЧ: убрать тёмный фон у зон, оставить только обводку и текст темнее.
"""
import re

def patch_file(path, pattern, replacement, label):
    with open(path, encoding="utf-8") as f:
        content = f.read()
    new_content, count = re.subn(pattern, replacement, content, flags=re.DOTALL)
    if count:
        with open(path, "w", encoding="utf-8") as f:
            f.write(new_content)
        print(f"[OK] {path}: {label}")
    else:
        print(f"[SKIP] {path}: паттерн не найден")

# ── ui_cabinet.py: zone_bg убираем (transparent) ───────────────────────
UI_FILE = "studio/cabinet/ui_cabinet.py"

UI_PATTERN = r'zone_color\s*=\s*"[^"]+"\s*\r?\n\s*zone_bg\s*=\s*"[^"]+"\s*\r?\n\s*zone_text\s*=\s*"[^"]+"'

UI_REPLACEMENT = (
    'zone_color = "rgba(0,140,160,0.9)"\n'
    '            zone_bg = "transparent"\n'
    '            zone_text = "rgba(160,220,230,0.95)"'
)

patch_file(UI_FILE, UI_PATTERN, UI_REPLACEMENT, "zone_bg → transparent")

print("Готово. Перезапусти студию.")
