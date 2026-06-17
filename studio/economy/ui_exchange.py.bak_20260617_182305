# studio/economy/ui_exchange.py
# ─────────────────────────────────────────────────────────────
# БИРЖА · КАРКАС СОВЕТА (Торговый Цех)
# Версия: 0.1 · Спринт 45 · 2026-06-16 · ТОЛЬКО СКЕЛЕТ
#
# Отдельная страница /exchange. Раскладка скопирована с воркшопа
# (studio/workshop/ui.py) — НЕ вшита в него, живёт здесь.
# Кнопка «Биржа» в дашборде перекидывает сюда (ui.navigate.to).
#
# СЕЙЧАС: чистый каркас. Хедер — пузырьки трейдеров A01–A09,
# левая колонка — только загрузчик, центр — чат + отчёты,
# правая — аватар активного агента.
#
# ПОКА НЕТ (следующими шагами): запуск живого Совета, снятие
# заглушки из hooks.run_live_council, чтение feed_out, ордера.
# ─────────────────────────────────────────────────────────────

from pathlib import Path
from nicegui import ui, app
import asyncio

# CSS воркшопа переиспользуем как есть — каркас «как воркшоп».
from studio.workshop.styles import IDENTITY_BUREAU_CSS

# Трейдеры Совета. id → подпись/иконка. Источник — info.json каждого
# агента в studio/modules/trading/AXX/. Порядок = порядок цепочки.
TRADING_COUNCIL = [
    {"id": "A01", "label": "Искра",       "icon": "✴️"},
    {"id": "A02", "label": "Морж",        "icon": "🦭"},
    {"id": "A03", "label": "Паникёр",     "icon": "😱"},
    {"id": "A04", "label": "Ганс",        "icon": "🎯"},
    {"id": "A05", "label": "Архивариус",  "icon": "📚"},
    {"id": "A06", "label": "Брут",        "icon": "🪨"},
    {"id": "A07", "label": "Авантюрист",  "icon": "🎲"},
    {"id": "A08", "label": "Консерватор", "icon": "⚖️"},
    {"id": "A09", "label": "Исполнитель", "icon": "🎬"},
]

# Папка трейдеров — отсюда позже возьмём аватары/промты.
_TRADING_DIR = Path("studio/modules/trading")


def _agent_label(agent_id: str) -> str:
    for a in TRADING_COUNCIL:
        if a["id"] == agent_id:
            return a["label"]
    return agent_id


