#!/usr/bin/env python3
"""
patch_map_sectors_css.py
Делает подписи локаций на карте читаемыми.

Что меняем в CABINET_CSS:
  .cab-map-sector — контрастная рамка + тёмный фон + крупнее шрифт
"""

import shutil
from pathlib import Path
from datetime import datetime

CSS_PATH = Path("studio/cabinet/css.py")
BACKUP_EXT = datetime.now().strftime("%Y%m%d_%H%M%S")


OLD = """.cab-map-sector {
  position: absolute; border-radius: 8px;
  border: 1px solid;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.6rem; font-weight: 500;
  letter-spacing: 0.08em; text-transform: uppercase;
  padding: 10px 14px;
  pointer-events: none;
}"""

NEW = """.cab-map-sector {
  position: absolute; border-radius: 8px;
  border: 2px solid rgba(0,242,255,0.55);
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.75rem; font-weight: 600;
  letter-spacing: 0.1em; text-transform: uppercase;
  padding: 8px 14px;
  pointer-events: none;
  background: transparent;
  color: rgba(0,242,255,0.95);
  text-shadow: 0 0 8px rgba(0,242,255,0.6);
}"""


def apply():
    print("=" * 55)
    print("patch_map_sectors_css.py — читаемые подписи на карте")
    print("=" * 55)

    if not CSS_PATH.exists():
        raise FileNotFoundError(f"Не найден: {CSS_PATH}")

    src = CSS_PATH.read_text(encoding="utf-8")

    if NEW.split("\n")[1] in src:
        print("⚠️  Патч уже применён — пропускаем")
        return

    if OLD not in src:
        raise RuntimeError("Якорь не найден — структура CSS изменилась")

    bak = CSS_PATH.with_suffix(f".py.bak_{BACKUP_EXT}")
    shutil.copy2(CSS_PATH, bak)
    print(f"[BACKUP] {bak.name}")

    src = src.replace(OLD, NEW, 1)
    CSS_PATH.write_text(src, encoding="utf-8")

    # Верификация
    result = CSS_PATH.read_text(encoding="utf-8")
    if "rgba(0,242,255,0.95)" in result:
        print("✅ Патч применён")
        print()
        print("Что изменилось:")
        print("  • Рамка зон: 2px, бирюзовая (0,242,255), 55% прозрачность")
        print("  • Фон зон: тёмный полупрозрачный — подпись не сливается с картой")
        print("  • Шрифт: 0.75rem вместо 0.6rem, weight 600")
        print("  • Цвет текста: бирюза с glow-эффектом")
        print()
        print("Перезапусти студию чтобы увидеть изменения.")
    else:
        print("❌ Что-то пошло не так — проверь вручную")


if __name__ == "__main__":
    apply()
