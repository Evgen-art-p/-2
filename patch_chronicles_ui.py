"""
patch_chronicles_ui.py
─────────────────────────────────────────────────────────────
Спринт 23 Блок Б · UI для встреч в Кабинете

Что делает:
  1. Копирует chronicles.py → studio/cabinet/chronicles.py
  2. Патчит studio/cabinet/ui_cabinet.py:
       • импорт chronicles
       • вкладка "хроники" в правой панели (рядом с агент/матрица/файлы/промпты/архив)
       • рендер списка хроник
       • центр-вид одной сцены (групповой чат)
       • реплика Садовника → агенты отвечают → шлейф в память
  3. Создаёт city_chronicles/ если ещё нет

Запуск:
    python patch_chronicles_ui.py

Идемпотентен: можно гонять повторно — пропустит уже применённые изменения.
"""

import re
import sys
import shutil
from pathlib import Path

REPO = Path(__file__).resolve().parent
UI_PATH         = REPO / "studio" / "cabinet" / "ui_cabinet.py"
CHRONICLES_DST  = REPO / "studio" / "cabinet" / "chronicles.py"
CHRONICLES_SRC  = REPO / "chronicles.py"           # рядом с патчем
CITY_CHRON_DIR  = REPO / "studio" / "city_chronicles"


# ═══════════════════════════════════════════════════════════
# ШАГ 0. Подготовка путей
# ═══════════════════════════════════════════════════════════

def step_paths():
    print("─" * 60)
    print("ШАГ 0. Проверка путей")
    print("─" * 60)
    assert UI_PATH.exists(), f"❌ Не найден {UI_PATH}"
    assert CHRONICLES_SRC.exists(), (
        f"❌ Не найден {CHRONICLES_SRC}. Положи chronicles.py рядом с патчем."
    )
    CITY_CHRON_DIR.mkdir(parents=True, exist_ok=True)
    print(f"✓ {UI_PATH}")
    print(f"✓ {CHRONICLES_SRC}")
    print(f"✓ {CITY_CHRON_DIR}/ (создана если не было)")


# ═══════════════════════════════════════════════════════════
# ШАГ 1. Установить chronicles.py в кабинет
# ═══════════════════════════════════════════════════════════

def step_install_chronicles():
    print()
    print("─" * 60)
    print("ШАГ 1. Установка studio/cabinet/chronicles.py")
    print("─" * 60)
    shutil.copy2(CHRONICLES_SRC, CHRONICLES_DST)
    print(f"✓ Скопирован: {CHRONICLES_DST}")


# ═══════════════════════════════════════════════════════════
# ШАГ 2. Патч ui_cabinet.py
# ═══════════════════════════════════════════════════════════

# Все блоки помечены маркерами `# === CHRONICLES_PATCH:NAME ===` —
# повторный запуск патча видит их и пропускает.


def _ensure_block(src: str, marker: str, block: str, anchor_after: str) -> tuple[str, bool]:
    """
    Если в src нет marker — вставить block после строки, содержащей anchor_after.
    Возвращает (новый_src, было_ли_изменение).
    """
    if marker in src:
        return src, False

    lines = src.splitlines(keepends=True)
    new_lines = []
    inserted = False
    for line in lines:
        new_lines.append(line)
        if not inserted and anchor_after in line:
            new_lines.append(block if block.endswith("\n") else block + "\n")
            inserted = True

    if not inserted:
        raise RuntimeError(
            f"❌ Якорь не найден для {marker}: '{anchor_after[:60]}...'"
        )

    return "".join(new_lines), True


def _replace_block(src: str, marker: str, old_pattern: str, new_block: str) -> tuple[str, bool]:
    """
    Заменить участок по регулярке (один раз). Если marker уже есть — пропустить.
    """
    if marker in src:
        return src, False
    new_src, n = re.subn(old_pattern, new_block, src, count=1)
    if n == 0:
        raise RuntimeError(f"❌ Паттерн не найден для {marker}: {old_pattern[:80]}")
    return new_src, True


