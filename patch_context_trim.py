#!/usr/bin/env python3
"""
patch_context_trim.py — обрезаем контекст агентов

ПРОБЛЕМА:
  К A03 в контекст летит: Грондхейм (душа) + Гавань (RAG) + каталог ассетов
  (111 ассетов!) + результаты A01 (800 симв) + результаты A02 (800 симв)
  + бриф + настройки + память клиента + стратегии + культура = ~15-20к токенов.
  
  Gemini Flash зависает или очень долго думает с таким контекстом.
  OpenRouter держит соединение открытым → requests висит 10+ минут.

ПРАВКИ:
  1. pipeline.py — каталог ассетов в контекст агента ТОЛЬКО если агент
     работает с визуалом (A06, A08, A11 в social_mix). Остальным не нужно
     знать 111 ассетов чтобы написать сценарий.
  
  2. pipeline.py — previous_output обрезаем до 400 символов на агента
     (сейчас 800). Цепочка растёт линейно — к A12 это 9600 символов только
     от предыдущих агентов.
  
  3. config.py — HTTP_TIMEOUT с 120 до 90 секунд. Если OpenRouter не ответил
     за 90 сек — это зависание, ретраим быстро а не ждём 2 минуты.
"""

import sys
import shutil
import py_compile
import tempfile
from pathlib import Path
from datetime import datetime

DRY_RUN = "--dry-run" in sys.argv
BACKUP_DIR = Path("_patch_backups") / f"context_trim_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

def backup(path: Path):
    if DRY_RUN:
        print(f"  [DRY] backup {path}")
        return
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    dest = BACKUP_DIR / path.name
    shutil.copy2(path, dest)
    print(f"  ✓ backup → {dest}")

def apply(path: Path, old: str, new: str, desc: str) -> bool:
    if not path.exists():
        print(f"  ❌ Файл не найден: {path}")
        return False
    content = path.read_text(encoding="utf-8")
    if old not in content:
        print(f"  ⚠ Не найдено: {desc}")
        return False
    new_content = content.replace(old, new, 1)
    if DRY_RUN:
        print(f"  [DRY] {path.name}: {desc}")
        return True
    backup(path)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8",
                                     suffix=".py", delete=False) as tmp:
        tmp.write(new_content)
        tmp_path = Path(tmp.name)
    try:
        py_compile.compile(str(tmp_path), doraise=True)
    except py_compile.PyCompileError as e:
        tmp_path.unlink()
        print(f"  ❌ Синтакс-ошибка: {e}")
        return False
    shutil.move(str(tmp_path), str(path))
    print(f"  ✓ {path.name}: {desc}")
    return True


# ══════════════════════════════════════════════════════════════════
# ПАТЧ 1: pipeline.py — каталог ассетов только для визуал-агентов
# ══════════════════════════════════════════════════════════════════

CATALOG_OLD = """    # Каталог ассетов
    catalog = _load_asset_catalog()
    if catalog:
        context += f"\\n\\n{catalog}\\n\\n\""""

CATALOG_NEW = """    # Каталог ассетов — только для агентов работающих с визуалом
    # (A06 Эван Вижн, A08 Феликс/Герман, A11 Федя — генерация и ОТК картинок)
    # Остальным 111 ассетов в контексте не нужны — только раздувают токены
    _visual_agents = {"A06", "A08", "A11", "A05"}
    if worker_id in _visual_agents:
        catalog = _load_asset_catalog()
        if catalog:
            context += f"\\n\\n{catalog}\\n\\n\""""

# ══════════════════════════════════════════════════════════════════
# ПАТЧ 2: pipeline.py — previous_output обрезаем до 400 символов
# ══════════════════════════════════════════════════════════════════

PREV_OLD = """    if meta.get("next_input"):
        previous_output += f"\\n\\n--- {label} ({worker_id}) ---\\n{meta['next_input']}"
    else:
        previous_output += f"\\n\\n--- {label} ({worker_id}) ---\\n{human_text[:800]}{chain_json}\""""

PREV_NEW = """    if meta.get("next_input"):
        previous_output += f"\\n\\n--- {label} ({worker_id}) ---\\n{meta['next_input']}"
    else:
        # ПАТЧ context_trim: 400 символов вместо 800
        # К A12 цепочка = 12 агентов × 400 = 4800 симв вместо 9600
        previous_output += f"\\n\\n--- {label} ({worker_id}) ---\\n{human_text[:400]}{chain_json}\""""

# ══════════════════════════════════════════════════════════════════
# ПАТЧ 3: config.py — HTTP_TIMEOUT 90 вместо 120
# ══════════════════════════════════════════════════════════════════

TIMEOUT_OLD = "HTTP_TIMEOUT = 120"
TIMEOUT_NEW = "HTTP_TIMEOUT = 90  # ПАТЧ context_trim: 90 сек вместо 120"


def main():
    print("=" * 55)
    print("ПАТЧ: Обрезаем контекст агентов (меньше токенов)")
    print("=" * 55)
    if DRY_RUN:
        print("РЕЖИМ: DRY-RUN\n")

    pipeline = Path("studio/workshop/pipeline.py")
    config   = Path("studio/config.py")

    print("\n[1/3] pipeline.py — каталог ассетов только визуал-агентам")
    apply(pipeline, CATALOG_OLD, CATALOG_NEW, "каталог только A05/A06/A08/A11")

    print("\n[2/3] pipeline.py — previous_output 400 вместо 800 символов")
    apply(pipeline, PREV_OLD, PREV_NEW, "обрезаем цепочку до 400 симв/агент")

    print("\n[3/3] config.py — HTTP_TIMEOUT 90 сек")
    apply(config, TIMEOUT_OLD, TIMEOUT_NEW, "таймаут 90 сек вместо 120")

    print("\n" + "=" * 55)
    if not DRY_RUN:
        print("✅ Готово!")
        print(f"   Бекапы: {BACKUP_DIR}")
        print()
        print("Что изменилось:")
        print("  • Каталог 111 ассетов — только визуал-агентам (A05/06/08/11)")
        print("  • Цепочка предыдущих результатов: 400 симв/агент (было 800)")
        print("  • Таймаут: 90 сек (было 120) — быстрее детектируем зависание")
        print()
        print("Примерная экономия контекста к A03: ~8-10к токенов")
        print()
        print("Перезапусти: python main.py")
    else:
        print("DRY-RUN завершён.")


if __name__ == "__main__":
    main()
