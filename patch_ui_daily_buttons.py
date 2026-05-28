#!/usr/bin/env python3
"""
patch_ui_daily_buttons.py
════════════════════════════════════════════════════════════════
Добавляет две кнопки в хедер карты города (ui_cabinet.py):
  🌅 день    → run_morning_checkout() → отчёт в чат
  🌙 ночь    → run_night_cycle()      → отчёт в чат

Отчёт: «Агент X → GENIUS (reason)» — прямо в центральный чат,
чтобы видеть логику «в поле» без консоли.

Вставка: сразу после кнопки 📚 библиотека.
Студия «Шесть Пальцев» · Спринт 23 · 2026
"""

import sys
from pathlib import Path
from datetime import datetime

ROOT        = Path(".")
UI_CABINET  = ROOT / "studio" / "cabinet" / "ui_cabinet.py"

if not UI_CABINET.exists():
    print("❌ studio/cabinet/ui_cabinet.py не найден")
    sys.exit(1)

# ════════════════════════════════════════════════════════════════
# ФУНКЦИИ ДЛЯ ВСТАВКИ В ui_cabinet.py
# ════════════════════════════════════════════════════════════════

# 1. Два async-метода — вставляем после _do_city_walk()
NEW_FUNCTIONS = '''
    async def _do_morning_checkout():
        """Утренний Чекаут: рассчитать режим дня для всех агентов."""
        try:
            from studio.morning_checkout import run_morning_checkout
            ui.notify("🌅 Утренний чекаут...", type="info")

            result = await run_morning_checkout()
            modes   = result.get("modes", {})
            summary = result.get("summary", {})

            if not modes:
                ui.notify("⚠ Агентов не найдено", type="warning")
                return

            # ── Формируем отчёт в чат ──────────────────────────────
            MODE_ICONS = {
                "GENIUS":   "🔥",
                "NORMAL":   "⚡",
                "SAFE":     "🛡",
                "RECOVERY": "💤",
            }
            lines = [
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
            _hide_map()
            ui.notify(
                f"✅ Чекаут: {summary.get('GENIUS',0)}🔥 "
                f"{summary.get('RECOVERY',0)}💤",
                type="positive"
            )

        except Exception as e:
            import traceback; traceback.print_exc()
            try:
                ui.notify(f"❌ {e}", type="negative")
            except Exception:
                print(f"[CHECKOUT] ❌ {e}")

    async def _do_night_cycle():
        """Ночной цикл: Decay + Ночная Автономия для всех агентов."""
        try:
            from studio.night_cycle import run_night_cycle
            ui.notify("🌙 Ночной цикл...", type="info")

            result = await run_night_cycle()
            summary = result.get("summary", {})
            revolts = result.get("revolts", [])
            night_results = result.get("night_results", {})

            if not night_results:
                ui.notify("⚠ Агентов не найдено", type="warning")
                return

            # ── Формируем отчёт в чат ──────────────────────────────
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
            _hide_map()
            reload_all_agents()
            update_residents()
            update_city_zone()

            notify_text = f"✅ Ночь: {summary.get('REVOLT',0)}⚡ бунт"
            if revolts:
                notify_text += f" · {', '.join(revolts[:2])}"
            ui.notify(notify_text, type="positive")

        except Exception as e:
            import traceback; traceback.print_exc()
            try:
                ui.notify(f"❌ {e}", type="negative")
            except Exception:
                print(f"[NIGHT] ❌ {e}")

'''

# 2. HTML двух кнопок — вставляем после кнопки 📚 библиотека
NEW_BUTTONS = '''                            with ui.element("div").classes("cab-map-btn").style(
                                "cursor:pointer;"
                                "background:rgba(255,180,50,0.04);"
                                "border:1px solid rgba(255,180,50,0.18);"
                                "color:rgba(255,200,80,0.8);"
                            ).on("click", lambda: ui.timer(0, _do_morning_checkout, once=True)):
                                ui.html("🌅 день")
                            with ui.element("div").classes("cab-map-btn").style(
                                "cursor:pointer;"
                                "background:rgba(108,80,200,0.04);"
                                "border:1px solid rgba(108,80,200,0.22);"
                                "color:rgba(160,130,240,0.8);"
                            ).on("click", lambda: ui.timer(0, _do_night_cycle, once=True)):
                                ui.html("🌙 ночь")
'''

# ════════════════════════════════════════════════════════════════
# ЯКОРЯ ДЛЯ ВСТАВКИ
# ════════════════════════════════════════════════════════════════

# Якорь 1: вставляем функции ПОСЛЕ конца _do_city_walk
ANCHOR_FUNC = "        except Exception as e:\n            try:\n                ui.notify(f\"❌ {e}\", type=\"negative\")\n            except Exception:\n                print(f\"[CITY] ❌ {e}\")\n"

