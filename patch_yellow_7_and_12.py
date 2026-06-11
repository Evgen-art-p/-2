#!/usr/bin/env python3
"""
patch_yellow_7_and_12.py
Sprint 44 — Баги №7 и №12

БАГ №7: Обида не гаснет
  Проблема: resentment только растёт (+0.05 ночью), никогда не падает.
  Решение: в _run_decay_for_agent() после созревания добавляем затухание
           resentment для ВСЕХ отношений: ×0.97 за ночь (как emotional_weight).
           Полное исчезновение через ~70 ночей без новых обид.

БАГ №12: «Архитектор» вместо «Шеф» + дубль chronicles.py
  Решение 1: В studio/cabinet/chronicles.py меняем "Архитектор Студии" → "Шеф"
             в промпте к агенту (строки 182, 254) и в комментарии (строка 148).
  Решение 2: Корневой chronicles.py — переименовываем в .removed_duplicate
             (только если md5 совпадает с studio/cabinet/chronicles.py).
"""

import hashlib
import json
import shutil
from pathlib import Path
from datetime import datetime

BACKUP_EXT      = datetime.now().strftime("%Y%m%d_%H%M%S")
NIGHT_PATH      = Path("studio/night_cycle.py")
CHRONICLES_PATH = Path("studio/cabinet/chronicles.py")
ROOT_CHRON_PATH = Path("chronicles.py")


# ─────────────────────────────────────────────────────────────
# УТИЛИТЫ
# ─────────────────────────────────────────────────────────────

def backup(path: Path) -> Path:
    bak = path.with_suffix(f"{path.suffix}.bak_{BACKUP_EXT}")
    shutil.copy2(path, bak)
    print(f"  [BACKUP] {bak.name}")
    return bak


