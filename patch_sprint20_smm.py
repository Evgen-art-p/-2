#!/usr/bin/env python3
"""
patch_sprint20_smm.py — Патч движков по итогам аудита SMM-цеха
Студия «Шесть Пальцев» · 2026 · Спринт 20

Исправления:
  1. studio/cartridge.py
       {"action": "stop"} из hooks.py теперь останавливает пайплайн.
       PLAN-режим social_mix (и любого другого цеха) начнёт работать корректно.

  2. studio/fal_client.py
       Синтаксическая ошибка строка 43: слиплись две строки в одну.
       _current_client_slug инициализировался как Path вместо None.

  3. studio/modules/social_mix/hooks.py
       Модель google/gemini-flash-1.5 (устарела) → google/gemini-2.5-flash.

  4. studio/modules/social_mix/hooks.py
       slot_id FAL-вызовов: было f"social_img_{attempt}" (ministry не копил статистику).
       Стало: единый ключ f"{active_dept}_fal" для всех попыток.

  5. studio/modules/video_long/hooks.py
       Хардкод update_slot_field("video_long") → использует state._slot_id.

Запуск:
  python patch_sprint20_smm.py            # применить патч
  python patch_sprint20_smm.py --dry-run  # проверка без изменений

Бэкапы создаются автоматически рядом с каждым файлом (.bak_YYYYMMDD_HHMMSS).
"""

import sys
import shutil
import datetime
from pathlib import Path

DRY_RUN = "--dry-run" in sys.argv
ROOT    = Path(".")

_applied    = []
_skipped    = []
_not_found  = []
_errors     = []


def _backup(path: Path) -> Path:
    ts  = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = path.with_suffix(f".bak_{ts}")
    shutil.copy2(path, bak)
    return bak


def _patch(rel_path: str, old: str, new: str, description: str, replace_all: bool = False) -> bool:
    """Заменяет old → new в файле. replace_all=True заменяет все вхождения."""
    path = ROOT / rel_path
    if not path.exists():
        print(f"  ⚠️  НЕ НАЙДЕН: {rel_path}")
        _not_found.append(f"{description} ({rel_path})")
        return False

    text = path.read_text(encoding="utf-8")

    count = text.count(old)
    if count == 0:
        print(f"  ℹ️  Уже применён или паттерн не найден: {description}")
        _skipped.append(description)
        return False

    if DRY_RUN:
        print(f"  ✅ [DRY-RUN] Применю ({count} вхожд.): {description}")
        _applied.append(f"[DRY] {description}")
        return True

    bak = _backup(path)
    if replace_all:
        new_text = text.replace(old, new)
    else:
        new_text = text.replace(old, new, 1)
    path.write_text(new_text, encoding="utf-8")
    n_str = f"{count} вхожд." if replace_all and count > 1 else ""
    print(f"  ✅ Применён {n_str}: {description}")
    print(f"     Бэкап: {bak.name}")
    _applied.append(description)
    return True


