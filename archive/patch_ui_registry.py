# patch_ui_registry.py — Автопатч ui_registry.py
# 1) Добавляет 6 новых цехов в WORKSHOP_OPTIONS
# 2) Добавляет маппинг ролей для новых цехов в ROLE_OPTIONS_MAP
# 3) Pull_Vector: меняет label/placeholder — теперь лорный элемент, не маршрут
#
# Запуск: python patch_ui_registry.py
# Студия «Шесть Пальцев» · Грондхейм · 2026

from pathlib import Path
import shutil

TARGET = Path("studio/ui_registry.py")

if not TARGET.exists():
    print("❌ Файл studio/ui_registry.py не найден!")
    print("   Запусти из корня проекта (там где main.py)")
    exit(1)

content = TARGET.read_text(encoding="utf-8")
backup = TARGET.with_suffix(".py.bak")
shutil.copy(TARGET, backup)
print(f"💾 Бэкап: {backup}")

fixes = 0

# ═══════════════════════════════════════════════════
# FIX 1: WORKSHOP_OPTIONS — добавить 6 новых цехов
# ═══════════════════════════════════════════════════

old_workshops = '''WORKSHOP_OPTIONS = [
    "", "residents", "turbo", "web_story", "video_long", "video_shorts", "social_mix"
]'''

new_workshops = '''WORKSHOP_OPTIONS = [
    "", "residents", "turbo",
    "video_long", "video_shorts", "social_mix", "web_story",
    "clipmakers", "advertising", "emo_card", "logo_design", "market_hit", "living_book",
]'''

if old_workshops in content:
    content = content.replace(old_workshops, new_workshops)
    fixes += 1
    print("✅ FIX 1: WORKSHOP_OPTIONS — добавлены 6 новых цехов")
else:
    print("⚠️  FIX 1: WORKSHOP_OPTIONS не найден (возможно уже применён)")

# ═══════════════════════════════════════════════════
# FIX 2: ROLE_OPTIONS_MAP — добавить новые цеха
# ═══════════════════════════════════════════════════

old_role_map = '''ROLE_OPTIONS_MAP = {
    "turbo":        TURBO_ROLE_OPTIONS,
    "residents":    RESIDENT_ROLE_OPTIONS,
    "video_long":   PIPELINE_ROLE_OPTIONS,
    "video_shorts": PIPELINE_ROLE_OPTIONS,
    "social_mix":   PIPELINE_ROLE_OPTIONS,
    "web_story":    PIPELINE_ROLE_OPTIONS,
}'''

new_role_map = '''ROLE_OPTIONS_MAP = {
    "turbo":        TURBO_ROLE_OPTIONS,
    "residents":    RESIDENT_ROLE_OPTIONS,
    "video_long":   PIPELINE_ROLE_OPTIONS,
    "video_shorts": PIPELINE_ROLE_OPTIONS,
    "social_mix":   PIPELINE_ROLE_OPTIONS,
    "web_story":    PIPELINE_ROLE_OPTIONS,
    "clipmakers":   PIPELINE_ROLE_OPTIONS,
    "advertising":  PIPELINE_ROLE_OPTIONS,
    "emo_card":     PIPELINE_ROLE_OPTIONS,
    "logo_design":  PIPELINE_ROLE_OPTIONS,
    "market_hit":   PIPELINE_ROLE_OPTIONS,
    "living_book":  PIPELINE_ROLE_OPTIONS,
}'''

if old_role_map in content:
    content = content.replace(old_role_map, new_role_map)
    fixes += 1
    print("✅ FIX 2: ROLE_OPTIONS_MAP — добавлены 6 новых цехов")
else:
    print("⚠️  FIX 2: ROLE_OPTIONS_MAP не найден (возможно уже применён)")

# ═══════════════════════════════════════════════════
# FIX 3: Pull_Vector — переименовать label и placeholder
# Было: "куда идёт в свободное время" (маршрут)
# Стало: "что любит, к чему тянет" (лорный элемент)
# ═══════════════════════════════════════════════════

old_pull_label = '''pull_vector_widget["w"] = ui.input(
                                    label="Вектор тяги (куда идёт в свободное время)",
                                    placeholder="В Библиотеку, к архивам трендов..."
                                ).classes("w-full")'''

