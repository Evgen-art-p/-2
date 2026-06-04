"""
patch_council_v3.py
===================
Полная переработка render_council_grid():
  1. Поле ввода — внизу, чат — занимает основное место
  2. Плитки — кликабельны (убран pointer-events баг)
  3. Эмодзи показываются у всех без аватара
  4. Карточка не исчезает при update_all()

Запуск: python patch_council_v3.py
"""

import shutil
import subprocess
from pathlib import Path

DASHBOARD = Path("studio/economy/ui_dashboard.py")

# Находим и заменяем всю render_council_grid целиком
OLD_MARKER = "    def render_council_grid():"
NEXT_FUNC  = "\n    async def send_council_message():"

NEW_GRID = '''    def render_council_grid():
        """Центральная область Совета: плитки → чат → поле ввода внизу."""
        el = refs["metrics_grid"]
        if not el:
            return
        el.clear()
        el.style(
            "display:flex;flex-direction:column;"
            "gap:0;margin:0;flex:1;min-height:0;overflow:hidden;"
        )
        with el:
            # ── Плитки резидентов ─────────────────────────────────────
            with ui.element("div").style(
                "display:grid;grid-template-columns:repeat(4,1fr);"
                "gap:10px;padding:14px 20px 12px;flex-shrink:0;"
                "border-bottom:1px solid rgba(99,130,255,0.08);"
            ):
                for _res in COUNCIL_RESIDENTS:
                    _rid   = _res["id"]
                    _label = _res["label"]
                    _emoji = _res["emoji"]
                    _color = _res["color"]
                    _ava   = _get_council_avatar(_rid)
                    _sel   = (state.get("council_resident") or {}).get("id") == _rid
                    _bdr   = "1px solid " + _color + "99" if _sel else "1px solid rgba(99,130,255,0.12)"
                    _bg    = "rgba(99,130,255,0.08)" if _sel else "rgba(99,130,255,0.03)"

                    with ui.element("div").style(
                        "display:flex;flex-direction:column;align-items:center;"
                        "justify-content:center;padding:10px 6px;"
                        "background:" + _bg + ";border:" + _bdr + ";"
                        "border-radius:8px;cursor:pointer;user-select:none;"
                        "min-height:80px;"
                    ).on("click", lambda _, r=_res: (
                        select_council_resident(r),
                        render_council_grid(),
                    )):
                        if _ava:
                            ui.html(
                                "<div style='width:40px;height:40px;border-radius:50%;"
                                "background-image:url(\"" + _ava + "\");"
                                "background-size:cover;background-position:center;"
                                "margin-bottom:5px;flex-shrink:0;'></div>"
                            )
                        else:
                            ui.html(
                                "<div style='font-size:1.5rem;margin-bottom:5px;"
                                "line-height:1;'>" + _emoji + "</div>"
                            )
                        ui.html(
                            "<div style='font-family:JetBrains Mono;font-size:0.58rem;"
                            "color:" + _color + ";font-weight:500;"
                            "text-align:center;line-height:1.2;'>" + _label + "</div>"
                        )

            # ── Лента чата ────────────────────────────────────────────
            refs["council_chat_el"] = ui.element("div").classes(
                "council-chat-scroll"
            ).style(
                "flex:1;overflow-y:auto;padding:12px 20px;"
                "scrollbar-width:thin;min-height:0;"
            )
            render_council_chat()

            # ── Поле ввода внизу ──────────────────────────────────────
            with ui.element("div").style(
                "padding:10px 20px 14px;flex-shrink:0;"
                "border-top:1px solid rgba(99,130,255,0.08);"
                "background:rgba(20,23,34,0.6);"
            ):
                with ui.row().style("gap:8px;align-items:flex-end;width:100%;"):
                    refs["council_input"] = ui.textarea(
                        placeholder="задай вопрос резиденту... (выбери плитку выше)"
                    ).props("borderless autogrow").style(
                        "flex:1;background:#141722;"
                        "border:1px solid rgba(99,130,255,0.10);"
                        "border-radius:6px;color:rgba(220,225,240,0.92);"
                        "font-family:JetBrains Mono;font-size:0.78rem;"
                        "padding:8px 12px;min-height:42px;max-height:90px;"
                    )
                    refs["council_input"].on(
                        "keydown.ctrl.enter",
                        lambda e: send_council_message()
                    )
                    ui.button(
                        "▶",
                        on_click=send_council_message,
                    ).style(
                        "background:rgba(108,140,255,0.12);"
                        "border:1px solid rgba(108,140,255,0.2);"
                        "color:#6c8cff;font-family:JetBrains Mono;"
                        "font-size:0.7rem;padding:8px 14px;"
                        "border-radius:6px;height:36px;flex-shrink:0;"
                    )
                ui.html(
                    "<div style='font-family:JetBrains Mono;font-size:0.48rem;"
                    "color:rgba(140,150,180,0.3);margin-top:3px;'>"
                    "Ctrl+Enter — отправить</div>"
                )
'''


def patch():
    if not DASHBOARD.exists():
        print("  ❌ ui_dashboard.py не найден")
        return False

    src = DASHBOARD.read_text(encoding="utf-8")

    if OLD_MARKER not in src:
        print("  ❌ render_council_grid не найдена")
        return False

    # Вырезаем старую функцию
    idx_start = src.index(OLD_MARKER)
    idx_end   = src.find(NEXT_FUNC, idx_start)
    if idx_end == -1:
        print("  ❌ Конец функции не найден")
        return False

    old_func = src[idx_start:idx_end]
    src = src.replace(old_func, NEW_GRID)
    print("  ✅ render_council_grid() переписана")

    # Защищаем render_detail() от Совета
    DETAIL_CHECK = 'if state.get("center_view") == "council":\n            return'
    if DETAIL_CHECK not in src:
        OLD_D = ('        el.clear()\n\n'
                 '        aid = state["selected_agent"]')
        NEW_D = ('        if state.get("center_view") == "council":\n'
                 '            return\n'
                 '        el.clear()\n\n'
                 '        aid = state["selected_agent"]')
        if OLD_D in src:
            src = src.replace(OLD_D, NEW_D, 1)
            print("  ✅ render_detail() защищена")
    else:
        print("  ✅ render_detail() уже защищена")

    DASHBOARD.write_text(src, encoding="utf-8")
    return True


def main():
    print("\n🔧 ПАТЧ v3: Совет — полная переработка")
    print("=" * 44)

    bak = DASHBOARD.with_suffix(".py.bak5")
    shutil.copy2(DASHBOARD, bak)
    print(f"📦 Бэкап: {bak}")

    ok = patch()
    if not ok:
        return

    result = subprocess.run(
        ["python", "-m", "py_compile", str(DASHBOARD)],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        print("✅ Синтаксис OK")
        print()
        print("Перезапусти студию → Дашборд → Совет:")
        print("  · Плитки кликабельны")
        print("  · Чат сверху, поле ввода снизу")
        print("  · У Локи и Джема аватары, у Кея/Юста эмодзи")
        print("  · Карточка не исчезает")
    else:
        print(f"❌ Ошибка:\n{result.stderr}")
        shutil.copy2(bak, DASHBOARD)
        print("↩ Бэкап восстановлен")


if __name__ == "__main__":
    main()
