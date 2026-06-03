"""
patch_daily_tick.py
===================
Два изменения в studio/cabinet/ui_cabinet.py:

1. Новая async функция _do_daily_tick() после _do_night_cycle()
   Последовательно: morning_checkout → evening_walk → night_cycle
   В конце переключает на вкладку "chronicles"

2. В хедере карты — до существующих кнопок — добавляем:
   • Кнопка «🖐 Тик» (главная, золотая)
   • Разделитель
   • Блок «📢 Событие»: input + select локаций + кнопка «Пустить слух»
   Существующие кнопки остаются — они полезны для ручного управления.
"""

from pathlib import Path
import sys

CABINET_PATH = Path("studio/cabinet/ui_cabinet.py")

ok_count  = 0
err_count = 0


def patch(path: Path, old: str, new: str, label: str):
    global ok_count, err_count
    text = path.read_text(encoding="utf-8")
    if old not in text:
        print(f"  MISS [{label}] — якорная строка не найдена")
        err_count += 1
        return
    if new.strip() in text:
        print(f"  SKIP [{label}] — патч уже применён")
        ok_count += 1
        return
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    print(f"  OK   [{label}]")
    ok_count += 1


print(f"\n=== patch_daily_tick.py ===")
print(f"Файл: {CABINET_PATH}\n")

# ════════════════════════════════════════════════════════════════════
# ПАТЧ 1 — добавляем _do_daily_tick() после _do_night_cycle()
# ════════════════════════════════════════════════════════════════════

OLD_AFTER_NIGHT = '''\
    # ═══ RIGHT PANEL ═══'''

NEW_AFTER_NIGHT = '''\
    # ═══ СУТОЧНЫЙ ТИК ═══

    async def _do_daily_tick():
        """
        Суточный Тик — один клик проживает весь день города.

        Последовательность:
          1. Утренний Чекаут (режимы + утренняя прогулка)
          2. Вечерняя прогулка (квантовые цепочки)
          3. Ночной цикл (Decay + Автономия)

        Фаза WORK (пайплайны цехов) не затрагивается — это отдельное решение Шефа.
        В конце открывает Хроники — читай что стряслось.
        """
        if state.get("_tick_running"):
            ui.notify("⏳ Тик уже идёт...", type="warning")
            return
        state["_tick_running"] = True

        # Блокируем кнопку визуально
        tick_btn = refs.get("tick_btn")
        if tick_btn:
            tick_btn.style(
                "opacity:0.5;cursor:not-allowed;"
                "background:rgba(212,175,55,0.04);"
                "border:1px solid rgba(212,175,55,0.12);"
            )

        try:
            # ── Шаг 1: Утро ──────────────────────────────────────
            await _do_morning_checkout()

            # ── Шаг 2: Вечер ─────────────────────────────────────
            await _do_evening_walk()

            # ── Шаг 3: Ночь ──────────────────────────────────────
            await _do_night_cycle()

            # ── Финал: открываем хроники ──────────────────────────
            _refresh_map()
            reload_all_agents()
            update_residents()
            update_city_zone()
            switch_tab("chronicles")
            update_right_panel("chronicles")

            ui.notify("✅ День прожит. Читай хроники.", type="positive")
            print("[TICK] 🖐 Суточный тик завершён")

        except Exception as e:
            import traceback; traceback.print_exc()
            try:
                ui.notify(f"❌ Тик упал: {e}", type="negative")
            except Exception:
                print(f"[TICK] ❌ {e}")
        finally:
            state["_tick_running"] = False
            # Разблокируем кнопку
            if tick_btn:
                tick_btn.style(
                    "opacity:1;cursor:pointer;"
                    "background:rgba(212,175,55,0.08);"
                    "border:1px solid rgba(212,175,55,0.35);"
                    "color:#d4af37;"
                )

    def _announce_event():
        """
        Пустить слух — записать глобальное событие в city_state.json.
        Выбранная локация получает временный буст веса для всех агентов.
        Буст применяется при следующем Суточном Тике (ttl=1 тик).
        """
        event_text = (refs.get("event_input") and refs["event_input"].value or "").strip()
        loc_name   = state.get("event_location", "")

        if not event_text:
            ui.notify("Напиши событие", type="warning")
            return

        try:
            from studio.city_walker import load_city_state, save_city_state, add_city_event

            city = load_city_state()

            # Глобальный буст: локация получает +0.4 к весу на 1 тик
            if loc_name:
                city["global_event_boost"] = {
                    "location": loc_name,
                    "power":    0.40,
                    "ttl":      1,          # сгорает после следующего тика
                    "reason":   event_text,
                }

            save_city_state(city)
            add_city_event(f"📢 {event_text}" + (f" → {loc_name}" if loc_name else ""))

            # Сброс поля
            if refs.get("event_input"):
                refs["event_input"].set_value("")

            msg = f"Слух пущен: «{event_text}»"
            if loc_name:
                msg += f" · агентов потянет в {loc_name}"
            ui.notify(msg, type="positive")
            _refresh_map()

        except Exception as e:
            ui.notify(f"⚠ {e}", type="negative")

    # ═══ RIGHT PANEL ═══'''

