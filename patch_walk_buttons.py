#!/usr/bin/env python3
"""
patch_walk_buttons.py — Спринт 24: Кнопки утро/вечер в Кабинете

Что делает:
  1. 🌅 день — после morning_checkout() запускает run_city_walk_morning()
     1 квант на агента, разогрев перед раном
  2. Добавляет кнопку 🌆 вечер рядом с 🌙 ночь
     для ручного запуска вечерней прогулки (вечерняя уже есть автотриггером,
     но иногда хочется запустить вручную)

Запуск: python patch_walk_buttons.py
"""

from pathlib import Path

UI_CABINET_PATH = Path("studio/cabinet/ui_cabinet.py")

# ─────────────────────────────────────────────────────────
# ПАТЧ 1: _do_morning_checkout — добавляем вызов утренней прогулки
# ─────────────────────────────────────────────────────────

# Якорь — конец функции _do_morning_checkout, перед закрывающим except
MORNING_ANCHOR = '''            ui.notify(
                f"✅ Чекаут: {summary.get('GENIUS',0)}🔥 "
                f"{summary.get('RECOVERY',0)}💤",
                type="positive"
            )

        except Exception as e:
            import traceback; traceback.print_exc()
            try:
                ui.notify(f"❌ {e}", type="negative")
            except Exception:
                print(f"[CHECKOUT] ❌ {e}")'''

MORNING_REPLACEMENT = '''            ui.notify(
                f"✅ Чекаут: {summary.get('GENIUS',0)}🔥 "
                f"{summary.get('RECOVERY',0)}💤",
                type="positive"
            )

            # ── Утренняя прогулка: 1 квант, агент идёт на работу · Спринт 24 ──
            try:
                from studio.city_walker import run_city_walk_morning as _morning_walk
                ui.notify("🚶 Дорога на работу...", type="info")
                await _morning_walk(max_agents=0)
                _refresh_map()
                reload_all_agents()
                update_residents()
                update_city_zone()
                print("[CITY] 🌅 Утренняя прогулка завершена")
            except Exception as _wm_err:
                print(f"[CITY] ⚠ Утренняя прогулка: {_wm_err}")
            # ── END утренняя прогулка ──

        except Exception as e:
            import traceback; traceback.print_exc()
            try:
                ui.notify(f"❌ {e}", type="negative")
            except Exception:
                print(f"[CHECKOUT] ❌ {e}")'''


# ─────────────────────────────────────────────────────────
# ПАТЧ 2: добавить кнопку 🌆 вечер рядом с 🌙 ночь
# ─────────────────────────────────────────────────────────

# Якорь — кнопка ночь (уникальный кусок)
NIGHT_BTN_ANCHOR = '''                            with ui.element("div").classes("cab-map-btn").style(
                                "cursor:pointer;"
                                "background:rgba(108,80,200,0.04);"
                                "border:1px solid rgba(108,80,200,0.22);"
                                "color:rgba(160,130,240,0.8);"
                            ).on("click", lambda: ui.timer(0, _do_night_cycle, once=True)):
                                ui.html("🌙 ночь")'''

NIGHT_BTN_REPLACEMENT = '''                            with ui.element("div").classes("cab-map-btn").style(
                                "cursor:pointer;"
                                "background:rgba(50,150,100,0.04);"
                                "border:1px solid rgba(50,200,120,0.18);"
                                "color:rgba(80,220,140,0.8);"
                            ).on("click", lambda: ui.timer(0, _do_evening_walk, once=True)):
                                ui.html("🌆 вечер")
                            with ui.element("div").classes("cab-map-btn").style(
                                "cursor:pointer;"
                                "background:rgba(108,80,200,0.04);"
                                "border:1px solid rgba(108,80,200,0.22);"
                                "color:rgba(160,130,240,0.8);"
                            ).on("click", lambda: ui.timer(0, _do_night_cycle, once=True)):
                                ui.html("🌙 ночь")'''