# Якорь 2: вставляем кнопки ПОСЛЕ кнопки 📚 библиотека
ANCHOR_BTN = """                            with ui.element("div").classes("cab-map-btn").style(
                                "cursor:pointer;"
                                "background:rgba(0,242,255,0.04);"
                                "border:1px solid rgba(0,242,255,0.15);"
                            ).on("click", lambda: open_ole_library()):
                                ui.html("📚 библиотека")"""

# ════════════════════════════════════════════════════════════════
# ПРИМЕНЕНИЕ ПАТЧА
# ════════════════════════════════════════════════════════════════

def apply_patch():
    code = UI_CABINET.read_text(encoding="utf-8")
    errors = []

    # ── Проверяем идемпотентность ──────────────────────────────
    if "_do_morning_checkout" in code:
        print("ℹ _do_morning_checkout уже есть — функции пропускаем")
        func_done = True
    else:
        func_done = False

    if "🌅 день" in code:
        print("ℹ Кнопки уже есть — пропускаем")
        btn_done = True
    else:
        btn_done = False

    if func_done and btn_done:
        print("✅ Патч уже применён полностью")
        return True

    # Бэкап
    backup = UI_CABINET.with_suffix(".py.bak_daily_btns")
    backup.write_text(code, encoding="utf-8")
    print(f"  ✅ Бэкап: {backup.name}")

    # ── Вставка функций ────────────────────────────────────────
    if not func_done:
        if ANCHOR_FUNC not in code:
            print("⚠ Якорь для функций не найден — пробуем запасной")
            # Запасной якорь: конец _do_city_walk по print
            fallback = '                print(f"[CITY] ❌ {e}")\n'
            if fallback in code:
                code = code.replace(fallback, fallback + NEW_FUNCTIONS, 1)
                print("  ✅ Функции вставлены (запасной якорь)")
            else:
                errors.append("Якорь для функций не найден")
                print("  ❌ Якорь для функций не найден")
        else:
            code = code.replace(ANCHOR_FUNC, ANCHOR_FUNC + NEW_FUNCTIONS, 1)
            print("  ✅ Функции _do_morning_checkout + _do_night_cycle вставлены")

    # ── Вставка кнопок ─────────────────────────────────────────
    if not btn_done:
        if ANCHOR_BTN not in code:
            print("⚠ Якорь для кнопок не найден — пробуем по тексту '📚 библиотека'")
            # Мягкий поиск по уникальному тексту
            SOFT = 'ui.html("📚 библиотека")'
            idx = code.find(SOFT)
            if idx == -1:
                errors.append("Якорь кнопок не найден")
                print("  ❌ Якорь кнопок не найден")
            else:
                # Вставляем после строки с библиотекой
                line_end = code.find("\n", idx) + 1
                code = code[:line_end] + NEW_BUTTONS + code[line_end:]
                print("  ✅ Кнопки вставлены (мягкий якорь)")
        else:
            code = code.replace(ANCHOR_BTN, ANCHOR_BTN + "\n" + NEW_BUTTONS, 1)
            print("  ✅ Кнопки 🌅 день + 🌙 ночь вставлены")

    if errors:
        print(f"\n⚠ Ошибки ({len(errors)}):")
        for e in errors:
            print(f"  • {e}")
        print("\nФайл НЕ перезаписан из-за ошибок.")
        return False

    UI_CABINET.write_text(code, encoding="utf-8")
    print(f"  ✅ ui_cabinet.py сохранён")
    return True


def main():
    print("=" * 60)
    print("ПАТЧ: КНОПКИ ДЕНЬ / НОЧЬ В КАБИНЕТЕ")
    print(f"Время: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)

    ok = apply_patch()

    print()
    if ok:
        print("✅ Готово. Перезапусти студию — в хедере карты появятся:")
        print("   🌅 день  — Утренний Чекаут (режимы + отчёт в чат)")
        print("   🌙 ночь  — Ночной Цикл (бунты + обиды + отчёт в чат)")
        print()
        print("Оба патча (patch_daily_cycle.py + этот) нужны оба.")
        print("Порядок: сначала patch_daily_cycle.py, потом этот.")
    else:
        print("⚠ Патч применён частично — проверь ошибки выше.")
        print("  Вставь вручную если якоря не нашлись:")
        print("  • _do_morning_checkout() и _do_night_cycle() — после _do_city_walk()")
        print("  • Кнопки 🌅/🌙 — в блок with ui.row().style(...) рядом с 📚")
    print("=" * 60)


if __name__ == "__main__":
    main()
