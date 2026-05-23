#!/usr/bin/env python3
"""
fix_async_indent.py — Исправляет отступы после patch_async_scoring
Запуск из корня проекта: python fix_async_indent.py
"""
import shutil, datetime
from pathlib import Path

ROOT = Path(".")

for rel in ("studio/workshop/pipeline.py", "studio/pipeline.py"):
    path = ROOT / rel
    if not path.exists():
        continue

    text = path.read_text(encoding="utf-8")

    # Ищем сломанный паттерн и заменяем правильным
    old = (
        '                if not state.get("async_scoring", False):  # patch_async_scoring\n'
        '            _ministry.record_outcome(\n'
        '                    agent_id=worker_id,\n'
        '                    slot_id=_slot_id,\n'
        '                    score=7.0,  # базовая оценка, QA уточнит позже\n'
        '                    cost_usd=_wcost,\n'
        '                )'
    )
    new = (
        '                if not state.get("async_scoring", False):  # patch_async_scoring\n'
        '                    _ministry.record_outcome(\n'
        '                        agent_id=worker_id,\n'
        '                        slot_id=_slot_id,\n'
        '                        score=7.0,  # базовая оценка, QA уточнит позже\n'
        '                        cost_usd=_wcost,\n'
        '                    )'
    )

    if old not in text:
        print(f"[{rel}] Паттерн не найден — возможно уже исправлен или отступы отличаются.")
        print("Исправь вручную: сдвинь _ministry.record_outcome и его аргументы на 4 пробела вправо,")
        print("чтобы они оказались внутри блока if not state.get('async_scoring', False):")
        print()
        print('                if not state.get("async_scoring", False):')
        print('                    _ministry.record_outcome(')
        print('                        agent_id=worker_id,')
        print('                        slot_id=_slot_id,')
        print('                        score=7.0,')
        print('                        cost_usd=_wcost,')
        print('                    )')
        continue

    bak = path.with_suffix(f".bak_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}")
    shutil.copy2(path, bak)
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    print(f"[{rel}] ✅ Отступы исправлены. Бэкап: {bak.name}")
    break
