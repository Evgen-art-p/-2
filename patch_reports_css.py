#!/usr/bin/env python3
"""
patch_reports_css.py
════════════════════════════════════════════════════════════════
Переносит стили вкладки «отчёты» в css.py.
Убирает инлайн-стили из _render_reports_tab() в ui_cabinet.py.
Студия «Шесть Пальцев» · Спринт 23 · 2026
"""
import sys
from pathlib import Path
from datetime import datetime

CSS_PY     = Path("studio/cabinet/css.py")
UI_CABINET = Path("studio/cabinet/ui_cabinet.py")

if not CSS_PY.exists():
    print("❌ studio/cabinet/css.py не найден")
    sys.exit(1)

# ════════════════════════════════════════════════════════════════
# 1. CSS — добавляем в конец CABINET_CSS перед закрывающим """
# ════════════════════════════════════════════════════════════════

REPORTS_CSS = """
/* ═══ RIGHT TAB: ОТЧЁТЫ (Спринт 23) ═══ */
.rep-header {
  display: flex; justify-content: space-between; align-items: center;
  padding: 4px 8px 6px;
}
.rep-count {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.58rem;
  color: rgba(180,190,220,0.45);
}
.rep-scroll {
  overflow-y: auto;
  max-height: calc(100vh - 160px);
  scrollbar-width: thin;
}

/* Карточка отчёта */
.rep-card {
  padding: 10px 12px; margin: 4px 6px;
  border-radius: 8px; cursor: pointer;
  transition: opacity 0.15s;
}
.rep-card:hover { opacity: 0.88; }
.rep-card-morning {
  background: rgba(255,180,50,0.04);
  border: 1px solid rgba(255,180,50,0.14);
}
.rep-card-night {
  background: rgba(108,80,200,0.04);
  border: 1px solid rgba(108,80,200,0.18);
}

/* Хедер карточки */
.rep-card-head {
  display: flex; justify-content: space-between;
  align-items: center; margin-bottom: 5px;
}
.rep-card-title-morning {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.72rem; font-weight: 500;
  color: rgba(255,180,50,0.85);
}
.rep-card-title-night {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.72rem; font-weight: 500;
  color: rgba(160,130,240,0.85);
}
.rep-card-ts {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.56rem;
  color: rgba(160,170,200,0.5);
}

/* Строка summary */
.rep-summary {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.66rem; margin-bottom: 3px;
}
.rep-genius  { color: rgba(255,100,80,0.9); }
.rep-normal  { color: rgba(255,210,90,0.7); }
.rep-safe    { color: rgba(100,190,255,0.7); }
.rep-recovery{ color: rgba(160,170,200,0.6); }
.rep-sleep   { color: rgba(160,170,200,0.55); }
.rep-restless{ color: rgba(255,210,90,0.7); }
.rep-revolt  { color: rgba(255,100,80,0.95); }

/* Детали (разворачиваемые) */
.rep-details {
  display: none;
  margin-top: 7px;
  border-top: 1px solid rgba(255,255,255,0.05);
  padding-top: 6px;
}
.rep-detail-block {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.62rem;
  line-height: 1.55;
  margin-top: 4px;
}
.rep-detail-morning { color: rgba(190,200,225,0.65); }
.rep-detail-revolts { color: rgba(255,120,80,0.9); }
.rep-detail-resentful { color: rgba(220,100,100,0.8); }
.rep-detail-restless { color: rgba(210,190,90,0.7); }
.rep-detail-empty {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.64rem;
  color: rgba(160,170,200,0.4);
  text-align: center;
  padding: 8px 0 2px;
}
"""

# ════════════════════════════════════════════════════════════════
# 2. Новый _render_reports_tab — чистый, с классами из css.py
# ════════════════════════════════════════════════════════════════

