#!/usr/bin/env python3
"""
patch_async_scoring.py — Патч асинхронной оценки
Студия «Шесть Пальцев» · 2026 · Спринт 20

Что делает:
  1. cartridge.py — читает async_scoring из manifest.json и пишет в state.
     Теперь все агенты знают что ministry вызывать не надо.

  2. pipeline.py — перед вызовом ministry.record_outcome проверяет флаг.
     Если state["async_scoring"] == True — пропускает. Ministry вызовет
     только Metrics Daemon с реальными данными через 24ч.

Запуск:
  python patch_async_scoring.py
  python patch_async_scoring.py --dry-run
"""

import sys
import shutil
import datetime
from pathlib import Path

DRY_RUN = "--dry-run" in sys.argv
ROOT    = Path(".")
_ok, _skip, _miss = [], [], []


def _backup(path):
    ts  = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = path.with_suffix(f".bak_{ts}")
    shutil.copy2(path, bak)
    return bak


def _patch(rel, old, new, desc):
    path = ROOT / rel
    if not path.exists():
        print(f"  ⚠️  НЕ НАЙДЕН: {rel}")
        _miss.append(desc)
        return False
    text = path.read_text(encoding="utf-8")
    if old not in text:
        print(f"  ℹ️  Уже применён: {desc}")
        _skip.append(desc)
        return False
    if DRY_RUN:
        print(f"  ✅ [DRY] {desc}")
        _ok.append(f"[DRY] {desc}")
        return True
    bak = _backup(path)
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    print(f"  ✅ {desc}  (бэкап: {bak.name})")
    _ok.append(desc)
    return True


print("=" * 60)
print(f"  ПАТЧ async_scoring{'  [DRY-RUN]' if DRY_RUN else ''}")
print("=" * 60)


# ──────────────────────────────────────────────────────────
# FIX 1 — cartridge.py: читаем async_scoring из manifest
#
# Ищем место где manifest-свойства пишутся в state.
# Добавляем одну строку рядом с manifest_id.
# ──────────────────────────────────────────────────────────
print("\n[1/2] cartridge.py — async_scoring из manifest → state")

_patch(
    "studio/cartridge.py",
    old='self.state["manifest_id"] = self.manifest.id',
    new=(
        'self.state["manifest_id"]    = self.manifest.id\n'
        '                self.state["async_scoring"] = '
        'self.manifest.data.get("async_scoring", False)  # patch_async_scoring'
    ),
    desc='cartridge.py: state["async_scoring"] = manifest.async_scoring',
)


# ──────────────────────────────────────────────────────────
# FIX 2 — pipeline.py: пропускаем ministry если async_scoring
#
# Ищем вызов ministry.record_outcome в process_agent_result.
# Оборачиваем проверкой флага из state.
#
# Паттерн ищем по сигнатуре ministry.record_outcome —
# если в файле несколько вызовов, заменяем первый (он же единственный
# в блоке QA-агента, остальные в других модулях).
# ──────────────────────────────────────────────────────────
print("\n[2/2] pipeline.py — пропускать ministry если async_scoring=True")

# Пробуем несколько вариантов сигнатуры — в разных версиях pipeline
# строка может выглядеть чуть по-разному
_candidates = [
    # Вариант A: ministry вызывается напрямую
    (
        '        ministry.record_outcome(',
        '        if not state.get("async_scoring", False):  # patch_async_scoring\n'
        '            ministry.record_outcome(',
    ),
    # Вариант B: с отступом 12 пробелов
    (
        '            ministry.record_outcome(',
        '            if not state.get("async_scoring", False):  # patch_async_scoring\n'
        '                ministry.record_outcome(',
    ),
    # Вариант C: через переменную _ministry
    (
        '        _ministry.record_outcome(',
        '        if not state.get("async_scoring", False):  # patch_async_scoring\n'
        '            _ministry.record_outcome(',
    ),
]

patched = False
for old, new in _candidates:
    if _patch("studio/workshop/pipeline.py", old, new,
              f'pipeline.py: ministry.record_outcome пропускается если async_scoring=True'):
        patched = True
        break

if not patched and "pipeline.py" not in str(_miss):
    # Последний вариант — ищем в studio/pipeline.py (другой путь)
    for old, new in _candidates:
        if _patch("studio/pipeline.py", old, new,
                  'pipeline.py (alt path): ministry.record_outcome skip if async_scoring'):
            patched = True
            break

if not patched:
    print("  ⚠️  ministry.record_outcome не найден автоматически.")
    print("     Найди в pipeline.py строку с ministry.record_outcome")
    print("     и добавь перед ней:")
    print('     if not state.get("async_scoring", False):')
    print("         [сдвинь вызов на 4 пробела вправо]")


# ──────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print(f"  ✅ Применено:  {len(_ok)}")
print(f"  ℹ️  Пропущено:  {len(_skip)}")
print(f"  ⚠️  Не найдено: {len(_miss)}")
if not DRY_RUN and _ok:
    print("  💾 Бэкапы созданы рядом с файлами")
print("=" * 60)
