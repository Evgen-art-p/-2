"""
ПАТЧ: Тёмнее подписи локаций и обводка на карте Грондхейма

Меняет два места:
1. studio/cabinet/css.py — класс .cab-map-sector (цвет текста + обводка)
2. studio/cabinet/ui_cabinet.py — инлайн zone_color и zone_text

Запуск: python patch_map_sector_colors.py
"""

# ──────────────────────────────────────────────────
# 1. css.py — .cab-map-sector
# ──────────────────────────────────────────────────
CSS_FILE = "studio/cabinet/css.py"

OLD_SECTOR = """.cab-map-sector {
  position: absolute; border-radius: 8px;
  border: 2px solid rgba(0,242,255,0.55);
  font-family: 'JetBrains Mono', monospace;
  letter-spacing: 0.1em; text-transform: uppercase;
  padding: 8px 14px;
  pointer-events: none;
  background: transparent;
  color: rgba(0,242,255,0.95);
  text-shadow: 0 0 8px rgba(0,242,255,0.6);
}"""

NEW_SECTOR = """.cab-map-sector {
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

with open(CSS_FILE, encoding="utf-8") as f:
    css = f.read()

if OLD_SECTOR in css:
    css = css.replace(OLD_SECTOR, NEW_SECTOR)
    with open(CSS_FILE, "w", encoding="utf-8") as f:
        f.write(css)
    print(f"[OK] {CSS_FILE}: .cab-map-sector обновлён")
else:
    print(f"[SKIP] {CSS_FILE}: блок не найден — уже пропатчен?")


# ──────────────────────────────────────────────────
# 2. ui_cabinet.py — zone_color и zone_text
# ──────────────────────────────────────────────────
UI_FILE = "studio/cabinet/ui_cabinet.py"

OLD_ZONE = '''            # Нейтральный цвет для всех зон (пока без индивидуальных цветов)
            zone_color = "rgba(180,200,220,0.25)"
            zone_bg = "rgba(180,200,220,0.04)"
            zone_text = "rgba(180,200,220,0.6)"'''

NEW_ZONE = '''            # Нейтральный цвет для всех зон (пока без индивидуальных цветов)
            zone_color = "rgba(0,140,160,0.9)"
            zone_bg = "rgba(180,200,220,0.04)"
            zone_text = "rgba(160,220,230,0.95)"'''

with open(UI_FILE, encoding="utf-8") as f:
    ui = f.read()

if OLD_ZONE in ui:
    ui = ui.replace(OLD_ZONE, NEW_ZONE)
    with open(UI_FILE, "w", encoding="utf-8") as f:
        f.write(ui)
    print(f"[OK] {UI_FILE}: zone_color и zone_text обновлены")
else:
    print(f"[SKIP] {UI_FILE}: блок не найден — уже пропатчен?")

print("Готово. Перезапусти студию.")
