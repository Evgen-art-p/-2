#!/usr/bin/env python3
"""
patch_complaint_book_ui.py
Добавляет вкладку «книга» в правую панель ui_cabinet.py.

Что добавляет:
  - Вкладка «книга» рядом с «хрониками»
  - Лента записей (жалобы 🗡 / благодарности 🌱)
  - Поле реплики Садовника под каждой записью
  - Кнопки действий: помирить / защитить / усилить / отпустить
  - Статистика в шапке

Запуск: python patch_complaint_book_ui.py
"""

from pathlib import Path

UI_PATH = Path("studio/cabinet/ui_cabinet.py")

# ════════════════════════════════════════════════════════════
# ПАТЧ 1 — добавить «книга» в список вкладок
# ════════════════════════════════════════════════════════════

ANCHOR_TABS = '    for tab_name, tab_label in [("agent","агент"),("matrix","матрица"),("chronicles","хроники"),("files","файлы"),("reports","отчёты"),("archive","архив")]:'

NEW_TABS = '    for tab_name, tab_label in [("agent","агент"),("matrix","матрица"),("chronicles","хроники"),("book","книга"),("files","файлы"),("reports","отчёты"),("archive","архив")]:'

# ════════════════════════════════════════════════════════════
# ПАТЧ 2 — добавить «книга» в список панелей
# ════════════════════════════════════════════════════════════

ANCHOR_PANELS = '                for tab_name in ["agent","matrix","chronicles","files","reports","archive"]:'

NEW_PANELS = '                for tab_name in ["agent","matrix","chronicles","book","files","reports","archive"]:'

# ════════════════════════════════════════════════════════════
# ПАТЧ 3 — добавить ветку в update_right_panel
# ════════════════════════════════════════════════════════════

ANCHOR_UPDATE = '            elif tab_name == "chronicles":  # === CHRONICLES_PATCH:update_right_panel ==='

NEW_UPDATE = '''            elif tab_name == "chronicles":  # === CHRONICLES_PATCH:update_right_panel ===
                _render_chronicles_tab()
            elif tab_name == "book":  # === BOOK_PATCH:update_right_panel ===
                _render_book_tab()
                return'''

# Убираем дублирующий вызов
ANCHOR_UPDATE_CALL = '''            elif tab_name == "chronicles":  # === CHRONICLES_PATCH:update_right_panel ===
                _render_chronicles_tab()
            elif tab_name == "book":  # === BOOK_PATCH:update_right_panel ===
                _render_book_tab()
                return
            elif tab_name == "chronicles":  # === CHRONICLES_PATCH:update_right_panel ==='''

# ════════════════════════════════════════════════════════════
# ПАТЧ 4 — добавить switch_tab кейс для «книга»
# ════════════════════════════════════════════════════════════

ANCHOR_SWITCH = '        if tab_name == "chronicles":  # === CHRONICLES_PATCH:switch_tab ==='

NEW_SWITCH = '''        if tab_name == "chronicles":  # === CHRONICLES_PATCH:switch_tab ===
            update_right_panel("chronicles")
        if tab_name == "book":  # === BOOK_PATCH:switch_tab ===
            update_right_panel("book")
            return'''

# ════════════════════════════════════════════════════════════
# ПАТЧ 5 — функция _render_book_tab (вставить перед def _render_chronicles_tab)
# ════════════════════════════════════════════════════════════

ANCHOR_FUNC = '    def _render_chronicles_tab():'

