"""
ПАТЧ: Тёмнее подписи локаций и обводка на карте Грондхейма
Работает с Windows CRLF и Unix LF одинаково.

Запуск: python patch_map_sector_colors.py
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
        print(f"[SKIP] {path}: паттерн не найден — уже пропатчен?")

# ── 1. css.py: заменяем блок .cab-map-sector ──────────────────────────────
CSS_FILE = "studio/cabinet/css.py"

CSS_PATTERN = r'(/\* Сектора \*/\s*)\.cab-map-sector \{[^}]+\}'

CSS_REPLACEMENT = r"""\1.cab-map-sector {
  position: absolute; border-radius: 8px;
  border: 2px solid rgba(0,140,160,0.9);
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.75rem; font-weight: 700;
  letter-spacing: 0.1em; text-transform: uppercase;
  padding: 8px 14px;
  pointer-events: none;
  background: transparent;
  color: rgba(160,220,230,0.95);
  text-shadow: 0 1px 4px rgba(0,0,0,0.95);
}"""

patch_file(CSS_FILE, CSS_PATTERN, CSS_REPLACEMENT, ".cab-map-sector обновлён")

# ── 2. ui_cabinet.py: zone_color и zone_text ──────────────────────────────
UI_FILE = "studio/cabinet/ui_cabinet.py"

UI_PATTERN = r'zone_color\s*=\s*"rgba\(180,200,220,0\.25\)"(\s*)zone_bg\s*=\s*"rgba\(180,200,220,0\.04\)"(\s*)zone_text\s*=\s*"rgba\(180,200,220,0\.6\)"'

UI_REPLACEMENT = r'zone_color = "rgba(0,140,160,0.9)"\1zone_bg = "rgba(180,200,220,0.04)"\2zone_text = "rgba(160,220,230,0.95)"'

patch_file(UI_FILE, UI_PATTERN, UI_REPLACEMENT, "zone_color и zone_text обновлены")

print("Готово. Перезапусти студию.")