NEW_RENDER_FUNC = '''    def _render_reports_tab():
        """Вкладка «отчёты» — история запусков Чекаута и Ночного цикла."""
        try:
            from studio.daily_reports import load_reports, format_ts
            reports = load_reports(limit=30)
        except Exception:
            reports = []

        if not reports:
            ui.html(
                \'<div class="rep-detail-empty" style="padding:32px 16px;">\' +
                \'отчётов пока нет<br>\' +
                \'<span style="font-size:0.56rem;color:rgba(160,170,200,0.3)">\' +
                \'нажми 🌅 день или 🌙 ночь</span></div>\'
            )
            return

        def _clear_reports():
            try:
                from pathlib import Path as _P
                _P("studio/daily_reports.jsonl").unlink(missing_ok=True)
                update_right_panel("reports")
                ui.notify("Отчёты очищены", type="info")
            except Exception as e:
                ui.notify(f"⚠ {e}", type="negative")

        with ui.element("div").classes("rep-header"):
            ui.html(f\'<span class="rep-count">записей: {len(reports)}</span>\')
            ui.button("🗑", on_click=_clear_reports).props("flat dense").style(
                "font-size:0.65rem;color:rgba(160,170,200,0.35);min-width:24px;"
            )

        with ui.element("div").classes("rep-scroll"):
            for report in reports:
                rtype      = report.get("type", "")
                ts         = format_ts(report.get("ts", ""))
                summary    = report.get("summary", {})
                details    = report.get("details", {})
                is_morning = rtype == "morning"

                icon      = "🌅" if is_morning else "🌙"
                label     = "Утренний Чекаут" if is_morning else "Ночной Цикл"
                card_cls  = "rep-card rep-card-morning" if is_morning else "rep-card rep-card-night"
                title_cls = "rep-card-title-morning" if is_morning else "rep-card-title-night"

                # Summary HTML
                if is_morning:
                    g = summary.get("GENIUS", 0)
                    n = summary.get("NORMAL", 0)
                    s = summary.get("SAFE", 0)
                    r = summary.get("RECOVERY", 0)
                    summary_html = (
                        f\'<span class="rep-genius">🔥{g}</span> \' +
                        f\'<span class="rep-normal">⚡{n}</span> \' +
                        f\'<span class="rep-safe">🛡{s}</span> \' +
                        f\'<span class="rep-recovery">💤{r}</span>\'
                    )
                else:
                    sl = summary.get("SLEEP", 0)
                    rs = summary.get("RESTLESS", 0)
                    rv = summary.get("REVOLT", 0)
                    summary_html = (
                        f\'<span class="rep-sleep">💤{sl}</span> \' +
                        f\'<span class="rep-restless">😰{rs}</span> \' +
                        f\'<span class="rep-revolt">⚡{rv}</span>\'
                    )

                expanded = {"open": False}

                with ui.element("div").classes(card_cls) as card:
                    # Хедер карточки
                    ui.html(
                        f\'<div class="rep-card-head">\' +
                        f\'<span class="{title_cls}">{icon} {label}</span>\' +
                        f\'<span class="rep-card-ts">{ts} ▾</span>\' +
                        f\'</div>\'
                    )
                    # Summary — всегда видна
                    ui.html(f\'<div class="rep-summary">{summary_html}</div>\')

                    # Детали — разворачиваются по клику
                    with ui.element("div").classes("rep-details") as detail_block:
                        if is_morning:
                            for mode_key, mode_cls, mode_icon in [
                                ("RECOVERY", "rep-detail-morning", "💤"),
                                ("SAFE",     "rep-detail-morning", "🛡"),
                                ("GENIUS",   "rep-detail-morning", "🔥"),
                                ("NORMAL",   "rep-detail-morning", "⚡"),
                            ]:
                                agents = details.get(mode_key, [])
                                if agents:
                                    body = "<br>".join(a for a in agents[:8])
                                    if len(agents) > 8:
                                        body += f"<br>...и ещё {len(agents)-8}"
                                    ui.html(
                                        f\'<div class="rep-detail-block {mode_cls}">\' +
                                        f\'<b>{mode_icon} {mode_key} ({len(agents)})</b><br>\' +
                                        body + \'</div>\'
                                    )
                        else:
                            revolts_d   = details.get("revolts", [])
                            resentful_d = details.get("resentful", [])
                            restless_d  = details.get("restless", [])

                            if revolts_d:
                                body = "<br>".join(f"⚡ {r}" for r in revolts_d[:8])
                                if len(revolts_d) > 8:
                                    body += f"<br>...и ещё {len(revolts_d)-8}"
                                ui.html(
                                    \'<div class="rep-detail-block rep-detail-revolts">\' +
                                    f\'<b>⚡ Бунтари ({len(revolts_d)})</b><br>\' +
                                    body + \'</div>\'
                                )
                            if resentful_d:
                                body = "<br>".join(f"🔴 {r}" for r in resentful_d[:5])
                                ui.html(
                                    \'<div class="rep-detail-block rep-detail-resentful">\' +
                                    f\'<b>🔴 Обиды ({len(resentful_d)})</b><br>\' +
                                    body + \'</div>\'
                                )
                            if restless_d:
                                ui.html(
                                    \'<div class="rep-detail-block rep-detail-restless">\' +
                                    f\'<b>😰 Тревожный сон ({len(restless_d)})</b><br>\' +
                                    ", ".join(restless_d[:12]) + \'</div>\'
                                )
                            if not revolts_d and not resentful_d and not restless_d:
                                ui.html(
                                    \'<div class="rep-detail-empty">все спят 💤 — город спокоен</div>\'
                                )

                    def _toggle(e, db=detail_block, es=expanded):
                        es["open"] = not es["open"]
                        db.classes(
                            replace="rep-details" + (" open" if es["open"] else "")
                        )
                        db.style("display:block;" if es["open"] else "display:none;")

                    card.on("click", _toggle)

'''

