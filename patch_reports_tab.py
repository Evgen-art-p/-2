#!/usr/bin/env python3
"""
patch_reports_tab.py
════════════════════════════════════════════════════════════════
Заменяет вкладку «промпты» на «отчёты» в правой панели Кабинета.

Что делает:
  1. Создаёт studio/daily_reports.py — хранилище отчётов (jsonl)
  2. Патчит ui_cabinet.py:
     - убирает «промпты» из таб-бара (заменяет на «отчёты»)
     - добавляет _render_reports_tab()
     - кнопки 🌅/🌙 теперь пишут отчёт в daily_reports.jsonl
       и открывают вкладку «отчёты» вместо чата

Студия «Шесть Пальцев» · Спринт 23 · 2026
"""

import sys
from pathlib import Path
from datetime import datetime

ROOT       = Path(".")
STUDIO     = ROOT / "studio"
UI_CABINET = STUDIO / "cabinet" / "ui_cabinet.py"
REPORTS_PY = STUDIO / "daily_reports.py"

if not UI_CABINET.exists():
    print("❌ studio/cabinet/ui_cabinet.py не найден")
    sys.exit(1)


# ════════════════════════════════════════════════════════════════
# 1. studio/daily_reports.py
# ════════════════════════════════════════════════════════════════

REPORTS_MODULE = '''\
# studio/daily_reports.py
"""
Хранилище суточных отчётов: Утренний Чекаут + Ночной Цикл.
Формат: jsonl, один отчёт — одна строка.
Студия «Шесть Пальцев» · Спринт 23 · 2026
"""

import json
from pathlib import Path
from datetime import datetime

REPORTS_FILE = Path("studio/daily_reports.jsonl")
MAX_REPORTS  = 60  # последние 60 записей


def save_report(report_type: str, summary: dict, details: dict):
    """
    Сохраняет отчёт в jsonl.
    report_type: "morning" | "night"
    summary: {"GENIUS": 40, "NORMAL": 60, ...} или {"SLEEP": 90, "REVOLT": 14, ...}
    details: любой dict с подробностями
    """
    entry = {
        "ts":      datetime.now().isoformat(),
        "type":    report_type,
        "summary": summary,
        "details": details,
    }
    REPORTS_FILE.parent.mkdir(parents=True, exist_ok=True)

    # Читаем существующие
    lines = []
    if REPORTS_FILE.exists():
        try:
            lines = REPORTS_FILE.read_text(encoding="utf-8").splitlines()
        except Exception:
            pass

    lines.append(json.dumps(entry, ensure_ascii=False))

    # Оставляем последние MAX_REPORTS
    lines = lines[-MAX_REPORTS:]
    REPORTS_FILE.write_text("\\n".join(lines) + "\\n", encoding="utf-8")


def load_reports(limit: int = 20) -> list[dict]:
    """Загружает последние N отчётов (новые первыми)."""
    if not REPORTS_FILE.exists():
        return []
    try:
        lines = REPORTS_FILE.read_text(encoding="utf-8").splitlines()
        result = []
        for line in reversed(lines):
            line = line.strip()
            if not line:
                continue
            try:
                result.append(json.loads(line))
            except Exception:
                continue
            if len(result) >= limit:
                break
        return result
    except Exception:
        return []


def format_ts(ts: str) -> str:
    """Форматирует timestamp для отображения."""
    try:
        dt = datetime.fromisoformat(ts)
        today = datetime.now().date()
        delta = (today - dt.date()).days
        if delta == 0:
            return f"сегодня {dt.strftime('%H:%M')}"
        elif delta == 1:
            return f"вчера {dt.strftime('%H:%M')}"
        else:
            months = ["янв","фев","мар","апр","май","июн",
                      "июл","авг","сен","окт","ноя","дек"]
            return f"{dt.day} {months[dt.month-1]} {dt.strftime('%H:%M')}"
    except Exception:
        return ts[:16]
'''


