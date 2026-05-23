#!/usr/bin/env python3
"""
patch_ministry_qa.py — Патч второго блока Ministry в pipeline.py
Студия «Шесть Пальцев» · 2026 · Спринт 20

Закрывает второе место вызова ministry.record_outcome —
блок QA-агента (post-fact, Этапы 6-7).
Первый блок уже пропатчен patch_async_scoring.py.

Запуск: python patch_ministry_qa.py
"""

import shutil, datetime
from pathlib import Path

ROOT = Path(".")


def _backup(path):
    ts  = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = path.with_suffix(f".bak_{ts}")
    shutil.copy2(path, bak)
    return bak


old = (
    '                try:\n'
    '                    _ministry.record_outcome(\n'
    '                        agent_id=_wid,\n'
    '                        slot_id=_ec_slot,\n'
    '                        score=_wscore,\n'
    '                        cost_usd=_wcost,\n'
    '                    )\n'
    '                except Exception as _me:\n'
    '                    print(f"[MINISTRY] record_outcome ошибка: {_me}")'
)

new = (
    '                try:\n'
    '                    if not state.get("async_scoring", False):  # patch_ministry_qa\n'
    '                        _ministry.record_outcome(\n'
    '                            agent_id=_wid,\n'
    '                            slot_id=_ec_slot,\n'
    '                            score=_wscore,\n'
    '                            cost_usd=_wcost,\n'
    '                        )\n'
    '                except Exception as _me:\n'
    '                    print(f"[MINISTRY] record_outcome ошибка: {_me}")'
)

for rel in ("studio/workshop/pipeline.py", "studio/pipeline.py"):
    path = ROOT / rel
    if not path.exists():
        continue

    text = path.read_text(encoding="utf-8")

    if new.split('\n')[1] in text:
        print(f"[{rel}] ℹ️  Уже применён.")
        break

    if old not in text:
        print(f"[{rel}] ⚠️  Паттерн не найден — отступы могут отличаться.")
        print("Найди в pipeline.py блок for _wid, _wdata in _agents_fb.items()")
        print("и внутри try/except оберни _ministry.record_outcome(...):")
        print()
        print('    if not state.get("async_scoring", False):')
        print('        _ministry.record_outcome(...)')
        break

    bak = _backup(path)
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    print(f"[{rel}] ✅ Второй блок ministry пропатчен. Бэкап: {bak.name}")
    break
