"""
patch_council_tiles.py
======================
Добавляет плитки резидентов в render_council_grid.
Запуск: python patch_council_tiles.py
"""

import shutil
import subprocess
from pathlib import Path

DASHBOARD = Path("studio/economy/ui_dashboard.py")

OLD_MARKER = '    def render_council_grid():\n        """Центральная область в режиме Совета."""'

NEW_FUNC = '''    def render_council_grid():
        """Центральная область в режиме Совета — плитки + чат."""
        el = refs["metrics_grid"]
        if not el:
            return
        el.clear()
        el.style(
            "display:flex;flex-direction:column;"
            "gap:0;margin:0;flex:1;min-height:0;"
        )
        with el:
            # ── Четыре плитки резидентов вверху ──────────────────────
            with ui.element("div").style(
                "display:grid;grid-template-columns:repeat(4,1fr);"
                "gap:12px;padding:16px 20px 12px;flex-shrink:0;"
                "border-bottom:1px solid rgba(99,130,255,0.08);"
            ):
                for _res in COUNCIL_RESIDENTS:
                    _rid   = _res["id"]
                    _label = _res["label"]
                    _emoji = _res["emoji"]
                    _color = _res["color"]
                    _ava   = _get_council_avatar(_rid)
                    _sel   = (state.get("council_resident") or {}).get("id") == _rid
                    _border = "2px solid " + _color if _sel else "1px solid rgba(99,130,255,0.12)"
                    _bg     = "rgba(99,130,255,0.10)" if _sel else "rgba(99,130,255,0.04)"
                    _tile_style = (
                        "display:flex;flex-direction:column;align-items:center;"
                        "justify-content:center;padding:10px 6px;"
                        "background:" + _bg + ";border:" + _border + ";"
                        "border-radius:8px;cursor:pointer;"
                    )
                    _tile = ui.element("div").style(_tile_style)
                    _tile.on("click", lambda _, r=_res: select_council_resident(r))
                    with _tile:
                        if _ava:
                            _img_style = (
                                "width:44px;height:44px;border-radius:50%;"
                                "background-image:url('" + _ava + "');"
                                "background-size:cover;background-position:center;"
                                "margin-bottom:6px;border:2px solid " + _color + "44;"
                            )
                            ui.html("<div style='" + _img_style + "'></div>")
                        else:
                            ui.html("<div style='font-size:1.6rem;margin-bottom:4px;'>" + _emoji + "</div>")
                        _lbl_style = (
                            "font-family:JetBrains Mono;font-size:0.6rem;"
                            "color:" + _color + ";font-weight:600;text-align:center;"
                        )
                        ui.html("<div style='" + _lbl_style + "'>" + _label + "</div>")

            # ── Поле ввода ────────────────────────────────────────────
            with ui.element("div").style(
                "padding:12px 20px 8px;flex-shrink:0;"
                "border-bottom:1px solid rgba(99,130,255,0.08);"
            ):
                with ui.row().style("gap:8px;align-items:flex-end;width:100%;"):
                    refs["council_input"] = ui.textarea(
                        placeholder="задай вопрос выбранному резиденту..."
                    ).props("borderless autogrow").style(
                        "flex:1;background:#141722;"
                        "border:1px solid rgba(99,130,255,0.08);"
                        "border-radius:6px;color:rgba(220,225,240,0.92);"
                        "font-family:JetBrains Mono;font-size:0.8rem;"
                        "padding:8px 12px;min-height:44px;max-height:100px;"
                    )
                    refs["council_input"].on(
                        "keydown.ctrl.enter",
                        lambda e: send_council_message()
                    )
                    ui.button(
                        "▶ спросить",
                        on_click=send_council_message,
                    ).style(
                        "background:rgba(108,140,255,0.12);"
                        "border:1px solid rgba(108,140,255,0.2);"
                        "color:#6c8cff;font-family:JetBrains Mono;"
                        "font-size:0.65rem;padding:8px 16px;"
                        "border-radius:6px;height:36px;"
                    )
                ui.html(
                    "<div style='font-family:JetBrains Mono;font-size:0.5rem;"
                    "color:rgba(140,150,180,0.3);margin-top:4px;'>"
                    "Ctrl+Enter · выбери резидента выше</div>"
                )

            refs["council_chat_el"] = ui.element("div").classes(
                "council-chat-scroll"
            ).style(
                "flex:1;overflow-y:auto;padding:12px 20px;"
                "scrollbar-width:thin;"
            )
            render_council_chat()'''


def patch():
    if not DASHBOARD.exists():
        print(f"  ❌ {DASHBOARD} не найден")
        return False

    src = DASHBOARD.read_text(encoding="utf-8")

    if "grid-template-columns:repeat(4,1fr)" in src:
        print("  ⚠  Плитки уже есть")
        return True

    if OLD_MARKER not in src:
        print("  ❌ Маркер render_council_grid не найден")
        return False

    # Находим конец функции — следующая def на том же уровне отступа
    idx = src.index(OLD_MARKER)
    # Ищем следующую функцию после render_council_grid
    next_def = src.find("\n    async def send_council_message", idx)
    if next_def == -1:
        next_def = src.find("\n    async def _council_talk_with_text", idx)
    if next_def == -1:
        print("  ❌ Конец функции не найден")
        return False

    old_func = src[idx:next_def]
    src = src.replace(old_func, NEW_FUNC)
    DASHBOARD.write_text(src, encoding="utf-8")
    print("  ✅ render_council_grid заменена")
    return True


def main():
    print("\n🎴 ПАТЧ: Плитки резидентов в Совете")
    print("=" * 42)

    bak = DASHBOARD.with_suffix(".py.bak3")
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
        print("\nПерезапусти студию → Дашборд → Совет")
        print("Вверху центра: 🌿 Лока  🎯 Джем  📊 Кей  ⚖️ Юст")
    else:
        print(f"❌ Ошибка:\n{result.stderr}")
        shutil.copy2(bak, DASHBOARD)
        print("↩ Бэкап восстановлен")


if __name__ == "__main__":
    main()