# ════════════════════════════════════════════════════════════════
# 2. _render_reports_tab() — вставляем в ui_cabinet.py
# ════════════════════════════════════════════════════════════════

RENDER_REPORTS_FUNC = '''
    def _render_reports_tab():
        """Вкладка «отчёты» — история запусков Чекаута и Ночного цикла."""
        try:
            from studio.daily_reports import load_reports, format_ts
            reports = load_reports(limit=30)
        except Exception:
            reports = []

        if not reports:
            ui.html(
                '<div style="text-align:center;padding:32px 16px;'
                'font-family:JetBrains Mono;font-size:0.56rem;'
                'color:rgba(140,150,180,0.3);">'
                'отчётов пока нет<br>'
                '<span style="font-size:0.5rem;color:rgba(140,150,180,0.2)">'
                'нажми 🌅 день или 🌙 ночь</span>'
                '</div>'
            )
            return

        # Кнопка очистки
        def _clear_reports():
            try:
                from pathlib import Path
                Path("studio/daily_reports.jsonl").unlink(missing_ok=True)
                update_right_panel("reports")
                ui.notify("Отчёты очищены", type="info")
            except Exception as e:
                ui.notify(f"⚠ {e}", type="negative")

        with ui.element("div").style(
            "display:flex;justify-content:space-between;align-items:center;"
            "padding:4px 8px 6px;"
        ):
            ui.html(
                f'<span style="font-family:JetBrains Mono;font-size:0.52rem;'
                f'color:rgba(140,150,180,0.35);">'
                f'записей: {len(reports)}</span>'
            )
            ui.button("🗑", on_click=_clear_reports).props("flat dense").style(
                "font-size:0.65rem;color:rgba(140,150,180,0.3);min-width:24px;"
            )

        MODE_ICONS = {"GENIUS": "🔥", "NORMAL": "⚡", "SAFE": "🛡", "RECOVERY": "💤"}

        with ui.element("div").style(
            "overflow-y:auto;max-height:calc(100vh - 160px);scrollbar-width:thin;"
        ):
            for report in reports:
                rtype   = report.get("type", "")
                ts      = format_ts(report.get("ts", ""))
                summary = report.get("summary", {})
                details = report.get("details", {})

                is_morning = rtype == "morning"
                icon  = "🌅" if is_morning else "🌙"
                label = "Утренний Чекаут" if is_morning else "Ночной Цикл"
                accent = "rgba(255,180,50,0.7)" if is_morning else "rgba(160,130,240,0.7)"
                bg     = "rgba(255,180,50,0.03)" if is_morning else "rgba(108,80,200,0.03)"
                border = "rgba(255,180,50,0.12)" if is_morning else "rgba(108,80,200,0.15)"

                # Строка summary
                if is_morning:
                    g = summary.get("GENIUS", 0)
                    n = summary.get("NORMAL", 0)
                    s = summary.get("SAFE", 0)
                    r = summary.get("RECOVERY", 0)
                    summary_line = (
                        f'<span style="color:rgba(255,100,80,0.8)">🔥{g}</span> '
                        f'<span style="color:rgba(255,200,80,0.6)">⚡{n}</span> '
                        f'<span style="color:rgba(100,180,255,0.6)">🛡{s}</span> '
                        f'<span style="color:rgba(140,150,180,0.5)">💤{r}</span>'
                    )
                else:
                    sl = summary.get("SLEEP", 0)
                    rs = summary.get("RESTLESS", 0)
                    rv = summary.get("REVOLT", 0)
                    summary_line = (
                        f'<span style="color:rgba(140,150,180,0.5)">💤{sl}</span> '
                        f'<span style="color:rgba(255,200,80,0.6)">😰{rs}</span> '
                        f'<span style="color:rgba(255,100,80,0.9)">⚡{rv}</span>'
                    )

                with ui.element("div").style(
                    f"padding:9px 10px;margin:4px 6px;"
                    f"background:{bg};border:1px solid {border};"
                    f"border-radius:8px;"
                ):
                    # Заголовок
                    ui.html(
                        f'<div style="display:flex;justify-content:space-between;'
                        f'align-items:center;margin-bottom:4px;">'
                        f'<span style="font-family:JetBrains Mono;font-size:0.65rem;'
                        f'color:{accent};font-weight:500;">{icon} {label}</span>'
                        f'<span style="font-family:JetBrains Mono;font-size:0.5rem;'
                        f'color:rgba(140,150,180,0.4);">{ts}</span>'
                        f'</div>'
                    )
                    # Summary строка
                    ui.html(
                        f'<div style="font-family:JetBrains Mono;font-size:0.6rem;'
                        f'margin-bottom:5px;">{summary_line}</div>'
                    )

                    # Детали — интересные агенты
                    if is_morning:
                        recovery = details.get("RECOVERY", [])
                        genius_revolt = [
                            a for a in details.get("GENIUS", [])
                            if "бунт" in a
                        ]
                        if recovery:
                            ui.html(
                                f'<div style="font-family:JetBrains Mono;'
                                f'font-size:0.55rem;color:rgba(140,150,180,0.5);'
                                f'border-top:1px solid rgba(255,255,255,0.04);'
                                f'padding-top:4px;margin-top:2px;">'
                                + "<br>".join(
                                    f'💤 {a}' for a in recovery[:4]
                                )
                                + ("..." if len(recovery) > 4 else "")
                                + "</div>"
                            )
                        if genius_revolt:
                            ui.html(
                                f'<div style="font-family:JetBrains Mono;'
                                f'font-size:0.55rem;color:rgba(255,100,80,0.7);'
                                f'margin-top:2px;">'
                                + "<br>".join(
                                    f'⚡ {a}' for a in genius_revolt[:3]
                                )
                                + "</div>"
                            )
                    else:
                        revolts  = details.get("revolts", [])
                        resentful = details.get("resentful", [])
                        if revolts:
                            ui.html(
                                f'<div style="font-family:JetBrains Mono;'
                                f'font-size:0.55rem;color:rgba(255,100,80,0.8);'
                                f'border-top:1px solid rgba(255,255,255,0.04);'
                                f'padding-top:4px;margin-top:2px;">'
                                + "<br>".join(
                                    f'⚡ {r}' for r in revolts[:5]
                                )
                                + ("..." if len(revolts) > 5 else "")
                                + "</div>"
                            )
                        if resentful:
                            ui.html(
                                f'<div style="font-family:JetBrains Mono;'
                                f'font-size:0.55rem;color:rgba(220,100,100,0.7);'
                                f'margin-top:2px;">'
                                + "<br>".join(
                                    f'🔴 {r}' for r in resentful[:3]
                                )
                                + "</div>"
                            )

'''