# ════════════════════════════════════════════════════════════════
# ПРИМЕНЕНИЕ
# ════════════════════════════════════════════════════════════════

def patch_css():
    code = CSS_PY.read_text(encoding="utf-8")
    if "rep-card" in code:
        print("  ℹ CSS уже содержит .rep-card — пропускаем")
        return True
    backup = CSS_PY.with_suffix(".py.bak_reports_css")
    backup.write_text(code, encoding="utf-8")
    print(f"  ✅ Бэкап css.py: {backup.name}")
    # Вставляем перед закрывающим """
    code = code.replace('"""\n', REPORTS_CSS + '"""\n', 1)
    CSS_PY.write_text(code, encoding="utf-8")
    print("  ✅ Стили отчётов добавлены в css.py")
    return True


def patch_ui():
    code = UI_CABINET.read_text(encoding="utf-8")

    # Ищем старую функцию от начала до следующей def на том же уровне
    FUNC_START = "    def _render_reports_tab():"
    FUNC_END   = "\n    def _render_chronicles_tab():"

    if FUNC_START not in code:
        print("  ❌ _render_reports_tab не найдена")
        return False

    start = code.find(FUNC_START)
    end   = code.find(FUNC_END, start)
    if end == -1:
        print("  ❌ Конец функции не найден")
        return False

    backup = UI_CABINET.with_suffix(".py.bak_reports_css")
    backup.write_text(code, encoding="utf-8")
    print(f"  ✅ Бэкап ui_cabinet.py: {backup.name}")

    new_code = code[:start] + NEW_RENDER_FUNC + code[end:]
    UI_CABINET.write_text(new_code, encoding="utf-8")
    print("  ✅ _render_reports_tab заменена на версию с CSS-классами")
    return True


def main():
    print("=" * 60)
    print("ПАТЧ: стили отчётов → css.py")
    print(f"Время: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)

    print("\n[1/2] css.py")
    patch_css()

    print("\n[2/2] ui_cabinet.py")
    ok = patch_ui()

    print()
    if ok:
        print("✅ Готово. Перезапусти студию.")
        print("   Теперь размер и цвет текста меняется в css.py — класс .rep-detail-empty")
    else:
        print("⚠ Проверь ошибки выше")
    print("=" * 60)


if __name__ == "__main__":
    main()