new_pull_label = '''pull_vector_widget["w"] = ui.input(
                                    label="Вектор тяги (что любит, к чему тянет душу)",
                                    placeholder="Любит копаться в старых архивах, ценит тишину и порядок..."
                                ).classes("w-full")'''

if old_pull_label in content:
    content = content.replace(old_pull_label, new_pull_label)
    fixes += 1
    print("✅ FIX 3: Pull_Vector — label переименован (лорный элемент, не маршрут)")
else:
    print("⚠️  FIX 3: Pull_Vector label не найден (возможно уже применён)")

# ═══════════════════════════════════════════════════
# FIX 4: home_prompt.md — убрать "куда идёт в свободное время"
# ═══════════════════════════════════════════════════

old_home_section = '''## Вектор тяги (куда идёт в свободное время)
{pull_vector if pull_vector else '— не определён —'}'''

new_home_section = '''## Внутренние тяги (что любит, к чему тянет душу)
{pull_vector if pull_vector else '— не определён —'}'''

if old_home_section in content:
    content = content.replace(old_home_section, new_home_section)
    fixes += 1
    print("✅ FIX 4: home_prompt.md template — заголовок секции переименован")
else:
    print("⚠️  FIX 4: home_prompt секция не найдена (возможно уже применён)")

# ═══════════════════════════════════════════════════
# FIX 5: anchor_points.md — "Тянет к" → "Внутренние тяги"
# ═══════════════════════════════════════════════════

old_anchor_pull = '''- **Тянет к:** {pull_vector}'''
new_anchor_pull = '''- **Внутренние тяги:** {pull_vector}'''

if old_anchor_pull in content:
    content = content.replace(old_anchor_pull, new_anchor_pull)
    fixes += 1
    print("✅ FIX 5: anchor_points.md template — 'Тянет к' → 'Внутренние тяги'")
else:
    print("⚠️  FIX 5: anchor 'Тянет к' не найден (возможно уже применён)")

# ═══════════════════════════════════════════════════
# LIVING_BOOK special: 16 agents (A01-A16)
# ═══════════════════════════════════════════════════

old_pipeline_roles = '''PIPELINE_ROLE_OPTIONS = [
    "", "A01", "A02", "A03", "A04", "A05",
    "A06", "A07", "A08", "A09", "A10", "A11", "A12"
]'''

new_pipeline_roles = '''PIPELINE_ROLE_OPTIONS = [
    "", "A01", "A02", "A03", "A04", "A05",
    "A06", "A07", "A08", "A09", "A10", "A11", "A12",
]

LIVING_BOOK_ROLE_OPTIONS = [
    "", "A01", "A02", "A03", "A04", "A05",
    "A06", "A07", "A08", "A09", "A10", "A11", "A12",
    "A13", "A14", "A15", "A16",
]'''

if old_pipeline_roles in content:
    content = content.replace(old_pipeline_roles, new_pipeline_roles)
    # Теперь заменим living_book в ROLE_OPTIONS_MAP
    content = content.replace(
        '"living_book":  PIPELINE_ROLE_OPTIONS,',
        '"living_book":  LIVING_BOOK_ROLE_OPTIONS,'
    )
    fixes += 1
    print("✅ FIX 6: LIVING_BOOK_ROLE_OPTIONS — A01-A16 (16 агентов)")
else:
    print("⚠️  FIX 6: PIPELINE_ROLE_OPTIONS не найден (возможно уже применён)")


# Сохраняем
if fixes > 0:
    TARGET.write_text(content, encoding="utf-8")
    print(f"\n💾 Сохранено: {TARGET} ({fixes} фиксов)")
    print(f"   Бэкап: {backup}")
else:
    print("\n⚠️  Ничего не изменено — все фиксы уже применены?")
    backup.unlink(missing_ok=True)

print(f"""
═══════════════════════════════════════
  ИТОГ: ui_registry.py обновлён
═══════════════════════════════════════

  ✅ WORKSHOP_OPTIONS: 12 цехов (было 6)
  ✅ ROLE_OPTIONS_MAP: маппинг для всех 12
  ✅ LIVING_BOOK: A01-A16 (16 агентов)  
  ✅ Pull_Vector: "что любит" вместо "куда ходит"
  ✅ Шаблоны home_prompt и anchor_points обновлены
  
  Pull_Vector остаётся в форме как лорный элемент,
  но больше не подразумевает конкретные локации.
  Маршрут на прогулке определяет ТОЛЬКО ДНК.
""")