def step_patch_ui():
    print()
    print("─" * 60)
    print("ШАГ 2. Патч studio/cabinet/ui_cabinet.py")
    print("─" * 60)

    src = UI_PATH.read_text(encoding="utf-8")
    original = src
    changes = []

    # ───────────────────────────────────────────────
    # 2.1 ИМПОРТ chronicles
    # ───────────────────────────────────────────────
    IMPORT_MARKER = "# === CHRONICLES_PATCH:import ==="
    import_block = (
        "\n# === CHRONICLES_PATCH:import ===\n"
        "from studio.cabinet.chronicles import (\n"
        "    list_chronicles, load_chronicle, gardener_reply_to_scene,\n"
        ")\n"
        "# === END CHRONICLES_PATCH:import ===\n"
    )
    src, ch = _ensure_block(
        src, IMPORT_MARKER, import_block,
        anchor_after="from studio.modules_registry import CURRENT_DEPT",
    )
    changes.append(("импорт chronicles", ch))

    # ───────────────────────────────────────────────
    # 2.2 STATE — добавить chronicle и chronicle_input
    # ───────────────────────────────────────────────
    STATE_MARKER = "# === CHRONICLES_PATCH:state ==="
    if STATE_MARKER not in src:
        state_old = '"active_tab": "agent",\n    }'
        state_new = (
            '"active_tab": "agent",\n'
            '        # === CHRONICLES_PATCH:state ===\n'
            '        "chronicle": None,            # открытая хроника (dict сцены)\n'
            '        "chronicle_file": None,       # путь к файлу хроники\n'
            '        "chronicle_sending": False,   # идёт ли отправка реплики\n'
            '        # === END CHRONICLES_PATCH:state ===\n'
            '    }'
        )
        if state_old in src:
            src = src.replace(state_old, state_new, 1)
            changes.append(("state.chronicle", True))
        else:
            print("  ⚠ state-анкор не найден — пропускаю (возможно уже патчили иначе)")
            changes.append(("state.chronicle", False))
    else:
        changes.append(("state.chronicle", False))

    # ───────────────────────────────────────────────
    # 2.3 REFS — добавить chronicle_view и chronicle_input
    # ───────────────────────────────────────────────
    REFS_MARKER = "# === CHRONICLES_PATCH:refs ==="
    if REFS_MARKER not in src:
        refs_old = '"right_tabs": {}, "right_panels": {},\n    }'
        refs_new = (
            '"right_tabs": {}, "right_panels": {},\n'
            '        # === CHRONICLES_PATCH:refs ===\n'
            '        "chronicle_wrap": None,   # центр-обёртка вида хроники\n'
            '        "chronicle_body": None,   # лента реплик\n'
            '        "chronicle_input": None,  # textarea реплики Садовника\n'
            '        "chronicle_header": None, # хедер сцены\n'
            '        # === END CHRONICLES_PATCH:refs ===\n'
            '    }'
        )
        if refs_old in src:
            src = src.replace(refs_old, refs_new, 1)
            changes.append(("refs.chronicle", True))
        else:
            print("  ⚠ refs-анкор не найден")
            changes.append(("refs.chronicle", False))
    else:
        changes.append(("refs.chronicle", False))

    # ───────────────────────────────────────────────
    # 2.4 ФУНКЦИИ ХРОНИК — вставить блок функций перед "# ═══ LAYOUT ═══"
    # ───────────────────────────────────────────────
    FNS_MARKER = "# === CHRONICLES_PATCH:functions ==="
    fns_block = '''
    # === CHRONICLES_PATCH:functions ===
    # ─────────────────────────────────────────────────────
    # ХРОНИКИ ВСТРЕЧ · Спринт 23 Блок Б
    # ─────────────────────────────────────────────────────

    def _format_chronicle_time(item):
        date = item.get("date", "")
        time = item.get("time", "")
        # Сегодня → "сегодня 14:22"; вчера → "вчера 14:22"; иначе → "28 мая 14:22"
        try:
            d = datetime.strptime(date, "%Y-%m-%d").date()
            today = datetime.now().date()
            delta = (today - d).days
            if delta == 0:
                prefix = "сегодня"
            elif delta == 1:
                prefix = "вчера"
            else:
                months = ["янв","фев","мар","апр","май","июн",
                          "июл","авг","сен","окт","ноя","дек"]
                prefix = f"{d.day} {months[d.month-1]}"
            return f"{prefix} {time}" if time else prefix
        except Exception:
            return f"{date} {time}".strip()

    LOC_ICONS = {
        "tavern": "🍺", "square": "🏛", "lighthouse": "🪔",
        "library": "📚", "harbor": "⚓", "castle": "🦉",
        "temple": "🕯", "pavilion": "⏳", "workshop": "🔧",
        "home": "🏠", "other": "📍",
    }

    INTERACTION_LABELS = {
        "collaboration": ("сотрудничество", "rgba(140,200,140,0.7)"),
        "praise":        ("благодарность", "rgba(220,180,90,0.8)"),
        "rescue":        ("спасение",      "rgba(120,200,255,0.8)"),
        "critique":      ("критика",       "rgba(200,160,90,0.7)"),
        "conflict":      ("конфликт",      "rgba(220,100,100,0.8)"),
    }

    def _render_chronicles_tab():
        """Список хроник в правой панели."""
        items = list_chronicles(limit=80)
        ui.html(
            f'<div style="padding:4px 8px;font-family:JetBrains Mono;'
            f'font-size:0.52rem;color:rgba(140,150,180,0.35);margin-bottom:4px">'
            f'встреч записано: {len(items)}'
            f'</div>'
        )
        if not items:
            ui.html(
                '<div style="text-align:center;padding:24px;'
                'font-family:JetBrains Mono;font-size:0.56rem;'
                'color:rgba(140,150,180,0.3)">'
                'хроник пока нет<br>'
                '<span style="font-size:0.5rem;color:rgba(140,150,180,0.2)">'
                'агенты встретятся во время прогулок</span>'
                '</div>'
            )
            return

        is_open = state.get("chronicle_file", "")

        for item in items:
            icon = LOC_ICONS.get(item.get("loc_type", "other"), "📍")
            participants = " · ".join(item["participants"][:2])
            inter_type = item.get("interaction", "")
            inter_label, inter_color = INTERACTION_LABELS.get(
                inter_type, ("", "rgba(140,150,180,0.35)")
            )
            gardener_mark = " 🌱" if item.get("has_gardener") else ""

            is_active = (item["file"] == is_open)
            active_bg = "background:rgba(108,140,255,0.07);" if is_active else ""
            active_border = (
                "border-left:2px solid rgba(108,140,255,0.6);"
                if is_active else "border-left:2px solid transparent;"
            )

            with ui.element("div").classes("cab-chronicle-item").style(
                f"padding:7px 10px;cursor:pointer;"
                f"border-bottom:1px solid rgba(255,255,255,0.035);"
                f"{active_bg}{active_border}"
            ).on("click", lambda _e=None, _f=item["file"]: open_chronicle(_f)):

                # Строка 1: иконка + локация + время
                ui.html(
                    f'<div style="display:flex;justify-content:space-between;'
                    f'align-items:center;gap:6px;">'
                    f'<span style="font-family:JetBrains Mono;font-size:0.62rem;'
                    f'color:rgba(220,225,240,0.85);overflow:hidden;'
                    f'text-overflow:ellipsis;white-space:nowrap;">'
                    f'{icon} {item["location"]}{gardener_mark}</span>'
                    f'<span style="font-family:JetBrains Mono;font-size:0.5rem;'
                    f'color:rgba(140,150,180,0.4);flex-shrink:0;">'
                    f'{_format_chronicle_time(item)}</span>'
                    f'</div>'
                )
                # Строка 2: участники
                ui.html(
                    f'<div style="font-family:JetBrains Mono;font-size:0.56rem;'
                    f'color:rgba(180,190,220,0.55);margin-top:2px;">'
                    f'{participants}</div>'
                )
                # Строка 3: тип + кол-во реплик
                meta_parts = []
                if inter_label:
                    meta_parts.append(
                        f'<span style="color:{inter_color}">{inter_label}</span>'
                    )
                meta_parts.append(
                    f'<span style="color:rgba(140,150,180,0.35)">'
                    f'{item.get("spoken", 0)} реплик</span>'
                )
                ui.html(
                    f'<div style="font-family:JetBrains Mono;font-size:0.5rem;'
                    f'margin-top:2px;">{" · ".join(meta_parts)}</div>'
                )

    def open_chronicle(file_path):
        """Открыть хронику в центре (вместо карты/чата)."""
        scene = load_chronicle(file_path)
        if not scene:
            ui.notify("Хроника не загружается", type="negative")
            return
        state["chronicle"] = scene
        state["chronicle_file"] = file_path

        # Спрятать карту, чат, поле ввода чата
        _hide_map()
        if refs.get("chat"):
            refs["chat"].style("display: none")
        if refs.get("input_area"):
            refs["input_area"].style("display: none")
        if refs.get("prompt_bar"):
            refs["prompt_bar"].style("display: none")
        if refs.get("back_btn"):
            refs["back_btn"].classes(remove="visible")

        # Показать вид хроники
        if refs.get("chronicle_wrap"):
            refs["chronicle_wrap"].style("display: flex")

        _render_chronicle_view()
        # Подсветить активную в списке справа
        update_right_panel("chronicles")

    def close_chronicle():
        """Закрыть хронику и вернуться к карте."""
        state["chronicle"] = None
        state["chronicle_file"] = None
        if refs.get("chronicle_wrap"):
            refs["chronicle_wrap"].style("display: none")
        _show_map()
        update_right_panel("chronicles")

    def _render_chronicle_view():
        """Рендер открытой хроники в центре: хедер + лента реплик + поле ввода."""
        scene = state.get("chronicle")
        if not scene:
            return

        # ── Хедер ──
        hdr = refs.get("chronicle_header")
        if hdr:
            hdr.clear()
            with hdr:
                loc = scene.get("location", "—")
                loc_type = scene.get("location_type", "other")
                icon = LOC_ICONS.get(loc_type, "📍")
                weather = scene.get("weather", "")
                ended = scene.get("ended_reason", "")
                p = scene.get("participants", {})
                a_name = p.get("a", {}).get("name", "?")
                b_name = p.get("b", {}).get("name", "?")

                started = scene.get("started_at", "")
                time_str = ""
                if started:
                    try:
                        time_str = datetime.fromisoformat(started).strftime("%d %b · %H:%M")
                    except Exception:
                        pass

                with ui.row().style("align-items:center;gap:10px;width:100%;"):
                    ui.html(
                        f'<div style="font-family:JetBrains Mono;font-size:0.85rem;'
                        f'color:rgba(220,225,240,0.95);font-weight:500;">'
                        f'{icon} {loc}</div>'
                    )
                    ui.html(
                        f'<div style="font-family:JetBrains Mono;font-size:0.62rem;'
                        f'color:rgba(140,150,180,0.5);">'
                        f'{a_name} · {b_name}</div>'
                    )
                    ui.element("div").style("flex:1")
                    if time_str:
                        ui.html(
                            f'<div style="font-family:JetBrains Mono;font-size:0.58rem;'
                            f'color:rgba(140,150,180,0.4);">{time_str}</div>'
                        )
                    ui.button("✕", on_click=lambda: close_chronicle()).props(
                        "flat dense"
                    ).style(
                        "color:rgba(180,190,220,0.5);min-width:28px;font-size:0.7rem;"
                        "background:transparent;"
                    )

                meta_parts = []
                if weather:
                    meta_parts.append(f"☁ {weather}")
                if ended:
                    meta_parts.append(ended)
                if meta_parts:
                    ui.html(
                        f'<div style="font-family:JetBrains Mono;font-size:0.56rem;'
                        f'color:rgba(140,150,180,0.4);margin-top:4px;">'
                        f'{" · ".join(meta_parts)}</div>'
                    )

        # ── Лента реплик ──
        body = refs.get("chronicle_body")
        if body:
            body.clear()
            dialogue = scene.get("dialogue", [])
            with body:
                if not dialogue:
                    ui.html(
                        '<div style="text-align:center;padding:24px;'
                        'font-family:JetBrains Mono;font-size:0.6rem;'
                        'color:rgba(140,150,180,0.3)">пусто</div>'
                    )
                else:
                    p = scene.get("participants", {})
                    a_name = p.get("a", {}).get("name", "?")
                    b_name = p.get("b", {}).get("name", "?")

                    for r in dialogue:
                        speaker = r.get("speaker", "")
                        name    = r.get("speaker_name") or {
                            "a": a_name, "b": b_name, "gardener": "Садовник",
                        }.get(speaker, "?")
                        text    = r.get("text", "")
                        action  = r.get("action", "continue")
                        felt    = r.get("felt", "")

                        # Палитра по говорящему
                        if speaker == "gardener":
                            name_color = "#d4af37"   # золотой
                            text_color = "rgba(240,225,180,0.95)"
                            bg = "rgba(212,175,55,0.05)"
                            border = "rgba(212,175,55,0.18)"
                        elif speaker == "a":
                            name_color = "#6c8cff"
                            text_color = "rgba(220,225,240,0.92)"
                            bg = "rgba(108,140,255,0.04)"
                            border = "rgba(108,140,255,0.12)"
                        else:  # "b"
                            name_color = "#00f2ff"
                            text_color = "rgba(220,225,240,0.92)"
                            bg = "rgba(0,242,255,0.04)"
                            border = "rgba(0,242,255,0.12)"

                        if not text:
                            # Молчание / уход — тихая ремарка
                            action_label = "промолчал" if action == "silent" else "ушёл"
                            ui.html(
                                f'<div style="padding:4px 12px;margin:6px 0;'
                                f'font-family:JetBrains Mono;font-size:0.56rem;'
                                f'color:rgba(140,150,180,0.35);font-style:italic;'
                                f'text-align:center;">'
                                f'— {name} {action_label} —'
                                f'</div>'
                            )
                            continue

                        # Реплика. felt — в title (тултип), не виден по умолчанию
                        felt_attr = (
                            f' title="внутри: {felt}"'
                            if felt else ""
                        )
                        ui.html(
                            f'<div style="padding:8px 12px;margin:6px 0;'
                            f'background:{bg};border:1px solid {border};'
                            f'border-radius:8px;"{felt_attr}>'
                            f'<div style="font-family:JetBrains Mono;font-size:0.58rem;'
                            f'color:{name_color};font-weight:500;margin-bottom:3px;'
                            f'text-transform:uppercase;letter-spacing:1px;">'
                            f'{name}</div>'
                            f'<div style="font-family:JetBrains Mono;font-size:0.78rem;'
                            f'color:{text_color};line-height:1.45;white-space:pre-wrap;">'
                            f'{_escape_html(text)}</div>'
                            f'</div>'
                        )

            # Прокрутка вниз
            ui.run_javascript(
                'const el = document.querySelector(".cab-chronicle-body");'
                'if(el) el.scrollTop = el.scrollHeight;'
            )

    def _escape_html(s):
        return (s.replace("&", "&amp;")
                 .replace("<", "&lt;")
                 .replace(">", "&gt;"))

    async def send_gardener_reply():
        """Отправить реплику Садовника в открытую хронику."""
        inp = refs.get("chronicle_input")
        if not inp:
            return
        text = (inp.value or "").strip()
        if not text or state.get("chronicle_sending"):
            return
        scene_file = state.get("chronicle_file")
        if not scene_file:
            ui.notify("Хроника не выбрана", type="warning")
            return

        state["chronicle_sending"] = True
        inp.set_value("")
        # Показываем "идёт"
        ui.notify("🌱 Садовник входит...", type="info")

        try:
            result = await gardener_reply_to_scene(scene_file, text)
            if not result.get("ok"):
                ui.notify(f"⚠ {result.get('error', '?')}", type="negative")
                return

            # Обновить открытую сцену
            state["chronicle"] = result["scene"]
            _render_chronicle_view()
            reload_all_agents()
            update_residents()
            update_city_zone()
            ui.notify("✓ Шлейф отложен", type="positive")
        except Exception as e:
            import traceback; traceback.print_exc()
            ui.notify(f"⚠ {e}", type="negative")
        finally:
            state["chronicle_sending"] = False

    # === END CHRONICLES_PATCH:functions ===
'''
    src, ch = _ensure_block(
        src, FNS_MARKER, fns_block,
        anchor_after="# ═══ LAYOUT ═══",
    )
    changes.append(("функции хроник", ch))

    # ───────────────────────────────────────────────
    # 2.5 ВКЛАДКА "ХРОНИКИ" в правой панели
    # ───────────────────────────────────────────────
    # Идемпотентность по факту: новый список уже в коде → пропускаем.
    chronicles_tab_marker = '("chronicles","хроники")'
    if chronicles_tab_marker not in src:
        tabs_old = '[("agent","агент"),("matrix","матрица"),("files","файлы"),("prompts","промпты"),("archive","архив")]'
        tabs_new = (
            '[("agent","агент"),("matrix","матрица"),'
            '("chronicles","хроники"),'
            '("files","файлы"),("prompts","промпты"),("archive","архив")]'
        )
        if tabs_old in src:
            src = src.replace(tabs_old, tabs_new, 1)
            changes.append(("вкладка 'хроники'", True))
        else:
            print("  ⚠ tabs-анкор не найден")
            changes.append(("вкладка 'хроники'", False))
    else:
        changes.append(("вкладка 'хроники'", False))

    # ───────────────────────────────────────────────
    # 2.6 СПИСОК ПАНЕЛЕЙ — добавить "chronicles"
    # ───────────────────────────────────────────────
    chronicles_panels_marker = '"agent","matrix","chronicles"'
    if chronicles_panels_marker not in src:
        panels_old = 'for tab_name in ["agent","matrix","files","prompts","archive"]:'
        panels_new = 'for tab_name in ["agent","matrix","chronicles","files","prompts","archive"]:'
        if panels_old in src:
            src = src.replace(panels_old, panels_new, 1)
            changes.append(("panels list", True))
        else:
            print("  ⚠ panels-анкор не найден")
            changes.append(("panels list", False))
    else:
        changes.append(("panels list", False))

    # ───────────────────────────────────────────────
    # 2.7 update_right_panel — обработка вкладки chronicles
    # ───────────────────────────────────────────────
    URP_MARKER = "# === CHRONICLES_PATCH:update_right_panel ==="
    if URP_MARKER not in src:
        urp_old = 'elif tab_name == "archive":\n                _render_archive_tab()'
        urp_new = (
            'elif tab_name == "archive":\n'
            '                _render_archive_tab()\n'
            '            elif tab_name == "chronicles":  '
            '# === CHRONICLES_PATCH:update_right_panel ===\n'
            '                _render_chronicles_tab()'
        )
        if urp_old in src:
            src = src.replace(urp_old, urp_new, 1)
            changes.append(("update_right_panel.chronicles", True))
        else:
            print("  ⚠ urp-анкор не найден")
            changes.append(("update_right_panel.chronicles", False))
    else:
        changes.append(("update_right_panel.chronicles", False))

    # ───────────────────────────────────────────────
    # 2.8 switch_tab — обновлять список хроник при переключении
    # ───────────────────────────────────────────────
    SWT_MARKER = "# === CHRONICLES_PATCH:switch_tab ==="
    if SWT_MARKER not in src:
        swt_old = (
            'if tab_name == "matrix":\n'
            '            reload_all_agents()\n'
            '            update_right_panel("matrix")'
        )
        swt_new = (
            'if tab_name == "matrix":\n'
            '            reload_all_agents()\n'
            '            update_right_panel("matrix")\n'
            '        if tab_name == "chronicles":  '
            '# === CHRONICLES_PATCH:switch_tab ===\n'
            '            update_right_panel("chronicles")'
        )
        if swt_old in src:
            src = src.replace(swt_old, swt_new, 1)
            changes.append(("switch_tab.chronicles", True))
        else:
            print("  ⚠ swt-анкор не найден")
            changes.append(("switch_tab.chronicles", False))
    else:
        changes.append(("switch_tab.chronicles", False))

    # ───────────────────────────────────────────────
    # 2.9 ЦЕНТР — вид хроники (вставляем перед chat = ui.element)
    # ───────────────────────────────────────────────
    CENTER_MARKER = "# === CHRONICLES_PATCH:center_view ==="
    center_block = '''
                # === CHRONICLES_PATCH:center_view ===
                # Вид одной хроники (групповой чат сцены)
                with ui.element("div").classes("cab-chronicle-wrap").style(
                    "display:none;flex:1;flex-direction:column;overflow:hidden;"
                ) as chron_wrap:
                    refs["chronicle_wrap"] = chron_wrap
                    refs["chronicle_header"] = ui.element("div").classes(
                        "cab-chronicle-header"
                    ).style(
                        "padding:14px 24px 10px;"
                        "border-bottom:1px solid rgba(99,130,255,0.08);"
                        "flex-shrink:0;"
                    )
                    refs["chronicle_body"] = ui.element("div").classes(
                        "cab-chronicle-body"
                    ).style(
                        "flex:1;overflow-y:auto;padding:14px 24px;"
                        "scrollbar-width:thin;"
                    )
                    # Поле ввода реплики Садовника
                    with ui.element("div").classes("cab-chronicle-input-area").style(
                        "padding:10px 24px 14px;"
                        "border-top:1px solid rgba(99,130,255,0.08);"
                        "flex-shrink:0;background:rgba(20,23,34,0.4);"
                    ):
                        with ui.row().style("gap:8px;align-items:flex-end;width:100%;"):
                            refs["chronicle_input"] = ui.textarea(
                                placeholder="🌱 как Садовник — войди в сцену..."
                            ).props("borderless autogrow").style(
                                "flex:1;background:#141722;"
                                "border:1px solid rgba(212,175,55,0.12);"
                                "border-radius:6px;color:rgba(240,225,180,0.92);"
                                "font-family:JetBrains Mono;font-size:0.82rem;"
                                "padding:10px 14px;min-height:50px;max-height:120px;"
                            )
                            refs["chronicle_input"].on(
                                "keydown.ctrl.enter",
                                lambda e: send_gardener_reply()
                            )
                            ui.button(
                                "🌱 войти",
                                on_click=lambda: send_gardener_reply()
                            ).style(
                                "background:rgba(212,175,55,0.12);"
                                "border:1px solid rgba(212,175,55,0.25);"
                                "color:#d4af37;font-family:JetBrains Mono;"
                                "font-size:0.7rem;padding:10px 16px;"
                                "border-radius:6px;height:40px;"
                            )
                        ui.html(
                            '<div style="font-family:JetBrains Mono;font-size:0.52rem;'
                            'color:rgba(140,150,180,0.3);margin-top:6px;text-align:right">'
                            'Ctrl+Enter — войти · агенты услышат и ответят, '
                            'шлейф ляжет в их память</div>'
                        )
                # === END CHRONICLES_PATCH:center_view ===
'''
    src, ch = _ensure_block(
        src, CENTER_MARKER, center_block,
        anchor_after='refs["chat"] = ui.element("div").classes("cab-chat")',
    )
    changes.append(("центр-вид хроники", ch))

    # ───────────────────────────────────────────────
    # ИТОГ
    # ───────────────────────────────────────────────
    if src == original:
        print("Ничего не изменилось (всё уже было применено).")
    else:
        # Бэкап
        backup = UI_PATH.with_suffix(".py.bak_chronicles")
        backup.write_text(original, encoding="utf-8")
        print(f"📦 Бэкап: {backup}")

        UI_PATH.write_text(src, encoding="utf-8")
        print(f"✓ Записан: {UI_PATH}")

    print()
    print("Изменения:")
    for name, applied in changes:
        mark = "✓ применено" if applied else "○ уже было"
        print(f"  {mark}: {name}")


