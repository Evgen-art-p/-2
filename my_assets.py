#!/usr/bin/env python3
"""
Six Fingers — Генератор списка ассетов
Создаёт файл МОИ_АССЕТЫ.txt рядом с собой.
Запусти: python my_assets.py
"""

import json
import os
from collections import defaultdict
from datetime import datetime

# --- Пути ---
script_dir = os.path.dirname(os.path.abspath(__file__))
output_path = os.path.join(script_dir, "МОИ_АССЕТЫ.txt")

# --- Ищем файл каталога (txt или json) ---
catalog_path = None
for name in ["assets_catalog.txt", "assets_catalog.json"]:
    path = os.path.join(script_dir, name)
    if os.path.exists(path):
        catalog_path = path
        break

if not catalog_path:
    print("Ошибка! Не найден файл assets_catalog.txt или assets_catalog.json")
    print(f"Положи его сюда: {script_dir}")
    input("Нажми Enter...")
    exit(1)

# --- Читаем каталог ---
try:
    with open(catalog_path, "r", encoding="utf-8") as f:
        data = json.load(f)
except json.JSONDecodeError as e:
    print(f"Ошибка в JSON: {e}")
    input("Нажми Enter...")
    exit(1)

assets = data["assets"]
groups = defaultdict(list)
for a in assets:
    groups[a.get("category", "?")].append(a)

labels = {
    "character": "ПЕРСОНАЖИ",
    "location":  "ЛОКАЦИИ",
    "prop":      "РЕКВИЗИТ",
}

# --- Формируем текст ---
lines = []
lines.append("=" * 60)
lines.append(f"  СТУДИЯ: {data.get('studio', '?')}")
lines.append(f"  СТИЛЬ:  {data.get('visual_code', '?')}")
lines.append(f"  ВСЕГО:  {len(assets)} ассетов")
lines.append(f"  ДАТА:   {datetime.now().strftime('%d.%m.%Y %H:%M')}")
lines.append(f"  ИСТОЧНИК: {os.path.basename(catalog_path)}")
lines.append("=" * 60)

n = 1
for cat in ["character", "location", "prop"]:
    if cat not in groups:
        continue
    items = sorted(groups[cat], key=lambda x: x["name"].lower())
    label = labels.get(cat, cat.upper())

    lines.append("")
    lines.append(f"  {label} — {len(items)} шт.")
    lines.append("  " + "-" * 50)

    for a in items:
        bg = a.get("background", "?")
        fname = a.get("filename", "?")
        lines.append(f"  {n:3d}. {a['name']}")
        lines.append(f"       файл: {fname}")
        lines.append(f"       фон: {bg}")
        n += 1

lines.append("")
lines.append("=" * 60)
lines.append(f"  ИТОГО: {len(assets)} ассетов")

# Подсчёт по категориям
for cat in ["character", "location", "prop"]:
    if cat in groups:
        lines.append(f"    {labels.get(cat, cat)}: {len(groups[cat])}")

lines.append("=" * 60)

# --- Записываем файл ---
with open(output_path, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print(f"Готово! Файл: {output_path}")
print(f"Найдено: {len(assets)} ассетов из {os.path.basename(catalog_path)}")
input("Нажми Enter чтобы закрыть...")