patch(CABINET_PATH, OLD_AFTER_NIGHT, NEW_AFTER_NIGHT,
      "_do_daily_tick + _announce_event: новые функции")


# ════════════════════════════════════════════════════════════════════
# ПАТЧ 2 — кнопка Тик + поле события в хедере карты
# ════════════════════════════════════════════════════════════════════

# Якорь — начало строки с кнопками в хедере карты
OLD_MAP_HEADER_BTNS = '''\
                        with ui.row().style("gap:6px"):
                            with ui.element("div").classes("cab-map-btn walk").style("cursor:pointer").on(
                                "click", lambda: ui.timer(0, _do_city_walk, once=True)
                            ):
                                ui.html("🚶 прогулка")'''

NEW_MAP_HEADER_BTNS = '''\
                        with ui.row().style("gap:6px"):
                            # ── СУТОЧНЫЙ ТИК — главная кнопка ──────────────────
                            _tick_el = ui.element("div").classes("cab-map-btn").style(
                                "cursor:pointer;"
                                "background:rgba(212,175,55,0.08);"
                                "border:1px solid rgba(212,175,55,0.35);"
                                "color:#d4af37;"
                                "font-weight:700;"
                                "font-size:0.72rem;"
                                "padding:5px 14px;"
                            ).on("click", lambda: ui.timer(0, _do_daily_tick, once=True))
                            with _tick_el:
                                ui.html("🖐 Тик")
                            refs["tick_btn"] = _tick_el

                            # ── РАЗДЕЛИТЕЛЬ ─────────────────────────────────────
                            ui.html(
                                '<div style="width:1px;height:20px;'
                                'background:rgba(255,255,255,0.08);'
                                'align-self:center;"></div>'
                            )

                            # ── ОБЪЯВИТЬ СОБЫТИЕ ────────────────────────────────
                            with ui.element("div").style(
                                "display:flex;align-items:center;gap:5px;"
                                "background:rgba(108,80,200,0.04);"
                                "border:1px solid rgba(108,80,200,0.18);"
                                "border-radius:8px;padding:3px 8px;"
                            ):
                                refs["event_input"] = ui.input(
                                    placeholder="📢 событие..."
                                ).props("borderless dense").style(
                                    "width:130px;"
                                    "font-family:JetBrains Mono;font-size:0.6rem;"
                                    "color:rgba(220,225,240,0.85);"
                                    "background:transparent;"
                                ).on("keydown.enter", lambda e: _announce_event())

                                # Select локаций из каталога
                                _locs = [
                                    loc["name"]
                                    for loc in _load_map_locations()
                                ]
                                state["event_location"] = _locs[0] if _locs else ""
                                if _locs:
                                    ui.select(
                                        _locs,
                                        value=_locs[0],
                                        on_change=lambda e: state.update(
                                            {"event_location": e.value}
                                        ),
                                    ).props("dense borderless dark options-dense").style(
                                        "font-family:JetBrains Mono;font-size:0.58rem;"
                                        "color:rgba(160,130,240,0.85);"
                                        "min-width:100px;max-width:140px;"
                                    )

                                ui.element("div").classes("cab-map-btn").style(
                                    "cursor:pointer;"
                                    "background:rgba(108,80,200,0.10);"
                                    "border:none;"
                                    "color:rgba(160,130,240,0.9);"
                                    "padding:3px 8px;"
                                    "font-size:0.6rem;"
                                ).on("click", lambda: _announce_event()).tooltip(
                                    "Буст локации на 1 тик"
                                )
                                with ui.element("div").style(
                                    "cursor:pointer;"
                                    "color:rgba(160,130,240,0.9);"
                                    "font-family:JetBrains Mono;font-size:0.6rem;"
                                    "padding:2px 6px;"
                                    "border-radius:4px;"
                                    "background:rgba(108,80,200,0.10);"
                                ).on("click", lambda: _announce_event()):
                                    ui.html("пустить слух")

                            # ── РАЗДЕЛИТЕЛЬ ─────────────────────────────────────
                            ui.html(
                                '<div style="width:1px;height:20px;'
                                'background:rgba(255,255,255,0.06);'
                                'align-self:center;"></div>'
                            )

                            # ── РУЧНЫЕ КНОПКИ (остаются для точечного управления)
                            with ui.element("div").classes("cab-map-btn walk").style("cursor:pointer").on(
                                "click", lambda: ui.timer(0, _do_city_walk, once=True)
                            ):
                                ui.html("🚶 прогулка")'''

