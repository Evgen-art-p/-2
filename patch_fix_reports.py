#!/usr/bin/env python3
"""
patch_fix_reports.py
════════════════════════════════════════════════════════════════
1. Убирает дублирование отчётов в центральный чат
2. Делает карточки в правой панели кликабельными (разворачивание)

Студия «Шесть Пальцев» · Спринт 23 · 2026
"""

import sys
from pathlib import Path
from datetime import datetime

UI_CABINET = Path("studio/cabinet/ui_cabinet.py")

if not UI_CABINET.exists():
    print("❌ studio/cabinet/ui_cabinet.py не найден")
    sys.exit(1)

# ════════════════════════════════════════════════════════════════
# 1. Убираем запись в chat_history из _do_morning_checkout
# ════════════════════════════════════════════════════════════════

OLD_CHAT_MORNING = '''            lines = [
                f"🌅 **Утренний Чекаут** · {datetime.now().strftime('%H:%M')}",
                f"GENIUS={summary.get('GENIUS',0)} · NORMAL={summary.get('NORMAL',0)} · "
                f"SAFE={summary.get('SAFE',0)} · RECOVERY={summary.get('RECOVERY',0)}",
                "",
            ]

            # Группируем по режиму — сначала интересные (RECOVERY и GENIUS)
            by_mode = {"GENIUS": [], "NORMAL": [], "SAFE": [], "RECOVERY": []}
            for key, data in modes.items():
                mode = data.get("mode", "NORMAL")
                folder = key.split("_")[0]
                reason = data.get("reason", "")
                energy = data.get("energy", 0.0)
                revolt = " ⚡ после бунта" if data.get("night_revolt") else ""
                by_mode[mode].append(f"  {MODE_ICONS[mode]} {folder}: {reason[:60]}{revolt}")

            for mode in ["RECOVERY", "GENIUS", "SAFE", "NORMAL"]:
                agents = by_mode[mode]
                if agents:
                    lines.append(f"**{MODE_ICONS[mode]} {mode}** ({len(agents)}):")
                    lines.extend(agents[:8])  # показываем первые 8 каждой группы
                    if len(agents) > 8:
                        lines.append(f"  ... и ещё {len(agents) - 8}")
                    lines.append("")

            report = "\\n".join(lines)
            state["chat_history"].append({
                "role": "assistant",
                "content": report,
                "time": datetime.now().strftime("%H:%M"),
            })
            update_chat()
            _hide_map()'''

NEW_CHAT_MORNING = '''            _hide_map()'''

# ════════════════════════════════════════════════════════════════
# 2. Убираем запись в chat_history из _do_night_cycle
# ════════════════════════════════════════════════════════════════

OLD_CHAT_NIGHT = '''            # ── Формируем отчёт в чат ──────────────────────────────
            lines = [
                f"🌙 **Ночной Цикл** · {datetime.now().strftime('%H:%M')}",
                f"SLEEP={summary.get('SLEEP',0)} · "
                f"RESTLESS={summary.get('RESTLESS',0)} · "
                f"REVOLT={summary.get('REVOLT',0)}",
                "",
            ]

            # Бунтари — самые интересные
            if revolts:
                lines.append(f"**⚡ Бунтари этой ночью** ({len(revolts)}):")
                for name in revolts[:10]:
                    # Найти причину из night_results
                    reason = ""
                    for key, data in night_results.items():
                        if data.get("agent_name") == name:
                            reason = data.get("reason", "")[:70]
                            break
                    lines.append(f"  ⚡ {name}: {reason}")
                if len(revolts) > 10:
                    lines.append(f"  ... и ещё {len(revolts) - 10}")
                lines.append("")

            # Тревожные
            restless = [
                d.get("agent_name", k.split("_")[0])
                for k, d in night_results.items()
                if d.get("decision") == "RESTLESS"
            ]
            if restless:
                lines.append(f"**😰 Тревожный сон** ({len(restless)}):")
                lines.append("  " + ", ".join(restless[:12]))
                lines.append("")

            # Resentment — кто накопил обиду
            resentful = [
                (d.get("agent_name", "?"), d.get("decay_changes", {}).get("resentment_grew", {}))
                for k, d in night_results.items()
                if d.get("decay_changes", {}).get("resentment_grew")
            ]
            if resentful:
                lines.append(f"**🔴 Зреет обида** ({len(resentful)}):")
                for name, res in resentful[:5]:
                    target = res.get("target", "?")
                    val    = res.get("new_value", 0)
                    lines.append(f"  {name} → {target}: resentment {val:.2f}")
                lines.append("")

            report = "\\n".join(lines)
            state["chat_history"].append({
                "role": "assistant",
                "content": report,
                "time": datetime.now().strftime("%H:%M"),
            })
            update_chat()
            _hide_map()'''