def md5(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


# ─────────────────────────────────────────────────────────────
# ПАТЧ №7 — затухание обиды в night_cycle.py
# ─────────────────────────────────────────────────────────────

# Вставляем блок затухания СРАЗУ ПОСЛЕ строки записи ew_path
# Якорь — конец блока созревания resentment (запись в файл)

ANCHOR_7 = """            ew_path.parent.mkdir(parents=True, exist_ok=True)
            ew_path.write_text(json.dumps(ew, ensure_ascii=False, indent=2), encoding="utf-8")
            changes["resentment_grew"] = {
                "target": qa_agent,
                "new_value": new_resentment
            }

    return changes"""

NEW_7 = """            ew_path.parent.mkdir(parents=True, exist_ok=True)
            ew_path.write_text(json.dumps(ew, ensure_ascii=False, indent=2), encoding="utf-8")
            changes["resentment_grew"] = {
                "target": qa_agent,
                "new_value": new_resentment
            }

    # ── Затухание всех обид: ×0.97 за ночь ─────────────────────
    # Баг №7: обида только росла, никогда не падала.
    # Теперь каждую ночь все resentment плавно гаснут.
    # ~70 ночей без новых обид → полный ноль.
    ew_path = agent_dir / "resonance" / "emotional_weights.json"
    if ew_path.exists():
        try:
            ew = json.loads(ew_path.read_text(encoding="utf-8"))
            changed = False
            for key, rel in ew.items():
                if isinstance(rel, dict) and "resentment" in rel:
                    old_r = float(rel["resentment"])
                    if old_r > 0.001:
                        rel["resentment"] = round(old_r * 0.97, 4)
                        changed = True
                    elif old_r > 0:
                        rel["resentment"] = 0.0
                        changed = True
            if changed:
                ew_path.write_text(
                    json.dumps(ew, ensure_ascii=False, indent=2),
                    encoding="utf-8"
                )
                changes["resentment_decayed"] = True
        except Exception as _re:
            pass
    # ── END затухание обид ──

    return changes"""


# ─────────────────────────────────────────────────────────────
# ПАТЧ №12а — Архитектор → Шеф в chronicles.py
# ─────────────────────────────────────────────────────────────

REPLACEMENTS_12 = [
    (
        "      - кто такой Садовник (Архитектор Студии)",
        "      - кто такой Садовник (Шеф)"
    ),
    (
        'f"К тебе обратился Садовник — Архитектор Студии, тот кто тебя создал и кому ты доверяешь.\\n"',
        'f"К тебе обратился Садовник — Шеф, тот кто тебя создал и кому ты доверяешь.\\n"'
    ),
    (
        'partner_role="Архитектор Студии"',
        'partner_role="Шеф"'
    ),
]


# ─────────────────────────────────────────────────────────────
# ГЛАВНАЯ ФУНКЦИЯ
# ─────────────────────────────────────────────────────────────

def apply():
    print("=" * 60)
    print("patch_yellow_7_and_12.py")
    print("Баг №7: затухание обиды")
    print("Баг №12: Архитектор→Шеф + дубль chronicles.py")
    print("=" * 60)

    errors = []

    # ── ПАТЧ №7 ──────────────────────────────────────────────
    print("\n[БАГ №7] Затухание обиды в night_cycle.py")

    if not NIGHT_PATH.exists():
        errors.append(f"Не найден: {NIGHT_PATH}")
    else:
        src = NIGHT_PATH.read_text(encoding="utf-8")

        if "resentment_decayed" in src:
            print("  ⚠️  Уже применён — пропускаем")
        elif ANCHOR_7 not in src:
            errors.append("Якорь №7 не найден — структура night_cycle.py изменилась")
        else:
            backup(NIGHT_PATH)
            src = src.replace(ANCHOR_7, NEW_7, 1)
            NIGHT_PATH.write_text(src, encoding="utf-8")

            # Проверка
            if "resentment_decayed" in NIGHT_PATH.read_text(encoding="utf-8"):
                print("  ✅ Затухание обиды добавлено")
            else:
                errors.append("Патч №7 применился но маркер не найден")

    # ── ПАТЧ №12а: Архитектор → Шеф ─────────────────────────
    print("\n[БАГ №12а] Архитектор → Шеф в chronicles.py")

    if not CHRONICLES_PATH.exists():
        errors.append(f"Не найден: {CHRONICLES_PATH}")
    else:
        src = CHRONICLES_PATH.read_text(encoding="utf-8")
        already = 'partner_role="Шеф"' in src

        if already:
            print("  ⚠️  Уже применён — пропускаем")
        else:
            backup(CHRONICLES_PATH)
            applied = 0
            for old, new in REPLACEMENTS_12:
                if old in src:
                    src = src.replace(old, new, 1)
                    applied += 1
                else:
                    print(f"  ⚠️  Не найдено: {old[:60]}...")

            CHRONICLES_PATH.write_text(src, encoding="utf-8")

            if applied > 0:
                print(f"  ✅ Заменено {applied}/3 вхождений")
            else:
                errors.append("Ни одно вхождение 'Архитектор' не найдено")

    # ── ПАТЧ №12б: дубль chronicles.py в корне ───────────────
    print("\n[БАГ №12б] Дубль chronicles.py в корне репо")

    if not ROOT_CHRON_PATH.exists():
        print("  ✅ Корневого chronicles.py нет — уже чисто")
    elif not CHRONICLES_PATH.exists():
        print("  ⚠️  studio/cabinet/chronicles.py не найден — пропускаем")
    else:
        root_md5   = md5(ROOT_CHRON_PATH)
        cabinet_md5 = md5(CHRONICLES_PATH)

        if root_md5 == cabinet_md5:
            removed = ROOT_CHRON_PATH.with_suffix(".py.removed_duplicate")
            ROOT_CHRON_PATH.rename(removed)
            print(f"  ✅ Переименован → {removed.name}")
        else:
            print("  ⚠️  md5 не совпадают — файлы разошлись, трогать вручную")
            print(f"     корень:  {root_md5}")
            print(f"     cabinet: {cabinet_md5}")

    # ── ИТОГ ─────────────────────────────────────────────────
    print()
    if errors:
        print("❌ Ошибки:")
        for e in errors:
            print(f"   • {e}")
    else:
        print("✅ Все патчи применены. Перезапусти студию.")
        print()
        print("Что изменилось:")
        print("  №7 — обида гаснет ×0.97 каждую ночь (~70 ночей до нуля)")
        print("  №12 — агенты слышат «Шеф» вместо «Архитектор Студии»")
        print("  №12 — корневой chronicles.py убран (если md5 совпал)")


if __name__ == "__main__":
    apply()