# ════════════════════════════════════════════════════════════════
# 3. Новые версии _do_morning_checkout и _do_night_cycle
#    — добавляем save_report() и switch_tab("reports")
# ════════════════════════════════════════════════════════════════

# Якорь: конец _do_morning_checkout — строка с ui.notify positive
MORNING_OLD_NOTIFY = '''            ui.notify(
                f"✅ Чекаут: {summary.get('GENIUS',0)}🔥 "
                f"{summary.get('RECOVERY',0)}💤",
                type="positive"
            )'''

MORNING_NEW_NOTIFY = '''            # Сохраняем отчёт
            try:
                from studio.daily_reports import save_report
                by_mode_save = {"GENIUS": [], "NORMAL": [], "SAFE": [], "RECOVERY": []}
                for key, data in modes.items():
                    m = data.get("mode", "NORMAL")
                    folder = key.split("_")[0]
                    revolt = " после бунта" if data.get("night_revolt") else ""
                    by_mode_save[m].append(f"{folder}: {data.get('reason','')[:50]}{revolt}")
                save_report("morning", summary, by_mode_save)
                switch_tab("reports")
                update_right_panel("reports")
            except Exception as _re:
                print(f"[CHECKOUT] ⚠ save_report: {_re}")

            ui.notify(
                f"✅ Чекаут: {summary.get('GENIUS',0)}🔥 "
                f"{summary.get('RECOVERY',0)}💤",
                type="positive"
            )'''

