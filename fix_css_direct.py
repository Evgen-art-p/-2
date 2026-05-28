#!/usr/bin/env python3
"""
fix_css_direct.py
Восстанавливает css.py из бэкапа и корректно вставляет стили отчётов.
"""
from pathlib import Path

CSS_PY = Path("studio/cabinet/css.py")

# Ищем последний бэкап
backups = sorted(CSS_PY.parent.glob("css.py.bak*"))
if not backups:
    print("❌ Бэкапов не найдено")
    exit(1)

latest = backups[-1]
print(f"Восстанавливаем из: {latest.name}")

# Читаем оригинал из бэкапа
original = latest.read_text(encoding="utf-8")

# CSS который вставляем ВНУТРЬ строки — только ASCII символы в комментариях
REPORTS_CSS = """
/* === REPORTS TAB === */
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
.rep-details  {
  display: none; margin-top: 7px;
  border-top: 1px solid rgba(255,255,255,0.05);
  padding-top: 6px;
}
.rep-detail-block {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.62rem; line-height: 1.55; margin-top: 4px;
}
.rep-detail-morning   { color: rgba(190,200,225,0.65); }
.rep-detail-revolts   { color: rgba(255,120,80,0.9); }
.rep-detail-resentful { color: rgba(220,100,100,0.8); }
.rep-detail-restless  { color: rgba(210,190,90,0.7); }
.rep-detail-empty {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.68rem;
  color: rgba(180,190,220,0.5);
  text-align: center;
  padding: 8px 0 2px;
}
"""

# Вставляем внутрь строки CABINET_CSS перед последним """
# Находим последнее вхождение закрывающего """
close_marker = '"""\n'
pos = original.rfind(close_marker)

if pos == -1:
    # Попробуем без \n
    close_marker = '"""'
    pos = original.rfind(close_marker)

if pos == -1:
    print("❌ Закрывающий маркер строки не найден")
    print("Первые 200 символов файла:")
    print(repr(original[:200]))
    exit(1)

# Собираем новый файл
new_code = original[:pos] + REPORTS_CSS + original[pos:]

# Проверяем что синтаксис корректный
try:
    compile(new_code, "css.py", "exec")
    print("✅ Синтаксис проверен")
except SyntaxError as e:
    print(f"❌ Синтаксическая ошибка: {e}")
    print("Записываем только оригинал без изменений")
    CSS_PY.write_text(original, encoding="utf-8")
    print("✅ css.py восстановлен из бэкапа (без стилей отчётов)")
    exit(0)

CSS_PY.write_text(new_code, encoding="utf-8")
print("✅ css.py обновлён корректно")
print("Перезапусти студию.")