# ══════════════════════════════════════════════════════════════
print("=" * 62)
print(f"  ПАТЧ sprint20_smm{'  [DRY-RUN]' if DRY_RUN else ''}")
print(f"  {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 62)


# ─────────────────────────────────────────────────────────────
# FIX 1 — cartridge.py: {"action": "stop"} останавливает цикл
# ─────────────────────────────────────────────────────────────
print("\n[1/5] cartridge.py — PLAN-режим и остановка по action=stop")

_patch(
    rel_path="studio/cartridge.py",
    old=(
        '                # ═══ HOOK: on_after_agent ═══\n'
        '                hook_result = self._call_hook("on_after_agent", self.state, worker_id, human_text, meta)\n'
        '                if hook_result and isinstance(hook_result, dict):\n'
        '                    human_text = hook_result.get("human_text", human_text)\n'
        '                    meta = hook_result.get("meta", meta)'
    ),
    new=(
        '                # ═══ HOOK: on_after_agent ═══\n'
        '                hook_result = self._call_hook("on_after_agent", self.state, worker_id, human_text, meta)\n'
        '                if hook_result and isinstance(hook_result, dict):\n'
        '                    if hook_result.get("action") == "stop":  # patch_sprint20_smm\n'
        '                        print(f"[HOOKS] ⏹ Пайплайн остановлен после {worker_id}.")\n'
        '                        await self.callbacks.on_status(\n'
        '                            self.slot_id, f"Стоп после {worker_id}.", "info"\n'
        '                        )\n'
        '                        break\n'
        '                    human_text = hook_result.get("human_text", human_text)\n'
        '                    meta = hook_result.get("meta", meta)'
    ),
    description='cartridge.py: action="stop" останавливает while-loop',
)


# ─────────────────────────────────────────────────────────────
# FIX 2 — fal_client.py: синтаксическая ошибка строка 43
# ─────────────────────────────────────────────────────────────
print("\n[2/5] fal_client.py — исправление слипшихся строк")

_patch(
    rel_path="studio/fal_client.py",
    old='_current_client_slug = NoneCLIENTS_DIR = Path("clients")',
    new='_current_client_slug = None\nCLIENTS_DIR = Path("clients")',
    description='fal_client.py: _current_client_slug=None, CLIENTS_DIR разделены',
)


# ─────────────────────────────────────────────────────────────
# FIX 3 — social_mix/hooks.py: устаревшая модель Gemini
# ─────────────────────────────────────────────────────────────
print("\n[3/5] social_mix/hooks.py — модель Gemini 1.5 → 2.5")

_patch(
    rel_path="studio/modules/social_mix/hooks.py",
    old='model="google/gemini-flash-1.5"',
    new='model="google/gemini-2.5-flash"',
    description='social_mix/hooks.py: QA-модель обновлена до gemini-2.5-flash',
)


# ─────────────────────────────────────────────────────────────
# FIX 4 — social_mix/hooks.py: slot_id FAL (все вхождения)
# ─────────────────────────────────────────────────────────────
print("\n[4/5] social_mix/hooks.py — единый slot_id для FAL-вызовов")

_patch(
    rel_path="studio/modules/social_mix/hooks.py",
    old='slot_id=f"social_img_{attempt}"',
    new="slot_id=f\"{state.get('active_dept', 'social_mix')}_fal\"",
    description='social_mix/hooks.py: slot_id FAL объединён для ministry-статистики',
    replace_all=True,
)


# ─────────────────────────────────────────────────────────────
# FIX 5 — video_long/hooks.py: хардкод в CulturalFieldTracker
# ─────────────────────────────────────────────────────────────
print("\n[5/5] video_long/hooks.py — убираю хардкод slot_id")

_patch(
    rel_path="studio/modules/video_long/hooks.py",
    old='        patterns = tracker.update_slot_field("video_long")',
    new='        patterns = tracker.update_slot_field(state.get("_slot_id", "video_long"))',
    description='video_long/hooks.py: CulturalFieldTracker использует state._slot_id',
)


# ══════════════════════════════════════════════════════════════
# ИТОГ
# ══════════════════════════════════════════════════════════════
print("\n" + "=" * 62)
print("ИТОГ:")
print(f"  ✅ Применено:   {len(_applied)}")
print(f"  ℹ️  Пропущено:   {len(_skipped)}  (уже были применены)")
print(f"  ⚠️  Не найдено:  {len(_not_found)}")

if _not_found:
    print("\n  Не найденные файлы — проверь что запускаешь из корня проекта:")
    for r in _not_found:
        print(f"    - {r}")
    print("\n  Корень проекта — папка где лежит studio/")

if not DRY_RUN and _applied:
    print("\n  💾 Бэкапы созданы рядом с исходниками (.bak_YYYYMMDD_HHMMSS)")

if not DRY_RUN and len(_applied) == 5:
    print("\n  🎉 Все 5 исправлений применены успешно.")
    print("  Теперь PLAN-режим остановится после A04.")
    print("  Если хочешь убедиться без изменений — запусти с --dry-run.")

print("=" * 62)