NEW_CHAT_NIGHT = '''            _hide_map()'''

# ════════════════════════════════════════════════════════════════
# 3. Новая _render_reports_tab с кликабельными карточками
# ════════════════════════════════════════════════════════════════

OLD_RENDER = '''    def _render_reports_tab():
        """Вкладка «отчёты» — история запусков Чекаута и Ночного цикла."""'''

NEW_RENDER = '''    def _render_reports_tab():
        """Вкладка «отчёты» — история запусков Чекаута и Ночного цикла.
        Карточки кликабельны — разворачивают детали."""'''

# ════════════════════════════════════════════════════════════════
# Разворачиваемые карточки — заменяем блок рендера карточки
# ════════════════════════════════════════════════════════════════

OLD_CARD = '''                with ui.element("div").style(
                    f"padding:9px 10px;margin:4px 6px;"
                    f"background:{bg};border:1px solid {border};"
                    f"border-radius:8px;"
                ):
                    # Заголовок
                    ui.html(
                        f\'<div style="display:flex;justify-content:space-between;\'
                        f\'align-items:center;margin-bottom:4px;">\'
                        f\'<span style="font-family:JetBrains Mono;font-size:0.65rem;\'
                        f\'color:{accent};font-weight:500;">{icon} {label}</span>\'
                        f\'<span style="font-family:JetBrains Mono;font-size:0.5rem;\'
                        f\'color:rgba(140,150,180,0.4);">{ts}</span>\'
                        f\'</div>\'
                    )
                    # Summary строка
                    ui.html(
                        f\'<div style="font-family:JetBrains Mono;font-size:0.6rem;\'
                        f\'margin-bottom:5px;">{summary_line}</div>\'
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
                                f\'<div style="font-family:JetBrains Mono;\'
                                f\'font-size:0.55rem;color:rgba(140,150,180,0.5);\'
                                f\'border-top:1px solid rgba(255,255,255,0.04);\'
                                f\'padding-top:4px;margin-top:2px;">\'
                                + "<br>".join(
                                    f\'💤 {a}\' for a in recovery[:4]
                                )
                                + ("..." if len(recovery) > 4 else "")
                                + "</div>"
                            )
                        if genius_revolt:
                            ui.html(
                                f\'<div style="font-family:JetBrains Mono;\'
                                f\'font-size:0.55rem;color:rgba(255,100,80,0.7);\'
                                f\'margin-top:2px;">\'
                                + "<br>".join(
                                    f\'⚡ {a}\' for a in genius_revolt[:3]
                                )
                                + "</div>"
                            )
                    else:
                        revolts  = details.get("revolts", [])
                        resentful = details.get("resentful", [])
                        if revolts:
                            ui.html(
                                f\'<div style="font-family:JetBrains Mono;\'
                                f\'font-size:0.55rem;color:rgba(255,100,80,0.8);\'
                                f\'border-top:1px solid rgba(255,255,255,0.04);\'
                                f\'padding-top:4px;margin-top:2px;">\'
                                + "<br>".join(
                                    f\'⚡ {r}\' for r in revolts[:5]
                                )
                                + ("..." if len(revolts) > 5 else "")
                                + "</div>"
                            )
                        if resentful:
                            ui.html(
                                f\'<div style="font-family:JetBrains Mono;\'
                                f\'font-size:0.55rem;color:rgba(220,100,100,0.7);\'
                                f\'margin-top:2px;">\'
                                + "<br>".join(
                                    f\'🔴 {r}\' for r in resentful[:3]
                                )
                                + "</div>"
                            )'''