BOOK_FUNC = '''    def _render_book_tab():
        """Вкладка «Книга Жалоб и Благодарностей» в правой панели."""
        try:
            from studio.complaint_book import get_book_entries, get_book_stats, gardener_note_to_entry, gardener_action
        except ImportError:
            ui.html(
                '<div style="text-align:center;padding:24px;font-family:JetBrains Mono;'
                'font-size:0.56rem;color:rgba(140,150,180,0.3)">'
                'complaint_book.py не найден</div>'
            )
            return

        stats = get_book_stats()
        entries = get_book_entries(limit=40)

        # ── Статистика ──
        complaints = stats.get("complaints", 0)
        gratitudes = stats.get("gratitudes", 0)
        total = stats.get("total", 0)

        ui.html(
            f'<div style="padding:6px 10px;font-family:JetBrains Mono;'
            f'font-size:0.52rem;color:rgba(140,150,180,0.35);">'
            f'записей: {total} · '
            f'<span style="color:rgba(220,100,100,0.7)">🗡 {complaints}</span> · '
            f'<span style="color:rgba(80,200,140,0.7)">🌱 {gratitudes}</span>'
            f'</div>'
        )

        if not entries:
            ui.html(
                '<div style="text-align:center;padding:32px 16px;'
                'font-family:JetBrains Mono;font-size:0.56rem;'
                'color:rgba(140,150,180,0.3)">Книга пуста<br>'
                '<span style="font-size:0.5rem;color:rgba(140,150,180,0.2)">'
                'записи появятся после первого рана с QA</span></div>'
            )
            return

        # ── Состояние развёрнутой записи ──
        expanded_entry = {"id": None}

        def _toggle_entry(entry_id):
            if expanded_entry["id"] == entry_id:
                expanded_entry["id"] = None
            else:
                expanded_entry["id"] = entry_id
            update_right_panel("book")

        def _send_note(entry_id, note_input):
            note = (note_input.value or "").strip()
            if not note:
                ui.notify("Напиши реплику", type="warning")
                return
            ok = gardener_note_to_entry(entry_id, note)
            if ok:
                ui.notify("🌱 Шлейф записан в память агентов", type="positive")
                note_input.set_value("")
                update_right_panel("book")
            else:
                ui.notify("⚠ Запись не найдена", type="negative")

        def _do_action(entry_id, action_name):
            ok = gardener_action(entry_id, action_name)
            if ok:
                labels = {
                    "mediate": "⚖️ Помирил",
                    "protect": "🛡 Защитил",
                    "amplify": "🌟 Усилил",
                    "release": "🌊 Отпустил",
                }
                ui.notify(labels.get(action_name, "✓"), type="positive")
                update_right_panel("book")
            else:
                ui.notify("⚠ Не удалось", type="negative")

        # ── Лента записей ──
        with ui.element("div").style(
            "overflow-y:auto;max-height:calc(100vh - 160px);scrollbar-width:thin;"
        ):
            for entry in entries:
                eid = entry.get("id", "")
                etype = entry.get("type", "complaint")
                from_a = entry.get("from", "?")
                to_a = entry.get("to", "?")
                text = entry.get("text", "")
                ts_raw = entry.get("ts", "")
                gardener_note = entry.get("gardener_note")
                gardener_action_done = entry.get("gardener_action")
                is_expanded = (expanded_entry["id"] == eid)

                # Форматируем время
                time_str = ""
                try:
                    from datetime import datetime as _dt
                    time_str = _dt.fromisoformat(ts_raw).strftime("%d %b · %H:%M")
                except Exception:
                    time_str = ts_raw[:16]

                # Цвета по типу
                if etype == "complaint":
                    icon = "🗡"
                    border_color = "rgba(220,100,100,0.2)"
                    bg_color = "rgba(220,100,100,0.04)"
                    name_color = "rgba(220,120,120,0.9)"
                    arrow = "→"
                else:
                    icon = "🌱"
                    border_color = "rgba(80,200,140,0.2)"
                    bg_color = "rgba(80,200,140,0.04)"
                    name_color = "rgba(80,200,140,0.9)"
                    arrow = "→"

                # Метки действия Садовника
                action_done_html = ""
                if gardener_action_done:
                    action_icons = {
                        "mediate": "⚖️", "protect": "🛡",
                        "amplify": "🌟", "release": "🌊"
                    }
                    action_done_html = (
                        f'<span style="color:rgba(212,175,55,0.6);font-size:0.5rem;">'
                        f' {action_icons.get(gardener_action_done, "✓")}</span>'
                    )

                gardener_html = ""
                if gardener_note:
                    gardener_html = (
                        f'<div style="margin-top:6px;padding:6px 8px;'
                        f'background:rgba(212,175,55,0.06);'
                        f'border-left:2px solid rgba(212,175,55,0.3);'
                        f'border-radius:4px;'
                        f'font-family:JetBrains Mono;font-size:0.58rem;'
                        f'color:rgba(240,225,180,0.75);">'
                        f'🌱 Садовник: {gardener_note[:200]}'
                        f'</div>'
                    )

                active_bg = "background:rgba(108,140,255,0.05);" if is_expanded else ""

                with ui.element("div").style(
                    f"padding:8px 10px;cursor:pointer;"
                    f"border-bottom:1px solid rgba(255,255,255,0.035);"
                    f"border-left:2px solid {border_color};"
                    f"background:{bg_color};{active_bg}"
                ).on("click", lambda _e=None, _id=eid: _toggle_entry(_id)):

                    # Строка 1: иконка + агенты + время
                    ui.html(
                        f'<div style="display:flex;justify-content:space-between;'
                        f'align-items:center;gap:6px;">'
                        f'<span style="font-family:JetBrains Mono;font-size:0.62rem;'
                        f'color:{name_color};">'
                        f'{icon} {from_a} {arrow} {to_a}'
                        f'{action_done_html}</span>'
                        f'<span style="font-family:JetBrains Mono;font-size:0.5rem;'
                        f'color:rgba(140,150,180,0.4);flex-shrink:0;">'
                        f'{time_str}</span>'
                        f'</div>'
                    )

                    # Строка 2: текст агента
                    if text:
                        ui.html(
                            f'<div style="font-family:JetBrains Mono;font-size:0.65rem;'
                            f'color:rgba(200,205,220,0.8);margin-top:4px;'
                            f'line-height:1.4;font-style:italic;">'
                            f'«{text[:180]}»</div>'
                        )

                    # Метка Садовника если уже есть
                    if gardener_note:
                        ui.html(gardener_html)

                # Развёрнутая секция — поле ввода + кнопки действий
                if is_expanded:
                    with ui.element("div").style(
                        "padding:8px 10px 12px;"
                        "background:rgba(20,23,34,0.6);"
                        "border-bottom:1px solid rgba(99,130,255,0.08);"
                    ):
                        # Полный текст
                        if len(text) > 180:
                            ui.html(
                                f'<div style="font-family:JetBrains Mono;font-size:0.62rem;'
                                f'color:rgba(200,205,220,0.7);margin-bottom:8px;'
                                f'line-height:1.45;font-style:italic;">'
                                f'«{text}»</div>'
                            )

                        # Триггер
                        trigger = entry.get("trigger", "")
                        if trigger:
                            ui.html(
                                f'<div style="font-family:JetBrains Mono;font-size:0.52rem;'
                                f'color:rgba(140,150,180,0.4);margin-bottom:10px;">'
                                f'причина: {trigger[:120]}</div>'
                            )

                        # Кнопки действий (зависят от типа)
                        with ui.row().style("gap:6px;margin-bottom:10px;flex-wrap:wrap;"):
                            if etype == "complaint":
                                action_btns = [
                                    ("mediate", "⚖️ помирить"),
                                    ("protect", "🛡 защитить"),
                                    ("release", "🌊 отпустить"),
                                ]
                            else:
                                action_btns = [
                                    ("amplify", "🌟 усилить"),
                                    ("release", "🌊 просто увидеть"),
                                ]

                            for act_id, act_label in action_btns:
                                already = (gardener_action_done == act_id)
                                ui.button(
                                    act_label,
                                    on_click=lambda _e=None, _a=act_id, _eid=eid: _do_action(_eid, _a)
                                ).props("flat dense no-caps").style(
                                    "font-family:JetBrains Mono;font-size:0.58rem;"
                                    "border-radius:5px;padding:4px 10px;"
                                    + (
                                        "background:rgba(212,175,55,0.12);"
                                        "color:#d4af37;border:1px solid rgba(212,175,55,0.25);"
                                        if already else
                                        "background:rgba(99,130,255,0.06);"
                                        "color:rgba(180,190,220,0.6);"
                                        "border:1px solid rgba(99,130,255,0.12);"
                                    )
                                )

                        # Поле реплики Садовника
                        ui.html(
                            '<div style="font-family:JetBrains Mono;font-size:0.52rem;'
                            'color:rgba(140,150,180,0.4);margin-bottom:4px;">'
                            '🌱 написать агентам (они прочитают дома в кабинете):</div>'
                        )
                        with ui.row().style("gap:6px;align-items:flex-end;width:100%;"):
                            note_inp = ui.textarea(
                                placeholder="твоя реплика..."
                            ).props("borderless autogrow").style(
                                "flex:1;background:#0d0f1a;"
                                "border:1px solid rgba(212,175,55,0.12);"
                                "border-radius:5px;"
                                "color:rgba(240,225,180,0.9);"
                                "font-family:JetBrains Mono;font-size:0.72rem;"
                                "padding:7px 10px;min-height:36px;max-height:80px;"
                            )
                            ui.button(
                                "🌱",
                                on_click=lambda _e=None, _eid=eid, _ni=note_inp: _send_note(_eid, _ni)
                            ).style(
                                "background:rgba(212,175,55,0.08);"
                                "border:1px solid rgba(212,175,55,0.2);"
                                "color:#d4af37;font-size:0.8rem;"
                                "border-radius:5px;padding:7px 12px;height:36px;"
                            )

    def _render_chronicles_tab():'''


