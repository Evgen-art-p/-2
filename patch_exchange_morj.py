# patch_exchange_morj.py
# ─────────────────────────────────────────────────────────────
# ПОДКЛЮЧАЕТ МОРЖА (A02) К КНОПКЕ РЫНОК НА БИРЖЕ
#
# Логика Шефа: Искра смотрит бар (всегда). Дальше:
#   t1_status == NOT_FOUND          → все спят, конец (никого не будим)
#   t1_status == DETECTED/CONFIRMED → «есть сигнал, думайте!» → будим Моржа
#
# Морж — НЕ шлагбаум. Он голос: слышит Искру из trading_state,
# смотрит Аллигатор + резинку, кладёт факт на стол. Решают трейдеры.
# (Ганс, Паникёр подключатся сюда же, когда оживут — тем же манером.)
#
# Три врезки в studio/economy/ui_exchange.py:
#   1. После отчёта Искры в run_market — ветка «сигнал есть → run_morj»
#   2. Чат: маршрут A02 → chat_with_morj (разблокировка пузырька Моржа)
#   3. last_run Моржа в state (чтобы чат знал его последний взгляд)
#
# Идемпотентен. Бэкап: ui_exchange.py.bak_morj
# ─────────────────────────────────────────────────────────────

import shutil
from pathlib import Path

UI = Path("studio/economy/ui_exchange.py")