# ─────────────────────────────────────────────────────────
# ПАТЧ 3: добавить функцию _do_evening_walk в ui_cabinet.py
# ─────────────────────────────────────────────────────────

# Вставляем перед _do_night_cycle
EVENING_FN_ANCHOR = "    async def _do_night_cycle():"

EVENING_FN_CODE = '''    async def _do_evening_walk():
        """Вечерняя прогулка — цепочка квантов пока есть силы. · Спринт 24"""
        try:
            from studio.city_walker import run_city_walk_evening as _evening_walk
            ui.notify("🌆 Агенты идут домой...", type="info")
            await _evening_walk(max_agents=0)
            _refresh_map()
            reload_all_agents()
            update_residents()
            update_city_zone()
            ui.notify("✅ Вечерняя прогулка завершена", type="positive")
        except Exception as e:
            try:
                ui.notify(f"❌ {e}", type="negative")
            except Exception:
                print(f"[CITY] ❌ вечерняя прогулка: {e}")

    async def _do_night_cycle():'''


# ─────────────────────────────────────────────────────────
# ПРИМЕНЕНИЕ
# ─────────────────────────────────────────────────────────

def apply():
    if not UI_CABINET_PATH.exists():
        print(f"[ПАТЧ] ❌ Не найден: {UI_CABINET_PATH}")
        return False

    text = UI_CABINET_PATH.read_text(encoding="utf-8")
    changed = False

    # Патч 1: утренняя прогулка
    if "_morning_walk" in text:
        print("[ПАТЧ] ⚠ Патч 1 (утренняя прогулка) уже применён")
    elif MORNING_ANCHOR in text:
        text = text.replace(MORNING_ANCHOR, MORNING_REPLACEMENT)
        changed = True
        print("[ПАТЧ] ✅ Патч 1: утренняя прогулка добавлена в _do_morning_checkout")
    else:
        print("[ПАТЧ] ❌ Патч 1: якорь не найден")

    # Патч 2: кнопка 🌆 вечер
    if "_do_evening_walk" in text and "🌆 вечер" in text:
        print("[ПАТЧ] ⚠ Патч 2 (кнопка вечер) уже применён")
    elif NIGHT_BTN_ANCHOR in text:
        text = text.replace(NIGHT_BTN_ANCHOR, NIGHT_BTN_REPLACEMENT)
        changed = True
        print("[ПАТЧ] ✅ Патч 2: кнопка 🌆 вечер добавлена")
    else:
        print("[ПАТЧ] ❌ Патч 2: якорь кнопки ночь не найден")

    # Патч 3: функция _do_evening_walk
    if "async def _do_evening_walk" in text:
        print("[ПАТЧ] ⚠ Патч 3 (_do_evening_walk) уже применён")
    elif EVENING_FN_ANCHOR in text:
        text = text.replace(EVENING_FN_ANCHOR, EVENING_FN_CODE)
        changed = True
        print("[ПАТЧ] ✅ Патч 3: функция _do_evening_walk добавлена")
    else:
        print("[ПАТЧ] ❌ Патч 3: якорь _do_night_cycle не найден")

    if changed:
        UI_CABINET_PATH.write_text(text, encoding="utf-8")

    return changed


if __name__ == "__main__":
    print("=" * 55)
    print("Спринт 24 — Кнопки утро/вечер в Кабинете")
    print("=" * 55)

    ok = apply()
    print()
    if ok:
        print("✅ Готово.")
        print()
        print("Итоговые кнопки в карте города:")
        print("  🚶 прогулка — старая (все агенты, без квантов)")
        print("  📚 библиотека — без изменений")
        print("  🌅 день — чекаут + утренняя прогулка (1 квант)")
        print("  🌆 вечер — вечерняя прогулка вручную (N квантов)")
        print("  🌙 ночь — ночной цикл")
        print()
        print("Автотриггер вечерней прогулки после рана — уже в pipeline.py")
    else:
        print("⚠ Изменений не было — возможно патч уже применён.")
