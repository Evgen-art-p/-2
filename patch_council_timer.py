"""
patch_council_timer.py
======================
Финальный фикс: update_all() не пересоздаёт центр в режиме Совета.

Проблема: таймер каждые 30 сек вызывает update_all()
→ render_center_grid() → render_council_grid()
→ council_chat_el пересоздаётся → старый ref умирает
→ сообщения Шефа исчезают через 30 сек.

Решение: в режиме council пропускаем render_center_grid() и render_charts().

Запуск: python patch_council_timer.py
"""
import shutil, subprocess
from pathlib import Path

DASHBOARD = Path("studio/economy/ui_dashboard.py")

OLD = '''    def update_all():
        state["economy_data"] = get_economy_data(state["period"])
        state["all_agents"]   = list_all_agents()
        render_agent_list()
        render_center_grid()    # рендерит активную сетку (economy или observability)
        render_charts()         # заливает данные в echart (только economy-рефы)
        render_detail()'''

NEW = '''    def update_all():
        state["economy_data"] = get_economy_data(state["period"])
        state["all_agents"]   = list_all_agents()
        render_agent_list()
        # В режиме Совета не пересоздаём центр — это убивает council_chat_el
        if state["center_view"] != "council":
            render_center_grid()
            render_charts()
        render_detail()'''

src = DASHBOARD.read_text(encoding="utf-8")
if OLD in src:
    bak = DASHBOARD.with_suffix(".py.bak_timer")
    shutil.copy2(DASHBOARD, bak)
    src = src.replace(OLD, NEW)
    DASHBOARD.write_text(src, encoding="utf-8")
    r = subprocess.run(["python", "-m", "py_compile", str(DASHBOARD)], capture_output=True, text=True)
    if r.returncode == 0:
        print("✅ Готово — перезапусти студию")
        print("   Чат Совета больше не сбрасывается каждые 30 секунд.")
    else:
        print(f"❌ {r.stderr}")
        shutil.copy2(bak, DASHBOARD)
        print("↩ Бэкап")
else:
    print("❌ Маркер не найден — возможно update_all уже исправлен")