# ═══════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════

def main():
    print()
    print("█" * 60)
    print("  ПАТЧ: ХРОНИКИ ВСТРЕЧ В КАБИНЕТЕ — Спринт 23 Блок Б")
    print("█" * 60)
    print()
    try:
        step_paths()
        step_install_chronicles()
        step_patch_ui()
    except Exception as e:
        print()
        print(f"❌ ОШИБКА: {e}")
        import traceback; traceback.print_exc()
        sys.exit(1)

    print()
    print("─" * 60)
    print("✅ ГОТОВО")
    print("─" * 60)
    print()
    print("Что добавилось в Кабинет:")
    print("  • Вкладка «хроники» в правой панели")
    print("  • Список встреч из city_chronicles/ (новые сверху)")
    print("  • Клик по встрече → центр становится сценой")
    print("  • Поле «🌱 как Садовник» — войди и агенты ответят")
    print("  • Шлейф присутствия: sensory + −3% стресса обоим")
    print()
    print("Дальше:")
    print("  1. Перезапусти студию: python main.py")
    print("  2. Открой /cabinet")
    print("  3. Прогуляй город (🚶 прогулка) — если хроник ещё нет")
    print("  4. Вкладка «хроники» → клик по встрече → войди как Садовник")
    print()


if __name__ == "__main__":
    main()
