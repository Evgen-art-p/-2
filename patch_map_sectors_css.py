#!/usr/bin/env python3
"""
patch_map_sectors_css.py
Делает подписи локаций на карте читаемыми — без фона.
"""

import shutil
from pathlib import Path
from datetime import datetime

CSS_PATH = Path("studio/cabinet/css.py")

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
    if not CSS_PATH.exists():
        raise FileNotFoundError(f"Не найден: {CSS_PATH}")

    src = CSS_PATH.read_text(encoding="utf-8")

    if OLD not in src:
        print("⚠️  Якорь не найден — возможно уже применён или структура изменилась")
        return

    bak = CSS_PATH.with_suffix(f".py.bak_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    shutil.copy2(CSS_PATH, bak)
    print(f"[BACKUP] {bak.name}")

    src = src.replace(OLD, NEW, 1)
    CSS_PATH.write_text(src, encoding="utf-8")
    print("✅ Готово. Перезапусти студию.")


if __name__ == "__main__":
    apply()
