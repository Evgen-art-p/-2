#!/usr/bin/env python3
"""
patch_fix_css_insert.py
Исправляет неправильную вставку CSS в css.py.
"""
from pathlib import Path
from datetime import datetime

CSS_PY = Path("studio/cabinet/css.py")
code = CSS_PY.read_text(encoding="utf-8")

backup = CSS_PY.with_suffix(".py.bak_fix_css")
backup.write_text(code, encoding="utf-8")
print(f"Бэкап: {backup.name}")

REPORTS_CSS = """
/* === REPORTS TAB (Sprint 23) === */
.rep-header {
  display: flex; justify-content: space-between; align-items: center;
  padding: 4px 8px 6px;
}
.rep-count {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.58rem;
  color: rgba(180,190,220,0.45);
}
.rep-scroll {
  overflow-y: auto;
  max-height: calc(100vh - 160px);
  scrollbar-width: thin;
}
.rep-card {
  padding: 10px 12px; margin: 4px 6px;
  border-radius: 8px; cursor: pointer;
  transition: opacity 0.15s;
}
.rep-card:hover { opacity: 0.88; }
.rep-card-morning {
  background: rgba(255,180,50,0.04);
  border: 1px solid rgba(255,180,50,0.14);
}
.rep-card-night {
  background: rgba(108,80,200,0.04);
  border: 1px solid rgba(108,80,200,0.18);
}
.rep-card-head {
  display: flex; justify-content: space-between;
  align-items: center; margin-bottom: 5px;
}
.rep-card-title-morning {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.72rem; font-weight: 500;
  color: rgba(255,180,50,0.85);
}
.rep-card-title-night {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.72rem; font-weight: 500;
  color: rgba(160,130,240,0.85);
}
.rep-card-ts {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.56rem;
  color: rgba(160,170,200,0.5);
}
.rep-summary {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.66rem; margin-bottom: 3px;
}
.rep-genius   { color: rgba(255,100,80,0.9); }
.rep-normal   { color: rgba(255,210,90,0.7); }
.rep-safe     { color: rgba(100,190,255,0.7); }
.rep-recovery { color: rgba(160,170,200,0.6); }
.rep-sleep    { color: rgba(160,170,200,0.55); }
.rep-restless { color: rgba(255,210,90,0.7); }
.rep-revolt   { color: rgba(255,100,80,0.95); }
.rep-details  { display: none; margin-top: 7px;
  border-top: 1px solid rgba(255,255,255,0.05);
  padding-top: 6px;
}
.rep-detail-block {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.62rem; line-height: 1.55; margin-top: 4px;
}
.rep-detail-morning  { color: rgba(190,200,225,0.65); }
.rep-detail-revolts  { color: rgba(255,120,80,0.9); }
.rep-detail-resentful{ color: rgba(220,100,100,0.8); }
.rep-detail-restless { color: rgba(210,190,90,0.7); }
.rep-detail-empty {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.68rem;
  color: rgba(180,190,220,0.5);
  text-align: center;
  padding: 8px 0 2px;
}
"""

# Вставляем CSS внутрь строки — перед последним """
ANCHOR = '"""\n'
last_pos = code.rfind(ANCHOR)

if last_pos == -1:
    print("❌ Закрывающий тройной кавычки не найден")
    exit(1)

if "rep-card" in code:
    print("ℹ CSS уже есть — убираем дубль и вставляем заново")
    # Убираем всё что попало за пределы строки
    # Ищем первое вхождение /* === REPORTS TAB вне строки
    outside_marker = '/* === REPORTS TAB'
    outside_pos = code.find(outside_marker)
    if outside_pos != -1 and outside_pos < last_pos:
        # Внутри строки — окей
        print("  CSS внутри строки — пропускаем")
    else:
        # Снаружи — удаляем и вставляем правильно
        code = code[:outside_pos] if outside_pos != -1 else code
        last_pos = code.rfind(ANCHOR)
        insert_pos = last_pos
        code = code[:insert_pos] + REPORTS_CSS + ANCHOR
        CSS_PY.write_text(code, encoding="utf-8")
        print("✅ CSS перенесён внутрь строки")
else:
    # Вставляем перед последним """
    insert_pos = last_pos
    code = code[:insert_pos] + REPORTS_CSS + ANCHOR
    CSS_PY.write_text(code, encoding="utf-8")
    print("✅ CSS добавлен внутрь CABINET_CSS")

print("Перезапусти студию.")