NIGHT_OLD_NOTIFY = '''            notify_text = f"✅ Ночь: {summary.get('REVOLT',0)}⚡ бунт"
            if revolts:
                notify_text += f" · {', '.join(revolts[:2])}"
            ui.notify(notify_text, type="positive")'''

NIGHT_NEW_NOTIFY = '''            # Сохраняем отчёт
            try:
                from studio.daily_reports import save_report
                resentful_save = [
                    f"{d.get('agent_name','?')} → {d.get('decay_changes',{}).get('resentment_grew',{}).get('target','?')}"
                    for k, d in night_results.items()
                    if d.get("decay_changes", {}).get("resentment_grew")
                ]
                save_report("night", summary, {
                    "revolts":   revolts,
                    "resentful": resentful_save,
                })
                switch_tab("reports")
                update_right_panel("reports")
            except Exception as _re:
                print(f"[NIGHT] ⚠ save_report: {_re}")

            notify_text = f"✅ Ночь: {summary.get('REVOLT',0)}⚡ бунт"
            if revolts:
                notify_text += f" · {', '.join(revolts[:2])}"
            ui.notify(notify_text, type="positive")'''


# ════════════════════════════════════════════════════════════════
# ПРИМЕНЕНИЕ ПАТЧА
# ════════════════════════════════════════════════════════════════