def page_exchange() -> None:
    """Страница Биржи — каркас Совета. Пока только скелет UI."""

    # Локальное состояние страницы (по образцу воркшопа, урезано).
    state = {
        "active_agent": "A01",     # активный пузырёк
        "chat_history": [],        # лента чата (личный разговор с агентом)
        "reports": {},             # отчёты агентов: agent_id → текст (размышления)
        "uploaded_files": [],      # загрузчик слева
        "iskra_signal": {},        # последний signal Искры → цифры под аватаром
        "iskra_last_run": None,     # рабочий контекст прогона (для чата в рабочем режиме)
        "iskra_stats": {},         # статистика Искры
        "market": {},              # symbol/timeframe/bar_time/point
        "running": False,          # идёт прогон РЫНОК
        "morj_last_run": None,     # рабочая память Моржа для чата
        "panic_last_run": None,    # рабочая память Паникёра для чата
        "hans_last_run": None,     # рабочая память Ганса для чата
    }

    # Refs на элементы UI — заполняются при сборке layout.
    chat_log_ref = {"element": None}
    viewer_ref   = {"element": None}
    files_ref    = {"element": None}
    avatar_ref   = {"element": None}
    stats_ref    = {"element": None}   # панель цифр под аватаром
    avatars_ref  = {"elements": {}}
    input_ref    = {"element": None}

    ui.add_head_html(f"<style>{IDENTITY_BUREAU_CSS}</style>")
    # Точечная правка только для Биржи: в воркшопе .right-col прижат вниз
    # (flex-end), т.к. под аватаром там RUNS и кнопки. У нас правая колонка
    # пока только аватар — поднимаем его наверх.
    ui.add_head_html("""<style>
    .right-col{ justify-content: flex-start !important; }
    </style>""")
    ui.html('<div id="bg"></div>')

    # ── Обновление ленты чата ────────────────────────────────
    def update_chat_display():
        if not chat_log_ref["element"]:
            return
        chat_log_ref["element"].clear()
        with chat_log_ref["element"]:
            if not state["chat_history"]:
                ui.html('<div class="chat-msg-system">SYSTEM: Биржа готова. '
                        'Каркас Совета — логика подключается следующими шагами.</div>')
            else:
                for msg in state["chat_history"]:
                    role = msg.get("role", "user")
                    content = msg.get("content", "")
                    who = msg.get("agent", "")
                    if role == "user":
                        ui.html(f'<div class="chat-msg-user"><b>ШЕФ:</b> {content}</div>')
                    else:
                        ui.html(f'<div class="chat-msg-assistant"><b>{who}:</b> {content}</div>')

    # ── Обновление viewer (отчёты) ───────────────────────────
    def update_viewer(content: str):
        if not viewer_ref["element"]:
            return
        viewer_ref["element"].clear()
        with viewer_ref["element"]:
            ui.markdown(content)

    # ── Аватар активного агента (правая колонка) ─────────────
    def update_avatar():
        if not avatar_ref["element"]:
            return
        agent_id = state["active_agent"]
        label = _agent_label(agent_id)
        avatar_ref["element"].clear()
        with avatar_ref["element"]:
            # Аватар ищем в static/avatars/trading/AXX.png; если нет —
            # onerror прячет img и остаётся подпись.
            ui.html(f'''
                <div style="position:relative; width:100%; height:100%; min-height:200px;">
                    <img src="/static/avatars/trading/{agent_id}.png"
                         style="width:100%; height:100%; object-fit:cover;
                                border-radius:12px; opacity:0.85;"
                         onerror="this.style.display='none'">
                    <div style="position:absolute; bottom:0; left:0; right:0;
                                padding:15px; background:linear-gradient(transparent, rgba(0,0,0,0.8));
                                border-radius:0 0 12px 12px;">
                        <div style="font-size:0.65rem; color:rgba(255,255,255,0.5);
                                    letter-spacing:0.15em;">АКТИВНЫЙ АГЕНТ</div>
                        <div style="font-size:1.3rem; font-weight:700; color:#00ff88;">{agent_id}</div>
                        <div style="font-size:0.8rem; color:rgba(255,255,255,0.8);">{label}</div>
                    </div>
                </div>
            ''')

    # ── Панель цифр под аватаром (статус/Точка Ноль/колокол/стата) ──
    def update_stats_panel():
        if not stats_ref["element"]:
            return
        sig = state["iskra_signal"]
        st  = state["iskra_stats"]
        mk  = state["market"]
        stats_ref["element"].clear()

        # ─── Приборы Моржа (A02): пасть + резинка + стата ───
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
                ui.html(f'''
                <div style="padding:10px 12px; font-family:\'JetBrains Mono\',monospace;">
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
                ''')
            return

        # ─── Приборы Ганса (A04): фрактал + Красная + поглощение ───
        if state["active_agent"] == "A04":
            hsig = state.get("hans_signal", {})
            hst  = state.get("hans_stats", {})
            hmk  = state.get("hans_market", {})
            if not hsig:
                with stats_ref["element"]:
                    ui.html('<div style="color:rgba(255,255,255,0.3); font-size:11px; '
                            'padding:10px; text-align:center;">Ганс ещё не выходил на след — '
                            'нажми РЫНОК (нужен сигнал Искры)</div>')
                return
            valid = hsig.get("fractal_valid")
            v_txt = "🎯 ВНЕ КРАСНОЙ" if valid else "пусто"
            v_color = "#00ff88" if valid else "rgba(255,255,255,0.4)"
            side = hsig.get("fractal_side") or "—"
            fprice = hsig.get("fractal_price")
            fprice_txt = f"{fprice}" if fprice is not None else "—"
            absr = hsig.get("absorption_ratio")
            absr_txt = f"{absr}" if absr is not None else "—"
            abs_color = "#ff5050" if (absr is not None and absr >= 0.7) else "rgba(255,255,255,0.7)"
            with stats_ref["element"]:
                ui.html(f'''
                <div style="padding:10px 12px; font-family:\'JetBrains Mono\',monospace;">
                  <div style="display:flex; justify-content:space-between; margin-bottom:7px;">
                    <span style="color:rgba(255,255,255,0.45); font-size:10px;">ФРАКТАЛ</span>
                    <span style="color:{v_color}; font-size:11px; font-weight:700;">{v_txt}</span>
                  </div>
                  <div style="display:flex; justify-content:space-between; margin-bottom:7px;">
                    <span style="color:rgba(255,255,255,0.45); font-size:10px;">СТОРОНА</span>
                    <span style="color:rgba(255,255,255,0.7); font-size:11px;">{side}</span>
                  </div>
                  <div style="display:flex; justify-content:space-between; margin-bottom:7px;">
                    <span style="color:rgba(255,255,255,0.45); font-size:10px;">ЦЕНА (ОРИЕНТИР)</span>
                    <span style="color:rgba(0,204,255,0.9); font-size:11px;">{fprice_txt}</span>
                  </div>
                  <div style="display:flex; justify-content:space-between; margin-bottom:10px;">
                    <span style="color:rgba(255,255,255,0.45); font-size:10px;">ПОГЛОЩЕНИЕ</span>
                    <span style="color:{abs_color}; font-size:11px;">{absr_txt}</span>
                  </div>
                  <div style="border-top:1px solid rgba(255,255,255,0.08); padding-top:8px;
                              color:rgba(255,255,255,0.35); font-size:9px; line-height:1.7;">
                    выходов: {hst.get("runs",0)} ·
                    добыча: {hst.get("valid",0)} ·
                    мёртвых: {hst.get("dead",0)} ·
                    пусто: {hst.get("none",0)}
                    <br>{hmk.get("symbol","")} {hmk.get("timeframe","")} · {hmk.get("bar_time","")}
                  </div>
                </div>
                ''')
            return

        # Только для Искры показываем её приборы; для других — заглушка.
        if state["active_agent"] != "A01":
            with stats_ref["element"]:
                ui.html('<div style="color:rgba(255,255,255,0.3); font-size:11px; '
                        'padding:10px; text-align:center;">Приборы появятся при подключении агента</div>')
            return

        t1 = sig.get("t1_status", "—")
        t1_color = {"DETECTED": "#ffb400", "CONFIRMED": "#00ff88",
                    "NOT_FOUND": "rgba(255,255,255,0.4)"}.get(t1, "rgba(255,255,255,0.4)")
        zero = sig.get("zero_point_price")
        zero_txt = f"{zero}" if zero else "—"
        bell = "🔔 ЗВОНИТ" if sig.get("exit_bell") else "—"
        bell_color = "#ff5050" if sig.get("exit_bell") else "rgba(255,255,255,0.4)"

        with stats_ref["element"]:
            ui.html(f'''
            <div style="padding:10px 12px; font-family:'JetBrains Mono',monospace;">
              <div style="display:flex; justify-content:space-between; margin-bottom:7px;">
                <span style="color:rgba(255,255,255,0.45); font-size:10px;">СТАТУС</span>
                <span style="color:{t1_color}; font-size:11px; font-weight:700;">{t1}</span>
              </div>
              <div style="display:flex; justify-content:space-between; margin-bottom:7px;">
                <span style="color:rgba(255,255,255,0.45); font-size:10px;">ТОЧКА НОЛЬ</span>
                <span style="color:rgba(0,204,255,0.9); font-size:11px;">{zero_txt}</span>
              </div>
              <div style="display:flex; justify-content:space-between; margin-bottom:10px;">
                <span style="color:rgba(255,255,255,0.45); font-size:10px;">КОЛОКОЛ</span>
                <span style="color:{bell_color}; font-size:11px;">{bell}</span>
              </div>
              <div style="border-top:1px solid rgba(255,255,255,0.08); padding-top:8px;
                          color:rgba(255,255,255,0.35); font-size:9px; line-height:1.7;">
                прогонов: {st.get("runs",0)} ·
                нашла: {st.get("detected",0)} ·
                подтвердилось: {st.get("confirmed",0)} ·
                аннулировано: {st.get("annulled",0)}
                <br>{mk.get("symbol","")} {mk.get("timeframe","")} · {mk.get("bar_time","")}
              </div>
            </div>
            ''')

    # ── РЫНОК: поднять контур + прогнать Искру ───────────────
    async def run_market():
        if state["running"]:
            ui.notify("Прогон уже идёт...", type="warning")
            return
        state["running"] = True
        ui.notify("📡 Поднимаю контур, бужу Искру...", type="info")
        try:
            from studio.modules.trading.iskra_live import run_iskra
            # Тяжёлый вызов (терминал + ядро + модель) — в отдельном потоке,
            # чтобы UI не подвисал.
            result = await asyncio.get_event_loop().run_in_executor(
                None, lambda: run_iskra(symbol="XAUUSD", timeframe="H4"))
        except Exception as e:
            state["running"] = False
            ui.notify(f"Сбой прогона: {e}", type="negative")
            return
        state["running"] = False

        if not result.get("ok"):
            err = result.get("error", "неизвестная ошибка")
            # Искра честно говорит в чат, если терминал недоступен
            state["chat_history"].append({
                "role": "assistant", "agent": "A01",
                "content": f"⚠️ {err}"})
            update_chat_display()
            ui.notify(err, type="negative", timeout=6000)
            return

        # Голос Искры → в отчёт (viewer), переключаемся на неё
        state["active_agent"] = "A01"
        state["iskra_signal"] = result.get("signal", {})
        state["iskra_stats"]  = result.get("stats", {})
        state["market"]       = result.get("market", {})
        state["reports"]["A01"] = result.get("narrative", "") or result.get("raw", "")

        # Рабочий контекст прогона — память для чата в рабочем режиме.
        # Когда Шеф спросит Искру в чате, она увидит ЭТО и ответит
        # конкретно про свой последний прогон, а не общими словами.
        state["iskra_last_run"] = {
            "narrative": result.get("narrative", ""),
            "signal":    result.get("signal", {}),
            "market":    result.get("market", {}),
        }

        update_avatar()
        update_avatar_states()
        update_stats_panel()
        sig = state["iskra_signal"]
        update_viewer(
            f"# ✴️ Искра (A01)\n\n"
            f"**Статус:** {sig.get('t1_status','—')}  ·  "
            f"**Дивергенция:** {sig.get('divergence','—')}\n\n"
            f"---\n\n{result.get('narrative','') or '*(нет текста)*'}"
        )
        # В чат — НЕ дубль текста, а приглашение к разговору.
        # Полный голос остался в отчёте; здесь только метка прогона.
        state["chat_history"].append({
            "role": "assistant", "agent": "A01",
            "content": f"✴️ Отработала рынок — статус {sig.get('t1_status','—')}. "
                       f"Отчёт справа. Спроси, если хочешь разобрать."})
        update_chat_display()
        ui.notify(f"✴️ Искра: {sig.get('t1_status','—')}", type="positive")

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
                ui.notify("🦭 Морж смолчал (нет данных или сбой)", type="warning")

            # ── EXCHANGE_PANIKYOR: Паникёр после Моржа (та же цепочка/затвор) ──
            # Паникёр чует толпу структурой (окна MFI). Наследует этаж Искры сам.
            ui.notify("😱 Бужу Паникёра — мерит толпу...", type="info")
            try:
                from studio.modules.trading.panikyor_live import run_panikyor
                pr = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: run_panikyor(symbol="XAUUSD", timeframe="H4"))
            except Exception as e:
                ui.notify(f"Паникёр не проснулся: {e}", type="negative")
                pr = {"ok": False}

            if pr.get("ok"):
                psig = pr.get("signal", {})
                state["reports"]["A03"] = pr.get("narrative", "") or pr.get("raw", "")
                state["panic_signal"] = psig
                state["panic_stats"]  = pr.get("stats", {})
                state["panic_market"] = pr.get("market", {})
                state["panic_last_run"] = {
                    "narrative": pr.get("narrative", ""),
                    "signal":    psig,
                    "market":    pr.get("market", {}),
                }
                state["chat_history"].append({
                    "role": "assistant", "agent": "A03",
                    "content": (f"😱 Толпа: {psig.get('panic_phase','—')}. "
                                f"{psig.get('crowd_sentiment','')} Отчёт справа.")})
                update_chat_display()
                update_avatar_states()
                ui.notify(f"😱 Паникёр: {psig.get('panic_phase','—')}", type="positive")
            else:
                ui.notify("😱 Паникёр смолчал (нет данных или сбой)", type="warning")

            # ── EXCHANGE_HANS: Ганс после Паникёра (та же цепочка/затвор) ──
            # Ганс ищет действительный фрактал вне Красной линии. Наследует
            # этаж Искры сам. БЕЗ ГЕЙТА (§1f) — кладёт факт на стол ВСЕГДА.
            ui.notify("🎯 Бужу Ганса — ищет фрактал...", type="info")
            try:
                from studio.modules.trading.hans_live import run_hans
                hr = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: run_hans(symbol="XAUUSD", timeframe="H4"))
            except Exception as e:
                ui.notify(f"Ганс не проснулся: {e}", type="negative")
                hr = {"ok": False}

            if hr.get("ok"):
                hsig = hr.get("signal", {})
                state["reports"]["A04"] = hr.get("narrative", "") or hr.get("raw", "")
                state["hans_signal"] = hsig
                state["hans_stats"]  = hr.get("stats", {})
                state["hans_market"] = hr.get("market", {})
                state["hans_last_run"] = {
                    "narrative": hr.get("narrative", ""),
                    "signal":    hsig,
                    "market":    hr.get("market", {}),
                }
                valid = hsig.get("fractal_valid")
                prey = (f"добыча {hsig.get('fractal_side','—')} "
                        f"@ {hsig.get('fractal_price','—')}" if valid
                        else "добычи нет")
                state["chat_history"].append({
                    "role": "assistant", "agent": "A04",
                    "content": (f"🎯 Фрактал: {prey}. Отчёт справа.")})
                update_chat_display()
                update_avatar_states()
                ui.notify(f"🎯 Ганс: {'фрактал вне Красной' if valid else 'пусто'}",
                          type="positive")
            else:
                ui.notify("🎯 Ганс смолчал (нет данных или сбой)", type="warning")

    # ── Подсветка активного пузырька ─────────────────────────
    def update_avatar_states():
        for aid, el in avatars_ref["elements"].items():
            el.classes(remove="active done")
            if aid == state["active_agent"]:
                el.classes(add="active")
            if aid in state["reports"]:
                el.classes(add="done")

    # ── Клик по пузырьку агента ──────────────────────────────
    def switch_agent(agent_id: str):
        state["active_agent"] = agent_id
        update_avatar()
        update_avatar_states()
        update_stats_panel()
        label = _agent_label(agent_id)
        if agent_id in state["reports"]:
            update_viewer(f"# {label} ({agent_id})\n\n{state['reports'][agent_id]}")
        else:
            update_viewer(f"# {label} ({agent_id})\n\n"
                          f"*Отчёт пока не создан. Совет ещё не подключён к этому каркасу.*")

    # ── Загрузчик (левая колонка) ────────────────────────────
    def update_files_display():
        if not files_ref["element"]:
            return
        files_ref["element"].clear()
        with files_ref["element"]:
            if not state["uploaded_files"]:
                ui.label("Нет файлов").style("color: rgba(255,255,255,0.4)")
            else:
                for f in state["uploaded_files"]:
                    ui.label(f["name"]).style(
                        "color: rgba(255,255,255,0.8); font-size: 11px;")

    def handle_upload(e):
        # Пока просто фиксируем имя файла в списке — без обработки.
        # Реальный разбор истории для тестера придёт позже.
        state["uploaded_files"].append({"name": e.name})
        update_files_display()
        ui.notify(f"Загружен: {e.name} (обработка — позже)", type="info")

    def clear_files():
        state["uploaded_files"] = []
        update_files_display()
        ui.notify("Очищено", type="info")

    # ── Чат с агентом в РАБОЧЕМ режиме ───────────────────────
    # Кликнул пузырёк, спросил — агент отвечает живой моделью.
    # Для Искры: подаём её промт + ПОСЛЕДНИЙ ПРОГОН РЫНКА, чтобы она
    # отвечала конкретно про то, что только что насчитала, а не вообще.
    async def send_message():
        if not input_ref["element"]:
            return
        msg = input_ref["element"].value.strip()
        if not msg:
            return
        input_ref["element"].value = ""
        state["chat_history"].append({"role": "user", "content": msg})
        update_chat_display()

        agent_id = state["active_agent"]

        # Живой чат: Искра (A01) и Морж (A02). Остальные — по очереди.
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

        if agent_id == "A03":
            ui.notify("😱 Паникёр чувствует...", type="info")
            try:
                from studio.modules.trading.panikyor_live import chat_with_panikyor
                dialog = [m for m in state["chat_history"]
                          if m.get("role") in ("user", "assistant") and m.get("content")]
                reply = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: chat_with_panikyor(msg, state.get("panic_last_run"), dialog))
            except Exception as e:
                reply = f"⚠️ Паникёр не смог ответить: {e}"
            state["chat_history"].append({
                "role": "assistant", "agent": "A03", "content": reply})
            update_chat_display()
            return

        if agent_id == "A04":
            ui.notify("🎯 Ганс на следу...", type="info")
            try:
                from studio.modules.trading.hans_live import chat_with_hans
                dialog = [m for m in state["chat_history"]
                          if m.get("role") in ("user", "assistant") and m.get("content")]
                reply = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: chat_with_hans(msg, state.get("hans_last_run"), dialog))
            except Exception as e:
                reply = f"⚠️ Ганс не смог ответить: {e}"
            state["chat_history"].append({
                "role": "assistant", "agent": "A04", "content": reply})
            update_chat_display()
            return

        if agent_id != "A01":
            state["chat_history"].append({
                "role": "assistant", "agent": agent_id,
                "content": f"{_agent_label(agent_id)} ещё не подключён к живому "
                           f"разговору — рожаем агентов по очереди, шеф."})
            update_chat_display()
            return

        ui.notify("✴️ Искра думает...", type="info")
        try:
            from studio.modules.trading.iskra_live import chat_with_iskra
            # Собираем историю личного диалога (только user/assistant текст)
            dialog = [m for m in state["chat_history"]
                      if m.get("role") in ("user", "assistant") and m.get("content")]
            reply = await asyncio.get_event_loop().run_in_executor(
                None, lambda: chat_with_iskra(msg, state.get("iskra_last_run"), dialog))
        except Exception as e:
            state["chat_history"].append({
                "role": "assistant", "agent": "A01",
                "content": f"⚠️ Не смогла ответить: {e}"})
            update_chat_display()
            return

        state["chat_history"].append({
            "role": "assistant", "agent": "A01", "content": reply})
        update_chat_display()

    # ═══ LAYOUT — точная калька воркшопа ═════════════════════
    with ui.element("div").classes("app-container"):

        # ─── HEADER: пузырьки трейдеров ──────────────────────
        with ui.element("div").classes("area-header"):
            with ui.element("div").classes("glass squad-deck").style(
                "display:flex; align-items:center; width:100%; gap:8px; "
                "padding:0 8px; position:relative;"
            ):
                with ui.element("div").style(
                    "display:flex; align-items:center; gap:6px; flex-wrap:wrap; "
                    "justify-content:center; flex:1;"
                ):
                    for a in TRADING_COUNCIL:
                        aid = a["id"]
                        avatar = ui.element("div").classes(
                            f'avatar {"active" if aid == "A01" else ""}')
                        avatar.on("click", lambda e, w=aid: switch_agent(w))
                        with avatar:
                            ui.label(aid).style("font-size: 10px")
                        avatars_ref["elements"][aid] = avatar

        # ─── LEFT: только загрузчик ──────────────────────────
        with ui.element("div").classes("area-left"):
            with ui.element("div").classes("left-col"):
                with ui.element("div").classes("glass asset-bay").style(
                    "height:auto; flex:1;"
                ):
                    with ui.row().style(
                        "width:100%; justify-content:space-between; align-items:center; "
                        "padding:8px 16px 6px 16px; "
                        "border-bottom:1px solid rgba(255,255,255,0.08);"
                    ):
                        ui.label("ЗАГРУЗЧИК").style(
                            "color:rgba(255,255,255,0.92); font-weight:900; "
                            "letter-spacing:.12em; text-transform:uppercase; font-size:11px;")
                        ui.button("CLEAR", on_click=clear_files).props(
                            "flat dense size=xs").style(
                            "color:rgba(255,80,80,0.5); font-size:9px;")
                    files_ref["element"] = ui.element("div").classes("file-list")
                    with files_ref["element"]:
                        ui.label("Нет файлов").style("color: rgba(255,255,255,0.4)")
                    ui.upload(
                        on_upload=handle_upload,
                        multiple=True,
                        auto_upload=True,
                    ).props("flat color=cyan").style("margin: 0 8px 8px 8px;")

        # ─── STAGE: чат + отчёты ─────────────────────────────
        with ui.element("div").classes("area-stage"):
            with ui.element("div").classes("glass stage-monitor").style(
                "height:100%; overflow:hidden;"
            ):
                # Тулбар — кнопка РЫНОК (стиль как BRIEF/ASSETS воркшопа).
                with ui.element("div").classes("stage-toolbar").style("flex-shrink:0;"):
                    with ui.element("div").style("display:flex; gap:6px; align-items:center;"):
                        ui.button("📡 РЫНОК", on_click=run_market).props("flat").style('''
                            padding: 8px 18px; border-radius: 8px;
                            background: linear-gradient(135deg, rgba(0,255,136,0.15), rgba(0,204,255,0.10)) !important;
                            border: 1px solid rgba(0,255,136,0.35);
                            color: rgba(255,255,255,0.9); font-weight: 700;
                        ''')
                    with ui.element("div").style(
                        "display:flex; gap:6px; align-items:center; justify-content:center;"
                    ):
                        ui.label("📊 БИРЖА · СОВЕТ").style(
                            "color:rgba(0,204,255,0.7); font-weight:800; "
                            "font-size:0.8rem; letter-spacing:0.08em;")
                    with ui.row().style("gap:8px; justify-content:flex-end;"):
                        ui.button("← Дашборд",
                                  on_click=lambda: ui.navigate.to("/dashboard")).props(
                            "flat").style(
                            "padding:6px 14px; border-radius:8px; font-size:12px; "
                            "background:rgba(99,130,255,0.08); "
                            "border:1px solid rgba(99,130,255,0.25); "
                            "color:rgba(180,190,220,0.8);")

                with ui.element("div").classes("stage-content").style(
                    "flex:1; min-height:0; overflow:hidden;"
                ):
                    with ui.element("div").classes("split-view").style(
                        "height:100%; min-height:0; overflow:hidden;"
                    ):
                        chat_log_ref["element"] = ui.element("div").classes(
                            "chat-log").style("flex:1; min-height:0; overflow-y:auto;")
                        with chat_log_ref["element"]:
                            ui.html('<div class="chat-msg-system">SYSTEM: Биржа готова</div>')

                        viewer_ref["element"] = ui.element("div").classes(
                            "viewer").style("flex:1; min-height:0; overflow-y:auto;")
                        with viewer_ref["element"]:
                            ui.label("Отчёты агентов появятся здесь")

                # Плавающая консоль ввода
                with ui.element("div").classes("floating-console"):
                    input_ref["element"] = ui.input(
                        placeholder="Сообщение Совету...").props("borderless").style("flex:1")
                    input_ref["element"].on("keydown.enter", send_message)
                    ui.button("SEND", on_click=send_message).classes("send-button")

        # ─── RIGHT: аватар активного агента + цифры ──────────
        with ui.element("div").classes("area-right"):
            with ui.element("div").classes("right-col"):
                avatar_ref["element"] = ui.element("div").classes("right-top-slot")
                with avatar_ref["element"]:
                    ui.html('''
                        <div style="position:relative; width:100%; height:100%; min-height:200px;">
                            <img src="/static/avatars/trading/A01.png"
                                 style="width:100%; height:100%; object-fit:cover;
                                        border-radius:12px; opacity:0.85;"
                                 onerror="this.style.display='none'">
                            <div style="position:absolute; bottom:0; left:0; right:0;
                                        padding:15px; background:linear-gradient(transparent, rgba(0,0,0,0.8));
                                        border-radius:0 0 12px 12px;">
                                <div style="font-size:0.65rem; color:rgba(255,255,255,0.5);">АКТИВНЫЙ АГЕНТ</div>
                                <div style="font-size:1.3rem; font-weight:700; color:#00ff88;">A01</div>
                                <div style="font-size:0.8rem; color:rgba(255,255,255,0.8);">Искра</div>
                            </div>
                        </div>
                    ''')

                # Приборная панель агента (цифры под аватаром)
                with ui.element("div").classes("glass").style(
                    "margin-top:12px; flex-shrink:0; overflow:hidden;"
                ):
                    ui.html('<div class="panel-title">ПРИБОРЫ</div>')
                    stats_ref["element"] = ui.element("div")
                    with stats_ref["element"]:
                        ui.html('<div style="color:rgba(255,255,255,0.3); font-size:11px; '
                                'padding:10px; text-align:center;">Нажми РЫНОК — Искра оживёт</div>')