NEW_CARD = '''                expanded_state = {"open": False}

                with ui.element("div").style(
                    f"padding:9px 10px;margin:4px 6px;"
                    f"background:{bg};border:1px solid {border};"
                    f"border-radius:8px;cursor:pointer;"
                ) as card:
                    # Заголовок — кликабельный
                    ui.html(
                        f\'<div style="display:flex;justify-content:space-between;\'
                        f\'align-items:center;margin-bottom:4px;">\'
                        f\'<span style="font-family:JetBrains Mono;font-size:0.65rem;\'
                        f\'color:{accent};font-weight:500;">{icon} {label}</span>\'
                        f\'<span style="font-family:JetBrains Mono;font-size:0.5rem;\'
                        f\'color:rgba(140,150,180,0.4);">{ts} ▾</span>\'
                        f\'</div>\'
                    )
                    # Summary строка — всегда видна
                    ui.html(
                        f\'<div style="font-family:JetBrains Mono;font-size:0.6rem;\'
                        f\'margin-bottom:3px;">{summary_line}</div>\'
                    )

                    # Детали — разворачиваются по клику
                    with ui.element("div").style("display:none;margin-top:6px;") as detail_block:
                        if is_morning:
                            for mode_key, mode_icon in [
                                ("RECOVERY","💤"), ("SAFE","🛡"),
                                ("GENIUS","🔥"), ("NORMAL","⚡")
                            ]:
                                agents = details.get(mode_key, [])
                                if agents:
                                    ui.html(
                                        f\'<div style="font-family:JetBrains Mono;\'
                                        f\'font-size:0.55rem;color:rgba(180,185,210,0.6);\'
                                        f\'border-top:1px solid rgba(255,255,255,0.04);\'
                                        f\'padding-top:4px;margin-top:3px;">\'
                                        f\'<b>{mode_icon} {mode_key} ({len(agents)})</b><br>\'
                                        + "<br>".join(a for a in agents[:6])
                                        + ("..." if len(agents) > 6 else "")
                                        + "</div>"
                                    )
                        else:
                            revolts_d   = details.get("revolts", [])
                            resentful_d = details.get("resentful", [])
                            restless_d  = details.get("restless", [])
                            if revolts_d:
                                ui.html(
                                    f\'<div style="font-family:JetBrains Mono;\'
                                    f\'font-size:0.55rem;color:rgba(255,120,80,0.85);\'
                                    f\'border-top:1px solid rgba(255,255,255,0.04);\'
                                    f\'padding-top:4px;margin-top:3px;">\'
                                    f\'<b>⚡ Бунтари ({len(revolts_d)})</b><br>\'
                                    + "<br>".join(f"⚡ {r}" for r in revolts_d[:8])
                                    + ("..." if len(revolts_d) > 8 else "")
                                    + "</div>"
                                )
                            if resentful_d:
                                ui.html(
                                    f\'<div style="font-family:JetBrains Mono;\'
                                    f\'font-size:0.55rem;color:rgba(220,100,100,0.75);\'
                                    f\'margin-top:3px;">\'
                                    f\'<b>🔴 Обиды ({len(resentful_d)})</b><br>\'
                                    + "<br>".join(f"🔴 {r}" for r in resentful_d[:5])
                                    + "</div>"
                                )
                            if restless_d:
                                ui.html(
                                    f\'<div style="font-family:JetBrains Mono;\'
                                    f\'font-size:0.55rem;color:rgba(200,180,80,0.6);\'
                                    f\'margin-top:3px;">\'
                                    f\'<b>😰 Тревожный сон ({len(restless_d)})</b><br>\'
                                    + ", ".join(restless_d[:10])
                                    + "</div>"
                                )

                    def _toggle(e, db=detail_block, es=expanded_state):
                        es["open"] = not es["open"]
                        db.style("display:block;" if es["open"] else "display:none;")

                    card.on("click", _toggle)'''


def apply():
    code = UI_CABINET.read_text(encoding="utf-8")
    errors = []

    backup = UI_CABINET.with_suffix(".py.bak_fix_reports")
    backup.write_text(code, encoding="utf-8")
    print(f"  ✅ Бэкап: {backup.name}")

    # 1. Убираем отчёт из чата (morning)
    if OLD_CHAT_MORNING in code:
        code = code.replace(OLD_CHAT_MORNING, NEW_CHAT_MORNING, 1)
        print("  ✅ Убран отчёт из чата (morning)")
    elif "_hide_map()" in code and "update_chat()" not in code:
        print("  ℹ Morning chat уже убран")
    else:
        errors.append("Якорь morning chat не найден")

    # 2. Убираем отчёт из чата (night)
    if OLD_CHAT_NIGHT in code:
        code = code.replace(OLD_CHAT_NIGHT, NEW_CHAT_NIGHT, 1)
        print("  ✅ Убран отчёт из чата (night)")
    else:
        print("  ℹ Night chat уже убран или якорь не найден — пропускаем")

    # 3. Кликабельные карточки
    if "expanded_state" in code:
        print("  ℹ Карточки уже кликабельны")
    elif OLD_CARD in code:
        code = code.replace(OLD_CARD, NEW_CARD, 1)
        print("  ✅ Карточки стали кликабельными")
    else:
        errors.append("Якорь карточек не найден")

    if errors:
        print(f"\n⚠ Ошибки ({len(errors)}):")
        for e in errors:
            print(f"  • {e}")

    UI_CABINET.write_text(code, encoding="utf-8")
    print("  ✅ ui_cabinet.py сохранён")
    return not errors


def main():
    print("=" * 60)
    print("ПАТЧ: фикс отчётов — убираем дубль, карточки кликабельны")
    print(f"Время: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)

    ok = apply()

    print()
    if ok:
        print("✅ Готово. Перезапусти студию.")
        print()
        print("Теперь:")
        print("  • Отчёт только в правой вкладке, не в чате")
        print("  • Карточка кликается → разворачивает детали")
    else:
        print("⚠ Частично применён — проверь ошибки выше")
    print("=" * 60)


if __name__ == "__main__":
    main()
