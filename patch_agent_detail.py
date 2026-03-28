# patch_agent_detail.py — Фикс отображения резонанса в кабинете
# Проблема: pull_vector, hidden_taste, trigger_keywords не видны
# Причина: искал "vector" вместо "pull_vector", trigger_keywords вообще не рендерился
#
# Запуск: python patch_agent_detail.py

from pathlib import Path
import shutil

TARGET = Path("studio/cabinet/agents.py")

if not TARGET.exists():
    print("❌ studio/cabinet/agents.py не найден!")
    exit(1)

content = TARGET.read_text(encoding="utf-8")
backup = TARGET.with_suffix(".py.bak")
shutil.copy(TARGET, backup)
print(f"💾 Бэкап: {backup}")

# ═══ Заменяем весь блок резонанса в render_agent_detail ═══

old_block = '''    # Resonance / anchors
    resonance = dna.get("resonance", {})
    anchors = resonance.get("anchor_points", [])
    if anchors:
        with ui.element("div").style("margin-bottom: 12px;"):
            ui.html('<div class="cab-detail-header">якоря</div>')
            with ui.element("div"):
                for tag in anchors:
                    ui.html(f'<span class="cab-anchor-tag">{tag}</span>')

    # Vector / taste
    vector = resonance.get("vector", "")
    taste = resonance.get("hidden_taste", "")
    if vector or taste:
        with ui.element("div").style("margin-bottom: 12px;"):
            ui.html('<div class="cab-detail-header">резонанс</div>')
            if vector:
                ui.label(f"Вектор: {vector}").style(
                    "font-family: 'JetBrains Mono'; font-size: 0.56rem; color: rgba(180,190,220,0.6);"
                )
            if taste:
                ui.label(f"Вкус: {taste}").style(
                    "font-family: 'JetBrains Mono'; font-size: 0.56rem; color: rgba(180,190,220,0.6);"
                )'''

new_block = '''    # ═══ Резонанс (pull_vector, hidden_taste, trigger_keywords) ═══
    resonance = dna.get("resonance", {})
    pull = resonance.get("pull_vector", "")
    taste = resonance.get("hidden_taste", "")
    triggers = resonance.get("trigger_keywords", [])

    if pull or taste or triggers:
        with ui.element("div").style("margin-bottom: 12px;"):
            ui.html('<div class="cab-detail-header">резонанс</div>')
            if pull:
                # pull_vector может быть списком или строкой
                if isinstance(pull, list):
                    pull_text = "; ".join(str(x)[:80] for x in pull[:3])
                else:
                    pull_text = str(pull)[:200]
                ui.label(f"Тяги: {pull_text}").style(
                    "font-family: 'JetBrains Mono'; font-size: 0.56rem; color: rgba(180,190,220,0.6); margin-bottom: 4px;"
                )
            if taste:
                if isinstance(taste, list):
                    taste_text = "; ".join(str(x)[:60] for x in taste[:3])
                else:
                    taste_text = str(taste)[:200]
                ui.label(f"Вкус: {taste_text}").style(
                    "font-family: 'JetBrains Mono'; font-size: 0.56rem; color: rgba(180,190,220,0.6); margin-bottom: 4px;"
                )
            if triggers:
                if isinstance(triggers, list):
                    tags_text = ", ".join(str(t) for t in triggers[:6])
                else:
                    tags_text = str(triggers)
                ui.label(f"Триггеры: {tags_text}").style(
                    "font-family: 'JetBrains Mono'; font-size: 0.56rem; color: rgba(201,168,76,0.6); margin-bottom: 4px;"
                )'''

if old_block in content:
    content = content.replace(old_block, new_block)
    TARGET.write_text(content, encoding="utf-8")
    print("✅ Резонанс пофикшен:")
    print('   - pull_vector: "vector" → "pull_vector"')
    print("   - hidden_taste: поддержка list формата")
    print("   - trigger_keywords: добавлено отображение")
else:
    print("⚠️  Блок не найден (возможно уже применён)")
    backup.unlink(missing_ok=True)