patch(CABINET_PATH, OLD_MAP_HEADER_BTNS, NEW_MAP_HEADER_BTNS,
      "хедер карты: кнопка Тик + поле события")


# ════════════════════════════════════════════════════════════════════
# ПАТЧ 3 — добавляем tick_btn и event_input в refs
# ════════════════════════════════════════════════════════════════════

OLD_REFS = '''\
    refs = {
        "chat": None, "input": None,
        "prompt_bar": None, "prompt_name": None,
        "residents_list": None, "city_zone": None,
        "search_input": None, "search_results": None,
        "right_tabs": {}, "right_panels": {},'''

NEW_REFS = '''\
    refs = {
        "chat": None, "input": None,
        "prompt_bar": None, "prompt_name": None,
        "residents_list": None, "city_zone": None,
        "search_input": None, "search_results": None,
        "right_tabs": {}, "right_panels": {},
        "tick_btn": None,       # кнопка Суточного Тика
        "event_input": None,    # поле ввода события'''

patch(CABINET_PATH, OLD_REFS, NEW_REFS, "refs: tick_btn + event_input")


# ════════════════════════════════════════════════════════════════════
# ПАТЧ 4 — глобальный буст в compute_location_weights()
# city_walker.py: читаем global_event_boost из city_state
# ════════════════════════════════════════════════════════════════════

WALKER_PATH = Path("studio/city_walker.py")

OLD_WEIGHTS_RETURN = '''\
    # ══ КАРТРИДЖ НАМЕРЕНИЙ · Спринт 23 ══'''

NEW_WEIGHTS_RETURN = '''\
    # ══ ГЛОБАЛЬНОЕ СОБЫТИЕ · Суточный Тик ══
    # Шеф объявил событие → одна локация получает буст для ВСЕХ агентов.
    # Читаем из city_state.global_event_boost, применяем и не трогаем ttl здесь.
    # TTL декрементируется в run_daily_tick после прогулки (в _clear_event_boost).
    try:
        _cs_ev = {}
        if CITY_STATE.exists():
            import json as _jev
            _cs_ev = _jev.loads(CITY_STATE.read_text(encoding="utf-8"))
        _boost = _cs_ev.get("global_event_boost", {})
        _boost_loc   = _boost.get("location", "")
        _boost_power = float(_boost.get("power", 0.0))
        if _boost_loc and _boost_power > 0:
            for _loc_name in list(weights.keys()):
                if _loc_name == _boost_loc:
                    old_w = weights[_loc_name]
                    weights[_loc_name] = round(min(0.98, old_w + _boost_power), 3)
                    print(
                        f"[EVENT BOOST] 📢 {_boost_loc}: "
                        f"+{_boost_power:.2f} "
                        f"({old_w:.2f}→{weights[_loc_name]:.2f})"
                    )
                    break
    except Exception as _ev_err:
        pass
    # ══ END ГЛОБАЛЬНОЕ СОБЫТИЕ ══

    # ══ КАРТРИДЖ НАМЕРЕНИЙ · Спринт 23 ══'''

patch(WALKER_PATH, OLD_WEIGHTS_RETURN, NEW_WEIGHTS_RETURN,
      "city_walker: глобальный буст события в compute_location_weights")


# ════════════════════════════════════════════════════════════════════
# ИТОГ
# ════════════════════════════════════════════════════════════════════

print(f"\n{'='*55}")
print(f"Готово. {ok_count} патчей применено, {err_count} ошибок.")

if err_count == 0:
    print("""
Что изменилось:

  ui_cabinet.py:
    • _do_daily_tick() — один клик запускает утро→вечер→ночь
    • _announce_event() — пустить слух в конкретную локацию
    • refs: tick_btn, event_input
    • Хедер карты: кнопка «🖐 Тик» + поле события + select локаций

  city_walker.py:
    • compute_location_weights() читает global_event_boost из city_state
    • Буст применяется для всех агентов пока ttl > 0

Commit:
  feat: Суточный Тик + Объявить событие в Кабинете (Шаг 1 Оживления почвы)
""")
else:
    print(f"\n⚠️  Есть ошибки — проверь вывод выше.")
    sys.exit(1)
