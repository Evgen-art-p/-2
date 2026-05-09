#!/usr/bin/env python3
"""
diagnose_ledger.py — диагностика биллинга студии
Запускай из корня проекта: python diagnose_ledger.py
"""

import json
import os
import sys
from pathlib import Path

print("=" * 60)
print("ДИАГНОСТИКА BILLING LEDGER")
print("=" * 60)

# ── 1. Где мы? ──
cwd = Path.cwd()
print(f"\n[1] Текущая директория: {cwd}")

# ── 2. Ищем billing_ledger.jsonl везде ──
print("\n[2] Ищем billing_ledger.jsonl на диске...")
found = list(Path("/").rglob("billing_ledger.jsonl")) if sys.platform != "win32" else \
        list(cwd.rglob("billing_ledger.jsonl"))

if found:
    for f in found:
        size = f.stat().st_size
        print(f"    НАЙДЕН: {f}  ({size} байт)")
else:
    print("    НЕ НАЙДЕН нигде!")

# ── 3. Проверяем BASE_DIR из config ──
print("\n[3] Проверяем studio/config.py...")
try:
    sys.path.insert(0, str(cwd))
    from studio.config import BASE_DIR
    print(f"    BASE_DIR = {BASE_DIR}")
    ledger_path = BASE_DIR / "studio" / "billing_ledger.jsonl"
    print(f"    Ожидаемый путь к леджеру: {ledger_path}")
    print(f"    Файл существует: {ledger_path.exists()}")
    if ledger_path.exists():
        lines = ledger_path.read_text(encoding="utf-8").strip().splitlines()
        print(f"    Строк в файле: {len(lines)}")
        if lines:
            print(f"    Последняя запись: {lines[-1][:120]}...")
        else:
            print("    ФАЙЛ ПУСТОЙ!")
except Exception as e:
    print(f"    ОШИБКА импорта: {e}")

# ── 4. Пробуем вызвать get_economy_data ──
print("\n[4] Вызываем get_economy_data(days=30)...")
try:
    from studio.billing_ledger import get_economy_data, read_ledger
    all_entries = read_ledger()
    print(f"    Всего записей в леджере: {len(all_entries)}")
    
    if all_entries:
        print(f"    Первая запись: {json.dumps(all_entries[0], ensure_ascii=False)[:200]}")
        print(f"    Последняя запись: {json.dumps(all_entries[-1], ensure_ascii=False)[:200]}")
        
        # Проверяем поля
        sample = all_entries[-1]
        print(f"\n    Поля в записи: {list(sample.keys())}")
        has_provider = "provider" in sample
        print(f"    Поле 'provider' есть: {has_provider}")
        if not has_provider:
            print("    ⚠️  ПРОБЛЕМА: поле 'provider' отсутствует в записях!")
            print("       В get_economy_data() используется entry.get('provider', 'openrouter')")
            print("       Т.е. все вызовы будут сваливаться в 'openrouter' — это нормально.")
    
    eco = get_economy_data(days=30)
    print(f"\n    get_economy_data(30): total={eco['total']}, entries обработано: см выше")
    print(f"    by_agent: {eco['by_agent']}")
    print(f"    by_model: {eco['by_model']}")
    print(f"    by_provider: {eco['by_provider']}")

except Exception as e:
    import traceback
    print(f"    ОШИБКА: {e}")
    traceback.print_exc()

# ── 5. Тест записи ──
print("\n[5] Тест записи тестовой строки в леджер...")
try:
    from studio.billing_ledger import record
    entry = record(
        agent_id="TEST_AGENT",
        slot_id="TEST_SLOT",
        model="google/gemini-2.5-flash",
        prompt_tokens=1000,
        completion_tokens=500,
        call_type="diagnostic",
    )
    print(f"    Запись успешна: {json.dumps(entry, ensure_ascii=False)}")
    
    # Читаем снова
    from studio.billing_ledger import read_ledger
    entries_after = read_ledger()
    print(f"    Записей после теста: {len(entries_after)}")
    print(f"    Тестовая запись найдена: {any(e.get('agent_id') == 'TEST_AGENT' for e in entries_after)}")
    
except Exception as e:
    import traceback
    print(f"    ОШИБКА записи: {e}")
    traceback.print_exc()

print("\n" + "=" * 60)
print("ДИАГНОСТИКА ЗАВЕРШЕНА")
print("=" * 60)