def apply():
    code = UI_CABINET.read_text(encoding="utf-8")
    errors = []
    changed = False

    # ── Бэкап ─────────────────────────────────────────────────
    backup = UI_CABINET.with_suffix(".py.bak_reports_tab")
    backup.write_text(code, encoding="utf-8")
    print(f"  ✅ Бэкап: {backup.name}")

    # ── 1. Заменяем вкладку «промпты» → «отчёты» в таб-баре ──
    OLD_TAB = '("prompts","промпты")'
    NEW_TAB = '("reports","отчёты")'
    if OLD_TAB in code:
        code = code.replace(OLD_TAB, NEW_TAB, 1)
        print("  ✅ Таб «промпты» → «отчёты»")
        changed = True
    elif NEW_TAB in code:
        print("  ℹ Таб уже переименован")
    else:
        errors.append("Таб 'промпты' не найден")

    # ── 2. Заменяем "prompts" → "reports" в инициализации панелей ──
    OLD_PANELS = '"agent","matrix","chronicles","files","prompts","archive"'
    NEW_PANELS = '"agent","matrix","chronicles","files","reports","archive"'
    if OLD_PANELS in code:
        code = code.replace(OLD_PANELS, NEW_PANELS, 1)
        print("  ✅ Панели: prompts → reports")
        changed = True
    elif NEW_PANELS in code:
        print("  ℹ Панели уже обновлены")
    else:
        errors.append("Строка инициализации панелей не найдена")

    # ── 3. update_right_panel: добавляем elif reports ─────────
    OLD_PANEL_ELIF = "        elif tab_name == \"chronicles\":  # === CHRONICLES_PATCH:switch_tab ==="
    NEW_PANEL_ELIF = (
        "        elif tab_name == \"reports\":\n"
        "            update_right_panel(\"reports\")\n"
        "        elif tab_name == \"chronicles\":  # === CHRONICLES_PATCH:switch_tab ==="
    )
    if "elif tab_name == \"reports\":" in code:
        print("  ℹ switch_tab reports уже есть")
    elif OLD_PANEL_ELIF in code:
        code = code.replace(OLD_PANEL_ELIF, NEW_PANEL_ELIF, 1)
        print("  ✅ switch_tab: добавлен elif reports")
        changed = True
    else:
        errors.append("Якорь switch_tab chronicles не найден")

    # ── 4. update_right_panel dispatcher: добавляем reports ───
    OLD_DISPATCH = "            elif tab_name == \"chronicles\":  # === CHRONICLES_PATCH:update_right_panel ==="
    NEW_DISPATCH = (
        "            elif tab_name == \"reports\":\n"
        "                _render_reports_tab()\n"
        "            elif tab_name == \"chronicles\":  # === CHRONICLES_PATCH:update_right_panel ==="
    )
    if "_render_reports_tab()" in code:
        print("  ℹ _render_reports_tab уже зарегистрирован")
    elif OLD_DISPATCH in code:
        code = code.replace(OLD_DISPATCH, NEW_DISPATCH, 1)
        print("  ✅ update_right_panel: добавлен reports")
        changed = True
    else:
        errors.append("Якорь update_right_panel chronicles не найден")

    # ── 5. Вставляем _render_reports_tab() перед _render_chronicles_tab ──
    ANCHOR_RENDER = "    def _render_chronicles_tab():"
    if "_render_reports_tab" in code and "def _render_reports_tab" in code:
        print("  ℹ _render_reports_tab уже есть")
    elif ANCHOR_RENDER in code:
        code = code.replace(
            ANCHOR_RENDER,
            RENDER_REPORTS_FUNC + "\n    def _render_chronicles_tab():",
            1
        )
        print("  ✅ _render_reports_tab() вставлена")
        changed = True
    else:
        errors.append("Якорь _render_chronicles_tab не найден")

    # ── 6. Патчим _do_morning_checkout: save_report + switch_tab ──
    if "save_report" in code and "morning" in code and "switch_tab(\"reports\")" in code:
        print("  ℹ _do_morning_checkout уже пропатчен")
    elif MORNING_OLD_NOTIFY in code:
        code = code.replace(MORNING_OLD_NOTIFY, MORNING_NEW_NOTIFY, 1)
        print("  ✅ _do_morning_checkout: save_report добавлен")
        changed = True
    else:
        errors.append("Якорь _do_morning_checkout notify не найден")

    # ── 7. Патчим _do_night_cycle: save_report + switch_tab ───
    if NIGHT_OLD_NOTIFY in code:
        code = code.replace(NIGHT_OLD_NOTIFY, NIGHT_NEW_NOTIFY, 1)
        print("  ✅ _do_night_cycle: save_report добавлен")
        changed = True
    elif '"night"' in code and 'save_report' in code:
        print("  ℹ _do_night_cycle уже пропатчен")
    else:
        errors.append("Якорь _do_night_cycle notify не найден")

    # ── Сохраняем ──────────────────────────────────────────────
    if errors:
        print(f"\n⚠ Ошибки ({len(errors)}):")
        for e in errors:
            print(f"  • {e}")
        if not changed:
            print("Файл НЕ перезаписан.")
            return False

    UI_CABINET.write_text(code, encoding="utf-8")
    print(f"  ✅ ui_cabinet.py сохранён")
    return True


def main():
    print("=" * 60)
    print("ПАТЧ: ВКЛАДКА ОТЧЁТОВ")
    print(f"Время: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)

    # Создаём daily_reports.py
    print("\n[1/2] studio/daily_reports.py")
    if REPORTS_PY.exists():
        print("  ℹ Уже существует — пропускаем")
    else:
        REPORTS_PY.write_text(REPORTS_MODULE, encoding="utf-8")
        print("  ✅ Создан")

    # Патчим ui_cabinet.py
    print("\n[2/2] Патч ui_cabinet.py")
    ok = apply()

    print("\n" + "=" * 60)
    if ok:
        print("✅ Готово. Перезапусти студию.")
        print()
        print("Вкладка «промпты» → «отчёты».")
        print("После нажатия 🌅 или 🌙 отчёт появится там автоматически.")
        print("История хранится в studio/daily_reports.jsonl")
    else:
        print("⚠ Патч применён частично — проверь ошибки выше.")
    print("=" * 60)


if __name__ == "__main__":
    main()
