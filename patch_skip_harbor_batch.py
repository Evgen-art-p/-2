# -*- coding: utf-8 -*-
# patch_skip_harbor_batch.py · 2026-06-14
# ─────────────────────────────────────────────────────────────
# Чинит зависание run_council_batch.py на первом сигнале.
#
# Причина: Гавань Смыслов (RAG) лениво загружает SentenceTransformer
# при первом обращении — это 30-60 сек молчаливой инициализации
# transformers/. Шеф видит тишину после "[MODE] A01: HOME" и жмёт
# Ctrl+C, получая KeyboardInterrupt в глубине стека.
#
# Решение:
#   1) Гавань для backtest бесполезна — это RAG по клиентским проектам,
#      не по торговой истории. Отключаем флагом state["_skip_harbor"].
#   2) Заодно форсируем WORK-режим в state["_force_work_mode"] —
#      city_pulse не успевает увидеть work_start() в CLI-ране,
#      пайплайн уже подготовил этот штатный обход.
#
# Запуск:
#   python patch_skip_harbor_batch.py
# ─────────────────────────────────────────────────────────────

from pathlib import Path

ROOT = Path(__file__).parent.resolve()


def patch_pipeline():
    """В pipeline.py — блок ГАВАНЬ уважает state['_skip_harbor']."""
    p = ROOT / "studio" / "workshop" / "pipeline.py"
    if not p.exists():
        print(f"❌ Не найден: {p}")
        return False

    src = p.read_text(encoding="utf-8")

    old = "    if _HARBOR_ENABLED:\n        harbor_ctx = get_harbor_knowledge("
    new = ("    if _HARBOR_ENABLED and not state.get(\"_skip_harbor\"):\n"
           "        harbor_ctx = get_harbor_knowledge(")

    if 'not state.get("_skip_harbor")' in src:
        print("⏭  pipeline.py: уже пропатчен, пропускаю")
        return True

    if old not in src:
        print("❌ pipeline.py: не нашёл маркер блока ГАВАНЬ")
        print("   Ожидалось:")
        print("   " + old.replace("\n", "\n   "))
        return False

    src_new = src.replace(old, new, 1)
    p.write_text(src_new, encoding="utf-8")
    print("✓ pipeline.py: блок ГАВАНЬ теперь уважает state['_skip_harbor']")
    return True


def patch_batch():
    """В run_council_batch.py — выставляем флаги _skip_harbor и _force_work_mode."""
    p = ROOT / "run_council_batch.py"
    if not p.exists():
        print(f"❌ Не найден: {p}")
        return False

    src = p.read_text(encoding="utf-8")

    if '"_skip_harbor"' in src:
        print("⏭  run_council_batch.py: уже пропатчен, пропускаю")
        return True

    old = (
        '    state = {\n'
        '        "active_dept":  "trading",\n'
        '        "run_type":     "batch_council",\n'
    )
    new = (
        '    state = {\n'
        '        "active_dept":  "trading",\n'
        '        "run_type":     "batch_council",\n'
        '        "_force_work_mode": True,   # CLI-ран: агенты в WORK, не HOME\n'
        '        "_skip_harbor":     True,   # batch: без RAG (трейдеру нужен рынок, не runs/)\n'
    )

    if old not in src:
        print("❌ run_council_batch.py: не нашёл маркер state-блока")
        return False

    src_new = src.replace(old, new, 1)
    p.write_text(src_new, encoding="utf-8")
    print("✓ run_council_batch.py: state форсирует WORK и пропускает Гавань")
    return True


if __name__ == "__main__":
    print("═══ patch_skip_harbor_batch ═══")
    ok1 = patch_pipeline()
    ok2 = patch_batch()
    print()
    if ok1 and ok2:
        print("✅ Готово. Запускай батч:")
        print("   python run_council_batch.py EURUSDDaily.csv EURUSD D1")
    else:
        print("⚠️  Один из патчей не применился — смотри сообщения выше.")
