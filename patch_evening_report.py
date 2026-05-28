#!/usr/bin/env python3
"""
patch_evening_report.py — Спринт 24: Вечерний отчёт в правой панели

Что делает:
  1. city_walker.py — run_city_walk_evening() пишет save_report("evening", ...)
     с итогами: сколько агентов, где были, сколько встреч
  2. ui_cabinet.py — _render_reports_tab() рендерит тип "evening"
     зелёная карточка 🌆, summary: агентов/кварталов/встреч

Запуск: python patch_evening_report.py
"""

from pathlib import Path

CITY_WALKER_PATH = Path("studio/city_walker.py")
UI_CABINET_PATH  = Path("studio/cabinet/ui_cabinet.py")

# ─────────────────────────────────────────────────────────
# ПАТЧ 1: city_walker.py — save_report в run_city_walk_evening
# ─────────────────────────────────────────────────────────

# Якорь — последние строки run_city_walk_evening перед return
WALKER_ANCHOR = '''    # Добавляем событие в историю города
    dept_label = workshops[0] if workshops and len(workshops) == 1 else "цех"
    add_city_event(f"Агенты {dept_label} вернулись с вечерней прогулки")

    return results'''

WALKER_REPLACEMENT = '''    # Добавляем событие в историю города
    dept_label = workshops[0] if workshops and len(workshops) == 1 else "цех"
    add_city_event(f"Агенты {dept_label} вернулись с вечерней прогулки")

    # ── Отчёт в daily_reports · Спринт 24 ──
    try:
        from studio.daily_reports import save_report as _save_rep
        ok_results   = [r for r in results if r.get("status") == "ok"]
        total_agents = len(set(r.get("agent", "") for r in ok_results))
        total_quanta = len(ok_results)  # каждый результат = 1 квант
        total_meets  = sum(1 for r in ok_results if r.get("met"))

        # Локации: считаем сколько раз каждая встретилась
        loc_counts: dict[str, int] = {}
        for r in ok_results:
            loc = r.get("location", "")
            if loc and loc != "неизвестно":
                loc_counts[loc] = loc_counts.get(loc, 0) + 1
        top_locs = sorted(loc_counts.items(), key=lambda x: x[1], reverse=True)[:5]

        summary = {
            "agents":  total_agents,
            "quanta":  total_quanta,
            "meets":   total_meets,
        }
        details = {
            "dept":     dept_label,
            "top_locs": [{"name": n, "count": c} for n, c in top_locs],
            "agents_list": [
                {"name": r.get("agent", ""), "location": r.get("location", "")}
                for r in ok_results
            ][:30],
        }
        _save_rep("evening", summary, details)
        print(f"[CITY] 📋 Вечерний отчёт сохранён: {total_agents} агентов, {total_quanta} кварталов, {total_meets} встреч")
    except Exception as _rep_err:
        print(f"[CITY] ⚠ Вечерний отчёт не сохранён: {_rep_err}")
    # ── END отчёт ──

    return results'''


# ─────────────────────────────────────────────────────────
# ПАТЧ 2: ui_cabinet.py — рендер "evening" в _render_reports_tab
# ─────────────────────────────────────────────────────────

# Якорь — начало блока где определяем icon/label/card_cls по типу
CABINET_ANCHOR = '''                is_morning = rtype == "morning"

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
                    )'''

CABINET_REPLACEMENT = '''                is_morning = rtype == "morning"
                is_evening = rtype == "evening"

                if is_morning:
                    icon, label = "🌅", "Утренний Чекаут"
                    card_cls  = "rep-card rep-card-morning"
                    title_cls = "rep-card-title-morning"
                elif is_evening:
                    icon, label = "🌆", "Вечерняя прогулка"
                    card_cls  = "rep-card rep-card-evening"
                    title_cls = "rep-card-title-evening"
                else:
                    icon, label = "🌙", "Ночной Цикл"
                    card_cls  = "rep-card rep-card-night"
                    title_cls = "rep-card-title-night"

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
                elif is_evening:
                    ag = summary.get("agents", 0)
                    qu = summary.get("quanta", 0)
                    me = summary.get("meets", 0)
                    summary_html = (
                        f\'<span style="color:rgba(80,220,140,0.8)">🚶{ag}</span> \' +
                        f\'<span style="color:rgba(80,220,140,0.55)">кв:{qu}</span> \' +
                        f\'<span style="color:rgba(212,175,55,0.7)">🤝{me}</span>\'
                    )
                else:
                    sl = summary.get("SLEEP", 0)
                    rs = summary.get("RESTLESS", 0)
                    rv = summary.get("REVOLT", 0)
                    summary_html = (
                        f\'<span class="rep-sleep">💤{sl}</span> \' +
                        f\'<span class="rep-restless">😰{rs}</span> \' +
                        f\'<span class="rep-revolt">⚡{rv}</span>\'
                    )'''


# Добавляем рендер деталей вечернего отчёта
# Якорь — блок деталей для morning/night, вставляем ветку evening перед else
DETAILS_ANCHOR = '''                    with ui.element("div").classes("rep-details") as detail_block:
                        if is_morning:'''