def main():
    if not UI.exists():
        print(f"❌ Не найден {UI} — запусти из корня репо (где папка studio/)")
        return

    txt = UI.read_text(encoding="utf-8")
    original = txt
    changed = []

    # ── ВРЕЗКА 1: после отчёта Искры будим Моржа если сигнал есть ──
    if "run_morj" in txt:
        print("• run_morj уже в каркасе — пропускаю врезку 1")
    else:
        anchor1 = '        ui.notify(f"✴️ Искра: {sig.get(\'t1_status\',\'—\')}", type="positive")'
        morj_block = anchor1 + '''

        # ── ЕСТЬ СИГНАЛ? → будим Моржа (и остальных сенсоров) ────
        # Закон Шефа: Искра молчит (NOT_FOUND) → цех спит. Крикнула
        # сигнал → просыпаются сенсоры. Морж не гейт — он голос:
        # кладёт факт (пасть, резинка, масштаб) на стол. Решат трейдеры.
        t1 = sig.get("t1_status", "NOT_FOUND")
        if t1 in ("DETECTED", "CONFIRMED"):
            ui.notify("📣 Искра: есть сигнал — бужу Моржа...", type="info")
            try:
                from studio.modules.trading.morj_live import run_morj
                mr = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: run_morj(symbol="XAUUSD", timeframe="H4"))
            except Exception as e:
                ui.notify(f"Морж не проснулся: {e}", type="negative")
                mr = {"ok": False}

            if mr.get("ok"):
                msig = mr.get("signal", {})
                rb   = mr.get("rubber_band", {})
                state["reports"]["A02"] = mr.get("narrative", "") or mr.get("raw", "")
                # Приборы Моржа в state (как iskra_signal/iskra_stats)
                state["morj_signal"] = msig
                state["morj_stats"]  = mr.get("stats", {})
                state["morj_rubber"] = rb
                state["morj_market"] = mr.get("market", {})
                # Рабочая память Моржа для чата (как у Искры)
                state["morj_last_run"] = {
                    "narrative":   mr.get("narrative", ""),
                    "signal":      msig,
                    "market":      mr.get("market", {}),
                    "rubber_band": rb,
                    "iskra_status": mr.get("iskra_status", t1),
                }
                state["chat_history"].append({
                    "role": "assistant", "agent": "A02",
                    "content": (f"🦭 Посмотрел. Пасть: "
                                f"{msig.get('morj_status','—')}, резинка "
                                f"{'натянута' if msig.get('tension_peak') else 'вяло'}. "
                                f"Отчёт справа.")})
                update_chat_display()
                update_avatar_states()
                ui.notify(f"🦭 Морж: {msig.get('morj_status','—')}", type="positive")
            else:
                ui.notify("🦭 Морж смолчал (нет данных или сбой)", type="warning")'''

        if anchor1 in txt:
            txt = txt.replace(anchor1, morj_block, 1)
            changed.append("1) РЫНОК будит Моржа при сигнале Искры")
        else:
            print("⚠️  не нашёл якорь 1 (ui.notify Искра) — пропуск")

    # ── ВРЕЗКА 2: маршрут чата A02 → chat_with_morj ──────────────
    if "chat_with_morj" in txt:
        print("• chat_with_morj уже в каркасе — пропускаю врезку 2")
    else:
        anchor2 = '''        # Пока живой чат подключён только для Искры (A01). Остальные —
        # подключим когда дойдём до них по цепочке.
        if agent_id != "A01":'''
        new2 = '''        # Живой чат: Искра (A01) и Морж (A02). Остальные — по очереди.
        if agent_id == "A02":
            ui.notify("🦭 Морж смотрит...", type="info")
            try:
                from studio.modules.trading.morj_live import chat_with_morj
                dialog = [m for m in state["chat_history"]
                          if m.get("role") in ("user", "assistant") and m.get("content")]
                reply = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: chat_with_morj(msg, state.get("morj_last_run"), dialog))
            except Exception as e:
                reply = f"⚠️ Морж не смог ответить: {e}"
            state["chat_history"].append({
                "role": "assistant", "agent": "A02", "content": reply})
            update_chat_display()
            return

        if agent_id != "A01":'''
        if anchor2 in txt:
            txt = txt.replace(anchor2, new2, 1)
            changed.append("2) чат A02 → chat_with_morj")
        else:
            print("⚠️  не нашёл якорь 2 (блокировка чата) — пропуск")

    # ── ВРЕЗКА 3: morj_last_run в начальный state ────────────────
    if '"morj_last_run": None' in txt:
        print("• morj_last_run уже в начальном state — пропускаю врезку 3")
    else:
        anchor3 = '        "running": False,          # идёт прогон РЫНОК'
        new3 = (anchor3 + '\n'
                '        "morj_last_run": None,     # рабочая память Моржа для чата')
        if anchor3 in txt:
            txt = txt.replace(anchor3, new3, 1)
            changed.append("3) morj_last_run в state")
        else:
            print("⚠️  не нашёл якорь 3 (running в state) — пропуск (не критично)")

    # ── ВРЕЗКА 4: приборы Моржа в update_stats_panel ────────────
    if "morj_signal" in txt and 'state["active_agent"] == "A02"' in txt:
        print("• приборы Моржа уже в панели — пропускаю врезку 4")
    else:
        anchor4 = '''        # Только для Искры показываем её приборы; для других — заглушка.
        if state["active_agent"] != "A01":
            with stats_ref["element"]:
                ui.html('<div style="color:rgba(255,255,255,0.3); font-size:11px; '
                        'padding:10px; text-align:center;">Приборы появятся при подключении агента</div>')
            return'''
        new4 = '''        # ─── Приборы Моржа (A02): пасть + резинка + стата ───
        if state["active_agent"] == "A02":
            msig = state.get("morj_signal", {})
            mst  = state.get("morj_stats", {})
            rb   = state.get("morj_rubber", {})
            mmk  = state.get("morj_market", {})
            if not msig:
                with stats_ref["element"]:
                    ui.html('<div style="color:rgba(255,255,255,0.3); font-size:11px; '
                            'padding:10px; text-align:center;">Морж ещё не смотрел — '
                            'нажми РЫНОК (нужен сигнал Искры)</div>')
                return
            mstatus = msig.get("morj_status", "—")
            st_color = {"AWAKE": "#00ff88", "WAKING": "#ffb400",
                        "SLEEPING": "rgba(255,255,255,0.4)"}.get(mstatus, "rgba(255,255,255,0.4)")
            peak = msig.get("tension_peak")
            peak_txt = "🔴 НА ПРЕДЕЛЕ" if peak else "вяло"
            peak_color = "#ff5050" if peak else "rgba(255,255,255,0.4)"
            ratio = rb.get("tension_ratio")
            ratio_txt = f"{ratio}" if ratio is not None else "—"
            dist = rb.get("distance_now")
            dist_txt = f"{dist} пт" if dist is not None else "—"
            wave1 = "✓" if msig.get("wave_1_validated") else "—"
            alst = (msig.get("alligator_state") or {})
            bopen = alst.get("bars_open", "—")
            with stats_ref["element"]:
                ui.html(f\'\'\'
                <div style="padding:10px 12px; font-family:\\'JetBrains Mono\\',monospace;">
                  <div style="display:flex; justify-content:space-between; margin-bottom:7px;">
                    <span style="color:rgba(255,255,255,0.45); font-size:10px;">ПАСТЬ</span>
                    <span style="color:{st_color}; font-size:11px; font-weight:700;">{mstatus}</span>
                  </div>
                  <div style="display:flex; justify-content:space-between; margin-bottom:7px;">
                    <span style="color:rgba(255,255,255,0.45); font-size:10px;">РЕЗИНКА</span>
                    <span style="color:{peak_color}; font-size:11px; font-weight:700;">{peak_txt}</span>
                  </div>
                  <div style="display:flex; justify-content:space-between; margin-bottom:7px;">
                    <span style="color:rgba(255,255,255,0.45); font-size:10px;">НАТЯЖЕНИЕ</span>
                    <span style="color:rgba(0,204,255,0.9); font-size:11px;">{ratio_txt} · {dist_txt}</span>
                  </div>
                  <div style="display:flex; justify-content:space-between; margin-bottom:10px;">
                    <span style="color:rgba(255,255,255,0.45); font-size:10px;">ВОЛНА 1 / БАРОВ ОТКРЫТ</span>
                    <span style="color:rgba(255,255,255,0.7); font-size:11px;">{wave1} · {bopen}</span>
                  </div>
                  <div style="border-top:1px solid rgba(255,255,255,0.08); padding-top:8px;
                              color:rgba(255,255,255,0.35); font-size:9px; line-height:1.7;">
                    взглядов: {mst.get("runs",0)} ·
                    проснулся: {mst.get("awake",0)} ·
                    спал: {mst.get("sleeping",0)} ·
                    пиков: {mst.get("tension_peaks",0)}
                    <br>{mmk.get("symbol","")} {mmk.get("timeframe","")} · {mmk.get("bar_time","")}
                  </div>
                </div>
                \'\'\')
            return

        # Только для Искры показываем её приборы; для других — заглушка.
        if state["active_agent"] != "A01":
            with stats_ref["element"]:
                ui.html('<div style="color:rgba(255,255,255,0.3); font-size:11px; '
                        'padding:10px; text-align:center;">Приборы появятся при подключении агента</div>')
            return'''
        if anchor4 in txt:
            txt = txt.replace(anchor4, new4, 1)
            changed.append("4) приборы Моржа в панели")
        else:
            print("⚠️  не нашёл якорь 4 (заглушка панели) — пропуск")

    if txt == original:
        print("\n✓ Изменений нет — патч уже применён ранее.")
        return

    backup = UI.with_suffix(".py.bak_morj")
    shutil.copy2(UI, backup)
    UI.write_text(txt, encoding="utf-8")

    print("\n✅ Патч применён. Врезки:")
    for c in changed:
        print(f"   • {c}")
    print(f"\n💾 Бэкап: {backup}")
    print("Проверь:  python -c \"import ast; ast.parse(open('studio/economy/ui_exchange.py',encoding='utf-8').read()); print('OK')\"")


if __name__ == "__main__":
    main()
