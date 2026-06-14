# -*- coding: utf-8 -*-
# patch_trading_turbo_workers.py · 2026-06-14
# ─────────────────────────────────────────────────────────────
# Исправляет: в Торговом Цехе запускались только 5 агентов из 9.
#
# Причина: cartridge.py::run_turbo() берёт manifest.turbo_workers,
# а если поле пустое — fallback get_all_agents()[:5]. В торговом
# manifest поля turbo_workers нет вовсе, поэтому Шасси берёт
# A01..A05 (сенсоры + Морж), а Брут/Авантюрист/Консерватор/
# Исполнитель остаются за кулисами. Трибунал молчал не потому
# что нет сигнала — а потому что его не звали к столу.
#
# Решение: объявить turbo_workers явно — все 9 агентов.
# Параллельность совета (turbo_parallel: A06/A07/A08) сохраняется,
# трое трейдеров пойдут одновременно как и задумано.
#
# Запуск:
#   python patch_trading_turbo_workers.py
# ─────────────────────────────────────────────────────────────

import json
from pathlib import Path

ROOT = Path(__file__).parent.resolve()
MANIFEST = ROOT / "studio" / "modules" / "trading" / "manifest.json"

ALL_AGENTS = ["A01", "A02", "A03", "A04", "A05",
              "A06", "A07", "A08", "A09"]


def main():
    if not MANIFEST.exists():
        print(f"❌ Не найден: {MANIFEST}")
        return

    data = json.loads(MANIFEST.read_text(encoding="utf-8"))

    current = data.get("turbo_workers", [])
    if current == ALL_AGENTS:
        print("⏭  turbo_workers уже корректный — пропускаю")
        return

    if current:
        print(f"⚠  Был список из {len(current)} агентов: {current}")
        print(f"   Заменяю на все 9.")
    else:
        print("✓ Поле turbo_workers отсутствовало — добавляю все 9.")

    # Вставляем turbo_workers ПЕРЕД turbo_parallel для логичной группировки.
    # Перестраиваем dict с нужным порядком ключей.
    new_data = {}
    inserted = False
    for k, v in data.items():
        if k == "turbo_parallel" and not inserted:
            new_data["turbo_workers"] = ALL_AGENTS
            inserted = True
        if k == "turbo_workers":
            # Старое значение пропускаем — мы его уже вставили (или вставим)
            continue
        new_data[k] = v

    # Если turbo_parallel в файле не было — добавляем turbo_workers в конец
    if not inserted:
        new_data["turbo_workers"] = ALL_AGENTS

    MANIFEST.write_text(
        json.dumps(new_data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"✓ {MANIFEST.name}: turbo_workers = {ALL_AGENTS}")
    print()
    print("→ Теперь батч прогонит всю девятку. Запускай:")
    print("   python run_council_batch.py EURUSDDaily.csv EURUSD D1")


if __name__ == "__main__":
    main()
