# studio/check_dashboard.py
"""Проверяет, что все файлы дашборда на месте и импортируются."""
import sys
from pathlib import Path

# Добавляем корень проекта в путь (папка, где лежит studio/)
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
print(f"📁 Корень проекта: {ROOT}")

errors = []

print("🔍 Проверка файлов дашборда...")
print("-" * 50)

# 1. billing_ledger.py
try:
    from studio.billing_ledger import get_economy_data, get_agent_stats
    print("✅ billing_ledger.py — get_economy_data, get_agent_stats импортированы")
except Exception as e:
    errors.append(f"❌ billing_ledger.py: {e}")

# 2. calculator.py
try:
    from studio.economy.calculator import get_economy_data, get_agent_stats
    print("✅ calculator.py — реэкспорт работает")
except Exception as e:
    errors.append(f"❌ calculator.py: {e}")

# 3. ui_dashboard.py — проверяем что файл без синтаксических ошибок
try:
    dashboard_path = ROOT / "studio" / "economy" / "ui_dashboard.py"
    compile(dashboard_path.read_text(encoding="utf-8"), "ui_dashboard.py", "exec")
    print("✅ ui_dashboard.py — синтаксис в порядке")
except Exception as e:
    errors.append(f"❌ ui_dashboard.py: {e}")

# 4. Быстрый тест данных (если ledger не пустой)
try:
    data = get_economy_data(days=1)
    print(f"✅ get_economy_data(1) → total=${data.get('total', 0):.4f}, "
          f"providers={len(data.get('by_provider', {}))}, "
          f"models={len(data.get('by_model', {}))}, "
          f"agents={len(data.get('by_agent', {}))}, "
          f"slots={len(data.get('by_slot', {}))}")
except Exception as e:
    print(f"⚠️  Тест данных: {e} (возможно леджер пуст)")

print("-" * 50)

if errors:
    print("\n❌ НАЙДЕНЫ ОШИБКИ:")
    for e in errors:
        print(f"  {e}")
    print("\nПерепроверь файлы и запусти снова.")
    sys.exit(1)
else:
    print("\n✅ ВСЁ ГОТОВО! Запускай студию и открывай /dashboard")