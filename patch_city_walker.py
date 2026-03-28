# patch_city_walker.py — Автопатч city_walker.py
# Убирает Pull_Vector из промпта прогулки и из расчёта весов
# Запуск: python patch_city_walker.py
#
# Студия «Шесть Пальцев» · Грондхейм · 2026

from pathlib import Path
import shutil

TARGET = Path("studio/city_walker.py")

if not TARGET.exists():
    print("❌ Файл studio/city_walker.py не найден!")
    print("   Запусти из корня проекта (там где main.py)")
    exit(1)

content = TARGET.read_text(encoding="utf-8")
backup = TARGET.with_suffix(".py.bak")
shutil.copy(TARGET, backup)
print(f"💾 Бэкап: {backup}")

fixes = 0

# ═══ FIX 1: format_agent_state — убрать pull_vector из промпта ═══
old1 = '''    # Резонанс
    pull   = resonance.get("pull_vector", "")
    taste  = resonance.get("hidden_taste", "")
    if pull:
        lines.append(f"\\nВектор тяги: {pull}")
    if taste:
        lines.append(f"Скрытый вкус: {taste}")'''

new1 = '''    # Резонанс — pull_vector НЕ передаём в промпт
    # Агент выбирает локацию по состоянию ДНК, не по записанной привычке
    taste = resonance.get("hidden_taste", "")
    if taste:
        lines.append(f"\\nСкрытый вкус: {taste}")'''

if old1 in content:
    content = content.replace(old1, new1)
    fixes += 1
    print("✅ FIX 1: pull_vector убран из format_agent_state (промпт прогулки)")
else:
    print("⚠️  FIX 1: блок не найден (возможно уже применён)")

# ═══ FIX 2a: compute_location_weights — убрать переменную pull_vector ═══
old2a = '    pull_vector = resonance.get("pull_vector", "").lower()'
new2a = '    # pull_vector больше не влияет — выбор только по состоянию ДНК'

if old2a in content:
    content = content.replace(old2a, new2a)
    fixes += 1
    print("✅ FIX 2a: переменная pull_vector убрана из compute_location_weights")
else:
    print("⚠️  FIX 2a: строка не найдена (возможно уже применён)")

# ═══ FIX 2b: compute_location_weights — убрать бонус от pull_vector ═══
old2b = '''        # Бонус от pull_vector
        loc_tags = loc.get("Style_Tags", "").lower()
        if pull_vector and any(word in loc_tags for word in pull_vector.split()):
            w += 0.1'''

new2b = '        # pull_vector бонус УБРАН — выбор по текущему состоянию агента'

if old2b in content:
    content = content.replace(old2b, new2b)
    fixes += 1
    print("✅ FIX 2b: бонус pull_vector убран из compute_location_weights")
else:
    print("⚠️  FIX 2b: блок не найден (возможно уже применён)")

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
  ИТОГ: Pull_Vector отвязан от маршрута
═══════════════════════════════════════
  
  Теперь агенты выбирают локацию ТОЛЬКО по ДНК:
    Стресс высокий → Таверна «Усталый Пиксель»
    Свет низкий → Храм Пробуждения
    Давно не был → Маяк (Голод по знаниям)
    Aesthetic высокий → Библиотека Смыслов  
    Одиночка → Дом (Высотка/Квартал)
  
  Pull_Vector остаётся в dna.json как лорная деталь
  (что агент любит) — но НЕ определяет маршрут.
""")
