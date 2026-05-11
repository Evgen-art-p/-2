#!/usr/bin/env python3
"""
fix_field_tracker.py
Добавляет Этап 8 (field_tracker) в cartridge.py.
Запускать из корня проекта если apply_sprint15_patch.py
пропустил [cartridge/field_tracker_stage8].
"""

from pathlib import Path
import shutil
from datetime import datetime

CARTRIDGE = Path("studio") / "cartridge.py"

text = CARTRIDGE.read_text(encoding="utf-8")

FIELD_TRACKER_BLOCK = (
    "\n"
    "        # ══ Этап 8: Culture Formation ══\n"
    "        try:\n"
    "            from studio.culture.field_tracker import CulturalFieldTracker\n"
    "            CulturalFieldTracker().update_slot_field(self.slot_id)\n"
    "            print(f\"[CULTURE] ✅ field_tracker обновлён для {self.slot_id}\")\n"
    "        except Exception as e:\n"
    "            print(f\"[CULTURE] Ошибка field_tracker: {e}\")\n"
)

# Уже применён?
if "CulturalFieldTracker" in text:
    print("✅ field_tracker уже подключён — ничего не делаю.")
    exit(0)

# Ищем место вставки — перед run_turbo
ANCHORS = [
    "    async def run_turbo(self):",  # LF
    "    async def run_turbo(self):\r",  # CRLF
]

inserted = False
for anchor in ANCHORS:
    if anchor in text:
        bak = CARTRIDGE.with_suffix(".py.bak_fieldtracker_" + datetime.now().strftime("%H%M%S"))
        shutil.copy2(CARTRIDGE, bak)
        print(f"💾 Бэкап → {bak.name}")
        text = text.replace(anchor, FIELD_TRACKER_BLOCK + anchor, 1)
        CARTRIDGE.write_text(text, encoding="utf-8")
        print("✅ [cartridge/field_tracker_stage8] Применён")
        inserted = True
        break

if not inserted:
    print("⚠️  Якорь run_turbo не найден. Добавь вручную в cartridge.py:")
    print(FIELD_TRACKER_BLOCK)