DETAILS_REPLACEMENT = '''                    with ui.element("div").classes("rep-details") as detail_block:
                        if is_evening:
                            top_locs = details.get("top_locs", [])
                            dept_d   = details.get("dept", "")
                            agents_d = details.get("agents_list", [])
                            if dept_d:
                                ui.html(
                                    f\'<div class="rep-detail-block" style="border-left:2px solid rgba(80,220,140,0.3);">\' +
                                    f\'<b>🌆 цех: {dept_d}</b></div>\'
                                )
                            if top_locs:
                                body = "<br>".join(
                                    f\'📍 {l["name"]} × {l["count"]}\' for l in top_locs
                                )
                                ui.html(
                                    \'<div class="rep-detail-block" style="border-left:2px solid rgba(80,220,140,0.3);">\' +
                                    f\'<b>Локации</b><br>{body}</div>\'
                                )
                            if agents_d:
                                body = "<br>".join(
                                    f\'{a["name"]} → {a["location"]}\' for a in agents_d[:10]
                                )
                                if len(agents_d) > 10:
                                    body += f\'<br>...и ещё {len(agents_d)-10}\'
                                ui.html(
                                    \'<div class="rep-detail-block" style="border-left:2px solid rgba(80,220,140,0.3);">\' +
                                    f\'<b>Агенты</b><br>{body}</div>\'
                                )
                        elif is_morning:'''


# Добавляем CSS для evening карточки
CSS_ANCHOR = "                card_cls  = \"rep-card rep-card-morning\" if is_morning else \"rep-card rep-card-night\""
# (уже заменён выше, CSS добавляем через отдельный inject в _render_reports_tab)

EVENING_CSS_ANCHOR = "        ui.html(f'<div style=\"padding:4px 8px;font-family:JetBrains Mono;"

EVENING_CSS_REPLACEMENT = '''        ui.add_head_html("""<style>
.rep-card-evening{border-left:2px solid rgba(80,220,140,0.35)!important;background:rgba(50,180,100,0.03)!important;}
.rep-card-title-evening{color:rgba(80,220,140,0.85)!important;}
</style>""")
        ui.html(f'<div style="padding:4px 8px;font-family:JetBrains Mono;'''


# ─────────────────────────────────────────────────────────
# ПРИМЕНЕНИЕ
# ─────────────────────────────────────────────────────────

def apply():
    ok = True

    # ── Патч 1: city_walker.py ──
    if not CITY_WALKER_PATH.exists():
        print(f"[ПАТЧ] ❌ {CITY_WALKER_PATH} не найден")
        ok = False
    else:
        text = CITY_WALKER_PATH.read_text(encoding="utf-8")
        if "_save_rep" in text:
            print("[ПАТЧ] ⚠ Патч 1 (save_report в walker) уже применён")
        elif WALKER_ANCHOR in text:
            text = text.replace(WALKER_ANCHOR, WALKER_REPLACEMENT)
            CITY_WALKER_PATH.write_text(text, encoding="utf-8")
            print("[ПАТЧ] ✅ Патч 1: save_report добавлен в run_city_walk_evening")
        else:
            print("[ПАТЧ] ❌ Патч 1: якорь не найден в city_walker.py")
            ok = False

    # ── Патч 2: ui_cabinet.py ──
    if not UI_CABINET_PATH.exists():
        print(f"[ПАТЧ] ❌ {UI_CABINET_PATH} не найден")
        ok = False
    else:
        text = UI_CABINET_PATH.read_text(encoding="utf-8")
        changed = False

        if "is_evening" in text:
            print("[ПАТЧ] ⚠ Патч 2а (is_evening) уже применён")
        elif CABINET_ANCHOR in text:
            text = text.replace(CABINET_ANCHOR, CABINET_REPLACEMENT)
            changed = True
            print("[ПАТЧ] ✅ Патч 2а: тип evening добавлен в summary")
        else:
            print("[ПАТЧ] ❌ Патч 2а: якорь summary не найден")
            ok = False

        if "if is_evening:" in text:
            print("[ПАТЧ] ⚠ Патч 2б (детали evening) уже применён")
        elif DETAILS_ANCHOR in text:
            text = text.replace(DETAILS_ANCHOR, DETAILS_REPLACEMENT)
            changed = True
            print("[ПАТЧ] ✅ Патч 2б: детали вечернего отчёта добавлены")
        else:
            print("[ПАТЧ] ❌ Патч 2б: якорь деталей не найден")

        if "rep-card-evening" in text:
            print("[ПАТЧ] ⚠ Патч 2в (CSS evening) уже применён")
        elif EVENING_CSS_ANCHOR in text:
            text = text.replace(EVENING_CSS_ANCHOR, EVENING_CSS_REPLACEMENT)
            changed = True
            print("[ПАТЧ] ✅ Патч 2в: CSS для вечерней карточки добавлен")
        else:
            print("[ПАТЧ] ❌ Патч 2в: якорь CSS не найден")

        if changed:
            UI_CABINET_PATH.write_text(text, encoding="utf-8")

    return ok


if __name__ == "__main__":
    print("=" * 55)
    print("Спринт 24 — Вечерний отчёт в правой панели")
    print("=" * 55)
    ok = apply()
    print()
    if ok:
        print("✅ Готово.")
        print()
        print("После вечерней прогулки в панели «отчёты» появится:")
        print("  🌆 Вечерняя прогулка")
        print("  🚶{агентов}  кв:{кварталов}  🤝{встреч}")
        print("  + список локаций и кто куда пошёл")
    else:
        print("⚠ Часть патча не применена — проверь выше.")
