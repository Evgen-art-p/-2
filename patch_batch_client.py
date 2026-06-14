# -*- coding: utf-8 -*-
# patch_batch_client.py · 2026-06-14
# ─────────────────────────────────────────────────────────────
# Без current_client в state пайплайн считает run_type="_sandbox"
# и весь блок QA пропускается: feedback.json не пишется,
# DNA не обновляется, стратегии не копятся.
#
# Одна строка в state — и трейдеры начинают жить по-настоящему.
# ─────────────────────────────────────────────────────────────

from pathlib import Path

ROOT = Path(__file__).parent.resolve()
TARGET = ROOT / "run_council_batch.py"


def main():
    if not TARGET.exists():
        print(f"❌ Не найден: {TARGET}")
        return

    src = TARGET.read_text(encoding="utf-8")

    if '"current_client"' in src:
        print("⏭  current_client уже есть — пропускаю")
        return

    old = '        "_skip_harbor":     True,   # batch: без RAG (трейдеру нужен рынок, не runs/)'
    new = (
        '        "_skip_harbor":     True,   # batch: без RAG (трейдеру нужен рынок, не runs/)\n'
        '        "current_client":   "trading_batch",  # не sandbox → DNA и feedback живые'
    )

    if old not in src:
        print("❌ Не нашёл маркер — возможно файл изменился")
        return

    TARGET.write_text(src.replace(old, new, 1), encoding="utf-8")
    print("✓ run_council_batch.py: current_client = 'trading_batch'")
    print()
    print("Теперь каждый прогон:")
    print("  · feedback.json → clients/trading_batch/feedback.json")
    print("  · DNA трейдеров обновляется после каждого заседания")
    print("  · стратегии копятся в Strategy Registry")
    print()
    print("Запускай:")
    print("  python run_council_batch.py EURUSDDaily.csv EURUSD D1")


if __name__ == "__main__":
    main()
