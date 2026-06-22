#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# reset_iskra_soul.py
# ─────────────────────────────────────────────────────────────
# ОДНОРАЗОВЫЙ СБРОС СОСТОЯНИЯ ИСКРЫ (A01)  ·  не патч кода
#
# Искра накопила стресс 0.80 и streak −13 из-за СТАРОГО несправедливого
# штрафа (bad_work за пустышку), который мы уже убрали патчем
# ISKRA_FAIR_JUDGEMENT_V1. Но накопленное состояние осталось в dna.json.
# Этот скрипт обнуляет рану — выставляет здоровое состояние, как делает
# физиологический сброс sync_to_dna при streak>=3, только разом.
#
# ЧТО ДЕЛАЕТ:
#   · Stress         → 0.0   (была 0.80 — отпускаем)
#   · streak         → 0     (был −13 — чистый лист, не минус, не плюс)
#   · Internal_Light → 0.8   (поднимаем — вернём огонь)
#   · Patience       → 1.0   (терпение восстановлено)
#   · Respect        → не трогаем (это к Шефу, его не сбрасываем)
#   · stars          → не трогаем (заслуги остаются)
#
#   Сбрасывает и daily-счётчики cabinet_chat (старые ключи по датам).
#
# БЕЗОПАСНО: показывает «было → стало», бэкап dna.json рядом. Идемпотентен
# в смысле результата (повторный запуск просто снова выставит здоровое).
#
# ЗАПУСК из корня репы (-2/):
#   python reset_iskra_soul.py
# ─────────────────────────────────────────────────────────────

import sys
import json
import shutil
from pathlib import Path
from datetime import datetime


def _die(msg):
    print(f"❌ {msg}")
    sys.exit(1)


def _find_iskra_dna():
    """Ищет dna.json Искры. Сначала прямой путь A01, потом по modules."""
    direct = Path("studio/modules/trading/A01/dna.json")
    if direct.exists():
        return direct
    # фоллбэк: ищем по полю id/name в modules/trading
    base = Path("studio/modules/trading")
    if base.exists():
        for d in base.iterdir():
            if not d.is_dir():
                continue
            dna_p = d / "dna.json"
            if not dna_p.exists():
                continue
            try:
                dna = json.loads(dna_p.read_text(encoding="utf-8"))
                ident = (str(dna.get("id", "")) + str(dna.get("name", ""))).upper()
                if "ISKRA" in ident or "ИСКР" in ident or d.name.upper().startswith("A01"):
                    return dna_p
            except Exception:
                continue
    return None


def main():
    dna_path = _find_iskra_dna()
    if not dna_path:
        _die("dna.json Искры не найден — запусти из корня репы (-2/). "
             "Ожидал studio/modules/trading/A01/dna.json")

    try:
        dna = json.loads(dna_path.read_text(encoding="utf-8"))
    except Exception as e:
        _die(f"не прочитал {dna_path}: {e}")

    dyn = dna.get("dynamic", {})
    if not dyn:
        _die("в dna.json нет блока dynamic — нечего сбрасывать.")

    # ── показываем что было ──
    was = {
        "Stress":         dyn.get("Stress"),
        "streak":         dyn.get("streak"),
        "Internal_Light": dyn.get("Internal_Light"),
        "Patience":       dyn.get("Patience"),
        "Respect":        dyn.get("Respect"),
        "stars":          dyn.get("stars"),
    }
    print("─" * 56)
    print(f"  Искра · {dna_path}")
    print("─" * 56)
    print("  БЫЛО:")
    for k, v in was.items():
        print(f"    {k:16} = {v}")

    # ── бэкап ──
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = dna_path.with_name(f"dna.bak_{stamp}.json")
    shutil.copy2(dna_path, backup)
    print(f"\n  💾 бэкап: {backup.name}")

    # ── сброс на здоровое состояние ──
    dyn["Stress"]         = 0.0
    dyn["streak"]         = 0
    dyn["Internal_Light"] = max(0.8, float(dyn.get("Internal_Light", 0.8)))
    dyn["Patience"]       = 1.0
    # Respect и stars НЕ трогаем — это заслуги и отношение к Шефу.

    # чистим daily-счётчики cabinet_chat (старые ключи по датам)
    for k in list(dyn.keys()):
        if k.startswith("cabinet_chat_"):
            del dyn[k]

    dna["dynamic"] = dyn
    dna_path.write_text(
        json.dumps(dna, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n  СТАЛО:")
    for k in ("Stress", "streak", "Internal_Light", "Patience", "Respect", "stars"):
        print(f"    {k:16} = {dyn.get(k)}")
    print("─" * 56)
    print("  ✅ Искра отпущена на чистый лист. Стресс снят, страйки обнулены.")
    print("     Огонь вернётся — теперь её судят по делу, а не за пустышки.")
    print(f"\n     откат при нужде: cp {backup.name} {dna_path.name}")


if __name__ == "__main__":
    main()