def patch():
    if not UI_PATH.exists():
        print(f"❌ Файл не найден: {UI_PATH}")
        return False

    content = UI_PATH.read_text(encoding="utf-8")

    if "BOOK_PATCH" in content:
        print("✅ Патч уже применён — пропускаем")
        return True

    errors = []

    # Патч 1: вкладки
    if ANCHOR_TABS in content:
        content = content.replace(ANCHOR_TABS, NEW_TABS)
        print("  ✓ Патч 1: вкладка «книга» добавлена в список")
    else:
        errors.append("Патч 1: якорь вкладок не найден")

    # Патч 2: панели
    if ANCHOR_PANELS in content:
        content = content.replace(ANCHOR_PANELS, NEW_PANELS)
        print("  ✓ Патч 2: панель «книга» добавлена")
    else:
        errors.append("Патч 2: якорь панелей не найден")

    # Патч 3: update_right_panel
    if ANCHOR_UPDATE in content and "BOOK_PATCH:update_right_panel" not in content:
        content = content.replace(ANCHOR_UPDATE, NEW_UPDATE)
        print("  ✓ Патч 3: ветка update_right_panel добавлена")
    else:
        errors.append("Патч 3: якорь update_right_panel не найден или уже есть")

    # Патч 4: switch_tab
    if ANCHOR_SWITCH in content and "BOOK_PATCH:switch_tab" not in content:
        content = content.replace(ANCHOR_SWITCH, NEW_SWITCH)
        print("  ✓ Патч 4: switch_tab кейс добавлен")
    else:
        errors.append("Патч 4: якорь switch_tab не найден или уже есть")

    # Патч 5: функция _render_book_tab
    if ANCHOR_FUNC in content and "_render_book_tab" not in content:
        content = content.replace(ANCHOR_FUNC, BOOK_FUNC)
        print("  ✓ Патч 5: функция _render_book_tab добавлена")
    else:
        errors.append("Патч 5: якорь функции не найден или уже есть")

    if errors:
        print("\n⚠ Некоторые патчи не применились:")
        for e in errors:
            print(f"   - {e}")
        if len(errors) == 5:
            print("❌ Ни один патч не применился — проверь файл вручную")
            return False

    UI_PATH.write_text(content, encoding="utf-8")
    applied = 5 - len(errors)
    print(f"\n✅ Применено патчей: {applied}/5 → {UI_PATH}")
    return True


if __name__ == "__main__":
    print("Патч: вкладка «Книга» в ui_cabinet.py")
    print("─" * 45)
    ok = patch()
    if ok:
        print("\nВкладка «книга» появится в правой панели Кабинета.")
        print("Записи появятся после первого рана с QA.")
    else:
        print("\n⚠ Патч не завершён — проверь вывод выше")
