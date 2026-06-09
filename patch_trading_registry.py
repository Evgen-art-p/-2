"""
patch_trading_registry.py
=========================
Студия «Шесть Пальцев» · 2026-06-09

Вносит три правки в studio/ui_registry.py:
  1. Добавляет "trading" в WORKSHOP_OPTIONS
  2. Добавляет TRADING_ROLE_OPTIONS (A01–A09)
  3. Добавляет "trading": TRADING_ROLE_OPTIONS в ROLE_OPTIONS_MAP

Запуск из корня проекта:
  python patch_trading_registry.py
"""

import shutil
from pathlib import Path
from datetime import datetime

REGISTRY_FILE = Path("studio/ui_registry.py")
BACKUP_DIR    = Path("_patch_backups")

# ═══════════════════════════════════════════════════
# ТРИ ПАТЧА
# ═══════════════════════════════════════════════════

PATCH_1_OLD = '''WORKSHOP_OPTIONS = [
    "", "residents", "turbo",
    "video_long", "video_shorts", "social_mix", "web_story",
    "clipmakers", "advertising", "emo_card", "logo_design", "market_hit", "living_book",
]'''

PATCH_1_NEW = '''WORKSHOP_OPTIONS = [
    "", "residents", "turbo",
    "video_long", "video_shorts", "social_mix", "web_story",
    "clipmakers", "advertising", "emo_card", "logo_design", "market_hit", "living_book",
    "trading",
]'''

# ───────────────────────────────────────────────────

PATCH_2_OLD = '''LIVING_BOOK_ROLE_OPTIONS = ['''

PATCH_2_NEW = '''TRADING_ROLE_OPTIONS = [
    "", "A01", "A02", "A03", "A04", "A05",
    "A06", "A07", "A08", "A09",
]

LIVING_BOOK_ROLE_OPTIONS = ['''

# ───────────────────────────────────────────────────

PATCH_3_OLD = '''    "living_book":  LIVING_BOOK_ROLE_OPTIONS,
}'''

PATCH_3_NEW = '''    "living_book":  LIVING_BOOK_ROLE_OPTIONS,
    "trading":      TRADING_ROLE_OPTIONS,
}'''

# ═══════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════

def main():
    print("=" * 55)
    print("  PATCH: ui_registry.py — Торговый Цех")
    print("  Студия «Шесть Пальцев» · 2026-06-09")
    print("=" * 55)

    if not REGISTRY_FILE.exists():
        print(f"\n  ❌ Файл не найден: {REGISTRY_FILE}")
        print("  Проверь что запускаешь из корня проекта.")
        return

    content = REGISTRY_FILE.read_text(encoding="utf-8")

    # Бэкап
    BACKUP_DIR.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = BACKUP_DIR / f"ui_registry_{ts}.py"
    shutil.copy2(REGISTRY_FILE, backup)
    print(f"\n  💾 Бэкап: {backup}")

    errors = []

    # ПАТЧ 1 — WORKSHOP_OPTIONS
    print("\n  [1] WORKSHOP_OPTIONS...")
    if '"trading"' in content and 'WORKSHOP_OPTIONS' in content:
        print("      ℹ️  'trading' уже есть — пропускаем")
    elif PATCH_1_OLD in content:
        content = content.replace(PATCH_1_OLD, PATCH_1_NEW, 1)
        print("      ✅ добавлен 'trading'")
    else:
        print("      ❌ не нашёл WORKSHOP_OPTIONS — пропускаем")
        errors.append("WORKSHOP_OPTIONS не найден")

    # ПАТЧ 2 — TRADING_ROLE_OPTIONS
    print("\n  [2] TRADING_ROLE_OPTIONS...")
    if 'TRADING_ROLE_OPTIONS' in content:
        print("      ℹ️  уже существует — пропускаем")
    elif PATCH_2_OLD in content:
        content = content.replace(PATCH_2_OLD, PATCH_2_NEW, 1)
        print("      ✅ добавлен TRADING_ROLE_OPTIONS")
    else:
        print("      ❌ не нашёл LIVING_BOOK_ROLE_OPTIONS — пропускаем")
        errors.append("LIVING_BOOK_ROLE_OPTIONS не найден")

    # ПАТЧ 3 — ROLE_OPTIONS_MAP
    print("\n  [3] ROLE_OPTIONS_MAP...")
    if '"trading":' in content and 'ROLE_OPTIONS_MAP' in content:
        print("      ℹ️  'trading' уже есть в MAP — пропускаем")
    elif PATCH_3_OLD in content:
        content = content.replace(PATCH_3_OLD, PATCH_3_NEW, 1)
        print("      ✅ добавлен 'trading': TRADING_ROLE_OPTIONS")
    else:
        print("      ❌ не нашёл конец ROLE_OPTIONS_MAP — пропускаем")
        errors.append("ROLE_OPTIONS_MAP не найден")

    # Записываем
    REGISTRY_FILE.write_text(content, encoding="utf-8")

    # Итог
    print("\n" + "=" * 55)
    if not errors:
        print("  ✅ ГОТОВО. Все три правки внесены.")
        print()
        print("  Следующие шаги:")
        print("  1. Перезапустить студию (main.py)")
        print("  2. Открыть /registry → Страница Жизни")
        print("  3. В дропдауне 'Цех' выбрать 'trading'")
        print("  4. Родить A01 Искру первой (роль A01)")
    else:
        print(f"  ⚠️  Завершено с ошибками:")
        for e in errors:
            print(f"     · {e}")
        print()
        print("  Остальные правки применены.")
    print("=" * 55)

if __name__ == "__main__":
    main()
